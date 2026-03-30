"""Heartbeat — periodic agent wake-up loop."""

import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console

from src.core.config import TerrariumConfig

console = Console()

HEARTBEAT_OK = "HEARTBEAT_OK"

SHORT_TERM_DAYS = 3


def _load_recent_memory(project_path: Path) -> str:
    """Read the last SHORT_TERM_DAYS days of memory-YYYY-MM-DD.md files."""
    memory_dir = project_path / ".terrarium" / "memory"
    if not memory_dir.exists():
        return ""
    parts = []
    today = datetime.now().date()
    for offset in range(SHORT_TERM_DAYS):
        day = today - timedelta(days=offset)
        path = memory_dir / f"memory-{day.isoformat()}.md"
        if path.exists():
            content = path.read_text().strip()
            if content:
                parts.append(content)
    if not parts:
        return ""
    return "## Recent Memory (last few days)\n\n" + "\n\n".join(parts)


def parse_interval(interval_str: str) -> int:
    """Parse interval string like '10m', '6h', '30s' to seconds."""
    s = interval_str.strip()
    if s.endswith("m"):
        return int(s[:-1]) * 60
    if s.endswith("h"):
        return int(s[:-1]) * 3600
    if s.endswith("s"):
        return int(s[:-1])
    return int(s)


def _is_ok(response: str) -> bool:
    stripped = response.strip()
    return stripped == HEARTBEAT_OK or stripped.endswith(HEARTBEAT_OK)


def start_heartbeat(project_path: Path, config: TerrariumConfig) -> None:
    """Start the heartbeat loop. Runs until Ctrl+C or SIGTERM."""
    from src.core.agent import create_terrarium_agent

    interval_seconds = parse_interval(config.heartbeat.interval)
    console.print(f"[blue]Heartbeat started — interval: {config.heartbeat.interval}[/blue]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    def shutdown(signum, frame):
        console.print("\n[yellow]Stopping heartbeat...[/yellow]")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        recent_memory = _load_recent_memory(project_path)

        prompt_parts = [
            f"Heartbeat at {timestamp}.",
            "Perceive the current project state, identify what needs improvement or attention, "
            "and take action if warranted.",
            "If everything is fine and nothing needs doing, reply with: HEARTBEAT_OK",
        ]
        if recent_memory:
            prompt_parts.append(recent_memory)
        prompt = "\n\n".join(prompt_parts)

        try:
            agent = create_terrarium_agent(config, project_path)
            result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
            response = result["messages"][-1].content

            if _is_ok(response):
                console.print(f"[dim]{timestamp}  HEARTBEAT_OK[/dim]")
            else:
                console.print(f"\n[green]{timestamp}[/green]")
                console.print(response)
                console.print()

        except Exception as e:
            console.print(f"[red]{timestamp}  Error: {e}[/red]")

        time.sleep(interval_seconds)
