"""
AzamLabs Asynchronous SQLite Database Manager
Provides ultra-lightweight persistence with WAL (Write-Ahead Logging) mode.
Eliminates heavy external SQL servers, saving ~400MB RAM.
"""

import contextlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from azamlabs.config import settings
from azamlabs.core.schema import AzamTopology, NodeStatus


class DatabaseManager:
    """Manages SQLite database storage for topologies, node states, and metrics."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextlib.contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            # Enable high-speed WAL mode and optimal caching
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initializes database tables and indexes."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS topologies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    version TEXT DEFAULT '1.0.0',
                    author TEXT DEFAULT '',
                    raw_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS node_states (
                    lab_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pid INTEGER,
                    console_port INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (lab_id, node_id),
                    FOREIGN KEY (lab_id) REFERENCES topologies(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS lab_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lab_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cpu_percent REAL DEFAULT 0.0,
                    ram_mb REAL DEFAULT 0.0,
                    active_nodes INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_node_states_lab ON node_states(lab_id);
            """)

    def save_topology(self, topology: AzamTopology) -> AzamTopology:
        """Inserts or updates a topology in the database."""
        raw_json = json.dumps(topology.model_dump(mode="json"))
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO topologies (id, name, description, version, author, raw_data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    version = excluded.version,
                    author = excluded.author,
                    raw_data = excluded.raw_data,
                    updated_at = excluded.updated_at;
            """, (
                topology.id,
                topology.name,
                topology.description,
                topology.version,
                topology.author,
                raw_json,
                now,
            ))
            # Sync node states
            for node in topology.nodes:
                conn.execute("""
                    INSERT INTO node_states (lab_id, node_id, node_name, status, pid, console_port, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(lab_id, node_id) DO UPDATE SET
                        node_name = excluded.node_name,
                        status = excluded.status,
                        console_port = excluded.console_port,
                        updated_at = excluded.updated_at;
                """, (
                    topology.id,
                    node.id,
                    node.name,
                    node.status.value,
                    None,
                    node.console_port,
                    now,
                ))
            conn.commit()
        return topology

    def get_topology(self, lab_id: str) -> Optional[AzamTopology]:
        """Retrieves a topology by ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT raw_data FROM topologies WHERE id = ?;", (lab_id,)).fetchone()
            if not row:
                return None
            data = json.loads(row["raw_data"])
            topo = AzamTopology(**data)

            # Overlay current node states from node_states table
            state_rows = conn.execute("SELECT node_id, status, console_port FROM node_states WHERE lab_id = ?;", (lab_id,)).fetchall()
            state_map = {r["node_id"]: r for r in state_rows}
            for node in topo.nodes:
                if node.id in state_map:
                    node.status = NodeStatus(state_map[node.id]["status"])
                    if state_map[node.id]["console_port"]:
                        node.console_port = state_map[node.id]["console_port"]
            return topo

    def list_topologies(self) -> List[Dict[str, Any]]:
        """Returns summary list of all stored topologies."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT t.id, t.name, t.description, t.version, t.author, t.created_at, t.updated_at,
                       COUNT(DISTINCT n.node_id) as total_nodes,
                       SUM(CASE WHEN n.status = 'running' THEN 1 ELSE 0 END) as running_nodes
                FROM topologies t
                LEFT JOIN node_states n ON t.id = n.lab_id
                GROUP BY t.id
                ORDER BY t.updated_at DESC;
            """).fetchall()
            return [dict(row) for row in rows]

    def delete_topology(self, lab_id: str) -> bool:
        """Deletes a topology and associated states."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM topologies WHERE id = ?;", (lab_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_node_status(
        self,
        lab_id: str,
        node_id: str,
        status: NodeStatus,
        pid: Optional[int] = None,
        console_port: Optional[int] = None
    ) -> None:
        """Updates runtime state of a specific node."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE node_states
                SET status = ?,
                    pid = COALESCE(?, pid),
                    console_port = COALESCE(?, console_port),
                    updated_at = ?
                WHERE lab_id = ? AND node_id = ?;
            """, (status.value, pid, console_port, now, lab_id, node_id))
            conn.commit()


# Global Database Instance
db = DatabaseManager()
db.init_db()
