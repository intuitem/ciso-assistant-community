import json
import time
from unittest.mock import patch

import jwt
import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from knox.models import AuthToken
from rest_framework.test import APIClient

from allauth.socialaccount.models import SocialApp

from core.startup import startup
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from global_settings.models import GlobalSettings
from iam.models import Folder, Role, ServiceAccount, User, UserGroup
from iam.service_accounts import provision_federated_service_account

SA_ENDPOINT = "/api/iam/service-accounts/"

ISSUER = "https://test-idp.example.com/"
SERVER_URL = "https://test-idp.example.com/.well-known/openid-configuration"
JWKS_URL = "https://test-idp.example.com/jwks"
CLIENT_ID = "test-client-id"
KID = "test-key-1"


@pytest.fixture(scope="module")
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = KID
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"
    return private_key, {"keys": [jwk]}


@pytest.fixture
def mocked_idp(rsa_keypair):
    _private_key, jwks_doc = rsa_keypair
    discovery_doc = {
        "issuer": ISSUER,
        "jwks_uri": JWKS_URL,
        "authorization_endpoint": ISSUER + "authorize",
        "token_endpoint": ISSUER + "token",
    }
    calls = {"discovery": 0, "jwks": 0}

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    def fake_get(self, url, *args, **kwargs):
        if url == SERVER_URL:
            calls["discovery"] += 1
            return FakeResponse(discovery_doc)
        if url == JWKS_URL:
            calls["jwks"] += 1
            return FakeResponse(jwks_doc)
        raise requests.RequestException(f"unexpected URL in test: {url}")

    with patch("requests.Session.get", new=fake_get):
        yield calls


@pytest.fixture
def app_config():
    startup(sender=None, **{})
    ff_settings, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    ff_settings.value = {**(ff_settings.value or {}), "service_accounts": True}
    ff_settings.save()


@pytest.fixture
def admin_client(app_config):
    admin = User.objects.create_superuser(
        "admin@federated-sa-tests.com", is_published=True
    )
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def domain_folder(app_config):
    return Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="federated sa test domain",
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.fixture
def social_app(mocked_idp, db):
    return SocialApp.objects.create(
        provider="openid_connect",
        provider_id="test-idp",
        name="Test IdP",
        client_id=CLIENT_ID,
        settings={"server_url": SERVER_URL},
    )


def _view_folder_permission_ids():
    return list(
        Permission.objects.filter(codename="view_folder").values_list("id", flat=True)
    )


def _create_federated_sa(
    admin_client, domain_folder, social_app, subject="worker-1", name="federated-sa"
):
    return admin_client.post(
        SA_ENDPOINT,
        {
            "name": name,
            "description": "federated test account",
            "identity_source": "federated",
            "social_app": str(social_app.id),
            "federated_subject": subject,
            "permissions": _view_folder_permission_ids(),
            "folders": [str(domain_folder.id)],
        },
        format="json",
    )


def _mint_jwt(
    private_key, *, aud=CLIENT_ID, sub="worker-1", exp_delta=3600, kid=KID, jti=None
):
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": aud,
        "sub": sub,
        "iat": now,
        "exp": now + exp_delta,
    }
    # jti is optional in OIDC; default one so tests can opt out with jti=False.
    if jti is not False:
        claims["jti"] = jti or "test-jti"
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


def _bearer_client(access_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    return client


@pytest.mark.django_db
class TestFederatedProvisioning:
    def test_create_federated_account_no_secret(
        self, admin_client, domain_folder, social_app
    ):
        response = _create_federated_sa(admin_client, domain_folder, social_app)
        assert response.status_code == 201, response.content
        payload = response.json()
        assert payload["identity_source"] == "federated"
        assert payload["federated_subject"] == "worker-1"
        assert payload["social_app"]["id"] == social_app.id
        assert "client_secret" not in payload

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.client is None
        assert sa.social_app_id == social_app.id
        assert set(sa.role.permissions.values_list("codename", flat=True)) == {
            "view_folder"
        }

    def test_create_federated_requires_social_app_and_subject(
        self, admin_client, domain_folder
    ):
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "incomplete",
                "identity_source": "federated",
                "permissions": _view_folder_permission_ids(),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 400

    def test_local_forbids_social_app_fields(
        self, admin_client, domain_folder, social_app
    ):
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "bad-local",
                "identity_source": "local",
                "social_app": str(social_app.id),
                "federated_subject": "x",
                "permissions": _view_folder_permission_ids(),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 400

    def test_duplicate_social_app_subject_rejected(
        self, admin_client, domain_folder, social_app
    ):
        first = _create_federated_sa(admin_client, domain_folder, social_app)
        assert first.status_code == 201, first.content
        second = _create_federated_sa(
            admin_client, domain_folder, social_app, name="federated-sa-2"
        )
        assert second.status_code == 400

    def test_live_check_fails_closed_on_unreachable_idp(
        self, admin_client, domain_folder, mocked_idp, db
    ):
        broken_app = SocialApp.objects.create(
            provider="openid_connect",
            provider_id="broken-idp",
            name="Broken IdP",
            client_id="broken-client-id",
            settings={
                "server_url": "https://unreachable.example.invalid/.well-known/openid-configuration"
            },
        )
        response = _create_federated_sa(
            admin_client, domain_folder, broken_app, name="broken-sa"
        )
        assert response.status_code == 400
        assert not ServiceAccount.objects.filter(name="broken-sa").exists()

    def test_identity_source_immutable_after_creation(
        self, admin_client, domain_folder, social_app
    ):
        payload = _create_federated_sa(admin_client, domain_folder, social_app).json()
        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"identity_source": "local"},
            format="json",
        )
        assert response.status_code == 400

    def test_federated_subject_can_be_changed(
        self, admin_client, domain_folder, social_app, mocked_idp
    ):
        payload = _create_federated_sa(admin_client, domain_folder, social_app).json()
        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"federated_subject": "worker-2"},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["federated_subject"] == "worker-2"
        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.federated_subject == "worker-2"

    def test_social_app_can_be_repointed(
        self, admin_client, domain_folder, social_app, mocked_idp
    ):
        other_app = SocialApp.objects.create(
            provider="openid_connect",
            provider_id="test-idp-2",
            name="Test IdP 2",
            client_id="other-client-id",
            settings={"server_url": SERVER_URL},
        )
        payload = _create_federated_sa(admin_client, domain_folder, social_app).json()
        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"social_app": str(other_app.id)},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["social_app"]["id"] == other_app.id
        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.social_app_id == other_app.id
        # subject is unchanged - only the provider was re-pointed.
        assert sa.federated_subject == "worker-1"

    def test_repoint_rejects_duplicate_pair(
        self, admin_client, domain_folder, social_app, mocked_idp
    ):
        first = _create_federated_sa(admin_client, domain_folder, social_app).json()
        second = _create_federated_sa(
            admin_client, domain_folder, social_app, subject="worker-2", name="sa-2"
        ).json()
        response = admin_client.patch(
            f"{SA_ENDPOINT}{second['id']}/",
            {"federated_subject": "worker-1"},
            format="json",
        )
        assert response.status_code == 400, response.content
        sa = ServiceAccount.objects.get(id=second["id"])
        assert sa.federated_subject == "worker-2"

    def test_local_account_forbids_federation_field_updates(
        self, admin_client, domain_folder
    ):
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "local-sa",
                "identity_source": "local",
                "permissions": _view_folder_permission_ids(),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        sa_id = response.json()["id"]
        patch_response = admin_client.patch(
            f"{SA_ENDPOINT}{sa_id}/",
            {"federated_subject": "worker-1"},
            format="json",
        )
        assert patch_response.status_code == 400, patch_response.content

    def test_rotate_secret_rejected_for_federated(
        self, admin_client, domain_folder, social_app
    ):
        payload = _create_federated_sa(admin_client, domain_folder, social_app).json()
        response = admin_client.post(
            f"{SA_ENDPOINT}{payload['id']}/rotate-secret/", format="json"
        )
        assert response.status_code == 400

    def test_concurrent_duplicate_maps_to_validation_error(
        self, domain_folder, social_app, mocked_idp
    ):
        """Simulates two requests racing past the .exists() pre-check: the
        first commits, the second must still get a clean ValidationError from
        the real unique_together constraint, not a bare IntegrityError/500."""
        kwargs = dict(
            description=None,
            permission_ids=_view_folder_permission_ids(),
            role_id=None,
            folder_ids=[domain_folder.id],
            is_recursive=False,
            created_by=None,
            social_app=social_app,
            federated_subject="worker-1",
        )
        provision_federated_service_account(name="first-sa", **kwargs)

        with patch(
            "iam.service_accounts.ServiceAccount.objects.filter"
        ) as mocked_filter:
            mocked_filter.return_value.exists.side_effect = [False, True]
            with pytest.raises(ValidationError, match="already registered"):
                provision_federated_service_account(name="second-sa", **kwargs)


@pytest.mark.django_db
class TestFederatedAuthentication:
    def test_valid_bearer_token_authenticates_and_scopes_access(
        self, admin_client, domain_folder, social_app, rsa_keypair, mocked_idp
    ):
        private_key, _ = rsa_keypair
        _create_federated_sa(admin_client, domain_folder, social_app)

        other_domain = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="unreachable federated domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        token = _mint_jwt(private_key)
        bearer = _bearer_client(token)
        response = bearer.get("/api/folders/")
        assert response.status_code == 200, response.content
        folder_ids = {row["id"] for row in response.json()["results"]}
        assert str(domain_folder.id) in folder_ids
        assert str(other_domain.id) not in folder_ids

        response = bearer.post(
            "/api/folders/",
            {"name": "sa-created", "parent_folder": str(domain_folder.id)},
            format="json",
        )
        assert response.status_code == 403

    def test_same_token_reusable_across_multiple_requests(
        self, admin_client, domain_folder, social_app, rsa_keypair, mocked_idp
    ):
        """A client_credentials bearer token is reused for many requests until
        it expires — it must not be treated as single-use like an id_token."""
        private_key, _ = rsa_keypair
        _create_federated_sa(admin_client, domain_folder, social_app)
        token = _mint_jwt(private_key, jti="reused-jti")
        bearer = _bearer_client(token)
        for _ in range(3):
            assert bearer.get("/api/folders/").status_code == 200

    def test_jwks_and_discovery_are_cached_across_requests(
        self, admin_client, domain_folder, social_app, rsa_keypair, mocked_idp
    ):
        private_key, _ = rsa_keypair
        _create_federated_sa(admin_client, domain_folder, social_app)
        discovery_calls_after_create = mocked_idp["discovery"]
        jwks_calls_after_create = mocked_idp["jwks"]

        token = _mint_jwt(private_key)
        for _ in range(3):
            response = _bearer_client(token).get("/api/folders/")
            assert response.status_code == 200

        assert mocked_idp["discovery"] == discovery_calls_after_create
        assert mocked_idp["jwks"] == jwks_calls_after_create

    def test_token_missing_exp_rejected(
        self, admin_client, domain_folder, social_app, rsa_keypair, mocked_idp
    ):
        """PyJWT only checks 'exp' if the claim is present, so a token that
        omits it entirely must be rejected explicitly, not treated as non-expiring."""
        private_key, _ = rsa_keypair
        _create_federated_sa(admin_client, domain_folder, social_app)
        claims = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "worker-1",
            "iat": int(time.time()),
        }
        token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": KID})
        response = _bearer_client(token).get("/api/folders/")
        assert response.status_code == 401

    def test_unknown_kid_refresh_is_rate_limited_per_provider(
        self, admin_client, domain_folder, social_app, rsa_keypair, mocked_idp
    ):
        """Rotating 'kid' values must not each force a live JWKS refetch."""
        private_key, _ = rsa_keypair
        _create_federated_sa(admin_client, domain_folder, social_app)
        jwks_calls_after_create = mocked_idp["jwks"]

        for i in range(5):
            token = _mint_jwt(private_key, kid=f"bogus-kid-{i}")
            response = _bearer_client(token).get("/api/folders/")
            assert response.status_code == 401

        assert mocked_idp["jwks"] - jwks_calls_after_create == 1

    def test_wrong_subject_rejected(
        self, admin_client, domain_folder, social_app, rsa_keypair, mocked_idp
    ):
        private_key, _ = rsa_keypair
        _create_federated_sa(
            admin_client, domain_folder, social_app, subject="worker-1"
        )
        token = _mint_jwt(private_key, sub="someone-else")
        response = _bearer_client(token).get("/api/folders/")
        assert response.status_code == 401

    def test_unregistered_audience_falls_through_unauthenticated(
        self, admin_client, domain_folder, social_app, rsa_keypair, mocked_idp
    ):
        private_key, _ = rsa_keypair
        _create_federated_sa(admin_client, domain_folder, social_app)
        token = _mint_jwt(private_key, aud="some-other-client-id")
        response = _bearer_client(token).get("/api/folders/")
        assert response.status_code == 401

    def test_expired_token_rejected(
        self, admin_client, domain_folder, social_app, rsa_keypair, mocked_idp
    ):
        private_key, _ = rsa_keypair
        _create_federated_sa(admin_client, domain_folder, social_app)
        token = _mint_jwt(private_key, exp_delta=-60)
        response = _bearer_client(token).get("/api/folders/")
        assert response.status_code == 401

    def test_wrong_signing_key_rejected(
        self, admin_client, domain_folder, social_app, mocked_idp
    ):
        _create_federated_sa(admin_client, domain_folder, social_app)
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = _mint_jwt(other_key)
        response = _bearer_client(token).get("/api/folders/")
        assert response.status_code == 401

    def test_deactivated_account_rejected(
        self, admin_client, domain_folder, social_app, rsa_keypair, mocked_idp
    ):
        private_key, _ = rsa_keypair
        payload = _create_federated_sa(admin_client, domain_folder, social_app).json()
        token = _mint_jwt(private_key)
        assert _bearer_client(token).get("/api/folders/").status_code == 200

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/", {"is_active": False}, format="json"
        )
        assert response.status_code == 200
        assert _bearer_client(token).get("/api/folders/").status_code == 401

    def test_local_bearer_tokens_unaffected_by_federated_authenticator(
        self, admin_client, domain_folder
    ):
        response = _bearer_client("not-a-jwt-at-all").get("/api/folders/")
        assert response.status_code == 401

    def test_second_subject_on_shared_social_app_authenticates(
        self, admin_client, domain_folder, social_app, rsa_keypair, mocked_idp
    ):
        private_key, _ = rsa_keypair
        _create_federated_sa(
            admin_client, domain_folder, social_app, subject="worker-1", name="sa-1"
        )
        _create_federated_sa(
            admin_client, domain_folder, social_app, subject="worker-2", name="sa-2"
        )

        token = _mint_jwt(private_key, sub="worker-2")
        response = _bearer_client(token).get("/api/folders/")
        assert response.status_code == 200, response.content


@pytest.mark.django_db
class TestFederatedRoleLinked:
    def _reader_role(self):
        return Role.objects.get(name="BI-RL-AUD", builtin=True)

    def test_create_with_role_links_live_permissions(
        self, admin_client, domain_folder, social_app
    ):
        role = self._reader_role()
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "federated-role-linked",
                "identity_source": "federated",
                "social_app": str(social_app.id),
                "federated_subject": "worker-1",
                "role": str(role.id),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        payload = response.json()
        assert payload["is_role_linked"] is True

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.role_id == role.id

    def test_switch_from_custom_to_role_on_update(
        self, admin_client, domain_folder, social_app
    ):
        payload = _create_federated_sa(admin_client, domain_folder, social_app).json()
        role = self._reader_role()

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"role": str(role.id)},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["is_role_linked"] is True

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.role_id == role.id
