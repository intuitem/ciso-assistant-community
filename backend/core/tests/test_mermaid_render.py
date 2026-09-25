"""Server-side Mermaid rendering for document PDFs."""

import markdown
from weasyprint import HTML

import pymupdf

from core.typst_render import MERMAID_MAX_SOURCE_CHARS, render_mermaid_svg
from doc_management.views import _render_mermaid_blocks, _safe_url_fetcher

FLOWCHART = "flowchart TD\n  A[Policy] --> B{Approved?}\n  B -->|yes| C[Published]\n"


def _markdown(source: str) -> str:
    return markdown.markdown(
        source, extensions=["tables", "fenced_code", "toc", "nl2br"]
    )


def _pdf_text(content_html: str) -> str:
    pdf = HTML(string=content_html, url_fetcher=_safe_url_fetcher).write_pdf()
    return "".join(page.get_text() for page in pymupdf.open(stream=pdf))


class TestRenderMermaidSvg:
    def test_renders_valid_diagram(self):
        svg = render_mermaid_svg(FLOWCHART)
        assert svg is not None
        assert svg.startswith(b"<svg")
        assert b"foreignObject" not in svg

    def test_returns_none_on_parse_error(self):
        assert render_mermaid_svg("flowchart TD\n  A[Start] -->\n  B{{{ broken") is None

    def test_skips_oversized_source(self):
        source = "flowchart TD\n  A[" + "x" * MERMAID_MAX_SOURCE_CHARS + "] --> B"
        assert render_mermaid_svg(source) is None

    def test_strips_markup_from_labels(self):
        svg = render_mermaid_svg(
            'flowchart LR\n  A["<img src=x onerror=alert(1)>Label"] --> '
            'B["<script>alert(2)</script>"]\n'
        )
        assert svg is not None
        decoded = svg.lower()
        assert b"<script" not in decoded
        assert b"onerror" not in decoded


class TestRenderMermaidBlocks:
    def test_replaces_mermaid_fence_with_diagram(self):
        content = _render_mermaid_blocks(
            _markdown(f"Intro\n\n```mermaid\n{FLOWCHART}```\n")
        )
        assert '<div class="mermaid-diagram"><svg' in content
        assert "language-mermaid" not in content

    def test_unescapes_source_before_rendering(self):
        content = _render_mermaid_blocks(
            _markdown("```mermaid\ngraph TD\n  A --> B & C\n```")
        )
        assert '<div class="mermaid-diagram">' in content

    def test_keeps_code_block_when_diagram_is_invalid(self):
        source = _markdown("```mermaid\nnot a diagram {{{\n```")
        assert _render_mermaid_blocks(source) == source

    def test_leaves_other_code_blocks_alone(self):
        source = _markdown("```python\nprint(1)\n```")
        assert _render_mermaid_blocks(source) == source

    def test_diagram_labels_reach_the_pdf(self):
        content = _render_mermaid_blocks(_markdown(f"```mermaid\n{FLOWCHART}```"))
        text = _pdf_text(f"<html><body>{content}</body></html>")
        for label in ("Policy", "Approved?", "Published"):
            assert label in text
