"""
AzamLabs Batch Lab Importer
Enables high-throughput batch extraction and conversion of bulk archives (.zip, .gns3project)
and host directories containing EVE-NG, PNETLab, GNS3, Containerlab, and CML labs.
Preserves folder taxonomy, resolves port collisions dynamically, and extracts Day-0 configs.
"""

import io
import os
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from azamlabs.core.schema import AzamTopology, DriverType
from azamlabs.converters.universal import UniversalConverter
from azamlabs.converters.gns3 import Gns3Converter
from azamlabs.converters.eve import EveConverter
from azamlabs.converters.containerlab import ContainerlabConverter
from azamlabs.converters.cml import CmlConverter
from azamlabs.core.database import db


class BatchLabImporter:
    """Orchestrates bulk lab imports from ZIP archives or local host directories."""

    SUPPORTED_EXTENSIONS = {
        ".unl",
        ".gns3",
        ".gns3project",
        ".clab.yml",
        ".clab.yaml",
        ".azaml",
        ".bundle",
    }

    @classmethod
    def is_supported_file(cls, path_or_name: str) -> bool:
        """Checks whether the given filename has a supported lab extension."""
        name_lower = path_or_name.lower()
        if name_lower.endswith((".clab.yml", ".clab.yaml")):
            return True
        ext = Path(name_lower).suffix
        return ext in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def resolve_port_collisions(cls, topo: AzamTopology) -> None:
        """
        Detects duplicate interface names per node and dynamically renames collisions,
        updating corresponding link endpoints to ensure flawless network simulation.
        """
        for node in topo.nodes:
            # 1. Resolve collisions in node.interfaces list
            seen_ifaces: Dict[str, int] = {}
            for iface in node.interfaces:
                if iface.name in seen_ifaces:
                    seen_ifaces[iface.name] += 1
                    old_name = iface.name
                    new_name = f"{old_name}_{seen_ifaces[old_name]}"
                    iface.name = new_name
                    # Remap any links referencing this node and old interface
                    for link in topo.links:
                        if link.source_node == node.name and link.source_interface == old_name:
                            link.source_interface = new_name
                        elif link.target_node == node.name and link.target_interface == old_name:
                            link.target_interface = new_name
                else:
                    seen_ifaces[iface.name] = 1

            # 2. Resolve link collisions where multiple links attach to the exact same interface
            iface_link_count: Dict[str, int] = {}
            for link in topo.links:
                if link.source_node == node.name:
                    if link.source_interface in iface_link_count:
                        iface_link_count[link.source_interface] += 1
                        new_name = f"{link.source_interface}_{iface_link_count[link.source_interface]}"
                        node.add_interface(new_name)
                        link.source_interface = new_name
                    else:
                        iface_link_count[link.source_interface] = 1
                elif link.target_node == node.name:
                    if link.target_interface in iface_link_count:
                        iface_link_count[link.target_interface] += 1
                        new_name = f"{link.target_interface}_{iface_link_count[link.target_interface]}"
                        node.add_interface(new_name)
                        link.target_interface = new_name
                    else:
                        iface_link_count[link.target_interface] = 1

    @classmethod
    def apply_iol_auto_licensing(cls, topo: AzamTopology) -> None:
        """
        Ensures Cisco IOL/IOU nodes have license environment variables and
        valid operational parameters to prevent simulation aborts.
        """
        for node in topo.nodes:
            template_name = str(node.metadata.get("template", "") if isinstance(node.metadata, dict) else "").lower()
            is_iol = (
                node.driver == DriverType.IOL or
                "iol" in template_name or
                "iou" in template_name or
                "iol" in node.image.lower() or
                "iou" in node.image.lower()
            )
            if is_iol:
                if not isinstance(node.env, dict):
                    node.env = {}
                node.env.setdefault("IOURC", "/etc/opt/iou/iourc")
                node.env.setdefault("CISCO_IOL_LICENSED", "true")

    @classmethod
    def import_zip(
        cls,
        zip_source: Union[bytes, str, Path],
        target_folder: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Extracts and converts all supported lab topologies from a ZIP archive.
        Preserves internal directory paths as folder hierarchies in AzamLabs.
        """
        if isinstance(zip_source, (str, Path)):
            zip_bytes = Path(zip_source).read_bytes()
        else:
            zip_bytes = zip_source

        results: Dict[str, Any] = {
            "total_found": 0,
            "imported_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "imported_labs": [],
            "errors": [],
        }

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zp:
            file_list = [f for f in zp.namelist() if not f.endswith("/")]

            # First, check for .gns3project nested files or project.gns3
            candidate_files = [f for f in file_list if cls.is_supported_file(f)]
            results["total_found"] = len(candidate_files)

            for member_name in candidate_files:
                try:
                    raw_bytes = zp.read(member_name)
                    member_path = Path(member_name)
                    parent_dir = member_path.parent.as_posix()

                    # Derive folder path
                    if parent_dir and parent_dir != ".":
                        folder_path = f"/{parent_dir}"
                        if target_folder and target_folder != "/":
                            folder_path = f"/{target_folder.strip('/')}/{parent_dir}"
                    else:
                        folder_path = target_folder or "/"

                    folder_path = folder_path.replace("\\", "/")
                    if not folder_path.startswith("/"):
                        folder_path = f"/{folder_path}"

                    # Detect and convert
                    ext = member_path.suffix.lower()
                    if ext == ".gns3project":
                        topo = Gns3Converter.gns3project_to_azam(raw_bytes)
                    elif ext == ".unl":
                        xml_str = raw_bytes.decode("utf-8", errors="ignore")
                        topo = EveConverter.eve_to_azam(xml_str)
                    elif ext == ".gns3":
                        json_str = raw_bytes.decode("utf-8", errors="ignore")
                        topo = Gns3Converter.gns3_to_azam(json_str)
                    elif member_name.lower().endswith((".clab.yml", ".clab.yaml")):
                        yaml_str = raw_bytes.decode("utf-8", errors="ignore")
                        topo = ContainerlabConverter.clab_to_azam(yaml_str)
                    else:
                        topo = UniversalConverter.import_lab(raw_bytes, filename=member_path.name)

                    # Post-process topology
                    cls.resolve_port_collisions(topo)
                    cls.apply_iol_auto_licensing(topo)
                    topo.folder_path = folder_path

                    if not dry_run:
                        db.get_or_create_folder_by_path(folder_path)
                        db.save_topology(topo)

                    results["imported_count"] += 1
                    results["imported_labs"].append({
                        "id": topo.id,
                        "name": topo.name,
                        "folder_path": folder_path,
                        "node_count": len(topo.nodes),
                        "link_count": len(topo.links),
                    })

                except Exception as ex:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "file": member_name,
                        "error": str(ex)
                    })

        return results

    @classmethod
    def import_directory(
        cls,
        dir_path: Union[str, Path],
        target_folder: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Recursively scans and converts all supported lab files from a local directory path.
        """
        root_path = Path(dir_path)
        if not root_path.is_dir():
            raise ValueError(f"Directory '{dir_path}' does not exist or is not a directory.")

        results: Dict[str, Any] = {
            "total_found": 0,
            "imported_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "imported_labs": [],
            "errors": [],
        }

        # Gather files
        all_candidates: List[Path] = []
        for current_root, _, files in os.walk(root_path):
            for file_name in files:
                if cls.is_supported_file(file_name):
                    all_candidates.append(Path(current_root) / file_name)

        results["total_found"] = len(all_candidates)

        for file_path in all_candidates:
            rel_path = file_path.relative_to(root_path)
            parent_dir = rel_path.parent.as_posix()

            if parent_dir and parent_dir != ".":
                folder_path = f"/{parent_dir}"
                if target_folder and target_folder != "/":
                    folder_path = f"/{target_folder.strip('/')}/{parent_dir}"
            else:
                folder_path = target_folder or "/"

            folder_path = folder_path.replace("\\", "/")
            if not folder_path.startswith("/"):
                folder_path = f"/{folder_path}"

            try:
                ext = file_path.suffix.lower()
                if ext == ".gns3project":
                    topo = Gns3Converter.gns3project_to_azam(file_path.read_bytes())
                elif ext == ".unl":
                    xml_str = file_path.read_text(encoding="utf-8", errors="ignore")
                    topo = EveConverter.eve_to_azam(xml_str)
                elif ext == ".gns3":
                    json_str = file_path.read_text(encoding="utf-8", errors="ignore")
                    topo = Gns3Converter.gns3_to_azam(json_str)
                elif file_path.name.lower().endswith((".clab.yml", ".clab.yaml")):
                    yaml_str = file_path.read_text(encoding="utf-8", errors="ignore")
                    topo = ContainerlabConverter.clab_to_azam(yaml_str)
                else:
                    topo = UniversalConverter.import_lab(file_path.read_bytes(), filename=file_path.name)

                cls.resolve_port_collisions(topo)
                cls.apply_iol_auto_licensing(topo)
                topo.folder_path = folder_path

                if not dry_run:
                    db.get_or_create_folder_by_path(folder_path)
                    db.save_topology(topo)

                results["imported_count"] += 1
                results["imported_labs"].append({
                    "id": topo.id,
                    "name": topo.name,
                    "folder_path": folder_path,
                    "node_count": len(topo.nodes),
                    "link_count": len(topo.links),
                })

            except Exception as ex:
                results["failed_count"] += 1
                results["errors"].append({
                    "file": str(rel_path),
                    "error": str(ex)
                })

        return results
