"""Tests for the DB-backed cross-worker login throttle (iam.LoginAttempt).

Covers the counter/window logic on the model and the deny-before-write wiring
in AccountAdapter.authenticate, including the composite (email, IP) keying that
stops an attacker from locking a legitimate user out from a different IP.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.utils import timezone

from iam.adapter import AccountAdapter
from iam.models import LoginAttempt

User = get_user_model()

PASSWORD = "correct-horse-battery-staple"
EMAIL = "local@example.com"


@pytest.fixture
def db_throttle(settings):
    # Neutralise the per-worker allauth cache limit so these tests exercise only
    # the DB throttle, then set a small, deterministic DB threshold.
    settings.ACCOUNT_RATE_LIMITS = {"login_failed": "100000/m/ip,100000/300s/key"}
    settings.LOGIN_ATTEMPT_MAX_FAILURES = 3
    settings.LOGIN_ATTEMPT_WINDOW_SECONDS = 900


@pytest.mark.django_db
@pytest.mark.usefixtures("db_throttle")
class TestLoginAttemptModel:
    def test_blocks_only_at_threshold(self):
        for _ in range(2):
            LoginAttempt.record_failure(EMAIL, "8.8.8.8")
        assert LoginAttempt.is_blocked(EMAIL, "8.8.8.8") is False
        LoginAttempt.record_failure(EMAIL, "8.8.8.8")
        assert LoginAttempt.is_blocked(EMAIL, "8.8.8.8") is True

    def test_composite_key_isolates_ip(self):
        for _ in range(3):
            LoginAttempt.record_failure(EMAIL, "8.8.8.8")
        assert LoginAttempt.is_blocked(EMAIL, "8.8.8.8") is True
        # Same account, different IP -> untouched. This is the lockout-DoS guard.
        assert LoginAttempt.is_blocked(EMAIL, "203.0.113.9") is False

    def test_window_expiry_resets_counter(self):
        for _ in range(3):
            LoginAttempt.record_failure(EMAIL, "8.8.8.8")
        row = LoginAttempt.objects.get(username_hash=LoginAttempt._hash(EMAIL))
        row.window_start = timezone.now() - timedelta(seconds=1000)
        row.save(update_fields=["window_start"])

        assert LoginAttempt.is_blocked(EMAIL, "8.8.8.8") is False
        # A failure after the window starts a fresh count of 1, not 4.
        LoginAttempt.record_failure(EMAIL, "8.8.8.8")
        row.refresh_from_db()
        assert row.failure_count == 1

    def test_reset_clears_counter(self):
        for _ in range(3):
            LoginAttempt.record_failure(EMAIL, "8.8.8.8")
        LoginAttempt.reset(EMAIL, "8.8.8.8")
        assert LoginAttempt.is_blocked(EMAIL, "8.8.8.8") is False
        assert not LoginAttempt.objects.filter(
            username_hash=LoginAttempt._hash(EMAIL)
        ).exists()

    def test_missing_ip_uses_sentinel(self):
        for _ in range(3):
            LoginAttempt.record_failure(EMAIL, None)
        assert LoginAttempt.is_blocked(EMAIL, None) is True
        assert LoginAttempt.objects.filter(
            username_hash=LoginAttempt._hash(EMAIL), ip=""
        ).exists()


@pytest.mark.django_db
@pytest.mark.usefixtures("db_throttle")
class TestAdapterDbThrottle:
    def setup_method(self):
        cache.clear()
        self.factory = RequestFactory()
        self.adapter = AccountAdapter()
        self.user = User.objects.create_user(email=EMAIL, password=PASSWORD)

    def _req(self, ip="8.8.8.8"):
        return self.factory.post("/_allauth/app/v1/auth/login", REMOTE_ADDR=ip)

    def test_blocks_after_threshold(self):
        for _ in range(3):
            assert (
                self.adapter.authenticate(self._req(), email=EMAIL, password="nope")
                is None
            )
        with pytest.raises(ValidationError) as exc:
            self.adapter.authenticate(self._req(), email=EMAIL, password="nope")
        assert exc.value.code == "too_many_login_attempts"

    def test_block_is_deny_before_write_even_for_valid_password(self):
        for _ in range(3):
            self.adapter.authenticate(self._req(), email=EMAIL, password="nope")
        # Once blocked, even the correct password is refused before hashing.
        with pytest.raises(ValidationError):
            self.adapter.authenticate(self._req(), email=EMAIL, password=PASSWORD)

    def test_isolated_per_ip(self):
        for _ in range(4):
            try:
                self.adapter.authenticate(
                    self._req("8.8.8.8"), email=EMAIL, password="nope"
                )
            except ValidationError:
                pass
        # A legitimate user on a different IP is not locked out.
        assert (
            self.adapter.authenticate(
                self._req("203.0.113.9"), email=EMAIL, password=PASSWORD
            )
            == self.user
        )

    def test_success_resets_counter(self):
        for _ in range(2):
            self.adapter.authenticate(self._req(), email=EMAIL, password="nope")
        assert (
            self.adapter.authenticate(self._req(), email=EMAIL, password=PASSWORD)
            == self.user
        )
        # Counter cleared, so a fresh run of failures is needed to block again.
        assert not LoginAttempt.objects.filter(
            username_hash=LoginAttempt._hash(EMAIL)
        ).exists()
