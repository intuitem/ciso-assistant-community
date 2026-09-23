"""Markdown fields in server-rendered exports."""

import shutil

import pymupdf
import pytest

from core import typst_render
from core.generators import findings_assessment_context
from core.markdown_render import MAX_DEPTH, markdown_html, markdown_tree
from core.models import Finding, FindingsAssessment
from core.tests.test_audit_word_export import app_config  # noqa: F401
from core.typst_render import SHARED_MODULES, localized_template, render_pdf
from iam.models import Folder


def _text(pdf):
    return "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))


@pytest.fixture
def probe(tmp_path, monkeypatch):
    """Renders `#md(d.value)` alone, with the shared modules beside it."""
    for name in SHARED_MODULES:
        shutil.copy(typst_render.TEMPLATE_DIR / name, tmp_path / name)
    (tmp_path / "probe.typ").write_text(
        '#import "_markdown.typ": md\n'
        "#let d = json(bytes(sys.inputs.data))\n"
        "#md(d.value)\n"
    )
    monkeypatch.setattr(typst_render, "TEMPLATE_DIR", tmp_path)
    return lambda value: _text(render_pdf("probe.typ", {"value": value}))


@pytest.mark.parametrize("value", ["", "-", None, 3])
def test_empty_and_placeholder_values_pass_through(value):
    assert markdown_tree(value) == value


def test_tree_shape():
    tree = markdown_tree("Some **bold**\n\n- one\n- two")
    assert tree == {
        "t": "md",
        "c": [
            {"t": "p", "c": ["Some ", {"t": "strong", "c": ["bold"]}]},
            {
                "t": "ul",
                "c": [
                    {"t": "li", "c": [{"t": "span", "c": ["one"]}]},
                    {"t": "li", "c": [{"t": "span", "c": ["two"]}]},
                ],
            },
        ],
    }


def test_single_newline_is_a_line_break_as_in_the_app():
    tree = markdown_tree("line one\nline two")
    assert tree["c"][0]["c"] == ["line one", {"t": "br"}, "line two"]
    assert "<br" in markdown_html("line one\nline two")


def test_only_web_and_mail_links_survive():
    tree = markdown_tree("[a](https://x.example) [b](file:///etc/passwd)")
    paragraph = tree["c"][0]["c"]
    assert paragraph[0] == {"t": "a", "href": "https://x.example", "c": ["a"]}
    assert not any(isinstance(n, dict) and n["t"] == "a" for n in paragraph[1:])


def test_deep_nesting_is_flattened_not_dropped():
    tree = markdown_tree(">" * (MAX_DEPTH * 3) + " bottom")

    def depth(node):
        if not isinstance(node, dict):
            return 0
        return 1 + max((depth(c) for c in node.get("c", [])), default=0)

    assert depth(tree) <= MAX_DEPTH + 2
    assert "bottom" in str(tree)


def test_markdown_is_rendered_not_printed(probe):
    text = probe(
        markdown_tree(
            "# Title\n\n**bold** and _it_\n\n- item\n\n| a | b |\n|---|---|\n| 1 | 2 |"
        )
    )
    for word in ("Title", "bold", "it", "item", "a", "b", "1", "2"):
        assert word in text
    for syntax in ("**", "# ", "_it_", "|---"):
        assert syntax not in text


def test_typst_syntax_in_user_text_stays_literal(probe):
    text = probe(markdown_tree('#read("/etc/passwd") $x$ *not bold* `#raw`'))
    assert '#read("/etc/passwd")' in text
    assert "$x$" in text
    assert "#raw" in text


def test_plain_strings_still_render(probe):
    assert "plain **text**" in probe("plain **text**")


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_findings_report_renders_markdown(app_config, lang):  # noqa: F811
    folder = Folder.objects.create(
        name="Markdown domain", content_type=Folder.ContentType.DOMAIN
    )
    assessment = FindingsAssessment.objects.create(
        name="Pentest",
        folder=folder,
        description="Scope: **production** only",
        observation="- first point\n- second point",
    )
    Finding.objects.create(
        findings_assessment=assessment,
        folder=folder,
        ref_id="F-001",
        name="Weak TLS",
        severity=3,
        status="identified",
        description="Uses `TLSv1.0` on _edge_ nodes",
        observation="See [the policy](https://example.com/tls)",
    )
    findings = Finding.objects.filter(findings_assessment=assessment)
    payload = findings_assessment_context(assessment, findings, lang)
    text = _text(render_pdf(localized_template("findings_report", lang), payload))

    assert "production" in text and "**production**" not in text
    assert "first point" in text and "- first point" not in text
    assert "TLSv1.0" in text and "`" not in text
    assert "the policy" in text and "](https://" not in text


def test_html_escapes_raw_html_and_unsafe_links():
    html = markdown_html(
        '<img src=x onerror="alert(1)"> [x](javascript:alert(1)) [ok](https://a.example)'
    )
    assert "<img" not in html
    assert 'href="javascript' not in html
    assert '<a href="https://a.example">ok</a>' in html


@pytest.mark.parametrize("value", ["", "   ", None])
def test_html_of_nothing_is_empty(value):
    assert markdown_html(value) == ""
