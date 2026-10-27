"""Regression: docxtpl rendering of admin-uploaded Word templates must run
inside a Jinja2 sandbox so a malicious .docx can't RCE via classic
`{{ ''.__class__.__mro__[1].__subclasses__()[...] }}` payloads."""

import io
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from docx import Document
from docxtpl import DocxTemplate
from jinja2.exceptions import SecurityError
from jinja2.sandbox import SandboxedEnvironment
from PIL import Image

from core.generators import (
    AUDIT_CHART_KEYS,
    DocxReportSandbox,
    gen_audit_context,
    inline_charts_for_docx,
    render_docx_report,
    render_docx_report_bounded,
)
from core.models import AppliedControl, RequirementAssessment
from core.tests.test_audit_word_export import app_config, audit  # noqa: F401
from core.views import get_sorted_requirement_nodes


_SSTI_PAYLOAD = "{{ ''.__class__.__mro__[1].__subclasses__()[0] }}"


def _docx_with(text: str) -> io.BytesIO:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def test_sandbox_blocks_ssti():
    template = DocxTemplate(_docx_with(_SSTI_PAYLOAD))
    with pytest.raises(SecurityError):
        template.render({}, jinja_env=SandboxedEnvironment())


def test_unsandboxed_render_lets_ssti_through():
    """Positive control: without the sandbox the payload renders fine,
    documenting why the sandbox is required."""
    template = DocxTemplate(_docx_with(_SSTI_PAYLOAD))
    template.render({})  # would expose <class 'type'> in the rendered doc


def _png() -> io.BytesIO:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buf, format="PNG")
    buf.seek(0)
    return buf


_TPL = "{%- set tpl = compliance_donut.tpl -%}"


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            _TPL
            + "{{ tpl.render_xml_part(\"{{ ''.__class__.__name__ }}\", tpl.docx.part, {}) }}",
            id="render_xml_part",
        ),
        pytest.param(_TPL + "{{ tpl.build_xml({}) }}", id="build_xml"),
        pytest.param(_TPL + "{{ tpl.render_properties({}) }}", id="render_properties"),
        pytest.param(_TPL + "{{ tpl.get_xml()|length }}", id="get_xml"),
        pytest.param(_TPL + "{{ tpl.write_xml(target) }}", id="write_xml"),
        pytest.param(_TPL + "{{ tpl.save(target) }}", id="save"),
    ],
)
def test_report_template_cannot_reach_the_docx_template(payload: str, tmp_path) -> None:
    target = tmp_path / "written"
    template = DocxTemplate(_docx_with(payload))
    with pytest.raises(SecurityError):
        render_docx_report(
            template, {"compliance_donut": _png(), "target": str(target)}
        )
    assert not target.exists()


def test_report_template_still_renders_charts() -> None:
    template = DocxTemplate(_docx_with("{{ compliance_donut }}"))
    render_docx_report(template, {"compliance_donut": _png()})
    out = io.BytesIO()
    template.save(out)
    out.seek(0)
    assert len(Document(out).inline_shapes) == 1


@pytest.mark.parametrize(
    "value, payload",
    [
        pytest.param(Document(), "{{ value.save(target) }}", id="docx_document"),
        pytest.param(
            np.float64(1.5), "{{ value.tofile(target) }}", id="float_subclass"
        ),
    ],
)
def test_report_template_cannot_use_other_objects(
    value: object, payload: str, tmp_path: Path
) -> None:
    target = tmp_path / "written"
    template = DocxTemplate(_docx_with(payload))
    with pytest.raises(SecurityError):
        render_docx_report(template, {"value": value, "target": str(target)})
    assert not target.exists()


def test_report_template_cannot_mutate_the_context() -> None:
    rows = [1, 2]
    template = DocxTemplate(_docx_with("{{ rows.clear() }}"))
    with pytest.raises(SecurityError):
        render_docx_report(template, {"rows": rows})
    assert rows == [1, 2]


def test_bounded_render_returns_the_report() -> None:
    report = render_docx_report_bounded(
        DocxTemplate(_docx_with("{{ name }}")), {"name": "audit"}
    )
    assert Document(io.BytesIO(report)).paragraphs[0].text == "audit"


def test_bounded_render_fails_on_template_errors() -> None:
    with pytest.raises(EOFError):
        render_docx_report_bounded(DocxTemplate(_docx_with(_SSTI_PAYLOAD)), {})


def test_bounded_render_stops_runaway_templates(monkeypatch) -> None:
    monkeypatch.setattr("core.generators.DOCX_RENDER_TIMEOUT", 1)
    template = DocxTemplate(
        _docx_with(
            "{% for i in range(99999) %}{% for j in range(99999) %}"
            "{% endfor %}{% endfor %}"
        )
    )
    with pytest.raises(TimeoutError):
        render_docx_report_bounded(template, {})


def _rendered_text(template: DocxTemplate) -> str:
    out = io.BytesIO()
    template.save(out)
    out.seek(0)
    return "\n".join(p.text for p in Document(out).paragraphs)


def test_report_template_keeps_the_usual_jinja_features() -> None:
    template = DocxTemplate(
        _docx_with(
            "{% set ns = namespace(total=0) %}{% set c = cycler('a', 'b') %}"
            "{% for row in rows %}{{ loop.index }}{{ c.next() }}"
            "{% set ns.total = ns.total + row.score %}{% endfor %}"
            "|{{ ns.total }}|{{ (name|e).upper() }}|{{ eta.strftime('%Y') }}"
            "|{% for k, v in req.items() %}{{ k }}{{ v }}{% endfor %}"
            "|{% for g in rows|groupby('kind') %}{{ g.grouper }}{{ g.list|length }}{% endfor %}"
        )
    )
    render_docx_report(
        template,
        {
            "rows": [{"score": 2, "kind": "x"}, {"score": 3, "kind": "x"}],
            "name": "audit",
            "eta": date(2026, 1, 1),
            "req": {"total": 4},
        },
    )
    assert _rendered_text(template) == "1a2b|5|AUDIT|2026|total4|x2"


def _template_values(value: object):
    yield value
    children = [*value.keys(), *value.values()] if isinstance(value, dict) else value
    if isinstance(value, (dict, list, tuple)):
        for child in children:
            yield from _template_values(child)


@pytest.fixture
def report_context(audit) -> dict:  # noqa: F811
    ras = list(RequirementAssessment.objects.filter(compliance_assessment=audit))
    for ra, result in zip(ras, RequirementAssessment.Result.values):
        ra.result = result
        ra.observation = "Observed"
        ra.save()
    control = AppliedControl.objects.create(
        name="Firewall", folder=audit.folder, priority=1, eta=date(2026, 6, 30)
    )
    ras[0].applied_controls.add(control)
    tree = get_sorted_requirement_nodes(
        audit.framework.requirement_nodes.all(),
        RequirementAssessment.objects.filter(compliance_assessment=audit),
        audit.framework.max_score,
        audit.framework.min_score,
    )
    return gen_audit_context(audit.id, tree, "en")


@pytest.mark.django_db
def test_report_context_only_holds_what_the_template_may_read(
    report_context: dict,
) -> None:
    sandbox = DocxReportSandbox()
    data = {k: v for k, v in report_context.items() if k not in AUDIT_CHART_KEYS}
    opaque = [
        type(v)
        for v in _template_values(data)
        if v is not None and not sandbox.is_safe_attribute(v, "attr", None)
    ]
    assert opaque == []


def _render_xml(template_path: Path, context: dict, jinja_env) -> bytes:
    template = DocxTemplate(template_path)
    template.render(inline_charts_for_docx(context, template), jinja_env=jinja_env)
    out = io.BytesIO()
    template.save(out)
    with zipfile.ZipFile(out) as zf:
        return zf.read("word/document.xml")


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_shipped_templates_render_as_with_the_stock_sandbox(
    report_context: dict, lang: str
) -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "core"
        / f"audit_report_template_{lang}.docx"
    )
    assert _render_xml(path, report_context, DocxReportSandbox()) == _render_xml(
        path, report_context, SandboxedEnvironment()
    )
