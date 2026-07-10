"""Priority-ordered context sections with token-budget truncation."""

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
    """Priority-ordered sections; truncates/drops low priority when over budget."""

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
            max_tokens = max_chars // 3
        self.max_tokens = max_tokens
        self._sections: list[_Section] = []

    def add(self, name: str, content: str, priority: int = 5) -> "ContextBuilder":
        """Empty/None content is silently skipped."""
        if content and content.strip():
            self._sections.append(
                _Section(name=name, content=content.strip(), priority=priority)
            )
        return self

    def build(self) -> str:
        if not self._sections:
            return ""

        ordered = sorted(self._sections, key=lambda s: s.priority, reverse=True)

        total = (
            sum(count_tokens(s.content) for s in ordered)
            + (len(ordered) - 1) * _SEP_TOKENS
        )
        if total <= self.max_tokens:
            return _SEPARATOR.join(s.content for s in ordered)

        # Separator accounting adds _SEP_TOKENS unconditionally per section (including
        # the first). Preserved from the char-based original — slight slack, harmless.
        parts = []
        remaining = self.max_tokens
        for section in ordered:
            if remaining <= 0:
                break
            content = section.content
            section_tokens = count_tokens(content)
            if section_tokens > remaining:
                available = remaining - _TAIL_TOKENS
                if available <= 0:
                    break
                content = truncate_to_tokens(content, available) + _TRUNCATED_TAIL
                section_tokens = count_tokens(content)
                if section_tokens > remaining:
                    break
            parts.append(content)
            remaining -= section_tokens + _SEP_TOKENS

        return _SEPARATOR.join(parts)

    def total_tokens(self) -> int:
        return sum(count_tokens(s.content) for s in self._sections)

    def total_chars(self) -> int:
        """Deprecated. Use total_tokens()."""
        warnings.warn(
            "ContextBuilder.total_chars() is deprecated; use total_tokens().",
            DeprecationWarning,
            stacklevel=2,
        )
        return sum(len(s.content) for s in self._sections)

    def section_names(self) -> list[str]:
        return [s.name for s in self._sections]
