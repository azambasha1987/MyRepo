"""
AzamLabs Universal Converter & Auto-Detector Orchestrator
Automatically identifies incoming lab formats (Containerlab, CML2, EVE-NG, GNS3, P2V, AZAML)
and converts seamlessly into canonical AzamTopology. Also provides multi-format export.
"""

import json
import yaml
from pathlib import Path
from typing import Union, Optional

from azamlabs.core.schema import AzamTopology
from azamlabs.converters.containerlab import ContainerlabConverter
from azamlabs.converters.cml import CmlConverter
from azamlabs.converters.eve import EveConverter
from azamlabs.converters.gns3 import Gns3Converter
from azamlabs.converters.p2v import P2VConverter
from azamlabs.converters.bundle import LabBundleManager


class UniversalConverter:
    """Master orchestrator for auto-detecting and translating network topologies."""

    SUPPORTED_FORMATS = ["clab", "cml", "eve", "gns3", "p2v", "azaml", "azam_yaml", "azam_json"]

    @classmethod
    def auto_detect_format(
        cls,
        content: Union[str, bytes],
        filename: Optional[str] = None
    ) -> str:
        """Determines the file or text format using extension and content signatures."""
        if filename:
            ext = Path(filename).suffix.lower()
            if ext in (".azaml", ".bundle"):
                return "azaml"
            elif ext in (".unl",):
                return "eve"
            elif ext in (".gns3",):
                return "gns3"
            elif ext in (".clab.yml", ".clab.yaml"):
                return "clab"

        # Check for binary .azaml tar archive signature
        if isinstance(content, bytes):
            # Gzip magic bytes (1f 8b)
            if len(content) > 2 and content[:2] == b"\x1f\x8b":
                return "azaml"
            try:
                content_str = content.decode("utf-8")
            except UnicodeDecodeError:
                return "azaml"
        else:
            content_str = content

        trimmed = content_str.strip()

        # 1. Check for XML (EVE-NG / PNETLab)
        if trimmed.startswith("<") or "<lab " in trimmed or "<topology>" in trimmed:
            return "eve"

        # 2. Check for GNS3 JSON
        if trimmed.startswith("{"):
            try:
                parsed_json = json.loads(trimmed)
                if isinstance(parsed_json, dict):
                    if "topology" in parsed_json and "nodes" in parsed_json.get("topology", {}):
                        return "gns3"
                    if "project_id" in parsed_json:
                        return "gns3"
                    if "version" in parsed_json and "nodes" in parsed_json:
                        return "azam_json"
            except Exception:
                pass

        # 3. Check for YAML formats (Containerlab, CML 2.x, or AzamLabs Canonical)
        try:
            parsed_yaml = yaml.safe_load(trimmed)
            if isinstance(parsed_yaml, dict):
                # AzamLabs Canonical
                if "author" in parsed_yaml and "nodes" in parsed_yaml and "links" in parsed_yaml:
                    return "azam_yaml"
                # Containerlab
                if "topology" in parsed_yaml and "nodes" in parsed_yaml.get("topology", {}):
                    return "clab"
                if "mgmt" in parsed_yaml and "name" in parsed_yaml:
                    return "clab"
                # Cisco CML 2.x
                if "lab" in parsed_yaml and "nodes" in parsed_yaml:
                    return "cml"
                if "nodes" in parsed_yaml and any("node_definition" in str(n) for n in parsed_yaml.get("nodes", [])):
                    return "cml"
        except Exception:
            pass

        # 4. Check for Physical-to-Virtual Config text
        if "hostname " in trimmed.lower() or "sysname " in trimmed.lower() or "interface " in trimmed.lower():
            return "p2v"

        return "unknown"

    @classmethod
    def import_lab(
        cls,
        content: Union[str, bytes],
        filename: Optional[str] = None,
        format_hint: Optional[str] = None,
    ) -> AzamTopology:
        """Auto-detects format and parses input into an AzamTopology."""
        detected = format_hint or cls.auto_detect_format(content, filename)

        if detected == "azaml":
            return LabBundleManager.import_azaml_archive(content)

        # Convert bytes to string for text formats
        if isinstance(content, bytes):
            content_str = content.decode("utf-8")
        else:
            content_str = content

        if detected == "clab":
            return ContainerlabConverter.clab_to_azam(content_str)
        elif detected == "cml":
            return CmlConverter.cml_to_azam(content_str)
        elif detected == "eve":
            return EveConverter.eve_to_azam(content_str)
        elif detected == "gns3":
            return Gns3Converter.gns3_to_azam(content_str)
        elif detected == "p2v":
            lab_name = Path(filename).stem if filename else "P2V-Topology"
            return P2VConverter.p2v_to_azam(content_str, lab_name=lab_name)
        elif detected in ("azam_yaml", "azam_json"):
            return AzamTopology.from_yaml(content_str)
        else:
            # Fallback: attempt to parse as P2V if configs, or AzamTopology YAML
            try:
                return AzamTopology.from_yaml(content_str)
            except Exception:
                return P2VConverter.p2v_to_azam(content_str)

    @classmethod
    def export_lab(
        cls,
        topology: AzamTopology,
        target_format: str
    ) -> Union[str, bytes]:
        """Translates an AzamTopology into any requested external platform format."""
        target = target_format.lower()

        if target == "clab":
            return ContainerlabConverter.azam_to_clab(topology)
        elif target == "cml":
            return CmlConverter.azam_to_cml(topology)
        elif target == "eve":
            return EveConverter.azam_to_eve(topology)
        elif target == "gns3":
            return Gns3Converter.azam_to_gns3(topology)
        elif target == "azaml":
            return LabBundleManager.export_azaml_bytes(topology)
        elif target == "json":
            return json.dumps(topology.model_dump(mode="json"), indent=2)
        elif target in ("yaml", "azam", "canonical"):
            return topology.to_yaml()
        else:
            raise ValueError(
                f"Unsupported export format '{target_format}'. "
                f"Supported formats: {cls.SUPPORTED_FORMATS}"
            )
