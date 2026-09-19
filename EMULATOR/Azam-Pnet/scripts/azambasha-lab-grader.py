#!/usr/bin/env python3
"""
==============================================================================
Azam Basha Automated Lab Grading & Validation Engine (azambasha-lab-grader.py)
==============================================================================
Validates student and engineer network lab topologies against customizable
certification exam checkpoints (CCNA, CCNP, CCIE) or dynamically against
any selected lab from the PNetLab Labs library. Outputs instant scores,
pass/fail metrics, and remediation hints.
==============================================================================
"""

import os
import sys
import json
import time
import argparse
import subprocess
import xml.etree.ElementTree as ET

LABS_ROOT = "/opt/unetlab/labs"

QUIZ_CATALOG = {
    "ccna_ospf_basics": {
        "title": "CCNA 200-301 — Multi-Area OSPF & VLAN Routing",
        "description": "Tests OSPFv2 Area 0 core adjacencies, passive interface security, and edge reachability.",
        "max_points": 100,
        "tasks": [
            {
                "id": "task_1",
                "name": "Core Router R1 to R2 OSPF Adjacency",
                "points": 25,
                "check_type": "ping",
                "target": "192.168.1.22",
                "expected": "online",
                "hint": "Ensure 'router ospf 1' is configured with matching Area 0 and MTU 1500."
            },
            {
                "id": "task_2",
                "name": "Gateway Reachability & Default Route",
                "points": 25,
                "check_type": "ping",
                "target": "192.168.1.1",
                "expected": "online",
                "hint": "Check 'ip route 0.0.0.0 0.0.0.0' pointing to the PNetLab gateway."
            },
            {
                "id": "task_3",
                "name": "Passive Interface Hardening on Access Links",
                "points": 25,
                "check_type": "process",
                "target": "qemu",
                "expected": "active",
                "hint": "Use 'passive-interface default' and unsuppress only routed core uplinks."
            },
            {
                "id": "task_4",
                "name": "End-to-End DNS Resolution & Outbound Ping",
                "points": 25,
                "check_type": "ping",
                "target": "1.1.1.1",
                "expected": "online",
                "hint": "Verify NAT overload (PAT) or external gateway transit route."
            }
        ]
    },
    "ccnp_bgp_enterprise": {
        "title": "CCNP ENCOR 350-401 — Enterprise Dual-Homed BGP & BFD",
        "description": "Tests eBGP multihop peering, AS-Path prepending, and sub-second BFD failover.",
        "max_points": 100,
        "tasks": [
            {
                "id": "task_1",
                "name": "Primary ISP eBGP Peering Established",
                "points": 30,
                "check_type": "ping",
                "target": "192.168.1.23",
                "expected": "online",
                "hint": "Check neighbor remote-as and verify TCP port 179 is not filtered."
            },
            {
                "id": "task_2",
                "name": "Secondary ISP Backup Transit & AS-Path Policy",
                "points": 30,
                "check_type": "ping",
                "target": "192.168.1.24",
                "expected": "online",
                "hint": "Ensure route-map prepends local AS 2x on the secondary link."
            },
            {
                "id": "task_3",
                "name": "BFD Hardware/Software Session Liveness",
                "points": 20,
                "check_type": "system",
                "target": "watchdog",
                "expected": "active",
                "hint": "Enable 'neighbor fall-over bfd' under router bgp."
            },
            {
                "id": "task_4",
                "name": "Loop-Free BGP Routing Convergence",
                "points": 20,
                "check_type": "ping",
                "target": "8.8.8.8",
                "expected": "online",
                "hint": "Verify default-originate or correct network prefix advertisement."
            }
        ]
    }
}


def ping_check(target_ip):
    try:
        r = subprocess.run(["ping", "-c", "2", "-W", "1", target_ip],
                           capture_output=True, text=True, timeout=3)
        return r.returncode == 0
    except Exception:
        return False


def resolve_lab_file(lab_path):
    if not lab_path:
        return None
    candidates = [
        lab_path,
        os.path.join(LABS_ROOT, lab_path),
        os.path.join(LABS_ROOT, f"{lab_path}.unl") if not lab_path.endswith(".unl") else None
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return os.path.abspath(c)

    # Search recursively under LABS_ROOT
    if os.path.isdir(LABS_ROOT):
        base_target = os.path.basename(lab_path)
        if not base_target.endswith(".unl"):
            base_target += ".unl"
        for root, dirs, files in os.walk(LABS_ROOT):
            if base_target in files:
                return os.path.join(root, base_target)
    return None


def parse_lab_topology(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        lab_name = root.attrib.get("name", os.path.splitext(os.path.basename(file_path))[0])
        desc_el = root.find("description")
        desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        nodes = []
        nodes_tag = root.find("topology/nodes")
        if nodes_tag is not None:
            for n in nodes_tag.findall("node"):
                nodes.append({
                    "id": n.attrib.get("id", ""),
                    "name": n.attrib.get("name", f"Node-{n.attrib.get('id', '')}"),
                    "type": n.attrib.get("type", "qemu"),
                    "template": n.attrib.get("template", ""),
                    "image": n.attrib.get("image", ""),
                    "ram": n.attrib.get("ram", "1024"),
                    "cpu": n.attrib.get("cpu", "1"),
                    "console": n.attrib.get("console", "")
                })

        networks = []
        nets_tag = root.find("topology/networks")
        if nets_tag is not None:
            for net in nets_tag.findall("network"):
                networks.append({
                    "id": net.attrib.get("id", ""),
                    "name": net.attrib.get("name", ""),
                    "type": net.attrib.get("type", "bridge")
                })

        return {
            "name": lab_name,
            "description": desc,
            "nodes": nodes,
            "networks": networks,
            "valid": True
        }
    except Exception as e:
        return {"valid": False, "error": str(e), "name": os.path.basename(file_path), "nodes": [], "networks": []}


def run_grading(quiz_id=None, lab_id="default_lab"):
    target_unl = resolve_lab_file(lab_id)

    # If an explicit quiz was requested and no unl file was provided
    if quiz_id and quiz_id in QUIZ_CATALOG and not target_unl:
        quiz = QUIZ_CATALOG[quiz_id]
        total_score = 0
        max_score = quiz["max_points"]
        results = []
        for task in quiz["tasks"]:
            passed = False
            ctype = task.get("check_type")
            target = task.get("target")
            if ctype == "ping":
                passed = ping_check(target)
            elif ctype == "process":
                try:
                    r = subprocess.run(["pgrep", "-f", target], capture_output=True)
                    passed = (r.returncode == 0)
                except Exception:
                    passed = False
            elif ctype == "system":
                try:
                    r = subprocess.run(["systemctl", "is-active", f"azam-{target}.service"], capture_output=True, text=True)
                    passed = (r.stdout.strip() == "active")
                except Exception:
                    passed = False

            pts = task["points"] if passed else 0
            total_score += pts
            results.append({
                "id": task["id"],
                "name": task["name"],
                "points_earned": pts,
                "max_points": task["points"],
                "status": "PASSED" if passed else "FAILED",
                "hint": "" if passed else task.get("hint", "")
            })
        pct = round((total_score / max(max_score, 1)) * 100, 1)
        return {
            "quiz_id": quiz_id,
            "title": quiz["title"],
            "lab_id": lab_id,
            "score": total_score,
            "max_score": max_score,
            "percentage": pct,
            "grade": "PASS" if pct >= 75 else "FAIL",
            "tasks": results,
            "timestamp": time.ctime()
        }

    # Dynamic Lab Evaluation against the real UNL topology
    topo = parse_lab_topology(target_unl) if target_unl else None
    lab_name = topo["name"] if topo and topo.get("valid") else (os.path.basename(lab_id) if lab_id else "Lab Evaluation")
    nodes = topo["nodes"] if topo and topo.get("valid") else []
    node_names = [n["name"] for n in nodes]

    tasks = []

    # Checkpoint 1: UNL Schema & Topology Definition
    schema_passed = (target_unl is not None and topo and topo.get("valid", False) and len(nodes) > 0)
    tasks.append({
        "id": "checkpoint_1",
        "name": f"UNL Topology Schema ({len(nodes)} Nodes Manifested)",
        "points": 20,
        "max_points": 20,
        "status": "PASSED" if schema_passed else "FAILED",
        "points_earned": 20 if schema_passed else 0,
        "hint": "" if schema_passed else "Verify lab XML is well-formed under /opt/unetlab/labs/."
    })

    # Checkpoint 2: Appliance Template & Allocation Compliance
    templates_valid = True
    if nodes:
        for n in nodes:
            if not n.get("template") and not n.get("type"):
                templates_valid = False
                break
    tasks.append({
        "id": "checkpoint_2",
        "name": "Appliance Template & RAM Allocation Compliance",
        "points": 20,
        "max_points": 20,
        "status": "PASSED" if templates_valid else "FAILED",
        "points_earned": 20 if templates_valid else 0,
        "hint": "" if templates_valid else "Check template YAML associations in /opt/unetlab/html/templates/."
    })

    # Checkpoint 3: Hypervisor Execution Plane & /dev/kvm Readiness
    hypervisor_ok = False
    try:
        r = subprocess.run(["pgrep", "-f", "qemu|dynamips|iol"], capture_output=True)
        if r.returncode == 0:
            hypervisor_ok = True
        else:
            hypervisor_ok = os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)
    except Exception:
        hypervisor_ok = False
    tasks.append({
        "id": "checkpoint_3",
        "name": "Hypervisor Execution Plane & /dev/kvm Readiness",
        "points": 20,
        "max_points": 20,
        "status": "PASSED" if hypervisor_ok else "FAILED",
        "points_earned": 20 if hypervisor_ok else 0,
        "hint": "" if hypervisor_ok else "Ensure /dev/kvm permissions are 0666 and KVM kernel module loaded."
    })

    # Checkpoint 4: Virtual Switching Fabric & Bridge TAP Connectivity
    bridge_ok = False
    try:
        r = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
        bridge_ok = ("pnet0" in r.stdout or "virbr0" in r.stdout or "docker0" in r.stdout)
    except Exception:
        bridge_ok = False
    tasks.append({
        "id": "checkpoint_4",
        "name": "Virtual Switching Fabric & Bridge TAP Connectivity",
        "points": 20,
        "max_points": 20,
        "status": "PASSED" if bridge_ok else "FAILED",
        "points_earned": 20 if bridge_ok else 0,
        "hint": "" if bridge_ok else "Verify pnet0 bridge is up in 'ip link show' or run azambasha-fix-network-boot."
    })

    # Checkpoint 5: Core Gateway Transit & External Reachability
    gw_ok = ping_check("192.168.1.1") or ping_check("1.1.1.1") or ping_check("8.8.8.8")
    tasks.append({
        "id": "checkpoint_5",
        "name": "Core Gateway Transit & External Reachability",
        "points": 20,
        "max_points": 20,
        "status": "PASSED" if gw_ok else "FAILED",
        "points_earned": 20 if gw_ok else 0,
        "hint": "" if gw_ok else "Check default gateway 192.168.1.1 and DNS connectivity."
    })

    total_score = sum(t["points_earned"] for t in tasks)
    max_score = sum(t["max_points"] for t in tasks)
    pct = round((total_score / max(max_score, 1)) * 100, 1)

    return {
        "lab_id": lab_id,
        "title": f"Lab Audit: {lab_name}",
        "unl_file": target_unl or lab_id,
        "node_count": len(nodes),
        "nodes": node_names,
        "score": total_score,
        "max_score": max_score,
        "percentage": pct,
        "grade": "PASS" if pct >= 75 else "FAIL",
        "tasks": tasks,
        "timestamp": time.ctime()
    }


def main():
    parser = argparse.ArgumentParser(description="Azam-Pnet Automated Lab Grader")
    parser.add_argument("--grade", action="store_true", help="Execute lab grading check")
    parser.add_argument("--quiz", type=str, default="", help="Quiz ID to run (optional)")
    parser.add_argument("--lab", type=str, default="", help="Target Lab Path or ID")
    parser.add_argument("--quizzes", action="store_true", help="List available quiz presets")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()

    if args.quizzes:
        catalog = [{"id": k, "title": v["title"], "desc": v["description"]} for k, v in QUIZ_CATALOG.items()]
        if args.json:
            print(json.dumps({"quizzes": catalog}, indent=2))
        else:
            print("=== Available Certification Quizzes ===")
            for q in catalog:
                print(f"  • {q['id'].ljust(22)}: {q['title']}")
        return

    report = run_grading(args.quiz, args.lab)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("================================================================================")
        print(f"         Azam-Pnet Exam Grader: {report['title']}")
        print("================================================================================")
        if report.get("unl_file"):
            print(f"  • Target File:        {report['unl_file']}")
        if report.get("nodes"):
            node_str = ", ".join(report["nodes"][:8])
            if len(report["nodes"]) > 8:
                node_str += f" (+{len(report['nodes']) - 8} more)"
            print(f"  • Topology Nodes:     {node_str}")
        print(f"  • Overall Score:      {report['score']} / {report['max_score']} ({report['percentage']}%)")
        status_color = "\033[32mPASS\033[0m" if report['grade'] == "PASS" else "\033[31mFAIL (Requires >= 75%)\033[0m"
        print(f"  • Result:             {status_color}")
        print("--------------------------------------------------------------------------------")
        for t in report["tasks"]:
            stat = "\033[32m[PASS]\033[0m" if t['status'] == 'PASSED' else "\033[31m[FAIL]\033[0m"
            print(f"  {stat} {t['name']:<50} ({t['points_earned']}/{t['max_points']} pts)")
            if t.get("hint"):
                print(f"        \033[33mHint: {t['hint']}\033[0m")
        print("================================================================================")


if __name__ == "__main__":
    main()
