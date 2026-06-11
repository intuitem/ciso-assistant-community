"""Tests for page_context.py — URL parsing into ParsedContext."""

import pytest

pytestmark = pytest.mark.django_db


class TestParsePageContext:
    def test_risk_assessments_list(self):
        from chat.page_context import parse_page_context

        result = parse_page_context({"path": "/risk-assessments"})
        assert result is not None
        assert result.model_key == "risk_assessment"
        assert result.object_id is None
        assert result.page_type == "list"

    def test_risk_assessments_detail(self):
        from chat.page_context import parse_page_context

        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = parse_page_context({"path": f"/risk-assessments/{uuid}"})
        assert result is not None
        assert result.model_key == "risk_assessment"
        assert result.object_id == uuid
        assert result.page_type == "detail"

    def test_risk_assessments_edit(self):
        from chat.page_context import parse_page_context

        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = parse_page_context({"path": f"/risk-assessments/{uuid}/edit"})
        assert result is not None
        assert result.model_key == "risk_assessment"
        assert result.object_id == uuid
        assert result.page_type == "edit"

    def test_ebios_rm_alias(self):
        from chat.page_context import parse_page_context

        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = parse_page_context({"path": f"/ebios-rm/{uuid}"})
        assert result is not None
        assert result.model_key == "ebios_rm_study"
        assert result.object_id == uuid

    def test_folders_detail(self):
        from chat.page_context import parse_page_context

        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = parse_page_context({"path": f"/folders/{uuid}"})
        assert result is not None
        assert result.model_key == "folder"
        assert result.object_id == uuid

    def test_empty_path_returns_none(self):
        from chat.page_context import parse_page_context

        assert parse_page_context({"path": ""}) is None
        assert parse_page_context({}) is None

    def test_unknown_path_returns_none(self):
        from chat.page_context import parse_page_context

        assert parse_page_context({"path": "/analytics"}) is None
        assert parse_page_context({"path": "/dashboard"}) is None

    def test_trailing_slashes(self):
        from chat.page_context import parse_page_context

        result = parse_page_context({"path": "/applied-controls/"})
        assert result is not None
        assert result.model_key == "applied_control"
        assert result.page_type == "list"

    def test_compliance_assessments(self):
        from chat.page_context import parse_page_context

        uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        result = parse_page_context({"path": f"/compliance-assessments/{uuid}"})
        assert result is not None
        assert result.model_key == "compliance_assessment"
        assert result.object_id == uuid
