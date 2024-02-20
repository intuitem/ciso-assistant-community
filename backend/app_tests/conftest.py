import pytest
from rest_framework.test import APIClient
from iam.models import Folder, User, UserGroup
from core.apps import startup


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


@pytest.fixture
def authenticated_client_with_role(app_config, request):
    """Get an authenticated client with a specific role"""
    user = User.objects.create_user("user@tests.com")
    UserGroup.objects.get(name=request.param['role'], folder=Folder.objects.get(name=request.param['folder']).id).user_set.add(user)
    client = APIClient()
    client.force_login(user)
    return client, request.param
