"""OAuth 2.0 over SMTP: environment presets, token grants, and the XOAUTH2
step on the SMTP connection, including the retry and the failover path."""

import json
import smtplib
from urllib.parse import parse_qs

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core import mail

from ciso_assistant.mailers import build_mailers, describe
from core import mail_oauth2, mailer
from core.email_backend import EmailBackend

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
HERE = "core.tests.test_mail_oauth2"

MICROSOFT_ENV = {
    "EMAIL_TRANSPORT": "smtp-oauth2",
    "EMAIL_OAUTH2_PROVIDER": "microsoft",
    "EMAIL_OAUTH2_TENANT_ID": "tenant-1",
    "EMAIL_OAUTH2_CLIENT_ID": "client-1",
    "EMAIL_OAUTH2_CLIENT_SECRET": "s3cret",
    "EMAIL_HOST_USER": "noreply@example.com",
}


@pytest.fixture(autouse=True)
def fresh_token_cache():
    mail_oauth2.clear_cache()
    yield
    mail_oauth2.clear_cache()


# --- environment presets ------------------------------------------------------


def test_microsoft_preset_fills_host_scope_and_token_url():
    options = build_mailers(MICROSOFT_ENV)["default"]["OPTIONS"]
    assert (options["host"], options["port"]) == ("smtp.office365.com", 587)
    assert (options["use_tls"], options["use_ssl"]) == (True, False)
    assert options["username"] == "noreply@example.com"
    assert options["password"] is None
    oauth2 = options["oauth2"]
    assert oauth2["grant_type"] == "client_credentials"
    assert oauth2["token_url"] == (
        "https://login.microsoftonline.com/tenant-1/oauth2/v2.0/token"
    )
    assert oauth2["scope"] == "https://outlook.office365.com/.default"
    assert oauth2["user"] == "noreply@example.com"


def test_google_preset_uses_service_account_file(tmp_path):
    account = tmp_path / "sa.json"
    account.write_text("{}")
    options = build_mailers(
        {
            "EMAIL_TRANSPORT": "smtp-oauth2",
            "EMAIL_OAUTH2_PROVIDER": "google",
            "EMAIL_OAUTH2_SERVICE_ACCOUNT_FILE": str(account),
            "EMAIL_HOST_USER": "noreply@example.com",
        }
    )["default"]["OPTIONS"]
    assert (options["host"], options["port"], options["use_tls"]) == (
        "smtp.gmail.com",
        587,
        True,
    )
    oauth2 = options["oauth2"]
    assert oauth2["grant_type"] == "jwt_bearer"
    assert oauth2["token_url"] == "https://oauth2.googleapis.com/token"
    assert oauth2["scope"] == "https://mail.google.com/"
    assert oauth2["service_account_file"] == str(account)


def test_explicit_host_and_port_override_the_preset():
    options = build_mailers(
        {**MICROSOFT_ENV, "EMAIL_HOST": "smtp.example", "EMAIL_PORT": "2525"}
    )["default"]["OPTIONS"]
    assert (options["host"], options["port"]) == ("smtp.example", 2525)


def test_generic_provider_spells_everything_out():
    options = build_mailers(
        {
            "EMAIL_TRANSPORT": "smtp-oauth2",
            "EMAIL_HOST": "smtp.example",
            "EMAIL_HOST_USER": "noreply@example.com",
            "EMAIL_OAUTH2_TOKEN_URL": "https://idp.example/token",
            "EMAIL_OAUTH2_GRANT_TYPE": "refresh_token",
            "EMAIL_OAUTH2_CLIENT_ID": "c",
            "EMAIL_OAUTH2_CLIENT_SECRET": "s",
            "EMAIL_OAUTH2_REFRESH_TOKEN": "r",
            "EMAIL_OAUTH2_SCOPE": "mail",
        }
    )["default"]["OPTIONS"]
    assert options["oauth2"]["provider"] == "generic"
    assert options["oauth2"]["refresh_token"] == "r"
    # No preset: STARTTLS is not assumed.
    assert options["use_tls"] is False


def test_password_transport_is_unchanged_by_default():
    options = build_mailers({"EMAIL_HOST": "smtp.example"})["default"]["OPTIONS"]
    assert "oauth2" not in options


def test_oauth2_rescue_behind_a_password_primary():
    env = {"EMAIL_HOST": "smtp.example"}
    env.update({f"{key}_RESCUE": value for key, value in MICROSOFT_ENV.items()})
    mailers = build_mailers(env)
    assert list(mailers) == ["default", "rescue"]
    assert "oauth2" not in mailers["default"]["OPTIONS"]
    assert mailers["rescue"]["OPTIONS"]["oauth2"]["grant_type"] == "client_credentials"


@pytest.mark.parametrize(
    "env, message",
    [
        ({"EMAIL_TRANSPORT": "carrier-pigeon", "EMAIL_HOST": "x"}, "EMAIL_TRANSPORT"),
        ({**MICROSOFT_ENV, "EMAIL_OAUTH2_PROVIDER": "yahoo"}, "EMAIL_OAUTH2_PROVIDER"),
        (
            {k: v for k, v in MICROSOFT_ENV.items() if k != "EMAIL_OAUTH2_TENANT_ID"},
            "EMAIL_OAUTH2_TENANT_ID",
        ),
        (
            {k: v for k, v in MICROSOFT_ENV.items() if k != "EMAIL_HOST_USER"},
            "EMAIL_HOST_USER",
        ),
        (
            {
                k: v
                for k, v in MICROSOFT_ENV.items()
                if k != "EMAIL_OAUTH2_CLIENT_SECRET"
            },
            "EMAIL_OAUTH2_CLIENT_SECRET",
        ),
        (
            {
                "EMAIL_TRANSPORT": "smtp-oauth2",
                "EMAIL_HOST": "smtp.example",
                "EMAIL_HOST_USER": "u",
                "EMAIL_OAUTH2_TOKEN_URL": "http://idp.example/token",
                "EMAIL_OAUTH2_GRANT_TYPE": "client_credentials",
                "EMAIL_OAUTH2_CLIENT_ID": "c",
                "EMAIL_OAUTH2_CLIENT_SECRET": "s",
            },
            "https",
        ),
        (
            {"EMAIL_TRANSPORT": "smtp-oauth2", "EMAIL_HOST_USER": "u"},
            "EMAIL_HOST",
        ),
    ],
)
def test_unusable_oauth_configuration_stops_startup(env, message):
    with pytest.raises(ValueError, match=message):
        build_mailers(env)


def test_describe_redacts_oauth_secrets():
    lines = describe(build_mailers(MICROSOFT_ENV))
    assert "s3cret" not in lines[0]
    assert "client-1" in lines[0]
    assert "tenant-1" in lines[0]


# --- token grants -------------------------------------------------------------


def make_endpoint(monkeypatch, handler):
    calls = []

    def recording(request):
        calls.append(request)
        return handler(request)

    monkeypatch.setattr(mail_oauth2, "TRANSPORT", httpx.MockTransport(recording))
    return calls


def form(request) -> dict:
    return {key: value[0] for key, value in parse_qs(request.content.decode()).items()}


def issue(token="tok", expires_in=3600):
    return lambda request: httpx.Response(
        200, json={"access_token": token, "expires_in": expires_in}
    )


CLIENT_CREDENTIALS = {
    "grant_type": "client_credentials",
    "token_url": "https://login.example/token",
    "client_id": "c",
    "client_secret": "s",
    "scope": "https://outlook.office365.com/.default",
    "user": "noreply@example.com",
}


def test_client_credentials_grant(monkeypatch):
    calls = make_endpoint(monkeypatch, issue("tok-1", 3600))
    assert mail_oauth2.get_token(CLIENT_CREDENTIALS) == "tok-1"
    assert str(calls[0].url) == "https://login.example/token"
    assert form(calls[0]) == {
        "grant_type": "client_credentials",
        "client_id": "c",
        "client_secret": "s",
        "scope": "https://outlook.office365.com/.default",
    }


def test_refresh_token_grant(monkeypatch):
    calls = make_endpoint(monkeypatch, issue())
    config = {
        **CLIENT_CREDENTIALS,
        "grant_type": "refresh_token",
        "refresh_token": "r",
        "scope": None,
    }
    mail_oauth2.get_token(config)
    assert form(calls[0]) == {
        "grant_type": "refresh_token",
        "client_id": "c",
        "client_secret": "s",
        "refresh_token": "r",
    }


def test_jwt_bearer_grant_signs_an_assertion_for_the_mailbox(monkeypatch, tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    account = tmp_path / "sa.json"
    account.write_text(
        json.dumps({"client_email": "svc@project.iam", "private_key": private_pem})
    )
    calls = make_endpoint(monkeypatch, issue("g-tok"))
    config = {
        "grant_type": "jwt_bearer",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "https://mail.google.com/",
        "service_account_file": str(account),
        "user": "noreply@example.com",
    }
    assert mail_oauth2.get_token(config) == "g-tok"
    payload = form(calls[0])
    assert payload["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
    claims = jwt.decode(
        payload["assertion"],
        public_pem,
        algorithms=["RS256"],
        audience="https://oauth2.googleapis.com/token",
    )
    assert claims["iss"] == "svc@project.iam"
    assert claims["sub"] == "noreply@example.com"
    assert claims["scope"] == "https://mail.google.com/"
    assert claims["exp"] - claims["iat"] == 3600


def test_tokens_are_cached_until_shortly_before_expiry(monkeypatch):
    calls = make_endpoint(monkeypatch, issue("tok", 3600))
    mail_oauth2.get_token(CLIENT_CREDENTIALS)
    mail_oauth2.get_token(CLIENT_CREDENTIALS)
    assert len(calls) == 1
    mail_oauth2.get_token(CLIENT_CREDENTIALS, force_refresh=True)
    assert len(calls) == 2


def test_short_lived_tokens_are_not_cached(monkeypatch):
    calls = make_endpoint(monkeypatch, issue("tok", 30))
    mail_oauth2.get_token(CLIENT_CREDENTIALS)
    mail_oauth2.get_token(CLIENT_CREDENTIALS)
    assert len(calls) == 2


def test_rejected_grant_reports_the_oauth_error(monkeypatch):
    make_endpoint(
        monkeypatch,
        lambda request: httpx.Response(
            400,
            json={"error": "invalid_client", "error_description": "bad secret"},
        ),
    )
    with pytest.raises(mail_oauth2.TokenError, match="400: invalid_client bad secret"):
        mail_oauth2.get_token(CLIENT_CREDENTIALS)


def test_unreachable_endpoint_is_a_token_error(monkeypatch):
    def down(request):
        raise httpx.ConnectError("refused")

    make_endpoint(monkeypatch, down)
    with pytest.raises(mail_oauth2.TokenError, match="unreachable"):
        mail_oauth2.get_token(CLIENT_CREDENTIALS)


def test_missing_access_token_is_a_token_error(monkeypatch):
    make_endpoint(monkeypatch, lambda request: httpx.Response(200, json={"ok": 1}))
    with pytest.raises(mail_oauth2.TokenError, match="no access_token"):
        mail_oauth2.get_token(CLIENT_CREDENTIALS)


def test_unreadable_service_account_file_is_a_token_error(monkeypatch, tmp_path):
    make_endpoint(monkeypatch, issue())
    config = {
        "grant_type": "jwt_bearer",
        "token_url": "https://oauth2.googleapis.com/token",
        "service_account_file": str(tmp_path / "missing.json"),
        "user": "u",
    }
    with pytest.raises(mail_oauth2.TokenError, match="service account file"):
        mail_oauth2.get_token(config)


# --- the XOAUTH2 step on the SMTP connection ---------------------------------


class FakeSMTP:
    """Just enough of smtplib.SMTP for open(): records the AUTH exchange."""

    instances: list = []
    reject: set = set()

    def __init__(self, host, port, local_hostname=None, timeout=None):
        self.host, self.port = host, port
        self.auth_calls = []
        self.closed = False
        FakeSMTP.instances.append(self)

    def starttls(self, context=None):
        self.tls = True

    def ehlo_or_helo_if_needed(self):
        self.ehlo = True

    def auth(self, mechanism, authobject, *, initial_response_ok=True):
        initial = authobject(None)
        self.auth_calls.append((mechanism, initial))
        if any(f"Bearer {token}\x01" in initial for token in FakeSMTP.reject):
            # The server answers the bad token with a challenge, the client
            # sends an empty line, the server closes with 535.
            assert authobject(b'{"status":"401"}') == ""
            raise smtplib.SMTPAuthenticationError(
                535, b"5.7.3 Authentication unsuccessful"
            )
        return 235, b"2.7.0 Authentication successful"

    def quit(self):
        self.closed = True

    def close(self):
        self.closed = True


class FakeSMTPBackend(EmailBackend):
    connection_class = FakeSMTP


@pytest.fixture(autouse=True)
def reset_fake_smtp():
    FakeSMTP.instances = []
    FakeSMTP.reject = set()


@pytest.fixture
def tokens(monkeypatch):
    issued = iter(["tok-1", "tok-2", "tok-3"])
    requests = []

    def fake_get_token(config, *, force_refresh=False):
        requests.append(force_refresh)
        return next(issued)

    monkeypatch.setattr(mail_oauth2, "get_token", fake_get_token)
    return requests


def oauth_backend(**overrides):
    options = {
        "alias": "test",
        "host": "smtp.office365.com",
        "port": 587,
        "username": "noreply@example.com",
        "use_tls": True,
        "oauth2": CLIENT_CREDENTIALS,
    }
    options.update(overrides)
    return FakeSMTPBackend(**options)


def test_open_authenticates_with_xoauth2(tokens):
    backend = oauth_backend(password="ignored")
    assert backend.password is None
    assert backend.open() is True
    connection = FakeSMTP.instances[0]
    assert connection.tls and connection.ehlo
    assert connection.auth_calls == [
        ("XOAUTH2", "user=noreply@example.com\x01auth=Bearer tok-1\x01\x01")
    ]
    assert tokens == [False]
    assert backend.connection is connection


def test_rejected_token_is_retried_once_with_a_fresh_one(tokens):
    FakeSMTP.reject = {"tok-1"}
    backend = oauth_backend()
    assert backend.open() is True
    mechanisms = [call[0] for call in FakeSMTP.instances[0].auth_calls]
    assert mechanisms == ["XOAUTH2", "XOAUTH2"]
    assert tokens == [False, True]


def test_two_rejections_fail_the_open_and_release_the_socket(tokens):
    FakeSMTP.reject = {"tok-1", "tok-2"}
    backend = oauth_backend()
    with pytest.raises(smtplib.SMTPAuthenticationError):
        backend.open()
    assert backend.connection is None
    assert FakeSMTP.instances[0].closed is True


def test_token_endpoint_failure_fails_the_open(monkeypatch):
    def no_token(config, *, force_refresh=False):
        raise mail_oauth2.TokenError("token endpoint answered 400")

    monkeypatch.setattr(mail_oauth2, "get_token", no_token)
    backend = oauth_backend()
    with pytest.raises(mail_oauth2.TokenError):
        backend.open()
    assert backend.connection is None


def test_authentication_failure_fails_over_to_the_rescue_mailer(settings, tokens):
    FakeSMTP.reject = {"tok-1", "tok-2"}
    settings.MAILERS = {
        "default": {
            "BACKEND": f"{HERE}.FakeSMTPBackend",
            "OPTIONS": {
                "host": "smtp.office365.com",
                "port": 587,
                "username": "noreply@example.com",
                "use_tls": True,
                "oauth2": CLIENT_CREDENTIALS,
            },
        },
        "rescue": {"BACKEND": LOCMEM},
    }
    settings.DEFAULT_FROM_EMAIL = "noreply@example.com"
    mailer.send("S", "body", "a@tests.local")
    assert [m.to for m in mail.outbox] == [["a@tests.local"]]
