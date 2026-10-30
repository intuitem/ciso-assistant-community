import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    Threat,
)
from core.risk_bridge import (
    related_requirement_assessments,
    related_scenarios_by_requirement_assessment,
    suggested_controls,
)
from iam.models import Folder, User, UserGroup
from test_fixtures import RISK_MATRIX_JSON_DEFINITION


@pytest.fixture
def bridge(db):
    folder = Folder.get_root_folder()
    exposed = Threat.objects.create(name="Exposed server", folder=folder)
    phishing = Threat.objects.create(name="Phishing", folder=folder)
    portal = Asset.objects.create(name="Portal", folder=folder)
    intranet = Asset.objects.create(name="Intranet", folder=folder)
    perimeter = Perimeter.objects.create(name="P", folder=folder)

    fw = Framework.objects.create(name="FW", folder=folder)

    def node(ref_id, threats, assessable=True):
        n = RequirementNode.objects.create(
            framework=fw,
            urn=f"urn:test:bridge:{ref_id}",
            ref_id=ref_id,
            assessable=assessable,
            folder=folder,
        )
        n.threats.set(threats)
        return n

    patch = node("PATCH", [exposed])
    mfa = node("MFA", [phishing])
    chapter = node("CHAPTER", [exposed], assessable=False)

    audit = ComplianceAssessment.objects.create(
        name="Audit portal", framework=fw, folder=folder, perimeter=perimeter
    )
    audit.assets.set([portal])
    other_audit = ComplianceAssessment.objects.create(
        name="Audit intranet", framework=fw, folder=folder
    )
    other_audit.assets.set([intranet])

    def ra(ca, requirement):
        return RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=requirement, folder=folder
        )

    ra_patch = ra(audit, patch)
    ra_mfa = ra(audit, mfa)
    ra_chapter = ra(audit, chapter)
    ra_patch_intranet = ra(other_audit, patch)

    matrix = RiskMatrix.objects.create(
        name="m", folder=folder, json_definition=RISK_MATRIX_JSON_DEFINITION
    )
    risk_assessment = RiskAssessment.objects.create(
        name="RA", folder=folder, risk_matrix=matrix, perimeter=perimeter
    )
    scenario = RiskScenario.objects.create(
        name="Portal compromise", risk_assessment=risk_assessment
    )
    scenario.threats.set([exposed])
    scenario.assets.set([portal])

    return {
        "folder": folder,
        "exposed": exposed,
        "risk_assessment": risk_assessment,
        "audit": audit,
        "scenario": scenario,
        "ra_patch": ra_patch,
        "ra_mfa": ra_mfa,
        "ra_chapter": ra_chapter,
        "ra_patch_intranet": ra_patch_intranet,
    }


@pytest.mark.django_db
class TestRelatedRequirementAssessments:
    def test_shared_threat_and_asset_only(self, bridge):
        # MFA: other threat · intranet audit: other asset · chapter: not assessable
        assert list(related_requirement_assessments(bridge["scenario"])) == [
            bridge["ra_patch"]
        ]

    def test_no_threat_means_nothing(self, bridge):
        bridge["scenario"].threats.clear()
        assert not related_requirement_assessments(bridge["scenario"]).exists()

    def test_perimeter_fallback_without_assets(self, bridge):
        bridge["scenario"].assets.clear()
        assert list(related_requirement_assessments(bridge["scenario"])) == [
            bridge["ra_patch"]
        ]

    def test_no_assets_no_perimeter_means_nothing(self, bridge):
        bridge["scenario"].assets.clear()
        bridge["risk_assessment"].perimeter = None
        bridge["risk_assessment"].save()
        bridge["scenario"].refresh_from_db()
        assert not related_requirement_assessments(bridge["scenario"]).exists()


@pytest.mark.django_db
class TestAuditScope:
    def test_requirements_outside_the_selected_groups_do_not_count(self, bridge):
        patch = bridge["ra_patch"].requirement
        patch.implementation_groups = ["advanced"]
        patch.save()
        bridge["audit"].selected_implementation_groups = ["basic"]
        bridge["audit"].save()
        assert not related_requirement_assessments(bridge["scenario"]).exists()
        assert related_scenarios_by_requirement_assessment(bridge["audit"]) == {}

    def test_requirements_in_a_selected_group_count(self, bridge):
        patch = bridge["ra_patch"].requirement
        patch.implementation_groups = ["basic", "advanced"]
        patch.save()
        bridge["audit"].selected_implementation_groups = ["basic"]
        bridge["audit"].save()
        assert list(related_requirement_assessments(bridge["scenario"])) == [
            bridge["ra_patch"]
        ]


@pytest.mark.django_db
class TestRelatedScenarios:
    def test_reverse_of_the_scenario_side(self, bridge):
        result = related_scenarios_by_requirement_assessment(bridge["audit"])
        assert result == {bridge["ra_patch"].id: [bridge["scenario"]]}

    def test_scenario_without_assets_matches_on_perimeter(self, bridge):
        bridge["scenario"].assets.clear()
        result = related_scenarios_by_requirement_assessment(bridge["audit"])
        assert result == {bridge["ra_patch"].id: [bridge["scenario"]]}

    def test_candidates_narrow_the_result(self, bridge):
        result = related_scenarios_by_requirement_assessment(
            bridge["audit"], scenarios=RiskScenario.objects.none()
        )
        assert result == {}


@pytest.mark.django_db
class TestSuggestedControls:
    def test_active_lands_existing_other_lands_planned(self, bridge):
        active = AppliedControl.objects.create(
            name="Patch policy",
            folder=bridge["folder"],
            status=AppliedControl.Status.ACTIVE,
        )
        todo = AppliedControl.objects.create(
            name="WAF", folder=bridge["folder"], status=AppliedControl.Status.TO_DO
        )
        bridge["ra_patch"].applied_controls.set([active, todo])
        suggestions = suggested_controls(
            bridge["scenario"], related_requirement_assessments(bridge["scenario"])
        )
        assert [(s["control"], s["target"]) for s in suggestions] == [
            (active, "existing"),
            (todo, "planned"),
        ]
        assert suggestions[0]["via"] == [bridge["ra_patch"]]

    def test_control_already_on_scenario_is_not_suggested(self, bridge):
        control = AppliedControl.objects.create(name="WAF", folder=bridge["folder"])
        bridge["ra_patch"].applied_controls.set([control])
        bridge["scenario"].applied_controls.add(control)
        assert (
            suggested_controls(
                bridge["scenario"],
                related_requirement_assessments(bridge["scenario"]),
            )
            == []
        )


@pytest.fixture
def admin_client(db):
    startup(sender=None)
    admin = User.objects.create_superuser("admin@risk-bridge.com")
    group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = group.folder
    admin.save()
    group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.mark.django_db
class TestBridgeApi:
    def test_related_requirements(self, admin_client, bridge):
        response = admin_client.get(
            f"/api/risk-scenarios/{bridge['scenario'].id}/related-requirements/"
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert [r["id"] for r in results] == [str(bridge["ra_patch"].id)]
        assert [t["id"] for t in results[0]["threats"]] == [str(bridge["exposed"].id)]

    def test_related_scenarios(self, admin_client, bridge):
        response = admin_client.get(
            f"/api/compliance-assessments/{bridge['audit'].id}/related-scenarios/"
        )
        assert response.status_code == 200
        assert list(response.json()) == [str(bridge["ra_patch"].id)]

    def test_confirm_adds_where_suggested(self, admin_client, bridge):
        active = AppliedControl.objects.create(
            name="Patch policy",
            folder=bridge["folder"],
            status=AppliedControl.Status.ACTIVE,
        )
        todo = AppliedControl.objects.create(name="WAF", folder=bridge["folder"])
        bridge["ra_patch"].applied_controls.set([active, todo])
        url = f"/api/risk-scenarios/{bridge['scenario'].id}/suggested-controls/"

        assert len(admin_client.get(url).json()["results"]) == 2
        response = admin_client.post(
            url,
            {"controls": [{"id": str(active.id)}, {"id": str(todo.id)}]},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["results"] == []
        assert list(bridge["scenario"].existing_applied_controls.all()) == [active]
        assert list(bridge["scenario"].applied_controls.all()) == [todo]

    def test_audit_likelihood_is_suggested_then_applied(self, admin_client, bridge):
        exposed = bridge["exposed"]
        exposed.urn = "urn:test:threat:exposed"
        exposed.save()
        framework = bridge["audit"].framework
        framework.outcomes_definition = [
            {
                "ref_id": "likelihood_exposed",
                "kind": "number",
                "expression": "3.0",
                "likelihood_of": exposed.urn,
            }
        ]
        framework.save()
        bridge["audit"].computed_values = {"likelihood_exposed": 3.0}
        bridge["audit"].save()
        url = f"/api/risk-scenarios/{bridge['scenario'].id}/suggested-likelihood/"

        listed = admin_client.get(url).json()
        assert [r["probability"] for r in listed["results"]] == [2]
        assert listed["current"] == -1

        applied = admin_client.post(
            url, {"audit": str(bridge["audit"].id)}, format="json"
        )
        assert applied.status_code == 200
        bridge["scenario"].refresh_from_db()
        assert bridge["scenario"].current_proba == 2

        refused = admin_client.post(url, {"audit": str(exposed.id)}, format="json")
        assert refused.status_code == 400

    def test_confirm_refuses_a_control_not_suggested(self, admin_client, bridge):
        stranger = AppliedControl.objects.create(name="Other", folder=bridge["folder"])
        response = admin_client.post(
            f"/api/risk-scenarios/{bridge['scenario'].id}/suggested-controls/",
            {"controls": [{"id": str(stranger.id)}]},
            format="json",
        )
        assert response.status_code == 400
        assert not bridge["scenario"].applied_controls.exists()
