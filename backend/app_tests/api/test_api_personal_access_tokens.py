import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from knox.models import AuthToken
from knox.settings import knox_settings
from knox.auth import TokenAuthentication

from iam.models import PersonalAccessToken

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(email="root@example.com", password="testpassword")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def auth_token(user):
    instance, token = AuthToken.objects.create(user=user, expiry=timedelta(days=30))
    return instance, token


@pytest.fixture
def personal_access_token(user, auth_token):
    instance = PersonalAccessToken.objects.create(
        auth_token=auth_token[0], name="Test Token"
    )
    return instance


@pytest.fixture
def protected_url():
    """URL to a protected resource for testing authentication."""
    return "/api/risk-assessments/"


class TestPersonalAccessTokenViewSet:
    @pytest.mark.django_db
    def test_create_token(self, authenticated_client):
        """Test creating a new personal access token."""
        url = "/api/iam/auth-tokens/"
        data = {"name": "My API Token", "expiry": 30}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert "token" in response.data
        assert response.data["name"] == "My API Token"

        # Verify token was created in the database
        assert PersonalAccessToken.objects.filter(name="My API Token").exists()

    @pytest.mark.django_db
    def test_create_token_with_custom_expiry(self, authenticated_client):
        """Test creating a token with a custom expiry period."""
        url = "/api/iam/auth-tokens/"
        data = {"name": "Short Token", "expiry": 7}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK

        # Check if the expiry matches (approximately) the requested time
        token = PersonalAccessToken.objects.get(name="Short Token")
        now = timezone.now()
        expected_expiry = now + timedelta(days=7)

        # Allow a small time difference for test execution
        assert abs((token.auth_token.expiry - expected_expiry).total_seconds()) < 10

    @pytest.mark.django_db
    def test_create_token_invalid_expiry(self, authenticated_client):
        """Test creating a token with invalid expiry values."""
        url = "/api/iam/auth-tokens/"

        # Test with negative expiry
        data = {"name": "Invalid Token", "expiry": -5}

        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        assert "Expiry must be a positive integer" in response.data["error"]

        # Test with non-integer expiry
        data["expiry"] = "not-a-number"
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_token_limit_per_user(self, authenticated_client, monkeypatch):
        """Test that users cannot exceed their token limit."""
        # Set token limit for test
        monkeypatch.setattr(knox_settings, "TOKEN_LIMIT_PER_USER", 2)

        url = "/api/iam/auth-tokens/"

        # Create first token
        authenticated_client.post(url, {"name": "Token 1", "expiry": 30})

        # Create second token
        authenticated_client.post(url, {"name": "Token 2", "expiry": 30})

        # Try to create a third token - should fail
        response = authenticated_client.post(url, {"name": "Token 3", "expiry": 30})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Maximum amount of tokens allowed" in response.data["error"]

        # Verify only 2 tokens were created
        assert PersonalAccessToken.objects.count() == 2

    @pytest.mark.django_db
    def test_get_tokens(self, authenticated_client, personal_access_token):
        """Test retrieving all tokens for a user."""
        url = "/api/iam/auth-tokens/"

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Test Token"

    @pytest.mark.django_db
    def test_get_tokens_empty(self, authenticated_client):
        """Test retrieving tokens when none exist."""
        url = "/api/iam/auth-tokens/"

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0
        assert response.data == []

    @pytest.mark.django_db
    def test_tokens_for_different_users(self, api_client):
        """Test that users can only see their own tokens."""
        # Create two users
        user1 = User.objects.create_user(
            email="john.doe@example.com", password="password1"
        )
        user2 = User.objects.create_user(
            email="jean.dupont@example.com", password="password2"
        )

        # Create a token for user1
        instance1, _ = AuthToken.objects.create(user=user1, expiry=timedelta(days=30))
        PersonalAccessToken.objects.create(auth_token=instance1, name="User1 Token")

        # Create a token for user2
        instance2, _ = AuthToken.objects.create(user=user2, expiry=timedelta(days=30))
        PersonalAccessToken.objects.create(auth_token=instance2, name="User2 Token")

        url = "/api/iam/auth-tokens/"

        # Authenticate as user1 and check tokens
        api_client.force_authenticate(user=user1)
        response1 = api_client.get(url)

        assert response1.status_code == status.HTTP_200_OK
        assert len(response1.data) == 1
        assert response1.data[0]["name"] == "User1 Token"

        # Authenticate as user2 and check tokens
        api_client.force_authenticate(user=user2)
        response2 = api_client.get(url)

        assert response2.status_code == status.HTTP_200_OK
        assert len(response2.data) == 1
        assert response2.data[0]["name"] == "User2 Token"

    @pytest.mark.django_db
    def test_unauthenticated_access(self, api_client):
        """Test that unauthenticated users cannot access tokens."""
        url = "/api/iam/auth-tokens/"

        # Try to get tokens
        get_response = api_client.get(url)
        assert get_response.status_code == status.HTTP_401_UNAUTHORIZED

        # Try to create a token
        post_response = api_client.post(url, {"name": "Unauth Token", "expiry": 30})
        assert post_response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_authenticate_with_token(
        self, api_client, authenticated_client, protected_url
    ):
        """Test that a personal access token can be used to authenticate a request."""
        # First create a new token
        token_url = "/api/iam/auth-tokens/"
        token_data = {"name": "Auth Test Token", "expiry": 30}

        # Create the token
        response = authenticated_client.post(token_url, token_data)
        assert response.status_code == status.HTTP_200_OK

        # Extract the token value
        token_value = response.data["token"]

        # Create a fresh client (unauthenticated)
        fresh_client = APIClient()

        # Try to access protected resource without authentication
        response_without_auth = fresh_client.get(protected_url)
        assert response_without_auth.status_code == status.HTTP_401_UNAUTHORIZED

        # Now try with token authentication
        fresh_client.credentials(HTTP_AUTHORIZATION=f"Token {token_value}")
        response_with_auth = fresh_client.get(protected_url)
        assert response_with_auth.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_expired_token_authentication(
        self, authenticated_client, api_client, protected_url
    ):
        """Test that an expired token cannot be used for authentication."""
        # Create a token with a very short expiry time
        token_url = "/api/iam/auth-tokens/"
        token_data = {
            "name": "Short-lived Token",
            "expiry": 1,  # 1 day expiry
        }

        # Create the token
        response = authenticated_client.post(token_url, token_data)
        assert response.status_code == status.HTTP_200_OK
        token_value = response.data["token"]

        # Get the token from the database
        pat = PersonalAccessToken.objects.get(name="Short-lived Token")
        auth_token = pat.auth_token

        # Verify the token works initially
        test_client = APIClient()
        test_client.credentials(HTTP_AUTHORIZATION=f"Token {token_value}")
        initial_response = test_client.get(protected_url)
        assert initial_response.status_code == status.HTTP_200_OK

        # Expire the token by setting its expiry time in the past
        auth_token.expiry = timezone.now() - timedelta(hours=1)
        auth_token.save()

        # Clear the authentication cache if needed
        TokenAuthentication.validate_user = lambda self, user: user

        # Try to use the expired token
        expired_response = test_client.get(protected_url)
        assert expired_response.status_code == status.HTTP_401_UNAUTHORIZED
