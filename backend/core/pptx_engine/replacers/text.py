"""
Text placeholder replacer for PPTX templates.

Handles {{variable}} style placeholders, replacing them with values from the context.
"""

import re
from typing import Any
from lxml import etree

from ..constants import NAMESPACES, PLACEHOLDER_PATTERN, IMAGE_PLACEHOLDER_PATTERN
from ..exceptions import MissingContextError
from ..utils import resolve_context_value


class TextReplacer:
    """
    Replaces text placeholders in PPTX XML with values from a context dictionary.
    """

    def __init__(self, context: dict[str, Any], strict: bool = False):
        """
        Initialize the text replacer.

        Args:
            context: Dictionary of values to substitute
            strict: If True, raise error on missing variables; if False, leave placeholder
        """
        self.context = context
        self.strict = strict
        self.a_ns = f"{{{NAMESPACES['a']}}}"
        # Track replacements made
        self.replacements_made: list[dict] = []

    def replace_in_slide(
        self, slide_root: etree._Element, slide_num: int = None
    ) -> etree._Element:
        """
        Replace all text placeholders in a slide.

        Args:
            slide_root: Root element of a slide XML
            slide_num: Slide number for error reporting

        Returns:
            The modified slide root
        """
        # Process all text elements
        for t_elem in slide_root.iter(f"{self.a_ns}t"):
            if t_elem.text:
                t_elem.text = self._replace_in_text(t_elem.text, slide_num)

        return slide_root

    def _replace_in_text(self, text: str, slide_num: int = None) -> str:
        """
        Replace placeholders in a text string.

        Args:
            text: Text containing placeholders
            slide_num: Slide number for error reporting

        Returns:
            Text with placeholders replaced
        """

        def replacer(match: re.Match) -> str:
            full_match = match.group(0)
            placeholder_content = match.group(1)

            # Skip image placeholders - those are handled by ImageReplacer
            if placeholder_content.startswith("image:"):
                return full_match

            # Skip loop placeholders
            if placeholder_content.startswith("#") or placeholder_content.startswith(
                "/"
            ):
                return full_match

            # Resolve the value from context
            value = resolve_context_value(self.context, placeholder_content)

            if value is None:
                if self.strict:
                    raise MissingContextError(placeholder_content, slide_num)
                # Leave placeholder as-is if not strict
                return full_match

            # Convert value to string
            str_value = self._value_to_string(value)

            # Track the replacement
            self.replacements_made.append(
                {
                    "placeholder": placeholder_content,
                    "value": str_value,
                    "slide": slide_num,
                }
            )

            return str_value

        return re.sub(PLACEHOLDER_PATTERN, replacer, text)

    def _value_to_string(self, value: Any) -> str:
        """
        Convert a context value to a string for insertion.

        Args:
            value: The value to convert

        Returns:
            String representation
        """
        if value is None:
            return ""
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, (list, tuple)):
            return ", ".join(str(item) for item in value)
        return str(value)

    def get_replacement_summary(self) -> dict:
        """
        Get a summary of replacements made.

        Returns:
            Dictionary with replacement statistics
        """
        return {
            "total_replacements": len(self.replacements_made),
            "unique_placeholders": len(
                set(r["placeholder"] for r in self.replacements_made)
            ),
            "replacements": self.replacements_made,
        }


def replace_text_placeholders(
    slide_root: etree._Element,
    context: dict[str, Any],
    strict: bool = False,
    slide_num: int = None,
) -> etree._Element:
    """
    Convenience function to replace text placeholders in a slide.

    Args:
        slide_root: Root element of a slide XML
        context: Dictionary of values to substitute
        strict: If True, raise error on missing variables
        slide_num: Slide number for error reporting

    Returns:
        The modified slide root
    """
    replacer = TextReplacer(context, strict)
    return replacer.replace_in_slide(slide_root, slide_num)
