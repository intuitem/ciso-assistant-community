"""Tests for constants.py — token budget config."""

import importlib

from chat import constants


class TestTokenBudgetConstants:
    def test_defaults(self):
        assert constants.MODEL_CONTEXT_TOKENS == 8000
        assert constants.RAG_CONTEXT_TOKENS == 2400
        assert constants.SUMMARY_TOKEN_CAP == 400
        assert constants.TOOL_REPLAY_TOKENS == 500
        assert constants.VERBATIM_WINDOW_TOKENS == 3000

    def test_invariants(self):
        # Hot-context pieces should not exceed model context on their own
        hot = (
            constants.RAG_CONTEXT_TOKENS
            + constants.SUMMARY_TOKEN_CAP
            + constants.VERBATIM_WINDOW_TOKENS
        )
        assert hot < constants.MODEL_CONTEXT_TOKENS

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("CHAT_MODEL_CONTEXT_TOKENS", "16000")
        monkeypatch.setenv("CHAT_RAG_CONTEXT_TOKENS", "4800")
        reloaded = importlib.reload(constants)
        try:
            assert reloaded.MODEL_CONTEXT_TOKENS == 16000
            assert reloaded.RAG_CONTEXT_TOKENS == 4800
        finally:
            # Restore module to default for downstream tests
            monkeypatch.delenv("CHAT_MODEL_CONTEXT_TOKENS", raising=False)
            monkeypatch.delenv("CHAT_RAG_CONTEXT_TOKENS", raising=False)
            importlib.reload(constants)
