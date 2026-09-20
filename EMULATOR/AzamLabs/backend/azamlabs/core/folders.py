"""
AzamLabs Folder-Wise Lab Hierarchy Service
Provides tree organization, folder creation, deletion, and lab movement.
"""

import io
import zipfile
from typing import List, Dict, Any, Optional
from azamlabs.core.database import db


class FolderService:
    """Manages folder taxonomy and hierarchical lab assignment."""

    @staticmethod
    def get_folder_tree() -> List[Dict[str, Any]]:
        """Returns structured folder tree with labs nested under each folder path."""
        return db.get_folder_tree()

    @staticmethod
    def list_folders() -> List[Dict[str, Any]]:
        """Returns all folders."""
        return db.list_folders()

    @staticmethod
    def create_folder(name: str, parent_id: Optional[str] = "root") -> Dict[str, Any]:
        """Creates a new folder."""
        return db.create_folder(name=name, parent_id=parent_id)

    @staticmethod
    def delete_folder(folder_id: str, delete_contents: bool = False) -> bool:
        """Deletes a folder. If delete_contents is True, deletes all nested labs; otherwise moves them to root."""
        return db.delete_folder(folder_id=folder_id, delete_topologies=delete_contents)

    @staticmethod
    def move_lab(lab_id: str, new_folder_path: str) -> bool:
        """Moves a lab to target folder path."""
        return db.move_topology_to_folder(lab_id=lab_id, new_folder_path=new_folder_path)

    @staticmethod
    def duplicate_lab(lab_id: str, new_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Duplicates a lab with a new ID and optional custom name."""
        return db.duplicate_topology(lab_id=lab_id, new_name=new_name)

    @staticmethod
    def export_folder_zip(folder_id: str) -> bytes:
        """Exports all topologies contained in a folder as a downloadable ZIP package."""
        all_folders = {f["id"]: f for f in db.list_folders()}
        target_folder = all_folders.get(folder_id)
        if not target_folder:
            raise ValueError(f"Folder '{folder_id}' not found.")

        folder_path = target_folder["path"]
        all_topos = db.list_topologies()
        matching_topos = [
            t for t in all_topos
            if (t.get("folder_path") == folder_path or
                (t.get("folder_path") or "").startswith(f"{folder_path}/"))
        ]

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zp:
            for summary in matching_topos:
                topo = db.get_topology(summary["id"])
                if not topo:
                    continue
                # Determine relative folder structure inside zip
                rel_path = (summary.get("folder_path") or "/").lstrip("/")
                safe_name = summary["name"].replace("/", "-").replace("\\", "-")
                filename = f"{rel_path}/{safe_name}.yaml" if rel_path else f"{safe_name}.yaml"
                zp.writestr(filename, topo.to_yaml())

        buf.seek(0)
        return buf.getvalue()


folder_service = FolderService()

