"""Terrarium CLI."""

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown

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


def _get_project_path() -> Path:
    return Path.cwd()


def _require_init(project_path: Path) -> None:
    if not (project_path / ".terrarium").exists():
        console.print("[red]Not initialized. Run 'terrarium init' first.[/red]")
        raise typer.Exit(1)


def _invoke_agent(message: str) -> None:
    project_path = _get_project_path()
    _require_init(project_path)
    config = load_config(project_path)

    from src.core.agent import create_terrarium_agent

    try:
        agent = create_terrarium_agent(config, project_path)
        result = agent.invoke({"messages": [{"role": "user", "content": message}]})
        response = result["messages"][-1].content
        console.print()
        console.print(Markdown(response))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def init() -> None:
    """Initialize Terrarium in the current project."""
    project_path = _get_project_path()
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
    console.print("\nEdit the config, then run [bold]terrarium start[/bold].")


@app.command()
def start() -> None:
    """Start the heartbeat loop — agent runs autonomously on each tick."""
    project_path = _get_project_path()
    _require_init(project_path)
    config = load_config(project_path)

    from src.core.heartbeat import start_heartbeat

    start_heartbeat(project_path, config)


@app.command()
def ask(
    message: str = typer.Argument(..., help="Message to send to the agent"),
) -> None:
    """Send a one-off message to the agent."""
    _invoke_agent(message)


if __name__ == "__main__":
    app()
