"""
Tests for per-template email toggles (disabled_email_templates).

Covers:
- is_email_template_enabled: enabled by default, disabled when listed,
  robust to a missing settings row or malformed value
- render_email_template: returns None for a disabled template (intentional
  skip), and {} when a template fails to load or render
- User.mailing: skips sending entirely (no legacy fallback) when the
  mapped template key is disabled
- GeneralSettingsSerializer: preserves disabled_email_templates when a
  general settings update does not provide it, rejects malformed values
"""

import pytest
from rest_framework import serializers as drf_serializers

from core.email_utils import is_email_template_enabled, render_email_template
from global_settings.models import GlobalSettings
from global_settings.serializers import GeneralSettingsSerializer
from iam.models import User


@pytest.fixture
def general_settings(db):
    settings, _ = GlobalSettings.objects.get_or_create(name="general")
    settings.value = settings.value or {}
    settings.save()
    return settings


def _disable(general_settings, *keys):
    general_settings.value["disabled_email_templates"] = list(keys)
    general_settings.save()


@pytest.mark.django_db
class TestIsEmailTemplateEnabled:
    def test_enabled_by_default(self, general_settings):
        assert is_email_template_enabled("welcome") is True

    def test_disabled_when_listed(self, general_settings):
        _disable(general_settings, "welcome")
        assert is_email_template_enabled("welcome") is False
        assert is_email_template_enabled("password_reset") is True

    def test_enabled_without_settings_row(self):
        # Deleting the row isn't possible here (SSOSettings is unmanaged MTI
        # over GlobalSettings), so only assert on whatever state the fresh
        # test database has: no row, or a row without the key.
        assert not GlobalSettings.objects.filter(
            name="general",
            value__has_key="disabled_email_templates",
        ).exists()
        assert is_email_template_enabled("welcome") is True

    def test_malformed_value_means_enabled(self, general_settings):
        general_settings.value["disabled_email_templates"] = "welcome"
        general_settings.save()
        assert is_email_template_enabled("welcome") is True


@pytest.mark.django_db
class TestRenderGate:
    def test_disabled_template_renders_none(self, general_settings):
        # None = intentional skip; {} is reserved for actual render failures
        # so callers can keep logging errors only for real problems.
        _disable(general_settings, "welcome")
        assert render_email_template("welcome", {}, locale="en") is None

    def test_missing_template_renders_empty_dict(self, general_settings):
        assert render_email_template("does_not_exist", {}, locale="en") == {}

    def test_enabled_template_renders(self, general_settings):
        rendered = render_email_template("welcome", {}, locale="en")
        assert rendered.get("subject")
        assert rendered.get("body")


@pytest.mark.django_db
class TestMailingGate:
    @pytest.fixture
    def user(self):
        return User.objects.create(email="toggle-mail@tests.com")

    def test_disabled_template_skips_send(self, general_settings, user, monkeypatch):
        sent = []
        monkeypatch.setattr(
            User, "_send_email", lambda self, *args, **kwargs: sent.append(args)
        )
        _disable(general_settings, "welcome")
        user.mailing("registration/first_connexion_email.html", "First connection")
        assert sent == []

    def test_enabled_template_sends(self, general_settings, user, monkeypatch):
        sent = []
        monkeypatch.setattr(
            User, "_send_email", lambda self, *args, **kwargs: sent.append(args)
        )
        user.mailing("registration/first_connexion_email.html", "First connection")
        assert len(sent) == 1


@pytest.mark.django_db
class TestSerializerPreservation:
    def test_preserved_when_absent_from_update(self, general_settings):
        _disable(general_settings, "welcome")
        GeneralSettingsSerializer().update(
            general_settings, {"value": {"currency": "€"}}
        )
        general_settings.refresh_from_db()
        assert general_settings.value["disabled_email_templates"] == ["welcome"]
        assert general_settings.value["currency"] == "€"

    def test_explicit_update_applies(self, general_settings):
        GeneralSettingsSerializer().update(
            general_settings,
            {"value": {"disabled_email_templates": ["expired_controls"]}},
        )
        general_settings.refresh_from_db()
        assert general_settings.value["disabled_email_templates"] == [
            "expired_controls"
        ]

    def test_malformed_value_rejected(self, general_settings):
        with pytest.raises(drf_serializers.ValidationError):
            GeneralSettingsSerializer().update(
                general_settings,
                {"value": {"disabled_email_templates": "welcome"}},
            )
