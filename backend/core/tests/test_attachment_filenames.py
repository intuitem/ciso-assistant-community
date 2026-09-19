"""Uploaded file names must survive the round trip to an exported archive.

SUP-1791: an evidence uploaded as "Procédure de gestion.pdf" came out of the audit
archive as "procc3a9dure20de20gestion.pdf" — the frontend percent-encoded the name into
a plain `filename=` param, and the backend then slugified whatever reached it.
"""

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
    """Stands in for an UploadedFile: the validator only touches `.name`."""

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
        # The extension is matched case-insensitively but must not be spliced out of
        # the middle of the stem, which `name.replace(extension, "")` used to do.
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
        # A leading dot hides the file; Windows drops trailing dots and spaces.
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
    # A dotfile has no extension to match, whatever it is named after the dot.
    with pytest.raises(ValidationError):
        _sanitized("///.pdf")


def test_rfc5987_header_reaches_the_backend_intact():
    """What `contentDispositionHeader()` emits is what Django must decode.

    Kept in sync by hand with frontend/src/lib/utils/contentDisposition.ts — this is
    the seam the bug lived in.
    """
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
        # Case-insensitive: the archive is often extracted on Windows or macOS.
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
    """A zip entry name is never trusted, whatever put it in original_filename.

    AnswerAttachment.filename is typed by an external respondent and follows the file
    into EvidenceRevision on promotion, so the archive builder re-sanitizes.
    """
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
