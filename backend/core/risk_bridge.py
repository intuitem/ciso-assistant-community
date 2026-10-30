"""Compliance → risk bridge: a requirement assessment bears on a risk scenario when
its requirement shares a threat with the scenario and its audit covers the same
asset. Scenarios without assets fall back to the risk assessment's perimeter.
Only requirements in the audit's scope count: with implementation groups
selected, a requirement must belong to one of them, as in the audit itself.
Read-only joins over existing relations; nothing is stored."""

from collections import defaultdict

from django.db.models import Q

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    RequirementAssessment,
    RiskScenario,
)


def _in_scope(selected_groups, requirement_groups) -> bool:
    return not selected_groups or bool(
        set(selected_groups) & set(requirement_groups or [])
    )


def _scoped(queryset):
    """`queryset` narrowed to requirement assessments in their audit's scope."""
    # shortcut: JSON overlap is not portable to SQLite, so the scope is checked in Python.
    rows = queryset.values_list(
        "id",
        "compliance_assessment__selected_implementation_groups",
        "requirement__implementation_groups",
    )
    return queryset.filter(
        id__in=[
            ra_id for ra_id, selected, groups in rows if _in_scope(selected, groups)
        ]
    )


def related_requirement_assessments(scenario: RiskScenario):
    threat_ids = list(scenario.threats.values_list("id", flat=True))
    if not threat_ids:
        return RequirementAssessment.objects.none()
    queryset = RequirementAssessment.objects.filter(
        requirement__assessable=True, requirement__threats__in=threat_ids
    )
    asset_ids = list(scenario.assets.values_list("id", flat=True))
    if asset_ids:
        queryset = queryset.filter(compliance_assessment__assets__in=asset_ids)
    elif perimeter_id := scenario.risk_assessment.perimeter_id:
        queryset = queryset.filter(compliance_assessment__perimeter_id=perimeter_id)
    else:
        return RequirementAssessment.objects.none()
    return _scoped(queryset.distinct())


def related_scenarios_by_requirement_assessment(
    compliance_assessment: ComplianceAssessment, scenarios=None
) -> dict:
    """{requirement assessment id: [scenario, …]}, the reverse of
    related_requirement_assessments over one audit. `scenarios` narrows the
    candidates (e.g. to the ones the user may view)."""
    selected = compliance_assessment.selected_implementation_groups
    threats_by_ra = defaultdict(set)
    for ra_id, threat_id, groups in RequirementAssessment.objects.filter(
        compliance_assessment=compliance_assessment,
        requirement__assessable=True,
        requirement__threats__isnull=False,
    ).values_list("id", "requirement__threats", "requirement__implementation_groups"):
        if _in_scope(selected, groups):
            threats_by_ra[ra_id].add(threat_id)
    if not threats_by_ra:
        return {}

    scope = Q(assets__in=compliance_assessment.assets.all())
    if compliance_assessment.perimeter_id:
        scope |= Q(
            assets__isnull=True,
            risk_assessment__perimeter_id=compliance_assessment.perimeter_id,
        )
    candidates = scenarios if scenarios is not None else RiskScenario.objects.all()
    all_threats = set().union(*threats_by_ra.values())
    matched = (
        candidates.filter(scope, threats__in=all_threats)
        .distinct()
        .select_related("risk_assessment__risk_matrix")
        .prefetch_related("threats")
    )

    result = defaultdict(list)
    for scenario in matched:
        scenario_threats = {t.id for t in scenario.threats.all()}
        for ra_id, ra_threats in threats_by_ra.items():
            if ra_threats & scenario_threats:
                result[ra_id].append(scenario)
    return result


def suggested_controls(scenario: RiskScenario, requirement_assessments) -> list[dict]:
    """Applied controls carried by the related requirement assessments and not yet
    on the scenario, each with the requirement assessments it comes from and
    where it would land: existing when active, planned otherwise."""
    on_scenario = set(scenario.applied_controls.values_list("id", flat=True)) | set(
        scenario.existing_applied_controls.values_list("id", flat=True)
    )
    via = defaultdict(list)
    for ra in requirement_assessments.select_related(
        "requirement", "compliance_assessment"
    ).prefetch_related("applied_controls"):
        for control in ra.applied_controls.all():
            if control.id not in on_scenario:
                via[control.id].append(ra)
    controls = AppliedControl.objects.filter(id__in=via).order_by("name")
    return [
        {
            "control": control,
            "target": "existing"
            if control.status == AppliedControl.Status.ACTIVE
            else "planned",
            "via": via[control.id],
        }
        for control in controls
    ]


def likelihood_suggestions(
    scenario: RiskScenario, requirement_assessments
) -> list[dict]:
    """Likelihoods the audits holding the related requirements compute for the
    scenario's threats: framework number rules carrying `likelihood_of` (a threat
    URN), valued 1 to the matrix's number of probabilities."""
    threats = {t.urn: t for t in scenario.threats.all() if t.urn}
    probabilities = scenario.get_matrix().get("probability") or []
    audits = ComplianceAssessment.objects.filter(
        id__in=requirement_assessments.values("compliance_assessment")
    ).select_related("framework")
    suggestions = []
    for audit in audits:
        for rule in audit.framework.outcomes_definition or []:
            threat = threats.get(rule.get("likelihood_of"))
            value = (audit.computed_values or {}).get(rule.get("ref_id"))
            if threat is None or not value or not 1 <= value <= len(probabilities):
                continue
            index = int(value) - 1
            suggestions.append(
                {
                    "audit": audit,
                    "threat": threat,
                    "probability": index,
                    "name": probabilities[index].get("name"),
                }
            )
    return suggestions
