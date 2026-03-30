"""Agent tools — the six actions Terrarium can take."""

import subprocess
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

from langchain.tools import tool

from src.core.config import TerrariumConfig

# Injected at agent creation time
_project_path: Optional[Path] = None
_config: Optional[TerrariumConfig] = None

MAX_OUTPUT_CHARS = 8000


def init_tools(project_path: Path, config: TerrariumConfig) -> None:
    """Set the project context used by all tools."""
    global _project_path, _config
    _project_path = project_path
    _config = config


def _resolve(path: str) -> Path:
    if _project_path is None:
        raise RuntimeError("Tools not initialized — call init_tools() first")
    return _project_path / path


def _glob_match(path: str, pattern: str) -> bool:
    """Match path against a glob pattern (supports **)."""
    if "**" in pattern:
        parts = pattern.split("**")
        prefix = parts[0].rstrip("/")
        suffix = parts[-1].lstrip("/")
        prefix_ok = not prefix or path.startswith(prefix + "/") or path == prefix
        if suffix:
            return prefix_ok and fnmatch(path.rsplit("/", 1)[-1], suffix)
        return prefix_ok
    return fnmatch(path, pattern)


def _check_writable(file_path: str) -> Optional[str]:
    """Return an error string if the file is not writable, else None."""
    if _config is None:
        return None
    for pattern in _config.boundaries.readonly:
        if _glob_match(file_path, pattern):
            return f"'{file_path}' is readonly (matches boundary rule '{pattern}')"
    if _config.boundaries.writable:
        if not any(_glob_match(file_path, p) for p in _config.boundaries.writable):
            return f"'{file_path}' is outside writable paths: {_config.boundaries.writable}"
    return None


@tool
def read_file(path: str) -> str:
    """Read the contents of a file. Path is relative to the project root."""
    full = _resolve(path)
    if not full.exists():
        return f"File not found: {path}"
    try:
        content = full.read_text()
        if len(content) > MAX_OUTPUT_CHARS:
            return content[:MAX_OUTPUT_CHARS] + f"\n... [truncated, {len(content)} total chars]"
        return content
    except Exception as e:
        return f"Error reading {path}: {e}"


@tool
def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Replace old_string with new_string in a file.

    The old_string must appear exactly once. Path is relative to project root.
    """
    err = _check_writable(path)
    if err:
        return f"Boundary error: {err}"

    full = _resolve(path)
    if not full.exists():
        return f"File not found: {path}"

    content = full.read_text()
    count = content.count(old_string)
    if count == 0:
        return "old_string not found in file"
    if count > 1:
        return f"old_string appears {count} times — must be unique"

    full.write_text(content.replace(old_string, new_string, 1))
    return f"Edited {path}"


@tool
def create_file(path: str, content: str) -> str:
    """Create a new file with the given content.

    Fails if the file already exists. Path is relative to project root.
    """
    err = _check_writable(path)
    if err:
        return f"Boundary error: {err}"

    full = _resolve(path)
    if full.exists():
        return f"File already exists: {path}"

    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)
    return f"Created {path}"


@tool
def read_skill(name: str) -> str:
    """Load the full guide for a skill by name.

    Use this to retrieve detailed instructions before applying a skill.
    Available skill names are listed in your system prompt.
    """
    from src.core.agent import get_skill_content, get_skill_names

    content = get_skill_content(name)
    if content is None:
        available = ", ".join(get_skill_names())
        return f"Skill not found: '{name}'. Available skills: {available}"
    return content


@tool
def list_files(path: str = ".", pattern: str = "*") -> str:
    """List files in a directory. Path is relative to the project root.

    Returns one file path per line, relative to the given path.
    Optionally filter by glob pattern (e.g. "*.py"). Searches recursively.
    """
    full = _resolve(path)
    if not full.exists():
        return f"Directory does not exist: {path}"
    if not full.is_dir():
        return f"Not a directory: {path}"
    files = sorted(
        str(p.relative_to(full))
        for p in full.rglob(pattern)
        if p.is_file() and "__pycache__" not in p.parts
    )
    if not files:
        return "(no files found)"
    result = "\n".join(files)
    if len(result) > MAX_OUTPUT_CHARS:
        result = result[:MAX_OUTPUT_CHARS] + "\n... [truncated]"
    return result


@tool
def run_command(command: str) -> str:
    """Run a shell command in the project root. Returns combined stdout+stderr."""
    if _project_path is None:
        raise RuntimeError("Tools not initialized — call init_tools() first")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(_project_path),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + "\n... [truncated]"
        exit_info = f"\n[exit code: {result.returncode}]"
        return (output or "(no output)") + exit_info
    except subprocess.TimeoutExpired:
        return "Command timed out (120s)"
    except Exception as e:
        return f"Error running command: {e}"


@tool
def memory_log(entry: str) -> str:
    """Append a short-term memory entry to today's daily log.

    Writes to .terrarium/memory/memory-YYYY-MM-DD.md.
    Use this to record observations, actions taken, and results for each heartbeat.
    """
    if _project_path is None:
        raise RuntimeError("Tools not initialized — call init_tools() first")
    memory_dir = _project_path / ".terrarium" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = memory_dir / f"memory-{today}.md"
    is_new = not log_path.exists() or log_path.stat().st_size == 0
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"- **{timestamp}** — {entry}\n"
    with open(log_path, "a") as f:
        if is_new:
            f.write(f"# {today}\n\n")
        f.write(line)
    return "Logged to short-term memory."


@tool
def memory_learn(content: str) -> str:
    """Save a long-term learning to MEMORY.md.

    Use this when you identify a persistent pattern, rule, or lesson
    that should guide future behavior across all heartbeats.
    Keep entries concise and actionable.
    """
    if _project_path is None:
        raise RuntimeError("Tools not initialized — call init_tools() first")
    memory_dir = _project_path / ".terrarium" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    mem_path = memory_dir / "MEMORY.md"
    is_new = not mem_path.exists() or mem_path.stat().st_size == 0
    timestamp = datetime.now().strftime("%Y-%m-%d")
    line = f"- [{timestamp}] {content}\n"
    with open(mem_path, "a") as f:
        if is_new:
            f.write("# Long-Term Memory\n\n")
        f.write(line)
    return "Saved to long-term memory."


ALL_TOOLS = [read_file, read_skill, list_files, edit_file, create_file, run_command, memory_log, memory_learn]
