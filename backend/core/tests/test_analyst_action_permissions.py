"""Detail POST actions that analysts are meant to use.

As a POST on an existing object, a detail `@action` demands `add_<model>` unless
the viewset maps it in `permission_overrides` (core/permissions.py). These
actions read or edit the object, so they must follow the right that matches.
"""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    AppliedControl,
    Evidence,
    QuickForm,
    ReferenceControl,
    TaskNode,
    TaskTemplate,
)
from core.tests.test_quick_forms import FORM_URN, LIBRARY_V1, _load
from iam.models import Folder, Role, RoleAssignment, User, UserGroup


@pytest.fixture
def app_config():
    startup(sender=None, **{})


def _role_client(email, role_code):
    """A user holding one built-in role on the whole tree."""
    root = Folder.get_root_folder()
    user = User.objects.create_user(email=email, is_published=True)
    user.folder = root
    user.save()
    group = UserGroup.objects.create(name=f"grp-{email}", folder=root)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=role_code),
        folder=root,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(root)
    token = AuthToken.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return user, client


@pytest.mark.django_db
def test_analyst_can_preview_quick_form(app_config):
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    _, client = _role_client("ana-preview@test.local", "BI-RL-ANA")

    res = client.post(
        f"/api/quick-forms/{form.id}/preview/", {"answers": {}}, format="json"
    )
    assert res.status_code == 200, res.content[:300]


@pytest.mark.django_db
def test_analyst_can_sync_reference_control(app_config):
    root = Folder.get_root_folder()
    reference_control = ReferenceControl.objects.create(
        name="rc", folder=root, category="technical", csf_function="protect"
    )
    applied_control = AppliedControl.objects.create(
        name="ac",
        folder=root,
        reference_control=reference_control,
        category="process",
        csf_function="identify",
    )
    _, client = _role_client("ana-sync@test.local", "BI-RL-ANA")

    res = client.post(
        f"/api/reference-controls/{reference_control.id}/sync-applied-controls/"
    )
    assert res.status_code == 200, res.content[:300]
    applied_control.refresh_from_db()
    assert applied_control.category == "technical"
    assert applied_control.csf_function == "protect"


def _task_node_with_evidence():
    root = Folder.get_root_folder()
    template = TaskTemplate.objects.create(name="tt", folder=root)
    node = TaskNode.objects.create(task_template=template, folder=root)
    evidence = Evidence.objects.create(name="ev", folder=root)
    node.evidences.add(evidence)
    return template, node, evidence


@pytest.mark.django_db
@pytest.mark.parametrize("move", [False, True])
def test_analyst_can_remove_task_node_evidence(app_config, move):
    template, node, evidence = _task_node_with_evidence()
    _, client = _role_client(f"ana-task-{move}@test.local", "BI-RL-ANA")

    res = client.post(
        f"/api/task-nodes/{node.id}/remove_evidence/",
        {"evidence_id": str(evidence.id), "move": move},
        format="json",
    )
    assert res.status_code == 200, res.content[:300]
    assert not node.evidences.filter(id=evidence.id).exists()
    assert template.evidences.filter(id=evidence.id).exists() is move


@pytest.mark.django_db
def test_reader_cannot_remove_task_node_evidence(app_config):
    _, node, evidence = _task_node_with_evidence()
    _, client = _role_client("reader-task@test.local", "BI-RL-AUD")

    res = client.post(
        f"/api/task-nodes/{node.id}/remove_evidence/",
        {"evidence_id": str(evidence.id)},
        format="json",
    )
    assert res.status_code == 403, res.content[:300]
    assert node.evidences.filter(id=evidence.id).exists()
