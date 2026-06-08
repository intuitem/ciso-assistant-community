"""Heuristic token counting. TODO: swap to tiktoken cl100k when cp314 wheels exist."""

_CHARS_PER_TOKEN = 3  # over-estimate: cl100k averages ~3.3 (en) / ~2.5 (cjk)


def count_tokens(text: str, model: str | None = None) -> int:
    """Approximate token count. `model` reserved for tiktoken swap."""
    _ = model
    if not text:
        return 0
    return (len(text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN


def truncate_to_tokens(text: str, n: int) -> str:
    """Truncate to at most `n` tokens."""
    if not text or n <= 0:
        return ""
    return text[: n * _CHARS_PER_TOKEN]
