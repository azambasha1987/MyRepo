"""
===============================================================================
Script Name   : napalmbgp1.py
Description   : Querying BGP neighbor relationships and peering states on a
                single Cisco router/switch using NAPALM.
Target Device : Cisco Device (192.168.1.105)
Audience      : Network Engineering Students & Automation Beginners
===============================================================================

WHAT IS BGP (Border Gateway Protocol)?
---------------------------------------
BGP is the exterior gateway routing protocol used across the global Internet and
in large enterprise/cloud data centers. It exchanges routing and reachability
information among autonomous systems (AS).

WHY USE NAPALM FOR BGP MONITORING?
----------------------------------
In traditional Cisco IOS CLI, an engineer runs:
    # show ip bgp summary
    # show ip bgp neighbors
Parsing this text output via regular expressions (screen-scraping) is fragile.
NAPALM's `get_bgp_neighbors()` normalizes the BGP state into structured JSON,
giving you:
- Remote Autonomous System (remote_as)
- Peering State ('is_up', uptime, state like 'Established', 'Active', 'Idle')
- Route Telemetry (prefixes received, accepted, and advertised)
"""

# -----------------------------------------------------------------------------
# STEP 1: Import required modules
# -----------------------------------------------------------------------------
import json
from napalm import get_network_driver

# -----------------------------------------------------------------------------
# STEP 2: Initialize Cisco IOS driver and credentials
# -----------------------------------------------------------------------------
driver = get_network_driver('ios')
iosvl2 = driver('192.168.1.105', 'azam', 'cisco')

# -----------------------------------------------------------------------------
# STEP 3: Open SSH session
# -----------------------------------------------------------------------------
print("Connecting to 192.168.1.105 to query BGP status...")
iosvl2.open()

try:
    # -------------------------------------------------------------------------
    # STEP 4: Retrieve BGP neighbor state
    # -------------------------------------------------------------------------
    bgp_neighbors = iosvl2.get_bgp_neighbors()

    # -------------------------------------------------------------------------
    # STEP 5: Pretty-print BGP neighbor data as formatted JSON
    # -------------------------------------------------------------------------
    print("\n" + "="*50)
    print("BGP NEIGHBOR STATE & PEERING TELEMETRY")
    print("="*50)
    print(json.dumps(bgp_neighbors, indent=4))

finally:
    # -------------------------------------------------------------------------
    # STEP 6: Close the session
    # -------------------------------------------------------------------------
    iosvl2.close()
    print("\nSession closed successfully.")