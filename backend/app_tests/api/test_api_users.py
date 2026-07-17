import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from iam.models import Folder, User, UserGroup


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
