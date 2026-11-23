import functools
import io

import openpyxl

import warnings
from pathlib import Path

from core.cyfun import (
    CYFUN_2023_URN,
    CYFUN_2025_URN,
    LEVELS,
    TEMPLATE_2023,
    normalize_ref_id,
    ref_id_2023,
)

CYFUN_LIBRARY_URN = "urn:intuitem:risk:library:ccb-cyfun2025"
CYFUN_2023_LIBRARY_URN = "urn:intuitem:risk:library:ccb-cff-2023-03-01"

FUNCTION_SHEETS = ("GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER")
LEVEL_TO_GROUP = {"basic": "B", "important": "I", "essential": "E"}

HEADER_ROW = 2
DATA_START_ROW = 3


def _detect_columns(sheet):
    """Map header labels to column indices; the BASIC edition has no
    'Assurance level' column, shifting everything after 'Subcategory' left."""
    headers = {}
    for cell in sheet[HEADER_ROW]:
        if cell.value:
            headers[str(cell.value).strip().lower()] = cell.column
    required = ("requirement", "documentation score", "implementation score")
    if not all(key in headers for key in required):
        return None
    return {
        "level": headers.get("assurance level"),
        "requirement": headers["requirement"],
        "doc_score": headers["documentation score"],
        "impl_score": headers["implementation score"],
        "comments": headers.get("comments and/or additional information"),
        "assessor_comments": headers.get("assessor comments"),
    }


def _parse_score(value):
    """Returns (score, is_na)."""
    if value is None or value == "":
        return None, False
    if isinstance(value, str):
        if value.strip().upper() in ("N/A", "NA"):
            return None, True
        try:
            return int(float(value)), False
        except ValueError:
            return None, False
    if isinstance(value, (int, float)):
        return int(value), False
    return None, False


def _cell(row, col):
    if not col or len(row) < col:
        return None
    return row[col - 1]


def _cell_text(row, col):
    return str(_cell(row, col) or "").strip()


def process_cyfun_file(file_content: bytes) -> dict:
    workbook = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
    sheet_names = set(workbook.sheetnames)
    is_2025 = all(name in sheet_names for name in FUNCTION_SHEETS)
    if not is_2025 and any(
        f"{level.upper()} Details" in sheet_names for level in LEVELS
    ):
        return _process_cyfun_2023(workbook)
    if not is_2025:
        raise ValueError("UnrecognizedCyfunWorkbook")

    level = None
    levels_seen = set()
    records = []
    for sheet_name in FUNCTION_SHEETS:
        sheet = workbook[sheet_name]
        cols = _detect_columns(sheet)
        if cols is None:
            raise ValueError("UnrecognizedCyfunWorkbook")
        if level is None:
            marker = str(sheet.cell(1, cols["doc_score"]).value or "").strip().lower()
            if marker in LEVELS:
                level = marker
        for row in sheet.iter_rows(min_row=DATA_START_ROW, values_only=True):
            ref_id = normalize_ref_id(_cell_text(row, cols["requirement"]))
            if not ref_id:
                continue
            row_level = _cell_text(row, cols["level"]).lower()
            if row_level in LEVELS:
                levels_seen.add(row_level)

            record = {"ref_id": ref_id, "assessable": True}
            doc_score, doc_na = _parse_score(_cell(row, cols["doc_score"]))
            impl_score, impl_na = _parse_score(_cell(row, cols["impl_score"]))
            if doc_na or impl_na:
                record["compliance_result"] = "not_applicable"
            else:
                if doc_score is not None:
                    record["documentation_score"] = doc_score
                if impl_score is not None:
                    record["implementation_score"] = impl_score

            observations = _cell_text(row, cols["comments"])
            assessor_comments = _cell_text(row, cols["assessor_comments"])
            if assessor_comments:
                assessor_comments = f"Assessor comments: {assessor_comments}"
                observations = (
                    f"{observations}\n\n{assessor_comments}"
                    if observations
                    else assessor_comments
                )
            if observations:
                record["observations"] = observations
            records.append(record)

    if not records:
        raise ValueError("EmptyCyfunWorkbook")
    if level not in LEVELS:
        level = next((lvl for lvl in reversed(LEVELS) if lvl in levels_seen), None)
    return {
        "assurance_level": level,
        "records": records,
        "framework_urn": CYFUN_2025_URN,
        "library_urn": CYFUN_LIBRARY_URN,
    }


# CyFun 2023 "<LEVEL> Details" sheets: requirement E, scores G/H, comments M.
_COLUMNS_2023 = {"requirement": 5, "doc_score": 7, "impl_score": 8, "comments": 13}


def _details_2023(workbook, level) -> dict:
    """{ref_id: (doc, impl, comment)} of a level's sheet, in library ref_ids."""
    name = f"{level.upper()} Details"
    if name not in workbook.sheetnames:
        return {}
    cells = {}
    for row in workbook[name].iter_rows(min_row=DATA_START_ROW, values_only=True):
        ref_id = ref_id_2023(_cell(row, _COLUMNS_2023["requirement"]), level)
        if ref_id:
            cells[ref_id] = tuple(
                _cell(row, _COLUMNS_2023[key])
                for key in ("doc_score", "impl_score", "comments")
            )
    return cells


@functools.cache
def _blank_details_2023() -> dict:
    """{level: details} of the bundled blank tool, parsed once per process."""
    blank_path = (
        Path(__file__).resolve().parents[1] / "core/templates/core" / TEMPLATE_2023
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Data Validation extension")
        blank = openpyxl.load_workbook(blank_path, data_only=True)
    return {level: _details_2023(blank, level) for level in LEVELS}


def _process_cyfun_2023(workbook) -> dict:
    """The 2023 tool holds all three levels and ships with every score at 1, so
    the level assessed is the highest one whose sheet differs from the blank
    tool (core/templates/core)."""
    blank = _blank_details_2023()
    for level in reversed(LEVELS):
        filled = _details_2023(workbook, level)
        if filled and filled != blank[level]:
            break
    else:
        raise ValueError("EmptyCyfunWorkbook")

    records = []
    for ref_id, (doc, impl, comment) in filled.items():
        record = {"ref_id": ref_id, "assessable": True}
        doc_score, doc_na = _parse_score(doc)
        impl_score, impl_na = _parse_score(impl)
        if doc_na or impl_na:
            record["compliance_result"] = "not_applicable"
        else:
            if doc_score is not None:
                record["documentation_score"] = doc_score
            if impl_score is not None:
                record["implementation_score"] = impl_score
        if comment and str(comment).strip():
            record["observations"] = str(comment).strip()
        records.append(record)
    return {
        "assurance_level": level,
        "records": records,
        "framework_urn": CYFUN_2023_URN,
        "library_urn": CYFUN_2023_LIBRARY_URN,
    }
