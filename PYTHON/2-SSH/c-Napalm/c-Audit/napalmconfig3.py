"""
===============================================================================
Script Name   : napalmconfig3.py
Description   : Multi-Stage Configuration Audit - Applying and auditing multiple
                independent configuration files (ACL and OSPF) sequentially.
Target Device : Cisco Switch/Router (192.168.1.105)
===============================================================================

MULTI-STAGE CONFIGURATION AUDITS:
---------------------------------
In network operations, changes are often separated into modular domains:
- Security policies (ACLs, firewall rules)
- Routing protocols (OSPF, BGP)
- Infrastructure services (NTP, SNMP, AAA)

This script demonstrates applying two separate configuration files in sequence
during a single management session:
1. Stage 1: Load and audit `ACL1.cfg` -> Compare -> Commit or Discard.
2. Stage 2: Load and audit `ospf1.cfg` -> Compare -> Commit or Discard.

Each stage operates independently: if the ACL is already compliant, only the
missing OSPF configuration is committed (or vice versa).
"""

# -----------------------------------------------------------------------------
# STEP 1: Import NAPALM driver loader
# -----------------------------------------------------------------------------
from napalm import get_network_driver

# -----------------------------------------------------------------------------
# STEP 2: Configure driver and target device
# -----------------------------------------------------------------------------
driver = get_network_driver('ios')
iosvl2 = driver('192.168.1.105', 'azam', 'cisco')

# -----------------------------------------------------------------------------
# STEP 3: Open SSH session
# -----------------------------------------------------------------------------
print("Accessing 192.168.1.105...")
iosvl2.open()

try:
    # =========================================================================
    # STAGE 1: Audit & Apply Access Control List (ACL1.cfg)
    # =========================================================================
    print("\n--- [Stage 1] Auditing ACL Configuration (ACL1.cfg) ---")
    iosvl2.load_merge_candidate(filename='ACL1.cfg')

    diffs = iosvl2.compare_config()
    if len(diffs) > 0:
        print("[+] ACL differences found! Proposed configuration diff:")
        print(diffs)
        print("Committing ACL changes...")
        iosvl2.commit_config()
        print("ACL commit successful.")
    else:
        print("[*] No ACL changes required (device already compliant).")
        iosvl2.discard_config()

    # =========================================================================
    # STAGE 2: Audit & Apply Routing Configuration (ospf1.cfg)
    # =========================================================================
    print("\n--- [Stage 2] Auditing OSPF Routing Configuration (ospf1.cfg) ---")
    iosvl2.load_merge_candidate(filename='ospf1.cfg')

    # Re-calculate diff specifically for OSPF candidate
    diffs = iosvl2.compare_config()
    if len(diffs) > 0:
        print("[+] OSPF differences found! Proposed configuration diff:")
        print(diffs)
        print("Committing OSPF changes...")
        iosvl2.commit_config()
        print("OSPF commit successful.")
    else:
        print("[*] No OSPF changes required (device already compliant).")
        iosvl2.discard_config()

finally:
    # -------------------------------------------------------------------------
    # STEP 4: Close session
    # -------------------------------------------------------------------------
    iosvl2.close()
    print("\nSession closed cleanly.")