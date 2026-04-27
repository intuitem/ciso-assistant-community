"""Shared constants for the chat module."""

import os

# Max characters in a single user message
MAX_MESSAGE_LENGTH = 10000

# Max characters for page_context field values
MAX_CONTEXT_FIELD_LENGTH = 200

# Max conversation history messages sent to the LLM
LLM_HISTORY_LIMIT = 20

# Token budget knobs (env-overridable). Phase 1 uses RAG_CONTEXT_TOKENS only;
# the rest are defined now so later phases (verbatim window, summary, tool
# replay) don't have to touch this file again.
MODEL_CONTEXT_TOKENS = int(os.environ.get("CHAT_MODEL_CONTEXT_TOKENS", 8000))
RAG_CONTEXT_TOKENS = int(os.environ.get("CHAT_RAG_CONTEXT_TOKENS", 2400))
SUMMARY_TOKEN_CAP = int(os.environ.get("CHAT_SUMMARY_TOKEN_CAP", 400))
TOOL_REPLAY_TOKENS = int(os.environ.get("CHAT_TOOL_REPLAY_TOKENS", 500))
VERBATIM_WINDOW_TOKENS = int(os.environ.get("CHAT_VERBATIM_WINDOW_TOKENS", 3000))

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
