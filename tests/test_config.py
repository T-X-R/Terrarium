# tests/test_config.py
import pytest
from pathlib import Path
import tempfile
import yaml

from src.core.config import load_config, TerrariumConfig


def test_load_config_from_yaml():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".terrarium" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("""
version: "0.1"
project:
  type: python
  name: "Test Project"
heartbeat:
  standard_interval: "30m"
  enabled: true
skills:
  - perception
  - memory
llm:
  provider: openai
  model: gpt-4o
boundaries:
  files:
    readonly:
      - "pyproject.toml"
""")
        config = load_config(Path(tmpdir))
        
        assert config.version == "0.1"
        assert config.project.type == "python"
        assert config.project.name == "Test Project"
        assert config.heartbeat.standard_interval == "30m"
        assert config.heartbeat.enabled is True
        assert "perception" in config.skills
        assert config.llm.provider == "openai"
        assert "pyproject.toml" in config.boundaries.files.readonly


def test_load_config_default_when_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(Path(tmpdir))
        
        assert config.version == "0.1"
        assert config.heartbeat.enabled is False
