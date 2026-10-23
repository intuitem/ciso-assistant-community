"""Editor counting and the license fields of the instance status."""

from datetime import datetime, timezone
from io import StringIO

import pytest
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import override_settings
from prometheus_client import REGISTRY

from enterprise_core import instance_status
from enterprise_core.license import (
    check_restored_seats,
    get_editors,
    is_editor,
    seat_limit_reachable,
)
from iam.models import Role, RoleAssignment, User

READ = ["view_folder", "view_asset", "view_appliedcontrol"]
WRITE = READ + ["add_asset", "change_asset", "delete_asset"]


def _user_with(email, folder, codenames, **extra):
    user = User.objects.create_user(email=email, password="password", **extra)
    role = Role.objects.create(name=f"role of {email}")
    role.permissions.set(Permission.objects.filter(codename__in=codenames))
    assignment = RoleAssignment.objects.create(
        user=user, role=role, folder=folder, is_recursive=True
    )
    assignment.perimeter_folders.add(folder)
    return user


@pytest.mark.django_db
class TestEditors:
    def test_reader_is_not_editor(self, domain):
        user = _user_with("reader@ee-tests.com", domain, READ)

        assert not is_editor(user)
        assert user not in get_editors()

    def test_writer_is_editor(self, domain):
        user = _user_with("writer@ee-tests.com", domain, WRITE)

        assert is_editor(user)
        assert get_editors() == [user]

    def test_non_seat_permissions_do_not_make_an_editor(self, domain):
        user = _user_with(
            "notified@ee-tests.com",
            domain,
            READ + ["change_notification", "delete_notification"],
        )

        assert not is_editor(user)

    def test_third_parties_hold_no_seat(self, domain):
        _user_with("vendor@ee-tests.com", domain, WRITE, is_third_party=True)

        assert get_editors() == []


@pytest.mark.django_db
class TestSeatLimit:
    def test_seat_limit_reachable_counts_seat_eligible_users(self):
        """Seat checks are skipped below this bound, so it must count every
        user get_editors() could return, and only those."""
        User.objects.create_user(email="a@ee-tests.com", password="password")
        User.objects.create_user(email="b@ee-tests.com", password="password")
        User.objects.create_user(
            email="tp@ee-tests.com", password="password", is_third_party=True
        )

        assert seat_limit_reachable(1)
        assert seat_limit_reachable(2)
        assert not seat_limit_reachable(3)

    def test_restored_backup_may_not_exceed_seats(self, domain):
        _user_with("w1@ee-tests.com", domain, WRITE)
        _user_with("w2@ee-tests.com", domain, WRITE)

        with override_settings(LICENSE_SEATS=1):
            assert check_restored_seats() == "errorLicenseSeatsExceeded"
        with override_settings(LICENSE_SEATS=2):
            assert check_restored_seats() is None

    def test_restore_check_skips_the_scan_below_reach(self, domain, monkeypatch):
        _user_with("w1@ee-tests.com", domain, WRITE)

        def scan():
            raise AssertionError("editor scan should be skipped")

        monkeypatch.setattr("enterprise_core.license.get_editors", scan)
        with override_settings(LICENSE_SEATS=1000):
            assert check_restored_seats() is None


@pytest.mark.django_db
class TestInstanceStatus:
    def test_status_line_ends_with_license_fields(self, domain):
        _user_with("writer@ee-tests.com", domain, WRITE)
        out = StringIO()

        with override_settings(LICENSE_SEATS=5, LICENSE_EXPIRATION="2027-08-29"):
            call_command("status", stdout=out)

        line = out.getvalue().strip()
        assert line.endswith(" seats=5 editors=1 expiration=2027-08-29")

    def test_metrics_publish_license_gauges(self, domain):
        _user_with("writer@ee-tests.com", domain, WRITE)

        with override_settings(LICENSE_SEATS=5, LICENSE_EXPIRATION="2027-08-29"):
            instance_status.update_metrics()

        expected_ts = datetime(2027, 8, 29, tzinfo=timezone.utc).timestamp()
        assert REGISTRY.get_sample_value("ciso_assistant_nb_seats") == 5
        assert REGISTRY.get_sample_value("ciso_assistant_nb_editors") == 1
        assert (
            REGISTRY.get_sample_value("ciso_assistant_license_expiration")
            == expected_ts
        )

    def test_unset_expiration_is_published_as_minus_one(self):
        with override_settings(LICENSE_EXPIRATION="unset"):
            instance_status.update_metrics()

        assert REGISTRY.get_sample_value("ciso_assistant_license_expiration") == -1
