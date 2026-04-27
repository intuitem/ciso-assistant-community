"""
Token counting helpers for chat memory budgeting.

Phase 1 uses a heuristic (~3 chars/token, conservative over-estimate) so we
don't depend on tiktoken — which has no cp314 wheel as of 0.12.0 and would
require a Rust toolchain in the Docker image to build from sdist.

The heuristic's precision is in the same class as the previous char-based
budget; the architectural win is the token-shaped API, not the precision.

TODO: swap to `tiktoken.get_encoding("cl100k_base")` when cp314 wheels ship.
The function signatures are the seam — callers stay unchanged.
"""

_CHARS_PER_TOKEN = 3  # over-estimate: cl100k averages ~3.3 (en) / ~2.5 (cjk)


def count_tokens(text: str, model: str | None = None) -> int:
    """
    Approximate token count for a string.

    `model` is accepted for forward compatibility (per-model encodings) but
    ignored under the heuristic.
    """
    _ = model  # reserved for tiktoken model-specific encoding
    if not text:
        return 0
    return (len(text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN


def truncate_to_tokens(text: str, n: int) -> str:
    """
    Truncate `text` so its token count is at most `n`.

    Under the heuristic, this is a char-slice — exact under tiktoken later.
    """
    if not text or n <= 0:
        return ""
    return text[: n * _CHARS_PER_TOKEN]
