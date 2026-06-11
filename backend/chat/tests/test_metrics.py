"""Tests for chat metrics: Level 1 JSONL helper + chat_metrics command helpers."""

import json
import os

import pytest

from chat.management.commands.chat_metrics import parse_since, percentile
from chat.metrics import build_turn_metrics, record_metric


# ----------------------------------------------------------------------------
# build_turn_metrics
# ----------------------------------------------------------------------------


class TestBuildTurnMetrics:
    def _kwargs(self, **overrides):
        defaults = dict(
            prompt_tokens=2000,
            model_context_tokens=8000,
            system_prompt_tokens=400,
            context_tokens=600,
            history_tokens=900,
            user_tokens=100,
            summary_tokens=0,
            history_messages=8,
            section_names=["language", "main_context"],
        )
        defaults.update(overrides)
        return defaults

    def test_under_budget(self):
        m = build_turn_metrics(**self._kwargs())
        assert m["over_budget"] is False
        assert m["high_watermark"] is False
        assert m["utilization_pct"] == 25.0

    def test_at_high_watermark(self):
        # 80% threshold — exactly 6400 / 8000
        m = build_turn_metrics(**self._kwargs(prompt_tokens=6400))
        assert m["over_budget"] is False
        assert m["high_watermark"] is True
        assert m["utilization_pct"] == 80.0

    def test_over_budget(self):
        m = build_turn_metrics(**self._kwargs(prompt_tokens=8200))
        assert m["over_budget"] is True
        assert m["high_watermark"] is True
        assert m["utilization_pct"] == 102.5

    def test_zero_model_context_safe(self):
        # Defensive: shouldn't divide by zero if misconfigured
        m = build_turn_metrics(**self._kwargs(model_context_tokens=0))
        assert m["utilization_pct"] >= 0  # no crash


# ----------------------------------------------------------------------------
# record_metric (Level 1 JSONL writer)
# ----------------------------------------------------------------------------


class TestRecordMetric:
    def test_writes_jsonl(self, tmp_path, monkeypatch):
        path = tmp_path / "chat_metrics.jsonl"
        monkeypatch.setenv("CHAT_METRICS_LOG_PATH", str(path))

        record_metric("test_event", session_id="abc", tokens=42)
        record_metric("test_event", session_id="def", tokens=99)

        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        e1 = json.loads(lines[0])
        e2 = json.loads(lines[1])
        assert e1["event"] == "test_event"
        assert e1["session_id"] == "abc"
        assert e1["tokens"] == 42
        assert "ts" in e1
        assert e2["session_id"] == "def"

    def test_disabled_when_empty(self, tmp_path, monkeypatch):
        # Empty env value disables the writer
        monkeypatch.setenv("CHAT_METRICS_LOG_PATH", "")
        # No file should be created at any default path under tmp_path
        before = set(os.listdir(tmp_path))
        record_metric("noop", x=1)
        after = set(os.listdir(tmp_path))
        assert before == after

    def test_disabled_keywords(self, tmp_path, monkeypatch):
        for value in ("off", "false", "0", "disabled"):
            monkeypatch.setenv("CHAT_METRICS_LOG_PATH", value)
            record_metric("noop", x=1)  # should not raise

    def test_creates_parent_directory(self, tmp_path, monkeypatch):
        path = tmp_path / "nested" / "deep" / "chat_metrics.jsonl"
        monkeypatch.setenv("CHAT_METRICS_LOG_PATH", str(path))
        record_metric("dir_create_test", x=1)
        assert path.exists()
        assert path.parent.is_dir()

    def test_write_failure_does_not_raise(self, tmp_path, monkeypatch):
        # Point at a path we can't write (parent is a regular file)
        blocker = tmp_path / "blocker"
        blocker.write_text("I am a file")
        bad_path = blocker / "metrics.jsonl"  # parent is a file → mkdir fails
        monkeypatch.setenv("CHAT_METRICS_LOG_PATH", str(bad_path))
        # Must not raise
        record_metric("bad_path", x=1)


# ----------------------------------------------------------------------------
# parse_since (management command helper)
# ----------------------------------------------------------------------------


class TestParseSince:
    def test_hours(self):
        assert parse_since("24h").total_seconds() == 24 * 3600

    def test_days(self):
        assert parse_since("7d").total_seconds() == 7 * 86400

    def test_weeks(self):
        assert parse_since("4w").total_seconds() == 4 * 7 * 86400

    def test_months(self):
        # Months as 30 days
        assert parse_since("6m").total_seconds() == 6 * 30 * 86400

    def test_case_insensitive(self):
        assert parse_since("24H") == parse_since("24h")

    def test_rejects_invalid(self):
        from django.core.management.base import CommandError

        for bad in ("", "abc", "10x", "-1d", "0h", "1.5d"):
            with pytest.raises(CommandError):
                parse_since(bad)


# ----------------------------------------------------------------------------
# percentile (management command helper)
# ----------------------------------------------------------------------------


class TestPercentile:
    def test_empty(self):
        assert percentile([], 0.5) == 0

    def test_single_element(self):
        assert percentile([42], 0.5) == 42
        assert percentile([42], 0.99) == 42

    def test_basic(self):
        # Linear interp: p50 of [1..10] is 5.5 → 5 (int)
        assert percentile(list(range(1, 11)), 0.50) == 5
        # p95 of 100 elements is element index 94.05 → ~95
        assert percentile(list(range(1, 101)), 0.95) == 95

    def test_max(self):
        assert percentile([10, 20, 30, 40], 1.0) == 40

    def test_min(self):
        assert percentile([10, 20, 30, 40], 0.0) == 10

    def test_unsorted_input(self):
        assert percentile([40, 10, 30, 20], 0.50) == percentile([10, 20, 30, 40], 0.50)
