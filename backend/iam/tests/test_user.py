import pytest
from django.contrib.auth.models import Permission

from core.tests.fixtures import *
from iam.models import Folder, Role, RoleAssignment, User


@pytest.mark.django_db
class TestUser:
    pytestmark = pytest.mark.django_db

    @pytest.mark.usefixtures("domain_project_fixture")
    def test_reader_user_is_not_editor(self):
        user = User.objects.create_user(email="root@example.com", password="password")
        assert user is not None

        folder = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN).last()
        reader_role = Role.objects.create(name="test reader")
        reader_permissions = Permission.objects.filter(
            codename__in=[
                "view_project",
                "view_riskassessment",
                "view_appliedcontrol",
                "view_riskscenario",
                "view_riskacceptance",
                "view_asset",
                "view_threat",
                "view_referencecontrol",
                "view_folder",
                "view_usergroup",
            ]
        )
        reader_role.permissions.set(reader_permissions)
        reader_role.save()
        reader_role_assignment = RoleAssignment.objects.create(
            user=user,
            role=reader_role,
            folder=folder,
            is_recursive=True,
        )
        reader_role_assignment.perimeter_folders.add(folder)
        reader_role_assignment.save()

        assert not user.is_editor

        editors = User.get_editors()
        assert len(editors) == 0
        assert user not in editors

    @pytest.mark.usefixtures("domain_project_fixture")
    def test_editor_user_is_editor(self):
        user = User.objects.create_user(email="root@example.com", password="password")
        assert user is not None

        folder = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN).last()
        editor_role = Role.objects.create(name="test editor")
        editor_permissions = Permission.objects.filter(
            codename__in=[
                "view_project",
                "view_riskassessment",
                "view_appliedcontrol",
                "view_riskscenario",
                "view_riskacceptance",
                "view_asset",
                "view_threat",
                "view_referencecontrol",
                "view_folder",
                "view_usergroup",
                "add_project",
                "change_project",
                "delete_project",
                "add_riskassessment",
                "change_riskassessment",
                "delete_riskassessment",
                "add_appliedcontrol",
                "change_appliedcontrol",
                "delete_appliedcontrol",
                "add_riskscenario",
                "change_riskscenario",
                "delete_riskscenario",
                "add_riskacceptance",
                "change_riskacceptance",
                "delete_riskacceptance",
                "add_asset",
                "change_asset",
                "delete_asset",
                "add_threat",
                "change_threat",
                "delete_threat",
                "add_referencecontrol",
                "change_referencecontrol",
                "delete_referencecontrol",
                "add_folder",
                "change_folder",
                "delete_folder",
                "add_usergroup",
                "change_usergroup",
                "delete_usergroup",
            ]
        )
        editor_role.permissions.set(editor_permissions)
        editor_role.save()
        editor_role_assignment = RoleAssignment.objects.create(
            user=user,
            role=editor_role,
            folder=folder,
            is_recursive=True,
        )
        editor_role_assignment.perimeter_folders.add(folder)
        editor_role_assignment.save()

        assert user.is_editor

        editors = User.get_editors()
        assert len(editors) == 1
        assert user in editors
