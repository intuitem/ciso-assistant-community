"""Integration tests for the PPTXTemplateEngine."""

import os
import tempfile
import zipfile
import pytest
from lxml import etree

from ..engine import PPTXTemplateEngine, render_template
from ..exceptions import InvalidTemplateError, MissingContextError


class TestPPTXTemplateEngine:
    """Integration tests for the full template engine."""

    def _create_minimal_pptx(self, slides_content: list[str]) -> str:
        """
        Create a minimal valid PPTX file for testing.

        Args:
            slides_content: List of text content for each slide

        Returns:
            Path to the created PPTX file
        """
        fd, pptx_path = tempfile.mkstemp(suffix=".pptx")
        os.close(fd)

        with zipfile.ZipFile(pptx_path, "w") as zf:
            # [Content_Types].xml
            content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>"""
            zf.writestr("[Content_Types].xml", content_types)

            # _rels/.rels
            root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""
            zf.writestr("_rels/.rels", root_rels)

            # ppt/presentation.xml
            presentation = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId2"/>
  </p:sldIdLst>
</p:presentation>"""
            zf.writestr("ppt/presentation.xml", presentation)

            # ppt/_rels/presentation.xml.rels
            pres_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>"""
            zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels)

            # Create slides
            for i, content in enumerate(slides_content):
                slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:sp>
        <p:txBody>
          <a:p>
            <a:r>
              <a:t>{content}</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>"""
                zf.writestr(f"ppt/slides/slide{i + 1}.xml", slide_xml)

        return pptx_path

    def _read_pptx_slide_text(self, pptx_path: str, slide_num: int = 1) -> str:
        """Read text content from a slide in a PPTX file."""
        with zipfile.ZipFile(pptx_path, "r") as zf:
            slide_xml = zf.read(f"ppt/slides/slide{slide_num}.xml")

        root = etree.fromstring(slide_xml)
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        texts = []
        for t in root.iter(f"{a_ns}t"):
            if t.text:
                texts.append(t.text)

        return "".join(texts)

    def test_simple_text_replacement(self):
        """Engine should replace simple text placeholders."""
        template_path = self._create_minimal_pptx(["Hello {{name}}!"])

        try:
            engine = PPTXTemplateEngine()
            output_path = engine.process(template_path, {"name": "World"})

            try:
                text = self._read_pptx_slide_text(output_path)
                assert text == "Hello World!"
            finally:
                os.unlink(output_path)
        finally:
            os.unlink(template_path)

    def test_multiple_placeholders(self):
        """Engine should replace multiple placeholders."""
        template_path = self._create_minimal_pptx(["{{greeting}} {{name}}!"])

        try:
            engine = PPTXTemplateEngine()
            output_path = engine.process(
                template_path, {"greeting": "Hello", "name": "World"}
            )

            try:
                text = self._read_pptx_slide_text(output_path)
                assert text == "Hello World!"
            finally:
                os.unlink(output_path)
        finally:
            os.unlink(template_path)

    def test_nested_context(self):
        """Engine should handle nested context values."""
        template_path = self._create_minimal_pptx(["Name: {{user.name}}"])

        try:
            engine = PPTXTemplateEngine()
            output_path = engine.process(template_path, {"user": {"name": "John Doe"}})

            try:
                text = self._read_pptx_slide_text(output_path)
                assert text == "Name: John Doe"
            finally:
                os.unlink(output_path)
        finally:
            os.unlink(template_path)

    def test_process_to_bytes(self):
        """process_to_bytes should return PPTX as bytes."""
        template_path = self._create_minimal_pptx(["Hello {{name}}!"])

        try:
            engine = PPTXTemplateEngine()
            result = engine.process_to_bytes(template_path, {"name": "World"})

            # Should be valid ZIP/PPTX data
            assert result[:4] == b"PK\x03\x04"
            assert len(result) > 100  # Should have some content
        finally:
            os.unlink(template_path)

    def test_extract_placeholders(self):
        """extract_placeholders should find all placeholders."""
        template_path = self._create_minimal_pptx(
            ["{{title}} {{image:logo}} {{#each items}}{{name}}{{/each}}"]
        )

        try:
            engine = PPTXTemplateEngine()
            placeholders = engine.extract_placeholders(template_path)

            assert "title" in placeholders["text"]
            assert "logo" in placeholders["image"]
            assert "items" in placeholders["each"]
        finally:
            os.unlink(template_path)

    def test_invalid_template_not_zip(self):
        """Should raise error for non-ZIP file."""
        fd, path = tempfile.mkstemp()
        os.write(fd, b"not a zip file")
        os.close(fd)

        try:
            engine = PPTXTemplateEngine()
            with pytest.raises(InvalidTemplateError):
                engine.process(path, {})
        finally:
            os.unlink(path)

    def test_invalid_template_not_found(self):
        """Should raise error for non-existent file."""
        engine = PPTXTemplateEngine()
        with pytest.raises(InvalidTemplateError):
            engine.process("/nonexistent/template.pptx", {})

    def test_strict_mode_missing_value(self):
        """Strict mode should raise error on missing values."""
        template_path = self._create_minimal_pptx(["Hello {{missing}}!"])

        try:
            engine = PPTXTemplateEngine(strict=True)
            with pytest.raises(MissingContextError):
                engine.process(template_path, {})
        finally:
            os.unlink(template_path)

    def test_non_strict_mode_preserves_placeholder(self):
        """Non-strict mode should preserve missing placeholders."""
        template_path = self._create_minimal_pptx(["Hello {{missing}}!"])

        try:
            engine = PPTXTemplateEngine(strict=False)
            output_path = engine.process(template_path, {})

            try:
                text = self._read_pptx_slide_text(output_path)
                assert text == "Hello {{missing}}!"
            finally:
                os.unlink(output_path)
        finally:
            os.unlink(template_path)

    def test_render_template_convenience(self):
        """render_template convenience function should work."""
        template_path = self._create_minimal_pptx(["Hello {{name}}!"])

        try:
            output_path = render_template(template_path, {"name": "World"})

            try:
                text = self._read_pptx_slide_text(output_path)
                assert text == "Hello World!"
            finally:
                os.unlink(output_path)
        finally:
            os.unlink(template_path)

    def test_file_like_input(self):
        """Engine should accept file-like objects."""
        template_path = self._create_minimal_pptx(["Hello {{name}}!"])

        try:
            engine = PPTXTemplateEngine()

            with open(template_path, "rb") as f:
                output_path = engine.process(f, {"name": "World"})

            try:
                text = self._read_pptx_slide_text(output_path)
                assert text == "Hello World!"
            finally:
                os.unlink(output_path)
        finally:
            os.unlink(template_path)

    def test_custom_output_path(self):
        """Engine should write to specified output path."""
        template_path = self._create_minimal_pptx(["Hello {{name}}!"])
        fd, output_path = tempfile.mkstemp(suffix=".pptx")
        os.close(fd)

        try:
            engine = PPTXTemplateEngine()
            result_path = engine.process(
                template_path, {"name": "World"}, output_path=output_path
            )

            assert result_path == output_path
            assert os.path.exists(output_path)

            text = self._read_pptx_slide_text(output_path)
            assert text == "Hello World!"
        finally:
            os.unlink(template_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
