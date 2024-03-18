import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from iam.models import User

from test_vars import GROUPS_PERMISSIONS, USERS_ENDPOINT as API_ENDPOINT
from test_utils import EndpointTestsQueries

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

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Users",
            User,
            {"email": USER_EMAIL, "first_name": USER_FIRSTNAME, "last_name": USER_NAME},
            base_count=2,
            item_search_field="email",
            user_group=test.user_group,
            scope="Global"
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
            scope="Global"
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
            scope="Global"
        )

    def test_delete_users(self, test):
        """test to delete users with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Users",
            User,
            {"email": USER_EMAIL, "first_name": USER_FIRSTNAME, "last_name": USER_NAME},
            user_group=test.user_group,
            scope="Global"
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
        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), "users can be created with an already used email"
        assert response.json() == {
            "email": ["user with this email already exists."]
        }, "users can be created with an already used email"

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
            assert (
                response.status_code == status.HTTP_400_BAD_REQUEST
            ), f"users can be created with an invalid email ({email})"
            assert response.json() == {
                "email": ["Enter a valid email address."]
            }, f"users can be created with an invalid email ({email})"
