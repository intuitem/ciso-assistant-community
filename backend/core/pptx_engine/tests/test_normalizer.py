"""Tests for the TextNormalizer component."""

import pytest
from lxml import etree

from ..constants import NAMESPACES
from ..normalizer import TextNormalizer


class TestTextNormalizer:
    """Test cases for TextNormalizer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = TextNormalizer()
        self.a_ns = f"{{{NAMESPACES['a']}}}"

    def _create_paragraph(self, runs: list[tuple[str, dict | None]]) -> etree._Element:
        """
        Create a paragraph element with multiple runs.

        Args:
            runs: List of (text, properties) tuples

        Returns:
            A paragraph element
        """
        nsmap = {"a": NAMESPACES["a"]}
        p = etree.Element(f"{self.a_ns}p", nsmap=nsmap)

        for text, props in runs:
            r = etree.SubElement(p, f"{self.a_ns}r")
            if props:
                rPr = etree.SubElement(r, f"{self.a_ns}rPr")
                for key, value in props.items():
                    rPr.set(key, value)
            t = etree.SubElement(r, f"{self.a_ns}t")
            t.text = text

        return p

    def _get_paragraph_text(self, p: etree._Element) -> str:
        """Get concatenated text from a paragraph."""
        texts = []
        for t in p.iter(f"{self.a_ns}t"):
            if t.text:
                texts.append(t.text)
        return "".join(texts)

    def _count_runs(self, p: etree._Element) -> int:
        """Count the number of runs in a paragraph."""
        return len(p.findall(f"{self.a_ns}r"))

    def test_single_run_unchanged(self):
        """A paragraph with a single run should not be modified."""
        p = self._create_paragraph([("Hello {{name}}", None)])

        self.normalizer.normalize_paragraph(p)

        assert self._get_paragraph_text(p) == "Hello {{name}}"
        assert self._count_runs(p) == 1

    def test_no_placeholders_unchanged(self):
        """Paragraphs without placeholders should not be modified."""
        p = self._create_paragraph(
            [
                ("Hello ", None),
                ("World", {"b": "1"}),
            ]
        )

        original_runs = self._count_runs(p)
        self.normalizer.normalize_paragraph(p)

        assert self._get_paragraph_text(p) == "Hello World"
        assert self._count_runs(p) == original_runs

    def test_split_placeholder_merged(self):
        """A placeholder split across runs should be merged."""
        p = self._create_paragraph(
            [
                ("{{", None),
                ("name", None),
                ("}}", None),
            ]
        )

        self.normalizer.normalize_paragraph(p)

        assert self._get_paragraph_text(p) == "{{name}}"
        assert self._count_runs(p) == 1

    def test_split_placeholder_with_surrounding_text(self):
        """A split placeholder with surrounding text should preserve that text."""
        p = self._create_paragraph(
            [
                ("Hello {{", None),
                ("user", None),
                ("}}, welcome!", None),
            ]
        )

        self.normalizer.normalize_paragraph(p)

        assert self._get_paragraph_text(p) == "Hello {{user}}, welcome!"

    def test_multiple_placeholders_both_merged(self):
        """Multiple split placeholders should all be merged."""
        p = self._create_paragraph(
            [
                ("{{", None),
                ("first", None),
                ("}} and {{", None),
                ("second", None),
                ("}}", None),
            ]
        )

        self.normalizer.normalize_paragraph(p)

        text = self._get_paragraph_text(p)
        assert "{{first}}" in text
        assert "{{second}}" in text

    def test_preserves_first_run_formatting(self):
        """Merged runs should preserve the formatting of the first run."""
        p = self._create_paragraph(
            [
                ("{{", {"b": "1", "i": "1"}),
                ("name", None),
                ("}}", None),
            ]
        )

        self.normalizer.normalize_paragraph(p)

        # Check that the merged run has the formatting from the first run
        first_run = p.find(f"{self.a_ns}r")
        rPr = first_run.find(f"{self.a_ns}rPr")

        assert rPr is not None
        assert rPr.get("b") == "1"
        assert rPr.get("i") == "1"

    def test_image_placeholder_merged(self):
        """Image placeholders should also be merged."""
        p = self._create_paragraph(
            [
                ("{{image:", None),
                ("logo", None),
                ("}}", None),
            ]
        )

        self.normalizer.normalize_paragraph(p)

        assert self._get_paragraph_text(p) == "{{image:logo}}"

    def test_each_placeholder_merged(self):
        """Loop placeholders should also be merged."""
        p = self._create_paragraph(
            [
                ("{{#each ", None),
                ("items", None),
                ("}}", None),
            ]
        )

        self.normalizer.normalize_paragraph(p)

        assert self._get_paragraph_text(p) == "{{#each items}}"

    def test_normalize_slide(self):
        """normalize_slide should process all paragraphs in a slide."""
        nsmap = {"a": NAMESPACES["a"], "p": NAMESPACES["p"]}
        slide = etree.Element(f"{{{NAMESPACES['p']}}}sld", nsmap=nsmap)

        # Create shape with split placeholder
        sp = etree.SubElement(slide, f"{{{NAMESPACES['p']}}}sp")
        txBody = etree.SubElement(sp, f"{{{NAMESPACES['p']}}}txBody")
        p = etree.SubElement(txBody, f"{self.a_ns}p")

        for text in ["{{", "name", "}}"]:
            r = etree.SubElement(p, f"{self.a_ns}r")
            t = etree.SubElement(r, f"{self.a_ns}t")
            t.text = text

        self.normalizer.normalize_slide(slide)

        # Verify normalization happened
        all_text = "".join(t.text for t in slide.iter(f"{self.a_ns}t") if t.text)
        assert all_text == "{{name}}"
