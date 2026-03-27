"""Scan project files and return statistics."""

import json
import sys
from pathlib import Path
from collections import defaultdict


def scan_files(
    project_path: str,
    include_patterns: list[str] = None,
    exclude_patterns: list[str] = None,
) -> dict:
    """Scan files and return statistics."""
    project = Path(project_path)
    include_patterns = include_patterns or ["**/*"]
    exclude_patterns = exclude_patterns or [".git/**", "__pycache__/**", ".terrarium/**"]
    
    files = []
    for pattern in include_patterns:
        files.extend(project.glob(pattern))
    
    # Filter out excluded patterns
    def is_excluded(path: Path) -> bool:
        rel_path = str(path.relative_to(project))
        for pattern in exclude_patterns:
            if path.match(pattern) or rel_path.startswith(pattern.replace("/**", "")):
                return True
        return False
    
    files = [f for f in files if f.is_file() and not is_excluded(f)]
    
    # Count by extension
    by_extension = defaultdict(int)
    for f in files:
        ext = f.suffix or "no_ext"
        by_extension[ext] += 1
    
    return {
        "total": len(files),
        "by_extension": dict(by_extension),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: scan_files.py <project_path>")
        sys.exit(1)
    
    result = scan_files(sys.argv[1])
    print(json.dumps(result, indent=2))
