"""Tests for context.py — structured context assembly."""

import warnings

from chat.context import ContextBuilder
from chat.tokens import count_tokens


class TestContextBuilder:
    def test_empty(self):
        assert ContextBuilder().build() == ""

    def test_single_section(self):
        ctx = ContextBuilder()
        ctx.add("lang", "Respond in French.", priority=10)
        assert ctx.build() == "Respond in French."

    def test_skips_empty_content(self):
        ctx = ContextBuilder()
        ctx.add("empty", "", priority=10)
        ctx.add("none", None, priority=10)  # type: ignore[arg-type]
        ctx.add("real", "Hello", priority=5)
        assert ctx.build() == "Hello"

    def test_priority_ordering(self):
        ctx = ContextBuilder()
        ctx.add("low", "LOW", priority=1)
        ctx.add("high", "HIGH", priority=10)
        ctx.add("mid", "MID", priority=5)
        result = ctx.build()
        assert result.index("HIGH") < result.index("MID") < result.index("LOW")

    def test_budget_truncates_low_priority(self):
        # 50 tokens budget = ~150 chars
        ctx = ContextBuilder(max_tokens=50)
        ctx.add("important", "A" * 30, priority=10)
        ctx.add("expendable", "B" * 1000, priority=1)
        result = ctx.build()
        assert "A" * 30 in result
        assert "B" * 1000 not in result  # truncated or dropped

    def test_budget_keeps_high_priority_intact(self):
        ctx = ContextBuilder(max_tokens=40)
        ctx.add("critical", "Keep this", priority=10)
        ctx.add("filler", "X" * 2000, priority=1)
        result = ctx.build()
        assert "Keep this" in result

    def test_under_budget_no_truncation(self):
        ctx = ContextBuilder(max_tokens=10000)
        ctx.add("a", "Hello", priority=5)
        ctx.add("b", "World", priority=3)
        result = ctx.build()
        assert "Hello" in result
        assert "World" in result

    def test_section_names(self):
        ctx = ContextBuilder()
        ctx.add("lang", "X", priority=10)
        ctx.add("rag", "Y", priority=3)
        assert ctx.section_names() == ["lang", "rag"]

    def test_total_tokens(self):
        ctx = ContextBuilder()
        ctx.add("a", "abcdef", priority=5)  # 6 chars → 2 tokens
        ctx.add("b", "ghijkl", priority=3)  # 6 chars → 2 tokens
        assert ctx.total_tokens() == 4

    def test_total_chars_deprecated(self):
        ctx = ContextBuilder()
        ctx.add("a", "1234", priority=5)
        ctx.add("b", "5678", priority=3)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = ctx.total_chars()
            assert result == 8
            assert any(issubclass(item.category, DeprecationWarning) for item in w)

    def test_max_chars_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ctx = ContextBuilder(max_chars=300)
            assert ctx.max_tokens == 100  # 300 // 3
            assert any(issubclass(item.category, DeprecationWarning) for item in w)

    def test_truncated_section_within_budget(self):
        ctx = ContextBuilder(max_tokens=20)
        ctx.add("big", "Z" * 500, priority=5)
        result = ctx.build()
        # Result must fit budget (allow small slack for separator approximation)
        assert count_tokens(result) <= 25
        assert "(truncated)" in result

    def test_tiny_budget_smaller_than_tail(self):
        # Budget too small for the truncation tail — must not append tail-only
        ctx = ContextBuilder(max_tokens=2)
        ctx.add("big", "Z" * 500, priority=5)
        result = ctx.build()
        # Either empty (section dropped) or under budget; never tail-only overflow
        assert count_tokens(result) <= 2
