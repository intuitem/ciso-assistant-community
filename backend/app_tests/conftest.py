import pytest
from rest_framework.test import APIClient
from api.test_utils import EndpointTestsUtils
from test_vars import GROUPS_PERMISSIONS
from iam.models import User, UserGroup
from core.apps import startup


class Test(dict):
    def __init__(self, *args, **kwargs):
        super(Test, self).__init__(*args, **kwargs)
        self.__dict__ = self


@pytest.fixture
def app_config():
    startup()


@pytest.fixture
def client():
    """Get an unauthenticated client"""
    client = APIClient()
    return client


@pytest.fixture
def authenticated_client(app_config):
    """Get an authenticated client"""
    admin = User.objects.create_superuser("admin@tests.com")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(admin)
    client = APIClient()
    client.force_login(admin)
    return client


@pytest.fixture(params=GROUPS_PERMISSIONS.keys(),
    ids=[GROUPS_PERMISSIONS[key]["name"] for key in GROUPS_PERMISSIONS.keys()]
)
def test(authenticated_client, request) -> Test:
    """Get the elements used by the tests such as client and associated folder"""
    client, folder = EndpointTestsUtils.get_test_client_and_folder(
        authenticated_client, request.param
    )
    return Test(
        {
            "client": client,
            "admin_client": authenticated_client,
            "folder": folder,
            "user_group": request.param,
        }
    )
