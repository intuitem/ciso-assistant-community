"""
Structured context assembly for LLM prompts.

Instead of concatenating strings, sections are accumulated with priorities.
When the total context exceeds the budget, lowest-priority sections are
truncated or dropped.
"""

from dataclasses import dataclass, field


@dataclass
class _Section:
    name: str
    content: str
    priority: int  # higher = more important, kept first


class ContextBuilder:
    """
    Accumulate context sections with priorities, then build a single string
    that fits within a character budget.

    Usage:
        ctx = ContextBuilder(max_chars=8000)
        ctx.add("language", "LANGUAGE: You MUST respond in French.", priority=10)
        ctx.add("query_result", formatted_result, priority=9)
        ctx.add("rag", rag_context, priority=4)
        result = ctx.build()
    """

    def __init__(self, max_chars: int = 12000):
        self.max_chars = max_chars
        self._sections: list[_Section] = []

    def add(self, name: str, content: str, priority: int = 5) -> "ContextBuilder":
        """Add a named section. Empty/None content is silently skipped."""
        if content and content.strip():
            self._sections.append(
                _Section(name=name, content=content.strip(), priority=priority)
            )
        return self

    def build(self) -> str:
        """
        Assemble sections into a single string, respecting the character budget.
        Sections are ordered by priority (highest first in the output).
        If total exceeds budget, lowest-priority sections are truncated or dropped.
        """
        if not self._sections:
            return ""

        # Sort by priority descending
        ordered = sorted(self._sections, key=lambda s: s.priority, reverse=True)

        # First pass: check if everything fits
        total = (
            sum(len(s.content) for s in ordered) + (len(ordered) - 1) * 2
        )  # \n\n separators
        if total <= self.max_chars:
            return "\n\n".join(s.content for s in ordered)

        # Second pass: include sections from highest priority, truncating/dropping as needed
        parts = []
        remaining = self.max_chars
        for section in ordered:
            if remaining <= 0:
                break
            content = section.content
            if len(content) > remaining:
                # Truncate this section to fit
                content = content[: remaining - 20] + "\n... (truncated)"
            parts.append(content)
            remaining -= len(content) + 2  # account for \n\n separator

        return "\n\n".join(parts)

    def total_chars(self) -> int:
        """Total characters across all sections (before budget enforcement)."""
        return sum(len(s.content) for s in self._sections)

    def section_names(self) -> list[str]:
        """Names of all added sections (in insertion order)."""
        return [s.name for s in self._sections]
