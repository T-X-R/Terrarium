"""Tests for CLI commands (no LLM calls)."""

import os

from typer.testing import CliRunner

from src.core.cli import app

runner = CliRunner()


def test_init_creates_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "initialized" in result.output.lower()
    assert (tmp_path / ".terrarium" / "config.yaml").exists()
    assert (tmp_path / ".terrarium" / "identity.md").exists()
    assert (tmp_path / ".terrarium" / "memory" / "MEMORY.md").exists()


def test_init_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "already" in result.output.lower()


def test_pause_without_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["pause"])
    assert result.exit_code == 1


def test_pause_and_resume(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["pause"])
    assert result.exit_code == 0
    assert "paused" in result.output.lower()
    assert (tmp_path / ".terrarium" / "paused").exists()

    result = runner.invoke(app, ["pause"])
    assert "already" in result.output.lower()

    result = runner.invoke(app, ["resume"])
    assert result.exit_code == 0
    assert "resumed" in result.output.lower()
    assert not (tmp_path / ".terrarium" / "paused").exists()

    result = runner.invoke(app, ["resume"])
    assert "not currently" in result.output.lower()


def test_status_shows_heartbeat_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Terrarium Status" in result.output


def test_status_without_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 1


def test_config_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "Terrarium Configuration" in result.output
    assert "My Project" in result.output
    assert "gpt-4o" in result.output
    assert "30m" in result.output


def test_config_without_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 1


def test_install_hook_requires_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["install-hook"])
    assert result.exit_code == 1
    assert "not a git" in result.output.lower()


def test_install_hook_in_git_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    runner.invoke(app, ["init"])
    (tmp_path / ".git" / "hooks" / "post-commit").unlink()

    result = runner.invoke(app, ["install-hook"])
    assert result.exit_code == 0
    assert "installed" in result.output.lower()
    hook = tmp_path / ".git" / "hooks" / "post-commit"
    assert hook.exists()
    assert os.access(hook, os.X_OK)


def test_install_hook_already_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "post-commit").write_text("#!/bin/sh\nexit 0")
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["install-hook"])
    assert "already exists" in result.output.lower()


def test_uninstall_hook(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["install-hook"])

    result = runner.invoke(app, ["uninstall-hook"])
    assert result.exit_code == 0
    assert "removed" in result.output.lower()
    assert not (hooks_dir / "post-commit").exists()


def test_uninstall_hook_not_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    result = runner.invoke(app, ["uninstall-hook"])
    assert "no post-commit hook" in result.output.lower()


def test_uninstall_hook_not_ours(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "post-commit").write_text("#!/bin/sh\necho custom hook")

    result = runner.invoke(app, ["uninstall-hook"])
    assert result.exit_code == 1
    assert "not installed by terrarium" in result.output.lower()


def test_init_installs_hook_in_git_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    result = runner.invoke(app, ["init"])
    assert "post-commit hook installed" in result.output.lower()
    assert (tmp_path / ".git" / "hooks" / "post-commit").exists()
