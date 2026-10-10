"""
`/iam/whoami/` tells the frontend's page guard who the caller is, without the cost of
`/iam/current-user/`: it answers with the caller's id and third-party flag only.
"""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from iam.models import User


@pytest.fixture(autouse=True)
def root_folder():
    startup(sender=None)


@pytest.mark.django_db
@pytest.mark.parametrize("is_third_party", [False, True])
def test_whoami_returns_id_and_third_party_flag_only(is_third_party):
    user = User.objects.create_user(
        email=f"whoami-{is_third_party}@whoami.test", is_third_party=is_third_party
    )
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )

    response = client.get("/api/iam/whoami/")

    assert response.status_code == 200
    assert response.json() == {"id": str(user.id), "is_third_party": is_third_party}


@pytest.mark.django_db
def test_whoami_requires_authentication():
    assert APIClient().get("/api/iam/whoami/").status_code == 401
