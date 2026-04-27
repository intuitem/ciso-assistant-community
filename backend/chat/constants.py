"""Shared constants for the chat module."""

# Max characters in a single user message
MAX_MESSAGE_LENGTH = 10000

# Max characters for page_context field values
MAX_CONTEXT_FIELD_LENGTH = 200

# Max conversation history messages sent to the LLM
LLM_HISTORY_LIMIT = 20

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
