import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.startup import startup
from global_settings.utils import clear_feature_flags_cache
from iam.models import Folder, User, UserGroup


@pytest.fixture(autouse=True)
def _cold_feature_flags_cache():
    """Test-DB rollbacks don't fire post_save, so a flags dict cached by one
    test would otherwise leak into the next; every test starts cold."""
    clear_feature_flags_cache()
    yield


@pytest.fixture
def app_config():
    startup(sender=None, **{})


@pytest.fixture
def admin(app_config):
    admin = User.objects.create_superuser("admin@ee-tests.com")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(admin)
    return admin


@pytest.fixture
def admin_client(admin):
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def domain(app_config):
    """A domain with its builtin IAM groups, as created from the UI."""
    folder = Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="EE test domain",
        content_type=Folder.ContentType.DOMAIN,
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(folder)
    return folder
