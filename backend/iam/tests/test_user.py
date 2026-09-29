import pytest
from django.contrib.auth.models import Permission

from core.tests.fixtures import *
from iam.models import Folder, Role, RoleAssignment, User


@pytest.mark.django_db
class TestUser:
    pytestmark = pytest.mark.django_db

    @pytest.mark.usefixtures("domain_perimeter_fixture")
    def test_reader_user_is_not_editor(self):
        user = User.objects.create_user(email="root@example.com", password="password")
        assert user is not None

        folder = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN).last()
        reader_role = Role.objects.create(name="test reader")
        reader_permissions = Permission.objects.filter(
            codename__in=[
                "view_perimeter",
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

    @pytest.mark.usefixtures("domain_perimeter_fixture")
    def test_editor_user_is_editor(self):
        user = User.objects.create_user(email="root@example.com", password="password")
        assert user is not None

        folder = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN).last()
        editor_role = Role.objects.create(name="test editor")
        editor_permissions = Permission.objects.filter(
            codename__in=[
                "view_perimeter",
                "view_riskassessment",
                "view_appliedcontrol",
                "view_riskscenario",
                "view_riskacceptance",
                "view_asset",
                "view_threat",
                "view_referencecontrol",
                "view_folder",
                "view_usergroup",
                "add_perimeter",
                "change_perimeter",
                "delete_perimeter",
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


@pytest.mark.django_db
class TestLicenseSeats:
    """The shipped roles, not a fabricated stand-in: `TestUser` builds its own
    permission list, so it keeps passing while a real role drifts."""

    # A seat is for editing work. These roles read, or approve — the approver's
    # `change_validationflow` is exempt precisely so approving stays free.
    SEATLESS_ROLES = ["BI-RL-AUD", "BI-RL-BSL", "BI-RL-APP"]

    @pytest.mark.usefixtures("domain_perimeter_fixture")
    @pytest.mark.parametrize("role_name", SEATLESS_ROLES)
    def test_shipped_role_does_not_consume_a_seat(self, role_name: str) -> None:
        user = User.objects.create_user(email=f"{role_name}@tests.com")
        folder = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN).last()
        assignment = RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name=role_name),
            folder=folder,
            is_recursive=True,
        )
        assignment.perimeter_folders.add(folder)

        user.refresh_from_db()
        assert not user.is_editor
        assert user not in User.get_editors()

    @pytest.mark.parametrize("role_name", SEATLESS_ROLES)
    def test_shipped_role_holds_no_billable_write_permission(
        self, role_name: str
    ) -> None:
        """Same rule read off the role itself, so a failure names the permission
        that started billing rather than only the role that broke."""
        write_prefixes = ("add_", "change_", "delete_")
        billable = {
            permission.codename
            for permission in Role.objects.get(name=role_name).permissions.all()
            if permission.codename.startswith(write_prefixes)
            and permission.codename not in User.NON_SEAT_PERMISSIONS
        }
        assert billable == set()
