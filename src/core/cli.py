"""Terrarium CLI commands."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.core.config import load_config
from src.core.skill_loader import SkillLoader
from src.models.state import ProjectState, FileStats
from src.utils.git import get_git_status

app = typer.Typer(
    name="terrarium",
    help="A self-iterating project framework",
)
console = Console()


def get_project_path() -> Path:
    """Get the current project path."""
    return Path.cwd()


@app.command()
def init():
    """Initialize Terrarium in the current project."""
    project_path = get_project_path()
    terrarium_dir = project_path / ".terrarium"
    
    if terrarium_dir.exists():
        console.print("[yellow]Terrarium already initialized.[/yellow]")
        return
    
    # Create directory structure
    terrarium_dir.mkdir(parents=True)
    (terrarium_dir / "memory").mkdir()
    (terrarium_dir / "logs").mkdir()
    
    # Create default config
    config_content = '''version: "0.1"

# 项目信息
project:
  type: python
  name: "My Project"

# 心跳配置
heartbeat:
  quick_interval: "10m"
  standard_interval: "30m"
  deep_interval: "6h"
  enabled: false

# 启用的 Skills
skills:
  - perception
  - memory

# LLM 配置
llm:
  provider: "openai"
  model: "gpt-4o"
  temperature: 0.3
  api_key: "${OPENAI_API_KEY}"

# 感知配置
perception:
  include_patterns:
    - "**/*.py"
    - "**/*.md"
  exclude_patterns:
    - ".git/**"
    - "__pycache__/**"
    - ".terrarium/**"
  commands:
    test: "pytest"
    lint: "ruff check ."

# 边界规则
boundaries:
  files:
    readonly:
      - "pyproject.toml"
      - "LICENSE"
    writable:
      - "src/**/*.py"
      - "tests/**/*.py"
  actions:
    allowed:
      - "edit_file"
      - "create_file"
      - "run_tests"
    forbidden:
      - "delete_file"
      - "git_push"
  changes:
    max_lines_per_change: 100
    require_approval:
      - "changes > 50 lines"
'''
    (terrarium_dir / "config.yaml").write_text(config_content)
    
    # Create identity template
    identity_content = """# Project Identity

## 我是谁
描述这个项目是什么...

## 核心价值
- 价值 1
- 价值 2

## 风格约定
- 约定 1
- 约定 2
"""
    (terrarium_dir / "identity.md").write_text(identity_content)
    
    console.print("[green]Terrarium initialized successfully![/green]")
    console.print(f"Config file: {terrarium_dir / 'config.yaml'}")


@app.command()
def observe():
    """Observe the current project state."""
    project_path = get_project_path()
    config = load_config(project_path)
    
    console.print("[blue]Observing project state...[/blue]")
    
    # Get Git status
    git_status = get_git_status(project_path)
    
    # Scan files (simplified)
    from src.skills.perception.scripts.scan_files import scan_files
    file_stats = scan_files(
        str(project_path),
        config.perception.include_patterns,
        config.perception.exclude_patterns,
    )
    
    # Build state
    state = ProjectState(
        files=FileStats(**file_stats),
        git=git_status,
    )
    
    # Display results
    table = Table(title="Project State")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Files", str(state.files.total))
    table.add_row("Git Branch", state.git.branch)
    table.add_row("Uncommitted Changes", str(state.git.uncommitted_changes))
    
    if state.files.by_extension:
        ext_str = ", ".join(f"{k}: {v}" for k, v in state.files.by_extension.items())
        table.add_row("File Types", ext_str)
    
    console.print(table)
    
    # Save to memory
    from src.skills.memory.scripts.save_observation import save_observation
    obs_id = save_observation(
        str(project_path),
        state.model_dump_json(),
        trigger="manual",
    )
    console.print(f"[dim]Observation saved (id: {obs_id})[/dim]")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show"),
):
    """Show observation history."""
    project_path = get_project_path()
    
    from src.skills.memory.scripts.query_history import query_history
    records = query_history(str(project_path), limit=limit)
    
    if not records:
        console.print("[yellow]No observation history found.[/yellow]")
        return
    
    table = Table(title="Observation History")
    table.add_column("ID", style="cyan")
    table.add_column("Timestamp", style="green")
    table.add_column("Trigger", style="yellow")
    table.add_column("Files", style="blue")
    
    for record in records:
        files = record["state"].get("files", {}).get("total", "?")
        table.add_row(
            str(record["id"]),
            record["timestamp"][:19],
            record["trigger"],
            str(files),
        )
    
    console.print(table)


@app.command()
def status():
    """Show Terrarium status."""
    project_path = get_project_path()
    terrarium_dir = project_path / ".terrarium"
    
    if not terrarium_dir.exists():
        console.print("[red]Terrarium not initialized. Run 'terrarium init' first.[/red]")
        return
    
    config = load_config(project_path)
    
    console.print("[bold]Terrarium Status[/bold]")
    console.print(f"  Project: {project_path.name}")
    console.print(f"  Type: {config.project.type}")
    console.print(f"  Heartbeat: {'enabled' if config.heartbeat.enabled else 'disabled'}")
    console.print(f"  Skills: {', '.join(config.skills)}")


@app.command()
def watch(
    interval: str = typer.Option("30m", "--interval", "-i", help="Observation interval (e.g., 10m, 1h)"),
):
    """Start heartbeat observation loop."""
    project_path = get_project_path()
    terrarium_dir = project_path / ".terrarium"
    
    if not terrarium_dir.exists():
        console.print("[red]Terrarium not initialized. Run 'terrarium init' first.[/red]")
        raise typer.Exit(1)
    
    from src.core.heartbeat import start_heartbeat
    start_heartbeat(project_path, interval)


@app.command()
def ask(
    message: str = typer.Argument(..., help="Message to send to the agent"),
):
    """Ask the Terrarium agent a question."""
    project_path = get_project_path()
    terrarium_dir = project_path / ".terrarium"
    
    if not terrarium_dir.exists():
        console.print("[red]Terrarium not initialized. Run 'terrarium init' first.[/red]")
        raise typer.Exit(1)
    
    config = load_config(project_path)
    
    console.print("[blue]Initializing agent...[/blue]")
    
    from src.core.agent import create_terrarium_agent, invoke_agent
    
    try:
        agent = create_terrarium_agent(config, project_path)
        console.print(f"[dim]Loaded {len(agent['skills'])} skills[/dim]")
        
        console.print("[blue]Thinking...[/blue]")
        response = invoke_agent(agent, message)
        
        console.print("\n[bold green]Agent Response:[/bold green]")
        console.print(response)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
