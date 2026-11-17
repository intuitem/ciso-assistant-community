"""License seats enforced through the API: editor rights granted by group
membership or by a role change, and active service accounts."""

import pytest
from django.contrib.auth.models import Permission
from django.test import override_settings

from enterprise_core import license
from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import Folder, Role, RoleAssignment, User, UserGroup

SA_ENDPOINT = "/api/iam/service-accounts/"


def _fail_scan():
    raise AssertionError("editor scan should be skipped")


@pytest.mark.django_db
class TestUserGroupSeatCheck:
    """Joining a group that grants write rights takes a seat. The admin
    fixture already holds one."""

    def _join_analysts(self, admin_client, domain, user):
        analysts = UserGroup.objects.get(folder=domain, name="BI-UG-ANA")
        return admin_client.patch(
            f"/api/users/{user.id}/",
            {"user_groups": [str(analysts.id)]},
            format="json",
        )

    def test_refused_when_seats_are_used_up(self, admin_client, domain):
        user = User.objects.create_user("new@ee-tests.com")

        with override_settings(LICENSE_SEATS=1):
            response = self._join_analysts(admin_client, domain, user)

        assert response.status_code == 400
        assert "errorLicenseSeatsExceeded" in str(response.json())
        assert not user.user_groups.exists()

    def test_unlimited_license_skips_the_editor_scan(
        self, admin_client, domain, monkeypatch
    ):
        user = User.objects.create_user("new@ee-tests.com")
        monkeypatch.setattr("enterprise_core.serializers.get_editors", _fail_scan)

        with override_settings(LICENSE_SEATS=1000):
            response = self._join_analysts(admin_client, domain, user)

        assert response.status_code == 200, response.content
        assert user.user_groups.filter(folder=domain).exists()

    def test_one_editor_scan_for_all_submitted_groups(
        self, admin_client, domain, monkeypatch
    ):
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="EE other domain",
            content_type=Folder.ContentType.DOMAIN,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(other)
        analysts = UserGroup.objects.filter(
            folder__in=[domain, other], name="BI-UG-ANA"
        )
        user = User.objects.create_user("new@ee-tests.com")
        scans = []

        def counted_scan():
            scans.append(1)
            return license.get_editors()

        monkeypatch.setattr("enterprise_core.serializers.get_editors", counted_scan)

        # Two seats, for the admin and the new user: in reach, so checked.
        with override_settings(LICENSE_SEATS=2):
            response = admin_client.patch(
                f"/api/users/{user.id}/",
                {"user_groups": [str(group.id) for group in analysts]},
                format="json",
            )

        assert response.status_code == 200, response.content
        assert len(scans) == 1


@pytest.mark.django_db
class TestRoleSeatCheck:
    """Adding write permissions to a role turns its holders into editors."""

    def _readers_role(self, domain):
        role = Role.objects.create(name="custom readers")
        role.permissions.set(Permission.objects.filter(codename="view_asset"))
        group = UserGroup.objects.create(name="custom readers", folder=domain)
        group.user_set.add(User.objects.create_user("reader@ee-tests.com"))
        assignment = RoleAssignment.objects.create(
            user_group=group, role=role, folder=domain, is_recursive=True
        )
        assignment.perimeter_folders.add(domain)
        return role

    def _grant_write(self, admin_client, role):
        permission_ids = list(
            Permission.objects.filter(
                codename__in=["view_asset", "add_asset"]
            ).values_list("id", flat=True)
        )
        return admin_client.patch(
            f"/api/roles/{role.id}/", {"permissions": permission_ids}, format="json"
        )

    def test_refused_when_it_exceeds_seats(self, admin_client, domain):
        role = self._readers_role(domain)

        with override_settings(LICENSE_SEATS=1):
            response = self._grant_write(admin_client, role)

        assert response.status_code == 400
        assert "errorLicenseSeatsExceeded" in str(response.json())
        assert not role.permissions.filter(codename="add_asset").exists()

    def test_unlimited_license_skips_the_editor_scan(
        self, admin_client, domain, monkeypatch
    ):
        role = self._readers_role(domain)
        monkeypatch.setattr("enterprise_core.views.get_editors", _fail_scan)

        with override_settings(LICENSE_SEATS=1000):
            response = self._grant_write(admin_client, role)

        assert response.status_code == 200, response.content
        assert role.permissions.filter(codename="add_asset").exists()


@pytest.fixture
def service_accounts_enabled(app_config):
    flags, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    flags.value = {**(flags.value or {}), "service_accounts": True}
    flags.save()
    # Direct ORM write: bypasses the serializer, the single invalidation point.
    clear_feature_flags_cache()


def _create_sa(admin_client, domain, name):
    return admin_client.post(
        SA_ENDPOINT,
        {
            "name": name,
            "permissions": list(
                Permission.objects.filter(codename="view_folder").values_list(
                    "id", flat=True
                )
            ),
            "folders": [str(domain.id)],
        },
        format="json",
    )


@pytest.fixture
def one_seat(settings):
    settings.LICENSE_SEATS = 1


@pytest.mark.django_db
@pytest.mark.usefixtures("service_accounts_enabled", "one_seat")
class TestServiceAccountSeatQuota:
    """At most one active service account per licensed seat."""

    def test_create_blocked_at_quota(self, admin_client, domain):
        assert _create_sa(admin_client, domain, "only-bot").status_code == 201

        response = _create_sa(admin_client, domain, "one-too-many")

        assert response.status_code == 400
        assert response.json()["error"] == ["errorServiceAccountSeatsExceeded"]

    def test_deactivation_frees_the_slot_and_reactivation_is_gated(
        self, admin_client, domain
    ):
        first = _create_sa(admin_client, domain, "first-bot").json()
        # deactivating is always allowed, and frees the slot
        response = admin_client.patch(
            f"{SA_ENDPOINT}{first['id']}/", {"is_active": False}, format="json"
        )
        assert response.status_code == 200

        assert _create_sa(admin_client, domain, "second-bot").status_code == 201

        # the slot is taken again: reactivating the first is refused
        response = admin_client.patch(
            f"{SA_ENDPOINT}{first['id']}/", {"is_active": True}, format="json"
        )
        assert response.status_code == 400
        assert response.json()["error"] == ["errorServiceAccountSeatsExceeded"]

        # updates that do not activate stay allowed on the inactive account
        response = admin_client.patch(
            f"{SA_ENDPOINT}{first['id']}/",
            {"description": "still editable"},
            format="json",
        )
        assert response.status_code == 200, response.content

    def test_service_account_users_hold_no_seat(self, admin_client, domain):
        from enterprise_core.license import get_editors
        from iam.models import ServiceAccount

        payload = _create_sa(admin_client, domain, "reporter").json()

        assert ServiceAccount.objects.get(id=payload["id"]).user not in get_editors()
