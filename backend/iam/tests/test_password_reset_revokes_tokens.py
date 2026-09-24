import base64

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from knox.models import AuthToken
from rest_framework.test import APIClient

from iam.models import PersonalAccessToken
from iam.utils import revoke_all_user_tokens

User = get_user_model()
PW = "correct-horse-battery-staple-9"


def _seed_tokens(user):
    AuthToken.objects.create(user=user)  # a session token
    instance = AuthToken.objects.create(user=user)[0]  # a PAT-backed token
    PersonalAccessToken.objects.create(auth_token=instance, name="ci")


@pytest.mark.django_db
class TestPasswordResetRevokesTokens:
    def test_helper_revokes_all_tokens_including_pats(self):
        user = User.objects.create_user(email="u@example.com", password=PW)
        _seed_tokens(user)
        assert AuthToken.objects.filter(user=user).count() == 2
        revoke_all_user_tokens(user)
        assert AuthToken.objects.filter(user=user).count() == 0

    def test_reset_confirm_revokes_all_sessions(self):
        user = User.objects.create_user(email="v@example.com", password=PW)
        _seed_tokens(user)

        uidb64 = base64.urlsafe_b64encode(str(user.pk).encode()).decode()
        token = PasswordResetTokenGenerator().make_token(user)
        resp = APIClient().post(
            "/api/iam/password-reset/confirm/",
            {
                "uidb64": uidb64,
                "token": token,
                "new_password": PW + "-new",
                "confirm_new_password": PW + "-new",
            },
            format="json",
        )
        assert resp.status_code == 200
        assert AuthToken.objects.filter(user=user).count() == 0
