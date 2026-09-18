#!/usr/bin/env python3
"""
==============================================================================
Azam Basha Anti-Bootstorm Staggered Node Startup Engine (azam-bootstorm.py)
==============================================================================
Prevents CPU/IO bootstorm when starting large multi-vendor topologies.
Uses the PNetLab REST API to stagger node boot order by weight:
  Heavy (C8000v, XRd, Windows 11, vMX)  -> first, 2-3 per batch, 18s apart
  Medium (CSR1000v, vEOS, FortiGate)     -> second, 4 per batch, 10s apart
  Light (IOL, Alpine, Docker)            -> last, unlimited concurrent
==============================================================================
"""

import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar

# Node weight classification by template prefix
HEAVY_TEMPLATES = {
    "c8000v", "xrd", "xrv9k", "win", "win2022", "win11", "win2019",
    "vmx", "vqfxre", "vqfxpfe", "nxosv9k", "asa", "asav", "ftdv",
    "vcenter", "esxi", "bigip", "ixia"
}

MEDIUM_TEMPLATES = {
    "csr1000vng", "csr1000v", "veos", "viosl2", "vios", "routeros",
    "mikrotik", "cpsg", "huaweiusg6kv", "fortios", "firepower6",
    "sonicwall", "timos", "iol-xe"
}

# Anything else = light (IOL, Alpine, Ubuntu, dynamips, docker)

def get_node_weight(node_type: str) -> str:
    """Return 'heavy', 'medium', or 'light' based on node template name."""
    t = node_type.lower().split("-")[0].split("_")[0]
    if t in HEAVY_TEMPLATES:
        return "heavy"
    for h in HEAVY_TEMPLATES:
        if t.startswith(h):
            return "heavy"
    if t in MEDIUM_TEMPLATES:
        return "medium"
    for m in MEDIUM_TEMPLATES:
        if t.startswith(m):
            return "medium"
    return "light"


def create_session(host, username, password):
    """Login to PNetLab API and return an authenticated session cookie jar."""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    login_data = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"https://{host}/api/auth/login",
        data=login_data,
        headers={"Content-Type": "application/json", "User-Agent": "Azam-Bootstorm/1.0"}
    )
    
    try:
        ctx = __import__("ssl").create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = __import__("ssl").CERT_NONE
        opener.addhandler = None  # use urllib ssl context
        
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("status") == "success":
                return cj, ctx
            else:
                print(f"[!] Login failed: {body.get('message', 'Unknown error')}")
                return None, None
    except Exception as e:
        print(f"[!] Auth error: {e}")
        return None, None


def api_call(host, path, method="GET", data=None, cj=None, ctx=None):
    """Make an authenticated API call to PNetLab."""
    import ssl
    if ctx is None:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    
    url = f"https://{host}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8") if data else None,
        method=method,
        headers={"Content-Type": "application/json", "User-Agent": "Azam-Bootstorm/1.0"}
    )

    if cj:
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj),
            urllib.request.HTTPSHandler(context=ctx)
        )
        try:
            with opener.open(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"status": "fail", "message": str(e)}
    return {}


def get_lab_nodes(host, lab_path, tenant, cj, ctx):
    """Retrieve all nodes from a running lab session."""
    result = api_call(host, f"/api/labs/{lab_path}/nodes", cj=cj, ctx=ctx)
    if result.get("status") == "success":
        return result.get("data", {})
    return {}


def start_node(host, lab_session, node_id, tenant, cj, ctx):
    """Start a single node via the lab session API."""
    result = api_call(
        host,
        f"/api/labs/session/nodes/{node_id}/start",
        method="GET",
        cj=cj, ctx=ctx
    )
    return result.get("status") == "success"


def run_bootstorm(host, lab_path, username, password,
                  heavy_batch=2, heavy_delay=18,
                  medium_batch=4, medium_delay=10,
                  dry_run=False):
    """
    Staggered boot orchestration:
      1. Authenticate to PNetLab API
      2. Classify each node into heavy / medium / light
      3. Start in batches with configurable delays
    """
    print("================================================================================")
    print("        Azam-Pnet Anti-Bootstorm Staggered Node Startup Engine                  ")
    print("================================================================================")
    print(f"  Target:       https://{host}")
    print(f"  Lab:          {lab_path}")
    print(f"  Heavy nodes:  batch={heavy_batch}, delay={heavy_delay}s between batches")
    print(f"  Medium nodes: batch={medium_batch}, delay={medium_delay}s between batches")
    print(f"  Light nodes:  all concurrent (no delay)")
    if dry_run:
        print("  *** DRY-RUN MODE - No nodes will actually be started ***")
    print("--------------------------------------------------------------------------------")

    cj, ctx = create_session(host, username, password)
    if not cj:
        print("[!] Cannot connect to PNetLab API. Check host/credentials.")
        sys.exit(1)

    nodes_data = get_lab_nodes(host, lab_path, None, cj, ctx)
    if not nodes_data:
        print("[!] Could not retrieve nodes from lab. Ensure lab is open.")
        sys.exit(1)

    # Classify nodes
    heavy_nodes, medium_nodes, light_nodes = [], [], []
    for nid, node in nodes_data.items():
        ntype = node.get("type", "iol")
        weight = get_node_weight(ntype)
        entry = {
            "id": nid,
            "name": node.get("name", f"node-{nid}"),
            "type": ntype,
            "status": node.get("status", 0),
            "weight": weight
        }
        if weight == "heavy":
            heavy_nodes.append(entry)
        elif weight == "medium":
            medium_nodes.append(entry)
        else:
            light_nodes.append(entry)

    total = len(heavy_nodes) + len(medium_nodes) + len(light_nodes)
    print(f"\n  Found {total} nodes total:")
    print(f"    Heavy:  {len(heavy_nodes)} nodes ({', '.join(n['name'] for n in heavy_nodes[:5])}{'...' if len(heavy_nodes)>5 else ''})")
    print(f"    Medium: {len(medium_nodes)} nodes ({', '.join(n['name'] for n in medium_nodes[:5])}{'...' if len(medium_nodes)>5 else ''})")
    print(f"    Light:  {len(light_nodes)} nodes ({', '.join(n['name'] for n in light_nodes[:5])}{'...' if len(light_nodes)>5 else ''})")
    print()

    started_ok = 0
    started_fail = 0

    def start_batch(batch, label, delay_before_next):
        nonlocal started_ok, started_fail
        for i, node in enumerate(batch):
            nid = node["id"]
            nname = node["name"]
            ntype = node["type"]
            # Skip already running nodes
            if int(node.get("status", 0)) == 2:
                print(f"  [SKIP] {nname} ({ntype}) - already running")
                continue
            if dry_run:
                print(f"  [DRY-RUN] Would start {nname} ({ntype}) [{label}]")
                started_ok += 1
            else:
                print(f"  [↑ START] {nname} ({ntype}) [{label}]...", end=" ", flush=True)
                ok = start_node(host, lab_path, nid, None, cj, ctx)
                if ok:
                    print("✔")
                    started_ok += 1
                else:
                    print("✘ FAILED")
                    started_fail += 1

            # Stagger within batch
            if (i + 1) % heavy_batch == 0 and i < len(batch) - 1:
                if delay_before_next > 0 and not dry_run:
                    print(f"  [⏱ ] Waiting {delay_before_next}s for CPU/IO stabilization...")
                    time.sleep(delay_before_next)

    # Phase 1: Heavy nodes
    if heavy_nodes:
        print(f"[1/3] Starting {len(heavy_nodes)} HEAVY nodes (batch of {heavy_batch}, {heavy_delay}s gap)...")
        start_batch(heavy_nodes, "HEAVY", heavy_delay)

    # Phase 2: Medium nodes
    if medium_nodes:
        print(f"\n[2/3] Starting {len(medium_nodes)} MEDIUM nodes (batch of {medium_batch}, {medium_delay}s gap)...")
        start_batch(medium_nodes, "MEDIUM", medium_delay)

    # Phase 3: Light nodes (all at once)
    if light_nodes:
        print(f"\n[3/3] Starting {len(light_nodes)} LIGHT nodes (concurrent, no delay)...")
        start_batch(light_nodes, "LIGHT", 0)

    print("\n================================================================================")
    print(f"[✔] Boot orchestration complete! Started: {started_ok} ✔  Failed: {started_fail} ✘")
    print("================================================================================")


def install_symlink():
    if sys.platform != "win32":
        try:
            target = "/usr/local/bin/azam-bootstorm"
            source = os.path.realpath(__file__)
            if not os.path.exists(target) or os.path.realpath(target) != source:
                if os.path.exists(target):
                    os.remove(target)
                os.symlink(source, target)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Azam-Pnet Anti-Bootstorm Staggered Node Startup Engine"
    )
    parser.add_argument("--host", default="192.168.1.23",
                        help="PNetLab master IP or hostname (default: 192.168.1.23)")
    parser.add_argument("--lab", required=False, default=None,
                        help="Lab .unl file path (e.g. /Admin/mylab.unl)")
    parser.add_argument("--username", default="admin",
                        help="PNetLab web-GUI username (default: admin)")
    parser.add_argument("--password", default="azam",
                        help="PNetLab web-GUI password (default: azam)")
    parser.add_argument("--heavy-batch", type=int, default=2,
                        help="Number of heavy nodes to start per batch (default: 2)")
    parser.add_argument("--heavy-delay", type=int, default=18,
                        help="Seconds to wait between heavy node batches (default: 18)")
    parser.add_argument("--medium-batch", type=int, default=4,
                        help="Number of medium nodes to start per batch (default: 4)")
    parser.add_argument("--medium-delay", type=int, default=10,
                        help="Seconds to wait between medium node batches (default: 10)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate boot sequence without actually starting nodes")
    args = parser.parse_args()

    install_symlink()

    if not args.lab:
        print("[!] Error: --lab <path> is required. Example: --lab /Admin/big-topology.unl")
        print("         Run: azam-bootstorm --host 192.168.1.23 --lab /Admin/topology.unl")
        sys.exit(1)

    run_bootstorm(
        host=args.host,
        lab_path=args.lab,
        username=args.username,
        password=args.password,
        heavy_batch=args.heavy_batch,
        heavy_delay=args.heavy_delay,
        medium_batch=args.medium_batch,
        medium_delay=args.medium_delay,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
