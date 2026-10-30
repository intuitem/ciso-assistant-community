"""`asset.risk_assessment` and `asset.audit`, driven by the MonServiceSécurisé
framing form: accepting writes the asset's risk scenarios and audit scope, and
accepting again updates the same objects."""

import pytest
from django.contrib.contenttypes.models import ContentType

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


def test_accepting_opens_a_homologation_cycle_and_renews_it_once_decided(setup):
    apply_on_accept(accepted(setup, "risque_r4", "besoins_niveau2"), setup["admin"])
    cycle = Accreditation.objects.get(asset=setup["asset"])
    assert cycle.status.name == "draft"
    assert cycle.category.name == "accreditation_elaborated"
    assert list(cycle.linked_collection.get_items("risk_assessments")) == [
        RiskAssessment.objects.get(folder=setup["domain"])
    ]
    assert list(cycle.linked_collection.get_items("compliance_assessments")) == [
        ComplianceAssessment.objects.get(folder=setup["domain"])
    ]

    # Still open: the same cycle follows the description.
    apply_on_accept(accepted(setup, "risque_r4", "besoins_niveau3"), setup["admin"])
    cycle.refresh_from_db()
    assert Accreditation.objects.filter(asset=setup["asset"]).count() == 1
    assert cycle.category.name == "accreditation_advanced"

    # Decided: the next acceptance starts the next cycle.
    cycle.status = Terminology.objects.get(
        field_path=Terminology.FieldPath.ACCREDITATION_STATUS, name="accredited"
    )
    cycle.save()
    apply_on_accept(accepted(setup, "risque_r4", "besoins_niveau3"), setup["admin"])
    assert Accreditation.objects.filter(asset=setup["asset"]).count() == 2


def test_audit_waits_for_the_security_needs(setup):
    rows = applied(plan(accepted(setup, "risque_r4"), setup["admin"]))
    assert rows["asset.audit"]["proposal"].reason == "implementationGroupsUndetermined"
    assert rows["asset.risk_assessment"]["proposal"].ok
