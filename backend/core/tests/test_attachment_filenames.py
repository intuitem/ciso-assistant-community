"""Uploaded names must survive the round trip to an exported archive."""

from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.http.multipartparser import parse_header_parameters

from core.validators import (
    ALLOWED_UPLOAD_EXTENSIONS,
    _validate_file_extension_and_sanitize,
    sanitize_file_name,
)


class _Upload:
    """The validator only touches `.name`."""

    def __init__(self, name):
        self.name = name


def _sanitized(name):
    upload = _Upload(name)
    _validate_file_extension_and_sanitize(upload, ALLOWED_UPLOAD_EXTENSIONS)
    return upload.name


@pytest.mark.parametrize(
    "uploaded,stored",
    [
        ("Procédure de gestion.pdf", "Procédure de gestion.pdf"),
        ("ÉTAT des lieux (v2).docx", "ÉTAT des lieux (v2).docx"),
        ("Plan d'action 2026.xlsx", "Plan d'action 2026.xlsx"),
        ("Rapport.PDF", "Rapport.pdf"),
        ("pdf-guide.pdf", "pdf-guide.pdf"),
    ],
)
def test_readable_names_survive(uploaded, stored):
    assert _sanitized(uploaded) == stored


@pytest.mark.parametrize(
    "uploaded,stored",
    [
        ("../../etc/passwd.txt", "passwd.txt"),
        (r"C:\Users\bob\Plan.xlsx", "Plan.xlsx"),
        ("a\x00b\tc.png", "abc.png"),
        ("  ..hidden..  .txt", "hidden.txt"),
        ("re<port>:1.csv", "re-port--1.csv"),
    ],
)
def test_unsafe_names_are_defused(uploaded, stored):
    assert _sanitized(uploaded) == stored


def test_a_name_sanitized_down_to_nothing_still_yields_a_file():
    assert _sanitized(". .pdf") == "file.pdf"


def test_extension_allowlist_still_applies():
    with pytest.raises(ValidationError):
        _sanitized("payload.exe")
    # A dotfile has no extension to match.
    with pytest.raises(ValidationError):
        _sanitized("///.pdf")


def test_rfc5987_header_reaches_the_backend_intact():
    """Mirrors frontend/src/lib/utils/contentDisposition.ts by hand."""
    name = "Procédure de gestion.pdf"
    ascii_fallback = "Proc-dure de gestion.pdf"
    header = (
        f'attachment; filename="{ascii_fallback}"; '
        "filename*=utf-8''Proc%C3%A9dure%20de%20gestion.pdf"
    )
    _, params = parse_header_parameters(header)
    assert params["filename"] == name
    assert sanitize_file_name(params["filename"]) == name


def test_archive_names_disambiguate_collisions():
    from core.views import build_evidence_archive_names

    class _Revision:
        def __init__(self, name):
            self.attachment = SimpleNamespace(name=f"evidence/{name}")
            self.filename = lambda: name

    class _Evidence:
        def __init__(self, id, attachment):
            self.id = id
            self.last_revision = _Revision(attachment) if attachment else None

    evidences = [
        _Evidence("1", "Procédure.pdf"),
        _Evidence("2", "Procédure.pdf"),
        _Evidence("3", "PROCÉDURE.pdf"),
        _Evidence("4", None),
    ]
    names = build_evidence_archive_names(evidences)

    assert names["1"] == "Procédure.pdf"
    assert names["2"] == "Procédure (2).pdf"
    assert names["3"] == "PROCÉDURE (3).pdf"
    assert "4" not in names
    assert len({n.lower() for n in names.values()}) == len(names)


@pytest.mark.parametrize(
    "hostile",
    [
        "../../etc/passwd.pdf",
        "../../../root/.ssh/authorized_keys.txt",
        r"..\..\Windows\System32\drivers\etc\hosts.txt",
        "evidences/../../escape.pdf",
        "/absolute/path.pdf",
    ],
)
def test_archive_entry_names_cannot_traverse(hostile):
    """AnswerAttachment.filename is external input and follows the file on promotion."""
    from core.views import build_evidence_archive_names

    class _Revision:
        def __init__(self, name):
            self.attachment = SimpleNamespace(name="evidence/stored.pdf")
            self.filename = lambda: name

    class _Evidence:
        def __init__(self, id, name):
            self.id = id
            self.last_revision = _Revision(name)

    entry = build_evidence_archive_names([_Evidence("1", hostile)])["1"]

    assert "/" not in entry
    assert "\\" not in entry
    assert not entry.startswith(".")
    assert ".." not in entry.split(".pdf")[0]


def test_a_long_name_keeps_its_extension():
    """Answer attachments cap size but not name length."""
    long_stem = "Procédure " * 40
    sanitized = sanitize_file_name(f"{long_stem}.pdf")

    assert len(sanitized) <= 255
    assert sanitized.endswith(".pdf")
    assert sanitized.startswith("Procédure")


def test_truncation_does_not_leave_a_trailing_space_before_the_extension():
    sanitized = sanitize_file_name("a" * 250 + " b.pdf")
    assert len(sanitized) <= 255
    assert ". " not in sanitized and " ." not in sanitized


def test_a_name_that_is_all_extension_is_still_bounded():
    sanitized = sanitize_file_name("x." + "y" * 300, max_length=50)
    assert len(sanitized) == 50
