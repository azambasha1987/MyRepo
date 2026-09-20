"""
AzamLabs Asynchronous SQLite Database Manager
Provides ultra-lightweight persistence with WAL (Write-Ahead Logging) mode.
Eliminates heavy external SQL servers, saving ~400MB RAM.
"""

import contextlib
import json
import uuid
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
                    folder_path TEXT DEFAULT '/',
                    raw_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS folders (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    parent_id TEXT,
                    path TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

            # Migration: Ensure folder_path column exists in topologies
            pragma_info = conn.execute("PRAGMA table_info(topologies);").fetchall()
            col_names = [c["name"] for c in pragma_info]
            if "folder_path" not in col_names:
                conn.execute("ALTER TABLE topologies ADD COLUMN folder_path TEXT DEFAULT '/';")

            # Seed default folders (INSERT OR IGNORE guarantees safety)
            now_str = datetime.now(timezone.utc).isoformat()
            default_folders = [
                ("root", "Root", None, "/", now_str),
                ("enterprise", "Enterprise Networks", "root", "/Enterprise Networks", now_str),
                ("datacenter", "Data Center & Cloud", "root", "/Data Center & Cloud", now_str),
                ("cybersecurity", "Cybersecurity & PenTest", "root", "/Cybersecurity & PenTest", now_str),
                ("service_provider", "Service Provider", "root", "/Service Provider", now_str),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO folders (id, name, parent_id, path, created_at) VALUES (?, ?, ?, ?, ?);",
                default_folders
            )
            conn.commit()

    def save_topology(self, topology: AzamTopology) -> AzamTopology:
        """Inserts or updates a topology in the database."""
        raw_json = json.dumps(topology.model_dump(mode="json"))
        now = datetime.now(timezone.utc).isoformat()
        folder_path = getattr(topology, "folder_path", "/") or "/"
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO topologies (id, name, description, version, author, folder_path, raw_data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    version = excluded.version,
                    author = excluded.author,
                    folder_path = excluded.folder_path,
                    raw_data = excluded.raw_data,
                    updated_at = excluded.updated_at;
            """, (
                topology.id,
                topology.name,
                topology.description,
                topology.version,
                topology.author,
                folder_path,
                raw_json,
                now,
            ))
            # Sync node states: purge nodes no longer present in topology
            current_node_ids = [node.id for node in topology.nodes]
            if current_node_ids:
                placeholders = ",".join("?" for _ in current_node_ids)
                conn.execute(f"DELETE FROM node_states WHERE lab_id = ? AND node_id NOT IN ({placeholders});", (topology.id, *current_node_ids))
            else:
                conn.execute("DELETE FROM node_states WHERE lab_id = ?;", (topology.id,))

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
            row = conn.execute("SELECT raw_data, folder_path FROM topologies WHERE id = ?;", (lab_id,)).fetchone()
            if not row:
                return None
            data = json.loads(row["raw_data"])
            topo = AzamTopology(**data)
            topo.folder_path = row["folder_path"] or "/"

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
                SELECT t.id, t.name, t.description, t.version, t.author, t.folder_path, t.created_at, t.updated_at,
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

    # ==========================================
    # Folder-Wise Lab Hierarchy Management
    # ==========================================

    def create_folder(self, name: str, parent_id: Optional[str] = "root") -> Dict[str, Any]:
        """Creates a new folder in the hierarchy."""
        folder_id = uuid.uuid4().hex[:8]
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            parent_path = "/"
            if parent_id and parent_id != "root":
                p_row = conn.execute("SELECT path FROM folders WHERE id = ?;", (parent_id,)).fetchone()
                if p_row:
                    parent_path = p_row["path"].rstrip("/")

            clean_name = name.strip().replace("/", "-")
            path = f"{parent_path}/{clean_name}" if parent_path != "/" else f"/{clean_name}"

            existing = conn.execute("SELECT id, name, parent_id, path, created_at FROM folders WHERE path = ?;", (path,)).fetchone()
            if existing:
                return dict(existing)

            conn.execute("""
                INSERT INTO folders (id, name, parent_id, path, created_at)
                VALUES (?, ?, ?, ?, ?);
            """, (folder_id, clean_name, parent_id, path, now))
            conn.commit()
            return {"id": folder_id, "name": clean_name, "parent_id": parent_id, "path": path, "created_at": now}

    def list_folders(self) -> List[Dict[str, Any]]:
        """Returns flat list of all registered folders."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT id, name, parent_id, path, created_at FROM folders ORDER BY path ASC;").fetchall()
            return [dict(r) for r in rows]

    def delete_folder(self, folder_id: str, delete_topologies: bool = False) -> bool:
        """Deletes a folder (cannot delete root). If delete_topologies is True, deletes all contained labs too; otherwise moves orphan labs to root '/'."""
        if folder_id in ("root", "/"):
            return False
        with self._get_connection() as conn:
            row = conn.execute("SELECT path FROM folders WHERE id = ?;", (folder_id,)).fetchone()
            if not row:
                return False
            path = row["path"]
            if delete_topologies:
                # Delete all topologies in this folder and its subfolders
                conn.execute("DELETE FROM topologies WHERE folder_path = ? OR folder_path LIKE ?;", (path, f"{path}/%"))
            else:
                # Move any labs in this folder path to '/'
                conn.execute("UPDATE topologies SET folder_path = '/' WHERE folder_path = ? OR folder_path LIKE ?;", (path, f"{path}/%"))
            # Delete child folders and this folder
            conn.execute("DELETE FROM folders WHERE path = ? OR path LIKE ?;", (path, f"{path}/%"))
            conn.commit()
            return True

    def get_or_create_folder_by_path(self, full_path: str) -> Dict[str, Any]:
        """Given a path like '/BGP/Advanced' or 'BGP/Advanced', ensures all ancestor folders exist and returns folder record."""
        clean_path = full_path.strip().replace("\\", "/")
        if not clean_path.startswith("/"):
            clean_path = f"/{clean_path}"
        clean_path = clean_path.rstrip("/")
        if not clean_path:
            return {"id": "root", "name": "Root", "parent_id": None, "path": "/"}

        parts = [p.strip() for p in clean_path.split("/") if p.strip()]
        current_path = ""
        parent_id = "root"
        last_folder = {"id": "root", "name": "Root", "parent_id": None, "path": "/"}

        with self._get_connection() as conn:
            for part in parts:
                current_path = f"{current_path}/{part}"
                row = conn.execute("SELECT id, name, parent_id, path, created_at FROM folders WHERE path = ?;", (current_path,)).fetchone()
                if row:
                    last_folder = dict(row)
                    parent_id = last_folder["id"]
                else:
                    folder_id = uuid.uuid4().hex[:8]
                    now = datetime.now(timezone.utc).isoformat()
                    conn.execute("""
                        INSERT INTO folders (id, name, parent_id, path, created_at)
                        VALUES (?, ?, ?, ?, ?);
                    """, (folder_id, part, parent_id, current_path, now))
                    last_folder = {"id": folder_id, "name": part, "parent_id": parent_id, "path": current_path, "created_at": now}
                    parent_id = folder_id
            conn.commit()
        return last_folder

    def duplicate_topology(self, lab_id: str, new_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Creates an exact clone of a topology with a new ID and timestamp."""
        existing = self.get_topology(lab_id)
        if not existing:
            return None
        clone_id = f"lab-{uuid.uuid4().hex[:8]}"
        name = new_name or f"{existing.name} (Copy)"

        # Clone the topology object and update id and name
        cloned_topo = existing.model_copy(deep=True)
        cloned_topo.id = clone_id
        cloned_topo.name = name

        raw_json = json.dumps(cloned_topo.model_dump(mode="json"))
        now = datetime.now(timezone.utc).isoformat()
        folder_path = getattr(cloned_topo, "folder_path", "/") or "/"

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO topologies (id, name, description, version, author, folder_path, raw_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                clone_id,
                name,
                cloned_topo.description,
                cloned_topo.version,
                cloned_topo.author,
                folder_path,
                raw_json,
                now,
                now,
            ))
            for node in cloned_topo.nodes:
                conn.execute("""
                    INSERT INTO node_states (lab_id, node_id, node_name, status, pid, console_port, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    clone_id,
                    node.id,
                    node.name,
                    node.status.value,
                    None,
                    node.console_port,
                    now,
                ))
            conn.commit()
            row = conn.execute("SELECT * FROM topologies WHERE id = ?;", (clone_id,)).fetchone()
            return dict(row) if row else None

    def purge_test_topologies(self, preserve_ids: Optional[List[str]] = None) -> int:
        """Purges any non-seed/test topologies to keep the database clean and pristine."""
        preserve = preserve_ids or ["prod-cloud-mesh"]
        placeholders = ",".join("?" for _ in preserve)
        with self._get_connection() as conn:
            cursor = conn.execute(f"DELETE FROM topologies WHERE id NOT IN ({placeholders});", preserve)
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    def move_topology_to_folder(self, lab_id: str, new_folder_path: str) -> bool:
        """Moves a topology to a different folder path."""
        target_path = new_folder_path if new_folder_path.startswith("/") else f"/{new_folder_path}"
        with self._get_connection() as conn:
            cursor = conn.execute("UPDATE topologies SET folder_path = ?, updated_at = ? WHERE id = ?;", (
                target_path, datetime.now(timezone.utc).isoformat(), lab_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def get_folder_tree(self) -> List[Dict[str, Any]]:
        """Returns structured folder tree with labs nested under each folder."""
        folders = self.list_folders()
        topologies = self.list_topologies()

        # Map labs by folder_path
        labs_by_folder: Dict[str, List[Dict[str, Any]]] = {}
        for topo in topologies:
            fp = topo.get("folder_path") or "/"
            if fp not in labs_by_folder:
                labs_by_folder[fp] = []
            labs_by_folder[fp].append(topo)

        tree = []
        for f in folders:
            f_copy = dict(f)
            path = f["path"]
            f_copy["labs"] = labs_by_folder.get(path, [])
            f_copy["lab_count"] = len(f_copy["labs"])
            tree.append(f_copy)

        return tree

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
