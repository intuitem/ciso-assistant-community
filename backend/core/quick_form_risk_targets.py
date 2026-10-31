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
from django.db.models import Q
from django.utils import timezone

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
    """Keeps the category of the asset's homologation in progress in step with
    the framing. Framing describes the service; it never opens a cycle (see
    `start_accreditation`) and leaves alone a cycle whose deliverables are frozen
    (see `freeze_accreditation`) or that is decided.

    The category comes from a fired rule carrying `accreditation_category` (an
    accreditation category name). Config: optional `name`, for the cycles
    `start_accreditation` opens."""

    key = "asset.accreditation"
    subject_model = "core.Asset"
    permission = "change_accreditation"
    label = "accreditation"

    CLOSED = ("accredited", "not_accredited", "obsolete")

    def current(self, subject):
        cycle = current_cycle(subject)
        return (str(cycle.pk), str(cycle)) if cycle else (None, "")

    def resolve(self, response, config, override=None) -> Proposal:
        from core.models import Asset

        name, reason = framed_category(response)
        if reason:
            return Proposal.refuse(reason)
        asset = Asset.objects.filter(pk=response.subject_object_id).first()
        cycle = current_cycle(asset) if asset else None
        if cycle is None or not is_open(cycle):
            return Proposal.refuse("noAccreditationInProgress")
        if is_frozen(cycle, asset):
            return Proposal.refuse("accreditationDeliverablesFrozen")
        return Proposal(ok=True, value={"category": name}, display=name)

    def apply(self, subject, proposal, *, response, user) -> None:
        from core.models import Terminology

        cycle = current_cycle(subject)
        cycle.category = Terminology.objects.get(
            field_path=Terminology.FieldPath.ACCREDITATION_CATEGORY,
            name=proposal.value["category"],
        )
        cycle.save(update_fields=["category"])
        proposal.value["id"] = str(cycle.pk)


def framed_category(response) -> tuple[str | None, str | None]:
    """The accreditation category a framing response calls for, or why none."""
    from core.models import Terminology

    names = {
        payload["accreditation_category"]
        for payload in _fired(response).values()
        if payload.get("accreditation_category")
    }
    if len(names) != 1:
        return None, "accreditationCategoryUndetermined"
    (name,) = names
    if not Terminology.objects.filter(
        field_path=Terminology.FieldPath.ACCREDITATION_CATEGORY, name=name
    ).exists():
        return None, "accreditationCategoryUnknown"
    return name, None


def current_cycle(asset):
    """The asset's latest homologation cycle."""
    from pmbok.models import Accreditation

    return Accreditation.objects.filter(asset=asset).order_by("-created_at").first()


def is_open(cycle) -> bool:
    return not (cycle.status and cycle.status.name in AssetAccreditationTarget.CLOSED)


def living_service(asset):
    """The risk assessment and audit the framing keeps up to date."""
    from core.models import ComplianceAssessment, RiskAssessment

    return (
        _last_written(AssetRiskAssessmentTarget.key, asset, RiskAssessment),
        _last_written(AssetAuditTarget.key, asset, ComplianceAssessment),
    )


def is_frozen(cycle, asset) -> bool:
    """Frozen once the cycle holds copies rather than the living service."""
    if cycle.linked_collection is None:
        return False
    assessment, _ = living_service(asset)
    linked = cycle.linked_collection.get_items("risk_assessments")
    return linked.exists() and not (
        assessment and linked.filter(pk=assessment.pk).exists()
    )


def _last_framing(asset):
    from core.models import QuickFormResponse
    from core.quick_form_apply import forms_with_target

    forms = {f for key in JOURNEY_TARGETS for f in forms_with_target(key)}
    return (
        QuickFormResponse.objects.filter(
            quick_form_id__in=forms,
            subject_content_type=ContentType.objects.get_for_model(asset),
            subject_object_id=asset.pk,
            status=QuickFormResponse.Status.CLOSED,
            resolution__in=[
                QuickFormResponse.Resolution.ACCEPTED,
                QuickFormResponse.Resolution.AUTO,
            ],
        )
        .order_by("-updated_at")
        .first()
    )


def _allowed(user, folder, *codenames) -> bool:
    from django.contrib.auth.models import Permission
    from iam.models import RoleAssignment

    return all(
        RoleAssignment.is_access_allowed(
            user=user, perm=Permission.objects.get(codename=codename), folder=folder
        )
        for codename in codenames
    )


def start_accreditation(asset, user):
    """Open the asset's next homologation cycle, on the living service and with
    the category its last framing calls for. Returns (cycle, error code)."""
    from core.models import Terminology
    from pmbok.models import Accreditation, GenericCollection

    if not _allowed(user, asset.folder, "add_accreditation"):
        return None, "permissionDenied"
    cycle = current_cycle(asset)
    if cycle is not None and is_open(cycle):
        return None, "accreditationInProgress"
    framing = _last_framing(asset)
    if framing is None:
        return None, "notFramedYet"
    category, reason = framed_category(framing)
    if reason:
        return None, reason
    config = next(
        (
            entry.get("config") or {}
            for entry in framing.quick_form.on_accept or []
            if entry.get("target") == AssetAccreditationTarget.key
        ),
        {},
    )
    name = _name(
        config.get("name") or framing.quick_form.name,
        asset.name,
        timezone.localdate().year,
    )
    cycle = Accreditation.objects.create(
        name=name,
        folder=asset.folder,
        asset=asset,
        category=Terminology.objects.get(
            field_path=Terminology.FieldPath.ACCREDITATION_CATEGORY, name=category
        ),
        status=Terminology.objects.get(
            field_path=Terminology.FieldPath.ACCREDITATION_STATUS, name="draft"
        ),
        linked_collection=GenericCollection.objects.create(
            name=name, folder=asset.folder
        ),
    )
    assessment, audit = living_service(asset)
    if assessment:
        cycle.linked_collection.set_items("risk_assessments", [assessment])
    if audit:
        cycle.linked_collection.set_items("compliance_assessments", [audit])
    return cycle, None


def freeze_accreditation(asset, user):
    """Put copies of the living service in the cycle in progress: reviewers then
    work on a version that later framings leave alone, and that stays editable
    until the decision. Returns (cycle, error code)."""
    if not _allowed(
        user,
        asset.folder,
        "change_accreditation",
        "add_riskassessment",
        "add_complianceassessment",
    ):
        return None, "permissionDenied"
    cycle = current_cycle(asset)
    if cycle is None or not is_open(cycle):
        return None, "noAccreditationInProgress"
    if is_frozen(cycle, asset):
        return None, "accreditationDeliverablesFrozen"
    assessment, audit = living_service(asset)
    if assessment is None and audit is None:
        return None, "notFramedYet"
    collection = cycle.linked_collection
    if assessment:
        collection.set_items("risk_assessments", [_copy_risk_assessment(assessment)])
    if audit:
        collection.set_items("compliance_assessments", [_copy_audit(audit)])
    return cycle, None


JOURNEY_TARGETS = (
    AssetRiskAssessmentTarget.key,
    AssetAuditTarget.key,
    AssetAccreditationTarget.key,
)


def _next_version(version: str | None) -> str:
    try:
        return f"{int(float(version)) + 1}.0"
    except TypeError, ValueError:
        return f"{version or ''} (2)".strip()


def _copy_risk_assessment(source):
    """A cycle's frozen risk assessment: the living one's scenarios with their
    levels, threats, assets and controls, as people left them."""
    from core.models import RiskAssessment, RiskScenario

    copy = RiskAssessment.objects.create(
        name=source.name,
        description=source.description,
        perimeter=source.perimeter,
        folder=source.folder,
        version=_next_version(source.version),
        risk_matrix=source.risk_matrix,
        ref_id=source.ref_id,
        status=source.status,
    )
    copy.authors.set(source.authors.all())
    copy.reviewers.set(source.reviewers.all())
    for scenario in source.risk_scenarios.all():
        twin = RiskScenario.objects.create(
            risk_assessment=copy,
            ref_id=scenario.ref_id,
            name=scenario.name,
            description=scenario.description,
            treatment=scenario.treatment,
            inherent_proba=scenario.inherent_proba,
            inherent_impact=scenario.inherent_impact,
            current_proba=scenario.current_proba,
            current_impact=scenario.current_impact,
            residual_proba=scenario.residual_proba,
            residual_impact=scenario.residual_impact,
            strength_of_knowledge=scenario.strength_of_knowledge,
            justification=scenario.justification,
        )
        twin.qualifications.set(scenario.qualifications.all())
        twin.threats.set(scenario.threats.all())
        twin.assets.set(scenario.assets.all())
        twin.applied_controls.set(scenario.applied_controls.all())
        twin.existing_applied_controls.set(scenario.existing_applied_controls.all())
        twin.owner.set(scenario.owner.all())
        twin.save()
    return copy


def _copy_audit(source):
    """A cycle's frozen audit, with the living one as its baseline: results,
    answers and evidence carry over, as when an audit is created from one."""
    from core.models import ComplianceAssessment

    copy = ComplianceAssessment.objects.create(
        name=source.name,
        description=source.description,
        framework=source.framework,
        perimeter=source.perimeter,
        folder=source.folder,
        version=_next_version(source.version),
        ref_id=source.ref_id,
        selected_implementation_groups=source.selected_implementation_groups,
    )
    copy.assets.set(source.assets.all())
    copy.create_requirement_assessments(baseline=source)
    return copy


def carry_over_answers(response, asset, user) -> bool:
    """Fill a framing just started about `asset` with the answers of the last one
    applied, so reframing means changing what moved, not answering it all again.
    Only an untouched draft of the user's own is filled."""
    from core.models import Answer, QuickFormResponse
    from iam.models import RoleAssignment

    subject_question = response.subject_question()
    if (
        response.status != QuickFormResponse.Status.DRAFT
        or str(response.subject_object_id) != str(asset.pk)
        or not response.respondents.filter(user=user).exists()
        or response.answers.exclude(question=subject_question)
        .filter(Q(value__isnull=False) | Q(selected_choices__isnull=False))
        .exists()
    ):
        return False
    previous = (
        QuickFormResponse.objects.filter(
            quick_form=response.quick_form,
            subject_content_type=response.subject_content_type,
            subject_object_id=response.subject_object_id,
            status=QuickFormResponse.Status.CLOSED,
            resolution__in=[
                QuickFormResponse.Resolution.ACCEPTED,
                QuickFormResponse.Resolution.AUTO,
            ],
        )
        .exclude(pk=response.pk)
        .order_by("-updated_at")
        .first()
    )
    if previous is None or not RoleAssignment.is_object_readable(
        user, QuickFormResponse, previous.pk
    ):
        return False
    # Choices live in `selected_choices`, typed answers in `value`.
    before = {
        answer.question_id: answer
        for answer in previous.answers.exclude(question=subject_question)
        .filter(Q(value__isnull=False) | Q(selected_choices__isnull=False))
        .distinct()
        .prefetch_related("selected_choices")
    }
    answers = list(response.answers.filter(question_id__in=before))
    for answer in answers:
        answer.value = before[answer.question_id].value
        answer.selected_choices.set(before[answer.question_id].selected_choices.all())
    Answer.objects.bulk_update(answers, ["value"])
    response.recompute()
    return bool(answers)


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
    cycle = current_cycle(asset)
    frozen = bool(cycle) and is_frozen(cycle, asset)

    def deliverable(field):
        linked = cycle.linked_collection.get_items(field).first()
        return {"id": str(linked.pk), "str": str(linked)} if viewable(linked) else None

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
            "levels": _risk_levels(assessment),
        }
        if viewable(assessment)
        else None,
        "audit": {
            "id": str(audit.pk),
            "str": str(audit),
            "progress": audit.progress,
            "results": [
                {"result": result, "count": count}
                for count, result in audit.get_requirements_result_count()
                if count
            ],
        }
        if viewable(audit)
        else None,
        "accreditation": {
            **_cycle(cycle),
            "open": is_open(cycle),
            "frozen": frozen,
            # What the cycle is reviewed on, once frozen: copies of the service.
            "deliverables": {
                "risk_assessment": deliverable("risk_assessments"),
                "audit": deliverable("compliance_assessments"),
            }
            if frozen
            else None,
            "authority": str(cycle.authority or cycle.authority_name or "") or None,
            "duration_months": cycle.duration_months,
        }
        if viewable(cycle)
        else None,
        "past_cycles": [
            _cycle(past)
            for past in Accreditation.objects.filter(asset=asset)
            .exclude(pk=cycle.pk if cycle else None)
            .select_related("status", "category")
            .order_by("-created_at")
            if viewable(past)
        ],
        "can_start": (cycle is None or not is_open(cycle))
        and _last_framing(asset) is not None,
    }


def _cycle(cycle) -> dict:
    return {
        "id": str(cycle.pk),
        "str": str(cycle),
        "status": cycle.status.name if cycle.status else None,
        "category": cycle.category.name if cycle.category else None,
        "commission_date": cycle.commission_date,
        "expiry_date": cycle.expiry_date,
    }


def _risk_levels(assessment) -> dict:
    """How many scenarios sit at each current risk level, in the matrix's order."""
    levels = assessment.risk_matrix.parse_json_translated()["risk"]
    counts = [0] * len(levels)
    unrated = 0
    for level in assessment.risk_scenarios.values_list("current_level", flat=True):
        if 0 <= level < len(levels):
            counts[level] += 1
        else:
            unrated += 1
    return {
        "counts": [
            {"name": level["name"], "hexcolor": level.get("hexcolor"), "count": count}
            for level, count in zip(levels, counts)
        ],
        "unrated": unrated,
    }
