"""
===============================================================================
Script Name   : napalmbgp2_a.py
Description   : Full 4-Router BGP Network Audit - Auditing BGP relationships
                across an extended multi-AS topology (AS 65001 and AS 65002).
Target Devices: 17.1.1.1 (R1), 17.1.1.2 (R2), 8.8.8.2 (R3), 15.1.1.2 (R4)
===============================================================================

TOPOLOGY & NETWORKING CONTEXT:
-------------------------------
In this larger topology:
- R1 (17.1.1.1) and R2 (17.1.1.2) are in Autonomous System 65001 (iBGP peering).
- R2 (8.8.8.1) peers with R3 (8.8.8.2) across AS boundaries (eBGP: AS 65001 <-> AS 65002).
- R3 (15.1.1.1) peers with R4 (15.1.1.2) within AS 65002 (iBGP peering).

Students can observe how NAPALM cleanly exposes differences in:
- `remote_as` (matching local AS for iBGP, differing for eBGP)
- Peering state (`is_up`: True/False)
- Accepted prefix counts propagated end-to-end.
"""

# -----------------------------------------------------------------------------
# STEP 1: Import required modules
# -----------------------------------------------------------------------------
import json
from napalm import get_network_driver

# -----------------------------------------------------------------------------
# STEP 2: Define full 4-router inventory
# -----------------------------------------------------------------------------
bgplist = [
    '17.1.1.1',   # R1 (AS 65001)
    '17.1.1.2',   # R2 (AS 65001)
    '8.8.8.2',    # R3 (AS 65002)
    '15.1.1.2'    # R4 (AS 65002)
]

# -----------------------------------------------------------------------------
# STEP 3: Load Cisco IOS driver
# -----------------------------------------------------------------------------
driver = get_network_driver('ios')

# -----------------------------------------------------------------------------
# STEP 4: Iterate through all routers in the topology
# -----------------------------------------------------------------------------
print("Starting full network BGP audit across {} routers...".format(len(bgplist)))

for ip_address in bgplist:
    print("\n" + "="*65)
    print("Connecting to router: {}".format(ip_address))
    print("="*65)

    # Initialize device connection object
    iosv_router = driver(ip_address, 'azam', 'cisco')

    try:
        # Open SSH session to the current router
        iosv_router.open()

        # Query BGP neighbor table
        bgp_neighbors = iosv_router.get_bgp_neighbors()

        # Pretty-print formatted JSON output
        print(json.dumps(bgp_neighbors, indent=4))

    except Exception as error:
        # Gracefully handle unreachable nodes or bad routes
        print("[!] ERROR: Unable to query router {}: {}".format(ip_address, error))

    finally:
        # Ensure session is always terminated cleanly
        iosv_router.close()
        print("Finished audit for {} (connection closed).".format(ip_address))

print("\nFull network BGP audit completed.")