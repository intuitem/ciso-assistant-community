"""ChangePasswordView used to leave every API token alive, unlike the reset and
admin-set flows which both revoke. A token stolen before the change kept working."""

import pytest
from knox.models import AuthToken

from iam.models import User
from iam.utils import generate_token, revoke_all_user_tokens

pytestmark = pytest.mark.django_db

OLD = "old-pass-phrase-9281"
NEW = "new-pass-phrase-7364"
URL = "/api/iam/change-password/"
WHOAMI = "/api/iam/current-user/"


@pytest.fixture
def user():
    return User.objects.create_user(email="pw@example.invalid", password=OLD)


def test_revoke_keeps_the_excluded_token(user):
    generate_token(user)
    generate_token(user)
    keep = AuthToken.objects.filter(user=user).first()

    revoke_all_user_tokens(user, exclude_token=keep)

    remaining = list(AuthToken.objects.filter(user=user))
    assert [t.pk for t in remaining] == [keep.pk]


def test_revoke_without_exclusion_drops_everything(user):
    generate_token(user)
    generate_token(user)

    revoke_all_user_tokens(user)

    assert not AuthToken.objects.filter(user=user).exists()


def test_changing_password_kills_other_tokens_but_not_the_caller(client, user):
    caller = generate_token(user)
    stolen = generate_token(user)
    assert AuthToken.objects.filter(user=user).count() == 2

    response = client.post(
        URL,
        data={"old_password": OLD, "new_password": NEW, "confirm_new_password": NEW},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Token {caller}",
    )

    assert response.status_code == 200, response.content
    user.refresh_from_db()
    assert user.check_password(NEW)

    # The caller's token is the one still standing.
    assert AuthToken.objects.filter(user=user).count() == 1
    still_works = client.get(WHOAMI, HTTP_AUTHORIZATION=f"Token {caller}")
    assert still_works.status_code == 200, still_works.content
    dead = client.get(WHOAMI, HTTP_AUTHORIZATION=f"Token {stolen}")
    assert dead.status_code == 401, dead.content


def test_a_wrong_old_password_revokes_nothing(client, user):
    caller = generate_token(user)
    generate_token(user)

    response = client.post(
        URL,
        data={
            "old_password": "not-the-password",
            "new_password": NEW,
            "confirm_new_password": NEW,
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Token {caller}",
    )

    assert response.status_code == 400
    assert AuthToken.objects.filter(user=user).count() == 2
    user.refresh_from_db()
    assert user.check_password(OLD)
