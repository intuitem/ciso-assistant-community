"""Tabular file digestion for the document import workflow.

Parses an uploaded xlsx/csv into headers + sample rows, computes the
header signature used by learned mapping profiles, and maps columns to
model fields deterministically (data_wizard alias tables + model fields)
before any LLM is consulted.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)

TABULAR_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
}

MAX_SAMPLE_ROWS = 5
MAX_COUNTED_ROWS = 10_000

# Import targets supported by the workflow. The consumer name refers to
# data_wizard.views — the same code path as the manual data wizard, so an
# AI-mediated import can never do more than a wizard import could.
IMPORT_TARGETS = {
    "applied_control": {
        "label": "Applied controls",
        "model": ("core", "AppliedControl"),
        "consumer": "AppliedControlRecordConsumer",
        "hints": ("control", "contrôle", "mesure"),
    },
    "finding": {
        "label": "Findings (pentest, audit…)",
        "model": ("core", "Finding"),
        "consumer": "FindingsAssessmentRecordConsumer",
        "hints": ("finding", "pentest", "constat", "vulnérabilité"),
    },
    "asset": {
        "label": "Assets",
        "model": ("core", "Asset"),
        "consumer": "AssetRecordConsumer",
        "hints": ("asset", "actif"),
    },
}


def target_terms(target_key: str) -> tuple[str, ...]:
    """Terms that identify an import target in a user message: the key,
    the display label, the model's verbose names, and configured hints."""
    from django.apps import apps

    target = IMPORT_TARGETS[target_key]
    meta = apps.get_model(*target["model"])._meta
    return (
        target_key.replace("_", " "),
        target["label"].lower(),
        str(meta.verbose_name).lower(),
        str(meta.verbose_name_plural).lower(),
        *target.get("hints", ()),
    )


# Same rationale as chat.tools._INTERNAL_FIELDS: never map a source column
# onto machine-managed fields.
_UNMAPPABLE_FIELDS = {
    "id",
    "created_at",
    "updated_at",
    "folder",
    "is_published",
    "urn",
    "locale",
    "default_locale",
    "provider",
    "workflow_state",
    "meta",
}


@dataclass
class TabularDigest:
    filename: str = ""
    headers: list[str] = field(default_factory=list)
    normalized_headers: list[str] = field(default_factory=list)
    row_count: int = 0
    row_count_capped: bool = False
    sample_rows: list[dict] = field(default_factory=list)
    signature: str = ""
    error: str = ""


def normalize_header(header) -> str:
    return str(header).strip().lower() if header is not None else ""


def header_signature(normalized_headers: list[str]) -> str:
    """Order-insensitive signature of a header set, the key for learned
    mapping profiles (browser-side in v1, server-side later)."""
    canonical = "\n".join(sorted(h for h in normalized_headers if h))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _iter_document_rows(doc):
    with doc.file.open("rb") as fh:
        raw = fh.read()
    if doc.content_type == "text/csv":
        return _iter_csv_rows(raw)
    return _iter_xlsx_rows(raw)


def digest_document(doc) -> TabularDigest:
    """Parse an IndexedDocument's file into a TabularDigest. Never raises —
    parse failures land in .error."""
    digest = TabularDigest(filename=doc.filename)
    try:
        _fill_digest(digest, _iter_document_rows(doc))
    except OSError:
        logger.error("tabular_file_read_failed", document_id=str(doc.id))
        digest.error = "The uploaded file could not be read back from storage."
        return digest
    except Exception:
        logger.error(
            "tabular_parse_failed",
            document_id=str(doc.id),
            content_type=doc.content_type,
            exc_info=True,
        )
        digest.error = "The file could not be parsed as a spreadsheet."
        return digest

    if not digest.headers:
        digest.error = "The file has no header row."
    elif digest.row_count == 0:
        digest.error = "The file has a header row but no data rows."
    return digest


def _iter_xlsx_rows(raw: bytes):
    import openpyxl

    workbook = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        for row in sheet.iter_rows(values_only=True):
            yield list(row)
    finally:
        workbook.close()


def _iter_csv_rows(raw: bytes):
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    yield from csv.reader(io.StringIO(text), dialect)


def _fill_digest(digest: TabularDigest, rows) -> None:
    for row in rows:
        values = ["" if v is None else v for v in row]
        if not any(str(v).strip() for v in values):
            continue

        if not digest.headers:
            digest.headers = [str(v).strip() for v in values]
            digest.normalized_headers = [normalize_header(v) for v in values]
            digest.signature = header_signature(digest.normalized_headers)
            continue

        digest.row_count += 1
        if digest.row_count > MAX_COUNTED_ROWS:
            digest.row_count = MAX_COUNTED_ROWS
            digest.row_count_capped = True
            break
        if len(digest.sample_rows) < MAX_SAMPLE_ROWS:
            digest.sample_rows.append(
                {
                    h: str(values[i]) if i < len(values) else ""
                    for i, h in enumerate(digest.normalized_headers)
                    if h
                }
            )


def known_columns(target_key: str) -> dict[str, str]:
    """Return {accepted column name -> canonical field} for an import target,
    derived from the target model's fields plus the data_wizard consumer's
    SOURCE_KEY_MAP aliases, so it stays in sync with what the consumer can
    actually ingest."""
    from django.apps import apps

    import data_wizard.views as dw

    target = IMPORT_TARGETS[target_key]
    model = apps.get_model(*target["model"])
    consumer_cls = getattr(dw, target["consumer"])

    columns: dict[str, str] = {}
    for f in model._meta.get_fields():
        if not getattr(f, "concrete", False) or f.name in _UNMAPPABLE_FIELDS:
            continue
        columns[f.name] = f.name

    for canonical, aliases in getattr(consumer_cls, "SOURCE_KEY_MAP", {}).items():
        for alias in aliases:
            columns[normalize_header(alias)] = canonical
        columns.setdefault(canonical, canonical)

    # Columns every consumer understands regardless of model fields.
    columns.setdefault("domain", "domain")
    columns.setdefault("internal_id", "internal_id")
    return columns


def map_columns(
    normalized_headers: list[str], target_key: str
) -> tuple[dict[str, str], list[str]]:
    """Deterministic column mapping. Returns (mapped {header -> field},
    unmapped headers). Headers left unmapped are the LLM's (or the user's)
    to resolve."""
    known = known_columns(target_key)
    mapped: dict[str, str] = {}
    unmapped: list[str] = []
    for header in normalized_headers:
        if not header:
            continue
        target_field = known.get(header) or known.get(header.replace(" ", "_"))
        if target_field:
            mapped[header] = target_field
        else:
            unmapped.append(header)
    return mapped, unmapped


def extract_records(doc, mapping: dict[str, str]) -> list[dict]:
    """Extract recognized columns as consumer-ready records, keyed by their
    source header — consumers resolve aliases themselves (a canonical key may
    stand for several columns, e.g. cost). Dates are ISO-formatted, mirroring
    data_wizard's normalize_datetime_columns."""
    import datetime

    records: list[dict] = []
    headers: list[str] = []
    for row in _iter_document_rows(doc):
        values = ["" if v is None else v for v in row]
        if not any(str(v).strip() for v in values):
            continue
        if not headers:
            headers = [normalize_header(v) for v in values]
            continue

        record = {}
        for i, header in enumerate(headers):
            if header not in mapping:
                continue
            value = values[i] if i < len(values) else ""
            if isinstance(value, (datetime.datetime, datetime.date)):
                value = value.isoformat()
            record[header] = value
        records.append(record)
        if len(records) >= MAX_COUNTED_ROWS:
            break
    return records


def detect_target(normalized_headers: list[str]) -> list[tuple[str, float]]:
    """Score each import target by the fraction of headers it recognizes,
    best first."""
    scores = []
    total = len([h for h in normalized_headers if h]) or 1
    for target_key in IMPORT_TARGETS:
        mapped, _ = map_columns(normalized_headers, target_key)
        scores.append((target_key, len(mapped) / total))
    scores.sort(key=lambda item: item[1], reverse=True)
    return scores
