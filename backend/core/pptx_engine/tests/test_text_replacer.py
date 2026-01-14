"""Tests for the TextReplacer component."""

import pytest
from lxml import etree

from ..constants import NAMESPACES
from ..exceptions import MissingContextError
from ..replacers.text import TextReplacer


class TestTextReplacer:
    """Test cases for TextReplacer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.a_ns = f"{{{NAMESPACES['a']}}}"

    def _create_slide_with_text(self, text: str) -> etree._Element:
        """Create a minimal slide structure with text."""
        nsmap = {"a": NAMESPACES["a"], "p": NAMESPACES["p"]}
        slide = etree.Element(f"{{{NAMESPACES['p']}}}sld", nsmap=nsmap)
        sp = etree.SubElement(slide, f"{{{NAMESPACES['p']}}}sp")
        txBody = etree.SubElement(sp, f"{{{NAMESPACES['p']}}}txBody")
        p = etree.SubElement(txBody, f"{self.a_ns}p")
        r = etree.SubElement(p, f"{self.a_ns}r")
        t = etree.SubElement(r, f"{self.a_ns}t")
        t.text = text
        return slide

    def _get_slide_text(self, slide: etree._Element) -> str:
        """Extract all text from a slide."""
        texts = []
        for t in slide.iter(f"{self.a_ns}t"):
            if t.text:
                texts.append(t.text)
        return "".join(texts)

    def test_simple_replacement(self):
        """Simple placeholder should be replaced."""
        slide = self._create_slide_with_text("Hello {{name}}!")
        context = {"name": "World"}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        assert self._get_slide_text(slide) == "Hello World!"

    def test_multiple_replacements(self):
        """Multiple placeholders should all be replaced."""
        slide = self._create_slide_with_text("{{greeting}} {{name}}!")
        context = {"greeting": "Hello", "name": "World"}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        assert self._get_slide_text(slide) == "Hello World!"

    def test_nested_context_access(self):
        """Nested context values should be accessible via dot notation."""
        slide = self._create_slide_with_text("Name: {{user.name}}")
        context = {"user": {"name": "John Doe"}}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        assert self._get_slide_text(slide) == "Name: John Doe"

    def test_deeply_nested_context(self):
        """Deeply nested values should be accessible."""
        slide = self._create_slide_with_text("{{a.b.c.d}}")
        context = {"a": {"b": {"c": {"d": "deep value"}}}}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        assert self._get_slide_text(slide) == "deep value"

    def test_missing_value_non_strict(self):
        """In non-strict mode, missing values should leave placeholder."""
        slide = self._create_slide_with_text("{{missing}}")
        context = {}

        replacer = TextReplacer(context, strict=False)
        replacer.replace_in_slide(slide)

        assert self._get_slide_text(slide) == "{{missing}}"

    def test_missing_value_strict(self):
        """In strict mode, missing values should raise error."""
        slide = self._create_slide_with_text("{{missing}}")
        context = {}

        replacer = TextReplacer(context, strict=True)

        with pytest.raises(MissingContextError) as exc_info:
            replacer.replace_in_slide(slide, slide_num=1)

        assert "missing" in str(exc_info.value)

    def test_boolean_true_conversion(self):
        """Boolean True should be converted to 'Yes'."""
        slide = self._create_slide_with_text("Active: {{active}}")
        context = {"active": True}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        assert self._get_slide_text(slide) == "Active: Yes"

    def test_boolean_false_conversion(self):
        """Boolean False should be converted to 'No'."""
        slide = self._create_slide_with_text("Active: {{active}}")
        context = {"active": False}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        assert self._get_slide_text(slide) == "Active: No"

    def test_list_conversion(self):
        """Lists should be joined with commas."""
        slide = self._create_slide_with_text("Items: {{items}}")
        context = {"items": ["a", "b", "c"]}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        assert self._get_slide_text(slide) == "Items: a, b, c"

    def test_number_conversion(self):
        """Numbers should be converted to strings."""
        slide = self._create_slide_with_text("Count: {{count}}")
        context = {"count": 42}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        assert self._get_slide_text(slide) == "Count: 42"

    def test_none_value(self):
        """None values should be converted to empty string."""
        slide = self._create_slide_with_text("Value: {{value}}")
        context = {"value": None}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        assert self._get_slide_text(slide) == "Value: "

    def test_image_placeholder_skipped(self):
        """Image placeholders should not be replaced by TextReplacer."""
        slide = self._create_slide_with_text("{{image:logo}}")
        context = {"logo": "/path/to/logo.png"}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        # Should remain unchanged
        assert self._get_slide_text(slide) == "{{image:logo}}"

    def test_loop_placeholder_skipped(self):
        """Loop placeholders should not be replaced by TextReplacer."""
        slide = self._create_slide_with_text("{{#each items}}{{/each}}")
        context = {"items": [1, 2, 3]}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide)

        # Should remain unchanged
        assert "{{#each items}}" in self._get_slide_text(slide)

    def test_replacement_summary(self):
        """Replacer should track replacements made."""
        slide = self._create_slide_with_text("{{a}} {{b}}")
        context = {"a": "1", "b": "2"}

        replacer = TextReplacer(context)
        replacer.replace_in_slide(slide, slide_num=1)

        summary = replacer.get_replacement_summary()
        assert summary["total_replacements"] == 2
        assert summary["unique_placeholders"] == 2
