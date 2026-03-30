"""Configuration loading and management."""

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


_ENV_VAR_PATTERN = re.compile(r"^\$\{(\w+)\}$")


def _resolve_env(value: str | None) -> str | None:
    """Resolve a ${VAR_NAME} reference to its environment variable value."""
    if not value:
        return value
    m = _ENV_VAR_PATTERN.match(value)
    if m:
        return os.environ.get(m.group(1))
    return value


def parse_interval(interval_str: str) -> int:
    """Parse interval string like '10m', '6h', '30s' to seconds.

    Raises ValueError with a descriptive message on invalid or non-positive input.
    """
    s = interval_str.strip()
    try:
        if s.endswith("m"):
            result = int(s[:-1]) * 60
        elif s.endswith("h"):
            result = int(s[:-1]) * 3600
        elif s.endswith("s"):
            result = int(s[:-1])
        else:
            result = int(s)
    except (ValueError, IndexError):
        raise ValueError(
            f"Invalid interval '{interval_str}'. "
            "Use a number followed by 's', 'm', or 'h' (e.g. '30s', '10m', '2h')."
        )
    if result <= 0:
        raise ValueError(
            f"Interval must be positive, got '{interval_str}' ({result}s)."
        )
    return result


class ProjectConfig(BaseModel):
    name: str = "My Project"


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.3
    api_key: str | None = None
    base_url: str | None = None

    def get_api_key(self) -> str | None:
        return _resolve_env(self.api_key)

    def get_base_url(self) -> str | None:
        return _resolve_env(self.base_url)


class HeartbeatConfig(BaseModel):
    interval: str = "30m"
    short_term_days: int = 3
    max_consecutive_errors: int = 5

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: str) -> str:
        parse_interval(v)
        return v

    @field_validator("short_term_days")
    @classmethod
    def validate_short_term_days(cls, v: int) -> int:
        if v < 1:
            raise ValueError("short_term_days must be at least 1")
        return v

    @field_validator("max_consecutive_errors")
    @classmethod
    def validate_max_consecutive_errors(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_consecutive_errors must be at least 1")
        return v


class BoundaryConfig(BaseModel):
    readonly: list[str] = Field(default_factory=lambda: ["pyproject.toml", "LICENSE"])
    writable: list[str] = Field(default_factory=lambda: ["src/**", "tests/**"])


class DriveConfig(BaseModel):
    name: str
    description: str


class TerrariumConfig(BaseModel):
    version: str = "0.1"
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)
    boundaries: BoundaryConfig = Field(default_factory=BoundaryConfig)
    drives: list[DriveConfig] = Field(default_factory=list)


def load_config(project_path: Path) -> TerrariumConfig:
    """Load configuration from .terrarium/config.yaml."""
    config_path = project_path / ".terrarium" / "config.yaml"
    if not config_path.exists():
        return TerrariumConfig()
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    return TerrariumConfig(**data)
