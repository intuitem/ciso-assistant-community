"""Validation of the OrcaRouter base URL.

The configured API key is attached to the provider health check and to every
request the delegated client makes, so the gateway URL must be https: a
plaintext endpoint would put the key on the wire.
"""

import pytest

from global_settings.models import GlobalSettings
from global_settings.serializers import GeneralSettingsSerializer

DEFAULT_BASE = "https://api.orcarouter.ai/v1"


def _patch_general_settings(value: dict) -> tuple[GeneralSettingsSerializer, bool]:
    """Run `value` through the general-settings serializer as the API does."""
    row, _ = GlobalSettings.objects.get_or_create(name="general", defaults={"value": {}})
    serializer = GeneralSettingsSerializer(row, data={"value": value}, partial=True)
    return serializer, serializer.is_valid()


def _orcarouter_error(serializer: GeneralSettingsSerializer) -> str:
    errors = serializer.errors["value"]
    return str(errors["orcarouter_api_base"])


@pytest.mark.django_db
class TestOrcaRouterBaseUrlValidation:
    def test_rejects_http_base_url(self):
        serializer, is_valid = _patch_general_settings(
            {"orcarouter_api_base": "http://api.orcarouter.ai/v1"}
        )

        assert not is_valid
        assert "https" in _orcarouter_error(serializer)

    def test_accepts_https_base_url(self):
        serializer, is_valid = _patch_general_settings(
            {"orcarouter_api_base": DEFAULT_BASE}
        )

        assert is_valid, serializer.errors
        assert serializer.save().value["orcarouter_api_base"] == DEFAULT_BASE

    def test_empty_base_url_falls_back_to_the_default(self):
        # An empty string would otherwise bypass validation, be stored as-is
        # and make get_llm() degrade to retrieval-only.
        serializer, is_valid = _patch_general_settings({"orcarouter_api_base": ""})

        assert is_valid, serializer.errors
        assert serializer.save().value["orcarouter_api_base"] == DEFAULT_BASE

    def test_http_is_still_allowed_for_the_other_providers(self):
        # Local inference servers are plain http by design; only OrcaRouter,
        # which carries a key, is restricted.
        serializer, is_valid = _patch_general_settings(
            {"ollama_base_url": "http://localhost:11434"}
        )

        assert is_valid, serializer.errors
