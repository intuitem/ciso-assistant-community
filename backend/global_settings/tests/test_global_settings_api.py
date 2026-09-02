from dataclasses import dataclass, field
from typing import Final, Literal
import json

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient
from django.conf import settings

from core.apps import startup
from iam.models import Folder, Role, RoleAssignment, User, UserGroup

ENABLE_INFRA_CONFIG_MANAGEMENT: Final[bool] = getattr(
    settings, "ENABLE_INFRA_CONFIG_MANAGEMENT", False
)


@dataclass(frozen=True)
class ExpectedResponse:
    """Represent the shape of the HTTP response expected after querying the `endpoint` HTTP endpoint."""

    verb: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    """HTTP Verb the HTTP request will use."""
    endpoint: str
    """Endpoint the HTTP request will be sent to (e.g. `/api/iam/current-user`)"""
    status_code: int
    """Represent the HTTP status code we expect the API to return in the response."""
    reason: str
    """The reason why we expect the `self.status_code` HTTP status code in the response."""
    data: dict = field(default_factory=dict)
    """JSON data(payload) sent in the HTTP request (for POST/PATCH/PUT HTTP requests)."""

    def run_check(self, client: APIClient):
        """Send an HTTP request and check(`assert`) if the HTTP response status code is the same as the `self.status_code` (as the status code we expected)."""

        data = json.dumps(self.data)
        if self.verb in ["GET", "DELETE"]:
            data = ""

        response = client.generic(
            self.verb,
            self.endpoint,
            data=data,
            content_type="application/json",
        )

        error_message = f"Expected status code {self.status_code}, got {response.status_code} (for {self.verb} {self.endpoint}) reason: {self.reason}"

        assert response.status_code == self.status_code, error_message


class Reason:
    """Used to store reusable `ExpectedResponse.reason` reasons (strings)."""

    NO_GLOBAL_SETTINGS_GENERIC_VIEWSET = "There shouldn't be a generic GlobalSettings ViewSet as there's no reason to perform operation on mutliple one at once."
    NO_NEED_FOR_STANDARD_USER_READ = "There's no need for users (beside admin loading the settings edition form) from reading these settings."
    ITS_OPEN_SOURCE_ANYWAY = "The data returned by this endpoint can be known by anyone as the application is open-source anyway."
    SENSITIVE_SETTINGS = "This kind of settings is considered sensitive, so we don't want anyone to see it except the admin."
    NON_SENSITIVE_SETTINGS = "These settings aren't sensitive and can be usefull to users, so any user can read it."
    NON_SENSITIVE_DATA = "The data returned by this endpoint is considered as non-sensitive so we don't hide them from users."
    NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS = "Only an admin SHALL be able to change any kind of global settings (A non-admin user SHALL NOT be able to do it)"
    SETTINGS_ARE_NOT_DELETABLE = (
        "GlobalSettings MUST NOT be deletable by anyone (including admins)."
    )
    # Creating a `GlobalSettings` doesn't make sense as they are already created at startup and can't have duplicates.
    # (Even if it was allowed, creating a new `GlobalSettings` would fail anyway because it would violate the the UNIQUE constraint on the `GlobalSettings.name` field).
    SETTINGS_ARE_NOT_CREATABLE = (
        "GlobalSettings MUST NOT be creatable by anyone (including admins)."
    )


NON_ADMIN_EXPECTED_RESPONSES: Final[list[ExpectedResponse]] = [
    ExpectedResponse(
        "GET", "/api/settings/", 404, Reason.NO_GLOBAL_SETTINGS_GENERIC_VIEWSET
    ),
    ExpectedResponse(
        "GET", "/api/settings/global/", 404, Reason.NO_GLOBAL_SETTINGS_GENERIC_VIEWSET
    ),
    ExpectedResponse(
        "GET", "/api/settings/general/", 200, Reason.NON_SENSITIVE_SETTINGS
    ),
    ExpectedResponse(
        "POST", "/api/settings/general/", 405, Reason.SETTINGS_ARE_NOT_CREATABLE
    ),
    ExpectedResponse(
        "PUT",
        "/api/settings/general/",
        403,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
        data={"value": {}},
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/general/",
        403,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
        data={"value": {}},
    ),
    ExpectedResponse(
        "GET", "/api/settings/general/object/", 200, Reason.NON_SENSITIVE_SETTINGS
    ),
    ExpectedResponse(
        "GET", "/api/settings/general/default_language/", 200, Reason.NON_SENSITIVE_DATA
    ),
    ExpectedResponse(
        "POST",
        "/api/settings/general/set-default-dashboard/",
        403,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    # We don't test: GET "/api/settings/general/default_custom_analytics_dashboard/" because it has no relation to `GlobalSettings``.
    # We don't test: POST "/api/settings/general/force_language/" because it's purely about `User` objects (not related to `GlobalSettings`).
    ExpectedResponse(
        "GET",
        "/api/settings/general/security_objective_scale/",
        200,
        Reason.ITS_OPEN_SOURCE_ANYWAY,
    ),
    ExpectedResponse(
        "GET",
        "/api/settings/general/ebios_radar_parameters/",
        200,
        Reason.NON_SENSITIVE_SETTINGS,
    ),
    ExpectedResponse(
        "GET",
        "/api/settings/general/notifications_settings/",
        200,
        Reason.NON_SENSITIVE_SETTINGS,
    ),
    ExpectedResponse(
        "GET",
        "/api/settings/general/interface_settings/",
        200,
        Reason.NON_SENSITIVE_SETTINGS,
    ),
    ExpectedResponse(
        "GET", "/api/settings/feature-flags/", 200, Reason.NON_SENSITIVE_SETTINGS
    ),
    ExpectedResponse(
        "POST", "/api/settings/feature-flags/", 405, Reason.SETTINGS_ARE_NOT_CREATABLE
    ),
    ExpectedResponse(
        "PUT",
        "/api/settings/feature-flags/",
        403,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/feature-flags/",
        403,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "DELETE", "/api/settings/feature-flags/", 405, Reason.SETTINGS_ARE_NOT_DELETABLE
    ),
    ExpectedResponse(
        "GET",
        "/api/settings/feature-flags/defaults/",
        200,
        Reason.ITS_OPEN_SOURCE_ANYWAY,
    ),
    ExpectedResponse(
        "GET",
        "/api/settings/vulnerability-sla/",
        403,
        Reason.NO_NEED_FOR_STANDARD_USER_READ,
    ),
    ExpectedResponse(
        "POST",
        "/api/settings/vulnerability-sla/",
        405,
        Reason.SETTINGS_ARE_NOT_CREATABLE,
    ),
    ExpectedResponse(
        "PUT",
        "/api/settings/vulnerability-sla/",
        403,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/vulnerability-sla/",
        403,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "DELETE",
        "/api/settings/vulnerability-sla/",
        405,
        Reason.SETTINGS_ARE_NOT_DELETABLE,
    ),
    ExpectedResponse(
        "GET",
        "/api/settings/sec-intel-feeds/",
        403,
        Reason.NO_NEED_FOR_STANDARD_USER_READ,
    ),
    ExpectedResponse(
        "POST", "/api/settings/sec-intel-feeds/", 405, Reason.SETTINGS_ARE_NOT_CREATABLE
    ),
    ExpectedResponse(
        "PUT",
        "/api/settings/sec-intel-feeds/",
        403,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/sec-intel-feeds/",
        403,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "DELETE",
        "/api/settings/sec-intel-feeds/",
        405,
        Reason.SETTINGS_ARE_NOT_DELETABLE,
    ),
    ExpectedResponse(
        "GET",
        "/api/settings/infra-config/",
        403 if ENABLE_INFRA_CONFIG_MANAGEMENT else 404,
        Reason.SENSITIVE_SETTINGS,
    ),
    ExpectedResponse(
        "POST",
        "/api/settings/infra-config/",
        405 if ENABLE_INFRA_CONFIG_MANAGEMENT else 404,
        Reason.SETTINGS_ARE_NOT_CREATABLE,
    ),
    ExpectedResponse(
        "PUT",
        "/api/settings/infra-config/",
        403 if ENABLE_INFRA_CONFIG_MANAGEMENT else 404,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/infra-config/",
        403 if ENABLE_INFRA_CONFIG_MANAGEMENT else 404,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "DELETE",
        "/api/settings/infra-config/",
        405 if ENABLE_INFRA_CONFIG_MANAGEMENT else 404,
        Reason.SETTINGS_ARE_NOT_DELETABLE,
    ),
    ExpectedResponse("GET", "/api/settings/sso/", 403, Reason.SENSITIVE_SETTINGS),
    ExpectedResponse(
        "POST", "/api/settings/sso/", 405, Reason.SETTINGS_ARE_NOT_CREATABLE
    ),
    ExpectedResponse(
        "PUT", "/api/settings/sso/", 403, Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS
    ),
    ExpectedResponse(
        "PATCH", "/api/settings/sso/", 403, Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS
    ),
    ExpectedResponse(
        "DELETE", "/api/settings/sso/", 405, Reason.SETTINGS_ARE_NOT_DELETABLE
    ),
    ExpectedResponse(
        "GET", "/api/settings/sso/provider/", 200, Reason.NON_SENSITIVE_DATA
    ),
    ExpectedResponse(
        "GET", "/api/settings/sso/object/", 403, Reason.SENSITIVE_SETTINGS
    ),
]

# The `ExpectedResponse` in this list overwrite the ones in `NON_ADMIN_EXPECTED_RESPONSES` for the admin user test.
# An `ExpectedResponse` in this list overwrite one in `NON_ADMIN_EXPECTED_RESPONSES` IF they both have the same `(verb, endpoint)` pair.
ADMIN_OVERWRITE_EXPECTED_RESPONSES: Final[list[ExpectedResponse]] = [
    ExpectedResponse(
        "PUT",
        "/api/settings/general/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
        data={"value": {}},
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/general/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
        data={"value": {}},
    ),
    ExpectedResponse(
        "POST",
        "/api/settings/general/set-default-dashboard/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "PUT",
        "/api/settings/feature-flags/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/feature-flags/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "GET",
        "/api/settings/vulnerability-sla/",
        200,
        Reason.NO_NEED_FOR_STANDARD_USER_READ,
    ),
    ExpectedResponse(
        "PUT",
        "/api/settings/vulnerability-sla/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/vulnerability-sla/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "GET",
        "/api/settings/sec-intel-feeds/",
        200,
        Reason.NO_NEED_FOR_STANDARD_USER_READ,
    ),
    ExpectedResponse(
        "PUT",
        "/api/settings/sec-intel-feeds/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/sec-intel-feeds/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "GET",
        "/api/settings/infra-config/",
        200 if ENABLE_INFRA_CONFIG_MANAGEMENT else 404,
        Reason.SENSITIVE_SETTINGS,
    ),
    ExpectedResponse(
        "PUT",
        "/api/settings/infra-config/",
        200 if ENABLE_INFRA_CONFIG_MANAGEMENT else 404,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/infra-config/",
        200 if ENABLE_INFRA_CONFIG_MANAGEMENT else 404,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
    ),
    ExpectedResponse("GET", "/api/settings/sso/", 200, Reason.SENSITIVE_SETTINGS),
    ExpectedResponse(
        "PUT",
        "/api/settings/sso/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
        data={"authn_request_signed": False},
    ),
    ExpectedResponse(
        "PATCH",
        "/api/settings/sso/",
        200,
        Reason.NON_ADMIN_SHALL_NOT_CHANGE_SETTINGS,
        data={"authn_request_signed": False},
    ),
    ExpectedResponse(
        "GET", "/api/settings/sso/object/", 200, Reason.SENSITIVE_SETTINGS
    ),
]

ADMIN_EXPECTED_RESPONSES = list(
    (
        {
            **{
                (response.verb, response.endpoint): response
                for response in NON_ADMIN_EXPECTED_RESPONSES
            },
            **{
                (response.verb, response.endpoint): response
                for response in ADMIN_OVERWRITE_EXPECTED_RESPONSES
            },
        }
    ).values()
)


@pytest.fixture
def app_config():
    startup(sender=None, **{})


def create_api_client_from_role(role: Role, folder: Folder) -> APIClient:
    user = User.objects.create_user(email=f"{role.name}@wow.com")
    group = UserGroup.objects.create(name=f"global_settings{role.name}", folder=folder)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=role,
        folder=folder,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(folder)
    group.user_set.add(user)

    client = APIClient()
    token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def domain(app_config):
    return Folder.objects.create(
        name="sso-perm-tests-domain",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.fixture
def reader_client(domain):
    role = Role.objects.get(name="BI-RL-AUD")
    return create_api_client_from_role(role, domain)


@pytest.fixture
def domain_manager_client(domain):
    role = Role.objects.get(name="BI-RL-DMA")
    return create_api_client_from_role(role, domain)


@pytest.fixture
def admin_client(app_config):
    role = Role.objects.get(name="BI-RL-ADM")
    return create_api_client_from_role(role, Folder.get_root_folder())


@pytest.mark.django_db
class TestGlobalSettingsAPIAccess:
    def test_reader_global_settings_access(self, reader_client):
        for expected_response in NON_ADMIN_EXPECTED_RESPONSES:
            expected_response.run_check(reader_client)

    def test_domain_manager_global_settings_access(self, domain_manager_client):
        # We use `NON_ADMIN_EXPECTED_RESPONSES` for both the `domain_manager_client` and `reader_client` as there should be no difference between a "reader" and a "domain manager" when it comes to `GlobalSettings`` permissions.
        for expected_response in NON_ADMIN_EXPECTED_RESPONSES:
            expected_response.run_check(domain_manager_client)

    def test_admin_global_settings_access(self, admin_client):
        for expected_response in ADMIN_EXPECTED_RESPONSES:
            expected_response.run_check(admin_client)
