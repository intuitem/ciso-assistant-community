"""Tests for context.py — structured context assembly."""

from chat.context import ContextBuilder


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
        ctx.add("none", None, priority=10)
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
        ctx = ContextBuilder(max_chars=50)
        ctx.add("important", "A" * 30, priority=10)
        ctx.add("expendable", "B" * 100, priority=1)
        result = ctx.build()
        assert "A" * 30 in result
        assert "B" * 100 not in result  # truncated or dropped

    def test_budget_keeps_high_priority_intact(self):
        ctx = ContextBuilder(max_chars=40)
        ctx.add("critical", "Keep this", priority=10)
        ctx.add("filler", "X" * 200, priority=1)
        result = ctx.build()
        assert "Keep this" in result

    def test_under_budget_no_truncation(self):
        ctx = ContextBuilder(max_chars=10000)
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

    def test_total_chars(self):
        ctx = ContextBuilder()
        ctx.add("a", "1234", priority=5)
        ctx.add("b", "5678", priority=3)
        assert ctx.total_chars() == 8
