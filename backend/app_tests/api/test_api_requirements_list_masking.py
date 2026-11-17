"""Actions that answer with read data mask the linked objects the caller cannot
view, as the list and detail endpoints do: `requirements_list` on an audit and on
a requirement assignment, the inspection of a requirement across audits, and the
update of a responsibility matrix activity. `requirements_list` also gives
`linked_ids`, every linked id, for editors."""

import json
import uuid
from types import SimpleNamespace

import pytest
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Evidence,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementAssignment,
    RequirementNode,
)
from core.utils import RoleCodename
from iam.models import Folder, Role, RoleAssignment, User
from pmbok.models import ResponsibilityMatrix, ResponsibilityMatrixActivity

LINKS = (("evidences", Evidence), ("applied_controls", AppliedControl))


def _domain(label):
    return Folder.objects.create(
        name=f"mask-{label}-{uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def _analyst(folder):
    """A user who is analyst on `folder` only, and a client for them."""
    user = User.objects.create_user(f"mask-{uuid.uuid4().hex[:6]}@test.com")
    RoleAssignment.objects.create(
        user=user,
        role=Role.objects.get(name=RoleCodename.ANALYST.value),
        folder=Folder.get_root_folder(),
        is_recursive=True,
    ).perimeter_folders.add(folder)
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return user, client


@pytest.fixture
def audit(db):
    """A requirement assessment in a domain the analyst works in, linked to one
    evidence and one applied control there, and to one of each in a domain the
    analyst cannot see."""
    mine, hidden = _domain("mine"), _domain("hidden")
    root = Folder.get_root_folder()
    tag = uuid.uuid4().hex[:6]
    framework = Framework.objects.create(
        name="fw", folder=root, urn=f"urn:test:risk:framework:mask-{tag}"
    )
    node = RequirementNode.objects.create(
        framework=framework,
        urn=f"urn:test:risk:req_node:mask-{tag}:1",
        ref_id="1",
        assessable=True,
        folder=root,
    )
    compliance_assessment = ComplianceAssessment.objects.create(
        name="audit",
        framework=framework,
        folder=mine,
        perimeter=Perimeter.objects.create(name="p", folder=mine),
    )
    requirement_assessment = RequirementAssessment.objects.create(
        compliance_assessment=compliance_assessment, requirement=node, folder=mine
    )
    links = {}
    for field, model in LINKS:
        visible = model.objects.create(name=f"visible {field}", folder=mine)
        concealed = model.objects.create(name=f"concealed {field}", folder=hidden)
        getattr(requirement_assessment, field).set([visible, concealed])
        links[field] = (visible, concealed)
    user, client = _analyst(mine)
    return SimpleNamespace(
        mine=mine,
        hidden=hidden,
        node=node,
        compliance_assessment=compliance_assessment,
        requirement_assessment=requirement_assessment,
        links=links,
        user=user,
        client=client,
    )


def _assignment(audit, actor):
    assignment = RequirementAssignment.objects.create(
        compliance_assessment=audit.compliance_assessment,
        folder=audit.mine,
        status="in_progress",
    )
    assignment.actor.set([actor])
    assignment.requirement_assessments.set([audit.requirement_assessment])
    return assignment


def _entry(response):
    assert response.status_code == status.HTTP_200_OK, response.content
    (entry,) = response.json()["requirement_assessments"]
    return entry


def _assert_hidden_links_masked(entry, links, fields):
    for field in fields:
        visible, concealed = links[field]
        assert {} in entry[field]
        assert [item["id"] for item in entry[field] if item] == [str(visible.id)]
        assert concealed.name not in json.dumps(entry)


def _assert_masked(entry, links, fields):
    _assert_hidden_links_masked(entry, links, fields)
    for field in fields:
        visible, concealed = links[field]
        assert sorted(entry["linked_ids"][field]) == sorted(
            [str(visible.id), str(concealed.id)]
        )


@pytest.mark.django_db
class TestRequirementsListMasking:
    def test_audit_requirements_list_masks_hidden_links(self, audit):
        response = audit.client.get(
            f"/api/compliance-assessments/{audit.compliance_assessment.id}/requirements_list/"
        )
        assert response.json()["viewer_role"] == "auditor"
        _assert_masked(_entry(response), audit.links, [field for field, _ in LINKS])

    def test_assignment_requirements_list_masks_hidden_links(self, audit):
        someone_else = User.objects.create_user("mask-other@test.com")
        assignment = _assignment(audit, someone_else.actor)
        response = audit.client.get(
            f"/api/requirement-assignments/{assignment.id}/requirements_list/"
        )
        assert response.json()["viewer_role"] == "auditor"
        _assert_masked(_entry(response), audit.links, [field for field, _ in LINKS])

    def test_respondent_gets_ids_only_for_the_fields_it_reads(self, audit):
        assignment = _assignment(audit, audit.user.actor)
        response = audit.client.get(
            f"/api/requirement-assignments/{assignment.id}/requirements_list/"
        )
        assert response.json()["viewer_role"] == "respondent"
        entry = _entry(response)
        assert "evidences" in entry
        assert set(entry["linked_ids"]) <= set(entry)
        _assert_masked(
            entry, audit.links, [field for field, _ in LINKS if field in entry]
        )

    def test_full_viewer_gets_every_link(self, audit, authenticated_client):
        entry = _entry(
            authenticated_client.get(
                f"/api/compliance-assessments/{audit.compliance_assessment.id}/requirements_list/"
            )
        )
        for field, (visible, concealed) in audit.links.items():
            assert sorted(item["id"] for item in entry[field]) == sorted(
                [str(visible.id), str(concealed.id)]
            )
            assert sorted(entry["linked_ids"][field]) == sorted(
                [str(visible.id), str(concealed.id)]
            )

    def test_linked_ids_sent_back_keep_the_hidden_link(self, audit):
        entry = _entry(
            audit.client.get(
                f"/api/compliance-assessments/{audit.compliance_assessment.id}/requirements_list/"
            )
        )
        extra = Evidence.objects.create(name="added", folder=audit.mine)
        response = audit.client.patch(
            f"/api/requirement-assessments/{audit.requirement_assessment.id}/",
            {"evidences": [*entry["linked_ids"]["evidences"], str(extra.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.content
        visible, concealed = audit.links["evidences"]
        assert set(audit.requirement_assessment.evidences.all()) == {
            visible,
            concealed,
            extra,
        }


@pytest.mark.django_db
def test_requirement_inspection_masks_hidden_links(audit):
    response = audit.client.get(
        f"/api/requirement-nodes/{audit.node.id}/inspect_requirement/"
    )
    _assert_hidden_links_masked(
        _entry(response), audit.links, [field for field, _ in LINKS]
    )


@pytest.mark.django_db
def test_matrix_activity_update_masks_hidden_links(audit):
    matrix = ResponsibilityMatrix.objects.create(
        name="matrix", folder=audit.mine, preset="raci"
    )
    activity = ResponsibilityMatrixActivity.objects.create(
        matrix=matrix, name="activity", order=0, folder=audit.mine
    )
    visible = Asset.objects.create(name="visible asset", folder=audit.mine)
    concealed = Asset.objects.create(name="concealed asset", folder=audit.hidden)
    activity.assets.set([visible, concealed])

    response = audit.client.patch(
        f"/api/pmbok/responsibility-matrix-activities/{activity.id}/",
        {"name": "renamed"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.content
    assets = response.json()["assets"]
    assert {} in assets
    assert [item["id"] for item in assets if item] == [str(visible.id)]
    assert concealed.name not in response.content.decode()
    assert set(activity.assets.all()) == {visible, concealed}
