from base64 import urlsafe_b64encode

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from iam.models import PersonalAccessToken, UserGroup

User = get_user_model()

CHANGE_PASSWORD_URL = "/api/iam/change-password/"
SET_PASSWORD_URL = "/api/iam/set-password/"
RESET_PASSWORD_CONFIRM_URL = "/api/iam/password-reset/confirm/"

OLD_PASSWORD = "pw-12345!"
NEW_PASSWORD = "Zq7!vortex-maple"


def create_session_token(user):
    """Create a plain Knox session token, returning (instance, token string)."""
    return AuthToken.objects.create(user=user)


def create_personal_access_token(user, name="test-pat"):
    """Create a PAT (a Knox token wrapped in a PersonalAccessToken)."""
    instance, token = AuthToken.objects.create(user=user)
    pat = PersonalAccessToken.objects.create(name=name, auth_token=instance)
    return pat, token


def session_tokens(user):
    """Knox tokens that are plain sessions (not backing a PAT)."""
    return AuthToken.objects.filter(user=user, personalaccesstoken__isnull=True)


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@tests.com", password=OLD_PASSWORD)


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="other@tests.com", password=OLD_PASSWORD)


@pytest.fixture
def admin_user(db):
    admin = User.objects.create_superuser(email="admin@tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin_group.user_set.add(admin)
    return admin


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


def change_password_payload():
    return {
        "old_password": OLD_PASSWORD,
        "new_password": NEW_PASSWORD,
        "confirm_new_password": NEW_PASSWORD,
    }


def set_password_payload(target_user):
    return {
        "user": str(target_user.id),
        "new_password": NEW_PASSWORD,
        "confirm_new_password": NEW_PASSWORD,
    }


def reset_confirm_payload(target_user, token=None):
    return {
        "uidb64": urlsafe_b64encode(str(target_user.pk).encode()).decode(),
        "token": token
        if token is not None
        else PasswordResetTokenGenerator().make_token(target_user),
        "new_password": NEW_PASSWORD,
        "confirm_new_password": NEW_PASSWORD,
    }


@pytest.mark.django_db
class TestChangePasswordSessionRevocation:
    def test_revokes_all_session_tokens_including_current(self, user):
        _, current_token = create_session_token(user)
        create_session_token(user)
        assert session_tokens(user).count() == 2

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {current_token}")
        response = client.post(
            CHANGE_PASSWORD_URL, data=change_password_payload(), format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)
        assert session_tokens(user).count() == 0

    def test_current_token_is_unusable_after_change(self, user):
        _, current_token = create_session_token(user)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {current_token}")
        response = client.post(
            CHANGE_PASSWORD_URL, data=change_password_payload(), format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        replay = client.post(
            CHANGE_PASSWORD_URL, data=change_password_payload(), format="json"
        )
        assert replay.status_code == status.HTTP_401_UNAUTHORIZED

    def test_preserves_personal_access_tokens(self, user):
        pat, _ = create_personal_access_token(user)
        create_session_token(user)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            CHANGE_PASSWORD_URL, data=change_password_payload(), format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert PersonalAccessToken.objects.filter(pk=pat.pk).exists()
        assert AuthToken.objects.filter(pk=pat.auth_token.pk).exists()
        assert session_tokens(user).count() == 0

    def test_does_not_touch_other_users_tokens(self, user, other_user):
        create_session_token(user)
        create_session_token(other_user)
        other_pat, _ = create_personal_access_token(other_user)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            CHANGE_PASSWORD_URL, data=change_password_payload(), format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert session_tokens(user).count() == 0
        assert session_tokens(other_user).count() == 1
        assert PersonalAccessToken.objects.filter(pk=other_pat.pk).exists()

    def test_wrong_old_password_keeps_tokens(self, user):
        create_session_token(user)

        client = APIClient()
        client.force_authenticate(user=user)
        payload = change_password_payload() | {"old_password": "not-the-password"}
        response = client.post(CHANGE_PASSWORD_URL, data=payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.check_password(OLD_PASSWORD)
        assert session_tokens(user).count() == 1

    def test_password_mismatch_keeps_tokens(self, user):
        create_session_token(user)

        client = APIClient()
        client.force_authenticate(user=user)
        payload = change_password_payload() | {"confirm_new_password": "mismatch-1!Aa"}
        response = client.post(CHANGE_PASSWORD_URL, data=payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert session_tokens(user).count() == 1


@pytest.mark.django_db
class TestSetPasswordSessionRevocation:
    def test_revokes_target_session_tokens(self, admin_client, user):
        create_session_token(user)
        create_session_token(user)

        response = admin_client.post(
            SET_PASSWORD_URL, data=set_password_payload(user), format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)
        assert session_tokens(user).count() == 0

    def test_preserves_target_personal_access_tokens(self, admin_client, user):
        pat, _ = create_personal_access_token(user)
        create_session_token(user)

        response = admin_client.post(
            SET_PASSWORD_URL, data=set_password_payload(user), format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert PersonalAccessToken.objects.filter(pk=pat.pk).exists()
        assert AuthToken.objects.filter(pk=pat.auth_token.pk).exists()
        assert session_tokens(user).count() == 0

    def test_keeps_admin_own_tokens(self, admin_client, admin_user, user):
        create_session_token(admin_user)
        create_session_token(user)

        response = admin_client.post(
            SET_PASSWORD_URL, data=set_password_payload(user), format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert session_tokens(admin_user).count() == 1
        assert session_tokens(user).count() == 0

    def test_non_admin_cannot_revoke_tokens(self, user, other_user):
        create_session_token(other_user)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            SET_PASSWORD_URL, data=set_password_payload(other_user), format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        other_user.refresh_from_db()
        assert other_user.check_password(OLD_PASSWORD)
        assert session_tokens(other_user).count() == 1


@pytest.mark.django_db
class TestResetPasswordConfirmSessionRevocation:
    def test_revokes_session_tokens(self, user):
        create_session_token(user)
        create_session_token(user)
        payload = reset_confirm_payload(user)

        response = APIClient().post(
            RESET_PASSWORD_CONFIRM_URL, data=payload, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)
        assert session_tokens(user).count() == 0

    def test_preserves_personal_access_tokens(self, user):
        pat, _ = create_personal_access_token(user)
        create_session_token(user)
        payload = reset_confirm_payload(user)

        response = APIClient().post(
            RESET_PASSWORD_CONFIRM_URL, data=payload, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert PersonalAccessToken.objects.filter(pk=pat.pk).exists()
        assert AuthToken.objects.filter(pk=pat.auth_token.pk).exists()
        assert session_tokens(user).count() == 0

    def test_invalid_reset_token_keeps_tokens(self, user):
        create_session_token(user)
        payload = reset_confirm_payload(user, token="invalid-token")

        response = APIClient().post(
            RESET_PASSWORD_CONFIRM_URL, data=payload, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.check_password(OLD_PASSWORD)
        assert session_tokens(user).count() == 1
