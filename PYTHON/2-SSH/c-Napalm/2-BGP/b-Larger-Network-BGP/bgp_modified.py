"""
===============================================================================
Script Name   : bgp_modified.py
Description   : Streamlined BGP Neighbor Query - Demonstrating targeted getter
                execution to minimize network and router CPU overhead.
Target Device : Cisco Router R2 (17.1.1.2)
Audience      : Network Engineering Students & Automation Beginners
===============================================================================

LESSON: OPTIMIZING AUTOMATION QUERIES
-------------------------------------
In `bgp.py`, we gathered both system facts (`get_facts()`) and BGP data
(`get_bgp_neighbors()`). However, in large-scale monitoring or automated health-checks:
- Fetching unneeded telemetry (like full hardware facts) creates extra latency
  and unnecessary CPU load on target routers.
- This script intentionally comments out `get_facts()` to demonstrate selective,
  high-performance polling focused strictly on BGP peering status.
"""

# -----------------------------------------------------------------------------
# STEP 1: Import required libraries
# -----------------------------------------------------------------------------
import json
from napalm import get_network_driver

# -----------------------------------------------------------------------------
# STEP 2: Configure Cisco IOS driver and credentials
# -----------------------------------------------------------------------------
driver = get_network_driver('ios')
iosv = driver('17.1.1.2', 'azam', 'cisco')

# -----------------------------------------------------------------------------
# STEP 3: Establish SSH connection
# -----------------------------------------------------------------------------
print("Connecting to router 17.1.1.2 for targeted BGP inspection...")
iosv.open()

try:
    # -------------------------------------------------------------------------
    # (Optional) System facts are omitted to optimize polling performance
    # -------------------------------------------------------------------------
    # ios_output = iosv.get_facts()
    # print(json.dumps(ios_output, indent=4))

    # -------------------------------------------------------------------------
    # STEP 4: Query only the BGP neighbor information
    # -------------------------------------------------------------------------
    print("\n" + "="*50)
    print("BGP NEIGHBOR STATE (Targeted Telemetry)")
    print("="*50)
    ios_output2 = iosv.get_bgp_neighbors()
    print(json.dumps(ios_output2, indent=4))

finally:
    # -------------------------------------------------------------------------
    # STEP 5: Safely close the SSH session
    # -------------------------------------------------------------------------
    iosv.close()
    print("\nConnection closed successfully.")
