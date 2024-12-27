import pytest
from rest_framework.test import APIClient
from api.test_utils import EndpointTestsUtils
from test_vars import GROUPS_PERMISSIONS
from iam.models import User, UserGroup
from core.apps import startup
from knox.models import AuthToken


class Test(dict):
    def __init__(self, *args, **kwargs):
        super(Test, self).__init__(*args, **kwargs)
        self.__dict__ = self


@pytest.fixture
def app_config():
    startup(sender=None, **{})


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
    _auth_token = AuthToken.objects.create(user=admin)
    auth_token = _auth_token[1]
    client.credentials(HTTP_AUTHORIZATION=f"Token {auth_token}")
    return client


@pytest.fixture(
    params=[
        (role, folder)
        for role in GROUPS_PERMISSIONS.keys()
        for folder in ["test", "test_outside_domain"]
    ],
    ids=[
        GROUPS_PERMISSIONS[key]["name"] + folder_name
        for key in GROUPS_PERMISSIONS.keys()
        for folder_name in ["", "_outside_domain"]
    ],
)
def test(authenticated_client, request) -> Test:
    """Get the elements used by the tests such as client and associated folder"""
    client, folder, assigned_folder = EndpointTestsUtils.get_test_client_and_folder(
        authenticated_client, request.param[0], request.param[1]
    )
    return Test(
        {
            "client": client,
            "admin_client": authenticated_client,
            "folder": folder,
            "assigned_folder": assigned_folder,
            "user_group": request.param[0],
        }
    )
