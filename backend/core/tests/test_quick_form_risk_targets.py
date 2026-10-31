"""`asset.risk_assessment` and `asset.audit`, driven by the MonServiceSécurisé
framing form: accepting writes the asset's risk scenarios and audit scope, and
accepting again updates the same objects."""

import pytest
from django.contrib.contenttypes.models import ContentType

from core import risk_bridge
from core.apps import startup
from core.models import (
    Asset,
    ComplianceAssessment,
    QuickForm,
    QuickFormResponse,
    RiskAssessment,
    StoredLibrary,
    Terminology,
)
from core.quick_form_apply import apply_on_accept, plan
from core.quick_form_risk_targets import (
    freeze_accreditation,
    journey_of,
    living_service,
    start_accreditation,
)
from iam.models import Folder, User, UserGroup
from pmbok.models import Accreditation

FORM_URN = "urn:intuitem:risk:quick_form:anssi-mss-v2-framing"
LIBRARY_URN = "urn:intuitem:risk:library:quick-form-anssi-mss-v2-framing"
NOT_PASSED_ON = ("expression", "ref_id", "implementation_groups")


@pytest.fixture
def setup(db):
    startup(sender=None)
    assert StoredLibrary.objects.get(urn=LIBRARY_URN).load() is None
    form = QuickForm.objects.get(urn=FORM_URN)
    domain = Folder.objects.create(
        name="mss-domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    asset = Asset.objects.create(name="Portail", folder=domain, type="PR")
    admin = User.objects.create_user(email="mss-targets@test.local", is_published=True)
    group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = group.folder
    admin.save()
    group.user_set.add(admin)
    return {"form": form, "domain": domain, "asset": asset, "admin": admin}


def accepted(setup, *rules, values=None) -> QuickFormResponse:
    """A response on the asset whose listed rules fired, as the engine stores them."""
    definitions = {r["ref_id"]: r for r in setup["form"].outcomes_definition}
    return QuickFormResponse.objects.create(
        name="cadrage",
        quick_form=setup["form"],
        folder=setup["domain"],
        status=QuickFormResponse.Status.SUBMITTED,
        subject_content_type=ContentType.objects.get_for_model(Asset),
        subject_object_id=setup["asset"].pk,
        computed_values=values or {},
        computed_outcome={
            ref: {k: v for k, v in definitions[ref].items() if k not in NOT_PASSED_ON}
            for ref in rules
        },
    )


def applied(rows) -> dict:
    return {row["target"]: row for row in rows}


def test_accepting_writes_scenarios_and_audit_scope(setup):
    response = accepted(setup, "risque_r4", "risque_r5", "besoins_niveau2")
    rows = applied(apply_on_accept(response, setup["admin"]))
    assert rows["asset.risk_assessment"]["applied"], rows
    assert rows["asset.audit"]["applied"], rows

    assessment = RiskAssessment.objects.get(folder=setup["domain"])
    assert assessment.risk_matrix.urn.endswith(":matrix:risk-matrix-4x4-ebios-rm")
    scenarios = {s.ref_id: s for s in assessment.risk_scenarios.all()}
    assert set(scenarios) == {"R4", "R5"}
    assert [t.ref_id for t in scenarios["R4"].threats.all()] == ["MSS-V4"]
    assert list(scenarios["R4"].assets.all()) == [setup["asset"]]

    audit = ComplianceAssessment.objects.get(folder=setup["domain"])
    assert audit.framework.urn.endswith(":framework:anssi-mss-v2")
    assert audit.selected_implementation_groups == ["M-I", "M-R"]
    assert list(audit.assets.all()) == [setup["asset"]]
    assert audit.requirement_assessments.count() > 0


def test_accepting_again_updates_the_same_objects(setup):
    apply_on_accept(accepted(setup, "risque_r4", "besoins_niveau2"), setup["admin"])
    scenario = RiskAssessment.objects.get(folder=setup["domain"]).risk_scenarios.get()
    scenario.name = "Renamed by the risk owner"
    scenario.save()

    apply_on_accept(
        accepted(setup, "risque_r4", "risque_r12", "besoins_niveau3"), setup["admin"]
    )
    assessment = RiskAssessment.objects.get(folder=setup["domain"])
    assert set(assessment.risk_scenarios.values_list("ref_id", flat=True)) == {
        "R4",
        "R12",
    }
    # What people edited stays.
    assert (
        assessment.risk_scenarios.get(ref_id="R4").name == "Renamed by the risk owner"
    )
    audit = ComplianceAssessment.objects.get(folder=setup["domain"])
    assert audit.selected_implementation_groups == ["A-I", "A-R"]


def test_severity_becomes_the_impact_until_someone_changes_it(setup):
    apply_on_accept(
        accepted(setup, "risque_r4", "risque_r5", values={"gravite_r4": 3.0}),
        setup["admin"],
    )
    scenarios = RiskAssessment.objects.get(folder=setup["domain"]).risk_scenarios
    r4 = scenarios.get(ref_id="R4")
    assert r4.current_impact == 2  # level 3 is the matrix's third impact
    assert scenarios.get(ref_id="R5").current_impact == -1  # no severity given

    apply_on_accept(
        accepted(setup, "risque_r4", values={"gravite_r4": 4.0}), setup["admin"]
    )
    r4.refresh_from_db()
    assert r4.current_impact == 3  # untouched since the last write: follows

    r4.current_impact = 1
    r4.save()
    apply_on_accept(
        accepted(setup, "risque_r4", values={"gravite_r4": 2.0}), setup["admin"]
    )
    r4.refresh_from_db()
    assert r4.current_impact == 1  # changed by a person: kept


def framed(setup, *rules, values=None) -> QuickFormResponse:
    """A framing accepted and applied, as the asset page then finds it."""
    response = accepted(setup, *rules, values=values)
    apply_on_accept(response, setup["admin"])
    QuickFormResponse.objects.filter(pk=response.pk).update(
        status=QuickFormResponse.Status.CLOSED,
        resolution=QuickFormResponse.Resolution.ACCEPTED,
    )
    return response


def decide(cycle, name="accredited"):
    cycle.status = Terminology.objects.get(
        field_path=Terminology.FieldPath.ACCREDITATION_STATUS, name=name
    )
    cycle.save()


def test_framing_describes_the_service_and_never_opens_a_cycle(setup):
    rows = applied(
        plan(accepted(setup, "risque_r4", "besoins_niveau2"), setup["admin"])
    )
    assert rows["asset.accreditation"]["proposal"].reason == "noAccreditationInProgress"
    framed(setup, "risque_r4", "besoins_niveau2")
    framed(setup, "risque_r4", "besoins_niveau3")
    assert not Accreditation.objects.filter(asset=setup["asset"]).exists()
    assert RiskAssessment.objects.filter(folder=setup["domain"]).count() == 1


def test_homologation_runs_on_frozen_deliverables(setup):
    asset, admin = setup["asset"], setup["admin"]
    assert start_accreditation(asset, admin) == (None, "notFramedYet")
    framed(setup, "risque_r4", "besoins_niveau2")
    living_assessment, living_audit = living_service(asset)

    cycle, error = start_accreditation(asset, admin)
    assert error is None and cycle.status.name == "draft"
    assert cycle.category.name == "accreditation_elaborated"
    assert start_accreditation(asset, admin) == (None, "accreditationInProgress")

    # Before freezing, reframing fixes the cycle's service and category.
    framed(setup, "risque_r4", "besoins_niveau3")
    cycle.refresh_from_db()
    assert cycle.category.name == "accreditation_advanced"
    assert list(cycle.linked_collection.get_items("risk_assessments")) == [
        living_assessment
    ]

    living_assessment.risk_scenarios.update(current_proba=1)
    measure = living_audit.requirement_assessments.filter(
        requirement__assessable=True
    ).first()
    measure.result = "compliant"
    measure.save()
    assert freeze_accreditation(asset, admin) == (cycle, None)
    assert freeze_accreditation(asset, admin) == (
        None,
        "accreditationDeliverablesFrozen",
    )
    (assessment,) = cycle.linked_collection.get_items("risk_assessments")
    (audit,) = cycle.linked_collection.get_items("compliance_assessments")
    assert assessment != living_assessment and audit != living_audit
    assert assessment.version == "2.0" and audit.version == "2.0"
    assert list(assessment.risk_scenarios.values_list("current_proba", flat=True)) == [
        1
    ]
    assert (
        audit.requirement_assessments.get(requirement=measure.requirement).result
        == "compliant"
    )
    # Each scenario reads its own audit: the living one or the frozen copy.
    for risk_assessment, own_audit in (
        (living_assessment, living_audit),
        (assessment, audit),
    ):
        scenario = risk_assessment.risk_scenarios.get()
        related = risk_bridge.related_requirement_assessments(scenario)
        assert related.exists()
        assert set(related.values_list("compliance_assessment", flat=True)) == {
            own_audit.pk
        }
        by_ra = risk_bridge.related_scenarios_by_requirement_assessment(own_audit)
        assert {s.pk for ss in by_ra.values() for s in ss} == {scenario.pk}

    # Frozen: reframing moves the service on, not the cycle.
    rows = applied(plan(accepted(setup, "risque_r4", "besoins_niveau2"), admin))
    assert (
        rows["asset.accreditation"]["proposal"].reason
        == "accreditationDeliverablesFrozen"
    )
    framed(setup, "risque_r4", "besoins_niveau2")
    cycle.refresh_from_db()
    assert cycle.category.name == "accreditation_advanced"
    assert living_service(asset) == (living_assessment, living_audit)

    journey = journey_of(asset, admin)
    assert journey["accreditation"]["frozen"] is True
    assert journey["accreditation"]["deliverables"]["risk_assessment"]["id"] == str(
        assessment.pk
    )
    assert journey["can_start"] is False

    # Decided: the next cycle starts again from the living service.
    decide(cycle)
    assert journey_of(asset, admin)["can_start"] is True
    renewed, error = start_accreditation(asset, admin)
    assert error is None and renewed != cycle
    assert renewed.category.name == "accreditation_elaborated"
    assert list(renewed.linked_collection.get_items("risk_assessments")) == [
        living_assessment
    ]
    journey = journey_of(asset, admin)
    assert [past["id"] for past in journey["past_cycles"]] == [str(cycle.pk)]
    assert journey["accreditation"]["frozen"] is False
    levels = journey["risk_assessment"]["levels"]
    assert levels["unrated"] + sum(level["count"] for level in levels["counts"]) == 1
    assert sum(r["count"] for r in journey["audit"]["results"]) > 0


def test_audit_waits_for_the_security_needs(setup):
    rows = applied(plan(accepted(setup, "risque_r4"), setup["admin"]))
    assert rows["asset.audit"]["proposal"].reason == "implementationGroupsUndetermined"
    assert rows["asset.risk_assessment"]["proposal"].ok


def test_reframing_starts_from_the_last_applied_answers(setup):
    from core.models import Answer
    from core.quick_form_risk_targets import carry_over_answers
    from core.views import start_quick_form_response

    def start():
        response, _ = start_quick_form_response(
            setup["admin"],
            subject_id=setup["asset"].pk,
            quick_form=setup["form"],
            folder=setup["domain"],
        )
        return response

    first = start()
    subject_question = first.subject_question()
    answer = first.answers.exclude(question=subject_question).first()
    answer.value = ["kept"]
    answer.save()
    picked = (
        first.answers.exclude(question=subject_question)
        .filter(question__choices__isnull=False)
        .exclude(pk=answer.pk)
        .first()
    )
    choice = picked.question.choices.first()
    picked.selected_choices.set([choice])
    QuickFormResponse.objects.filter(pk=first.pk).update(
        status=QuickFormResponse.Status.CLOSED,
        resolution=QuickFormResponse.Resolution.ACCEPTED,
    )

    second = start()
    assert second != first
    assert carry_over_answers(second, setup["asset"], setup["admin"])
    assert Answer.objects.get(response=second, question=answer.question).value == [
        "kept"
    ]
    assert list(
        Answer.objects.get(
            response=second, question=picked.question
        ).selected_choices.all()
    ) == [choice]
    assert Answer.objects.get(response=second, question=subject_question).value == [
        str(setup["asset"].pk)
    ]
    # Touched since: left alone.
    assert not carry_over_answers(second, setup["asset"], setup["admin"])
