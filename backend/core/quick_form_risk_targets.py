"""`asset.risk_assessment` / `asset.audit` / `asset.accreditation`: an accepted
response writes its asset's risk assessment, audit and homologation cycle.

The form says what to write through its rules' pass-through keys, so a method is
library content, not code:

- a yes/no rule carrying `scenario: {ref_id, name, threats: [urn], impact_value}`
  that fires is one risk scenario on the asset; `impact_value` names the number
  rule giving its impact as a 1-based level of the matrix;
- a yes/no rule carrying `audit_implementation_groups` (and optionally the
  `framework` URN they belong to) that fires gives the audit's scope.

Config: `asset.risk_assessment` takes `risk_matrix` (URN), `asset.audit` takes
`framework` (URN).

Each target finds the assessment it wrote for the same asset last time through
the application log, so accepting again updates it instead of adding another.
Owners, controls and treatment are never touched, and a scenario no longer
retained is kept: treatment may hang off it. An impact is written when the
scenario is created, and updated later only if nobody changed it since.
"""

from django.contrib.contenttypes.models import ContentType

from core.quick_form_targets import Proposal, Target, register


def _fired(response) -> dict:
    outcome = getattr(response, "computed_outcome", None) or {}
    return {k: v for k, v in outcome.items() if isinstance(v, dict)}


def _last_value(key: str, subject) -> dict:
    """What the last application of `key` on `subject` wrote, as logged."""
    from core.models import QuickFormApplication

    application = (
        QuickFormApplication.objects.filter(
            target=key,
            subject_content_type=ContentType.objects.get_for_model(subject),
            subject_object_id=subject.pk,
        )
        .order_by("-created_at")
        .first()
    )
    value = application.new_value if application else None
    return value if isinstance(value, dict) else {}


def _last_written(key: str, subject, model):
    """The object the last application of `key` on `subject` wrote, if it still
    exists."""
    object_id = _last_value(key, subject).get("id")
    return model.objects.filter(pk=object_id).first() if object_id else None


def _name(*parts) -> str:
    return " · ".join(str(p) for p in parts if p)[:200]


@register
class AssetRiskAssessmentTarget(Target):
    key = "asset.risk_assessment"
    subject_model = "core.Asset"
    permission = "add_riskassessment"
    label = "riskAssessment"

    def validate_config(self, config, quick_form) -> list[str]:
        return (
            [] if isinstance(config.get("risk_matrix"), str) else ["riskMatrixRequired"]
        )

    def health(self, config, quick_form, cache=None) -> list[str]:
        from core.models import RiskMatrix

        errors = self.validate_config(config, quick_form)
        if (
            not errors
            and not RiskMatrix.objects.filter(urn=config["risk_matrix"]).exists()
        ):
            errors.append("riskMatrixNotLoaded")
        return errors

    def current(self, subject):
        from core.models import RiskAssessment

        assessment = _last_written(self.key, subject, RiskAssessment)
        return (str(assessment.pk), str(assessment)) if assessment else (None, "")

    def resolve(self, response, config, override=None) -> Proposal:
        from core.models import RiskMatrix, Threat

        matrix = RiskMatrix.objects.filter(urn=config.get("risk_matrix")).first()
        if matrix is None:
            return Proposal.refuse("riskMatrixNotLoaded")
        impacts = len(matrix.parse_json().get("impact") or [])
        values = getattr(response, "computed_values", None) or {}

        def impact(spec) -> int | None:
            level = values.get(spec.get("impact_value"))
            return int(level) - 1 if level and 1 <= level <= impacts else None

        # Copies: the specs are the response's stored outcome, not to be mutated.
        scenarios = [
            {**payload["scenario"], "impact": impact(payload["scenario"])}
            for payload in _fired(response).values()
            if isinstance(payload.get("scenario"), dict)
            and payload["scenario"].get("ref_id")
        ]
        if not scenarios:
            return Proposal.refuse("noScenario")
        urns = {u for s in scenarios for u in s.get("threats") or []}
        # Fail closed: a scenario without its threat would never meet its requirements.
        if Threat.objects.filter(urn__in=urns).count() != len(urns):
            return Proposal.refuse("threatsNotLoaded")
        return Proposal(
            ok=True,
            value={"risk_matrix": config["risk_matrix"], "scenarios": scenarios},
            display=", ".join(s["ref_id"] for s in scenarios),
        )

    def apply(self, subject, proposal, *, response, user) -> None:
        from core.models import RiskAssessment, RiskMatrix, RiskScenario, Threat

        value = proposal.value
        assessment = _last_written(self.key, subject, RiskAssessment)
        written = {
            s.get("ref_id"): s.get("impact")
            for s in _last_value(self.key, subject).get("scenarios") or []
        }
        if assessment is None:
            assessment = RiskAssessment.objects.create(
                name=_name(response.quick_form.name, subject.name),
                folder=subject.folder,
                risk_matrix=RiskMatrix.objects.get(urn=value["risk_matrix"]),
            )
        for spec in value["scenarios"]:
            scenario = RiskScenario.objects.filter(
                risk_assessment=assessment, ref_id=spec["ref_id"]
            ).first() or RiskScenario.objects.create(
                risk_assessment=assessment,
                ref_id=spec["ref_id"],
                name=str(spec.get("name") or spec["ref_id"])[:200],
            )
            scenario.threats.add(
                *Threat.objects.filter(urn__in=spec.get("threats") or [])
            )
            scenario.assets.add(subject)
            last = written.get(spec["ref_id"])
            unchanged = scenario.current_impact == (-1 if last is None else last)
            if spec.get("impact") is not None and unchanged:
                scenario.current_impact = spec["impact"]
                scenario.save()
        # The log row is written from the proposal after this: keep the id there so
        # the next acceptance finds this assessment again.
        value["id"] = str(assessment.pk)


@register
class AssetAuditTarget(Target):
    key = "asset.audit"
    subject_model = "core.Asset"
    permission = "add_complianceassessment"
    label = "complianceAssessment"

    def validate_config(self, config, quick_form) -> list[str]:
        return [] if isinstance(config.get("framework"), str) else ["frameworkRequired"]

    def health(self, config, quick_form, cache=None) -> list[str]:
        from core.models import Framework

        errors = self.validate_config(config, quick_form)
        if (
            not errors
            and not Framework.objects.filter(urn=config["framework"]).exists()
        ):
            errors.append("frameworkNotLoaded")
        return errors

    def current(self, subject):
        from core.models import ComplianceAssessment

        audit = _last_written(self.key, subject, ComplianceAssessment)
        return (str(audit.pk), str(audit)) if audit else (None, "")

    def resolve(self, response, config, override=None) -> Proposal:
        from core.models import Framework

        framework = Framework.objects.filter(urn=config.get("framework")).first()
        if framework is None:
            return Proposal.refuse("frameworkNotLoaded")
        groups = sorted(
            {
                group
                for payload in _fired(response).values()
                if payload.get("framework") in (None, framework.urn)
                for group in payload.get("audit_implementation_groups") or []
            }
        )
        if not groups:
            return Proposal.refuse("implementationGroupsUndetermined")
        names = {
            g.get("ref_id"): g.get("name")
            for g in framework.implementation_groups_definition or []
        }
        if any(g not in names for g in groups):
            return Proposal.refuse("unknownImplementationGroup")
        return Proposal(
            ok=True,
            value={"framework": framework.urn, "implementation_groups": groups},
            display=", ".join(str(names[g]) for g in groups),
        )

    def apply(self, subject, proposal, *, response, user) -> None:
        from core.models import ComplianceAssessment, Framework

        value = proposal.value
        audit = _last_written(self.key, subject, ComplianceAssessment)
        if audit is None:
            framework = Framework.objects.get(urn=value["framework"])
            audit = ComplianceAssessment.objects.create(
                name=_name(framework.name, subject.name),
                framework=framework,
                folder=subject.folder,
                selected_implementation_groups=value["implementation_groups"],
            )
            audit.create_requirement_assessments()
            audit.assets.add(subject)
        else:
            audit.selected_implementation_groups = value["implementation_groups"]
            audit.save(update_fields=["selected_implementation_groups"])
        value["id"] = str(audit.pk)


@register
class AssetAccreditationTarget(Target):
    """Opens or updates the asset's homologation cycle, with the risk assessment
    and audit the two targets above wrote in its collection: list it after them.

    The category comes from a fired rule carrying `accreditation_category` (an
    accreditation category name). A cycle already decided is never reopened: the
    next acceptance starts a new one. Config: optional `name`."""

    key = "asset.accreditation"
    subject_model = "core.Asset"
    permission = "add_accreditation"
    label = "accreditation"

    CLOSED = ("accredited", "not_accredited", "obsolete")

    def current(self, subject):
        from pmbok.models import Accreditation

        cycle = _last_written(self.key, subject, Accreditation)
        return (str(cycle.pk), str(cycle)) if cycle else (None, "")

    def resolve(self, response, config, override=None) -> Proposal:
        from core.models import Terminology

        names = {
            payload["accreditation_category"]
            for payload in _fired(response).values()
            if payload.get("accreditation_category")
        }
        if len(names) != 1:
            return Proposal.refuse("accreditationCategoryUndetermined")
        (name,) = names
        if not Terminology.objects.filter(
            field_path=Terminology.FieldPath.ACCREDITATION_CATEGORY, name=name
        ).exists():
            return Proposal.refuse("accreditationCategoryUnknown")
        return Proposal(
            ok=True, value={"category": name, "name": config.get("name")}, display=name
        )

    def apply(self, subject, proposal, *, response, user) -> None:
        from core.models import ComplianceAssessment, RiskAssessment, Terminology
        from pmbok.models import Accreditation, GenericCollection

        value = proposal.value
        category = Terminology.objects.get(
            field_path=Terminology.FieldPath.ACCREDITATION_CATEGORY,
            name=value["category"],
        )
        cycle = _last_written(self.key, subject, Accreditation)
        if cycle is None or cycle.status.name in self.CLOSED:
            name = _name(value.get("name") or response.quick_form.name, subject.name)
            cycle = Accreditation.objects.create(
                name=name,
                folder=subject.folder,
                asset=subject,
                category=category,
                status=Terminology.objects.get(
                    field_path=Terminology.FieldPath.ACCREDITATION_STATUS, name="draft"
                ),
                linked_collection=GenericCollection.objects.create(
                    name=name, folder=subject.folder
                ),
            )
        else:
            cycle.category = category
            cycle.save(update_fields=["category"])
        if cycle.linked_collection is None:
            cycle.linked_collection = GenericCollection.objects.create(
                name=cycle.name, folder=subject.folder
            )
            cycle.save(update_fields=["linked_collection"])
        collection = cycle.linked_collection
        if assessment := _last_written(
            AssetRiskAssessmentTarget.key, subject, RiskAssessment
        ):
            collection.set_items(
                "risk_assessments",
                [*collection.get_items("risk_assessments"), assessment],
            )
        if audit := _last_written(AssetAuditTarget.key, subject, ComplianceAssessment):
            collection.set_items(
                "compliance_assessments",
                [*collection.get_items("compliance_assessments"), audit],
            )
        value["id"] = str(cycle.pk)


JOURNEY_TARGETS = (
    AssetRiskAssessmentTarget.key,
    AssetAuditTarget.key,
    AssetAccreditationTarget.key,
)


def journey_of(asset, user) -> dict:
    """Where the asset stands in a form-driven assessment: the latest response
    about it from a form writing these targets, and what was written, each only
    if the user may view it."""
    from core.models import (
        ComplianceAssessment,
        QuickFormResponse,
        RiskAssessment,
    )
    from core.quick_form_apply import forms_with_target
    from iam.models import RoleAssignment
    from pmbok.models import Accreditation

    def viewable(obj):
        return obj and RoleAssignment.is_object_readable(user, type(obj), obj.pk)

    forms = {f for key in JOURNEY_TARGETS for f in forms_with_target(key)}
    response = (
        QuickFormResponse.objects.filter(
            quick_form_id__in=forms,
            subject_content_type=ContentType.objects.get_for_model(asset),
            subject_object_id=asset.pk,
        )
        .order_by("-updated_at")
        .first()
    )
    assessment = _last_written(AssetRiskAssessmentTarget.key, asset, RiskAssessment)
    audit = _last_written(AssetAuditTarget.key, asset, ComplianceAssessment)
    cycle = _last_written(AssetAccreditationTarget.key, asset, Accreditation)
    return {
        "response": {
            "id": str(response.pk),
            "ref_id": response.ref_id,
            "status": response.status,
            "quick_form": response.quick_form.get_name_translated,
            "updated_at": response.updated_at,
        }
        if viewable(response)
        else None,
        "risk_assessment": {
            "id": str(assessment.pk),
            "str": str(assessment),
            "scenarios": assessment.risk_scenarios.count(),
        }
        if viewable(assessment)
        else None,
        "audit": {"id": str(audit.pk), "str": str(audit), "progress": audit.progress}
        if viewable(audit)
        else None,
        "accreditation": {
            "id": str(cycle.pk),
            "str": str(cycle),
            "status": cycle.status.name,
            "category": cycle.category.name,
            "expiry_date": cycle.expiry_date,
        }
        if viewable(cycle)
        else None,
        "past_cycles": Accreditation.objects.filter(asset=asset)
        .exclude(pk=cycle.pk if cycle else None)
        .count(),
    }
