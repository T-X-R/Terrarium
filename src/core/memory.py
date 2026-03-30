"""Memory subsystem — loading, building, and lifecycle management.

Centralises all memory I/O so that agent, heartbeat, and CLI share one
implementation instead of duplicating or wrapping each other.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from src.core.config import TerrariumConfig

logger = logging.getLogger("terrarium.memory")


def load_long_term_memory(project_path: Path) -> str:
    """Read long-term memory from .terrarium/memory/MEMORY.md."""
    mem_file = project_path / ".terrarium" / "memory" / "MEMORY.md"
    if not mem_file.exists():
        return ""
    content = mem_file.read_text().strip()
    return f"## Long-Term Memory\n\n{content}" if content else ""


def load_recent_memory(project_path: Path, short_term_days: int) -> str:
    """Read the last *short_term_days* days of memory-YYYY-MM-DD.md files."""
    memory_dir = project_path / ".terrarium" / "memory"
    if not memory_dir.exists():
        return ""
    parts = []
    today = datetime.now().date()
    for offset in range(short_term_days):
        day = today - timedelta(days=offset)
        path = memory_dir / f"memory-{day.isoformat()}.md"
        if path.exists():
            content = path.read_text().strip()
            if content:
                parts.append(content)
    if not parts:
        return ""
    return "## Recent Memory (last few days)\n\n" + "\n\n".join(parts)


def cleanup_old_memory(project_path: Path, keep_days: int) -> None:
    """Remove short-term memory files older than *keep_days*."""
    memory_dir = project_path / ".terrarium" / "memory"
    if not memory_dir.exists():
        return
    cutoff = datetime.now().date() - timedelta(days=keep_days)
    for path in memory_dir.glob("memory-*.md"):
        try:
            date_str = path.stem.removeprefix("memory-")
            file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if file_date < cutoff:
                path.unlink()
                logger.info("Cleaned up old memory file: %s", path.name)
        except ValueError:
            continue


def should_cleanup_today(project_path: Path) -> bool:
    """Return True if cleanup has not yet run today.

    Tracks the last cleanup date in .terrarium/last_cleanup_date so that
    cleanup runs at most once per calendar day instead of every heartbeat.
    """
    marker = project_path / ".terrarium" / "last_cleanup_date"
    today = datetime.now().date().isoformat()
    if marker.exists() and marker.read_text().strip() == today:
        return False
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(today)
    return True


def build_user_message(
    project_path: Path,
    config: TerrariumConfig,
    base_message: str,
) -> str:
    """Assemble a user message with recent + long-term memory appended.

    Used by both the heartbeat loop and the ``ask`` CLI command so that
    memory injection logic lives in exactly one place.
    """
    parts: list[str] = [base_message]

    recent = load_recent_memory(project_path, config.heartbeat.short_term_days)
    if recent:
        parts.append(recent)

    long_term = load_long_term_memory(project_path)
    if long_term:
        parts.append(long_term)

    return "\n\n".join(parts)
