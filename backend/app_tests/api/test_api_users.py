import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from iam.models import User

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

    def test_user_can_see_himself_and_update_only_if_admin(self, test):
        """
        - A user can retrieve their own user object only if in the same domain
        - Only an admin can update their own user object
        """

        list_url = reverse(API_ENDPOINT)
        is_admin = test.user_group == "BI-UG-ADM"

        # --- create the user via admin ---
        user_data = {
            "email": USER_EMAIL,
            "first_name": "Self",
            "last_name": "User",
        }

        response = test.admin_client.post(list_url, user_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        user_id = response.json()["id"]
        detail_url = reverse("users-detail", args=[user_id])

        # --- user attempts to retrieve himself ---
        response = test.client.get(detail_url)

        if (
            is_admin
            or test.folder == response.json().get("folder")
            or test.user_group == "BI-UG-GAD"
            or test.user_group == "BI-UG-GAP"
        ):
            # Admin or same domain can access
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["email"] == USER_EMAIL
        else:
            # Other users cannot access
            assert response.status_code in (
                status.HTTP_403_FORBIDDEN,
                status.HTTP_401_UNAUTHORIZED,
            )

        # --- attempt to update self ---
        updated_data = {"first_name": "Updated"}
        response = test.client.patch(detail_url, updated_data, format="json")

        if is_admin:
            assert response.status_code == status.HTTP_200_OK
            user = User.objects.get(id=user_id)
            assert user.first_name == "Updated"
        else:
            assert response.status_code in (
                status.HTTP_403_FORBIDDEN,
                status.HTTP_401_UNAUTHORIZED,
            )
