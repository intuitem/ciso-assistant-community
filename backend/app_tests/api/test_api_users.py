from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.apps import apps as django_apps
from django.contrib.auth.models import Permission
from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient
from core.serializers import UserReadSerializer, UserWriteSerializer
from core.startup import ensure_user_creator_group
from core.models import Actor
from core.views import UserFilter, UserViewSet
from iam.models import Folder, IdPGroup, Role, RoleAssignment, User, UserGroup


from test_vars import USERS_ENDPOINT as API_ENDPOINT
from test_utils import EndpointTestsQueries
from test_vars import GROUPS_PERMISSIONS

# Generic user data for tests
USER_FIRSTNAME = "John"
USER_NAME = "James"
USER_EMAIL = "john.james@tests.com"
USER_PASSWORD = "secretpassword123"


@pytest.mark.django_db
class TestUsersUnauthenticated:
    """Perform tests on Users API endpoint without authentication"""

    client = APIClient()

    def test_get_users(self):
        """test to get users from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Users",
            User,
            {
                "email": USER_EMAIL,
                "password": USER_PASSWORD,
                "first_name": USER_FIRSTNAME,
                "last_name": USER_NAME,
            },
        )

    def test_create_users(self):
        """test to create users with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Users",
            User,
            {"email": USER_EMAIL, "first_name": USER_FIRSTNAME, "last_name": USER_NAME},
        )

    def test_update_users(self):
        """test to update users with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Users",
            User,
            {"email": USER_EMAIL, "first_name": USER_FIRSTNAME, "last_name": USER_NAME},
            {
                "email": "new" + USER_EMAIL,
                "first_name": "new" + USER_FIRSTNAME,
                "last_name": "new" + USER_NAME,
            },
        )

    def test_delete_users(self):
        """test to delete users with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Users",
            User,
            {"email": USER_EMAIL, "first_name": USER_FIRSTNAME, "last_name": USER_NAME},
        )


@pytest.mark.django_db
class TestUsersAuthenticated:
    """Perform tests on Users API endpoint with authentication"""

    def test_get_users(self, test):
        """test to get users from the API with authentication"""

        # Users with Global folder access can see all users (admin + test user)
        # Users with domain folder access can only see themselves
        expected_count = 2

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Users",
            User,
            {"email": USER_EMAIL, "first_name": USER_FIRSTNAME, "last_name": USER_NAME},
            base_count=expected_count,
            item_search_field="email",
            user_group=test.user_group,
            scope="Global",
        )

    def test_create_users(self, test):
        """test to create users with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Users",
            User,
            {"email": USER_EMAIL, "first_name": USER_FIRSTNAME, "last_name": USER_NAME},
            base_count=2,
            item_search_field="email",
            user_group=test.user_group,
            scope="Global",
        )

    def test_update_users(self, test):
        """test to update users with the API with authentication"""

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Users",
            User,
            {"email": USER_EMAIL, "first_name": USER_FIRSTNAME, "last_name": USER_NAME},
            {
                "email": "new" + USER_EMAIL,
                "first_name": "new" + USER_FIRSTNAME,
                "last_name": "new" + USER_NAME,
            },
            user_group=test.user_group,
            scope="Global",
            #  scope=GROUPS_PERMISSIONS[test.user_group]["folder"],
        )

    def test_delete_users(self, test):
        """test to delete users with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Users",
            User,
            {"email": USER_EMAIL, "first_name": USER_FIRSTNAME, "last_name": USER_NAME},
            user_group=test.user_group,
            scope="Global",
        )

    def test_uniqueness_emails(self, test):
        """test to create users with the API with authentication and already existing email"""

        url = reverse(API_ENDPOINT)
        data = {
            "email": USER_EMAIL,
            "first_name": USER_FIRSTNAME,
            "last_name": USER_NAME,
        }

        # Uses the API endpoint to create a user
        response = test.admin_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        # Uses the API endpoint to create another user with the same email
        response = test.admin_client.post(url, data, format="json")

        # Asserts that the user was not created
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            "users can be created with an already used email"
        )
        assert response.json() == {"email": ["user with this email already exists."]}, (
            "users can be created with an already used email"
        )

    def test_invalid_emails(self, test):
        """test to create users with the API with authentication and invalid emails"""

        url = reverse(API_ENDPOINT)
        emails = [
            "test",
            "test@",
            "@test",
            "@test.",
            "test@test",
            "test@test.",
            "test@test.c",
        ]

        for email in emails:
            data = {
                "email": email,
                "first_name": USER_FIRSTNAME,
                "last_name": USER_NAME,
            }

            # Uses the API endpoint to create a user
            response = test.admin_client.post(url, data, format="json")

            # Asserts that the user was not created
            assert response.status_code == status.HTTP_400_BAD_REQUEST, (
                f"users can be created with an invalid email ({email})"
            )
            assert response.json() == {"email": ["Enter a valid email address."]}, (
                f"users can be created with an invalid email ({email})"
            )

    def test_update_only_if_admin(self, test):
        is_admin = test.user_group == "BI-UG-ADM"

        user, created = User.objects.get_or_create(
            email=USER_EMAIL,
            defaults={
                "first_name": USER_FIRSTNAME,
                "last_name": USER_NAME,
                "password": USER_PASSWORD,
                "is_active": True,
            },
        )

        detail_url = reverse("users-detail", args=[user.id])

        # Attempt to update another user (requires admin privileges)
        response = test.client.patch(
            detail_url, {"first_name": "Updated"}, format="json"
        )

        # Non-admin users may get 404 if they don't have IAM visibility to this user
        if is_admin:
            assert response.status_code == status.HTTP_200_OK
            user.refresh_from_db()
            assert user.first_name == "Updated"
        else:
            # Non-admin users either can't see the user (404) or don't have permission (403)
            assert response.status_code in (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,  # User not visible due to IAM filtering
            )

    def test_superuser_cannot_be_deactivated(self, test):
        superuser, _ = User.objects.get_or_create(
            email="admin.tests@example.com",
            defaults={
                "first_name": "Admin",
                "last_name": "User",
                "password": USER_PASSWORD,
                "is_superuser": True,
                "is_active": True,
            },
        )

        url = reverse("users-detail", args=[superuser.id])
        response = test.client.patch(url, {"is_active": False}, format="json")

        superuser.refresh_from_db()

        assert superuser.is_active is True


@pytest.mark.django_db
class TestUsersAutocomplete:
    """The lightweight autocomplete endpoint powers user pickers at scale."""

    def test_autocomplete_returns_display_string(self, authenticated_client):
        User.objects.create_user(
            "alice@tests.com", first_name="Alice", last_name="Smith"
        )

        url = reverse("users-autocomplete")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        rows = (
            response.data["results"]
            if isinstance(response.data, dict)
            else response.data
        )
        alice = next(r for r in rows if r["email"] == "alice@tests.com")
        assert alice["str"] == "Alice Smith"
        assert "id" in alice

    def test_autocomplete_search_filters(self, authenticated_client):
        User.objects.create_user("needle@tests.com")
        User.objects.create_user("haystack@tests.com")

        url = reverse("users-autocomplete")
        response = authenticated_client.get(url, {"search": "needle"})

        assert response.status_code == status.HTTP_200_OK
        rows = (
            response.data["results"]
            if isinstance(response.data, dict)
            else response.data
        )
        emails = [r["email"] for r in rows]
        assert "needle@tests.com" in emails
        assert "haystack@tests.com" not in emails

    def test_autocomplete_id_filter_hydrates_selection(self, authenticated_client):
        target = User.objects.create_user("target@tests.com")
        User.objects.create_user("other@tests.com")

        url = reverse("users-autocomplete")
        response = authenticated_client.get(url, {"id": str(target.id)})

        assert response.status_code == status.HTTP_200_OK
        rows = (
            response.data["results"]
            if isinstance(response.data, dict)
            else response.data
        )
        assert [r["email"] for r in rows] == ["target@tests.com"]

    def test_autocomplete_returns_active_flag(self, authenticated_client):
        User.objects.create_user("inactive@tests.com", is_active=False)

        url = reverse("users-autocomplete")
        response = authenticated_client.get(url, {"search": "inactive"})

        rows = (
            response.data["results"]
            if isinstance(response.data, dict)
            else response.data
        )
        assert rows[0]["is_active"] is False

    def test_autocomplete_column_icontains(self, authenticated_client):
        User.objects.create_user("picker@tests.com", first_name="Wolfgang")
        User.objects.create_user("other@tests.com", first_name="Bela")

        url = reverse("users-autocomplete")
        response = authenticated_client.get(url, {"first_name__icontains": "olfg"})

        rows = (
            response.data["results"]
            if isinstance(response.data, dict)
            else response.data
        )
        emails = [r["email"] for r in rows]
        assert "picker@tests.com" in emails
        assert "other@tests.com" not in emails

    def test_autocomplete_exclude_user_groups(self, authenticated_client):
        """Add-only pickers drop users already in the group."""
        folder = Folder.get_root_folder()
        group = UserGroup.objects.create(name="picker-grp", folder=folder)
        member = User.objects.create_user("member@tests.com")
        User.objects.create_user("outsider@tests.com")
        group.user_set.add(member)

        url = reverse("users-autocomplete")
        response = authenticated_client.get(url, {"exclude_user_groups": str(group.id)})

        rows = (
            response.data["results"]
            if isinstance(response.data, dict)
            else response.data
        )
        emails = [r["email"] for r in rows]
        assert "member@tests.com" not in emails
        assert "outsider@tests.com" in emails

    def test_autocomplete_ordering(self, authenticated_client):
        User.objects.create_user("zzz@tests.com", first_name="Zed")
        User.objects.create_user("aaa@tests.com", first_name="Ann")

        url = reverse("users-autocomplete")
        asc = authenticated_client.get(url, {"ordering": "email"})
        desc = authenticated_client.get(url, {"ordering": "-email"})

        def emails(resp):
            rows = resp.data["results"] if isinstance(resp.data, dict) else resp.data
            return [r["email"] for r in rows]

        assert emails(asc) == sorted(emails(asc))
        assert emails(desc) == sorted(emails(desc), reverse=True)


def _client_for(user: User) -> APIClient:
    client = APIClient()
    token = AuthToken.objects.create(user=user)[1]
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _make_user_manager(email: str, permissions: list[str]) -> User:
    """Create a user holding a custom role with the given permissions on the
    root folder (recursive) — the 'user manager without group assignment
    rights' persona of the escalation scenarios."""
    root = Folder.get_root_folder()
    role = Role.objects.create(name=f"custom role for {email}", folder=root)
    role.permissions.set(Permission.objects.filter(codename__in=permissions))
    group = UserGroup.objects.create(name=f"custom group for {email}", folder=root)
    ra = RoleAssignment.objects.create(
        user_group=group, role=role, is_recursive=True, folder=root
    )
    ra.perimeter_folders.add(root)
    user = User.objects.create_user(email, is_published=True)
    group.user_set.add(user)
    return user


def _make_scim_user(email: str) -> User:
    user = User.objects.create_user(email, is_published=True)
    # create_user() does not pass the flag through; set it the way the SCIM
    # provisioner does (iam/scim/views.py).
    user.is_scim_managed = True
    user.save(update_fields=["is_scim_managed"])
    return user


@pytest.fixture
def escalation_env(app_config, authenticated_client):
    """A user manager (add/change/delete/view user + view_usergroup, but no
    change_usergroup), a plain grouped user, and the builtin admin group.
    `authenticated_client` guarantees a global admin exists so the last-admin
    viewset guard never interferes with the serializer guards under test."""
    manager = _make_user_manager(
        "user.manager@tests.com",
        ["add_user", "change_user", "delete_user", "view_user", "view_usergroup"],
    )
    return SimpleNamespace(
        manager=manager,
        manager_client=_client_for(manager),
        admin_client=authenticated_client,
        admin_group=UserGroup.objects.get(name="BI-UG-ADM"),
        reader_group=UserGroup.objects.get(name="BI-UG-GAD"),
    )


@pytest.mark.django_db
class TestUserPrivilegeEscalationGuards:
    """A custom role holding user-management permissions must not be able to
    escalate to admin via is_superuser, user_groups, or an email re-binding."""

    def test_user_manager_cannot_set_superuser_on_update(self, escalation_env):
        target = User.objects.create_user("victim@tests.com", is_published=True)

        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"is_superuser": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "cannotChangeSuperuserStatus" in response.json()["is_superuser"]
        target.refresh_from_db()
        assert target.is_superuser is False

    def test_user_manager_cannot_set_superuser_on_self(self, escalation_env):
        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[escalation_env.manager.id]),
            {"is_superuser": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        escalation_env.manager.refresh_from_db()
        assert escalation_env.manager.is_superuser is False

    def test_user_manager_cannot_create_superuser(self, escalation_env):
        response = escalation_env.manager_client.post(
            reverse("users-list"),
            {"email": "new.superuser@tests.com", "is_superuser": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not User.objects.filter(email="new.superuser@tests.com").exists()

    def test_admin_cannot_set_superuser_either(self, escalation_env):
        """The flag is deployment-owned (env var/createsuperuser), not an API
        concept: even a global admin cannot flip it."""
        target = User.objects.create_user("victim2@tests.com", is_published=True)

        response = escalation_env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"is_superuser": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target.refresh_from_db()
        assert target.is_superuser is False

    def test_echoing_current_superuser_value_passes(self, escalation_env):
        """A full PUT that echoes back the value it read is not a change."""
        target = User.objects.create_user("victim3@tests.com", is_published=True)

        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"first_name": "Updated", "is_superuser": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.first_name == "Updated"

    def test_user_manager_cannot_join_admin_group(self, escalation_env):
        env = escalation_env
        current_group_ids = [
            str(pk) for pk in env.manager.user_groups.values_list("id", flat=True)
        ]

        response = env.manager_client.patch(
            reverse("users-detail", args=[env.manager.id]),
            {"user_groups": current_group_ids + [str(env.admin_group.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "missingPermissionToManageUserGroupMembership"
            in response.json()["user_groups"]
        )
        env.manager.refresh_from_db()
        assert not env.manager.user_groups.filter(pk=env.admin_group.pk).exists()

    def test_user_manager_cannot_add_others_to_admin_group(self, escalation_env):
        env = escalation_env
        target = User.objects.create_user("accomplice@tests.com", is_published=True)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"user_groups": [str(env.admin_group.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target.refresh_from_db()
        assert not target.user_groups.exists()

    def test_user_manager_cannot_grant_groups_on_create(self, escalation_env):
        env = escalation_env

        response = env.manager_client.post(
            reverse("users-list"),
            {
                "email": "preloaded@tests.com",
                "user_groups": [str(env.admin_group.id)],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not User.objects.filter(email="preloaded@tests.com").exists()

    def test_user_manager_cannot_strip_admin_group(self, escalation_env):
        env = escalation_env
        target = User.objects.create_user("other.admin@tests.com", is_published=True)
        env.admin_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"user_groups": []},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target.refresh_from_db()
        assert target.user_groups.filter(pk=env.admin_group.pk).exists()

    def test_user_manager_edit_with_echoed_groups_passes(self, escalation_env):
        """The guard applies to the membership delta only: a full PUT echoing
        unchanged memberships must not block a plain profile edit."""
        env = escalation_env
        target = User.objects.create_user("grouped@tests.com", is_published=True)
        env.admin_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"first_name": "Renamed", "user_groups": [str(env.admin_group.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.first_name == "Renamed"
        assert target.user_groups.filter(pk=env.admin_group.pk).exists()

    def test_invisible_memberships_are_preserved_not_stripped(
        self, app_config, authenticated_client
    ):
        """A manager without view_usergroup cannot see the target's groups, so
        a full PUT from them omits the memberships; the omission must preserve
        them, not silently remove them."""
        blind_manager = _make_user_manager(
            "blind.manager@tests.com",
            ["add_user", "change_user", "delete_user", "view_user"],
        )
        admin_group = UserGroup.objects.get(name="BI-UG-ADM")
        target = User.objects.create_user("hidden.admin@tests.com", is_published=True)
        admin_group.user_set.add(target)

        response = _client_for(blind_manager).patch(
            reverse("users-detail", args=[target.id]),
            {"first_name": "Renamed", "user_groups": []},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.first_name == "Renamed"
        assert target.user_groups.filter(pk=admin_group.pk).exists()

    def test_admin_can_manage_group_membership(self, escalation_env):
        env = escalation_env
        target = User.objects.create_user("promoted@tests.com", is_published=True)

        response = env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"user_groups": [str(env.reader_group.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.user_groups.filter(pk=env.reader_group.pk).exists()

    def test_user_manager_can_change_email_of_groupless_user(self, escalation_env):
        target = User.objects.create_user("plain@tests.com", is_published=True)

        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"email": "renamed@tests.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.email == "renamed@tests.com"

    def test_user_manager_cannot_change_email_of_grouped_user(self, escalation_env):
        """An SSO login maps to its account by email: rewriting the email of a
        user holding group-granted roles is an identity re-binding."""
        env = escalation_env
        target = User.objects.create_user("reader@tests.com", is_published=True)
        env.reader_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"email": "hijacked@tests.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "emailChangeRequiresUserGroupManagementRights" in response.json()["email"]
        )
        target.refresh_from_db()
        assert target.email == "reader@tests.com"

    def test_admin_can_change_email_of_grouped_user(self, escalation_env):
        env = escalation_env
        target = User.objects.create_user("reader2@tests.com", is_published=True)
        env.reader_group.user_set.add(target)

        response = env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"email": "renamed.reader@tests.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.email == "renamed.reader@tests.com"

    def test_user_manager_cannot_change_email_of_idp_bound_user(self, escalation_env):
        target = User.objects.create_user(
            "jit.user@tests.com", is_published=True, is_jit_provisioned=True
        )

        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"email": "rebound@tests.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "emailChangeOfIdpManagedUserRequiresAdmin" in response.json()["email"]
        target.refresh_from_db()
        assert target.email == "jit.user@tests.com"

    def test_admin_can_change_email_of_idp_bound_user(self, escalation_env):
        target = User.objects.create_user(
            "jit.user2@tests.com", is_published=True, is_jit_provisioned=True
        )

        response = escalation_env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"email": "fixed.jit@tests.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.email == "fixed.jit@tests.com"

    def test_email_echo_passes_for_user_manager(self, escalation_env):
        """PUT-style payloads echo the unchanged email; that is not a change."""
        env = escalation_env
        target = User.objects.create_user("reader3@tests.com", is_published=True)
        env.reader_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"email": "Reader3@tests.com", "first_name": "Echoed"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.first_name == "Echoed"

    def test_email_of_invisibly_grouped_user_is_still_protected(
        self, app_config, authenticated_client
    ):
        """Memberships the requester cannot see must still make the target's
        email privileged — the guard reads the DB, not the visibility-filtered
        prefetch."""
        blind_manager = _make_user_manager(
            "blind.manager2@tests.com",
            ["add_user", "change_user", "delete_user", "view_user"],
        )
        target = User.objects.create_user("hidden.reader@tests.com", is_published=True)
        UserGroup.objects.get(name="BI-UG-GAD").user_set.add(target)

        response = _client_for(blind_manager).patch(
            reverse("users-detail", args=[target.id]),
            {"email": "hijacked2@tests.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target.refresh_from_db()
        assert target.email == "hidden.reader@tests.com"

    def test_admin_cannot_change_email_of_scim_account(self, escalation_env):
        """SCIM is the authoritative write channel: identity fields of a
        SCIM-managed account are immutable via the API even for admins."""
        target = _make_scim_user("scim.user@tests.com")

        response = escalation_env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"email": "drifted@tests.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "fieldManagedByScim" in response.json()["email"]
        target.refresh_from_db()
        assert target.email == "scim.user@tests.com"

    def test_user_manager_cannot_change_email_of_scim_account(self, escalation_env):
        target = _make_scim_user("scim.user2@tests.com")

        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"email": "rebound.scim@tests.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "fieldManagedByScim" in response.json()["email"]
        target.refresh_from_db()
        assert target.email == "scim.user2@tests.com"

    def test_admin_cannot_change_name_of_scim_account(self, escalation_env):
        target = _make_scim_user("scim.user3@tests.com")

        response = escalation_env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"first_name": "Renamed"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "fieldManagedByScim" in response.json()["first_name"]
        target.refresh_from_db()
        assert target.first_name == ""

    def test_scim_identity_echo_passes(self, escalation_env):
        """Echoing the unchanged identity fields back (full PUT style) is not a
        change; local-only fields stay editable on SCIM accounts."""
        target = _make_scim_user("scim.user4@tests.com")

        response = escalation_env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {
                "email": "Scim.User4@tests.com",
                "first_name": "",
                "last_name": "",
                "observation": "local note",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.observation == "local note"
        # a case-variant echo may rewrite the stored casing; identity is iexact
        assert target.email.lower() == "scim.user4@tests.com"

    def test_admin_can_toggle_scim_account_active_status(self, escalation_env):
        """Break-glass: emergency deactivation must not wait on IdP sync."""
        target = _make_scim_user("scim.user5@tests.com")

        response = escalation_env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.is_active is False

    def test_user_manager_cannot_toggle_scim_account_active_status(
        self, escalation_env
    ):
        target = _make_scim_user("scim.user6@tests.com")

        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "scimAccountFieldRequiresAdmin" in response.json()["is_active"]
        target.refresh_from_db()
        assert target.is_active is True

    def test_user_manager_cannot_enable_local_login_on_scim_account(
        self, escalation_env
    ):
        target = _make_scim_user("scim.user9@tests.com")

        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"keep_local_login": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "scimAccountCannotEnableLocalLogin" in response.json()["keep_local_login"]
        )
        target.refresh_from_db()
        assert target.keep_local_login is False

    def test_admin_cannot_enable_local_login_on_scim_account(self, escalation_env):
        """A SCIM identity stays SSO-only — no password fallback, admin or not.
        The decommission escape is deleting the account, not a local backdoor."""
        target = _make_scim_user("scim.user10@tests.com")

        response = escalation_env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"keep_local_login": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "scimAccountCannotEnableLocalLogin" in response.json()["keep_local_login"]
        )
        target.refresh_from_db()
        assert target.keep_local_login is False

    def test_admin_can_disable_legacy_local_login_on_scim_account(self, escalation_env):
        """Reducing the auth surface of a legacy flagged account stays possible
        (admin-only via the SCIM lifecycle rule)."""
        target = _make_scim_user("scim.user11@tests.com")
        target.keep_local_login = True
        target.save(update_fields=["keep_local_login"])

        response = escalation_env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"keep_local_login": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.keep_local_login is False

    def test_user_manager_cannot_deactivate_admin_account(self, escalation_env):
        """Deactivating an admin is a lifecycle operation on the admin group's
        power: deactivating every admin would lock the deployment out."""
        env = escalation_env
        target = User.objects.create_user("second.admin@tests.com", is_published=True)
        env.admin_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "adminAccountLifecycleChangeRequiresAdminRights"
            in response.json()["is_active"]
        )
        target.refresh_from_db()
        assert target.is_active is True

    def test_user_manager_can_deactivate_non_admin_grouped_user(self, escalation_env):
        """Deactivation of non-admin accounts is routine offboarding, open to
        user managers: it is a recoverable denial of service, unlike the email
        re-binding, which is a takeover and stays gated on all groups."""
        env = escalation_env
        target = User.objects.create_user("grouped.active@tests.com", is_published=True)
        env.reader_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.is_active is False

    def test_user_manager_cannot_expire_admin_account(self, escalation_env):
        """expiry_date is deferred deactivation (the nightly task applies it):
        it must not bypass the is_active guard on admin accounts."""
        env = escalation_env
        target = User.objects.create_user("expiring.admin@tests.com", is_published=True)
        env.admin_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"expiry_date": "2020-01-01"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "adminAccountLifecycleChangeRequiresAdminRights"
            in response.json()["expiry_date"]
        )
        target.refresh_from_db()
        assert target.expiry_date is None

    def test_user_manager_can_expire_non_admin_user(self, escalation_env):
        env = escalation_env
        target = User.objects.create_user("expiring.user@tests.com", is_published=True)
        env.reader_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"expiry_date": "2030-01-01"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert str(target.expiry_date) == "2030-01-01"

    def test_user_manager_cannot_expire_scim_account(self, escalation_env):
        target = _make_scim_user("scim.expiry@tests.com")

        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"expiry_date": "2020-01-01"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "scimAccountFieldRequiresAdmin" in response.json()["expiry_date"]
        target.refresh_from_db()
        assert target.expiry_date is None

    def test_user_manager_can_deactivate_groupless_user(self, escalation_env):
        target = User.objects.create_user(
            "groupless.active@tests.com", is_published=True
        )

        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.is_active is False

    def test_admin_can_deactivate_grouped_user(self, escalation_env):
        env = escalation_env
        target = User.objects.create_user(
            "grouped.active2@tests.com", is_published=True
        )
        env.reader_group.user_set.add(target)

        response = env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.is_active is False

    def test_user_manager_cannot_flip_local_login_on_admin_account(
        self, escalation_env
    ):
        env = escalation_env
        target = User.objects.create_user("login.admin@tests.com", is_published=True)
        env.admin_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"keep_local_login": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "adminAccountLifecycleChangeRequiresAdminRights"
            in response.json()["keep_local_login"]
        )
        target.refresh_from_db()
        assert target.keep_local_login is False

    def test_user_manager_can_flip_local_login_on_non_admin_grouped_user(
        self, escalation_env
    ):
        env = escalation_env
        target = User.objects.create_user("grouped.login@tests.com", is_published=True)
        env.reader_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"keep_local_login": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.keep_local_login is True

    def test_user_manager_can_flip_local_login_on_groupless_user(self, escalation_env):
        target = User.objects.create_user(
            "groupless.login@tests.com", is_published=True
        )

        response = escalation_env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"keep_local_login": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.keep_local_login is True

    def test_lifecycle_echo_passes_for_user_manager(self, escalation_env):
        """Echoing unchanged is_active/keep_local_login (full PUT style) is not
        a lifecycle change, even on an admin account."""
        env = escalation_env
        target = User.objects.create_user("grouped.echo@tests.com", is_published=True)
        env.admin_group.user_set.add(target)

        response = env.manager_client.patch(
            reverse("users-detail", args=[target.id]),
            {"is_active": True, "keep_local_login": False, "first_name": "Echoed"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.first_name == "Echoed"

    def test_user_manager_cannot_delete_scim_account(self, escalation_env):
        target = _make_scim_user("scim.user7@tests.com")

        response = escalation_env.manager_client.delete(
            reverse("users-detail", args=[target.id])
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error"] == "onlyAdminCanDeleteScimAccount"
        assert User.objects.filter(id=target.id).exists()

    def test_admin_can_delete_scim_account(self, escalation_env):
        """The admin-only escape hatch for a decommissioned SCIM integration."""
        target = _make_scim_user("scim.user8@tests.com")

        response = escalation_env.admin_client.delete(
            reverse("users-detail", args=[target.id])
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(id=target.id).exists()

    def test_user_manager_cannot_delete_admin_account(self, escalation_env):
        """Deletion must not be the bigger hammer that bypasses the
        deactivation guard on admin accounts."""
        env = escalation_env
        target = User.objects.create_user(
            "deletable.admin@tests.com", is_published=True
        )
        env.admin_group.user_set.add(target)

        response = env.manager_client.delete(reverse("users-detail", args=[target.id]))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error"] == "deletingAdminAccountRequiresAdminRights"
        assert User.objects.filter(id=target.id).exists()

    def test_user_manager_can_delete_non_admin_grouped_user(self, escalation_env):
        """Consistent with deactivation: non-admin accounts are routine
        offboarding territory for user managers."""
        env = escalation_env
        target = User.objects.create_user("deletable.user@tests.com", is_published=True)
        env.reader_group.user_set.add(target)

        response = env.manager_client.delete(reverse("users-detail", args=[target.id]))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(id=target.id).exists()

    def test_admin_can_delete_a_non_last_admin(self, escalation_env):
        env = escalation_env
        target = User.objects.create_user(
            "deletable.admin2@tests.com", is_published=True
        )
        env.admin_group.user_set.add(target)

        response = env.admin_client.delete(reverse("users-detail", args=[target.id]))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(id=target.id).exists()

    def test_only_active_admin_cannot_be_deactivated_even_by_admin(
        self, escalation_env
    ):
        """Self-lockout guard: mirrors the last-admin delete/group guards."""
        only_admin = User.objects.get(email="admin@tests.com")

        response = escalation_env.admin_client.patch(
            reverse("users-detail", args=[only_admin.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "attemptToDeactivateOnlyAdminAccountError" in response.json()["is_active"]
        )
        only_admin.refresh_from_db()
        assert only_admin.is_active is True

    def test_only_active_admin_cannot_be_given_an_expiry(self, escalation_env):
        only_admin = User.objects.get(email="admin@tests.com")

        response = escalation_env.admin_client.patch(
            reverse("users-detail", args=[only_admin.id]),
            {"expiry_date": "2030-01-01"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "attemptToDeactivateOnlyAdminAccountError" in response.json()["expiry_date"]
        )
        only_admin.refresh_from_db()
        assert only_admin.expiry_date is None

    def test_admin_can_deactivate_a_non_last_admin(self, escalation_env):
        env = escalation_env
        target = User.objects.create_user("spare.admin@tests.com", is_published=True)
        env.admin_group.user_set.add(target)

        response = env.admin_client.patch(
            reverse("users-detail", args=[target.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.is_active is False


@pytest.mark.django_db
class TestBlindUserManagerGuards:
    """The same guards, exercised by a user manager who cannot *see* the admin
    group. Every persona above holds view_usergroup at the root, so the
    admin-account guards were only ever tested against a requester for whom
    BI-UG-ADM is visible.

    That distinction is load-bearing: UserViewSet.get_queryset prefetches
    user_groups filtered to the requester's viewable groups, and Django keeps
    that filtered queryset in the prefetch cache, so
    `instance.user_groups.filter(...)` clones it and inherits the filter rather
    than hitting the DB clean. Every guard that asked the relation "is this
    target an administrator?" therefore answered *no* for a requester who
    cannot see the group — silently opening deactivation, expiry, deletion and
    the local-login fallback on administrator accounts, up to and including
    deleting the last one. The predicates query UserGroup.objects directly for
    exactly this reason; these tests are what keeps them there."""

    BLIND = ["add_user", "change_user", "delete_user", "view_user"]

    @pytest.fixture
    def blind_manager(self, app_config, authenticated_client):
        """A user manager without view_usergroup, so no group is visible to it.
        `authenticated_client` guarantees a global admin exists to target."""
        return _make_user_manager("blind.guarded@tests.com", self.BLIND)

    def test_blind_manager_sees_no_user_group(self, blind_manager):
        """The precondition the guards used to trip over."""
        assert not list(
            RoleAssignment.get_viewable_object_ids(blind_manager, UserGroup)
        )

    def test_is_admin_survives_the_visibility_filtered_prefetch(self, blind_manager):
        """The mechanism, pinned directly: a User loaded through the viewset's
        prefetch must still know it is an administrator."""
        from django.db.models import Prefetch

        admin_group = UserGroup.objects.get(name="BI-UG-ADM")
        target = User.objects.create_user(
            "prefetched.admin@tests.com", is_published=True
        )
        admin_group.user_set.add(target)

        viewable = RoleAssignment.get_viewable_object_ids(blind_manager, UserGroup)
        tainted = User.objects.prefetch_related(
            Prefetch("user_groups", queryset=UserGroup.objects.filter(id__in=viewable))
        ).get(pk=target.pk)

        assert list(tainted.user_groups.all()) == []
        assert tainted.is_admin() is True

    def test_blind_manager_cannot_deactivate_admin(self, blind_manager):
        admin_group = UserGroup.objects.get(name="BI-UG-ADM")
        target = User.objects.create_user("blind.target1@tests.com", is_published=True)
        admin_group.user_set.add(target)

        response = _client_for(blind_manager).patch(
            reverse("users-detail", args=[target.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "adminAccountLifecycleChangeRequiresAdminRights"
            in response.json()["is_active"]
        )
        target.refresh_from_db()
        assert target.is_active is True

    def test_blind_manager_cannot_expire_the_last_admin(self, blind_manager):
        only_admin = User.objects.get(email="admin@tests.com")

        response = _client_for(blind_manager).patch(
            reverse("users-detail", args=[only_admin.id]),
            {"expiry_date": "2020-01-01"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        only_admin.refresh_from_db()
        assert only_admin.expiry_date is None

    def test_blind_manager_cannot_enable_local_login_on_admin(self, blind_manager):
        admin_group = UserGroup.objects.get(name="BI-UG-ADM")
        target = User.objects.create_user("blind.target2@tests.com", is_published=True)
        admin_group.user_set.add(target)

        response = _client_for(blind_manager).patch(
            reverse("users-detail", args=[target.id]),
            {"keep_local_login": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target.refresh_from_db()
        assert target.keep_local_login is False

    def test_blind_manager_cannot_delete_admin(self, blind_manager):
        admin_group = UserGroup.objects.get(name="BI-UG-ADM")
        target = User.objects.create_user("blind.target3@tests.com", is_published=True)
        admin_group.user_set.add(target)

        response = _client_for(blind_manager).delete(
            reverse("users-detail", args=[target.id])
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error"] == "deletingAdminAccountRequiresAdminRights"
        assert User.objects.filter(id=target.id).exists()

    def test_blind_manager_cannot_delete_the_last_admin(self, blind_manager):
        """The worst outcome of the visibility-filtered read: a complete,
        unrecoverable admin lockout."""
        only_admin = User.objects.get(email="admin@tests.com")

        response = _client_for(blind_manager).delete(
            reverse("users-detail", args=[only_admin.id])
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert User.objects.filter(id=only_admin.id).exists()

    def test_blind_manager_can_still_offboard_a_plain_user(self, blind_manager):
        """The guards stay targeted: routine offboarding is unaffected."""
        target = User.objects.create_user("blind.plain@tests.com", is_published=True)

        response = _client_for(blind_manager).patch(
            reverse("users-detail", args=[target.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.is_active is False


@pytest.mark.django_db
class TestBatchActionGuards:
    """batch_action calls perform_destroy()/the serializer directly rather than
    going through destroy()/update(), so every guard must hold on this path too
    — otherwise POST /users/batch-action/ is an unguarded door to exactly the
    deletions and demotions the single-object endpoints refuse."""

    def test_user_manager_cannot_batch_delete_scim_account(self, escalation_env):
        target = _make_scim_user("scim.batch@tests.com")

        response = escalation_env.manager_client.post(
            reverse("users-batch-action"),
            {"action": "delete", "ids": [str(target.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["succeeded"] == []
        assert (
            response.json()["failed"][0]["error"]["error"]
            == "onlyAdminCanDeleteScimAccount"
        )
        assert User.objects.filter(id=target.id).exists()

    def test_user_manager_cannot_batch_delete_admin_account(self, escalation_env):
        env = escalation_env
        target = User.objects.create_user("batch.admin@tests.com", is_published=True)
        env.admin_group.user_set.add(target)

        response = env.manager_client.post(
            reverse("users-batch-action"),
            {"action": "delete", "ids": [str(target.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["succeeded"] == []
        assert (
            response.json()["failed"][0]["error"]["error"]
            == "deletingAdminAccountRequiresAdminRights"
        )
        assert User.objects.filter(id=target.id).exists()

    def test_last_admin_cannot_be_batch_deleted(self, escalation_env):
        """The lockout guard, on the path that used to skip it entirely."""
        env = escalation_env
        last_admin = User.objects.get(email="admin@tests.com")

        response = env.admin_client.post(
            reverse("users-batch-action"),
            {"action": "delete", "ids": [str(last_admin.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["succeeded"] == []
        assert (
            response.json()["failed"][0]["error"]["error"]
            == "attemptToDeleteOnlyAdminAccountError"
        )
        assert User.objects.filter(id=last_admin.id).exists()

    def test_user_manager_can_batch_delete_non_admin_user(self, escalation_env):
        """The guards are targeted, not a blanket ban: routine offboarding
        still works in batch."""
        env = escalation_env
        target = User.objects.create_user("batch.plain@tests.com", is_published=True)
        env.reader_group.user_set.add(target)

        response = env.manager_client.post(
            reverse("users-batch-action"),
            {"action": "delete", "ids": [str(target.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["failed"] == []
        assert not User.objects.filter(id=target.id).exists()

    def test_last_admin_group_cannot_be_batch_removed(self, escalation_env):
        """remove_m2m on user_groups reaches the serializer, never
        UserViewSet.update — so the last-admin check has to live there."""
        env = escalation_env
        last_admin = User.objects.get(email="admin@tests.com")

        response = env.admin_client.post(
            reverse("users-batch-action"),
            {
                "action": "remove_m2m",
                "ids": [str(last_admin.id)],
                "field": "user_groups",
                "value": [str(env.admin_group.id)],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["succeeded"] == []
        assert (
            response.json()["failed"][0]["error"]["error"]
            == "attemptToRemoveOnlyAdminUserGroup"
        )
        last_admin.refresh_from_db()
        assert last_admin.user_groups.filter(pk=env.admin_group.pk).exists()

    def test_user_manager_cannot_batch_deactivate_admin(self, escalation_env):
        """change_field on is_active goes through the serializer, so the
        admin-lifecycle guard applies in batch as well."""
        env = escalation_env
        target = User.objects.create_user(
            "batch.deactivate@tests.com", is_published=True
        )
        env.admin_group.user_set.add(target)

        response = env.manager_client.post(
            reverse("users-batch-action"),
            {
                "action": "change_field",
                "ids": [str(target.id)],
                "field": "is_active",
                "value": False,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["succeeded"] == []
        target.refresh_from_db()
        assert target.is_active is True


@pytest.mark.django_db
class TestLastAdminWriteTimeRecheck:
    """The serializer's last-admin checks read before any lock is held, so on
    their own they are check-then-act: two concurrent requests stripping
    BI-UG-ADM from two *different* admins would both see a second admin standing
    and both proceed. UserViewSet.perform_update re-runs the predicates under
    the admin-group lock, in the write's transaction.

    These tests neutralize the serializer's copy of the check, standing in for a
    concurrent request that committed in the window between it and the write,
    and assert the write is still refused. A real thread race is not tested on
    purpose: the test DB is SQLite, where select_for_update compiles to nothing,
    so such a test would prove nothing here and would be timing-dependent in CI.
    What matters and is deterministic is that the write-time pass is
    authoritative rather than a duplicate of the validation-time one."""

    def test_group_removal_refused_when_validation_passed_on_stale_data(
        self, escalation_env
    ):
        env = escalation_env
        last_admin = User.objects.get(email="admin@tests.com")

        with patch.object(
            UserWriteSerializer, "_enforce_last_admin_group", lambda self, attrs: None
        ):
            response = env.admin_client.patch(
                reverse("users-detail", args=[last_admin.id]),
                {"user_groups": []},
                format="json",
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error"] == "attemptToRemoveOnlyAdminUserGroup"
        assert last_admin.user_groups.filter(pk=env.admin_group.pk).exists()

    def test_batch_group_removal_refused_when_validation_passed_on_stale_data(
        self, escalation_env
    ):
        """The path the lock previously did not cover at all — and, because a
        lock only excludes writers that take it, the one that could slip past a
        concurrent update() holding it."""
        env = escalation_env
        last_admin = User.objects.get(email="admin@tests.com")

        with patch.object(
            UserWriteSerializer, "_enforce_last_admin_group", lambda self, attrs: None
        ):
            response = env.admin_client.post(
                reverse("users-batch-action"),
                {
                    "action": "remove_m2m",
                    "ids": [str(last_admin.id)],
                    "field": "user_groups",
                    "value": [str(env.admin_group.id)],
                },
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["succeeded"] == []
        assert (
            response.json()["failed"][0]["error"]["error"]
            == "attemptToRemoveOnlyAdminUserGroup"
        )
        assert last_admin.user_groups.filter(pk=env.admin_group.pk).exists()

    def test_deactivation_refused_when_validation_passed_on_stale_data(
        self, escalation_env
    ):
        env = escalation_env
        last_admin = User.objects.get(email="admin@tests.com")

        with patch.object(
            UserWriteSerializer, "_enforce_last_active_admin", lambda self, attrs: None
        ):
            response = env.admin_client.patch(
                reverse("users-detail", args=[last_admin.id]),
                {"is_active": False},
                format="json",
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["is_active"] == [
            "attemptToDeactivateOnlyAdminAccountError"
        ]
        last_admin.refresh_from_db()
        assert last_admin.is_active is True

    def test_ordinary_admin_writes_still_go_through(self, escalation_env):
        """The re-check is targeted: writes that keep an administrator standing
        are untouched by the lock path."""
        env = escalation_env
        spare = User.objects.create_user("spare.admin3@tests.com", is_published=True)
        env.admin_group.user_set.add(spare)

        response = env.admin_client.patch(
            reverse("users-detail", args=[spare.id]),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        spare.refresh_from_db()
        assert spare.is_active is False


@pytest.mark.django_db
class TestExpiredUsersTaskLastAdminBackstop:
    """The nightly deactivate_expired_users task must never expire the
    deployment out of administration (expiry dates may predate the API guard)."""

    def test_task_skips_the_last_active_admin(self, app_config, authenticated_client):
        from datetime import date, timedelta

        from core.tasks import deactivate_expired_users

        admin_group = UserGroup.objects.get(name="BI-UG-ADM")
        expired_admin = User.objects.create_user(
            "expired.admin@tests.com", is_published=True
        )
        admin_group.user_set.add(expired_admin)
        expired_admin.expiry_date = date.today() - timedelta(days=1)
        expired_admin.save(update_fields=["expiry_date"])
        # Sideline the fixture superuser admin without triggering the model's
        # superuser-reactivation logic, making expired_admin the last active one.
        User.objects.filter(email="admin@tests.com").update(is_active=False)

        expired_user = User.objects.create_user(
            "expired.user@tests.com", is_published=True
        )
        expired_user.expiry_date = date.today() - timedelta(days=1)
        expired_user.save(update_fields=["expiry_date"])

        deactivate_expired_users.call_local()

        expired_admin.refresh_from_db()
        expired_user.refresh_from_db()
        assert expired_admin.is_active is True
        assert expired_user.is_active is False


@pytest.mark.django_db
class TestUserCreatorEditionGate:
    """The User creator role and group only exist where DELEGATED_USER_CREATION
    is set (the enterprise settings), mirroring CONFIGURABLE_DEFAULT_ROLE."""

    def test_not_provisioned_without_the_setting(self):
        # The test database was built by startup() under community settings.
        assert not Role.objects.filter(name="BI-RL-UCR").exists()
        assert not UserGroup.objects.filter(name="BI-UG-GUC").exists()

    def test_startup_provisions_them_with_the_setting(self):
        from django.apps import apps as django_apps
        from django.test import override_settings

        from core.startup import startup

        migratable = [
            c for c in django_apps.get_app_configs() if c.models_module is not None
        ]
        with override_settings(DELEGATED_USER_CREATION=True):
            startup(sender=migratable[-1])

        assert Role.objects.filter(name="BI-RL-UCR", builtin=True).exists()
        assert UserGroup.objects.filter(
            name="BI-UG-GUC", folder=Folder.get_root_folder(), builtin=True
        ).exists()


@pytest.mark.django_db
class TestGlobalUserCreatorGroup:
    """The builtin "Global - User creator" group lets a non-admin (typically a
    domain manager) create users, and nothing more: placing them in groups
    still needs change_usergroup, and editing or deleting them stays with
    administrators."""

    @pytest.fixture(autouse=True)
    def user_creator_group(self, app_config):
        ensure_user_creator_group()

    @pytest.fixture
    def creator_client(self, authenticated_client):
        creator = User.objects.create_user("creator@tests.com")
        UserGroup.objects.get(name="BI-UG-GUC").user_set.add(creator)
        return _client_for(creator)

    def test_group_grants_create_and_view_user_on_global_only(self, app_config):
        group = UserGroup.objects.get(name="BI-UG-GUC")
        ra = RoleAssignment.objects.get(user_group=group)

        assert group.builtin and ra.builtin
        assert ra.is_recursive is False
        assert list(ra.perimeter_folders.all()) == [Folder.get_root_folder()]
        assert set(ra.role.permissions.values_list("codename", flat=True)) == {
            "add_user",
            "view_user",
        }
        assert str(group) == "Global - User creator"

    def test_domain_group_backfill_keeps_it_non_recursive(self, app_config):
        """create_default_ug_and_ra forces recursion on the per-domain builtin
        assignments; it must leave this Global one alone."""
        domain = Folder.objects.create(
            name="backfill domain",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(domain)
        assert UserGroup.objects.filter(folder=domain, builtin=True).exists()

        ra = RoleAssignment.objects.get(user_group__name="BI-UG-GUC")
        assert ra.is_recursive is False

    def test_interrupted_provisioning_leaves_nothing_behind(self, app_config):
        """The group and its grant are written together: a run that fails half-way
        must not leave a group that the next startup's existence check would
        skip forever."""
        UserGroup.objects.filter(name="BI-UG-GUC").delete()

        with patch.object(RoleAssignment.objects, "create", side_effect=RuntimeError):
            with pytest.raises(RuntimeError):
                ensure_user_creator_group()
        assert not UserGroup.objects.filter(name="BI-UG-GUC").exists()

        ensure_user_creator_group()
        ra = RoleAssignment.objects.get(user_group__name="BI-UG-GUC")
        assert ra.is_recursive is False
        assert list(ra.perimeter_folders.all()) == [Folder.get_root_folder()]

    def test_member_can_create_and_list_users(self, creator_client):
        response = creator_client.post(
            reverse("users-list"), {"email": "newcomer@tests.com"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED, response.content
        listed = creator_client.get(reverse("users-list"), {"limit": 1000}).json()
        assert "newcomer@tests.com" in {row["email"] for row in listed["results"]}

    def test_member_cannot_grant_groups_on_create(self, creator_client):
        reader_group = UserGroup.objects.get(name="BI-UG-GAD")

        response = creator_client.post(
            reverse("users-list"),
            {"email": "preloaded@tests.com", "user_groups": [str(reader_group.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not User.objects.filter(email="preloaded@tests.com").exists()

    def test_member_cannot_edit_or_delete_users(self, creator_client):
        target = User.objects.create_user("existing@tests.com")

        patch_response = creator_client.patch(
            reverse("users-detail", args=[target.id]),
            {"first_name": "Renamed"},
            format="json",
        )
        delete_response = creator_client.delete(
            reverse("users-detail", args=[target.id])
        )

        assert patch_response.status_code == status.HTTP_403_FORBIDDEN
        assert delete_response.status_code == status.HTTP_403_FORBIDDEN
        target.refresh_from_db()
        assert target.first_name == ""

    def test_domain_manager_creates_user_then_places_them(self, authenticated_client):
        """The intended flow: create the user, then add them to a group of the
        manager's own domain through add-members."""
        domain = Folder.objects.create(
            name="managed domain",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(domain)
        manager = User.objects.create_user("domain.manager@tests.com")
        UserGroup.objects.get(name="BI-UG-DMA", folder=domain).user_set.add(manager)
        UserGroup.objects.get(name="BI-UG-GUC").user_set.add(manager)
        client = _client_for(manager)

        created = client.post(
            reverse("users-list"), {"email": "recruit@tests.com"}, format="json"
        )
        assert created.status_code == status.HTTP_201_CREATED, created.content
        recruit = User.objects.get(email="recruit@tests.com")

        analysts = UserGroup.objects.get(name="BI-UG-ANA", folder=domain)
        placed = client.post(
            reverse("user-groups-add-members", args=[analysts.id]),
            {"users": [str(recruit.id)]},
            format="json",
        )
        assert placed.status_code == status.HTTP_200_OK, placed.content
        assert analysts.user_set.filter(pk=recruit.pk).exists()


@pytest.mark.django_db
class TestUserFullView:
    """Every domain member sees users through `view_user`, ambient on the root
    folder. Sign-in and administration fields need the full view of the user: being
    them, or holding `view_user_full` or `change_user` on their folder (see the
    full-view-permissions ADR)."""

    TARGET_EXPIRY = "2030-01-01"
    # Spelled out rather than imported, so dropping a field from the serializer's
    # list fails here.
    FULL_VIEW_FIELDS = {
        "is_superuser",
        "has_mfa_enabled",
        "expiry_date",
        "keep_local_login",
        "is_scim_managed",
        "is_jit_provisioned",
        "observation",
    }
    # Base view only: the ambient baseline role, a domain Reader, the Global
    # analyst, approver and user creator groups, and a custom role holding only
    # `view_user` on Global.
    VIEWERS = [
        "ambient",
        "reader",
        "global_analyst",
        "global_approver",
        "creator",
        "base_only",
    ]
    # Full view through `view_user_full` or `change_user` on Global.
    FULL_VIEWERS = [
        "superuser",
        "manager",
        "full_viewer",
        "change_only",
        "global_reader",
    ]

    @pytest.fixture
    def env(self, authenticated_client):
        domain = Folder.objects.create(
            name="full view domain",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(domain)

        # Sorts before admin@tests.com, so a superuser-first order is visible.
        target = User.objects.create_user("aaron.target@tests.com")
        target.expiry_date = self.TARGET_EXPIRY
        target.keep_local_login = True
        target.observation = "contractor, leaves in January"
        target.save()
        idp_group = IdPGroup.objects.create(name="sg-contractors")
        target.idp_groups.add(idp_group)
        # Users live in Global, which is where a custom user manager role applies.
        assert target.folder_id == Folder.get_root_folder().id
        # Sorts first by email, so an order that drops `-is_active` shows.
        User.objects.create_user("aardvark.inactive@tests.com", is_active=False)

        root = Folder.get_root_folder()

        # The Auditee role holds no user permission: its view of users is ambient.
        ambient = User.objects.create_user("ambient@tests.com")
        auditees = UserGroup.objects.get(name="BI-UG-ADE", folder=domain)
        assert not auditees.roleassignment_set.filter(
            role__permissions__codename__in=["view_user", "view_user_full"]
        ).exists()
        auditees.user_set.add(ambient)

        reader = User.objects.create_user("reader@tests.com")
        UserGroup.objects.get(name="BI-UG-AUD", folder=domain).user_set.add(reader)

        global_analyst = User.objects.create_user("global.analyst@tests.com")
        UserGroup.objects.get(name="BI-UG-ANA", folder=root).user_set.add(
            global_analyst
        )
        global_approver = User.objects.create_user("global.approver@tests.com")
        UserGroup.objects.get(name="BI-UG-GAP", folder=root).user_set.add(
            global_approver
        )
        ensure_user_creator_group()
        creator = User.objects.create_user("creator@tests.com")
        UserGroup.objects.get(name="BI-UG-GUC").user_set.add(creator)
        base_only = _make_user_manager("base.only@tests.com", ["view_user"])

        global_reader = User.objects.create_user("global.reader@tests.com")
        UserGroup.objects.get(name="BI-UG-GAD", folder=root).user_set.add(global_reader)
        # Not superusers: the full view from view_user_full, change_user, or both.
        manager = _make_user_manager(
            "manager@tests.com", ["view_user", "view_user_full", "change_user"]
        )
        full_viewer = _make_user_manager(
            "full.viewer@tests.com", ["view_user", "view_user_full"]
        )
        change_only = _make_user_manager(
            "change.only@tests.com", ["view_user", "change_user"]
        )

        users = {
            "ambient": ambient,
            "reader": reader,
            "global_analyst": global_analyst,
            "global_approver": global_approver,
            "creator": creator,
            "base_only": base_only,
        }
        full_viewers = {
            "manager": manager,
            "full_viewer": full_viewer,
            "change_only": change_only,
            "global_reader": global_reader,
        }
        return SimpleNamespace(
            domain=domain,
            target=target,
            idp_group=idp_group,
            admin_client=authenticated_client,
            full_viewers={
                "superuser": authenticated_client,
                **{name: _client_for(user) for name, user in full_viewers.items()},
            },
            clients={name: _client_for(user) for name, user in users.items()},
            users=users,
        )

    @staticmethod
    def _rows(response):
        assert response.status_code == status.HTTP_200_OK, response.content
        data = response.data
        return data["results"] if isinstance(data, dict) else data

    def _payloads(self, client, user):
        """The user as served by the list, the detail and the edit-form read."""
        listed = {
            row["email"]: row for row in self._rows(client.get(reverse(API_ENDPOINT)))
        }
        detail = client.get(reverse("users-detail", args=[user.id]))
        write = client.get(reverse("users-object", args=[user.id]))
        assert detail.status_code == status.HTTP_200_OK, detail.content
        assert write.status_code == status.HTTP_200_OK, write.content
        return [listed[user.email], detail.data, write.data]

    @pytest.mark.parametrize("viewer", VIEWERS)
    def test_viewer_gets_base_fields_only(self, env, viewer):
        for payload in self._payloads(env.clients[viewer], env.target):
            assert payload["email"] == env.target.email
            assert payload["is_active"] is True
            assert not self.FULL_VIEW_FIELDS & set(payload)

        write = self._payloads(env.clients[viewer], env.target)[2]
        assert "user_groups" not in write and "is_local" not in write

    @pytest.mark.parametrize("full_viewer", FULL_VIEWERS)
    def test_full_viewer_gets_full_record(self, env, full_viewer):
        payloads = self._payloads(env.full_viewers[full_viewer], env.target)
        assert "is_local" in payloads[2] and "user_groups" in payloads[2]
        for payload in payloads:
            assert self.FULL_VIEW_FIELDS <= set(payload)
            assert payload["expiry_date"] == self.TARGET_EXPIRY
            assert payload["keep_local_login"] is True
            assert payload["observation"] == "contractor, leaves in January"
            assert payload["is_superuser"] is False

    @pytest.mark.parametrize("viewer", [*VIEWERS, "global_reader"])
    def test_idp_groups_follow_their_own_permission(self, env, viewer):
        """IdP groups are not a full-view field: like any related object, each one
        is masked for whoever can't read it (`view_idpgroup`, administrators only)."""
        client = env.clients.get(viewer) or env.full_viewers[viewer]
        for payload in self._payloads(client, env.target)[:2]:
            assert payload["idp_groups"] == [{}]
        for payload in self._payloads(env.admin_client, env.target)[:2]:
            assert [group["str"] for group in payload["idp_groups"]] == [
                env.idp_group.name
            ]

    @pytest.mark.parametrize("viewer", VIEWERS)
    def test_self_gets_own_full_record(self, env, viewer):
        user = env.users[viewer]
        payloads = self._payloads(env.clients[viewer], user)
        assert "is_local" in payloads[2] and "user_groups" in payloads[2]
        for payload in payloads:
            assert self.FULL_VIEW_FIELDS <= set(payload)

    @pytest.mark.parametrize("viewer", VIEWERS)
    @pytest.mark.parametrize(
        "query",
        [
            "keep_local_login=true",
            f"expiry_date={TARGET_EXPIRY}",
            "expiry_date__gte=2029-12-31",
            "expiry_date__lt=2031-01-01",
            "expiry_date__isnull=false",
        ],
    )
    def test_full_view_filters_match_fully_viewed_users_only(self, env, viewer, query):
        url = f"{reverse(API_ENDPOINT)}?{query}"
        assert env.target.email not in {
            row["email"] for row in self._rows(env.clients[viewer].get(url))
        }
        for client in env.full_viewers.values():
            assert env.target.email in {
                row["email"] for row in self._rows(client.get(url))
            }

    @pytest.mark.parametrize("viewer", VIEWERS)
    def test_full_view_filter_matches_own_record(self, env, viewer):
        user = env.users[viewer]
        user.keep_local_login = True
        user.save()
        url = f"{reverse(API_ENDPOINT)}?keep_local_login=true"
        assert user.email in {
            row["email"] for row in self._rows(env.clients[viewer].get(url))
        }

    @pytest.mark.parametrize("viewer", VIEWERS)
    def test_viewer_order_reveals_no_full_view_field(self, env, viewer):
        client = env.clients[viewer]

        def emails(query):
            return [
                row["email"]
                for row in self._rows(client.get(f"{reverse(API_ENDPOINT)}?{query}"))
            ]

        rows = self._rows(client.get(reverse(API_ENDPOINT)))
        default = [row["email"] for row in rows]
        # Superusers are not listed first.
        assert default == [
            row["email"]
            for row in sorted(rows, key=lambda r: (not r["is_active"], r["email"]))
        ]
        for field in ("is_superuser", "expiry_date", "keep_local_login"):
            assert emails(f"ordering={field}") == default
            assert emails(f"ordering=-{field}") == default

    def test_folder_members_order_reveals_no_full_view_field(self, env):
        """`/api/folders/<id>/users/` lists a domain's members to its managers,
        who don't have the full view of users."""
        manager = User.objects.create_user("domain.manager@tests.com")
        UserGroup.objects.get(name="BI-UG-DMA", folder=env.domain).user_set.add(manager)
        analysts = UserGroup.objects.get(name="BI-UG-ANA", folder=env.domain)
        analysts.user_set.add(User.objects.create_user("a.plain@tests.com"))
        secret = User.objects.create_user("c.secret@tests.com")
        secret.is_superuser = True
        secret.keep_local_login = True
        secret.save()
        analysts.user_set.add(secret)

        client = _client_for(manager)
        url = reverse("user-perms-on-folder-list", args=[env.domain.id])

        def emails(query):
            return [row["email"] for row in self._rows(client.get(f"{url}?{query}"))]

        by_email = emails("ordering=email")
        # Out of alphabetical order if the superuser flag were sorted on.
        assert by_email.index(secret.email) > by_email.index("a.plain@tests.com")
        for field in ("is_superuser", "keep_local_login", "expiry_date"):
            assert emails(f"ordering=-{field},email") == by_email

    def test_rows_follow_view_user(self, env):
        client = env.clients["base_only"]
        listed = self._rows(client.get(reverse(API_ENDPOINT)))
        assert env.target.email in {row["email"] for row in listed}
        detail = client.get(reverse("users-detail", args=[env.target.id]))
        assert detail.status_code == status.HTTP_200_OK
        found = self._rows(client.get(f"{reverse('users-autocomplete')}?search=aaron"))
        assert env.target.email in {row["email"] for row in found}
        actors = self._rows(client.get(reverse("actors-list")))
        assert str(Actor.objects.get(user=env.target).id) in {
            str(row["id"]) for row in actors
        }

        # Without it, other users stay out of sight.
        nobody = _client_for(User.objects.create_user("nobody@tests.com"))
        listed = self._rows(nobody.get(reverse(API_ENDPOINT)))
        assert env.target.email not in {row["email"] for row in listed}
        detail = nobody.get(reverse("users-detail", args=[env.target.id]))
        assert detail.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_full_view_alone_grants_no_rows(self, env):
        user = _make_user_manager("full.only@tests.com", ["view_user_full"])
        assert env.target.id not in set(
            RoleAssignment.get_viewable_object_ids(user, User)
        )
        client = _client_for(user)
        listed = self._rows(client.get(reverse(API_ENDPOINT)))
        assert {row["email"] for row in listed} == {user.email}
        detail = client.get(reverse("users-detail", args=[env.target.id]))
        assert detail.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_builtin_role_grants(self, env):
        def codenames(role):
            return set(
                Role.objects.get(name=role).permissions.values_list(
                    "codename", flat=True
                )
            )

        for role in ("BI-RL-ADM", "BI-RL-AUD"):
            assert {"view_user", "view_user_full"} <= codenames(role)
        for role in ("BI-RL-BSL", "BI-RL-ANA", "BI-RL-APP", "BI-RL-DMA", "BI-RL-UCR"):
            assert "view_user" in codenames(role)
            assert "view_user_full" not in codenames(role)

    @pytest.mark.parametrize(
        "serializer_class", [UserReadSerializer, UserWriteSerializer]
    )
    def test_hidden_without_request(self, env, serializer_class):
        assert not self.FULL_VIEW_FIELDS & set(serializer_class(env.target).data)

    def test_full_view_filter_without_request_matches_nothing(self, env):
        filterset = UserFilter(
            data={"keep_local_login": True}, queryset=User.objects.all()
        )
        assert not filterset.qs.exists()

    def test_picker_skips_the_check_on_every_row(self, env):
        # Pickers query on every keystroke and don't order on full-view fields, so
        # they skip checking the full view of every row; listings run it.
        with patch.object(UserViewSet, "_has_full_view_of", side_effect=AssertionError):
            found = self._rows(
                env.admin_client.get(f"{reverse('users-autocomplete')}?search=aaron")
            )
            with pytest.raises(AssertionError):
                env.admin_client.get(reverse(API_ENDPOINT))
        assert env.target.email in {row["email"] for row in found}

    def test_full_viewer_order_keeps_full_view_fields(self, env):
        def emails(query):
            return [
                row["email"]
                for row in self._rows(
                    env.admin_client.get(f"{reverse(API_ENDPOINT)}?{query}")
                )
            ]

        assert emails("")[0] == "admin@tests.com"
        assert emails("ordering=is_superuser")[-1] == "admin@tests.com"


@pytest.mark.django_db
class TestViewUserFullMigration:
    """The upgrade keeps what custom roles serve, except through Global's default
    role, which every member holds."""

    @staticmethod
    def _grant():
        import_module(
            "iam.migrations.0033_user_view_full_permission"
        ).grant_view_user_full(django_apps, None)

    def test_custom_roles_with_view_user_keep_the_full_record(self):
        root = Folder.get_root_folder()
        view_user = Permission.objects.get(codename="view_user")
        full = Permission.objects.get(codename="view_user_full")

        custom = Role.objects.create(name="access reviewers", folder=root)
        custom.permissions.add(view_user)
        unrelated = Role.objects.create(name="asset readers", folder=root)
        default = Role.objects.create(name="custom default", folder=root)
        default.permissions.add(view_user)
        Folder.objects.filter(pk=root.pk).update(default_role=default)
        baseline = Role.objects.get(name="BI-RL-BSL")
        baseline.permissions.add(view_user)

        self._grant()

        assert custom.permissions.filter(pk=full.pk).exists()
        assert not unrelated.permissions.filter(pk=full.pk).exists()
        assert not default.permissions.filter(pk=full.pk).exists()
        # Builtin roles are startup's business.
        assert not baseline.permissions.filter(pk=full.pk).exists()

    def test_rerun_is_harmless(self):
        custom = Role.objects.create(
            name="access reviewers", folder=Folder.get_root_folder()
        )
        custom.permissions.add(Permission.objects.get(codename="view_user"))
        self._grant()
        self._grant()
        assert custom.permissions.filter(codename="view_user_full").count() == 1


@pytest.fixture
def third_party_env(app_config, authenticated_client):
    """A vendor entity in domain A with one third-party representative, an
    analyst on A, and an analyst on an unrelated domain B (who still reaches
    Global's baseline role, which carries `view_user`)."""
    from tprm.models import Entity, Representative

    domains = {}
    for name in ("vendor domain", "other domain"):
        domains[name] = Folder.objects.create(
            name=name,
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(domains[name])
    vendor_domain, other_domain = domains["vendor domain"], domains["other domain"]

    entity = Entity.objects.create(name="Vendor Co", folder=vendor_domain)
    third_party = User.objects.create_user("rep@vendor.test", is_third_party=True)
    Representative.objects.create(
        entity=entity, email=third_party.email, user=third_party
    )

    def analyst_on(domain, email):
        user = User.objects.create_user(email)
        UserGroup.objects.get(name="BI-UG-ANA", folder=domain).user_set.add(user)
        return user

    analyst = analyst_on(vendor_domain, "analyst.vendor@tests.com")
    outsider = analyst_on(other_domain, "analyst.other@tests.com")
    return SimpleNamespace(
        vendor_domain=vendor_domain,
        other_domain=other_domain,
        entity=entity,
        third_party=third_party,
        analyst=analyst,
        outsider=outsider,
        admin_client=authenticated_client,
    )


def _emails(response) -> set[str]:
    assert response.status_code == status.HTTP_200_OK, response.content
    rows = (
        response.data["results"] if isinstance(response.data, dict) else response.data
    )
    return {row["email"] for row in rows}


@pytest.mark.django_db
class TestThirdPartyUserVisibility:
    """A third-party user sits in Global, where the baseline role grants
    `view_user` to every member. It must show only to those who can view one of
    its representatives or have the full view of users where it sits, and to
    itself."""

    def test_member_elsewhere_does_not_see_third_party(self, third_party_env):
        env = third_party_env
        client = _client_for(env.outsider)

        listed = _emails(client.get(reverse("users-list")))
        assert env.third_party.email not in listed
        # Internal users are listed as before.
        assert env.analyst.email in listed

        assert env.third_party.email not in _emails(
            client.get(reverse("users-autocomplete"))
        )
        retrieved = client.get(reverse("users-detail", args=[env.third_party.id]))
        assert retrieved.status_code == status.HTTP_404_NOT_FOUND

    def test_analyst_on_entity_domain_sees_third_party(self, third_party_env):
        env = third_party_env
        client = _client_for(env.analyst)

        assert env.third_party.email in _emails(client.get(reverse("users-list")))
        assert env.third_party.email in _emails(
            client.get(reverse("users-autocomplete"))
        )
        retrieved = client.get(reverse("users-detail", args=[env.third_party.id]))
        assert retrieved.status_code == status.HTTP_200_OK

    def test_admin_sees_third_party(self, third_party_env):
        env = third_party_env
        assert env.third_party.email in _emails(
            env.admin_client.get(reverse("users-list"))
        )

    def test_user_manager_sees_third_party_without_representative_access(
        self, third_party_env
    ):
        """`change_user` where the user sits is enough, even with no
        `view_representative` anywhere."""
        env = third_party_env
        manager = _make_user_manager(
            "user.manager@tests.com", ["view_user", "change_user"]
        )
        listed = _emails(_client_for(manager).get(reverse("users-list")))
        assert env.third_party.email in listed

    def test_full_viewer_sees_every_third_party(self, third_party_env):
        """`view_user_full` where the users sit is enough: an access review lists
        every account, those whose representative is gone included."""
        env = third_party_env
        viewer = _make_user_manager(
            "full.viewer@tests.com", ["view_user", "view_user_full"]
        )
        orphan = User.objects.create_user("orphan@vendor.test", is_third_party=True)
        listed = _emails(_client_for(viewer).get(reverse("users-list")))
        assert {env.third_party.email, orphan.email} <= listed

    def test_third_party_with_no_representative_is_hidden_from_members(
        self, third_party_env
    ):
        env = third_party_env
        orphan = User.objects.create_user("orphan@vendor.test", is_third_party=True)
        assert orphan.email not in _emails(
            _client_for(env.analyst).get(reverse("users-list"))
        )
        assert orphan.email in _emails(env.admin_client.get(reverse("users-list")))

    def test_third_party_sees_themself(self, third_party_env):
        env = third_party_env
        client = _client_for(env.third_party)

        assert env.third_party.email in _emails(client.get(reverse("users-list")))
        retrieved = client.get(reverse("users-detail", args=[env.third_party.id]))
        assert retrieved.status_code == status.HTTP_200_OK

    def test_entity_assessment_picker_query(self, third_party_env):
        """EntityAssessmentForm loads representatives from
        users?is_third_party=true&representative__entity=<entity>."""
        env = third_party_env
        params = {"is_third_party": "true", "representative__entity": env.entity.id}

        assert _emails(_client_for(env.analyst).get(reverse("users-list"), params)) == {
            env.third_party.email
        }
        assert (
            _emails(_client_for(env.outsider).get(reverse("users-list"), params))
            == set()
        )

    def test_names_on_readable_objects_still_render(self, third_party_env):
        """Masking of related users reads IAM on its own, not this queryset:
        a readable assessment still names its representative."""
        from tprm.models import EntityAssessment

        env = third_party_env
        assessment = EntityAssessment.objects.create(
            name="Vendor review", folder=env.other_domain, entity=env.entity
        )
        assessment.representatives.add(env.third_party)

        response = _client_for(env.outsider).get(
            reverse("entity-assessments-detail", args=[assessment.id])
        )
        assert response.status_code == status.HTTP_200_OK, response.content
        assert response.json()["representatives"] == [
            {"id": str(env.third_party.id), "str": str(env.third_party)}
        ]
