"""Query observation history."""

import json
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta


def query_history(
    project_path: str,
    limit: int = 10,
    since: str = None,
) -> list[dict]:
    """Query observation history."""
    db_path = Path(project_path) / ".terrarium" / "memory" / "observations.db"
    
    if not db_path.exists():
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    query = "SELECT * FROM observations"
    params = []
    
    if since:
        query += " WHERE timestamp >= ?"
        params.append(since)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "trigger": row["trigger"],
            "state": json.loads(row["state_json"]),
            "summary": row["summary"],
        }
        for row in rows
    ]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query_history.py <project_path> [limit] [since]")
        sys.exit(1)
    
    project_path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    since = sys.argv[3] if len(sys.argv) > 3 else None
    
    history = query_history(project_path, limit, since)
    print(json.dumps(history, indent=2))
