"""Tests for configuration loading."""

import tempfile
from pathlib import Path

from src.core.config import load_config, TerrariumConfig


def test_defaults_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(Path(tmpdir))
        assert isinstance(config, TerrariumConfig)
        assert config.version == "0.1"
        assert config.heartbeat.interval == "30m"
        assert config.project.name == "My Project"
        assert "pyproject.toml" in config.boundaries.readonly


def test_load_from_yaml():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".terrarium" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("""\
version: "0.1"
project:
  name: "Test Project"
heartbeat:
  interval: "10m"
llm:
  provider: openai
  model: gpt-4o
boundaries:
  readonly:
    - "pyproject.toml"
    - "LICENSE"
  writable:
    - "src/**"
drives:
  - name: stability
    description: "tests must pass"
""")
        config = load_config(Path(tmpdir))

        assert config.project.name == "Test Project"
        assert config.heartbeat.interval == "10m"
        assert config.llm.provider == "openai"
        assert config.llm.model == "gpt-4o"
        assert "pyproject.toml" in config.boundaries.readonly
        assert "src/**" in config.boundaries.writable
        assert len(config.drives) == 1
        assert config.drives[0].name == "stability"


def test_env_var_api_key(monkeypatch):
    monkeypatch.setenv("MY_API_KEY", "test-key-123")
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".terrarium" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("llm:\n  api_key: \"${MY_API_KEY}\"\n")
        config = load_config(Path(tmpdir))
        assert config.llm.get_api_key() == "test-key-123"
