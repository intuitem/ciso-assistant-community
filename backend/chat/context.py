"""
Structured context assembly for LLM prompts.

Instead of concatenating strings, sections are accumulated with priorities.
When the total context exceeds the budget, lowest-priority sections are
truncated or dropped.
"""

import warnings
from dataclasses import dataclass

from .tokens import count_tokens, truncate_to_tokens


_SEPARATOR = "\n\n"
_SEP_TOKENS = count_tokens(_SEPARATOR)
_TRUNCATED_TAIL = "\n... (truncated)"
_TAIL_TOKENS = count_tokens(_TRUNCATED_TAIL)


@dataclass
class _Section:
    name: str
    content: str
    priority: int  # higher = more important, kept first


class ContextBuilder:
    """
    Accumulate context sections with priorities, then build a single string
    that fits within a token budget.

    Usage:
        ctx = ContextBuilder(max_tokens=2400)
        ctx.add("language", "LANGUAGE: You MUST respond in French.", priority=10)
        ctx.add("query_result", formatted_result, priority=9)
        ctx.add("rag", rag_context, priority=4)
        result = ctx.build()
    """

    def __init__(
        self,
        max_tokens: int = 2400,
        max_chars: int | None = None,
    ):
        if max_chars is not None:
            warnings.warn(
                "ContextBuilder(max_chars=…) is deprecated; use max_tokens=… instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            # ~3 chars/token heuristic, matches tokens.py
            max_tokens = max_chars // 3
        self.max_tokens = max_tokens
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
        Assemble sections into a single string, respecting the token budget.
        Sections are ordered by priority (highest first in the output).
        If total exceeds budget, lowest-priority sections are truncated or dropped.
        """
        if not self._sections:
            return ""

        ordered = sorted(self._sections, key=lambda s: s.priority, reverse=True)

        # First pass: check if everything fits
        total = (
            sum(count_tokens(s.content) for s in ordered)
            + (len(ordered) - 1) * _SEP_TOKENS
        )
        if total <= self.max_tokens:
            return _SEPARATOR.join(s.content for s in ordered)

        # Second pass: include sections from highest priority, truncating/dropping as needed.
        # Separator accounting (+_SEP_TOKENS unconditionally per section, including the first)
        # is preserved from the previous char-based implementation — slight slack, harmless.
        parts = []
        remaining = self.max_tokens
        for section in ordered:
            if remaining <= 0:
                break
            content = section.content
            section_tokens = count_tokens(content)
            if section_tokens > remaining:
                content = (
                    truncate_to_tokens(content, remaining - _TAIL_TOKENS)
                    + _TRUNCATED_TAIL
                )
                section_tokens = count_tokens(content)
            parts.append(content)
            remaining -= section_tokens + _SEP_TOKENS

        return _SEPARATOR.join(parts)

    def total_tokens(self) -> int:
        """Total tokens across all sections (before budget enforcement)."""
        return sum(count_tokens(s.content) for s in self._sections)

    def total_chars(self) -> int:
        """Deprecated alias — returns char count for compatibility."""
        warnings.warn(
            "ContextBuilder.total_chars() is deprecated; use total_tokens().",
            DeprecationWarning,
            stacklevel=2,
        )
        return sum(len(s.content) for s in self._sections)

    def section_names(self) -> list[str]:
        """Names of all added sections (in insertion order)."""
        return [s.name for s in self._sections]
