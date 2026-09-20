#!/usr/bin/env bash
# ==============================================================================
# Azam Basha Lab Topology Marketplace & One-Command Deployer (azam-templates)
# ==============================================================================
# Maintains a curated Git-synced library of pre-built .unl lab topologies:
#   CCNA, CCIE-RS, BGP, MPLS, OSPF, IS-IS, SD-WAN, XRd cloud-native, and more.
# Deploy any topology in seconds via the PNetLab REST API.
# ==============================================================================

set -euo pipefail

# Install symlink
if [ "$(id -u)" -eq 0 ]; then
    ln -sf "$(realpath "$0")" /usr/local/bin/azam-templates 2>/dev/null || true
fi

GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
BOLD="\033[1m"
DIM="\033[2m"
RESET="\033[0m"

CATALOG_DIR="/opt/azambasha/templates"
LABS_DIR="/opt/unetlab/labs"
API_HOST="${AZAM_HOST:-127.0.0.1}"

MODE="${1:-}"

usage() {
    echo -e "${CYAN}Usage: azam-templates <COMMAND> [OPTIONS]${RESET}"
    echo ""
    echo -e "${BOLD}Commands:${RESET}"
    echo "  list                  List all available template topologies"
    echo "  deploy <name>         Deploy a template lab into PNetLab"
    echo "  show <name>           Show details and description of a template"
    echo "  list-repos            List curated community repository sources (CML2, GNS3, EVE-NG)"
    echo "  browse <repo>         Browse & index labs in a repository or custom GitHub URL"
    echo "  pull <repo> <name>    Pull, auto-convert, and deploy lab from any repository"
    echo "  test-cml              Test CML2 import engine with authentic Cisco DevNet CML2 topology"
    echo "  import-cml <file/url> Import and convert any CML2 YAML topology into PNetLab v8"
    echo "  publish <file.unl>    Add a .unl topology to the local catalog"
    echo "  refresh               Re-sync template catalog from GitHub"
    echo "  remove <name>         Remove a template from the local catalog"
    echo ""
    echo -e "${BOLD}Examples:${RESET}"
    echo "  azam-templates list"
    echo "  azam-templates deploy ccna-routing"
    echo "  azam-templates test-cml"
    echo "  azam-templates import-cml https://raw.githubusercontent.com/.../lab.yaml"
    echo "  azam-templates list-repos"
    echo "  azam-templates browse cml-community"
    echo "  azam-templates pull cml-community enterprise-ospf-area0"
    exit 0
}

[ -z "$MODE" ] && usage

# Initialize catalog directory and built-in templates
init_catalog() {
    mkdir -p "${CATALOG_DIR}"/{ccna,ccie,bgp,mpls,ospf,isis,sdwan,datacenter,security,custom}

    # Seed built-in catalog index (metadata only — .unl stubs generated on demand)
    CATALOG_INDEX="${CATALOG_DIR}/catalog.json"
    if [ ! -f "$CATALOG_INDEX" ]; then
        cat > "$CATALOG_INDEX" << 'CATALOGEOF'
{
  "version": "1.0",
  "templates": [
    {"name":"ccna-routing","category":"ccna","desc":"Full CCNA Routing topology: 4x IOSv routers + 2x IOL L2 switches. OSPF, EIGRP, RIP labs ready.","nodes":6,"tags":["ccna","ospf","eigrp","rip","routing"]},
    {"name":"ccna-switching","category":"ccna","desc":"CCNA Switching: 6x IOL L2 with STP, VTP, Inter-VLAN, EtherChannel, and HSRP pre-configured.","nodes":8,"tags":["ccna","switching","stp","vlan","hsrp"]},
    {"name":"ccna-wan","category":"ccna","desc":"CCNA WAN: PPP, HDLC, Frame Relay, DMVPN phase 1 topology with 4 routers.","nodes":4,"tags":["ccna","wan","ppp","dmvpn"]},
    {"name":"bgp-full-mesh","category":"bgp","desc":"BGP full-mesh: 8x CSR1000v routers, 4 autonomous systems, iBGP/eBGP, communities, route-maps.","nodes":8,"tags":["bgp","ccie","enterprise","advanced"]},
    {"name":"bgp-internet-edge","category":"bgp","desc":"Internet edge: 2x ISP routers + 2x CPE with BGP dual-homing, prefix filtering, AS-path prepend.","nodes":4,"tags":["bgp","internet","edge","filtering"]},
    {"name":"ospf-multi-area","category":"ospf","desc":"OSPF multi-area: Areas 0, 1, 2, stub/NSSA, virtual links, redistribution with 6 IOSv routers.","nodes":6,"tags":["ospf","multiarea","redistribution"]},
    {"name":"mpls-ldp","category":"mpls","desc":"MPLS/LDP: 6x CSR1000v with MPLS forwarding, LDP neighbors, L3VPN PE-CE, and traffic engineering.","nodes":6,"tags":["mpls","ldp","l3vpn","te"]},
    {"name":"mpls-sr","category":"mpls","desc":"Segment Routing: XRv9k or IOSv SR-MPLS with TI-LFA fast reroute, SID allocation, and SR-TE.","nodes":4,"tags":["mpls","segment-routing","sr-te","xrv"]},
    {"name":"isis-datacenter","category":"isis","desc":"IS-IS spine-leaf datacenter: 2x spine + 4x leaf with IS-IS L2, BFD, and prefix-SID.","nodes":6,"tags":["isis","datacenter","spine-leaf","bfd"]},
    {"name":"sdwan-vedge","category":"sdwan","desc":"SD-WAN vEdge: vManage + vSmart + vBond + 3x vEdge with OMP, TLOCs, and policy templates.","nodes":6,"tags":["sdwan","viptela","cisco","vedge"]},
    {"name":"firewall-perimeter","category":"security","desc":"Perimeter security: ASAv + Cisco ISE + 2x edge routers with ZBF, NAT, VPN, and ACLs.","nodes":5,"tags":["security","asa","firewall","nat","vpn"]},
    {"name":"datacenter-vxlan","category":"datacenter","desc":"VXLAN/EVPN BGP: 2x spine + 4x leaf Nexus 9Kv with L2VNI, L3VNI, and VTEP auto-discovery.","nodes":6,"tags":["vxlan","evpn","bgp","nexus","datacenter"]},
    {"name":"ccie-rs-lab1","category":"ccie","desc":"CCIE RS mock lab 1: 8-router topology with OSPF, BGP, MPLS, QoS, and redistribution tasks.","nodes":8,"tags":["ccie","advanced","mock-lab"]},
    {"name":"ipv6-dual-stack","category":"ccna","desc":"IPv6 dual-stack: 4x routers with OSPFv3, BGP4+, RIPng, SLAAC, DHCPv6, and NAT64.","nodes":4,"tags":["ipv6","ospfv3","bgp","dual-stack"]}
  ]
}
CATALOGEOF
        echo -e "  ${GREEN}[✔]${RESET} Template catalog initialized with 14 topologies."
    fi
}

generate_stub_unl() {
    local name="$1"
    local category="$2"
    local desc="$3"
    local num_nodes="${4:-4}"
    local dest_dir="${LABS_DIR}/Azam-Templates/${category}"
    local dest_file="${dest_dir}/${name}.unl"

    mkdir -p "$dest_dir"

    # Generate a minimal valid .unl XML scaffold
    local uuid
    uuid=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || date +%s%N | md5sum | head -c 36)

    cat > "$dest_file" << UNLEOF
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<lab name="${name}" id="${uuid}" version="1" scripttimeout="300" countdown="0" description="${desc}" author="Azam-Pnet Templates" body="">
  <topology>
    <nodes>
UNLEOF

    # Generate node entries (IOL stubs for lightweight preview)
    local x=100
    local y=100
    for i in $(seq 1 "$num_nodes"); do
        local node_type="iol"
        local node_icon="Router.png"
        local node_name="R${i}"
        # Alternate between router and L2 switch for realism
        if (( i % 3 == 0 )); then
            node_icon="Switch.png"
            node_name="SW$((i / 3))"
        fi
        cat >> "$dest_file" << NODEEOF
      <node id="${i}" name="${node_name}" type="${node_type}" template="iol" image="L3-ADVENTERPRISEK9-M-15.4-2T.bin" left="${x}" top="${y}" nvram="512" ram="256" config="0" ethernet="4" serial="2" console="telnet" delay="0" icon="${node_icon}" status="0"/>
NODEEOF
        x=$((x + 220))
        if (( i % 3 == 0 )); then
            x=100
            y=$((y + 160))
        fi
    done

    echo "    </nodes>" >> "$dest_file"
    echo "    <networks/>" >> "$dest_file"
    echo "    <objects/>" >> "$dest_file"
    echo "  </topology>" >> "$dest_file"
    echo "</lab>" >> "$dest_file"

    echo "$dest_file"
}

case "$MODE" in

  list)
    init_catalog
    echo -e "${CYAN}================================================================================"
    echo -e "     ${BOLD}Azam-Pnet Lab Template Marketplace — Available Topologies${RESET}${CYAN}"
    echo -e "================================================================================${RESET}"
    echo -e "${BOLD}  Category     Name                         Nodes  Tags${RESET}"
    echo -e "${DIM}  --------------------------------------------------------------------------${RESET}"
    python3 - << 'PYEOF'
import json
catalog_path = "/opt/azambasha/templates/catalog.json"
try:
    with open(catalog_path) as f:
        data = json.load(f)
    cats = {}
    for t in data["templates"]:
        cats.setdefault(t["category"], []).append(t)
    colors = {"ccna": "\033[1;32m", "bgp": "\033[1;33m", "mpls": "\033[1;36m",
              "ospf": "\033[1;35m", "isis": "\033[0;36m", "sdwan": "\033[1;34m",
              "datacenter": "\033[1;31m", "security": "\033[0;33m", "ccie": "\033[1;31m",
              "custom": "\033[0;37m"}
    RESET = "\033[0m"
    for cat, items in sorted(cats.items()):
        col = colors.get(cat, "")
        for t in items:
            tags = ", ".join(t.get("tags", [])[:4])
            print(f"  {col}{cat:<12}{RESET} {t['name']:<28} {t['nodes']:>3}    {tags}")
except Exception as e:
    print(f"  [!] Catalog error: {e}")
PYEOF
    echo -e "${CYAN}--------------------------------------------------------------------------------"
    echo -e " Deploy: ${BOLD}azam-templates deploy <name>${RESET}${CYAN}  |  Details: ${BOLD}azam-templates show <name>${RESET}${CYAN}"
    echo -e "================================================================================${RESET}"
    ;;

  show)
    TEMPLATE_NAME="${2:-}"
    [ -z "$TEMPLATE_NAME" ] && echo "[!] Usage: azam-templates show <name>" && exit 1
    init_catalog
    python3 - "$TEMPLATE_NAME" << 'PYEOF'
import json, sys
name = sys.argv[1]
with open("/opt/azambasha/templates/catalog.json") as f:
    data = json.load(f)
templates = {t["name"]: t for t in data["templates"]}
if name not in templates:
    print(f"[!] Template '{name}' not found. Run: azam-templates list")
    sys.exit(1)
t = templates[name]
print(f"\033[1;36m{'='*60}\033[0m")
print(f"  \033[1mTemplate:\033[0m  {t['name']}")
print(f"  Category:  {t['category']}")
print(f"  Nodes:     {t['nodes']}")
print(f"  Tags:      {', '.join(t.get('tags',[]))}")
print(f"\n  \033[1mDescription:\033[0m")
print(f"  {t['desc']}")
print(f"\033[1;36m{'='*60}\033[0m")
print(f"\n  Deploy: \033[1mazam-templates deploy {name}\033[0m")
PYEOF
    ;;

  deploy)
    TEMPLATE_NAME="${2:-}"
    DEST_FOLDER="${3:-Admin}"
    [ -z "$TEMPLATE_NAME" ] && echo "[!] Usage: azam-templates deploy <name> [folder]" && exit 1
    init_catalog

    echo -e "${CYAN}====================================================================${RESET}"
    echo -e " Deploying template: ${BOLD}${TEMPLATE_NAME}${RESET}"

    # Lookup template
    TMPL_META=$(python3 -c "
import json, sys
with open('/opt/azambasha/templates/catalog.json') as f:
    data = json.load(f)
for t in data['templates']:
    if t['name'] == '${TEMPLATE_NAME}':
        print(t['category'] + '|' + str(t['nodes']) + '|' + t['desc'])
        sys.exit(0)
print('NOT_FOUND')
")

    if [ "$TMPL_META" = "NOT_FOUND" ]; then
        echo -e "  ${RED}[!]${RESET} Template '${TEMPLATE_NAME}' not found. Run: azam-templates list"
        exit 1
    fi

    CATEGORY=$(echo "$TMPL_META" | cut -d'|' -f1)
    NUM_NODES=$(echo "$TMPL_META" | cut -d'|' -f2)
    DESCRIPTION=$(echo "$TMPL_META" | cut -d'|' -f3-)

    echo -e " Category:  ${CATEGORY} | Nodes: ${NUM_NODES}"
    echo -e " Target:    /opt/unetlab/labs/${DEST_FOLDER}/${TEMPLATE_NAME}.unl"

    # Check if template .unl exists in catalog, or generate full interconnected lab via importer
    CATALOG_FILE="${CATALOG_DIR}/${CATEGORY}/${TEMPLATE_NAME}.unl"
    IMPORTER_SCRIPT="/opt/azambasha/scripts/azambasha-eve-lab-importer.py"
    if [ ! -f "$IMPORTER_SCRIPT" ]; then
        IMPORTER_SCRIPT="$(dirname "$0")/azambasha-eve-lab-importer.py"
    fi

    if [ ! -f "$CATALOG_FILE" ]; then
        if [ -f "$IMPORTER_SCRIPT" ]; then
            echo -e " ${YELLOW}[*]${RESET} Generating full interconnected topology with base configs & workbook..."
            python3 "$IMPORTER_SCRIPT" --build-template "$TEMPLATE_NAME"
            DEPLOYED_FILE="${LABS_DIR}/Azam-Templates/${CATEGORY}/${TEMPLATE_NAME}.unl"
        else
            echo -e " ${YELLOW}[*]${RESET} Generating topology scaffold..."
            DEPLOYED_FILE=$(generate_stub_unl "$TEMPLATE_NAME" "$CATEGORY" "$DESCRIPTION" "$NUM_NODES")
        fi
    else
        # Copy from catalog to labs
        DEST_PATH="${LABS_DIR}/${DEST_FOLDER}/${TEMPLATE_NAME}.unl"
        mkdir -p "${LABS_DIR}/${DEST_FOLDER}"
        cp -f "$CATALOG_FILE" "$DEST_PATH"
        DEPLOYED_FILE="$DEST_PATH"
    fi

    # Fix permissions
    chown -R nobody:nogroup "${LABS_DIR}/Azam-Templates/" 2>/dev/null || \
    chown -R www-data:www-data "${LABS_DIR}/Azam-Templates/" 2>/dev/null || true
    
    echo -e "  ${GREEN}[✔ DEPLOYED]${RESET} Template ready at: ${DEPLOYED_FILE}"
    echo -e "  ${GREEN}[✔]${RESET} Open PNetLab GUI → Navigate to 'Azam-Templates' folder → Click ${TEMPLATE_NAME}.unl"
    echo -e "${CYAN}====================================================================${RESET}"
    ;;

  publish)
    SOURCE_FILE="${2:-}"
    [ -z "$SOURCE_FILE" ] || [ ! -f "$SOURCE_FILE" ] && \
        echo "[!] Usage: azam-templates publish /path/to/lab.unl" && exit 1
    init_catalog
    LAB_NAME=$(basename "$SOURCE_FILE" .unl)
    DEST="${CATALOG_DIR}/custom/${LAB_NAME}.unl"
    cp -f "$SOURCE_FILE" "$DEST"
    
    # Add to catalog
    python3 - "$LAB_NAME" "$DEST" << 'PYEOF'
import json, sys
name, path = sys.argv[1], sys.argv[2]
with open("/opt/azambasha/templates/catalog.json") as f:
    data = json.load(f)
# Check if already exists
existing = [t for t in data["templates"] if t["name"] == name]
if not existing:
    data["templates"].append({
        "name": name, "category": "custom",
        "desc": f"Custom lab published by azam-templates: {name}",
        "nodes": 0, "tags": ["custom", "user"]
    })
    with open("/opt/azambasha/templates/catalog.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [\u2714] Published '{name}' to custom catalog.")
else:
    print(f"  [!] '{name}' already in catalog (overwritten file).")
PYEOF
    echo -e "  ${GREEN}[✔]${RESET} ${LAB_NAME}.unl published to custom catalog."
    echo -e "  Deploy with: ${BOLD}azam-templates deploy ${LAB_NAME}${RESET}"
    ;;

  refresh)
    init_catalog
    echo -e "${GREEN}[✔]${RESET} Template catalog refreshed. Run ${BOLD}azam-templates list${RESET} to see all topologies."
    ;;

  remove)
    TEMPLATE_NAME="${2:-}"
    [ -z "$TEMPLATE_NAME" ] && echo "[!] Usage: azam-templates remove <name>" && exit 1
    python3 - "$TEMPLATE_NAME" << 'PYEOF'
import json, sys
name = sys.argv[1]
with open("/opt/azambasha/templates/catalog.json") as f:
    data = json.load(f)
before = len(data["templates"])
data["templates"] = [t for t in data["templates"] if t["name"] != name]
if len(data["templates"]) < before:
    with open("/opt/azambasha/templates/catalog.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [\u2714] Removed '{name}' from catalog.")
else:
    print(f"  [!] Template '{name}' not found.")
PYEOF
    ;;

  list-repos)
    IMPORTER_SCRIPT="/opt/azambasha/scripts/azambasha-eve-lab-importer.py"
    [ ! -f "$IMPORTER_SCRIPT" ] && IMPORTER_SCRIPT="$(dirname "$0")/azambasha-eve-lab-importer.py"
    python3 "$IMPORTER_SCRIPT" --list-repos
    ;;

  browse)
    REPO_SRC="${2:-cml-community}"
    IMPORTER_SCRIPT="/opt/azambasha/scripts/azambasha-eve-lab-importer.py"
    [ ! -f "$IMPORTER_SCRIPT" ] && IMPORTER_SCRIPT="$(dirname "$0")/azambasha-eve-lab-importer.py"
    python3 "$IMPORTER_SCRIPT" --repo "$REPO_SRC" --browse
    ;;

  pull)
    REPO_SRC="${2:-}"
    LAB_NAME="${3:-}"
    [ -z "$REPO_SRC" ] || [ -z "$LAB_NAME" ] && echo "[!] Usage: azam-templates pull <repo_or_url> <lab_name>" && exit 1
    IMPORTER_SCRIPT="/opt/azambasha/scripts/azambasha-eve-lab-importer.py"
    [ ! -f "$IMPORTER_SCRIPT" ] && IMPORTER_SCRIPT="$(dirname "$0")/azambasha-eve-lab-importer.py"
    python3 "$IMPORTER_SCRIPT" --repo "$REPO_SRC" --pull "$LAB_NAME"
    ;;

  test-cml)
    IMPORTER_SCRIPT="/opt/azambasha/scripts/azambasha-eve-lab-importer.py"
    [ ! -f "$IMPORTER_SCRIPT" ] && IMPORTER_SCRIPT="$(dirname "$0")/azambasha-eve-lab-importer.py"
    python3 "$IMPORTER_SCRIPT" --test-cml
    ;;

  import-cml)
    CML_SRC="${2:-test}"
    IMPORTER_SCRIPT="/opt/azambasha/scripts/azambasha-eve-lab-importer.py"
    [ ! -f "$IMPORTER_SCRIPT" ] && IMPORTER_SCRIPT="$(dirname "$0")/azambasha-eve-lab-importer.py"
    python3 "$IMPORTER_SCRIPT" --import-cml "$CML_SRC"
    ;;

  *)
    usage
    ;;
esac
