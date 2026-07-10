"""Regression: docxtpl rendering of admin-uploaded Word templates must run
inside a Jinja2 sandbox so a malicious .docx can't RCE via classic
`{{ ''.__class__.__mro__[1].__subclasses__()[...] }}` payloads."""

import io

import pytest
from docx import Document
from docxtpl import DocxTemplate
from jinja2.exceptions import SecurityError
from jinja2.sandbox import SandboxedEnvironment


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
