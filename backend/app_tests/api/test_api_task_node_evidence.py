"""Removing an evidence from a task node follows the generic many-to-many rule:
change on the node, nothing on the evidence. Moving it to the task template links
it there: change on the template and view on the evidence."""

import uuid
from datetime import date

import pytest
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Evidence, TaskNode, TaskTemplate
from core.utils import RoleCodename
from iam.models import Folder, Role, RoleAssignment, User


def _domain(label):
    return Folder.objects.create(
        name=f"task-{label}-{uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.mark.django_db
class TestRemoveEvidence:
    def setup_method(self):
        mine, hidden = _domain("mine"), _domain("hidden")
        self.template = TaskTemplate.objects.create(
            name="Task", folder=mine, task_date=date.today()
        )
        self.node = TaskNode.objects.filter(
            task_template=self.template
        ).first() or TaskNode.objects.create(
            task_template=self.template, folder=mine, due_date=date.today()
        )
        self.visible = Evidence.objects.create(name="Visible", folder=mine)
        self.hidden = Evidence.objects.create(name="Hidden", folder=hidden)
        self.node.evidences.add(self.visible, self.hidden)
        user = User.objects.create_user(f"task-{uuid.uuid4().hex[:6]}@test.com")
        RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name=RoleCodename.ANALYST.value),
            folder=Folder.get_root_folder(),
            is_recursive=True,
        ).perimeter_folders.add(mine)
        self.client = APIClient()
        _, token = AuthToken.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    def _remove(self, evidence_id, move=False):
        return self.client.post(
            f"/api/task-nodes/{self.node.id}/remove_evidence/",
            {"evidence_id": str(evidence_id), "move": move},
            format="json",
        )

    def test_hidden_evidence_can_be_removed(self):
        r = self._remove(self.hidden.id)
        assert r.status_code == status.HTTP_200_OK, r.content
        assert list(self.node.evidences.all()) == [self.visible]

    def test_visible_evidence_can_be_moved_to_the_template(self):
        r = self._remove(self.visible.id, move=True)
        assert r.status_code == status.HTTP_200_OK, r.content
        assert list(self.node.evidences.all()) == [self.hidden]
        assert list(self.template.evidences.all()) == [self.visible]

    def test_hidden_evidence_cannot_be_moved_to_the_template(self):
        r = self._remove(self.hidden.id, move=True)
        assert r.status_code == status.HTTP_403_FORBIDDEN, r.content
        assert self.node.evidences.filter(id=self.hidden.id).exists()
        assert not self.template.evidences.exists()

    def test_unlinked_evidence_is_not_found(self):
        r = self._remove(uuid.uuid4())
        assert r.status_code == status.HTTP_404_NOT_FOUND, r.content

    def test_move_sent_as_the_text_false_only_removes(self):
        r = self.client.post(
            f"/api/task-nodes/{self.node.id}/remove_evidence/",
            {"evidence_id": str(self.visible.id), "move": "false"},
        )
        assert r.status_code == status.HTTP_200_OK, r.content
        assert list(self.node.evidences.all()) == [self.hidden]
        assert not self.template.evidences.exists()

    def test_move_must_be_a_boolean(self):
        r = self._remove(self.visible.id, move="maybe")
        assert r.status_code == status.HTTP_400_BAD_REQUEST, r.content
        assert "move" in r.json()
        assert self.node.evidences.count() == 2

    def test_move_without_a_template_is_refused(self):
        TaskNode.objects.filter(id=self.node.id).update(task_template=None)
        r = self._remove(self.visible.id, move=True)
        assert r.status_code == status.HTTP_400_BAD_REQUEST, r.content
        assert "move" in r.json()
        assert self.node.evidences.count() == 2
