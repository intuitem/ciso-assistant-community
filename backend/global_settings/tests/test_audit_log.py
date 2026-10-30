"""Auditing of settings, feature flags, integrations and webhooks — with secret masking."""

import pytest
from auditlog.context import set_actor
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from global_settings.models import GlobalSettings
from global_settings.utils import (
    SETTINGS_MASK_PLACEHOLDER,
    mask_sensitive_settings,
    redact_secret_value,
)
from iam.models import User


def _ct():
    return ContentType.objects.get_for_model(GlobalSettings)


@pytest.mark.django_db
class TestSettingsAuditLog:
    def test_general_setting_change_is_logged_with_actor(self):
        gs, _ = GlobalSettings.objects.get_or_create(name="general")
        gs.value = {"currency": "USD", "daily_rate": 500}
        gs.save()

        user = User.objects.create_user(email="admin@test.com")
        with set_actor(actor=user):
            gs.value = {"currency": "EUR", "daily_rate": 600}
            gs.save(update_fields=["value"])

        entry = (
            LogEntry.objects.filter(
                content_type=_ct(), object_pk=str(gs.pk), action=LogEntry.Action.UPDATE
            )
            .order_by("-timestamp")
            .first()
        )
        assert entry is not None
        assert entry.actor_id == user.pk
        assert "value" in entry.changes
        old, new = entry.changes["value"]
        assert "USD" in old and "EUR" in new
        assert "500" in old and "600" in new

    def test_feature_flag_toggle_is_logged(self):
        gs, _ = GlobalSettings.objects.get_or_create(name="feature-flags")
        gs.value = {"tprm": True}
        gs.save()

        gs.value = {"tprm": False}
        gs.save(update_fields=["value"])

        entry = (
            LogEntry.objects.filter(
                content_type=_ct(), object_pk=str(gs.pk), action=LogEntry.Action.UPDATE
            )
            .order_by("-timestamp")
            .first()
        )
        assert entry is not None
        old, new = entry.changes["value"]
        assert "true" in old and "false" in new

    def test_api_key_is_never_stored_in_the_audit_log(self):
        secret = "sk-supersecret-should-never-leak"
        gs, _ = GlobalSettings.objects.get_or_create(name="general")
        gs.value = {"currency": "USD", "openai_api_key": secret}
        gs.save()

        gs.value = {"currency": "EUR", "openai_api_key": secret}
        gs.save(update_fields=["value"])

        for entry in LogEntry.objects.filter(content_type=_ct(), object_pk=str(gs.pk)):
            assert secret not in str(entry.changes)
            assert secret not in (entry.changes_text or "")

    def test_sso_secrets_are_never_stored_in_the_audit_log(self):
        # SSO is stored in the name="sso" row; secrets sit top-level and nested.
        secrets = ["CLIENT_SECRET", "CONSUMER_KEY", "-----BEGIN PRIVATE KEY-----"]
        gs, _ = GlobalSettings.objects.get_or_create(name="sso")
        gs.value = {
            "provider": "saml",
            "secret": secrets[0],
            "key": secrets[1],
            "settings": {
                "idp": {"entity_id": "https://idp", "x509cert": "PUBLIC"},
                "advanced": {"private_key": secrets[2]},
            },
        }
        gs.save()

        entries = LogEntry.objects.filter(content_type=_ct(), object_pk=str(gs.pk))
        assert entries.exists()
        blob = " ".join(str(e.changes) + (e.changes_text or "") for e in entries)
        for secret in secrets:
            assert secret not in blob
        assert "https://idp" in blob

    def test_folder_id_captured_for_settings_entries(self):
        gs, _ = GlobalSettings.objects.get_or_create(name="general")
        gs.value = {"currency": "USD"}
        gs.save()
        gs.value = {"currency": "GBP"}
        gs.save(update_fields=["value"])

        entry = (
            LogEntry.objects.filter(content_type=_ct(), object_pk=str(gs.pk))
            .order_by("-timestamp")
            .first()
        )
        assert (entry.additional_data or {}).get("folder_id")


class TestMaskSensitiveSettings:
    def test_masks_only_the_secret(self):
        out = mask_sensitive_settings(
            '{"currency": "USD", "openai_api_key": "sk-live-abc"}'
        )
        assert "sk-live-abc" not in out
        assert SETTINGS_MASK_PLACEHOLDER in out
        assert "USD" in out

    def test_passthrough_without_secret(self):
        blob = '{"currency": "EUR"}'
        assert mask_sensitive_settings(blob) == blob

    def test_passthrough_on_non_json(self):
        assert mask_sensitive_settings("not-json") == "not-json"

    def test_empty_api_key_left_untouched(self):
        blob = '{"openai_api_key": ""}'
        assert mask_sensitive_settings(blob) == blob

    def test_masks_nested_sso_private_key_keeps_config(self):
        out = mask_sensitive_settings(
            '{"secret": "s", "settings": {"idp": {"x509cert": "PUB"}, '
            '"advanced": {"private_key": "PRIV", "want_name_id": false}}}'
        )
        assert "PRIV" not in out and out.count(SETTINGS_MASK_PLACEHOLDER) == 2
        assert "PUB" in out and "want_name_id" in out


class TestRedactSecretValue:
    def test_bare_string_fully_redacted(self):
        assert redact_secret_value("HMAC_SECRET") == SETTINGS_MASK_PLACEHOLDER

    def test_dict_keeps_keys_redacts_every_value(self):
        out = redact_secret_value('{"api_token": "TOKENVAL", "username": "USERVAL"}')
        assert "TOKENVAL" not in out and "USERVAL" not in out
        assert "api_token" in out and "username" in out

    def test_nested_kafka_sasl_redacted(self):
        out = redact_secret_value(
            '{"bootstrap_servers": "b", "config": {"sasl_plain_password": "pw"}}'
        )
        assert "pw" not in out and "sasl_plain_password" in out

    def test_empty_passthrough(self):
        assert redact_secret_value("") == ""


@pytest.mark.django_db
class TestIntegrationConfigAuditLog:
    def test_credentials_change_logged_without_leaking_token(self):
        from integrations.models import IntegrationConfiguration, IntegrationProvider

        provider = IntegrationProvider.objects.create(
            name="jira-audittest", provider_type="itsm"
        )
        config = IntegrationConfiguration.objects.create(
            provider=provider,
            credentials={"api_token": "OLD_TOKEN"},
            webhook_secret="OLD_WH_SECRET",
        )
        config.credentials = {"api_token": "NEW_SECRET_TOKEN"}
        config.webhook_secret = "NEW_WH_SECRET"
        config.save(update_fields=["credentials", "webhook_secret"])

        ct = ContentType.objects.get_for_model(IntegrationConfiguration)
        entries = LogEntry.objects.filter(content_type=ct, object_pk=str(config.pk))
        assert entries.exists()
        for entry in entries:
            blob = str(entry.changes) + (entry.changes_text or "")
            for secret in (
                "OLD_TOKEN",
                "NEW_SECRET_TOKEN",
                "OLD_WH_SECRET",
                "NEW_WH_SECRET",
            ):
                assert secret not in blob
