"""Tests for configuration loading."""

import yaml
import pytest
from pydantic import ValidationError

from src.core.cli import DEFAULT_CONFIG
from src.core.config import (
    HeartbeatConfig,
    LLMConfig,
    TerrariumConfig,
    load_config,
    parse_interval,
)


class TestParseInterval:
    def test_minutes(self):
        assert parse_interval("10m") == 600

    def test_hours(self):
        assert parse_interval("2h") == 7200

    def test_seconds(self):
        assert parse_interval("30s") == 30

    def test_bare_number(self):
        assert parse_interval("120") == 120

    def test_whitespace_stripped(self):
        assert parse_interval("  2h  ") == 7200

    def test_one_minute(self):
        assert parse_interval("1m") == 60

    def test_invalid_suffix(self):
        with pytest.raises(ValueError, match="Invalid interval"):
            parse_interval("10x")

    def test_negative(self):
        with pytest.raises(ValueError, match="Interval must be positive"):
            parse_interval("-5s")

    def test_zero(self):
        with pytest.raises(ValueError, match="Interval must be positive"):
            parse_interval("0s")


class TestHeartbeatValidation:
    def test_invalid_interval_raises_validation_error(self):
        with pytest.raises(ValidationError):
            HeartbeatConfig(interval="not-an-interval")

    def test_short_term_days_zero_raises(self):
        with pytest.raises(ValidationError):
            HeartbeatConfig(short_term_days=0)

    def test_max_consecutive_errors_zero_raises(self):
        with pytest.raises(ValidationError):
            HeartbeatConfig(max_consecutive_errors=0)

    def test_custom_valid_values(self):
        hb = HeartbeatConfig(
            interval="15m",
            short_term_days=7,
            max_consecutive_errors=10,
        )
        assert hb.interval == "15m"
        assert hb.short_term_days == 7
        assert hb.max_consecutive_errors == 10


class TestLoadConfig:
    def test_defaults_when_no_file(self, tmp_path):
        config = load_config(tmp_path)
        assert isinstance(config, TerrariumConfig)
        assert config.version == "0.1"
        assert config.heartbeat.interval == "30m"
        assert config.project.name == "My Project"
        assert "pyproject.toml" in config.boundaries.readonly

    def test_load_from_yaml(self, tmp_path):
        config_path = tmp_path / ".terrarium" / "config.yaml"
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
        config = load_config(tmp_path)

        assert config.project.name == "Test Project"
        assert config.heartbeat.interval == "10m"
        assert config.llm.provider == "openai"
        assert config.llm.model == "gpt-4o"
        assert "pyproject.toml" in config.boundaries.readonly
        assert "src/**" in config.boundaries.writable
        assert len(config.drives) == 1
        assert config.drives[0].name == "stability"


class TestLLMConfig:
    def test_env_var_api_key(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_API_KEY", "test-key-123")
        config_path = tmp_path / ".terrarium" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text('llm:\n  api_key: "${MY_API_KEY}"\n')
        config = load_config(tmp_path)
        assert config.llm.get_api_key() == "test-key-123"

    def test_env_var_base_url(self, monkeypatch):
        monkeypatch.setenv("MY_BASE_URL", "https://api.example.com")
        cfg = LLMConfig(base_url="${MY_BASE_URL}")
        assert cfg.get_base_url() == "https://api.example.com"

    def test_malformed_env_var_returned_as_literal(self):
        cfg = LLMConfig(api_key="${")
        assert cfg.get_api_key() == "${"

        cfg2 = LLMConfig(api_key="${MISSING_CLOSE")
        assert cfg2.get_api_key() == "${MISSING_CLOSE"

    def test_plain_api_key_returned_as_is(self):
        cfg = LLMConfig(api_key="sk-plain-key")
        assert cfg.get_api_key() == "sk-plain-key"

    def test_none_api_key(self):
        cfg = LLMConfig()
        assert cfg.get_api_key() is None


class TestDefaultConfigTemplate:
    """Ensure DEFAULT_CONFIG in cli.py stays in sync with model defaults."""

    def test_parses_as_valid_terrarium_config(self):
        data = yaml.safe_load(DEFAULT_CONFIG) or {}
        config = TerrariumConfig(**data)
        assert config.version == "0.1"
        assert config.project.name == "My Project"

    def test_heartbeat_interval_matches_default(self):
        data = yaml.safe_load(DEFAULT_CONFIG) or {}
        config = TerrariumConfig(**data)
        defaults = TerrariumConfig()
        assert config.heartbeat.interval == defaults.heartbeat.interval

    def test_boundaries_match_defaults(self):
        data = yaml.safe_load(DEFAULT_CONFIG) or {}
        config = TerrariumConfig(**data)
        defaults = TerrariumConfig()
        assert set(config.boundaries.readonly) == set(defaults.boundaries.readonly)

    def test_llm_defaults_match(self):
        data = yaml.safe_load(DEFAULT_CONFIG) or {}
        config = TerrariumConfig(**data)
        defaults = TerrariumConfig()
        assert config.llm.provider == defaults.llm.provider
        assert config.llm.model == defaults.llm.model
        assert config.llm.temperature == defaults.llm.temperature
