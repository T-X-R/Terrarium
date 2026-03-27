"""Get Git repository status."""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parents[4]))

from src.utils.git import get_git_status


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: git_status.py <project_path>")
        sys.exit(1)
    
    status = get_git_status(Path(sys.argv[1]))
    print(json.dumps(status.model_dump(), indent=2))
