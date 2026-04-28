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
