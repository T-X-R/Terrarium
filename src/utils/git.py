"""Git operations wrapper."""

from pathlib import Path
from git import Repo, InvalidGitRepositoryError

from src.models.state import GitStatus


def get_git_status(project_path: Path) -> GitStatus:
    """Get Git repository status."""
    try:
        repo = Repo(project_path)
    except InvalidGitRepositoryError:
        return GitStatus()
    
    # Get current branch
    try:
        branch = repo.active_branch.name
    except TypeError:
        branch = "detached"
    
    # Count uncommitted changes
    uncommitted = len(repo.index.diff(None)) + len(repo.untracked_files)
    
    # Get recent commits
    recent_commits = []
    try:
        for commit in repo.iter_commits(max_count=5):
            recent_commits.append(f"{commit.hexsha[:7]} {commit.summary}")
    except Exception:
        pass
    
    return GitStatus(
        branch=branch,
        uncommitted_changes=uncommitted,
        recent_commits=recent_commits,
    )
