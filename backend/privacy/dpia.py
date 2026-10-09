from core.models import AppliedControl, Asset, RiskAssessment, RiskScenario
from django.db import transaction
from django.utils.translation import gettext as _

from .models import (
    ART6_LAWFUL_BASIS_CHOICES,
    ART9_SPECIAL_CATEGORY_CONDITION_CHOICES,
    TRANSFER_MECHANISM_CHOICES,
    DataRecipient,
    DataSubject,
    Dpia,
)

FEARED_EVENTS = [
    (
        "Illegitimate access to personal data",
        "Personal data is disclosed to or accessed by someone who should not see it.",
    ),
    (
        "Unwanted modification of personal data",
        "Personal data is altered, corrupted or falsified without authorisation.",
    ),
    (
        "Disappearance of personal data",
        "Personal data is lost, deleted or becomes unavailable.",
    ),
]

EDPB_MEASURE_STATUS = {
    AppliedControl.Status.ACTIVE: "implemented",
    AppliedControl.Status.IN_PROGRESS: "partially_implemented",
    AppliedControl.Status.DEGRADED: "partially_implemented",
    AppliedControl.Status.DEPRECATED: "deprecated",
}


def supporting_assets(processing):
    return Asset.objects.filter(personal_data__processing=processing).distinct()


@transaction.atomic
def create_risk_registers(dpia: Dpia, risk_matrix) -> Dpia:
    common = {
        "risk_matrix": risk_matrix,
        "folder": dpia.folder,
        "perimeter": dpia.perimeter,
    }
    if dpia.design_risk_assessment is None:
        dpia.design_risk_assessment = RiskAssessment.objects.create(
            name=f"{dpia.name} — {_('design risk')}", **common
        )
    if dpia.incident_risk_assessment is None:
        incident = RiskAssessment.objects.create(
            name=f"{dpia.name} — {_('incident risk')}", **common
        )
        assets = list(supporting_assets(dpia.processing))
        for name, description in FEARED_EVENTS:
            scenario = RiskScenario.objects.create(
                risk_assessment=incident,
                name=_(name),
                description=_(description),
                ref_id=RiskScenario.get_default_ref_id(incident),
            )
            scenario.assets.set(assets)
        dpia.incident_risk_assessment = incident
    dpia.save(update_fields=["design_risk_assessment", "incident_risk_assessment"])
    return dpia


def _label(choices, value):
    return dict(choices).get(value, value)


def _scenarios(risk_assessment):
    if risk_assessment is None:
        return None
    return {
        "id": str(risk_assessment.id),
        "name": risk_assessment.name,
        "risk_matrix": risk_assessment.risk_matrix.name,
        "scenarios": [
            {
                "id": str(s.id),
                "ref_id": s.ref_id,
                "name": s.name,
                "description": s.description,
                "treatment": s.treatment,
                "inherent": s.get_inherent_risk(),
                "current": s.get_current_risk(),
                "residual": s.get_residual_risk(),
                "assets": [a.name for a in s.assets.all()],
                "applied_controls": [c.name for c in s.applied_controls.all()],
            }
            for s in risk_assessment.risk_scenarios.prefetch_related(
                "assets", "applied_controls"
            ).order_by("ref_id", "created_at")
        ],
    }


def _screening(response):
    if response is None:
        return None
    return {
        "id": str(response.id),
        "ref_id": response.ref_id,
        "submitted_at": response.submitted_at,
        "outcomes": [
            {"ref_id": ref_id, "label": o.get("label"), "color": o.get("color")}
            for ref_id, o in (response.computed_outcome or {}).items()
        ],
    }


def _missing(dpia: Dpia, report: dict) -> list[str]:
    missing = []
    if not dpia.reasons:
        missing.append("reasons")
    if not report["description"]["purposes"]:
        missing.append("purposes")
    if not report["description"]["personal_data"]:
        missing.append("personal_data")
    if not report["description"]["data_subjects"]:
        missing.append("data_subjects")
    if not report["description"]["supporting_assets"]:
        missing.append("supporting_assets")
    if not dpia.necessity:
        missing.append("necessity")
    if not dpia.proportionality:
        missing.append("proportionality")
    if dpia.design_risk_assessment is None:
        missing.append("design_risk_assessment")
    if dpia.incident_risk_assessment is None:
        missing.append("incident_risk_assessment")
    if not dpia.method_statement:
        missing.append("method_statement")
    if not dpia.dpo_opinion:
        missing.append("dpo_opinion")
    if not (dpia.data_subject_views or dpia.views_not_sought_reason):
        missing.append("data_subject_views")
    if not dpia.decision:
        missing.append("decision")
    return missing


def build_report(dpia: Dpia) -> dict:
    processing = dpia.processing
    report = {
        "overview": {
            "processing": {
                "id": str(processing.id),
                "ref_id": processing.ref_id,
                "name": processing.name,
                "description": processing.description,
                "status": processing.get_status_display(),
                "nature": [n.name for n in processing.nature.all()],
            },
            "folder": processing.folder.name,
            "dpia": {
                "ref_id": dpia.ref_id,
                "name": dpia.name,
                "version": dpia.version,
                "status": dpia.get_status_display() if dpia.status else "",
            },
        },
        "technical_sheet": {
            "reasons": [
                {"value": r, "label": _label(Dpia.Reason.choices, r)}
                for r in dpia.reasons
            ],
            "screening": _screening(dpia.screening),
            "scope_boundaries": dpia.scope_boundaries,
            "authors": [str(a) for a in dpia.authors.all()],
            "reviewers": [str(r) for r in dpia.reviewers.all()],
            "validated_by": str(dpia.validated_by) if dpia.validated_by else None,
            "validated_at": dpia.validated_at,
            "review_due": dpia.review_due,
        },
        "description": {
            "purposes": [
                {
                    "name": p.name,
                    "legal_basis": _label(ART6_LAWFUL_BASIS_CHOICES, p.legal_basis),
                    "article_9_condition": _label(
                        ART9_SPECIAL_CATEGORY_CONDITION_CHOICES, p.article_9_condition
                    )
                    if p.article_9_condition
                    else None,
                }
                for p in processing.purposes.all()
            ],
            "personal_data": [
                {
                    "name": pd.name,
                    "category": pd.category.name if pd.category else None,
                    "retention": pd.retention,
                    "deletion_policy": pd.get_deletion_policy_display(),
                    "is_sensitive": pd.is_sensitive,
                }
                for pd in processing.personal_data.select_related("category")
            ],
            "data_subjects": [
                {
                    "name": ds.name,
                    "category": _label(DataSubject.CATEGORY_CHOICES, ds.category),
                }
                for ds in processing.data_subjects.all()
            ],
            "recipients": [
                {
                    "name": r.name,
                    "category": _label(DataRecipient.CATEGORY_CHOICES, r.category),
                }
                for r in processing.data_recipients.all()
            ],
            "contractors": [
                {
                    "name": c.name,
                    "entity": c.entity.name if c.entity else None,
                    "relationship_type": c.get_relationship_type_display(),
                    "country": c.country,
                }
                for c in processing.contractors_involved.select_related("entity")
            ],
            "transfers": [
                {
                    "name": t.name,
                    "entity": t.entity.name if t.entity else None,
                    "country": t.country,
                    "transfer_mechanism": _label(
                        TRANSFER_MECHANISM_CHOICES, t.transfer_mechanism
                    ),
                    "guarantees": t.guarantees,
                }
                for t in processing.data_transfers.select_related("entity")
            ],
            "supporting_assets": [
                {"id": str(a.id), "name": a.name, "type": a.type}
                for a in supporting_assets(processing)
            ],
        },
        "measures": [
            {
                "id": str(c.id),
                "ref_id": c.ref_id,
                "name": c.name,
                "category": c.category,
                "status": c.status,
                "edpb_status": EDPB_MEASURE_STATUS.get(c.status, "planned"),
                "eta": c.eta,
                "owner": [str(o) for o in c.owner.all()],
            }
            for c in processing.associated_controls.prefetch_related("owner")
        ],
        "necessity_proportionality": {
            "necessity": dpia.necessity,
            "proportionality": dpia.proportionality,
            "design_risk": _scenarios(dpia.design_risk_assessment),
        },
        "incident_risk": {
            "method_statement": dpia.method_statement,
            "register": _scenarios(dpia.incident_risk_assessment),
        },
        "opinions": {
            "dpo_opinion": dpia.dpo_opinion,
            "dpo_advice_applied": dpia.dpo_advice_applied,
            "data_subject_views": dpia.data_subject_views,
            "views_not_sought_reason": dpia.views_not_sought_reason,
        },
        "decision": {
            "value": dpia.decision,
            "label": dpia.get_decision_display() if dpia.decision else "",
            "conditions": dpia.conditions,
        },
    }
    report["missing"] = _missing(dpia, report)
    return report
