"""Heartbeat scheduling for periodic observations."""

import signal
import sys
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from rich.console import Console

from src.core.config import load_config

console = Console()


def parse_interval(interval_str: str) -> int:
    """Parse interval string to seconds."""
    if interval_str.endswith("m"):
        return int(interval_str[:-1]) * 60
    elif interval_str.endswith("h"):
        return int(interval_str[:-1]) * 3600
    elif interval_str.endswith("s"):
        return int(interval_str[:-1])
    else:
        return int(interval_str)


def run_observation(project_path: Path, interval_type: str):
    """Run a single observation."""
    console.print(f"[dim]{datetime.now().isoformat()} [{interval_type}] Running observation...[/dim]")
    
    try:
        # Import here to avoid circular imports
        from src.models.state import ProjectState, FileStats
        from src.utils.git import get_git_status
        from src.skills.perception.scripts.scan_files import scan_files
        from src.skills.memory.scripts.save_observation import save_observation
        
        config = load_config(project_path)
        
        git_status = get_git_status(project_path)
        file_stats = scan_files(
            str(project_path),
            config.perception.include_patterns,
            config.perception.exclude_patterns,
        )
        
        state = ProjectState(
            files=FileStats(**file_stats),
            git=git_status,
        )
        
        obs_id = save_observation(
            str(project_path),
            state.model_dump_json(),
            trigger=f"heartbeat_{interval_type}",
        )
        
        console.print(f"[green]Observation complete (id: {obs_id})[/green]")
        
    except Exception as e:
        console.print(f"[red]Observation failed: {e}[/red]")


def start_heartbeat(project_path: Path, interval: str = None):
    """Start the heartbeat scheduler."""
    config = load_config(project_path)
    
    if interval:
        seconds = parse_interval(interval)
    else:
        seconds = parse_interval(config.heartbeat.standard_interval)
    
    console.print(f"[blue]Starting heartbeat (interval: {seconds}s)...[/blue]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    
    scheduler = BlockingScheduler()
    
    # Add job
    scheduler.add_job(
        run_observation,
        trigger=IntervalTrigger(seconds=seconds),
        args=[project_path, "standard"],
        id="heartbeat",
        next_run_time=datetime.now(),  # Run immediately
    )
    
    # Handle graceful shutdown
    def shutdown(signum, frame):
        console.print("\n[yellow]Stopping heartbeat...[/yellow]")
        scheduler.shutdown(wait=False)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
