"""Import from any spreadsheet: analyse it, then map it onto one of our templates.

A mapping only reshapes the file (sheet, header row, column and value renames)
into the workbook the matching template describes; the regular importer then
reads it, so validation, conflict modes and permissions stay in one place.
"""

import csv
import difflib
import io
import json
import re
import unicodedata
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import date, datetime, time
from functools import cache
from pathlib import Path
from typing import Any
from uuid import UUID

import openpyxl
import pandas as pd
import structlog
from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from django.db.models import F
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core import mailer
from core.views import BaseModelViewSet
from iam.models import RoleAssignment

from .models import ImportMapping
from .serializers import LoadFileSerializer
from .views import (
    IMPORT_TEMPLATES,
    IMPORT_TEMPLATES_DIR,
    SHEET_NAME_INVALID_CHARS,
    AppliedControlRecordConsumer,
    AssetRecordConsumer,
    ConflictMode,
    EvidenceRecordConsumer,
    ImportOptions,
    LoadFileView,
    ModelType,
    PerimeterRecordConsumer,
    get_accessible_folders_map,
    is_excel_file,
)

logger = structlog.get_logger(__name__)

# The model whose records fill each data sheet of a template. Templates or
# sheets left out (task templates, notes) cannot be targeted by a mapping.
TEMPLATE_ROW_MODELS: dict[ModelType, dict[str, str]] = {
    ModelType.ASSET: {"Sheet1": "core.Asset"},
    ModelType.APPLIED_CONTROL: {"Sheet1": "core.AppliedControl"},
    ModelType.POLICY: {"Sheet1": "core.Policy"},
    ModelType.EVIDENCE: {"Sheet1": "core.Evidence"},
    ModelType.PERIMETER: {"Sheet1": "core.Perimeter"},
    ModelType.USER: {"Sheet1": "iam.User"},
    ModelType.FOLDER: {"Folder": "iam.Folder"},
    ModelType.REFERENCE_CONTROL: {"Reference Controls": "core.ReferenceControl"},
    ModelType.THREAT: {"Threats": "core.Threat"},
    ModelType.VULNERABILITY: {"RA CISO": "core.Vulnerability"},
    ModelType.SECURITY_EXCEPTION: {"Sheet1": "core.SecurityException"},
    ModelType.INCIDENT: {"Sheet1": "core.Incident"},
    ModelType.ELEMENTARY_ACTION: {"Sheet1": "ebios_rm.ElementaryAction"},
    ModelType.PROCESSING: {"Sheet1": "privacy.Processing"},
    ModelType.FINDINGS_ASSESSMENT: {"Sheet1": "core.Finding"},
    ModelType.RISK_ASSESSMENT: {"Sheet1": "core.RiskScenario"},
    ModelType.BUSINESS_IMPACT_ANALYSIS: {
        "Summary": "resilience.BusinessImpactAnalysis",
        "bia": "resilience.AssetAssessment",
        "bia - thresholds": "resilience.EscalationThreshold",
    },
    ModelType.METRIC_INSTANCE: {"Metric instances": "metrology.MetricInstance"},
    ModelType.METRIC_SAMPLE: {"Samples": "metrology.CustomMetricSample"},
    # Task definitions only: the occurrence sheets are keyed by sheet name.
    ModelType.TASK_TEMPLATE: {"Summary": "core.TaskTemplate"},
    # Audit rows: one per requirement, matched on ref_id or urn.
    ModelType.COMPLIANCE_ASSESSMENT: {"Requirements": "core.RequirementAssessment"},
    ModelType.TPRM: {
        "Entities": "tprm.Entity",
        "Solutions": "tprm.Solution",
        "EntityAssessments": "tprm.EntityAssessment",
        "Contracts": "tprm.Contract",
        "Representatives": "tprm.Representative",
    },
}

# Consumers declaring alternative column names (SOURCE_KEY_MAP).
ALIAS_SOURCES = {
    ModelType.ASSET: AssetRecordConsumer,
    ModelType.APPLIED_CONTROL: AppliedControlRecordConsumer,
    ModelType.EVIDENCE: EvidenceRecordConsumer,
    ModelType.PERIMETER: PerimeterRecordConsumer,
}

# Columns an importer reads that its template leaves out. Not in the downloadable
# template on purpose: a blank owner cell clears owners in Update mode, while a
# mapping only sends the columns the user chose.
EXTRA_COLUMNS: dict[ModelType, dict[str, list[str]]] = {
    ModelType.APPLIED_CONTROL: {"Sheet1": ["owner"]},
    ModelType.POLICY: {"Sheet1": ["owner"]},
    ModelType.METRIC_INSTANCE: {"Metric instances": ["owner"]},
    # Read by the mapped import only: becomes a completed past occurrence.
    ModelType.TASK_TEMPLATE: {"Summary": ["last_done"]},
}
# Labels for template columns that are not model fields.
COLUMN_LABELS = {"last_done": "Last done on (a completed occurrence)"}


def _is_domain(column: str) -> bool:
    return COLUMN_FIELDS.get(column, column) == "folder"


# Imports with no downloadable template (their columns do not depend on a
# framework, their rows do): the columns their importer reads.
VIRTUAL_TEMPLATES: dict[ModelType, dict[str, list[str]]] = {
    ModelType.COMPLIANCE_ASSESSMENT: {
        "Requirements": [
            "ref_id",
            "urn",
            "compliance_result",
            "extended_result",
            "requirement_progress",
            "score",
            "implementation_score",
            "documentation_score",
            "is_score_overridden",
            "observations",
            "applied_controls",
            "answers",
            "assessable",
        ]
    },
}

# Values an importer needs that a user's file would not carry. Our audit export
# marks rows that can be assessed; any other audit file means all of them.
DEFAULT_VALUES: dict[ModelType, dict[str, Any]] = {
    ModelType.COMPLIANCE_ASSESSMENT: {"assessable": True},
}

SCHEDULE_PAIR = {
    "schedule_frequency": "schedule_interval",
    "schedule_interval": "schedule_frequency",
}

# Template columns named after the user-facing concept rather than the field.
COLUMN_FIELDS = {
    "domain": "folder",
    "compliance_result": "result",
    "requirement_progress": "status",
    "observations": "observation",
}

HEADER_SCAN_ROWS = 20
MAX_DISTINCT_VALUES = 50
SAMPLE_SIZE = 5
MIN_TARGET_SCORE = 0.2


def normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore")
    return re.sub(r"[^a-z0-9]+", "_", text.decode().lower()).strip("_")


def _cell_key(value: Any) -> str:
    return str(value).strip()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _translations(text) -> set[str]:
    out = set()
    for code, _name in settings.LANGUAGES:
        with translation.override(code):
            out.add(normalize(str(text)))
            # Many verbose names are lowercase while the catalogue holds "Status".
            raw = str(text)
            out.add(normalize(translation.gettext(raw[:1].upper() + raw[1:])))
    out.discard("")
    return out


# ─── Target schema ───────────────────────────────────────────────────────────


def _model_field(model, column: str):
    try:
        return model._meta.get_field(COLUMN_FIELDS.get(column, column))
    except FieldDoesNotExist:
        return None


def _column_schema(model, column: str, aliases: list[str]) -> dict:
    model_field = _model_field(model, column)
    label = (
        _("Domain")
        if _is_domain(column)
        else getattr(model_field, "verbose_name", None)
        or COLUMN_LABELS.get(column, column)
    )
    choices = None
    if model_field is not None and getattr(model_field, "choices", None):
        choices = [
            {"value": value, "label": str(choice_label)}
            for value, choice_label in model_field.flatchoices
        ]
    elif model_field is None and (enum := _json_enum(model, column)):
        choices = [
            {"value": v, "label": v.replace("_", " ").capitalize()} for v in enum
        ]
    return {
        "key": column,
        "label": str(label),
        "aliases": aliases,
        "choices": choices,
        "boolean": model_field is not None
        and model_field.get_internal_type() == "BooleanField",
    }


def _aliases(model_type: ModelType) -> dict[str, list[str]]:
    consumer = ALIAS_SOURCES.get(model_type)
    if consumer is None:
        return {}
    return {
        key: [s for s in sources if s != key]
        for key, sources in consumer.SOURCE_KEY_MAP.items()
    }


@cache
def _template_headers(model_type: ModelType) -> dict[str, list[str]]:
    if model_type in VIRTUAL_TEMPLATES:
        return {
            sheet: list(cols) for sheet, cols in VIRTUAL_TEMPLATES[model_type].items()
        }
    workbook = openpyxl.load_workbook(
        IMPORT_TEMPLATES_DIR / IMPORT_TEMPLATES[model_type], read_only=True
    )
    try:
        return {
            sheet: [
                str(c).strip().lower()
                for c in next(workbook[sheet].iter_rows(max_row=1, values_only=True))
                if c is not None
            ]
            + EXTRA_COLUMNS.get(model_type, {}).get(sheet, [])
            for sheet in TEMPLATE_ROW_MODELS[model_type]
        }
    finally:
        workbook.close()


def template_schema(model_type: ModelType) -> dict:
    aliases = _aliases(model_type)
    sheets = []
    for sheet, columns in _template_headers(model_type).items():
        model = apps.get_model(TEMPLATE_ROW_MODELS[model_type][sheet])
        sheets.append(
            {
                "name": sheet,
                "model": model._meta.model_name,
                "columns": [
                    _column_schema(model, c, aliases.get(c, [])) for c in columns
                ],
            }
        )
    return {"model_type": model_type.value, "sheets": sheets}


def mappable_model_types() -> list[str]:
    return [model_type.value for model_type in TEMPLATE_ROW_MODELS]


# ─── Reading the source file ─────────────────────────────────────────────────


@dataclass
class SourceSheet:
    name: str
    raw: pd.DataFrame  # header=None, every cell as read
    header_row: int = 0  # 0-based index into raw

    @property
    def headers(self) -> list[str]:
        seen: dict[str, int] = {}
        out = []
        for cell in self.raw.iloc[self.header_row].tolist():
            text = "" if pd.isna(cell) else _cell_key(cell)
            if text:
                seen[text] = seen.get(text, 0) + 1
                if seen[text] > 1:
                    text = f"{text} ({seen[text]})"
            out.append(text)
        return out

    def check_header_row(self) -> None:
        if not 0 <= self.header_row < len(self.raw):
            raise ValueError(f"HeaderRowOutOfRange: {self.header_row + 1}")

    def frame(self) -> pd.DataFrame:
        """The data rows below the header, keyed by header, blank rows dropped."""
        data = self.raw.iloc[self.header_row + 1 :].copy()
        data.columns = self.headers
        data = data.loc[:, [h for h in data.columns if h]]
        return data.dropna(how="all")


def read_source(file: io.BytesIO) -> list[SourceSheet]:
    if is_excel_file(file):
        sheets = pd.read_excel(file, sheet_name=None, header=None, dtype=object)
        return [SourceSheet(str(name), df) for name, df in sheets.items()]
    # Every line as cells, header included: a title line above the table is
    # found like on a sheet, and "007" or "1.10" stay text.
    text = file.read().decode("utf-8-sig", errors="replace")
    try:
        sep = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|").delimiter
    except csv.Error:
        sep = ","
    rows = list(csv.reader(io.StringIO(text), delimiter=sep))
    raw = pd.DataFrame(rows, dtype=object)
    return [SourceSheet("CSV", raw.replace("", None))]


def detect_header_row(raw: pd.DataFrame) -> int:
    """The row among the first ones holding the most text cells; title banners
    above a table hold one or two."""
    best, best_count = 0, 0
    for index in range(min(HEADER_SCAN_ROWS, len(raw))):
        count = sum(
            isinstance(v, str) and v.strip() != "" for v in raw.iloc[index].tolist()
        )
        if count > best_count:
            best, best_count = index, count
    return best


# ─── Suggestions ─────────────────────────────────────────────────────────────


@dataclass
class TargetColumn:
    key: str
    names: set[str]  # normalized key, aliases and labels in every language
    choices: dict[str, Any] | None  # normalized key or label -> choice value
    kind: str | None = None  # what the field holds: date, email, url or person
    # Filled by looking records up or creating them (labels, owners, assets...):
    # a wrong guess there links or creates the wrong things, so name match only.
    relational: bool = False


def _target_kind(column: str, model_field) -> str | None:
    if column == "email":
        return "email"
    if column.endswith("link"):
        return "url"
    if model_field is None:
        return None
    if model_field.get_internal_type() in ("DateField", "DateTimeField"):
        return "date"
    related = getattr(model_field, "related_model", None)
    if related is not None and related.__name__ in ("Actor", "User"):
        return "person"
    return None


def _json_enum(model, column: str) -> list | None:
    """Choices of a column flattening a JSON field: schedule_frequency takes the
    frequency enum of TaskTemplate.SCHEDULE_JSONSCHEMA."""
    field, _, prop = column.partition("_")
    schema = getattr(model, f"{field.upper()}_JSONSCHEMA", None) or {}
    return schema.get("properties", {}).get(prop, {}).get("enum")


@cache
def _target_columns(model_type: ModelType, sheet: str) -> list[TargetColumn]:
    schema = next(
        s for s in template_schema(model_type)["sheets"] if s["name"] == sheet
    )
    model = apps.get_model(TEMPLATE_ROW_MODELS[model_type][sheet])
    out = []
    for column in schema["columns"]:
        names = {normalize(column["key"])} | {normalize(a) for a in column["aliases"]}
        model_field = _model_field(model, column["key"])
        if _is_domain(column["key"]):
            names |= _translations(_("Domain"))
        elif model_field is not None and hasattr(model_field, "verbose_name"):
            names |= _translations(model_field.verbose_name)
        choices = None
        if model_field is None and (enum := _json_enum(model, column["key"])):
            choices = {normalize(v): v for v in enum}
        elif model_field is not None and getattr(model_field, "choices", None):
            choices = {}
            for value, label in model_field.flatchoices:
                choices[normalize(value)] = value
                for name in _translations(label):
                    choices.setdefault(name, value)
        related = getattr(model_field, "related_model", None)
        out.append(
            TargetColumn(
                column["key"],
                names,
                choices,
                _target_kind(column["key"], model_field),
                relational=related is not None and not _is_domain(column["key"]),
            )
        )
    return out


@cache
def _target_hints(model_type: ModelType, sheet: str) -> set[str]:
    """Names a sheet or file holding these records is likely to carry."""
    meta = apps.get_model(TEMPLATE_ROW_MODELS[model_type][sheet])._meta
    hints = _translations(meta.verbose_name) | _translations(meta.verbose_name_plural)
    if not re.fullmatch(r"sheet\d*", normalize(sheet)):
        hints.add(normalize(sheet))
    return hints


def suggest_value(value: Any, choices: dict[str, Any]) -> dict | None:
    name = normalize(value)
    if not name:
        return None
    if name in choices:
        return {"value": choices[name], "reason": "exact"}
    close = difflib.get_close_matches(name, choices.keys(), n=1, cutoff=0.8)
    if close:
        return {"value": choices[close[0]], "reason": "close"}
    # A longer spelling of one choice ("informational" for "info").
    stems = {choices[k] for k in choices if len(k) >= 3 and name.startswith(k)}
    if len(stems) == 1:
        return {"value": stems.pop(), "reason": "close"}
    return None


def _fits(profile: "ColumnProfile", target: "TargetColumn") -> bool:
    """Whether a column's values can go into the field: for a choice field, at
    least half of them must match a choice."""
    if target.key == "answers":
        # Exported questionnaire cells: "question >> answer" (parse_answers_cell).
        return any(">>" in str(v) for v in profile.distinct or [])
    if not target.choices or not profile.distinct:
        return True
    values = [v for v in profile.distinct if normalize(v)]
    if not values:
        return True
    matched = sum(1 for v in values if suggest_value(v, target.choices))
    return matched * 2 >= len(values)


EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}")
CODE = re.compile(r"\S*\d\S*")


@dataclass
class ColumnProfile:
    header: str
    samples: list
    distinct: list | None  # None when there are too many to map one by one
    kind: str | None = None  # email, url, date, code or text
    avg_length: float = 0


def _share(values: list, test) -> float:
    return sum(1 for v in values if test(v)) / len(values) if values else 0


def _content_kind(values: list) -> str | None:
    """What a column holds, judged on its non-empty cells."""
    if not values:
        return None
    texts = [str(v).strip() for v in values]
    if _share(texts, EMAIL.fullmatch) >= 0.8:
        return "email"
    if _share(texts, lambda t: t.startswith(("http://", "https://"))) >= 0.8:
        return "url"
    # Planning cells often mix real dates with "Q3" or "TBD".
    if (
        _share(
            values,
            lambda v: (
                isinstance(v, (date, datetime))
                or bool(ISO_DATE.fullmatch(str(v).strip()))
            ),
        )
        >= 0.6
    ):
        return "date"
    unique = len(set(texts)) == len(texts)
    if unique and all(len(t) <= 30 and CODE.fullmatch(t) for t in texts):
        return "code"
    if unique and _share(texts, lambda t: " " in t) >= 0.5:
        return "text"
    return None


def profile_columns(frame: pd.DataFrame) -> list[ColumnProfile]:
    profiles = []
    for header in frame.columns:
        values = [v for v in frame[header].tolist() if not pd.isna(v) and v != ""]
        distinct = list(dict.fromkeys(_cell_key(v) for v in values))
        profiles.append(
            ColumnProfile(
                header=header,
                samples=[_jsonable(v) for v in values[:SAMPLE_SIZE]],
                distinct=distinct if len(distinct) <= MAX_DISTINCT_VALUES else None,
                kind=_content_kind(values),
                avg_length=sum(len(str(v)) for v in values) / len(values)
                if values
                else 0,
            )
        )
    return profiles


def _within(name: str, longer: str) -> bool:
    """Whether *name* appears in *longer* as whole words."""
    return f"_{name}_" in f"_{longer}_"


# Weight of each reason in a target's score.
REASON_WEIGHTS = {
    "name": 1,
    "partial": 1,
    "close": 1,
    "values": 1,
    "content": 1,
    # Emails filling a model's only people field: a weaker vote, as any table
    # with an owner would claim a column of emails.
    "people": 0.5,
}
# Found in nearly every table: they say nothing about which object it holds.
GENERIC_KEYS = {"ref_id", "name", "description"}


def suggest_columns(
    profiles: list[ColumnProfile],
    targets: list[TargetColumn],
    folder_names: set[str],
) -> dict[str, dict]:
    """Source header -> {key, reason}, each target column used at most once."""
    suggestions: dict[str, dict] = {}
    taken: set[str] = set()
    by_key = {t.key: t for t in targets}

    def assign(header, key, reason):
        suggestions[header] = {"key": key, "reason": reason}
        taken.add(key)

    def free(profile):
        return profile.header not in suggestions

    # The exact name is strong enough on its own: a choice column whose values do
    # not fit then shows them for review rather than being left unmapped.
    for profile in profiles:
        name = normalize(profile.header)
        for target in targets:
            if target.key not in taken and name in target.names:
                assign(profile.header, target.key, "name")
                break

    # A header holding a field's name among other words: "Evidence link".
    for profile in filter(free, profiles):
        name = normalize(profile.header)
        best = max(
            (
                (len(n), t.key)
                for t in targets
                if t.key not in taken and not t.relational and _fits(profile, t)
                for n in t.names
                # "Evidence link" holds link; "Target" is held by target_value.
                if (len(n) >= 4 and _within(n, name))
                or (len(name) >= 5 and _within(name, n))
            ),
            default=None,
        )
        if best:
            assign(profile.header, best[1], "partial")

    # Near spellings: "Threat" for "threats", "E-mail" for "email".
    for profile in filter(free, profiles):
        name = normalize(profile.header)
        best = max(
            (
                (difflib.SequenceMatcher(None, name, n).ratio(), t.key)
                for t in targets
                if t.key not in taken and _fits(profile, t)
                for n in t.names
                if len(n) >= 4
            ),
            default=(0, None),
        )
        if best[0] >= 0.85:
            assign(profile.header, best[1], "close")

    # Unmatched headers: judge the column by what it holds. Plain numbers say
    # little: any count or amount fits a numbered scale.
    for profile in filter(free, profiles):
        if not profile.distinct:
            continue
        values = {normalize(v) for v in profile.distinct} - {""}
        if not values or all(v.isdigit() for v in values):
            continue
        for target in targets:
            if target.key in taken:
                continue
            if target.choices and len(values & target.choices.keys()) >= max(
                1, len(values) // 2
            ):
                assign(profile.header, target.key, "values")
                break
            if _is_domain(target.key) and len(values & folder_names) >= max(
                1, len(values) // 2
            ):
                assign(profile.header, target.key, "values")
                break

    for profile in filter(free, profiles):
        if profile.kind == "email":
            # An email field first; else the one field holding people, which
            # resolves them by email (a task's assignees).
            free_targets = [t for t in targets if t.key not in taken]
            people = [t for t in free_targets if t.kind == "person"]
            target = next((t for t in free_targets if t.kind == "email"), None)
            if target:
                assign(profile.header, target.key, "content")
            elif len(people) == 1:
                assign(profile.header, people[0].key, "people")
        elif profile.kind in ("url", "date"):
            candidates = [
                t for t in targets if t.kind == profile.kind and t.key not in taken
            ]
            if candidates:
                # Several date fields: take the one whose name reads closest.
                name = normalize(profile.header)
                target = max(
                    candidates,
                    key=lambda t: max(
                        difflib.SequenceMatcher(None, name, n).ratio() for n in t.names
                    ),
                )
                assign(profile.header, target.key, "content")

    # Identifier, name and description: what nearly every table has.
    if "ref_id" in by_key and "ref_id" not in taken:
        code = next((p for p in profiles if free(p) and p.kind == "code"), None)
        if code:
            assign(code.header, "ref_id", "generic")
    texts = [p for p in profiles if free(p) and p.kind == "text"]
    if "name" in by_key and "name" not in taken and texts:
        assign(texts.pop(0).header, "name", "generic")
    if "description" in by_key and "description" not in taken and texts:
        longest = max(texts, key=lambda p: p.avg_length)
        assign(longest.header, "description", "generic")
    return suggestions


def suggest_values(
    profiles: list[ColumnProfile],
    columns: dict[str, str],
    targets: list[TargetColumn],
) -> dict[str, dict[str, dict | None]]:
    by_key = {t.key: t for t in targets}
    out = {}
    for profile in profiles:
        target = by_key.get(columns.get(profile.header))
        if target is None or not target.choices or profile.distinct is None:
            continue
        out[profile.header] = {
            v: suggest_value(v, target.choices) for v in profile.distinct
        }
    return out


HINT_BONUS = 0.5
# A column whose cells are the field's own choices ("Primaire" for an asset type).
VALUES_BONUS = 0.5


def _values_fit(profile: ColumnProfile, target: TargetColumn) -> bool:
    if not target.choices or not profile.distinct:
        return False
    values = {normalize(v) for v in profile.distinct} - {""}
    return bool(values) and all(suggest_value(v, target.choices) for v in values)


def rank_targets(
    profiles: list[ColumnProfile], folder_names: set[str], hint: str = ""
) -> list[dict]:
    """Template sheets ordered by how much of the source they account for:
    columns recognised, plus a bonus when the sheet or file is named after
    the records the template holds."""
    hint = normalize(hint)
    ranked = []
    for model_type, sheets in TEMPLATE_ROW_MODELS.items():
        for sheet in sheets:
            targets = _target_columns(model_type, sheet)
            by_key = {t.key: t for t in targets}
            suggestions = suggest_columns(profiles, targets, folder_names)
            # A choice column whose values do not fit says nothing about the
            # target: "Status" holding "Prod" is no vote for applied controls.
            matched = sum(
                REASON_WEIGHTS.get(s["reason"], 0)
                + (VALUES_BONUS if _values_fit(p, by_key[s["key"]]) else 0)
                for p in profiles
                if (s := suggestions.get(p.header))
                and s["key"] not in GENERIC_KEYS
                and _fits(p, by_key[s["key"]])
            )
            score = matched / len(profiles) if profiles else 0
            if hint and any(_within(h, hint) for h in _target_hints(model_type, sheet)):
                score += HINT_BONUS
            if score >= MIN_TARGET_SCORE:
                ranked.append(
                    {
                        "model_type": model_type.value,
                        "sheet": sheet,
                        "score": round(min(score, 1), 2),
                    }
                )
    # Stable sort: equal scores keep the template order.
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:3]


# ─── Saved mappings ──────────────────────────────────────────────────────────

# A saved layout still applies when a file gained or lost a couple of columns.
SAVED_MAX_DIFF = 2
SAVED_MIN_OVERLAP = 0.75


def validate_saved_sheets(sheets: Any) -> None:
    """Check what a client wants to save; raise ValueError on anything off."""
    if not isinstance(sheets, list) or not sheets:
        raise ValueError("InvalidSheets: expected a non-empty list")
    for entry in sheets:
        if not isinstance(entry, dict):
            raise TypeError("InvalidSheets: expected objects")
        headers = entry.get("headers")
        if not isinstance(headers, list) or not all(
            isinstance(h, str) for h in headers
        ):
            raise ValueError("InvalidHeaders")
        columns = entry.get("columns") or {}
        if set(columns) - set(headers):
            raise ValueError("ColumnsOutsideHeaders")
        parse_steps(
            {
                "steps": [
                    {
                        "model_type": entry.get("model_type"),
                        "sheets": [
                            {
                                "source": entry.get("source"),
                                "target": entry.get("target"),
                                "header_row": entry.get("header_row", 1),
                                "columns": columns,
                                "values": entry.get("values") or {},
                                "defaults": entry.get("defaults") or {},
                            }
                        ],
                    }
                ]
            }
        )


def match_saved(headers: list[str], saved: list[dict]) -> tuple[dict, dict] | None:
    """The saved mapping and sheet entry whose headers best match *headers*.
    *saved* is ordered by preference (most recently used first)."""
    current = {normalize(h) for h in headers if h}
    best, best_overlap = None, 0.0
    for mapping_ in saved:
        for entry in mapping_["sheets"]:
            known = {normalize(h) for h in entry.get("headers", []) if h}
            if not current or not known:
                continue
            union = len(current | known)
            common = len(current & known)
            if union - common > SAVED_MAX_DIFF or common / union < SAVED_MIN_OVERLAP:
                continue
            if common / union > best_overlap:
                best, best_overlap = (mapping_, entry), common / union
    return best


def apply_saved(
    entry: dict,
    profiles: list[ColumnProfile],
    folder_names: set[str],
) -> dict | None:
    """Suggestions for a sheet from a saved entry; columns the entry does not
    know get fresh suggestions. None when the entry's target no longer exists."""
    try:
        model_type = ModelType(entry["model_type"])
        targets = _target_columns(model_type, entry["target"])
    except ValueError, KeyError, StopIteration:
        return None
    valid_keys = {t.key for t in targets}
    saved_columns = {normalize(h): k for h, k in entry.get("columns", {}).items()}
    saved_values = {normalize(h): v for h, v in (entry.get("values") or {}).items()}
    known = {normalize(h) for h in entry.get("headers", [])}
    columns = {}
    for profile in profiles:
        key = saved_columns.get(normalize(profile.header))
        if key in valid_keys:
            columns[profile.header] = {"key": key, "reason": "saved"}
    new = [p for p in profiles if normalize(p.header) not in known]
    taken = {s["key"] for s in columns.values()}
    fresh = suggest_columns(
        new, [t for t in targets if t.key not in taken], folder_names
    )
    columns.update(fresh)
    keys = {h: s["key"] for h, s in columns.items()}
    values = suggest_values(profiles, keys, targets)
    for header, suggestions in values.items():
        for value, choice in saved_values.get(normalize(header), {}).items():
            if value in suggestions:
                suggestions[value] = {"value": choice, "reason": "saved"}
    defaults = {
        k: v
        for k, v in (entry.get("defaults") or {}).items()
        if k in valid_keys and k not in keys.values()
    }
    return {
        "target": {"model_type": model_type.value, "sheet": entry["target"]},
        "mapping": {"columns": columns, "values": values, "defaults": defaults},
        "new_columns": [p.header for p in new],
    }


def _saved_header_row(source: SourceSheet, saved: list[dict]) -> int:
    """Where the header is, once a saved layout is known: the detected row
    unless a saved mapping recognises the headers on the row it was saved with
    (one set by hand under a busy banner)."""
    if match_saved(source.headers, saved):
        return source.header_row
    for row in sorted({e.get("header_row", 1) for m in saved for e in m["sheets"]}):
        if not isinstance(row, int) or not 1 <= row <= len(source.raw):
            continue
        at_row = [
            {**m, "sheets": [e for e in m["sheets"] if e.get("header_row", 1) == row]}
            for m in saved
        ]
        if match_saved(SourceSheet(source.name, source.raw, row - 1).headers, at_row):
            return row - 1
    return source.header_row


def analyze(
    file: io.BytesIO,
    folder_names: set[str],
    overrides: dict[str, dict] | None = None,
    filename: str = "",
    saved: list[dict] | None = None,
) -> dict:
    """Describe every sheet and suggest a mapping for it.

    *overrides* maps a source sheet name to {"header_row", "model_type",
    "sheet"} the user chose, replacing what would be detected. *saved* are the
    saved mappings to try first, as {"id", "name", "sheets"}.
    """
    overrides = overrides or {}
    if not isinstance(overrides, dict) or not all(
        isinstance(v, dict) for v in overrides.values()
    ):
        raise TypeError("InvalidOverrides")
    out = []
    for source in read_source(file):
        chosen = overrides.get(source.name, {})
        if source.raw.empty:
            out.append({"name": source.name, "empty": True})
            continue
        source.header_row = (
            int(chosen["header_row"]) - 1
            if chosen.get("header_row")
            else detect_header_row(source.raw)
        )
        source.check_header_row()
        if saved and not chosen:
            source.header_row = _saved_header_row(source, saved)
        frame = source.frame()
        profiles = profile_columns(frame)
        # A CSV has no sheet name: its file name says what it holds.
        hint = Path(filename).stem if source.name == "CSV" else source.name
        candidates = rank_targets(profiles, folder_names, hint)
        from_saved = None
        if saved and not chosen.get("model_type"):
            match = match_saved([p.header for p in profiles], saved)
            if match and (applied := apply_saved(match[1], profiles, folder_names)):
                from_saved = {
                    "id": match[0]["id"],
                    "name": match[0]["name"],
                    "new_columns": applied["new_columns"],
                }
        target = (
            {"model_type": chosen["model_type"], "sheet": chosen["sheet"]}
            if chosen.get("model_type")
            else (candidates[0] if candidates else None)
        )
        mapping = None
        if from_saved:
            target, mapping = applied["target"], applied["mapping"]
        elif target is not None:
            model_type = ModelType(target["model_type"])
            if target["sheet"] not in TEMPLATE_ROW_MODELS.get(model_type, {}):
                raise ValueError(f"UnknownTargetSheet: {target['sheet']}")
            targets = _target_columns(model_type, target["sheet"])
            column_suggestions = suggest_columns(profiles, targets, folder_names)
            columns = {h: s["key"] for h, s in column_suggestions.items()}
            mapping = {
                "columns": column_suggestions,
                "values": suggest_values(profiles, columns, targets),
            }
        out.append(
            {
                "name": source.name,
                "empty": False,
                "header_row": source.header_row + 1,
                "row_count": len(frame),
                "columns": [
                    {"header": p.header, "samples": p.samples, "distinct": p.distinct}
                    for p in profiles
                ],
                "candidates": candidates,
                "target": target,
                "mapping": mapping,
                "saved_mapping": from_saved,
            }
        )
    return {"sheets": out}


# ─── Applying a mapping ──────────────────────────────────────────────────────


@dataclass
class SheetMapping:
    source: str
    target: str
    header_row: int  # 1-based
    columns: dict[str, str]  # source header -> template column
    values: dict[str, dict[str, Any]] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)  # same value, every row


@dataclass
class ImportStep:
    model_type: ModelType
    sheets: list[SheetMapping]
    options: dict = field(default_factory=dict)


def parse_steps(payload: Any) -> list[ImportStep]:
    """Validate the mapping a client sends; raise ValueError on anything off."""
    if not isinstance(payload, dict) or not isinstance(payload.get("steps"), list):
        raise TypeError("InvalidMapping: steps")
    steps = []
    for raw_step in payload["steps"]:
        if not isinstance(raw_step, dict) or not isinstance(
            raw_step.get("sheets") or [], list
        ):
            raise TypeError("InvalidMapping: step")
        if not isinstance(raw_step.get("options") or {}, dict):
            raise TypeError("InvalidMapping: options")
        model_type = ModelType.from_string(raw_step.get("model_type"))
        if model_type not in TEMPLATE_ROW_MODELS:
            raise ValueError(f"UnmappableModelType: {raw_step.get('model_type')}")
        templates = _template_headers(model_type)
        sheets = []
        for raw_sheet in raw_step.get("sheets") or []:
            if not isinstance(raw_sheet, dict):
                raise TypeError("InvalidMapping: sheet")
            columns = raw_sheet.get("columns") or {}
            values = raw_sheet.get("values") or {}
            if not isinstance(columns, dict) or not all(
                isinstance(k, str) for k in columns.values()
            ):
                raise TypeError("InvalidMapping: columns")
            if not isinstance(values, dict) or not all(
                isinstance(v, dict) for v in values.values()
            ):
                raise TypeError("InvalidMapping: values")
            target = raw_sheet.get("target")
            if target not in templates:
                raise ValueError(f"UnknownTargetSheet: {target}")
            unknown = set(columns.values()) - set(templates[target])
            if unknown:
                raise ValueError(f"UnknownColumns: {sorted(unknown)}")
            if len(set(columns.values())) != len(columns):
                raise ValueError("DuplicateTargetColumns")
            defaults = raw_sheet.get("defaults") or {}
            if not isinstance(defaults, dict) or not all(
                isinstance(v, str | int | float | bool) for v in defaults.values()
            ):
                raise ValueError("InvalidDefaults")
            if set(defaults) - set(templates[target]):
                raise ValueError(
                    f"UnknownColumns: {sorted(set(defaults) - set(templates[target]))}"
                )
            if set(defaults) & set(columns.values()):
                raise ValueError("DefaultForMappedColumn")
            header_row = raw_sheet.get("header_row", 1)
            if not isinstance(header_row, int) or header_row < 1:
                raise ValueError("InvalidHeaderRow")
            sheets.append(
                SheetMapping(
                    source=str(raw_sheet.get("source")),
                    target=target,
                    header_row=header_row,
                    columns=columns,
                    values=values,
                    defaults=defaults,
                )
            )
        if not sheets:
            raise ValueError("InvalidMapping: no sheet")
        steps.append(ImportStep(model_type, sheets, raw_step.get("options") or {}))
    if not steps:
        raise ValueError("InvalidMapping: no step")
    return steps


def apply_sheet(source: SourceSheet, mapping: SheetMapping) -> pd.DataFrame:
    source.header_row = mapping.header_row - 1
    source.check_header_row()
    frame = source.frame()
    missing = set(mapping.columns) - set(frame.columns)
    if missing:
        raise ValueError(f"MissingSourceColumns: {sorted(missing)}")
    out = pd.DataFrame(index=frame.index)
    for header, key in mapping.columns.items():
        translate = {_cell_key(k): v for k, v in mapping.values.get(header, {}).items()}
        out[key] = frame[header].map(
            lambda v, translate=translate: (
                v if pd.isna(v) else translate.get(_cell_key(v), v)
            )
        )
    return out


def _task_occurrences(summary: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Split dates the task importer does not read off the task rows.

    A last-done date becomes a completed occurrence, in the per-task sheets
    ("{row}-{name}") the importer reads past occurrences from. With no start
    date mapped, the schedule starts there, so the next occurrence follows from
    the period; failing that, at the next-occurrence date (export-only otherwise).
    """
    summary = summary.reset_index(drop=True)
    anchors = [summary[a] for a in ("last_done", "next_occurrence") if a in summary]
    if "task_date" not in summary.columns and anchors:
        summary["task_date"] = (
            anchors[0].combine_first(anchors[1]) if len(anchors) == 2 else anchors[0]
        )
    occurrences = {}
    if "last_done" in summary.columns:
        for row, (name, done) in enumerate(
            zip(summary.get("name", [""] * len(summary)), summary["last_done"]),
            start=1,
        ):
            if pd.isna(done) or not str(done).strip():
                continue
            title = f"{row}-{re.sub(SHEET_NAME_INVALID_CHARS, '', str(name or ''))}"
            occurrences[title[:31]] = pd.DataFrame(
                [{"due_date": done, "status": "completed"}]
            )
    dropped = ["last_done", "next_occurrence", "next_occurrence_status"]
    return summary.drop(columns=dropped, errors="ignore"), occurrences


def build_workbook(sources: list[SourceSheet], step: ImportStep) -> io.BytesIO:
    """The workbook the step's template describes, filled from the source."""
    by_name = {s.name: s for s in sources}
    frames: dict[str, list[pd.DataFrame]] = {}
    for sheet in step.sheets:
        source = by_name.get(sheet.source)
        if source is None:
            raise ValueError(f"UnknownSourceSheet: {sheet.source}")
        frame = apply_sheet(source, sheet)
        for column, value in {
            **DEFAULT_VALUES.get(step.model_type, {}),
            **sheet.defaults,
        }.items():
            if column not in frame.columns:
                frame[column] = value
                # Half a schedule completes rows carrying the other half; a row
                # with neither is a one-off task.
                other = SCHEDULE_PAIR.get(column)
                if step.model_type == ModelType.TASK_TEMPLATE and other in frame:
                    blank = frame[other].isna() | (
                        frame[other].astype(str).str.strip() == ""
                    )
                    frame.loc[blank, column] = None
        frames.setdefault(sheet.target, []).append(frame)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # Template order: multi-sheet importers read parents before children.
        occurrences = {}
        for target in _template_headers(step.model_type):
            if target in frames:
                frame = pd.concat(frames[target], ignore_index=True)
                if step.model_type == ModelType.TASK_TEMPLATE:
                    frame, occurrences = _task_occurrences(frame)
                frame.to_excel(writer, sheet_name=target, index=False)
        for title, rows in occurrences.items():
            rows.to_excel(writer, sheet_name=title, index=False)
    buffer.seek(0)
    return buffer


def _stopped(results) -> bool:
    """Whether an importer stopped on a conflict; multi-sheet importers report
    it per sheet ({"templates": {"stopped": true}, ...})."""
    if not isinstance(results, dict):
        return False
    return bool(results.get("stopped")) or any(
        isinstance(v, dict) and v.get("stopped") for v in results.values()
    )


def run_steps(
    request,
    steps: list[ImportStep],
    workbooks: list[io.BytesIO],
    defaults: dict,
    dry_run: bool,
) -> list[dict]:
    """Run each step through the regular importer. A dry run executes the same
    writes and rolls them all back, with outgoing mail swallowed."""
    loader = LoadFileView()
    results = []
    with (
        transaction.atomic() if dry_run else nullcontext(),
        mailer.suppressed() if dry_run else nullcontext(),
    ):
        for step, workbook in zip(steps, workbooks, strict=True):
            options = {**defaults, **step.options}
            response = loader.process_excel_file(
                request,
                workbook,
                ImportOptions(
                    model_type=step.model_type.value,
                    folder_id=options.get("folder_id") or None,
                    perimeter_id=options.get("perimeter_id") or None,
                    framework_id=options.get("framework_id") or None,
                    matrix_id=options.get("matrix_id") or None,
                    target_id=options.get("target_id") or None,
                    on_conflict=options.get("on_conflict") or ConflictMode.STOP,
                    container_name=options.get("container_name") or None,
                ),
            )
            results.append(
                {
                    "model_type": step.model_type.value,
                    "status": response.status_code,
                    # A refusal comes back without a body (403 from the importer).
                    **(response.data or {"error": "notAllowed"}),
                }
            )
            if response.status_code != status.HTTP_200_OK or _stopped(
                (response.data or {}).get("results")
            ):
                break
        if dry_run:
            transaction.set_rollback(True)
    return results


# ─── API ─────────────────────────────────────────────────────────────────────


def _uploaded_file(request) -> tuple[io.BytesIO | None, Response | None]:
    serializer = LoadFileSerializer(data=request.data)
    if not serializer.is_valid():
        return None, Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return io.BytesIO(serializer.validated_data["file"].read()), None


# What a client may learn of a refusal: the code its message starts with. The
# message itself, which can quote the input, stays in the logs.
ERROR_CODES = (
    "HeaderRowOutOfRange",
    "InvalidHeaderRow",
    "InvalidHeaders",
    "InvalidSheets",
    "ColumnsOutsideHeaders",
    "InvalidOverrides",
    "InvalidField",
    "InvalidMapping",
    "InvalidDefaults",
    "DefaultForMappedColumn",
    "UnmappableModelType",
    "UnknownTargetSheet",
    "UnknownSourceSheet",
    "UnknownColumns",
    "DuplicateTargetColumns",
    "MissingSourceColumns",
)


def error_code(error: Exception) -> str | None:
    text = str(error)
    return next((code for code in ERROR_CODES if text.startswith(code)), None)


def _json_field(request, name: str, default):
    raw = request.data.get(name)
    if raw in (None, ""):
        return default
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise TypeError(f"InvalidField: {name} is not an object")
    return value


class MappingSchemaView(APIView):
    def get(self, request, model_type: str | None = None):
        if model_type is None:
            return Response({"model_types": mappable_model_types()})
        parsed = ModelType.from_string(model_type)
        if parsed not in TEMPLATE_ROW_MODELS:
            return Response(
                {"error": "UnmappableModelType"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(template_schema(parsed))


class AnalyzeFileView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file, error = _uploaded_file(request)
        if error:
            return error
        try:
            overrides = _json_field(request, "overrides", {})
            folder_names = {
                normalize(n) for n in get_accessible_folders_map(request.user)
            }
            name = request.data["file"].name
            saved = None
            if str(request.data.get("use_saved", "true")).lower() != "false":
                saved = [
                    {"id": str(m.id), "name": m.name, "sheets": m.sheets}
                    for m in viewable_mappings(request.user).order_by(
                        F("last_used_at").desc(nulls_last=True), "-created_at"
                    )
                ]
            return Response(analyze(file, folder_names, overrides, name, saved))
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("file analysis failed", error=e)
            return Response(
                {"error": "fileAnalysisFailed", "detail": error_code(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MappedImportView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file, error = _uploaded_file(request)
        if error:
            return error
        try:
            steps = parse_steps(_json_field(request, "mapping", None))
            defaults = _json_field(request, "options", {})
            try:
                used = [UUID(str(i)) for i in defaults.get("saved_mapping_ids") or []]
            except ValueError as e:
                raise ValueError("InvalidField: saved_mapping_ids") from e
            sources = read_source(file)
            # Build every workbook upfront: a bad mapping fails before any write.
            workbooks = [build_workbook(sources, step) for step in steps]
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("invalid import mapping", error=e)
            return Response(
                {"error": "invalidMapping", "detail": error_code(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dry_run = str(request.data.get("dry_run", "")).lower() in ("1", "true")
        results = run_steps(request, steps, workbooks, defaults, dry_run)
        if not dry_run and used:
            viewable_mappings(request.user).filter(id__in=used).update(
                use_count=F("use_count") + 1, last_used_at=timezone.now()
            )
        return Response({"dry_run": dry_run, "steps": results})


def viewable_mappings(user):
    return ImportMapping.objects.filter(
        id__in=RoleAssignment.get_viewable_object_ids(user, ImportMapping)
    )


class ImportMappingViewSet(BaseModelViewSet):
    """Saved mappings of recurring spreadsheet layouts, shared across the instance."""

    serializers_module = "data_wizard.serializers"
    model = ImportMapping
    filterset_fields = ["folder"]
    search_fields = ["name", "description"]
