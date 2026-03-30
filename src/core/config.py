"""Configuration loading and management."""

from pathlib import Path
from typing import Optional
import os
import yaml
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    name: str = "My Project"


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.3
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    def get_api_key(self) -> Optional[str]:
        if self.api_key and self.api_key.startswith("${"):
            return os.environ.get(self.api_key[2:-1])
        return self.api_key

    def get_base_url(self) -> Optional[str]:
        if self.base_url and self.base_url.startswith("${"):
            return os.environ.get(self.base_url[2:-1])
        return self.base_url


class HeartbeatConfig(BaseModel):
    interval: str = "30m"


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
