"""Experimental reliance ranking over visible, explicitly linked objects."""

from collections import defaultdict


from django.db.models import Count, Exists, OuterRef, Q

from core.models import (
    Actor,
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Evidence,
    Finding,
    Incident,
    ReferenceControl,
    RequirementAssessment,
    RequirementNode,
    RiskScenario,
    SecurityException,
    TaskTemplate,
    Vulnerability,
)
from core.utils import get_respondent_scoped_folder_ids, is_field_visible_to
from crq.models import QuantitativeRiskHypothesis, QuantitativeRiskScenario
from doc_management.access import published_only_ids
from doc_management.models import DocumentContainer
from global_settings.utils import ff_is_enabled
from iam.models import Folder, RoleAssignment
from privacy.models import DataBreach
from threat_modeling.models import ThreatModel, ThreatModelNode

WEIGHTS = {
    "requirement_assessments": 2,
    "risk_scenarios": 3,
    "quantitative_risk_existing": 3,
    "findings": 2,
    "open_vulnerabilities": 2,
    "data_breaches": 2,
}
RELATIONS = (
    ("risk_treatment", RiskScenario, "applied_controls"),
    ("risk_existing", RiskScenario, "existing_applied_controls"),
    ("findings", Finding, "applied_controls"),
    ("data_breaches", DataBreach, "remediation_measures"),
    ("incidents", Incident, "applied_controls"),
    ("assets", Asset, "applied_controls"),
    ("security_exceptions", SecurityException, "applied_controls"),
    ("evidences", Evidence, "applied_controls"),
    ("documents", DocumentContainer, "applied_controls"),
    ("documents", DocumentContainer, "policies"),
)
QUANTITATIVE_ROLES = ("existing", "added", "removed")
COUNT_KEYS = (
    *dict.fromkeys(key for key, _, _ in RELATIONS),
    "requirement_assessments",
    "audits",
    "open_vulnerabilities",
    "resolved_vulnerabilities",
    "recurring_tasks",
    "threat_models",
    *(f"quantitative_risk_{role}" for role in QUANTITATIVE_ROLES),
)


def _metrics(links):
    counts = {key: len(links.get(key, set())) for key in COUNT_KEYS}
    counts["risk_scenarios"] = len(
        links.get("risk_treatment", set()) | links.get("risk_existing", set())
    )
    return {
        "counts": counts,
        "score": sum(counts[key] * weight for key, weight in WEIGHTS.items()),
    }


def build(controls, user):
    visibility = {}

    def visible(model):
        if model not in visibility:
            allowed = Q(pk__in=RoleAssignment.get_viewable_object_ids(user, model))
            if model is DocumentContainer:
                allowed |= Q(pk__in=published_only_ids(user, model))
            visibility[model] = model.objects.filter(allowed).order_by()
        return visibility[model]

    controls = controls.order_by()
    control_ids = controls.values("pk")
    references = visible(ReferenceControl)
    catalog = dict(
        visible(RequirementNode)
        .filter(reference_controls__in=references.values("pk"))
        .values_list("reference_controls")
        .annotate(count=Count("pk", distinct=True))
    )
    reference_rows = {
        row["id"]: {
            **row,
            "catalog_requirements": catalog.get(row["id"], 0),
            "implementations": 0,
        }
        for row in references.filter(
            Q(pk__in=controls.values("reference_control_id"))
            | Q(requirements__in=visible(RequirementNode).values("pk"))
        )
        .values("id", "name", "ref_id")
        .distinct()
    }
    control_links = defaultdict(lambda: defaultdict(set))

    def linked(queryset, field, *fields):
        return queryset.filter(**{f"{field}__in": control_ids}).values_list(
            field, *fields
        )

    def collect(key, queryset, field, target="pk"):
        for control_id, target_id in linked(queryset, field, target).iterator():
            control_links[control_id][key].add(target_id)

    for key, model, field in RELATIONS:
        collect(key, visible(model), field)

    audits = visible(ComplianceAssessment)
    requirements = visible(RequirementAssessment)
    respondent_folders = get_respondent_scoped_folder_ids(user)
    if respondent_folders:
        actors = Actor.get_all_for_user(user)
        not_respondent = ~Q(folder_id__in=respondent_folders)
        audits = audits.filter(
            not_respondent | Q(requirement_assignments__actor__in=actors)
        ).distinct()
        requirements = requirements.filter(
            not_respondent | Q(assignments__actor__in=actors)
        ).distinct()
    visible_audit_ids = {
        audit.id
        for audit in audits.only("id", "folder_id", "field_visibility")
        if is_field_visible_to(
            audit,
            "applied_controls",
            "respondent" if audit.folder_id in respondent_folders else "auditor",
        )
    }
    for control_id, requirement_id, audit_id in linked(
        requirements,
        "applied_controls",
        "pk",
        "compliance_assessment_id",
    ).iterator():
        if audit_id in visible_audit_ids:
            control_links[control_id]["requirement_assessments"].add(requirement_id)
            control_links[control_id]["audits"].add(audit_id)

    for control_id, vulnerability_id, status in linked(
        visible(Vulnerability), "applied_controls", "pk", "status"
    ).iterator():
        key = (
            "resolved_vulnerabilities"
            if status in Vulnerability.RESOLVED_STATUSES
            else "open_vulnerabilities"
        )
        control_links[control_id][key].add(vulnerability_id)

    collect(
        "recurring_tasks",
        visible(TaskTemplate).filter(enabled=True, is_recurrent=True),
        "applied_controls",
    )
    if ff_is_enabled("threat_modeling"):
        collect(
            "threat_models",
            visible(ThreatModelNode).filter(threat_model__in=visible(ThreatModel)),
            "applied_controls",
            "threat_model_id",
        )
    hypotheses = visible(QuantitativeRiskHypothesis).filter(
        quantitative_risk_scenario__in=visible(QuantitativeRiskScenario)
    )
    for role in QUANTITATIVE_ROLES:
        collect(
            f"quantitative_risk_{role}",
            hypotheses,
            f"{role}_applied_controls",
            "quantitative_risk_scenario_id",
        )

    applied_rows = []
    reference_links = defaultdict(lambda: defaultdict(set))
    visible_domains = dict(visible(Folder).values_list("id", "name"))
    changeable_ids = RoleAssignment.get_changeable_object_ids(user, AppliedControl)
    for control in controls.values(
        "id",
        "name",
        "ref_id",
        "reference_control_id",
        "priority",
        "folder_id",
        can_edit_priority=Exists(changeable_ids.filter(pk=OuterRef("pk"))),
    ):
        control["domain"] = visible_domains.get(control.pop("folder_id"), "")
        links = control_links.get(control["id"], {})
        reference_id = control.pop("reference_control_id")
        reference = reference_rows.get(reference_id)
        if reference is not None:
            reference["implementations"] += 1
            for key, targets in links.items():
                reference_links[reference_id][key].update(targets)
        applied_rows.append({**control, **_metrics(links)})

    def sorted_rows(rows):
        # Catalog controls may have only a reference ID. Keep the API name a
        # string for client-side search and let the UI display the reference ID.
        return sorted(
            ({**row, "name": row["name"] or ""} for row in rows),
            key=lambda row: (
                -row["score"],
                (row["name"] or row["ref_id"] or "").casefold(),
                row["id"],
            ),
        )

    return {
        "weights": WEIGHTS,
        "applied_controls": sorted_rows(applied_rows),
        "reference_controls": sorted_rows(
            {**row, **_metrics(reference_links.get(pk, {}))}
            for pk, row in reference_rows.items()
        ),
    }
