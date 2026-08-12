"""Tests for chat.questionnaire parser + vocabulary detection.

Covers the pure / openpyxl-driven helpers that don't need Qdrant or LLM:

- ``_detect_headers`` — first-row-with-≥2-non-empty heuristic
- ``_collect_rows`` — preview + total row counting with skip rules
- ``_extract_status_marker`` — pulls the verdict-bearing field out of an
  indexed text body for the visible context label
- ``_parse_data_validation_list`` — inline-quoted list and range-ref forms
- ``_detect_cell_vocabulary`` — per-cell drop-down detection

``extract_questions_from_sheet`` (the end-to-end row materializer) needs DB +
file storage and is exercised by the integration smoke flow rather than here.
"""

import io

import openpyxl
import pytest
from openpyxl.worksheet.datavalidation import DataValidation

from chat.questionnaire import (
    _collect_rows,
    _detect_cell_vocabulary,
    _detect_column_candidates,
    _detect_headers,
    _extract_status_marker,
    _parse_data_validation_list,
)


def _new_ws():
    wb = openpyxl.Workbook()
    return wb, wb.active


class TestDetectHeaders:
    def test_first_row_is_headers(self):
        wb, ws = _new_ws()
        ws.append(["Question", "Status", "Comment"])
        ws.append(["Q1", "Yes", ""])
        idx, headers = _detect_headers(ws)
        assert idx == 0
        assert headers == ["Question", "Status", "Comment"]

    def test_skips_title_row_then_blank(self):
        wb, ws = _new_ws()
        ws.append(["Big Title"])
        ws.append([])
        ws.append(["Question", "Status", "Comment"])
        idx, headers = _detect_headers(ws)
        assert idx == 2
        assert headers == ["Question", "Status", "Comment"]

    def test_empty_sheet(self):
        wb, ws = _new_ws()
        idx, headers = _detect_headers(ws)
        assert idx == 0
        assert headers == []

    def test_trailing_empty_columns_trimmed(self):
        wb, ws = _new_ws()
        ws.append(["A", "B", "", "", ""])
        ws.append(["v", "w"])
        idx, headers = _detect_headers(ws)
        assert headers == ["A", "B"]


class TestCollectRows:
    def test_count_and_preview(self):
        wb, ws = _new_ws()
        ws.append(["Q", "S"])
        for i in range(25):
            ws.append([f"q{i}", "yes"])
        total, preview = _collect_rows(ws, header_row_idx=0, header_count=2)
        assert total == 25
        assert len(preview) == 20  # capped preview
        assert preview[0] == ["q0", "yes"]

    def test_skips_blank_rows_in_count(self):
        wb, ws = _new_ws()
        ws.append(["Q", "S"])
        ws.append(["q1", "yes"])
        ws.append([])  # all-blank
        ws.append(["q2", "no"])
        total, _ = _collect_rows(ws, header_row_idx=0, header_count=2)
        assert total == 2

    def test_no_headers(self):
        wb, ws = _new_ws()
        total, preview = _collect_rows(ws, header_row_idx=0, header_count=0)
        assert total == 0
        assert preview == []


class TestExtractStatusMarker:
    def test_result_wins_over_status(self):
        text = (
            "Type: Requirement assessment\nStatus: To do\nResult: Partially compliant\n"
        )
        assert _extract_status_marker(text) == "result=partially_compliant"

    def test_status_only(self):
        text = "Type: Applied control\nStatus: Active\n"
        assert _extract_status_marker(text) == "status=active"

    def test_no_marker(self):
        assert _extract_status_marker("just some text") == ""
        assert _extract_status_marker("") == ""

    def test_normalises_spaces_and_dashes(self):
        text = "Status: In Progress\n"
        assert _extract_status_marker(text) == "status=in_progress"


class TestParseDataValidationList:
    def test_inline_quoted_list(self):
        wb, ws = _new_ws()
        formula = '"Yes,No,Partial,N/A"'
        assert _parse_data_validation_list(ws, formula) == [
            "Yes",
            "No",
            "Partial",
            "N/A",
        ]

    def test_inline_with_whitespace(self):
        wb, ws = _new_ws()
        formula = '"Compliant , Partial , Not Compliant"'
        assert _parse_data_validation_list(ws, formula) == [
            "Compliant",
            "Partial",
            "Not Compliant",
        ]

    def test_empty_or_none(self):
        wb, ws = _new_ws()
        assert _parse_data_validation_list(ws, None) == []
        assert _parse_data_validation_list(ws, "") == []


class TestDetectCellVocabulary:
    def test_dropdown_inline_list(self):
        wb, ws = _new_ws()
        ws.append(["Q", "Response"])
        ws.append(["q1", ""])
        dv = DataValidation(
            type="list",
            formula1='"Compliant,Partially Compliant,Not Compliant,N/A"',
            allow_blank=True,
        )
        dv.add("B2:B100")
        ws.add_data_validation(dv)
        # Cell B2, col index 1 (zero-based). excel_row=2.
        assert _detect_cell_vocabulary(ws, excel_row=2, col_idx=1) == [
            "Compliant",
            "Partially Compliant",
            "Not Compliant",
            "N/A",
        ]

    def test_no_dropdown(self):
        wb, ws = _new_ws()
        ws.append(["Q", "Response"])
        assert _detect_cell_vocabulary(ws, excel_row=2, col_idx=1) == []

    def test_dropdown_outside_target_cell(self):
        wb, ws = _new_ws()
        ws.append(["Q", "Response"])
        dv = DataValidation(
            type="list",
            formula1='"Yes,No"',
            allow_blank=True,
        )
        dv.add("A1:A1")  # only on a different cell
        ws.add_data_validation(dv)
        assert _detect_cell_vocabulary(ws, excel_row=2, col_idx=1) == []


class TestDetectColumnCandidates:
    def test_picks_data_validation_first(self):
        wb, ws = _new_ws()
        ws.append(["A", "B"])
        ws.append(["x", "Yes"])
        ws.append(["y", "No"])
        dv = DataValidation(
            type="list",
            formula1='"Yes,No,Maybe"',
            allow_blank=True,
        )
        dv.add("B2:B100")
        ws.add_data_validation(dv)
        result = _detect_column_candidates(ws, col_idx=1, header_row_idx=0)
        assert result is not None
        assert result["source"] == "data_validation"
        assert result["values"] == ["Yes", "No", "Maybe"]

    def test_falls_back_to_distinct_values(self):
        wb, ws = _new_ws()
        ws.append(["A", "B"])
        ws.append(["x", "Yes"])
        ws.append(["y", "No"])
        ws.append(["z", "Yes"])
        result = _detect_column_candidates(ws, col_idx=1, header_row_idx=0)
        assert result is not None
        assert result["source"] == "distinct_values"
        assert sorted(result["values"]) == ["No", "Yes"]

    def test_too_many_distinct_returns_none(self):
        wb, ws = _new_ws()
        ws.append(["A", "B"])
        for i in range(25):
            ws.append([f"q{i}", f"unique-answer-{i}"])
        # >max_distinct → free text, not a controlled vocab
        result = _detect_column_candidates(
            ws, col_idx=1, header_row_idx=0, max_distinct=20
        )
        assert result is None

    def test_single_value_not_a_vocab(self):
        wb, ws = _new_ws()
        ws.append(["A", "B"])
        ws.append(["x", "Yes"])
        result = _detect_column_candidates(ws, col_idx=1, header_row_idx=0)
        assert result is None
