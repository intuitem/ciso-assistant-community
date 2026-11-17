"""Audit logging of IAM access-control models, with builtin rows excluded."""

import pytest
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from iam.models import Folder, Role, RoleAssignment, UserGroup


@pytest.fixture
def root_folder(db):
    return Folder.get_root_folder()


def _count(model, obj):
    ct = ContentType.objects.get_for_model(model)
    return LogEntry.objects.filter(content_type=ct, object_pk=str(obj.pk)).count()


@pytest.mark.django_db
class TestRbacAuditLog:
    def test_non_builtin_role_assignment_is_logged(self, root_folder):
        role = Role.objects.filter(builtin=True).first()
        ra = RoleAssignment.objects.create(role=role, folder=root_folder)
        assert _count(RoleAssignment, ra) >= 1

    def test_builtin_role_assignment_is_not_logged(self, root_folder):
        role = Role.objects.filter(builtin=True).first()
        ra = RoleAssignment.objects.create(role=role, folder=root_folder, builtin=True)
        assert _count(RoleAssignment, ra) == 0

    def test_builtin_user_group_is_not_logged(self, root_folder):
        ug = UserGroup.objects.create(name="B", folder=root_folder, builtin=True)
        assert _count(UserGroup, ug) == 0

    def test_non_builtin_user_group_is_logged(self, root_folder):
        ug = UserGroup.objects.create(name="C", folder=root_folder)
        assert _count(UserGroup, ug) >= 1
