"""Tests for heartbeat utility functions."""

import logging
from datetime import datetime, timedelta

from src.core.config import HeartbeatConfig, TerrariumConfig
from src.core.heartbeat import (
    _is_ok,
    _record_heartbeat_time,
    _setup_file_logging,
    build_heartbeat_prompt,
)
from src.core.memory import (
    cleanup_old_memory,
    load_recent_memory,
    should_cleanup_today,
)


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


class TestLoadRecentMemory:
    def test_returns_empty_when_no_memory_dir(self, tmp_path):
        assert load_recent_memory(tmp_path, 3) == ""

    def test_returns_empty_when_no_files(self, tmp_path):
        (tmp_path / ".terrarium" / "memory").mkdir(parents=True)
        assert load_recent_memory(tmp_path, 3) == ""

    def test_loads_today(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        today = datetime.now().date().isoformat()
        (mem_dir / f"memory-{today}.md").write_text(
            f"# {today}\n\n- something happened"
        )

        result = load_recent_memory(tmp_path, 3)
        assert "something happened" in result
        assert "Recent Memory" in result

    def test_loads_multiple_days(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        today = datetime.now().date()
        for offset in range(3):
            day = today - timedelta(days=offset)
            (mem_dir / f"memory-{day.isoformat()}.md").write_text(
                f"# {day}\n\n- day {offset}"
            )

        result = load_recent_memory(tmp_path, 3)
        assert "day 0" in result
        assert "day 1" in result
        assert "day 2" in result

    def test_skips_old_files(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        old_day = datetime.now().date() - timedelta(days=10)
        (mem_dir / f"memory-{old_day.isoformat()}.md").write_text(
            "# old\n\n- ancient history"
        )

        assert load_recent_memory(tmp_path, 3) == ""

    def test_skips_empty_files(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        today = datetime.now().date().isoformat()
        (mem_dir / f"memory-{today}.md").write_text("")

        assert load_recent_memory(tmp_path, 3) == ""


class TestCleanupOldMemory:
    def test_does_nothing_when_memory_dir_missing(self, tmp_path):
        cleanup_old_memory(tmp_path, 7)

    def test_removes_files_older_than_keep_days(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        old = datetime.now().date() - timedelta(days=10)
        recent = datetime.now().date() - timedelta(days=1)
        old_path = mem_dir / f"memory-{old.isoformat()}.md"
        recent_path = mem_dir / f"memory-{recent.isoformat()}.md"
        old_path.write_text("old")
        recent_path.write_text("recent")

        cleanup_old_memory(tmp_path, 3)

        assert not old_path.exists()
        assert recent_path.exists()

    def test_keeps_recent_files(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        today = datetime.now().date().isoformat()
        p = mem_dir / f"memory-{today}.md"
        p.write_text("today")

        cleanup_old_memory(tmp_path, 7)

        assert p.exists()

    def test_ignores_non_matching_filenames(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        other = mem_dir / "MEMORY.md"
        other.write_text("long term")

        cleanup_old_memory(tmp_path, 0)

        assert other.exists()


class TestShouldCleanupToday:
    def test_first_call_returns_true(self, tmp_path):
        (tmp_path / ".terrarium").mkdir(parents=True)
        assert should_cleanup_today(tmp_path) is True

    def test_second_call_same_day_returns_false(self, tmp_path):
        (tmp_path / ".terrarium").mkdir(parents=True)
        assert should_cleanup_today(tmp_path) is True
        assert should_cleanup_today(tmp_path) is False

    def test_returns_true_after_day_change(self, tmp_path):
        (tmp_path / ".terrarium").mkdir(parents=True)
        marker = tmp_path / ".terrarium" / "last_cleanup_date"
        marker.write_text("2000-01-01")
        assert should_cleanup_today(tmp_path) is True


class TestRecordHeartbeatTime:
    def test_creates_file(self, tmp_path):
        (tmp_path / ".terrarium").mkdir(parents=True)
        _record_heartbeat_time(tmp_path)
        marker = tmp_path / ".terrarium" / "last_heartbeat"
        assert marker.is_file()

    def test_creates_parent_dir_if_missing(self, tmp_path):
        _record_heartbeat_time(tmp_path)
        marker = tmp_path / ".terrarium" / "last_heartbeat"
        assert marker.is_file()

    def test_file_content_is_valid_iso_timestamp(self, tmp_path):
        (tmp_path / ".terrarium").mkdir(parents=True)
        before = datetime.now()
        _record_heartbeat_time(tmp_path)
        after = datetime.now()
        text = (tmp_path / ".terrarium" / "last_heartbeat").read_text().strip()
        parsed = datetime.fromisoformat(text)
        assert before <= parsed <= after


class TestBuildHeartbeatPrompt:
    def test_contains_timestamp(self, tmp_path):
        ts = "2026-03-30 12:00:00"
        config = TerrariumConfig(heartbeat=HeartbeatConfig(short_term_days=3))
        prompt = build_heartbeat_prompt(tmp_path, config, ts)
        assert ts in prompt

    def test_contains_heartbeat_ok_instruction(self, tmp_path):
        config = TerrariumConfig(heartbeat=HeartbeatConfig(short_term_days=3))
        prompt = build_heartbeat_prompt(tmp_path, config, "t")
        assert "HEARTBEAT_OK" in prompt

    def test_includes_recent_memory_when_present(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        today = datetime.now().date().isoformat()
        (mem_dir / f"memory-{today}.md").write_text("recent snippet")
        config = TerrariumConfig(heartbeat=HeartbeatConfig(short_term_days=3))
        prompt = build_heartbeat_prompt(tmp_path, config, "t")
        assert "recent snippet" in prompt
        assert "Recent Memory" in prompt

    def test_includes_long_term_memory_when_present(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        (mem_dir / "MEMORY.md").write_text("ltm content")
        config = TerrariumConfig(heartbeat=HeartbeatConfig(short_term_days=3))
        prompt = build_heartbeat_prompt(tmp_path, config, "t")
        assert "Long-Term Memory" in prompt
        assert "ltm content" in prompt


class TestSetupFileLogging:
    def test_second_call_does_not_add_duplicate_file_handler(self, tmp_path):
        root = logging.getLogger("terrarium")
        removed = []
        for h in root.handlers[:]:
            if isinstance(h, logging.FileHandler):
                root.removeHandler(h)
                removed.append(h)
        try:
            _setup_file_logging(tmp_path)
            after_first = [
                h for h in root.handlers if isinstance(h, logging.FileHandler)
            ]
            assert len(after_first) == 1
            _setup_file_logging(tmp_path)
            after_second = [
                h for h in root.handlers if isinstance(h, logging.FileHandler)
            ]
            assert len(after_second) == 1
        finally:
            for h in root.handlers[:]:
                if isinstance(h, logging.FileHandler):
                    root.removeHandler(h)
                    h.close()
            for h in removed:
                root.addHandler(h)
