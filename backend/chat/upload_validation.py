"""Upload validation for chat file uploads (Questionnaire Autopilot and
session document uploads).

Belt-and-braces checks that go beyond the generic core validators:

- **Magic bytes**: Excel .xlsx files are zip archives — they MUST start with
  the local-file-header signature ``PK\\x03\\x04``. A renamed .docx, .zip,
  or arbitrary binary would pass the extension check but trip here.
- **Zip integrity**: opens the file as a zip and inspects the member list.
  Verifies the OOXML "[Content_Types].xml" marker is present.
- **No macros**: rejects files containing ``xl/vbaProject.bin`` — i.e.
  ``.xlsm`` style macro-enabled workbooks. We never execute macros on the
  parser side, but they don't belong in a customer questionnaire either,
  and storing them as evidence is unnecessary attack surface.
- **Decompression ratio**: caps total uncompressed size and total /
  compressed ratio to defang zip-bomb-style payloads. A typical xlsx
  compresses ~3-5x; we allow up to 200x and 300 MB uncompressed.
"""

from __future__ import annotations

import io
import zipfile

from django.core.exceptions import ValidationError

# OOXML SpreadsheetML files always carry these markers in their zip.
_OOXML_REQUIRED_MEMBERS = ("[Content_Types].xml",)

# Macro-enabled marker — any presence of this rejects the file.
_MACRO_MARKER = "xl/vbaProject.bin"

# Decompression bomb guards. A normal questionnaire xlsx of ~30 questions
# compresses to ~10–50 KB, ~100–300 KB uncompressed (ratio 5–10x).
# These thresholds are generous for legitimate files but kill obvious bombs.
_MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024  # 300 MB
_MAX_DECOMPRESSION_RATIO = 200  # uncompressed / compressed


# Extensions accepted on the generic chat upload endpoint, mapped to the
# canonical content type the extractor registry keys on. The client-supplied
# content type is never trusted.
CHAT_UPLOAD_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".txt": "text/plain",
}


def validate_questionnaire_upload(file_obj) -> None:
    """Validate the uploaded file is a benign .xlsx.

    Raises :class:`django.core.exceptions.ValidationError` with a
    user-readable message on the first violation. Caller should treat any
    exception as a 400-class error.

    The file_obj is read in full (small files; ATTACHMENT_MAX_SIZE_MB caps
    upstream) and the cursor is reset so subsequent ``.save()`` works.
    """
    name = getattr(file_obj, "name", "") or ""
    if not name.lower().endswith(".xlsx"):
        raise ValidationError(
            "Only .xlsx files are accepted. Macro-enabled .xlsm and "
            "legacy .xls are rejected."
        )

    file_obj.seek(0)
    raw = file_obj.read()
    file_obj.seek(0)
    _validate_xlsx_zip(raw)


def validate_chat_upload(file_obj) -> str:
    """Validate a file uploaded to a chat session and return its canonical
    content type.

    Same contract as :func:`validate_questionnaire_upload` (raises
    ``ValidationError``, resets the cursor) but accepts every type the
    extractor registry can digest, with per-format magic-byte checks.
    """
    name = getattr(file_obj, "name", "") or ""
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    content_type = CHAT_UPLOAD_CONTENT_TYPES.get(ext)
    if not content_type:
        accepted = ", ".join(sorted(CHAT_UPLOAD_CONTENT_TYPES))
        raise ValidationError(f"Unsupported file type. Accepted: {accepted}.")

    file_obj.seek(0)
    raw = file_obj.read()
    file_obj.seek(0)

    if not raw:
        raise ValidationError("File is empty.")

    if ext == ".xlsx":
        _validate_xlsx_zip(raw)
    elif ext == ".pdf":
        if not raw.startswith(b"%PDF-"):
            raise ValidationError("File does not look like a valid PDF.")
    else:  # .csv / .txt
        if b"\x00" in raw[: 64 * 1024]:
            raise ValidationError("File does not look like a text file.")

    return content_type


def _validate_xlsx_zip(raw: bytes) -> None:
    """Zip-level checks shared by the questionnaire and chat upload paths."""
    if raw[:4] != b"PK\x03\x04":
        raise ValidationError(
            "File does not look like a valid .xlsx (missing zip header)."
        )

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise ValidationError(
            "File is not a valid Excel workbook (zip structure is broken)."
        )

    namelist = set(zf.namelist())

    for required in _OOXML_REQUIRED_MEMBERS:
        if required not in namelist:
            raise ValidationError(
                f"File is missing the OOXML marker '{required}' — "
                "not a valid Excel workbook."
            )

    if _MACRO_MARKER in namelist:
        raise ValidationError(
            "Macro-enabled workbooks are not accepted. "
            "Save the file as a standard .xlsx and re-upload."
        )

    total_uncompressed = 0
    compressed_size = max(len(raw), 1)
    for info in zf.infolist():
        total_uncompressed += info.file_size
        if total_uncompressed > _MAX_UNCOMPRESSED_BYTES:
            raise ValidationError(
                "File expands to more than 300 MB uncompressed — refusing to load."
            )
    if total_uncompressed > _MAX_DECOMPRESSION_RATIO * compressed_size:
        raise ValidationError(
            "Suspicious decompression ratio; refusing to load this file."
        )
