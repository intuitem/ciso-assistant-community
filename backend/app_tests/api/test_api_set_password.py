import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from iam.models import UserGroup

User = get_user_model()

SET_PASSWORD_URL = "/api/iam/set-password/"
OLD_PASSWORD = "pw-12345!"
NEW_PASSWORD = "Zq7!vortex-maple"


@pytest.fixture
def admin_user(db):
    admin = User.objects.create_superuser(email="admin@tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin_group.user_set.add(admin)
    return admin


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(email="regular@tests.com", password=OLD_PASSWORD)


@pytest.fixture
def target_user(db):
    return User.objects.create_user(email="target@tests.com", password=OLD_PASSWORD)


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


def _payload(target_user):
    return {
        "user": str(target_user.id),
        "new_password": NEW_PASSWORD,
        "confirm_new_password": NEW_PASSWORD,
    }


@pytest.mark.django_db
class TestSetPasswordView:
    def test_non_admin_cannot_set_another_users_password(
        self, regular_client, target_user
    ):
        response = regular_client.post(
            SET_PASSWORD_URL, data=_payload(target_user), format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target_user.refresh_from_db()
        assert not target_user.check_password(NEW_PASSWORD)
        assert target_user.check_password(OLD_PASSWORD)

    def test_admin_can_set_another_users_password(self, admin_client, target_user):
        response = admin_client.post(
            SET_PASSWORD_URL, data=_payload(target_user), format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        target_user.refresh_from_db()
        assert target_user.check_password(NEW_PASSWORD)

    def test_unauthenticated_request_is_rejected(self, target_user):
        response = APIClient().post(
            SET_PASSWORD_URL, data=_payload(target_user), format="json"
        )

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
        target_user.refresh_from_db()
        assert target_user.check_password(OLD_PASSWORD)
