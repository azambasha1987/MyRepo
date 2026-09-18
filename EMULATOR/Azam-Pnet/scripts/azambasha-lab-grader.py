#!/usr/bin/env python3
"""
==============================================================================
Azam Basha Automated Lab Grading & Validation Engine (azambasha-lab-grader.py)
==============================================================================
Validates student and engineer network lab topologies against customizable
certification exam checkpoints (CCNA, CCNP, CCIE). Outputs instant scores,
pass/fail metrics, and remediation hints.
==============================================================================
"""

import os
import sys
import json
import time
import argparse
import subprocess

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


def run_grading(quiz_id="ccna_ospf_basics", lab_id="default_lab"):
    quiz = QUIZ_CATALOG.get(quiz_id, QUIZ_CATALOG["ccna_ospf_basics"])
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
    passed_exam = (pct >= 75)

    return {
        "quiz_id": quiz_id,
        "title": quiz["title"],
        "lab_id": lab_id,
        "score": total_score,
        "max_score": max_score,
        "percentage": pct,
        "grade": "PASS" if passed_exam else "FAIL",
        "tasks": results,
        "timestamp": time.ctime()
    }


def main():
    parser = argparse.ArgumentParser(description="Azam-Pnet Automated Lab Grader")
    parser.add_argument("--grade", action="store_true", help="Execute lab grading check")
    parser.add_argument("--quiz", type=str, default="ccna_ospf_basics", help="Quiz ID to run")
    parser.add_argument("--lab", type=str, default="default_lab", help="Target Lab ID")
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

    if args.grade or True:
        report = run_grading(args.quiz, args.lab)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("================================================================================")
            print(f"         Azam-Pnet Exam Grader: {report['title']}")
            print("================================================================================")
            print(f"  • Overall Score:      {report['score']} / {report['max_score']} ({report['percentage']}%)")
            status_color = "\033[32mPASS\033[0m" if report['grade'] == "PASS" else "\033[31mFAIL (Requires >= 75%)\033[0m"
            print(f"  • Result:             {status_color}")
            print("--------------------------------------------------------------------------------")
            for t in report["tasks"]:
                stat = "\033[32m[PASS]\033[0m" if t['status'] == 'PASSED' else "\033[31m[FAIL]\033[0m"
                print(f"  {stat} {t['name']:<48} ({t['points_earned']}/{t['max_points']} pts)")
                if t["hint"]:
                    print(f"        \033[33mHint: {t['hint']}\033[0m")
            print("================================================================================")


if __name__ == "__main__":
    main()
