"""Shared constants for the chat module."""

import os

# Max characters in a single user message
MAX_MESSAGE_LENGTH = 10000

# Max characters for page_context field values
MAX_CONTEXT_FIELD_LENGTH = 200

# Token budget knobs (env-overridable)
MODEL_CONTEXT_TOKENS = int(os.environ.get("CHAT_MODEL_CONTEXT_TOKENS", 8000))
RAG_CONTEXT_TOKENS = int(os.environ.get("CHAT_RAG_CONTEXT_TOKENS", 2400))
SUMMARY_TOKEN_CAP = int(os.environ.get("CHAT_SUMMARY_TOKEN_CAP", 400))
TOOL_REPLAY_TOKENS = int(os.environ.get("CHAT_TOOL_REPLAY_TOKENS", 500))
VERBATIM_WINDOW_TOKENS = int(os.environ.get("CHAT_VERBATIM_WINDOW_TOKENS", 3000))

# Mirrors ENABLE_CHAT parsing in settings.py
_TRUTHY = ("true", "1", "yes", "on")

CHAT_SESSION_SUMMARY_ENABLED = (
    os.environ.get("CHAT_SESSION_SUMMARY", "true").strip().lower() in _TRUTHY
)
# Async via Huey when true (needs a running worker); sync inline when false
CHAT_SESSION_SUMMARY_ASYNC = (
    os.environ.get("CHAT_SESSION_SUMMARY_ASYNC", "false").strip().lower() in _TRUTHY
)
SUMMARY_INPUT_TOKEN_CAP = int(os.environ.get("CHAT_SUMMARY_INPUT_TOKEN_CAP", 1500))

CHAT_TOOL_REPLAY_ENABLED = (
    os.environ.get("CHAT_TOOL_REPLAY", "true").strip().lower() in _TRUTHY
)
TOOL_REPLAY_TURNS = int(os.environ.get("CHAT_TOOL_REPLAY_TURNS", 2))


class Verdict:
    """Canonical questionnaire verdict strings.

    Used end-to-end: LLM JSON output → AgentAction.payload['status'] →
    refiner downgrade rules → frontend banded review → xlsx export. One
    source of truth so a typo anywhere in the chain can't silently corrupt
    a verdict. Kept in sync with the matching TS module at
    ``frontend/src/lib/utils/questionnaire-verdict.ts``.
    """

    YES = "yes"
    PARTIAL = "partial"
    NO = "no"
    NEEDS_INFO = "needs_info"

    ALL = frozenset({YES, PARTIAL, NO, NEEDS_INFO})

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.ALL


# ISO language code → English name (for LLM instructions)
LANG_MAP = {
    "fr": "French",
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "nl": "Dutch",
    "pt": "Portuguese",
    "ar": "Arabic",
    "pl": "Polish",
    "ro": "Romanian",
    "sv": "Swedish",
    "da": "Danish",
    "cs": "Czech",
    "uk": "Ukrainian",
    "el": "Greek",
    "tr": "Turkish",
    "hr": "Croatian",
    "zh": "Chinese",
    "lt": "Lithuanian",
    "ko": "Korean",
}
