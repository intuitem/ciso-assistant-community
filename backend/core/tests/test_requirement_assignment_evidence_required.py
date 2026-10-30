"""API tests for the evidence gate on assignment submission."""

from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from knox.models import AuthToken

from core.apps import startup
from core.models import (
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementAssignment,
    RequirementNode,
)
from iam.models import Folder, User, UserGroup


@pytest.fixture
def app_config():
    startup(sender=None, **{})


def _admin_client(email):
    user = User.objects.create_user(email=email)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = admin_group.folder
    user.save()
    admin_group.user_set.add(user)
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {_auth_token[1]}")
    return user, client


@pytest.fixture
def evidence_fixture(app_config):
    root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    folder = Folder.objects.create(parent_folder=root_folder, name="evidence gate")
    perimeter = Perimeter.objects.create(name="evidence gate", folder=folder)
    framework = Framework.objects.create(
        name="evidence gate",
        folder=folder,
        implementation_groups_definition=[
            {"ref_id": "in", "name": "In"},
            {"ref_id": "out", "name": "Out"},
        ],
    )

    def node(key, **kwargs):
        kwargs.setdefault("implementation_groups", ["in"])
        return RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:test:risk:req_node:evidence-gate:{key}",
            ref_id=key.upper(),
            assessable=True,
            folder=folder,
            **kwargs,
        )

    nodes = {
        "flagged": node("flagged", evidence_required=True),
        "plain": node("plain"),
        "hidden": node("hidden", evidence_required=True, visibility_expression="false"),
        "out_of_ig": node(
            "out_of_ig", evidence_required=True, implementation_groups=["out"]
        ),
    }
    compliance_assessment = ComplianceAssessment.objects.create(
        name="evidence gate",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
        selected_implementation_groups=["in"],
    )
    ras = {
        key: RequirementAssessment.objects.create(
            compliance_assessment=compliance_assessment,
            requirement=requirement,
            folder=folder,
        )
        for key, requirement in nodes.items()
    }

    actor_user, actor_client = _admin_client("evidence_gate_actor@tests.com")
    assignment = RequirementAssignment.objects.create(
        compliance_assessment=compliance_assessment,
        folder=folder,
        status="in_progress",
    )
    assignment.actor.set([actor_user.actor])
    assignment.requirement_assessments.set(ras.values())

    return {
        "folder": folder,
        "assignment": assignment,
        "ras": ras,
        "client": actor_client,
    }


def _submit(client, assignment):
    return client.post(
        f"/api/requirement-assignments/{assignment.id}/set_status/",
        data={"status": "submitted"},
    )


def _attach(ra, folder, revision=None):
    evidence = Evidence.objects.create(name=f"evidence {uuid4()}", folder=folder)
    if revision is not None:
        EvidenceRevision.objects.create(evidence=evidence, folder=folder, **revision)
    ra.evidences.add(evidence)
    return evidence


@pytest.mark.django_db
class TestEvidenceGate:
    @pytest.mark.parametrize("start_status", ["in_progress", "changes_requested"])
    def test_flagged_requirement_without_evidence_blocks(
        self, evidence_fixture, start_status
    ):
        assignment = evidence_fixture["assignment"]
        assignment.status = start_status
        assignment.save(update_fields=["status"])

        response = _submit(evidence_fixture["client"], assignment)

        assert response.status_code == 400
        assert response.data["error"] == "evidenceRequired"
        # Only the visible, in-scope flagged requirement is named.
        assert [item["id"] for item in response.data["missing_evidence"]] == [
            str(evidence_fixture["ras"]["flagged"].id)
        ]
        assignment.refresh_from_db()
        assert assignment.status == start_status

    def test_revision_without_file_or_link_does_not_count(self, evidence_fixture):
        ra = evidence_fixture["ras"]["flagged"]
        _attach(ra, evidence_fixture["folder"], {"observation": "see attached"})
        _attach(ra, evidence_fixture["folder"])

        response = _submit(evidence_fixture["client"], evidence_fixture["assignment"])

        assert response.status_code == 400
        assert response.data["missing_evidence"][0]["id"] == str(ra.id)

    def test_only_the_newest_revision_counts(self, evidence_fixture):
        ra = evidence_fixture["ras"]["flagged"]
        folder = evidence_fixture["folder"]
        evidence = _attach(ra, folder, {"link": "https://example.com/old"})
        EvidenceRevision.objects.create(
            evidence=evidence, folder=folder, version=2, observation="replaced"
        )

        response = _submit(evidence_fixture["client"], evidence_fixture["assignment"])

        assert response.status_code == 400
        assert response.data["missing_evidence"][0]["id"] == str(ra.id)

    @pytest.mark.parametrize(
        "make_revision",
        [
            lambda: {"link": "https://example.com/policy"},
            lambda: {"attachment": SimpleUploadedFile("policy.txt", b"policy")},
        ],
        ids=["link", "attachment"],
    )
    def test_file_or_link_satisfies_the_requirement(
        self, evidence_fixture, make_revision
    ):
        assignment = evidence_fixture["assignment"]
        _attach(
            evidence_fixture["ras"]["flagged"],
            evidence_fixture["folder"],
            make_revision(),
        )

        response = _submit(evidence_fixture["client"], assignment)

        assert response.status_code == 200
        assignment.refresh_from_db()
        assert assignment.status == "submitted"

    def test_no_flagged_requirement_does_not_block(self, evidence_fixture):
        assignment = evidence_fixture["assignment"]
        assignment.requirement_assessments.set([evidence_fixture["ras"]["plain"]])

        response = _submit(evidence_fixture["client"], assignment)

        assert response.status_code == 200


@pytest.mark.django_db
class TestRequirementsListEvidence:
    def test_has_usable_evidence_matches_the_gate(self, evidence_fixture):
        ras = evidence_fixture["ras"]
        _attach(ras["plain"], evidence_fixture["folder"], {"observation": "empty"})
        _attach(
            ras["flagged"],
            evidence_fixture["folder"],
            {"link": "https://example.com/policy"},
        )

        response = evidence_fixture["client"].get(
            f"/api/requirement-assignments/{evidence_fixture['assignment'].id}/requirements_list/"
        )

        assert response.status_code == 200
        by_id = {
            str(item["id"]): item for item in response.data["requirement_assessments"]
        }
        assert by_id[str(ras["flagged"].id)]["has_usable_evidence"] is True
        assert by_id[str(ras["plain"].id)]["has_usable_evidence"] is False
        assert str(ras["hidden"].id) not in by_id
        assert str(ras["out_of_ig"].id) not in by_id
