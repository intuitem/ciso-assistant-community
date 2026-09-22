import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import RequestFactory, override_settings
from structlog.testing import capture_logs

from global_settings.models import GlobalSettings
from iam.adapter import AccountAdapter, resolve_client_ip

User = get_user_model()

PASSWORD = "correct-horse-battery-staple"


class TestResolveClientIp:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_no_request_returns_none(self):
        assert resolve_client_ip(None) is None

    def test_public_remote_addr_ignores_spoofed_header(self):
        # Direct internet request (no trusted reverse proxy in the middle):
        # a self-supplied X-Real-IP must not override the real peer address.
        req = self.factory.post(
            "/login", REMOTE_ADDR="8.8.8.8", HTTP_X_REAL_IP="1.2.3.4"
        )
        assert resolve_client_ip(req) == "8.8.8.8"

    def test_private_remote_addr_trusts_forwarded_header(self):
        # Request arrived via our own reverse proxy on an internal network.
        req = self.factory.post(
            "/login", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="203.0.113.7"
        )
        assert resolve_client_ip(req) == "203.0.113.7"

    def test_loopback_remote_addr_trusts_forwarded_header(self):
        req = self.factory.post(
            "/login", REMOTE_ADDR="127.0.0.1", HTTP_X_REAL_IP="203.0.113.7"
        )
        assert resolve_client_ip(req) == "203.0.113.7"

    def test_no_header_falls_back_to_remote_addr(self):
        req = self.factory.post("/login", REMOTE_ADDR="8.8.8.8")
        assert resolve_client_ip(req) == "8.8.8.8"


@pytest.mark.django_db
class TestAccountAdapterAuthenticate:
    def setup_method(self):
        cache.clear()
        self.factory = RequestFactory()
        self.adapter = AccountAdapter()
        self.user = User.objects.create_user(
            email="local@example.com", password=PASSWORD
        )

    def _request(self):
        return self.factory.post("/_allauth/app/v1/auth/login")

    def test_correct_password_returns_user(self):
        assert (
            self.adapter.authenticate(
                self._request(), email="local@example.com", password=PASSWORD
            )
            == self.user
        )

    def test_wrong_password_returns_none(self):
        assert (
            self.adapter.authenticate(
                self._request(), email="local@example.com", password="nope"
            )
            is None
        )

    def test_non_local_user_is_rejected(self):
        GlobalSettings.objects.update_or_create(
            name=GlobalSettings.Names.SSO,
            defaults={"value": {"is_enabled": True, "force_sso": True}},
        )
        assert self.user.is_local is False
        assert (
            self.adapter.authenticate(
                self._request(), email="local@example.com", password=PASSWORD
            )
            is None
        )

    @override_settings(ACCOUNT_RATE_LIMITS={"login_failed": "1000/m/ip,2/300s/key"})
    def test_rate_limit_raises_after_key_limit(self):
        req = self._request()
        for _ in range(2):
            assert (
                self.adapter.authenticate(
                    req, email="local@example.com", password="nope"
                )
                is None
            )
        with pytest.raises(ValidationError):
            self.adapter.authenticate(req, email="local@example.com", password="nope")

    @override_settings(ACCOUNT_RATE_LIMITS={"login_failed": "1000/m/ip,2/300s/key"})
    def test_successful_login_does_not_consume_failure_budget(self):
        req = self._request()
        for _ in range(5):
            assert (
                self.adapter.authenticate(
                    req, email="local@example.com", password=PASSWORD
                )
                == self.user
            )

    @override_settings(ACCOUNT_RATE_LIMITS={"login_failed": "1000/m/ip,2/300s/key"})
    def test_throttled_attempt_is_logged(self):
        req = self._request()
        for _ in range(2):
            self.adapter.authenticate(req, email="local@example.com", password="nope")
        with capture_logs() as logs:
            with pytest.raises(ValidationError):
                self.adapter.authenticate(
                    req, email="local@example.com", password="nope"
                )
        assert [entry for entry in logs if entry.get("event") == "login_throttled"]

    @override_settings(ACCOUNT_RATE_LIMITS={"login_failed": "1000/m/ip,2/300s/key"})
    def test_lockout_is_isolated_per_client_ip(self):
        def attempt(ip):
            req = self.factory.post("/login", REMOTE_ADDR=ip, HTTP_HOST="localhost")
            try:
                self.adapter.authenticate(
                    req, email="local@example.com", password="nope"
                )
                return False
            except ValidationError:
                return True

        # Attacker on one IP trips the (email, IP) limit for that IP only.
        assert [attempt("198.51.100.10") for _ in range(3)] == [False, False, True]
        # The real user on a different IP is unaffected.
        assert attempt("203.0.113.50") is False

    @override_settings(ACCOUNT_RATE_LIMITS={"login_failed": "1000/m/ip,2/300s/key"})
    def test_throttle_keys_on_forwarded_client_ip_not_remote_addr(self):
        # All requests share one frontend-container REMOTE_ADDR; the real client
        # is carried in the BFF-forwarded X-Real-IP header.
        def attempt(real_ip):
            req = self.factory.post(
                "/login",
                REMOTE_ADDR="10.0.0.1",
                HTTP_HOST="localhost",
                HTTP_X_REAL_IP=real_ip,
            )
            try:
                self.adapter.authenticate(
                    req, email="local@example.com", password="nope"
                )
                return False
            except ValidationError:
                return True

        assert [attempt("198.51.100.10") for _ in range(3)] == [False, False, True]
        # Different real client, same container REMOTE_ADDR -> not blocked.
        assert attempt("203.0.113.50") is False
