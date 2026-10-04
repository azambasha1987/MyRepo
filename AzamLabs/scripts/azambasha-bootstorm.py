#!/usr/bin/env python3
"""
==============================================================================
Azam Basha Anti-Bootstorm Staggered Node Startup Engine (azam-bootstorm.py)
==============================================================================
Prevents CPU/IO bootstorm when starting large multi-vendor topologies.
Uses a multi-tier startup pipeline (REST API, brokerd socket, unl_wrapper)
and staggers node boot order by weight:
  Heavy (C8000v, XRd, Windows 11, vMX)  -> first, 2-3 per batch, 18s apart
  Medium (CSR1000v, vEOS, IOSvL2, Forti) -> second, 4 per batch, 10s apart
  Light (IOL, VPCS, Alpine, Docker)      -> last, unlimited concurrent
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
    "c8000v", "c8k", "cat8k", "cat9k", "c9300", "c9500", "c9800",
    "xrd", "xrv9k", "xrv", "win", "win2022", "win11", "win2019", "win10", "win2016", "win7",
    "vmx", "vqfxre", "vqfxpfe", "vqfx", "nxosv9k", "nxosv", "nxos", "nexus",
    "asa", "asav", "ftdv", "vcenter", "esxi", "bigip", "ixia", "pan", "paloalto", "nsx"
}

MEDIUM_TEMPLATES = {
    "csr1000vng", "csr1000v", "csr", "veos", "viosl2", "vios-l2", "vios", "iosvl2", "iosv-l2", "iosv",
    "routeros", "mikrotik", "cpsg", "huaweiusg6kv", "fortios", "fortigate", "firepower6",
    "sonicwall", "timos", "iol-xe", "sros", "vyos", "pfsense", "cumulus", "arista",
    "dcsw", "switch", "distribution"
}

# Anything else = light (IOL, Alpine, Ubuntu, dynamips, docker, vpcs)


def get_node_weight(token: str) -> str:
    """Return 'heavy', 'medium', or 'light' based on node token (template/image/name)."""
    if not token:
        return "light"
    t = str(token).lower().strip()
    t_clean = os.path.basename(t).split("-")[0].split("_")[0].split(".")[0]

    # Exact match on cleaned token
    if t_clean in HEAVY_TEMPLATES:
        return "heavy"
    if t_clean in MEDIUM_TEMPLATES:
        return "medium"

    # Prefix match
    for h in HEAVY_TEMPLATES:
        if t_clean.startswith(h) or t.startswith(h):
            return "heavy"
    for m in MEDIUM_TEMPLATES:
        if t_clean.startswith(m) or t.startswith(m):
            return "medium"

    return "light"


def classify_node(node: dict) -> tuple:
    """
    Classify node into (weight, display_type).
    Inspects template, image, name, and type in order of specificity.
    """
    template = str(node.get("template") or "").strip().lower()
    image = str(node.get("image") or "").strip().lower()
    ntype = str(node.get("type") or "").strip().lower()
    name = str(node.get("name") or "").strip().lower()

    # 1. Determine most descriptive display label
    if template and template != "qemu":
        display_type = template
    elif image:
        display_type = os.path.basename(image).split("-")[0].split("_")[0]
    elif ntype and ntype != "qemu":
        display_type = ntype
    elif name and any(name.startswith(p) for p in ("dcsw", "sw", "rtr", "server")):
        display_type = f"{ntype or 'node'}/{name.rstrip('0123456789-_')}"
    else:
        display_type = ntype or "qemu"

    # 2. Check for heavy candidates
    for cand in [template, image, name, ntype]:
        if cand and get_node_weight(cand) == "heavy":
            return "heavy", display_type

    # 3. Check for medium candidates
    for cand in [template, image, name, ntype]:
        if cand and get_node_weight(cand) == "medium":
            return "medium", display_type

    # 4. Default to light
    return "light", display_type


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
    """Make an authenticated API call to PNetLab with robust JSON error unwrapping."""
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
            resp_bytes = resp.read()
            if not resp_bytes:
                return {"status": "success", "code": resp.status}
            try:
                return json.loads(resp_bytes.decode("utf-8"))
            except Exception:
                return {"status": "success", "code": resp.status, "raw": resp_bytes.decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        err_msg = f"HTTP Error {e.code}: {e.reason}"
        try:
            err_bytes = e.read()
            if err_bytes:
                err_json = json.loads(err_bytes.decode("utf-8"))
                if isinstance(err_json, dict):
                    err_json.setdefault("status", "fail")
                    err_json.setdefault("code", e.code)
                    return err_json
        except Exception:
            pass
        return {"status": "fail", "code": e.code, "message": err_msg}
    except Exception as e:
        return {"status": "fail", "message": str(e)}


def resolve_lab_disk_path(lab_path: str) -> str:
    """Resolve the authoritative absolute path to the .unl file on disk."""
    clean = lab_path.strip("/")
    if not clean.endswith(".unl"):
        clean += ".unl"

    labs_base = "/opt/unetlab/labs"

    # 1. If absolute path under labs_base provided directly
    if lab_path.startswith(labs_base):
        return lab_path if lab_path.endswith(".unl") else f"{lab_path}.unl"

    # 2. Direct path under labs_base
    direct = f"{labs_base}/{clean}"
    if os.path.isfile(direct):
        return direct

    # 3. Search recursively under labs_base for the filename
    if os.path.isdir(labs_base):
        target_name = os.path.basename(clean)
        for root, _, files in os.walk(labs_base):
            if target_name in files:
                return os.path.join(root, target_name).replace("\\", "/")

    # 4. Fallback to standard path (normalized with forward slashes for Linux)
    return f"{labs_base}/{clean}"


def open_lab_session(host, lab_path, cj, ctx, proto="https", opener=None):
    """
    Ensure the lab is actively loaded into the PNetLab session state ($_SESSION['lab']).
    Without an active session, /api/labs/session/nodes/{id}/start will fail with code 412.
    """
    clean = lab_path.strip("/")
    clean_no_ext = clean[:-4] if clean.endswith(".unl") else clean
    clean_with_ext = clean if clean.endswith(".unl") else f"{clean}.unl"

    # 1. Check if lab is already loaded in current session
    sess_check = api_call(host, "/api/labs/session", method="GET", cj=cj, ctx=ctx, proto=proto, opener=opener)
    if sess_check.get("status") == "success" and sess_check.get("data"):
        data = sess_check.get("data")
        sess_name = data.get("name", "") or data.get("file", "")
        return True, f"Session already active ({sess_name})"

    # 2. Attempt to open/load lab into session via candidate routes
    open_candidates = [
        (f"/api/labs/{clean_with_ext}", "GET", None),
        (f"/api/labs/{clean_no_ext}", "GET", None),
        (f"/api/labs/{lab_path}", "GET", None),
        ("/api/labs/session", "POST", {"path": f"/{clean_with_ext}"}),
        ("/api/labs/session", "POST", {"path": clean_with_ext}),
        ("/api/labs/session", "POST", {"path": f"/{clean_no_ext}"}),
        ("/api/labs/session", "POST", {"lab": clean_with_ext}),
        ("/api/labs/session", "POST", {"lab": clean_no_ext}),
    ]

    for path, method, data in open_candidates:
        res = api_call(host, path, method=method, data=data, cj=cj, ctx=ctx, proto=proto, opener=opener)
        if res.get("status") == "success" or res.get("code") == 200:
            return True, f"Active via {path}"

    return False, "Could not initialize session state via REST"


def get_lab_nodes(host, lab_path, tenant, cj, ctx, proto="https", opener=None):
    """Retrieve all nodes from a running lab session or lab file path."""
    clean = lab_path.strip("/")
    clean_no_ext = clean[:-4] if clean.endswith(".unl") else clean
    clean_with_ext = clean if clean.endswith(".unl") else f"{clean}.unl"

    candidates = [
        f"/api/labs/{clean_no_ext}/nodes",
        f"/api/labs/{clean_with_ext}/nodes",
        "/api/labs/session/nodes",
        f"/api/labs/{clean}/nodes"
    ]

    for path in candidates:
        result = api_call(host, path, cj=cj, ctx=ctx, proto=proto, opener=opener)
        if result.get("status") == "success" and result.get("data"):
            data = result.get("data")
            if isinstance(data, dict):
                return data
            elif isinstance(data, list):
                return {str(item.get("id", idx)): item for idx, item in enumerate(data)}

    # Direct local file discovery fallback if running locally
    lab_file = resolve_lab_disk_path(lab_path)
    if os.path.isfile(lab_file):
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(lab_file)
            root = tree.getroot()
            nodes_dict = {}
            for n in root.findall(".//node"):
                nid = n.get("id")
                nodes_dict[nid] = {
                    "id": nid,
                    "name": n.get("name", f"node-{nid}"),
                    "type": n.get("type", "qemu"),
                    "template": n.get("template", ""),
                    "image": n.get("image", ""),
                    "status": 0
                }
            if nodes_dict:
                print(f"  [i] Discovered {len(nodes_dict)} nodes directly from topology file: {lab_file}")
                return nodes_dict
        except Exception:
            pass

    return {}


def start_node_broker(node_id, lab_disk_path):
    """Start node via /run/pnetlab/broker.sock if running locally on PNetLab host."""
    sock_path = "/run/pnetlab/broker.sock"
    if not os.path.exists(sock_path):
        return False, "Broker socket not found"
    try:
        import socket
        for session_id in [1, 0]:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(15)
            s.connect(sock_path)
            payload = {
                "verb": "wrapper",
                "args": {
                    "action": "start",
                    "tenant": 0,
                    "session": session_id,
                    "node": int(node_id),
                    "lab": lab_disk_path
                }
            }
            s.sendall(json.dumps(payload).encode("utf-8") + b"\n")
            raw = b""
            while not raw.endswith(b"\n"):
                chunk = s.recv(4096)
                if not chunk:
                    break
                raw += chunk
            s.close()
            if raw:
                res = json.loads(raw.decode("utf-8"))
                if res.get("ok") or res.get("rc") == 0:
                    return True, "brokerd"
        return False, f"brokerd rc={res.get('rc')}: {res.get('err', '')}"
    except Exception as e:
        return False, f"brokerd error: {e}"


def start_node_wrapper(node_id, lab_disk_path):
    """Start node directly via /opt/unetlab/wrappers/unl_wrapper with full parameters."""
    unl_wrap = "/opt/unetlab/wrappers/unl_wrapper"
    if not (os.path.isfile(unl_wrap) and os.access(unl_wrap, os.X_OK)):
        return False, "unl_wrapper not accessible"

    import subprocess
    # unl_wrapper requires -a start -T <tenant> -S <session> -D <node> -F <lab_path>
    attempts = [
        [unl_wrap, "-a", "start", "-T", "0", "-S", "1", "-D", str(node_id), "-F", lab_disk_path],
        [unl_wrap, "-a", "start", "-T", "0", "-S", "0", "-D", str(node_id), "-F", lab_disk_path],
        [unl_wrap, "-a", "start", "-T", "1", "-S", "1", "-D", str(node_id), "-F", lab_disk_path],
        [unl_wrap, "-a", "start", "-T", "0", "-D", str(node_id), "-F", lab_disk_path],
    ]
    last_err = ""
    for argv in attempts:
        try:
            res = subprocess.run(argv, capture_output=True, timeout=20)
            if res.returncode == 0:
                return True, "unl_wrapper"
            last_err = res.stderr.decode("utf-8", errors="replace").strip() or res.stdout.decode("utf-8", errors="replace").strip()
        except Exception as e:
            last_err = str(e)

    return False, f"unl_wrapper: {last_err or 'rc!=0'}"


def start_node(host, lab_path, node_id, tenant, cj, ctx, proto="https", opener=None, lab_disk_path=None):
    """
    Start a single node using a resilient 3-tier startup pipeline:
      Tier 1: Authenticated REST API (/api/labs/session/nodes/{id}/start)
      Tier 2: Broker Daemon Unix Socket (/run/pnetlab/broker.sock)
      Tier 3: Native unl_wrapper CLI (-a start -T 0 -S 1 -D {id} -F {lab_file})
    """
    clean = lab_path.strip("/")
    clean_no_ext = clean[:-4] if clean.endswith(".unl") else clean
    clean_with_ext = clean if clean.endswith(".unl") else f"{clean}.unl"

    api_errors = []

    # ── Tier 1: PNetLab REST API ──────────────────────────────────────────────
    start_candidates = [
        f"/api/labs/session/nodes/{node_id}/start",
        f"/api/labs/session/nodes/{node_id}/start/0",
        f"/api/labs/session/nodes/{node_id}/start?html5=0",
        f"/api/labs/{clean_with_ext}/nodes/{node_id}/start",
        f"/api/labs/{clean_no_ext}/nodes/{node_id}/start",
    ]

    for path in start_candidates:
        result = api_call(host, path, method="GET", cj=cj, ctx=ctx, proto=proto, opener=opener)
        if result.get("status") == "success" or result.get("code") == 200:
            return True, "API"
        err = result.get("message") or result.get("error")
        if err:
            api_errors.append(str(err))

    # If running locally or on localhost, proceed to local tiers
    is_local = host in ("127.0.0.1", "localhost", "::1") or os.environ.get("AZAM_LOCAL", "0") == "1"
    if not is_local:
        first_err = api_errors[0] if api_errors else "API rejected start"
        return False, first_err

    if not lab_disk_path:
        lab_disk_path = resolve_lab_disk_path(lab_path)

    # ── Tier 2: Broker Daemon Socket (/run/pnetlab/broker.sock) ───────────────
    ok_broker, msg_broker = start_node_broker(node_id, lab_disk_path)
    if ok_broker:
        return True, "brokerd"

    # ── Tier 3: Direct unl_wrapper Execution ──────────────────────────────────
    ok_wrap, msg_wrap = start_node_wrapper(node_id, lab_disk_path)
    if ok_wrap:
        return True, "unl_wrapper"

    # Aggregate failure detail
    err_summary = api_errors[0] if api_errors else (msg_broker if "not found" not in msg_broker else msg_wrap)
    return False, err_summary


def run_bootstorm(host, lab_path, username, password,
                  heavy_batch=2, heavy_delay=18,
                  medium_batch=4, medium_delay=10,
                  dry_run=False):
    """
    Staggered boot orchestration:
      1. Authenticate to PNetLab API
      2. Verify and activate lab in session state
      3. Classify each node into heavy / medium / light
      4. Start in batches with configurable delays across multi-tier engine
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

    lab_disk_path = resolve_lab_disk_path(lab_path)
    if os.path.isfile(lab_disk_path):
        print(f"  [i] Topology file verified: {lab_disk_path}")

    # Activate lab in session state
    sess_ok, sess_msg = open_lab_session(host, lab_path, cj, ctx, proto=proto, opener=opener)
    if sess_ok:
        print(f"  [✔] Lab session initialized: {sess_msg}")
    else:
        print(f"  [⚠] Lab session notice: {sess_msg} (will use multi-tier fallbacks)")

    nodes_data = get_lab_nodes(host, lab_path, None, cj, ctx, proto=proto, opener=opener)
    if not nodes_data:
        print("[!] Could not retrieve nodes from lab. Ensure lab is open or valid .unl path.")
        sys.exit(1)

    # Classify nodes
    heavy_nodes, medium_nodes, light_nodes = [], [], []
    for nid, node in nodes_data.items():
        weight, display_type = classify_node(node)
        entry = {
            "id": nid,
            "name": node.get("name", f"node-{nid}"),
            "type": display_type,
            "raw_node": node,
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
        batch_size = heavy_batch if label == "HEAVY" else medium_batch
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
                ok, detail = start_node(host, lab_path, nid, None, cj, ctx, proto=proto, opener=opener, lab_disk_path=lab_disk_path)
                if ok:
                    print(f"✔ ({detail})")
                    started_ok += 1
                else:
                    print(f"✘ FAILED ({detail})")
                    started_fail += 1

            # Stagger within batch
            if (i + 1) % batch_size == 0 and i < len(batch) - 1:
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
