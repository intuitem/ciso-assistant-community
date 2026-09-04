from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient
from iam.models import Folder, Role, RoleAssignment, User, UserGroup


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

        # Ensure the user exists with is_published=true (since Users are now IAM-filtered)
        user, created = User.objects.get_or_create(
            email=USER_EMAIL,
            defaults={
                "first_name": USER_FIRSTNAME,
                "last_name": USER_NAME,
                "password": USER_PASSWORD,
                "is_active": True,
                "is_published": True,  # Users are now published and IAM-filtered
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
            "alice@tests.com", first_name="Alice", last_name="Smith", is_published=True
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
        User.objects.create_user("needle@tests.com", is_published=True)
        User.objects.create_user("haystack@tests.com", is_published=True)

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
        target = User.objects.create_user("target@tests.com", is_published=True)
        User.objects.create_user("other@tests.com", is_published=True)

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
        User.objects.create_user(
            "inactive@tests.com", is_active=False, is_published=True
        )

        url = reverse("users-autocomplete")
        response = authenticated_client.get(url, {"search": "inactive"})

        rows = (
            response.data["results"]
            if isinstance(response.data, dict)
            else response.data
        )
        assert rows[0]["is_active"] is False

    def test_autocomplete_column_icontains(self, authenticated_client):
        User.objects.create_user(
            "picker@tests.com", first_name="Wolfgang", is_published=True
        )
        User.objects.create_user(
            "other@tests.com", first_name="Bela", is_published=True
        )

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
        member = User.objects.create_user("member@tests.com", is_published=True)
        User.objects.create_user("outsider@tests.com", is_published=True)
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
        User.objects.create_user("zzz@tests.com", first_name="Zed", is_published=True)
        User.objects.create_user("aaa@tests.com", first_name="Ann", is_published=True)

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
