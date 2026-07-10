"""Tests for tokens.py — heuristic token counting."""

from chat.tokens import count_tokens, truncate_to_tokens


class TestCountTokens:
    def test_empty(self):
        assert count_tokens("") == 0
        assert count_tokens(None) == 0  # type: ignore[arg-type]

    def test_short_text(self):
        assert count_tokens("abc") == 1
        assert count_tokens("a") == 1

    def test_monotonic_with_length(self):
        a = count_tokens("hello")
        b = count_tokens("hello world")
        c = count_tokens("hello world, this is a longer message")
        assert a < b < c

    def test_model_arg_ignored(self):
        # Forward-compat slot — must not change behavior under the heuristic
        assert count_tokens("hello", model="gpt-4o") == count_tokens("hello")
        assert count_tokens("hello", model=None) == count_tokens("hello")

    def test_round_trip_ceiling(self):
        # Ceiling division: 4 chars at 3 chars/token → 2 tokens
        assert count_tokens("abcd") == 2
        # 6 chars → 2 tokens (exact)
        assert count_tokens("abcdef") == 2
        # 7 chars → 3 tokens (ceiling)
        assert count_tokens("abcdefg") == 3


class TestTruncateToTokens:
    def test_empty_input(self):
        assert truncate_to_tokens("", 10) == ""
        assert truncate_to_tokens(None, 10) == ""  # type: ignore[arg-type]

    def test_zero_or_negative(self):
        assert truncate_to_tokens("hello world", 0) == ""
        assert truncate_to_tokens("hello world", -1) == ""

    def test_truncates_long_text(self):
        text = "a" * 100
        result = truncate_to_tokens(text, 10)
        # 10 tokens × 3 chars = 30 chars
        assert len(result) == 30
        assert count_tokens(result) <= 10

    def test_short_text_unchanged(self):
        text = "hi"
        result = truncate_to_tokens(text, 100)
        assert result == text

    def test_count_after_truncate_within_budget(self):
        text = "x" * 1000
        for n in (1, 5, 50, 500):
            result = truncate_to_tokens(text, n)
            assert count_tokens(result) <= n
