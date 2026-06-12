import pytest
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from iam.models import UserGroup

User = get_user_model()

RESET_MFA_URL = "/api/iam/reset-mfa/"


@pytest.fixture
def admin_user(db):
    admin = User.objects.create_superuser(email="admin@tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin_group.user_set.add(admin)
    return admin


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(email="regular@tests.com", password="pw-12345!")


@pytest.fixture
def target_user_with_mfa(db):
    user = User.objects.create_user(email="target@tests.com", password="pw-12345!")
    Authenticator.objects.create(
        user=user,
        type=Authenticator.Type.TOTP,
        data={"secret": "JBSWY3DPEHPK3PXP"},
    )
    return user


@pytest.fixture
def target_user_no_mfa(db):
    return User.objects.create_user(email="no-mfa@tests.com", password="pw-12345!")


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def regular_client(regular_user):
    client = APIClient()
    client.force_authenticate(user=regular_user)
    return client


@pytest.mark.django_db
class TestResetMFAView:
    def test_admin_can_reset_another_users_mfa(
        self, admin_client, target_user_with_mfa
    ):
        assert Authenticator.objects.filter(user=target_user_with_mfa).exists()

        response = admin_client.post(
            RESET_MFA_URL,
            data={"user": str(target_user_with_mfa.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert not Authenticator.objects.filter(user=target_user_with_mfa).exists()

    def test_admin_cannot_reset_own_mfa(self, admin_client, admin_user):
        Authenticator.objects.create(
            user=admin_user,
            type=Authenticator.Type.TOTP,
            data={"secret": "JBSWY3DPEHPK3PXP"},
        )

        response = admin_client.post(
            RESET_MFA_URL,
            data={"user": str(admin_user.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data.get("error") == "cannotResetOwnMFA"
        assert Authenticator.objects.filter(user=admin_user).exists()

    def test_returns_400_when_target_user_has_no_mfa(
        self, admin_client, target_user_no_mfa
    ):
        response = admin_client.post(
            RESET_MFA_URL,
            data={"user": str(target_user_no_mfa.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data.get("error") == "userHasNoMFAEnabled"

    def test_non_admin_cannot_reset_mfa(self, regular_client, target_user_with_mfa):
        response = regular_client.post(
            RESET_MFA_URL,
            data={"user": str(target_user_with_mfa.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Authenticator.objects.filter(user=target_user_with_mfa).exists()

    def test_unauthenticated_request_is_rejected(self, target_user_with_mfa):
        client = APIClient()
        response = client.post(
            RESET_MFA_URL,
            data={"user": str(target_user_with_mfa.id)},
            format="json",
        )

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
        assert Authenticator.objects.filter(user=target_user_with_mfa).exists()
