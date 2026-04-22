"""
Helper for Summary page (Compliance Section)
"""

from django.db.models import Prefetch
from django.db.models.functions import Lower

from core.models import RequirementAssessment


def _matches_selected_groups(compliance_assessment, requirement) -> bool:
    """
    Return whether a requirement should be included for recap computations.

    Recap follows the assessment's selected implementation groups: when groups are
    configured, requirements outside those groups are ignored. When no groups are
    configured, all assessable requirements are included.
    """
    if not compliance_assessment.selected_implementation_groups:
        return True

    selected_groups = set(compliance_assessment.selected_implementation_groups)
    if not selected_groups:
        return True

    requirement_groups = set(requirement.implementation_groups or [])
    return bool(selected_groups & requirement_groups)


def _build_result_counts(compliance_assessment, requirement_assessments):
    """
    Build the raw result counters consumed by the recap frontend.

    The backend intentionally returns counts only; colors, percentages, and chart
    formatting are rebuilt on the frontend.
    """
    counts = {result: 0 for result in RequirementAssessment.Result.values}

    for requirement_assessment in requirement_assessments:
        if _matches_selected_groups(
            compliance_assessment, requirement_assessment.requirement
        ):
            counts[requirement_assessment.result] = (
                counts.get(requirement_assessment.result, 0) + 1
            )

    return counts


def _build_score_summary(compliance_assessment, requirement_assessments):
    """
    Compute the score subset needed by /recap.

    This mirrors the global score business rules already used elsewhere in the
    product, but only returns the fields currently displayed by recap.
    """
    if compliance_assessment.anchor_na_to_target:
        scored = [
            requirement_assessment
            for requirement_assessment in requirement_assessments
            if not (
                requirement_assessment.result
                != RequirementAssessment.Result.NOT_APPLICABLE
                and requirement_assessment.is_scored is False
            )
        ]
    else:
        scored = [
            requirement_assessment
            for requirement_assessment in requirement_assessments
            if requirement_assessment.is_scored is not False
            and requirement_assessment.result
            != RequirementAssessment.Result.NOT_APPLICABLE
        ]

    implementation_groups = (
        set(compliance_assessment.selected_implementation_groups)
        if compliance_assessment.selected_implementation_groups
        else None
    )

    na_target = None
    if compliance_assessment.anchor_na_to_target:
        na_target = (
            compliance_assessment.target_score
            if compliance_assessment.target_score is not None
            else compliance_assessment.max_score
        )

    implementation_score = compliance_assessment._compute_score_for_field(
        scored, implementation_groups, "score", na_target
    )

    documentation_score = None
    if compliance_assessment.show_documentation_score:
        documentation_score = compliance_assessment._compute_score_for_field(
            scored, implementation_groups, "documentation_score", na_target
        )

    enabled_scores = [
        score
        for score in [implementation_score, documentation_score]
        if score is not None and score != -1
    ]
    if enabled_scores:
        maturity_score = int(sum(enabled_scores) / len(enabled_scores) * 10) / 10
    else:
        maturity_score = implementation_score

    return {
        "maturity_score": maturity_score,
        "max_score": compliance_assessment.max_score,
    }


def build_compliance_recap_results(compliance_assessments_queryset):
    """
    Build the raw recap payload from a ComplianceAssessment queryset.

    The caller is responsible for providing the base queryset with the correct
    visibility scope. This helper enriches it with the ORM optimizations and
    transforms it into the compact response structure expected by the recap route.
    """
    assessments = list(
        compliance_assessments_queryset.select_related("folder", "framework")
        .prefetch_related(
            Prefetch(
                "requirement_assessments",
                queryset=RequirementAssessment.objects.filter(
                    requirement__assessable=True
                ).select_related("requirement"),
            )
        )
        .order_by(Lower("folder__name"), Lower("name"))
    )

    folders_map = {}
    for assessment in assessments:
        folder_id = str(assessment.folder_id)
        if folder_id not in folders_map:
            folders_map[folder_id] = {
                "id": folder_id,
                "name": assessment.folder.name,
                "compliance_assessments": [],
            }

        requirement_assessments = list(assessment.requirement_assessments.all())
        result_counts = _build_result_counts(assessment, requirement_assessments)
        global_score = _build_score_summary(assessment, requirement_assessments)

        folders_map[folder_id]["compliance_assessments"].append(
            {
                "id": str(assessment.id),
                "name": assessment.name,
                "framework_name": assessment.framework.name,
                "result_counts": result_counts,
                "global_score": global_score,
            }
        )

    return list(folders_map.values())
