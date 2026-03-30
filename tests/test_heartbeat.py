"""Tests for heartbeat utility functions."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.core.heartbeat import parse_interval, _is_ok, _load_recent_memory


# --- parse_interval ---


class TestParseInterval:
    def test_minutes(self):
        assert parse_interval("10m") == 600

    def test_hours(self):
        assert parse_interval("6h") == 21600

    def test_seconds(self):
        assert parse_interval("30s") == 30

    def test_bare_number_treated_as_seconds(self):
        assert parse_interval("120") == 120

    def test_strips_whitespace(self):
        assert parse_interval("  5m  ") == 300

    def test_one_minute(self):
        assert parse_interval("1m") == 60

    def test_invalid_suffix_raises(self):
        with pytest.raises(ValueError):
            parse_interval("10x")


# --- _is_ok ---


class TestIsOk:
    def test_exact_match(self):
        assert _is_ok("HEARTBEAT_OK") is True

    def test_with_trailing_whitespace(self):
        assert _is_ok("HEARTBEAT_OK  \n") is True

    def test_with_leading_whitespace(self):
        assert _is_ok("  HEARTBEAT_OK") is True

    def test_ends_with_ok(self):
        assert _is_ok("Everything looks good.\nHEARTBEAT_OK") is True

    def test_not_ok(self):
        assert _is_ok("I found some issues to fix.") is False

    def test_partial_match(self):
        assert _is_ok("HEARTBEAT") is False

    def test_empty_string(self):
        assert _is_ok("") is False

    def test_ok_in_middle_is_not_ok(self):
        assert _is_ok("HEARTBEAT_OK but also some notes") is False


# --- _load_recent_memory ---


class TestLoadRecentMemory:
    def test_returns_empty_when_no_memory_dir(self, tmp_path):
        assert _load_recent_memory(tmp_path) == ""

    def test_returns_empty_when_no_files(self, tmp_path):
        (tmp_path / ".terrarium" / "memory").mkdir(parents=True)
        assert _load_recent_memory(tmp_path) == ""

    def test_loads_today(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        today = datetime.now().date().isoformat()
        (mem_dir / f"memory-{today}.md").write_text(f"# {today}\n\n- something happened")

        result = _load_recent_memory(tmp_path)
        assert "something happened" in result
        assert "Recent Memory" in result

    def test_loads_multiple_days(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        today = datetime.now().date()
        for offset in range(3):
            day = today - timedelta(days=offset)
            (mem_dir / f"memory-{day.isoformat()}.md").write_text(f"# {day}\n\n- day {offset}")

        result = _load_recent_memory(tmp_path)
        assert "day 0" in result
        assert "day 1" in result
        assert "day 2" in result

    def test_skips_old_files(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        old_day = datetime.now().date() - timedelta(days=10)
        (mem_dir / f"memory-{old_day.isoformat()}.md").write_text("# old\n\n- ancient history")

        assert _load_recent_memory(tmp_path) == ""

    def test_skips_empty_files(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        today = datetime.now().date().isoformat()
        (mem_dir / f"memory-{today}.md").write_text("")

        assert _load_recent_memory(tmp_path) == ""
