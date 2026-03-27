"""Configuration loading and management."""

from pathlib import Path
from typing import Optional
import os
import yaml
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    """Project information."""
    type: str = "python"
    name: str = "My Project"


class HeartbeatConfig(BaseModel):
    """Heartbeat scheduling configuration."""
    quick_interval: str = "10m"
    standard_interval: str = "30m"
    deep_interval: str = "6h"
    enabled: bool = False


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.3
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from config or environment."""
        if self.api_key and self.api_key.startswith("${"):
            env_var = self.api_key[2:-1]
            return os.environ.get(env_var)
        return self.api_key
    
    def get_base_url(self) -> Optional[str]:
        """Get base URL from config or environment."""
        if self.base_url and self.base_url.startswith("${"):
            env_var = self.base_url[2:-1]
            return os.environ.get(env_var)
        return self.base_url


class PerceptionConfig(BaseModel):
    """Perception skill configuration."""
    include_patterns: list[str] = Field(default_factory=lambda: ["**/*.py", "**/*.md"])
    exclude_patterns: list[str] = Field(default_factory=lambda: [".git/**", "__pycache__/**", ".terrarium/**"])
    commands: dict[str, str] = Field(default_factory=dict)


class FileBoundaries(BaseModel):
    """File-level boundaries."""
    readonly: list[str] = Field(default_factory=lambda: ["pyproject.toml", "LICENSE"])
    writable: list[str] = Field(default_factory=lambda: ["src/**/*.py", "tests/**/*.py"])


class ActionBoundaries(BaseModel):
    """Action-level boundaries."""
    allowed: list[str] = Field(default_factory=lambda: ["edit_file", "create_file", "run_tests"])
    forbidden: list[str] = Field(default_factory=lambda: ["delete_file", "git_push"])


class ChangeBoundaries(BaseModel):
    """Change-level boundaries."""
    max_lines_per_change: int = 100
    require_approval: list[str] = Field(default_factory=lambda: ["changes > 50 lines"])


class BoundariesConfig(BaseModel):
    """All boundary rules."""
    files: FileBoundaries = Field(default_factory=FileBoundaries)
    actions: ActionBoundaries = Field(default_factory=ActionBoundaries)
    changes: ChangeBoundaries = Field(default_factory=ChangeBoundaries)


class TerrariumConfig(BaseModel):
    """Main Terrarium configuration."""
    version: str = "0.1"
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)
    skills: list[str] = Field(default_factory=lambda: ["perception", "memory"])
    llm: LLMConfig = Field(default_factory=LLMConfig)
    perception: PerceptionConfig = Field(default_factory=PerceptionConfig)
    boundaries: BoundariesConfig = Field(default_factory=BoundariesConfig)


def load_config(project_path: Path) -> TerrariumConfig:
    """Load configuration from .terrarium/config.yaml."""
    config_path = project_path / ".terrarium" / "config.yaml"
    
    if not config_path.exists():
        return TerrariumConfig()
    
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    
    return TerrariumConfig(**data)
