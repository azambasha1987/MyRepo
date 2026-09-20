"""
AzamLabs Universal .azaml Portable Lab Archive Manager
Packages complete lab environments (topology, configs, impairments, and metadata)
into a single compressed portable archive for effortless sharing and backup.
"""

import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from azamlabs.core.schema import AzamTopology, AzamNode


class LabBundleManager:
    """Handles packaging and extracting universal .azaml lab archives."""

    BUNDLE_VERSION = "1.0.0"

    @classmethod
    def export_azaml_bytes(cls, topology: AzamTopology) -> bytes:
        """Packages an AzamTopology into in-memory .azaml tar.gz bytes."""
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # 1. topology.yaml
            topo_yaml = topology.to_yaml().encode("utf-8")
            t_info = tarfile.TarInfo(name="topology.yaml")
            t_info.size = len(topo_yaml)
            t_info.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(t_info, io.BytesIO(topo_yaml))

            # 2. metadata.json
            metadata = {
                "format": "azaml",
                "bundle_version": cls.BUNDLE_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "lab_name": topology.name,
                "node_count": len(topology.nodes),
                "link_count": len(topology.links),
                "author": topology.author,
            }
            meta_bytes = json.dumps(metadata, indent=2).encode("utf-8")
            m_info = tarfile.TarInfo(name="metadata.json")
            m_info.size = len(meta_bytes)
            m_info.mtime = t_info.mtime
            tar.addfile(m_info, io.BytesIO(meta_bytes))

            # 3. configs/<node>.cfg
            for node in topology.nodes:
                cfg_content = node.startup_config or node.running_config
                if cfg_content:
                    c_bytes = cfg_content.encode("utf-8")
                    c_info = tarfile.TarInfo(name=f"configs/{node.name}.cfg")
                    c_info.size = len(c_bytes)
                    c_info.mtime = t_info.mtime
                    tar.addfile(c_info, io.BytesIO(c_bytes))

        return buffer.getvalue()

    @classmethod
    def export_azaml_file(cls, topology: AzamTopology, output_path: Union[str, Path]) -> Path:
        """Writes .azaml bundle directly to a file."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        bundle_bytes = cls.export_azaml_bytes(topology)
        target.write_bytes(bundle_bytes)
        return target

    @classmethod
    def import_azaml_archive(cls, archive: Union[str, Path, bytes]) -> AzamTopology:
        """Extracts and parses an AzamTopology from .azaml archive bytes or file path."""
        if isinstance(archive, (str, Path)):
            file_path = Path(archive)
            buffer = io.BytesIO(file_path.read_bytes())
        elif isinstance(archive, bytes):
            buffer = io.BytesIO(archive)
        else:
            raise ValueError("archive must be a file path or bytes")

        configs: dict[str, str] = {}
        topo_yaml_str: str | None = None

        with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name == "topology.yaml":
                    extracted = tar.extractfile(member)
                    if extracted:
                        topo_yaml_str = extracted.read().decode("utf-8")
                elif member.name.startswith("configs/") and member.name.endswith(".cfg"):
                    node_name = Path(member.name).stem
                    extracted = tar.extractfile(member)
                    if extracted:
                        configs[node_name] = extracted.read().decode("utf-8")

        if not topo_yaml_str:
            raise ValueError("Corrupt .azaml bundle: 'topology.yaml' not found in archive.")

        topology = AzamTopology.from_yaml(topo_yaml_str)

        # Overlay extracted configs
        for node in topology.nodes:
            if node.name in configs:
                node.startup_config = configs[node.name]

        return topology
