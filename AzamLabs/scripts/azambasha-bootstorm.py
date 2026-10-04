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
    """Login to PNetLab API and return an authenticated session cookie jar, context, proto, and opener."""
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=ctx),
        urllib.request.HTTPHandler()
    )

    login_data = json.dumps({"username": username, "password": password, "html5": 0}).encode("utf-8")
    
    # Try endpoints: standard PNetLab is /api/auth, followed by fallbacks
    endpoints = ["/api/auth", "/api/auth/login"]
    protocols = ["https", "http"] if host in ("127.0.0.1", "localhost") else ["https", "http"]

    last_err = None
    for proto in protocols:
        for ep in endpoints:
            url = f"{proto}://{host}{ep}"
            req = urllib.request.Request(
                url,
                data=login_data,
                headers={"Content-Type": "application/json", "User-Agent": "Azam-Bootstorm/1.0"}
            )
            try:
                with opener.open(req, timeout=15) as resp:
                    resp_body = resp.read().decode("utf-8")
                    try:
                        body = json.loads(resp_body)
                    except Exception:
                        body = {}
                    if body.get("status") == "success" or resp.status == 200:
                        return cj, ctx, proto, opener
                    else:
                        last_err = body.get("message", "Authentication rejected")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue  # Try next endpoint
                try:
                    err_body = json.loads(e.read().decode("utf-8"))
                    last_err = err_body.get("message", f"HTTP Error {e.code}: {e.reason}")
                except Exception:
                    last_err = f"HTTP Error {e.code}: {e.reason}"
            except Exception as e:
                last_err = str(e)

    print(f"[!] Auth error: {last_err or 'Endpoint resolution failed'}")
    return None, None, None, None


def api_call(host, path, method="GET", data=None, cj=None, ctx=None, proto="https", opener=None):
    """Make an authenticated API call to PNetLab."""
    import ssl
    if ctx is None:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    
    if opener is None:
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj) if cj else urllib.request.BaseHandler(),
            urllib.request.HTTPSHandler(context=ctx),
            urllib.request.HTTPHandler()
        )
    
    url = f"{proto}://{host}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8") if data else None,
        method=method,
        headers={"Content-Type": "application/json", "User-Agent": "Azam-Bootstorm/1.0"}
    )

    try:
        with opener.open(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"status": "fail", "message": str(e)}


def get_lab_nodes(host, lab_path, tenant, cj, ctx, proto="https", opener=None):
    """Retrieve all nodes from a running lab session or lab file path."""
    clean_path = lab_path.strip("/")
    candidates = [
        f"/api/labs/{clean_path}/nodes",
        f"/api/labs/{clean_path}.unl/nodes",
        "/api/labs/session/nodes"
    ]
    if clean_path.endswith(".unl"):
        candidates.insert(0, f"/api/labs/{clean_path[:-4]}/nodes")

    for path in candidates:
        result = api_call(host, path, cj=cj, ctx=ctx, proto=proto, opener=opener)
        if result.get("status") == "success" and result.get("data"):
            data = result.get("data")
            if isinstance(data, dict):
                return data
            elif isinstance(data, list):
                return {str(item.get("id", idx)): item for idx, item in enumerate(data)}

    # Direct local file discovery fallback if running locally
    labs_base = "/opt/unetlab/labs"
    if os.path.isdir(labs_base):
        local_candidates = [
            os.path.join(labs_base, clean_path),
            os.path.join(labs_base, f"{clean_path}.unl"),
            os.path.join(labs_base, f"{clean_path}.unl".replace("//", "/"))
        ]
        # Also recursive search for filename
        base_name = os.path.basename(clean_path)
        if not base_name.endswith(".unl"):
            base_name += ".unl"
        for root, dirs, files in os.walk(labs_base):
            if base_name in files:
                local_candidates.append(os.path.join(root, base_name))

        for cand in local_candidates:
            if os.path.isfile(cand):
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(cand)
                    root = tree.getroot()
                    nodes_dict = {}
                    for n in root.findall(".//node"):
                        nid = n.get("id")
                        nodes_dict[nid] = {
                            "id": nid,
                            "name": n.get("name", f"node-{nid}"),
                            "type": n.get("template", n.get("type", "iol")),
                            "status": 0
                        }
                    if nodes_dict:
                        print(f"  [i] Discovered {len(nodes_dict)} nodes directly from topology file: {cand}")
                        return nodes_dict
                except Exception:
                    pass

    return {}


def start_node(host, lab_path, node_id, tenant, cj, ctx, proto="https", opener=None):
    """Start a single node via session API, path API, or local unl_wrapper."""
    clean_path = lab_path.strip("/")
    start_candidates = [
        f"/api/labs/session/nodes/{node_id}/start",
        f"/api/labs/{clean_path}/nodes/{node_id}/start",
        f"/api/labs/{clean_path}.unl/nodes/{node_id}/start"
    ]
    if clean_path.endswith(".unl"):
        start_candidates.append(f"/api/labs/{clean_path[:-4]}/nodes/{node_id}/start")

    for path in start_candidates:
        result = api_call(host, path, method="GET", cj=cj, ctx=ctx, proto=proto, opener=opener)
        if result.get("status") == "success":
            return True

    # Fallback to local wrapper execution if running on localhost / master
    unl_wrap = "/opt/unetlab/wrappers/unl_wrapper"
    if os.path.isfile(unl_wrap) and os.access(unl_wrap, os.X_OK):
        import subprocess
        try:
            res = subprocess.run([unl_wrap, "-a", "start", "-T", "0", "-D", str(node_id)], capture_output=True, timeout=10)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    return False


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
    cj, ctx, proto, opener = create_session(host, username, password)
    if not cj:
        print("[!] Cannot connect to PNetLab API. Check host/credentials.")
        sys.exit(1)

    print(f"  Target:       {proto}://{host}")
    print(f"  Lab:          {lab_path}")
    print(f"  Heavy nodes:  batch={heavy_batch}, delay={heavy_delay}s between batches")
    print(f"  Medium nodes: batch={medium_batch}, delay={medium_delay}s between batches")
    print(f"  Light nodes:  all concurrent (no delay)")
    if dry_run:
        print("  *** DRY-RUN MODE - No nodes will actually be started ***")
    print("--------------------------------------------------------------------------------")

    nodes_data = get_lab_nodes(host, lab_path, None, cj, ctx, proto=proto, opener=opener)
    if not nodes_data:
        print("[!] Could not retrieve nodes from lab. Ensure lab is open or valid .unl path.")
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
                ok = start_node(host, lab_path, nid, None, cj, ctx, proto=proto, opener=opener)
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
                if os.path.exists(target) or os.path.islink(target):
                    try:
                        os.unlink(target)
                    except Exception:
                        pass
                os.symlink(source, target)
            # Also create alias pnet-bootstorm
            pnet_target = "/usr/local/bin/pnet-bootstorm"
            if not os.path.exists(pnet_target) or os.path.realpath(pnet_target) != source:
                if os.path.exists(pnet_target) or os.path.islink(pnet_target):
                    try:
                        os.unlink(pnet_target)
                    except Exception:
                        pass
                os.symlink(source, pnet_target)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Azam-Pnet Anti-Bootstorm Staggered Node Startup Engine"
    )
    default_host = os.environ.get("AZAM_HOST", "127.0.0.1")
    parser.add_argument("--host", default=default_host,
                        help=f"PNetLab master IP or hostname (default: {default_host})")
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
