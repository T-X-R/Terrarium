"""Agent tools — the actions Terrarium can take."""

import os
import re
import subprocess
import tempfile
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

from langchain_core.tools import tool

from src.core.config import TerrariumConfig


MAX_OUTPUT_CHARS = 8000

BLOCKED_COMMANDS: list[re.Pattern] = [
    re.compile(r"\brm\s+(-\w*\s+)*-\w*r\w*\s", re.IGNORECASE),
    re.compile(r"\bgit\s+(push|commit|rebase|merge|reset)\b", re.IGNORECASE),
    re.compile(r"\bgit\s+checkout\s+(-b\s+)?\S", re.IGNORECASE),
    re.compile(r"\bcurl\b.*\|\s*(ba)?sh", re.IGNORECASE),
    re.compile(r"\bsudo\b", re.IGNORECASE),
]

ALLOWED_COMMAND_PREFIXES: tuple[str, ...] = (
    "pytest",
    "python -m pytest",
    "ruff",
    "python -m ruff",
    "git status",
    "git log",
    "git diff",
    "git show",
    "git branch",
    "git ls-files",
    "echo",
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "find",
    "grep",
    "rg",
    "python -c",
)

_HIDDEN_DIRS = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "node_modules",
        ".ruff_cache",
        ".pytest_cache",
    }
)


def _resolve(path: str, project_path: Path) -> Path:
    """Resolve a relative path within the project root, blocking traversal escapes."""
    resolved = (project_path / path).resolve()
    project_root = project_path.resolve()
    if not resolved.is_relative_to(project_root):
        raise ValueError(f"Path '{path}' escapes the project root")
    return resolved


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


def _check_writable(file_path: str, config: TerrariumConfig | None) -> str | None:
    """Return an error string if the file is not writable, else None."""
    if config is None:
        return None
    for pattern in config.boundaries.readonly:
        if _glob_match(file_path, pattern):
            return f"'{file_path}' is readonly (matches boundary rule '{pattern}')"
    if config.boundaries.writable:
        if not any(_glob_match(file_path, p) for p in config.boundaries.writable):
            return (
                f"'{file_path}' is outside writable paths: {config.boundaries.writable}"
            )
    return None


def _check_command_blocked(command: str) -> str | None:
    """Return an error string if the command matches a blocked pattern, else None."""
    for pattern in BLOCKED_COMMANDS:
        if pattern.search(command):
            return f"Blocked: '{command}' matches safety rule. This command is not allowed."
    return None


def _check_command_allowed(command: str) -> str | None:
    """Return an error string if the command is not in the allowed-prefix whitelist."""
    cmd = command.strip()
    if any(cmd.startswith(prefix) for prefix in ALLOWED_COMMAND_PREFIXES):
        return None
    return (
        f"Command not in allowed list. "
        f"Allowed prefixes: {', '.join(ALLOWED_COMMAND_PREFIXES)}"
    )


def _atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write *content* to *path* atomically via temp file + rename.

    Ensures partial writes never leave a corrupted file on disk.
    """
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def create_tools(project_path: Path, config: TerrariumConfig) -> list:
    """Create all agent tools bound to the given project context.

    Each invocation returns fresh tool instances that capture *project_path*
    and *config* via closure — no global mutable state involved.
    """

    @tool
    def read_file(path: str) -> str:
        """Read the contents of a file. Path is relative to the project root."""
        try:
            full = _resolve(path, project_path)
        except ValueError as e:
            return f"Boundary error: {e}"
        if not full.exists():
            return f"File not found: {path}"
        try:
            content = full.read_text(encoding="utf-8")
            if len(content) > MAX_OUTPUT_CHARS:
                return (
                    content[:MAX_OUTPUT_CHARS]
                    + f"\n... [truncated, {len(content)} total chars]"
                )
            return content
        except Exception as e:
            return f"Error reading {path}: {e}"

    @tool
    def edit_file(path: str, old_string: str, new_string: str) -> str:
        """Replace old_string with new_string in a file.

        The old_string must appear exactly once. Path is relative to project root.
        """
        err = _check_writable(path, config)
        if err:
            return f"Boundary error: {err}"
        try:
            full = _resolve(path, project_path)
        except ValueError as e:
            return f"Boundary error: {e}"
        if not full.exists():
            return f"File not found: {path}"

        content = full.read_text(encoding="utf-8")
        count = content.count(old_string)
        if count == 0:
            return "old_string not found in file"
        if count > 1:
            return f"old_string appears {count} times — must be unique"

        _atomic_write(full, content.replace(old_string, new_string, 1))
        return f"Edited {path}"

    @tool
    def create_file(path: str, content: str) -> str:
        """Create a new file with the given content.

        Fails if the file already exists. Path is relative to project root.
        """
        err = _check_writable(path, config)
        if err:
            return f"Boundary error: {err}"
        try:
            full = _resolve(path, project_path)
        except ValueError as e:
            return f"Boundary error: {e}"
        if full.exists():
            return f"File already exists: {path}"

        full.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(full, content)
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
        try:
            full = _resolve(path, project_path)
        except ValueError as e:
            return f"Boundary error: {e}"
        if not full.exists():
            return f"Directory does not exist: {path}"
        if not full.is_dir():
            return f"Not a directory: {path}"
        files = sorted(
            str(p.relative_to(full))
            for p in full.rglob(pattern)
            if p.is_file() and not any(part in _HIDDEN_DIRS for part in p.parts)
        )
        if not files:
            return "(no files found)"
        result = "\n".join(files)
        if len(result) > MAX_OUTPUT_CHARS:
            result = result[:MAX_OUTPUT_CHARS] + "\n... [truncated]"
        return result

    @tool
    def run_command(command: str) -> str:
        """Run a shell command in the project root. Returns combined stdout+stderr.

        Only commands matching the allowed-prefix whitelist are accepted.
        Allowed prefixes include: pytest, ruff, git status/log/diff/show/branch,
        echo, ls, cat, head, tail, wc, find, grep, rg, python -c.
        """
        blocked = _check_command_blocked(command)
        if blocked:
            return blocked
        allowed = _check_command_allowed(command)
        if allowed:
            return allowed
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(project_path),
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
        memory_dir = project_path / ".terrarium" / "memory"
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
        memory_dir = project_path / ".terrarium" / "memory"
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

    return [
        read_file,
        read_skill,
        list_files,
        edit_file,
        create_file,
        run_command,
        memory_log,
        memory_learn,
    ]
