"""Terrarium CLI."""

import concurrent.futures
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from src.core.config import load_config

app = typer.Typer(name="terrarium", help="A self-iterating project framework")
console = Console()

DEFAULT_CONFIG = """\
version: "0.1"

project:
  name: "My Project"

llm:
  provider: openai
  model: gpt-4o
  temperature: 0.3
  api_key: "${OPENAI_API_KEY}"

heartbeat:
  interval: "30m"

boundaries:
  readonly:
    - "pyproject.toml"
    - "LICENSE"
  writable:
    - "src/**"
    - "tests/**"

drives:
  - name: stability
    description: "所有测试必须通过"
  - name: consistency
    description: "代码风格保持统一"
  - name: completeness
    description: "TODO 和 FIXME 应持续减少"
"""

DEFAULT_IDENTITY = """\
# Project Identity

Describe what this project is, what it aims to become, and what values it holds.

## What I Am
A Python project managed by Terrarium.

## What I Value
- Clean, well-tested code
- Clear and consistent structure
- Continuous improvement
"""


GIT_HOOK_SCRIPT = """\
#!/bin/sh
# Installed by Terrarium — triggers a lightweight agent check after each commit.
# Remove this file to disable, or run: terrarium uninstall-hook
terrarium ask "A new commit was just made. Quickly check if anything needs immediate attention." &
"""


ProjectPath = Annotated[
    Path | None,
    typer.Option(
        "--project-path",
        "-p",
        help="Path to the project root (defaults to current directory)",
    ),
]


def _get_project_path(project_path: Path | None = None) -> Path:
    if project_path is not None:
        return project_path.resolve()
    return Path.cwd()


def _install_git_hook(project_path: Path) -> bool:
    """Install post-commit hook. Returns True if installed, False if skipped."""
    git_dir = project_path / ".git"
    if not git_dir.is_dir():
        return False
    hook_path = git_dir / "hooks" / "post-commit"
    if hook_path.exists():
        return False
    hook_path.parent.mkdir(exist_ok=True)
    hook_path.write_text(GIT_HOOK_SCRIPT)
    hook_path.chmod(0o755)
    return True


def _require_init(project_path: Path) -> None:
    if not (project_path / ".terrarium").exists():
        console.print("[red]Not initialized. Run 'terrarium init' first.[/red]")
        raise typer.Exit(1)


def _invoke_agent(message: str, project_path: Path) -> None:
    _require_init(project_path)
    config = load_config(project_path)

    from src.core.agent import create_terrarium_agent
    from src.core.memory import build_user_message

    full_message = build_user_message(project_path, config, message)

    try:
        agent = create_terrarium_agent(config, project_path)
        result = agent.invoke({"messages": [{"role": "user", "content": full_message}]})
        response = result["messages"][-1].content
        console.print()
        console.print(Markdown(response))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _run_check(label: str, cmd: str, cwd: str) -> tuple[str, bool, str]:
    """Run a single check command, return (label, ok, summary)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        ok = result.returncode == 0
        output = (result.stdout + result.stderr).strip()
        short = output.splitlines()[-1] if output else ""
        return (label, ok, short)
    except subprocess.TimeoutExpired:
        return (label, False, "TIMEOUT")


@app.command()
def init(project_path: ProjectPath = None) -> None:
    """Initialize Terrarium in the current project."""
    project_path = _get_project_path(project_path)
    terrarium_dir = project_path / ".terrarium"

    if terrarium_dir.exists():
        console.print("[yellow]Already initialized.[/yellow]")
        return

    terrarium_dir.mkdir(parents=True)
    (terrarium_dir / "config.yaml").write_text(DEFAULT_CONFIG)
    (terrarium_dir / "identity.md").write_text(DEFAULT_IDENTITY)

    memory_dir = terrarium_dir / "memory"
    memory_dir.mkdir()
    (memory_dir / "MEMORY.md").write_text("# Long-Term Memory\n\n")

    console.print("[green]Terrarium initialized.[/green]")
    console.print(f"  Config:   {terrarium_dir / 'config.yaml'}")
    console.print(f"  Identity: {terrarium_dir / 'identity.md'}")
    console.print(f"  Memory:   {memory_dir / 'MEMORY.md'}")

    hook_installed = _install_git_hook(project_path)
    if hook_installed:
        console.print("  Git hook: [green]post-commit hook installed[/green]")
    else:
        console.print(
            "  Git hook: [dim]skipped (not a git repo or hook already exists)[/dim]"
        )

    console.print("\nEdit the config, then run [bold]terrarium start[/bold].")


@app.command()
def start(project_path: ProjectPath = None) -> None:
    """Start the heartbeat loop — agent runs autonomously on each tick."""
    project_path = _get_project_path(project_path)
    _require_init(project_path)
    config = load_config(project_path)

    from src.core.heartbeat import start_heartbeat

    start_heartbeat(project_path, config)


@app.command()
def ask(
    message: str = typer.Argument(..., help="Message to send to the agent"),
    project_path: ProjectPath = None,
) -> None:
    """Send a one-off message to the agent."""
    _invoke_agent(message, _get_project_path(project_path))


@app.command()
def pause(project_path: ProjectPath = None) -> None:
    """Pause the heartbeat loop without stopping the process."""
    project_path = _get_project_path(project_path)
    _require_init(project_path)
    marker = project_path / ".terrarium" / "paused"
    if marker.exists():
        console.print("[yellow]Already paused.[/yellow]")
        return
    marker.touch()
    console.print(
        "[yellow]Heartbeat paused.[/yellow] Run [bold]terrarium resume[/bold] to continue."
    )


@app.command()
def resume(project_path: ProjectPath = None) -> None:
    """Resume a paused heartbeat loop."""
    project_path = _get_project_path(project_path)
    _require_init(project_path)
    marker = project_path / ".terrarium" / "paused"
    if not marker.exists():
        console.print("[yellow]Not currently paused.[/yellow]")
        return
    marker.unlink()
    console.print("[green]Heartbeat resumed.[/green]")


@app.command()
def status(project_path: ProjectPath = None) -> None:
    """Show a quick health snapshot of the project (no LLM call)."""
    project_path = _get_project_path(project_path)
    _require_init(project_path)

    console.print("\n[bold]Terrarium Status[/bold]\n")

    paused_marker = project_path / ".terrarium" / "paused"
    heartbeat_state = (
        "[yellow]paused[/yellow]" if paused_marker.exists() else "[green]active[/green]"
    )
    console.print(f"  Heartbeat : {heartbeat_state}")

    last_hb = project_path / ".terrarium" / "last_heartbeat"
    if last_hb.exists():
        console.print(f"  Last beat : {last_hb.read_text().strip()}")

    checks = [
        ("Tests", "pytest --tb=no -q"),
        ("Lint", "ruff check . --quiet"),
        ("Format", "ruff format --check . --quiet"),
    ]

    cwd = str(project_path)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(_run_check, label, cmd, cwd) for label, cmd in checks
        ]
        results = [f.result() for f in futures]

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Check", style="dim", width=10)
    table.add_column("Result")
    table.add_column("Output", overflow="fold")

    for label, ok, short in results:
        if short == "TIMEOUT":
            table.add_row(label, "[yellow]TIMEOUT[/yellow]", "")
        else:
            status_text = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
            table.add_row(label, status_text, short)

    console.print()
    console.print(table)

    mem_file = project_path / ".terrarium" / "memory" / "MEMORY.md"
    if mem_file.exists():
        lines = [
            line for line in mem_file.read_text().splitlines() if line.startswith("- ")
        ]
        console.print(f"\n  Long-term memory: {len(lines)} entries")

    console.print()


@app.command("config")
def show_config(project_path: ProjectPath = None) -> None:
    """Show the current Terrarium configuration."""
    project_path = _get_project_path(project_path)
    _require_init(project_path)

    config_path = project_path / ".terrarium" / "config.yaml"
    if not config_path.exists():
        console.print("[yellow]No config.yaml found (using defaults).[/yellow]")

    config = load_config(project_path)

    console.print("\n[bold]Terrarium Configuration[/bold]\n")
    console.print(f"  Version   : {config.version}")
    console.print(f"  Project   : {config.project.name}")
    console.print(f"  Provider  : {config.llm.provider}")
    console.print(f"  Model     : {config.llm.model}")
    console.print(f"  Interval  : {config.heartbeat.interval}")
    console.print(f"  Readonly  : {', '.join(config.boundaries.readonly)}")
    console.print(f"  Writable  : {', '.join(config.boundaries.writable)}")
    if config.drives:
        console.print("  Drives    :")
        for d in config.drives:
            console.print(f"    - {d.name}: {d.description}")
    console.print()


@app.command("install-hook")
def install_hook(project_path: ProjectPath = None) -> None:
    """Install the post-commit git hook for event-triggered agent checks."""
    project_path = _get_project_path(project_path)
    _require_init(project_path)
    git_dir = project_path / ".git"
    if not git_dir.is_dir():
        console.print("[red]Not a git repository.[/red]")
        raise typer.Exit(1)
    hook_path = git_dir / "hooks" / "post-commit"
    if hook_path.exists():
        console.print(
            "[yellow]post-commit hook already exists. Remove it first to reinstall.[/yellow]"
        )
        return
    hook_path.parent.mkdir(exist_ok=True)
    hook_path.write_text(GIT_HOOK_SCRIPT)
    hook_path.chmod(0o755)
    console.print("[green]post-commit hook installed.[/green]")
    console.print("  Agent will be triggered after every git commit.")


@app.command("uninstall-hook")
def uninstall_hook(project_path: ProjectPath = None) -> None:
    """Remove the Terrarium post-commit git hook."""
    project_path = _get_project_path(project_path)
    hook_path = project_path / ".git" / "hooks" / "post-commit"
    if not hook_path.exists():
        console.print("[yellow]No post-commit hook found.[/yellow]")
        return
    if "Installed by Terrarium" not in hook_path.read_text():
        console.print(
            "[red]Hook exists but was not installed by Terrarium. Aborting.[/red]"
        )
        raise typer.Exit(1)
    hook_path.unlink()
    console.print("[green]post-commit hook removed.[/green]")


if __name__ == "__main__":
    app()
