"""Save observation to database."""

import json
import sys
import sqlite3
from pathlib import Path
from datetime import datetime


def ensure_db(db_path: Path) -> sqlite3.Connection:
    """Ensure database exists and return connection."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            trigger TEXT NOT NULL,
            state_json TEXT NOT NULL,
            summary TEXT
        )
    """)
    conn.commit()
    return conn


def save_observation(
    project_path: str,
    state_json: str,
    trigger: str = "manual",
    summary: str = None,
) -> int:
    """Save an observation record."""
    db_path = Path(project_path) / ".terrarium" / "memory" / "observations.db"
    conn = ensure_db(db_path)
    
    cursor = conn.execute(
        """
        INSERT INTO observations (timestamp, trigger, state_json, summary)
        VALUES (?, ?, ?, ?)
        """,
        (datetime.now().isoformat(), trigger, state_json, summary),
    )
    conn.commit()
    
    observation_id = cursor.lastrowid
    conn.close()
    
    return observation_id


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: save_observation.py <project_path> <state_json> [trigger] [summary]")
        sys.exit(1)
    
    project_path = sys.argv[1]
    state_json = sys.argv[2]
    trigger = sys.argv[3] if len(sys.argv) > 3 else "manual"
    summary = sys.argv[4] if len(sys.argv) > 4 else None
    
    obs_id = save_observation(project_path, state_json, trigger, summary)
    print(json.dumps({"id": obs_id}))
