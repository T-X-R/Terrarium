"""Tests for agent tools."""

from datetime import datetime
from pathlib import Path

from src.core.config import TerrariumConfig
from src.core.tools import (
    _glob_match,
    init_tools, read_file, read_skill, edit_file, create_file,
    run_command, list_files, memory_log, memory_learn,
)


def setup_tools(project_path: Path) -> None:
    config = TerrariumConfig()
    init_tools(project_path, config)


def test_read_file_existing(tmp_path):
    (tmp_path / "hello.txt").write_text("hello world")
    setup_tools(tmp_path)
    result = read_file.invoke({"path": "hello.txt"})
    assert result == "hello world"


def test_read_file_missing(tmp_path):
    setup_tools(tmp_path)
    result = read_file.invoke({"path": "nonexistent.txt"})
    assert "not found" in result


def test_edit_file_success(tmp_path):
    f = tmp_path / "src" / "main.py"
    f.parent.mkdir()
    f.write_text("def foo():\n    pass\n")
    setup_tools(tmp_path)
    result = edit_file.invoke({"path": "src/main.py", "old_string": "    pass", "new_string": "    return 42"})
    assert "Edited" in result
    assert (tmp_path / "src" / "main.py").read_text() == "def foo():\n    return 42\n"


def test_edit_file_old_string_not_found(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def foo(): pass")
    setup_tools(tmp_path)
    result = edit_file.invoke({"path": "src/main.py", "old_string": "NOTHERE", "new_string": "x"})
    assert "not found" in result


def test_edit_file_readonly_blocked(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]")
    setup_tools(tmp_path)
    result = edit_file.invoke({"path": "pyproject.toml", "old_string": "[project]", "new_string": "[x]"})
    assert "Boundary error" in result


def test_create_file(tmp_path):
    setup_tools(tmp_path)
    result = create_file.invoke({"path": "src/new.py", "content": "# new file\n"})
    assert "Created" in result
    assert (tmp_path / "src" / "new.py").read_text() == "# new file\n"


def test_create_file_already_exists(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "existing.py").write_text("x = 1")
    setup_tools(tmp_path)
    result = create_file.invoke({"path": "src/existing.py", "content": "y = 2"})
    assert "already exists" in result
    assert (tmp_path / "src" / "existing.py").read_text() == "x = 1"


def test_run_command(tmp_path):
    setup_tools(tmp_path)
    result = run_command.invoke({"command": "echo hello"})
    assert "hello" in result
    assert "[exit code: 0]" in result


def test_run_command_exit_code(tmp_path):
    setup_tools(tmp_path)
    result = run_command.invoke({"command": "exit 1"})
    assert "[exit code: 1]" in result


# --- read_skill ---


def test_read_skill_existing(tmp_path):
    setup_tools(tmp_path)
    result = read_skill.invoke({"name": "perception"})
    assert "感知" in result
    assert "## 感知方式" in result


def test_read_skill_nonexistent(tmp_path):
    setup_tools(tmp_path)
    result = read_skill.invoke({"name": "nonexistent_skill"})
    assert "not found" in result.lower()
    assert "perception" in result


# --- _glob_match ---


class TestGlobMatch:
    def test_double_star_matches_nested(self):
        assert _glob_match("src/core/agent.py", "src/**") is True

    def test_double_star_matches_direct_child(self):
        assert _glob_match("src/main.py", "src/**") is True

    def test_double_star_no_match_outside(self):
        assert _glob_match("docs/readme.md", "src/**") is False

    def test_double_star_with_suffix(self):
        assert _glob_match("src/core/agent.py", "src/**/*.py") is True

    def test_double_star_suffix_no_match(self):
        assert _glob_match("src/core/agent.js", "src/**/*.py") is False

    def test_exact_match(self):
        assert _glob_match("pyproject.toml", "pyproject.toml") is True

    def test_exact_no_match(self):
        assert _glob_match("setup.py", "pyproject.toml") is False

    def test_wildcard_pattern(self):
        assert _glob_match("README.md", "*.md") is True

    def test_tests_double_star(self):
        assert _glob_match("tests/test_config.py", "tests/**") is True

    def test_root_file_not_in_src(self):
        assert _glob_match("README.md", "src/**") is False

    def test_bare_double_star(self):
        assert _glob_match("anything/at/all.py", "**") is True

    def test_double_star_py_suffix(self):
        assert _glob_match("deep/nested/file.py", "**/*.py") is True


# --- list_files ---


def test_list_files(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1")
    (tmp_path / "src" / "util.py").write_text("y = 2")
    (tmp_path / "README.md").write_text("# hi")
    setup_tools(tmp_path)
    result = list_files.invoke({"path": "."})
    assert "src/main.py" in result
    assert "src/util.py" in result
    assert "README.md" in result


def test_list_files_subdirectory(tmp_path):
    (tmp_path / "src" / "core").mkdir(parents=True)
    (tmp_path / "src" / "core" / "a.py").write_text("")
    (tmp_path / "src" / "b.py").write_text("")
    setup_tools(tmp_path)
    result = list_files.invoke({"path": "src/core"})
    assert "a.py" in result
    assert "b.py" not in result


def test_list_files_missing_dir(tmp_path):
    setup_tools(tmp_path)
    result = list_files.invoke({"path": "nonexistent"})
    assert "not found" in result.lower() or "does not exist" in result.lower()


# --- Short-term memory ---


def test_memory_log_creates_daily_file(tmp_path):
    (tmp_path / ".terrarium" / "memory").mkdir(parents=True)
    setup_tools(tmp_path)
    memory_log.invoke({"entry": "observed tests passing"})

    today = datetime.now().strftime("%Y-%m-%d")
    log_path = tmp_path / ".terrarium" / "memory" / f"memory-{today}.md"
    assert log_path.exists()
    content = log_path.read_text()
    assert "observed tests passing" in content
    assert today in content


def test_memory_log_appends(tmp_path):
    (tmp_path / ".terrarium" / "memory").mkdir(parents=True)
    setup_tools(tmp_path)
    memory_log.invoke({"entry": "first"})
    memory_log.invoke({"entry": "second"})

    today = datetime.now().strftime("%Y-%m-%d")
    log_path = tmp_path / ".terrarium" / "memory" / f"memory-{today}.md"
    content = log_path.read_text()
    assert "first" in content
    assert "second" in content


# --- Long-term memory ---


def test_memory_learn_creates_file(tmp_path):
    (tmp_path / ".terrarium" / "memory").mkdir(parents=True)
    setup_tools(tmp_path)
    memory_learn.invoke({"content": "always run tests after edits"})

    mem_path = tmp_path / ".terrarium" / "memory" / "MEMORY.md"
    assert mem_path.exists()
    content = mem_path.read_text()
    assert "always run tests after edits" in content
    assert "Long-Term Memory" in content


def test_memory_learn_appends(tmp_path):
    (tmp_path / ".terrarium" / "memory").mkdir(parents=True)
    setup_tools(tmp_path)
    memory_learn.invoke({"content": "rule one"})
    memory_learn.invoke({"content": "rule two"})

    mem_path = tmp_path / ".terrarium" / "memory" / "MEMORY.md"
    content = mem_path.read_text()
    assert "rule one" in content
    assert "rule two" in content
