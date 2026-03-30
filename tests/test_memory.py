"""Tests for the memory module."""

from datetime import datetime, timedelta

from src.core.config import HeartbeatConfig, TerrariumConfig
from src.core.memory import (
    build_user_message,
    cleanup_old_memory,
    load_long_term_memory,
    load_recent_memory,
    should_cleanup_today,
)


class TestLoadLongTermMemory:
    def test_returns_empty_when_no_file(self, tmp_path):
        assert load_long_term_memory(tmp_path) == ""

    def test_returns_empty_when_file_is_blank(self, tmp_path):
        mem = tmp_path / ".terrarium" / "memory" / "MEMORY.md"
        mem.parent.mkdir(parents=True)
        mem.write_text("   \n  ")
        assert load_long_term_memory(tmp_path) == ""

    def test_loads_content(self, tmp_path):
        mem = tmp_path / ".terrarium" / "memory" / "MEMORY.md"
        mem.parent.mkdir(parents=True)
        mem.write_text("# Long-Term Memory\n\n- always run tests")
        result = load_long_term_memory(tmp_path)
        assert "## Long-Term Memory" in result
        assert "always run tests" in result


class TestLoadRecentMemory:
    def test_returns_empty_when_no_dir(self, tmp_path):
        assert load_recent_memory(tmp_path, 3) == ""

    def test_loads_today(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        today = datetime.now().date().isoformat()
        (mem_dir / f"memory-{today}.md").write_text(f"# {today}\n\n- note")
        result = load_recent_memory(tmp_path, 3)
        assert "note" in result

    def test_skips_old(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        old = datetime.now().date() - timedelta(days=10)
        (mem_dir / f"memory-{old.isoformat()}.md").write_text("old")
        assert load_recent_memory(tmp_path, 3) == ""


class TestCleanupOldMemory:
    def test_removes_old_keeps_recent(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        old = datetime.now().date() - timedelta(days=10)
        recent = datetime.now().date()
        (mem_dir / f"memory-{old.isoformat()}.md").write_text("old")
        (mem_dir / f"memory-{recent.isoformat()}.md").write_text("recent")
        cleanup_old_memory(tmp_path, 3)
        assert not (mem_dir / f"memory-{old.isoformat()}.md").exists()
        assert (mem_dir / f"memory-{recent.isoformat()}.md").exists()


class TestShouldCleanupToday:
    def test_first_call_returns_true(self, tmp_path):
        assert should_cleanup_today(tmp_path) is True

    def test_second_call_returns_false(self, tmp_path):
        assert should_cleanup_today(tmp_path) is True
        assert should_cleanup_today(tmp_path) is False

    def test_stale_marker_triggers_cleanup(self, tmp_path):
        marker = tmp_path / ".terrarium" / "last_cleanup_date"
        marker.parent.mkdir(parents=True)
        marker.write_text("2000-01-01")
        assert should_cleanup_today(tmp_path) is True


class TestBuildUserMessage:
    def test_base_only_when_no_memory(self, tmp_path):
        config = TerrariumConfig()
        result = build_user_message(tmp_path, config, "hello")
        assert result == "hello"

    def test_appends_recent_memory(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        today = datetime.now().date().isoformat()
        (mem_dir / f"memory-{today}.md").write_text("recent note")
        config = TerrariumConfig(heartbeat=HeartbeatConfig(short_term_days=3))
        result = build_user_message(tmp_path, config, "hello")
        assert "hello" in result
        assert "recent note" in result

    def test_appends_long_term_memory(self, tmp_path):
        mem_dir = tmp_path / ".terrarium" / "memory"
        mem_dir.mkdir(parents=True)
        (mem_dir / "MEMORY.md").write_text("- important rule")
        config = TerrariumConfig()
        result = build_user_message(tmp_path, config, "base")
        assert "base" in result
        assert "important rule" in result
