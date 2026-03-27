"""Project state and observation models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class GitStatus(BaseModel):
    """Git repository status."""
    branch: str = "unknown"
    uncommitted_changes: int = 0
    recent_commits: list[str] = Field(default_factory=list)


class FileStats(BaseModel):
    """File statistics."""
    total: int = 0
    by_extension: dict[str, int] = Field(default_factory=dict)


class TestResults(BaseModel):
    """Test execution results."""
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    error: Optional[str] = None


class ProjectState(BaseModel):
    """Current state of the project."""
    timestamp: datetime = Field(default_factory=datetime.now)
    files: FileStats = Field(default_factory=FileStats)
    git: GitStatus = Field(default_factory=GitStatus)
    tests: Optional[TestResults] = None


class Observation(BaseModel):
    """A single observation record."""
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    trigger: str = "manual"  # manual, heartbeat
    state: ProjectState = Field(default_factory=ProjectState)
    summary: Optional[str] = None
