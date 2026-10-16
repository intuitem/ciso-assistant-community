"""Custom mailer settings: routing by the stored configuration, the API with
its test-before-save rule, change notifications, and delivery health."""

import importlib

import pytest
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.locmem import EmailBackend as LocmemBackend
from django.urls import NoReverseMatch, clear_url_caches, reverse
from rest_framework.test import APIClient

from core import mailer
from global_settings.models import Mailer, MailerConfiguration, MailerHealth
from iam.models import User

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

pytestmark = pytest.mark.django_db


class RefusingBackend(BaseEmailBackend):
    def open(self):
        raise ConnectionRefusedError("connection refused")

    def send_messages(self, email_messages):
        raise AssertionError("never asked to send")


@pytest.fixture
def fake_smtp(monkeypatch):
    """Custom mailer rows always name the real SMTP backend; map two test
    hosts to in-memory stand-ins so the API tests never open a socket."""
    original = mailer.MailerSpec.build

    def build(spec):
        host = spec.options.get("host")
        if host == "locmem.test":
            return LocmemBackend(alias=spec.alias)
        if host == "refused.test":
            return RefusingBackend(alias=spec.alias)
        return original(spec)

    monkeypatch.setattr(mailer.MailerSpec, "build", build)


def _reload_urls():
    # The router registers the route at import time depending on the switch;
    # rebuild the whole include chain so reverse() sees the change.
    import ciso_assistant.urls
    import core.urls
    import global_settings.urls

    importlib.reload(global_settings.urls)
    importlib.reload(core.urls)
    importlib.reload(ciso_assistant.urls)
    clear_url_caches()


@pytest.fixture
def switch_on(settings):
    settings.ENABLE_CUSTOM_MAILER = True
    # The test hosts do not resolve; the network policy has its own tests.
    settings.ALLOW_PRIVATE_NETWORK_REQUESTS = True
    settings.MAILERS = {"default": {"BACKEND": LOCMEM}}
    settings.DEFAULT_FROM_EMAIL = "env@tests.local"
    _reload_urls()
    yield
    settings.ENABLE_CUSTOM_MAILER = False
    _reload_urls()


@pytest.fixture
def admin():
    return User.objects.create_superuser(email="admin@tests.local", password="pw")


@pytest.fixture
def other_admin():
    return User.objects.create_superuser(email="other@tests.local", password="pw")


@pytest.fixture
def client(admin):
    client = APIClient()
    client.force_authenticate(admin)
    return client


def payload(host="locmem.test", **overrides):
    data = {
        "is_active": True,
        "from_email": "hello@example.com",
        "mailers": [
            {
                "position": 1,
                "transport": "smtp",
                "host": host,
                "port": 587,
                "use_tls": True,
                "use_ssl": False,
                "username": "hello@example.com",
                "password": "pw",
            }
        ],
    }
    data.update(overrides)
    return data


def url(name="mailer-settings-detail"):
    return reverse(name)


# --- the switch ---------------------------------------------------------------


def test_routes_do_not_exist_when_the_switch_is_off(settings):
    settings.ENABLE_CUSTOM_MAILER = False
    _reload_urls()
    with pytest.raises(NoReverseMatch):
        reverse("mailer-settings-detail")


def test_stored_configuration_is_ignored_when_the_switch_is_off(settings, fake_smtp):
    settings.ENABLE_CUSTOM_MAILER = False
    settings.MAILERS = {"default": {"BACKEND": LOCMEM}}
    configuration = MailerConfiguration.get()
    configuration.is_active = True
    configuration.from_email = "hello@example.com"
    configuration.save()
    Mailer.objects.create(configuration=configuration, position=1, host="locmem.test")
    assert [spec.alias for spec in mailer.active_mailers()] == ["default"]


# --- routing -----------------------------------------------------------------


def test_active_configuration_replaces_the_environment(switch_on, fake_smtp):
    configuration = MailerConfiguration.get()
    configuration.is_active = True
    configuration.from_email = "hello@example.com"
    configuration.save()
    Mailer.objects.create(configuration=configuration, position=1, host="refused.test")
    Mailer.objects.create(configuration=configuration, position=2, host="locmem.test")

    assert [spec.alias for spec in mailer.active_mailers()] == ["custom-1", "custom-2"]
    assert mailer.sender_address() == "hello@example.com"
    mailer.send("S", "b", "a@tests.local")
    assert mail.outbox[0].from_email == "hello@example.com"
    health = {row.alias: row for row in MailerHealth.objects.all()}
    assert health["custom-1"].last_outcome == "unreachable"
    assert health["custom-2"].last_outcome == "ok"
    assert health["custom-2"].via_failover is True
    assert health["custom-2"].source == "custom"


def test_parked_configuration_falls_back_to_the_environment(switch_on, fake_smtp):
    configuration = MailerConfiguration.get()
    configuration.is_active = False
    configuration.from_email = "hello@example.com"
    configuration.save()
    Mailer.objects.create(configuration=configuration, position=1, host="locmem.test")
    assert [spec.alias for spec in mailer.active_mailers()] == ["default"]
    assert mailer.sender_address() == "env@tests.local"


def test_environment_mailers_record_health_too(switch_on):
    mailer.send("S", "b", "a@tests.local")
    row = MailerHealth.objects.get(alias="default")
    assert (row.source, row.last_outcome, row.via_failover) == (
        "environment",
        "ok",
        False,
    )
    assert row.last_success_at is not None


# --- the API -----------------------------------------------------------------


def test_reading_requires_the_permission(switch_on):
    user = User.objects.create_user(email="nobody@tests.local", password="pw")
    client = APIClient()
    client.force_authenticate(user)
    assert client.get(url()).status_code == 403
    assert client.put(url(), payload(), format="json").status_code == 403
    assert (
        client.post(url("mailer-settings-test"), payload(), format="json").status_code
        == 403
    )


def test_empty_configuration_reads_back(switch_on, client):
    response = client.get(url())
    assert response.status_code == 200
    assert response.json() == {
        "is_active": False,
        "from_email": "",
        "last_tested_at": None,
        "mailers": [],
    }


def test_saving_without_a_test_is_refused(switch_on, client, fake_smtp):
    response = client.put(url(), payload(), format="json")
    assert response.status_code == 400
    assert "test_token" in response.json()
    assert MailerConfiguration.get().mailers.count() == 0


def test_test_endpoint_sends_to_the_requester_and_issues_a_token(
    switch_on, client, fake_smtp
):
    response = client.post(url("mailer-settings-test"), payload(), format="json")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert [(r["mailer"], r["ok"]) for r in body["results"]] == [("custom-1", True)]
    assert body["test_token"]
    assert mail.outbox[0].to == ["admin@tests.local"]
    assert mail.outbox[0].from_email == "hello@example.com"
    assert "CISO Assistant test email" == mail.outbox[0].subject
    # Nothing was saved by the test.
    assert MailerConfiguration.get().mailers.count() == 0


def test_test_endpoint_reports_failure_without_a_token(switch_on, client, fake_smtp):
    response = client.post(
        url("mailer-settings-test"), payload(host="refused.test"), format="json"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "test_token" not in body
    assert body["results"][0]["ok"] is False
    assert "refused" in body["results"][0]["error"]


def test_tested_values_save_and_notify_the_other_administrators(
    switch_on, client, fake_smtp, other_admin
):
    token = client.post(url("mailer-settings-test"), payload(), format="json").json()[
        "test_token"
    ]
    mail.outbox.clear()

    response = client.put(url(), payload(test_token=token), format="json")

    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["is_active"] is True
    assert data["last_tested_at"] is not None
    assert data["mailers"][0]["host"] == "locmem.test"
    assert data["mailers"][0]["has_password"] is True
    assert "password" not in data["mailers"][0]
    row = MailerConfiguration.get().mailers.get(position=1)
    assert row.password == "pw"
    # The notification went through the environment mailer that was active
    # before the change, to the other administrator only.
    assert len(mail.outbox) == 1
    notice = mail.outbox[0]
    assert notice.to == ["other@tests.local"]
    assert notice.from_email == "env@tests.local"
    assert "changed the outgoing mail configuration" in notice.body
    assert "admin@tests.local" in notice.body


def test_token_is_bound_to_the_exact_values(switch_on, client, fake_smtp):
    token = client.post(url("mailer-settings-test"), payload(), format="json").json()[
        "test_token"
    ]
    edited = payload(test_token=token)
    edited["mailers"][0]["port"] = 2525
    response = client.put(url(), edited, format="json")
    assert response.status_code == 400
    assert "test_token" in response.json()


def test_override_saves_without_a_test(switch_on, client, fake_smtp):
    response = client.put(url(), payload(override_untested=True), format="json")
    assert response.status_code == 200
    assert response.json()["last_tested_at"] is None
    assert MailerConfiguration.get().is_active is True


def test_blank_secret_keeps_the_stored_one(switch_on, client, fake_smtp):
    client.put(url(), payload(override_untested=True), format="json")
    edited = payload(override_untested=True)
    edited["mailers"][0]["password"] = ""
    edited["mailers"][0]["port"] = 2525
    response = client.put(url(), edited, format="json")
    assert response.status_code == 200
    row = MailerConfiguration.get().mailers.get(position=1)
    assert (row.password, row.port) == ("pw", 2525)


def test_second_mailer_can_be_removed(switch_on, client, fake_smtp):
    two = payload(override_untested=True)
    two["mailers"].append({**two["mailers"][0], "position": 2, "host": "refused.test"})
    assert client.put(url(), two, format="json").status_code == 200
    assert MailerConfiguration.get().mailers.count() == 2
    assert (
        client.put(url(), payload(override_untested=True), format="json").status_code
        == 200
    )
    assert list(
        MailerConfiguration.get().mailers.values_list("position", flat=True)
    ) == [1]


def test_unusable_oauth_row_is_refused(switch_on, client, fake_smtp):
    data = payload(override_untested=True)
    data["mailers"][0]["transport"] = "smtp-oauth2"
    data["mailers"][0]["oauth2_grant_type"] = "client_credentials"
    data["mailers"][0]["oauth2_token_url"] = "http://idp.example/token"
    data["mailers"][0]["oauth2_client_id"] = "c"
    data["mailers"][0]["oauth2_client_secret"] = "s"
    response = client.put(url(), data, format="json")
    assert response.status_code == 400
    assert "https" in str(response.json()["mailers"])


def test_malformed_oauth_token_url_is_reported_in_our_own_words(
    switch_on, client, fake_smtp
):
    # urlsplit raises on this; the answer must carry our message, never the
    # exception's text.
    data = payload(override_untested=True)
    data["mailers"][0]["transport"] = "smtp-oauth2"
    data["mailers"][0]["oauth2_grant_type"] = "client_credentials"
    data["mailers"][0]["oauth2_token_url"] = "https://[idp.example/token"
    data["mailers"][0]["oauth2_client_id"] = "c"
    data["mailers"][0]["oauth2_client_secret"] = "s"
    response = client.put(url(), data, format="json")
    assert response.status_code == 400
    assert (
        response.json()["mailers"] == "mailer 1: EMAIL_OAUTH2_TOKEN_URL must use https"
    )


def test_contradictory_tls_row_is_refused(switch_on, client, fake_smtp):
    data = payload(override_untested=True)
    data["mailers"][0]["use_tls"] = True
    data["mailers"][0]["use_ssl"] = True
    response = client.put(url(), data, format="json")
    assert response.status_code == 400
    assert response.json()["mailers"] == "mailer 1: TLS and SSL are mutually exclusive"


def test_activating_requires_a_sender_address(switch_on, client, fake_smtp):
    response = client.put(
        url(), payload(override_untested=True, from_email=""), format="json"
    )
    assert response.status_code == 400
    assert "from_email" in response.json()


def test_health_endpoint_lists_the_rows(switch_on, client):
    mailer.send("S", "b", "a@tests.local")
    response = client.get(url("mailer-settings-health"))
    assert response.status_code == 200
    rows = response.json()
    assert rows[0]["alias"] == "default"
    assert rows[0]["last_outcome"] == "ok"


def test_every_mailer_is_tested_and_a_failing_second_one_blocks_the_token(
    switch_on, client, fake_smtp
):
    two = payload()
    two["mailers"].append({**two["mailers"][0], "position": 2, "host": "refused.test"})
    response = client.post(url("mailer-settings-test"), two, format="json")
    body = response.json()
    assert body["ok"] is False
    assert "test_token" not in body
    assert [(r["mailer"], r["ok"]) for r in body["results"]] == [
        ("custom-1", True),
        ("custom-2", False),
    ]
    # The first mailer really was exercised on its own.
    assert [m.to for m in mail.outbox] == [["admin@tests.local"]]


def test_blank_port_is_tested_and_saved(switch_on, client, fake_smtp):
    data = payload()
    data["mailers"][0]["port"] = None
    response = client.post(url("mailer-settings-test"), data, format="json")
    assert response.status_code == 200, response.json()
    data["test_token"] = response.json()["test_token"]
    response = client.put(url(), data, format="json")
    assert response.status_code == 200, response.json()
    row = Mailer.objects.get(position=1)
    assert row.port is None
    # The backend gets no port and lets smtplib pick the standard one.
    assert row.mailer_entry()["OPTIONS"]["port"] is None
    assert response.json()["mailers"][0]["port"] is None


def _resolving_to(monkeypatch, address):
    import socket

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, *a, **k: [(socket.AF_INET, None, None, "", (address, 0))],
    )


def test_private_hosts_are_refused_unless_the_deployment_allows_them(
    switch_on, settings, client, fake_smtp, monkeypatch
):
    settings.ALLOW_PRIVATE_NETWORK_REQUESTS = False
    _resolving_to(monkeypatch, "10.0.0.5")
    data = payload(host="relay.internal")
    for method, target in (
        (client.post, url("mailer-settings-test")),
        (client.put, url()),
    ):
        response = method(target, {**data, "override_untested": True}, format="json")
        assert response.status_code == 400
        assert "mailer 1: the host must resolve to a public address" in str(
            response.json()["mailers"]
        )
    assert Mailer.objects.count() == 0
    assert mail.outbox == []

    settings.ALLOW_PRIVATE_NETWORK_REQUESTS = True
    response = client.post(url("mailer-settings-test"), payload(), format="json")
    assert response.status_code == 200


def test_oauth_token_url_follows_the_same_network_policy(
    switch_on, settings, client, fake_smtp, monkeypatch
):
    settings.ALLOW_PRIVATE_NETWORK_REQUESTS = False
    import socket

    real = socket.getaddrinfo

    def resolve(host, *a, **k):
        if host == "idp.internal":
            return [(socket.AF_INET, None, None, "", ("192.168.1.9", 0))]
        return [(socket.AF_INET, None, None, "", ("8.8.8.8", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    data = payload(host="smtp.example.com")
    data["mailers"][0].update(
        {
            "transport": "smtp-oauth2",
            "password": "",
            "oauth2_grant_type": "client_credentials",
            "oauth2_token_url": "https://idp.internal/token",
            "oauth2_scope": "mail",
            "oauth2_client_id": "id",
            "oauth2_client_secret": "secret",
        }
    )
    response = client.post(url("mailer-settings-test"), data, format="json")
    assert response.status_code == 400
    assert "the token URL must resolve to a public address" in str(
        response.json()["mailers"]
    )
    del real


def test_unresolvable_host_is_reported_in_our_words(
    switch_on, settings, client, fake_smtp, monkeypatch
):
    settings.ALLOW_PRIVATE_NETWORK_REQUESTS = False
    import socket

    def resolve(host, *a, **k):
        raise socket.gaierror(8, "nodename nor servname provided")

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    response = client.post(
        url("mailer-settings-test"), payload(host="nope.example"), format="json"
    )
    assert response.status_code == 400
    assert response.json()["mailers"] == "mailer 1: the host could not be resolved"


def test_health_lists_configured_mailers_never_attempted(switch_on, client, fake_smtp):
    two = payload(override_untested=True)
    two["mailers"].append({**two["mailers"][0], "position": 2, "host": "refused.test"})
    assert client.put(url(), two, format="json").status_code == 200
    rows = client.get(url("mailer-settings-health")).json()
    assert [(r["alias"], r["last_outcome"], r["last_attempt_at"]) for r in rows] == [
        ("custom-1", None, None),
        ("custom-2", None, None),
    ]


def test_testing_the_saved_configuration_records_health_for_each_mailer(
    switch_on, client, fake_smtp
):
    two = payload(override_untested=True)
    two["mailers"].append({**two["mailers"][0], "position": 2, "host": "refused.test"})
    assert client.put(url(), two, format="json").status_code == 200
    two.pop("override_untested")
    response = client.post(url("mailer-settings-test"), two, format="json")
    assert response.json()["ok"] is False
    health = {row.alias: row for row in MailerHealth.objects.all()}
    assert health["custom-1"].last_outcome == "ok"
    assert health["custom-2"].last_outcome == "unreachable"


def test_draft_test_does_not_rewrite_live_health(switch_on, client, fake_smtp):
    # The live mailer delivered once; a failed test of a draft with the same
    # position must not mark it unreachable.
    client.put(url(), payload(override_untested=True), format="json")
    mailer.send("S", "b", "a@tests.local")
    assert MailerHealth.objects.get(alias="custom-1").last_outcome == "ok"

    response = client.post(
        url("mailer-settings-test"), payload(host="refused.test"), format="json"
    )

    assert response.json()["ok"] is False
    assert MailerHealth.objects.get(alias="custom-1").last_outcome == "ok"
