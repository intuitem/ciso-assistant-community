"""Unit tests for the MCP task template tools: asset resolution and scheduling.

Network calls are mocked at their import sites, as in
test_risk_review_tools.py.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp.tools import (  # noqa: E402
    read_tools,
    update_tools,
    write_tools,
)
from tests.mcp.helpers import (  # noqa: E402
    UUID_A,
    UUID_C,
    UUID_F,
    _response,
    run,
)


class TestUpdateTaskTemplate:
    def _patch_ok(self):
        return patch.object(
            update_tools,
            "make_patch_request",
            return_value=_response(200, {"id": UUID_A, "name": "T"}),
        )

    def test_assets_resolved_in_folder(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(
                update_tools, "resolve_asset_id", return_value=UUID_C
            ) as resolve_asset,
        ):
            run(
                update_tools.update_task_template(
                    task_id=UUID_A, folder_id=UUID_F, assets=["ERP"]
                )
            )
        resolve_asset.assert_called_once_with("ERP", folder_id=UUID_F)
        assert patch_req.call_args.args[1] == {"folder": UUID_F, "assets": [UUID_C]}

    def test_assets_unscoped_without_folder(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(
                update_tools, "resolve_asset_id", return_value=UUID_C
            ) as resolve_asset,
        ):
            run(update_tools.update_task_template(task_id=UUID_A, assets=["ERP"]))
        resolve_asset.assert_called_once_with("ERP", folder_id=None)
        assert patch_req.call_args.args[1] == {"assets": [UUID_C]}


# ---------------------------------------------------------------------------
# _build_schedule
# ---------------------------------------------------------------------------


class TestBuildSchedule:
    def test_no_fields_returns_none(self):
        schedule, error = write_tools._build_schedule()
        assert schedule is None
        assert error is None

    def test_minimal_required_fields(self):
        schedule, error = write_tools._build_schedule("WEEKLY", 2)
        assert error is None
        assert schedule == {"interval": 2, "frequency": "WEEKLY"}

    def test_all_fields(self):
        schedule, error = write_tools._build_schedule(
            frequency="MONTHLY",
            interval=1,
            days_of_week=[1, 3],
            weeks_of_month=[1, -1],
            months_of_year=[1, 6],
            end_date="2027-01-01",
            occurrences=10,
            overdue_behavior="DELAY_NEXT",
        )
        assert error is None
        assert schedule == {
            "interval": 1,
            "frequency": "MONTHLY",
            "days_of_week": [1, 3],
            "weeks_of_month": [1, -1],
            "months_of_year": [1, 6],
            "end_date": "2027-01-01",
            "occurrences": 10,
            "overdue_behavior": "DELAY_NEXT",
        }

    def test_frequency_without_interval_is_rejected(self):
        schedule, error = write_tools._build_schedule(frequency="DAILY")
        assert schedule is None
        assert "required" in error

    def test_interval_without_frequency_is_rejected(self):
        schedule, error = write_tools._build_schedule(interval=1)
        assert schedule is None
        assert "required" in error

    def test_invalid_frequency_is_rejected(self):
        schedule, error = write_tools._build_schedule("BOGUS", 1)
        assert schedule is None
        assert "Invalid schedule_frequency" in error

    def test_invalid_overdue_behavior_is_rejected(self):
        schedule, error = write_tools._build_schedule(
            "DAILY", 1, overdue_behavior="BOGUS"
        )
        assert schedule is None
        assert "Invalid schedule_overdue_behavior" in error

    def test_a_single_optional_field_is_enough_to_require_the_pair(self):
        schedule, error = write_tools._build_schedule(end_date="2027-01-01")
        assert schedule is None
        assert "required" in error


# ---------------------------------------------------------------------------
# create_task_template / update_task_template: scheduling
# ---------------------------------------------------------------------------


class TestTaskTemplateScheduling:
    def test_create_with_schedule_sets_is_recurrent_true(self):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "T"}))
        with patch.object(write_tools, "make_post_request", post):
            result = run(
                write_tools.create_task_template(
                    name="T",
                    folder_id=UUID_F,
                    schedule_frequency="WEEKLY",
                    schedule_interval=2,
                    schedule_days_of_week=[1, 3],
                )
            )
        assert "Created task template" in result
        payload = post.call_args.args[1]
        assert payload["is_recurrent"] is True
        assert payload["schedule"] == {
            "interval": 2,
            "frequency": "WEEKLY",
            "days_of_week": [1, 3],
        }

    def test_create_without_schedule_defaults_is_recurrent_false(self):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "T"}))
        with patch.object(write_tools, "make_post_request", post):
            run(write_tools.create_task_template(name="T", folder_id=UUID_F))
        assert post.call_args.args[1]["is_recurrent"] is False

    def test_create_explicit_is_recurrent_overrides_schedule_inference(self):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "T"}))
        with patch.object(write_tools, "make_post_request", post):
            run(
                write_tools.create_task_template(
                    name="T",
                    folder_id=UUID_F,
                    schedule_frequency="DAILY",
                    schedule_interval=1,
                    is_recurrent=False,
                )
            )
        assert post.call_args.args[1]["is_recurrent"] is False

    def test_create_invalid_schedule_is_rejected_before_posting(self):
        post = Mock()
        with patch.object(write_tools, "make_post_request", post):
            result = run(
                write_tools.create_task_template(
                    name="T",
                    folder_id=UUID_F,
                    schedule_frequency="BOGUS",
                    schedule_interval=1,
                )
            )
        post.assert_not_called()
        assert "Invalid schedule_frequency" in result

    def test_update_with_schedule_sets_is_recurrent_true(self):
        patch_req = Mock(return_value=_response(200, {"id": UUID_A, "name": "T"}))
        with patch.object(update_tools, "make_patch_request", patch_req):
            result = run(
                update_tools.update_task_template(
                    task_id=UUID_A,
                    schedule_frequency="YEARLY",
                    schedule_interval=1,
                )
            )
        assert "Updated task template" in result
        payload = patch_req.call_args.args[1]
        assert payload["is_recurrent"] is True
        assert payload["schedule"] == {"interval": 1, "frequency": "YEARLY"}

    def test_update_explicit_is_recurrent_overrides_schedule_inference(self):
        patch_req = Mock(return_value=_response(200, {"id": UUID_A, "name": "T"}))
        with patch.object(update_tools, "make_patch_request", patch_req):
            run(
                update_tools.update_task_template(
                    task_id=UUID_A,
                    schedule_frequency="YEARLY",
                    schedule_interval=1,
                    is_recurrent=False,
                )
            )
        assert patch_req.call_args.args[1]["is_recurrent"] is False

    def test_update_without_schedule_leaves_is_recurrent_untouched(self):
        patch_req = Mock(return_value=_response(200, {"id": UUID_A, "name": "T"}))
        with patch.object(update_tools, "make_patch_request", patch_req):
            run(update_tools.update_task_template(task_id=UUID_A, name="T2"))
        assert "is_recurrent" not in patch_req.call_args.args[1]


# ---------------------------------------------------------------------------
# _format_schedule / get_task_template_details
# ---------------------------------------------------------------------------


class TestFormatSchedule:
    def test_none_schedule(self):
        assert read_tools._format_schedule(None) == "N/A"

    def test_minimal_schedule(self):
        assert (
            read_tools._format_schedule({"interval": 1, "frequency": "DAILY"})
            == "Every 1 Daily"
        )

    def test_full_schedule(self):
        formatted = read_tools._format_schedule(
            {
                "interval": 2,
                "frequency": "WEEKLY",
                "days_of_week": [1, 7],
                "end_date": "2027-01-01",
                "occurrences": 5,
                "overdue_behavior": "DELAY_NEXT",
            }
        )
        assert formatted == (
            "Every 2 Weekly; on Mon, Sun; until 2027-01-01; for 5 occurrence(s); "
            "(overdue: DELAY_NEXT)"
        )

    def test_no_impact_overdue_behavior_is_not_shown(self):
        formatted = read_tools._format_schedule(
            {"interval": 1, "frequency": "DAILY", "overdue_behavior": "NO_IMPACT"}
        )
        assert "overdue" not in formatted


class TestGetTaskTemplateDetails:
    def test_table_columns_stay_aligned(self):
        task = {
            "id": UUID_A,
            "name": "T",
            "is_recurrent": True,
            "enabled": True,
            "schedule": {"interval": 1, "frequency": "DAILY"},
            "next_occurrence": "2026-11-10",
            "assets": [],
            "applied_controls": [],
            "compliance_assessments": [],
            "risk_assessments": [],
            "assigned_to": [],
        }
        with patch.object(
            read_tools, "make_get_request", return_value=_response(200, task)
        ):
            result = run(read_tools.get_task_template_details(UUID_A))
        lines = result.strip().splitlines()
        header_cols = lines[0].count("|") - 1
        sep_cols = lines[1].count("|") - 1
        body_cols = lines[2].count("|") - 1
        assert header_cols == sep_cols == body_cols
        assert "Every 1 Daily" in lines[2]
        assert "2026-11-10" in lines[2]
