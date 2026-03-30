"""Heartbeat — periodic agent wake-up loop."""

import logging
import signal
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from rich.console import Console

from src.core.config import TerrariumConfig, parse_interval
from src.core.memory import build_user_message, cleanup_old_memory, should_cleanup_today

console = Console()
logger = logging.getLogger("terrarium.heartbeat")

HEARTBEAT_OK = "HEARTBEAT_OK"

BACKOFF_BASE_SECONDS = 2
BACKOFF_MAX_SECONDS = 300


def is_paused(project_path: Path) -> bool:
    """Return True if a .terrarium/paused marker file exists."""
    return (project_path / ".terrarium" / "paused").exists()


def _is_ok(response: str) -> bool:
    stripped = response.strip()
    return stripped == HEARTBEAT_OK or stripped.endswith(HEARTBEAT_OK)


def _setup_file_logging(project_path: Path) -> None:
    """Configure file-based logging under .terrarium/logs/."""
    root = logging.getLogger("terrarium")
    if any(isinstance(h, logging.FileHandler) for h in root.handlers):
        return
    log_dir = project_path / ".terrarium" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / "heartbeat.log")
    handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def _record_heartbeat_time(project_path: Path) -> None:
    """Write the current timestamp to .terrarium/last_heartbeat for status display."""
    marker = project_path / ".terrarium" / "last_heartbeat"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(datetime.now().isoformat())


def build_heartbeat_prompt(
    project_path: Path,
    config: TerrariumConfig,
    timestamp: str,
) -> str:
    """Build the per-heartbeat user message with dynamic memory.

    Delegates memory assembly to ``build_user_message`` so that the
    heartbeat loop and CLI ``ask`` share the same injection logic.
    """
    base = (
        f"Heartbeat at {timestamp}.\n"
        "Perceive the current project state, identify what needs improvement or attention, "
        "and take action if warranted.\n"
        "If everything is fine and nothing needs doing, reply with: HEARTBEAT_OK"
    )
    return build_user_message(project_path, config, base)


def start_heartbeat(project_path: Path, config: TerrariumConfig) -> None:
    """Start the heartbeat loop. Runs until Ctrl+C or SIGTERM."""
    from src.core.agent import create_model, create_terrarium_agent

    _setup_file_logging(project_path)

    try:
        interval_seconds = parse_interval(config.heartbeat.interval)
    except ValueError as e:
        console.print(f"[red]Config error: {e}[/red]")
        sys.exit(1)

    console.print(
        f"[blue]Heartbeat started — interval: {config.heartbeat.interval}[/blue]"
    )
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    logger.info(
        "Heartbeat started — interval: %s (%ds)",
        config.heartbeat.interval,
        interval_seconds,
    )

    model = create_model(config)
    agent = create_terrarium_agent(config, project_path, model=model)

    max_errors = config.heartbeat.max_consecutive_errors
    consecutive_errors = 0
    shutdown_requested = False

    def shutdown(signum, _frame):
        nonlocal shutdown_requested
        shutdown_requested = True
        console.print("\n[yellow]Stopping heartbeat...[/yellow]")
        logger.info("Heartbeat stopped by signal %s", signum)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while not shutdown_requested:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if is_paused(project_path):
            console.print(
                f"[dim]{timestamp}  PAUSED — run 'terrarium resume' to continue[/dim]"
            )
            time.sleep(interval_seconds)
            continue

        if should_cleanup_today(project_path):
            cleanup_old_memory(project_path, config.heartbeat.short_term_days)

        prompt = build_heartbeat_prompt(project_path, config, timestamp)

        try:
            result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
            response = result["messages"][-1].content
            consecutive_errors = 0

            _record_heartbeat_time(project_path)

            if _is_ok(response):
                console.print(f"[dim]{timestamp}  HEARTBEAT_OK[/dim]")
                logger.info("HEARTBEAT_OK")
            else:
                console.print(f"\n[green]{timestamp}[/green]")
                console.print(response)
                console.print()
                logger.info("Agent acted: %s", response[:200])

        except Exception as e:
            consecutive_errors += 1
            console.print(
                f"[red]{timestamp}  Error ({consecutive_errors}/{max_errors}): {e}[/red]"
            )
            logger.error("Heartbeat error: %s\n%s", e, traceback.format_exc())

            if consecutive_errors >= max_errors:
                (project_path / ".terrarium" / "paused").touch()
                console.print(
                    f"[red bold]Auto-paused after {max_errors} consecutive errors.[/red bold]\n"
                    "Fix the issue, then run [bold]terrarium resume[/bold]."
                )
                logger.error("Auto-paused after %d consecutive errors", max_errors)
                break

            backoff = min(BACKOFF_BASE_SECONDS**consecutive_errors, BACKOFF_MAX_SECONDS)
            logger.warning("Backing off %ds before next attempt", backoff)
            time.sleep(backoff)

        time.sleep(interval_seconds)
