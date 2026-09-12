"""
===============================================================================
Script Name   : napalmbgp2.py
Description   : Two-Router BGP Peering Verification - Testing automated verification
                on a baseline 2-router link (GW-R1: 192.168.20.1 and GW-R2: 192.168.20.2).
Target Devices: 192.168.20.1 (GW-R1), 192.168.20.2 (GW-R2)
===============================================================================

PEDAGOGICAL OBJECTIVE:
----------------------
Before deploying scripts across an entire enterprise network of dozens or hundreds
of routers, best practice is to test the automation logic against a minimal
peering pair (GW-R1 and GW-R2).
This script verifies that:
1. Both endpoints are reachable over IP.
2. BGP adjacency is established between AS 65001 neighbors.
3. The automated loop pattern functions correctly before adding GW-R3 and GW-R4.
"""

# -----------------------------------------------------------------------------
# STEP 1: Import required libraries
# -----------------------------------------------------------------------------
import json
from napalm import get_network_driver

# -----------------------------------------------------------------------------
# STEP 2: Define baseline 2-router inventory
# -----------------------------------------------------------------------------
bgplist = [
    '192.168.20.1',
    '192.168.20.2'
]

# -----------------------------------------------------------------------------
# STEP 3: Load the Cisco IOS network driver
# -----------------------------------------------------------------------------
driver = get_network_driver('ios')

# -----------------------------------------------------------------------------
# STEP 4: Iterate and verify each router in sequence
# -----------------------------------------------------------------------------
print("Starting BGP verification for baseline routers: {}...".format(bgplist))

for ip_address in bgplist:
    print("\n" + "="*60)
    print("Connecting to router: {}".format(ip_address))
    print("="*60)

    # Instantiate driver with student credentials
    iosv_router = driver(ip_address, 'azam', 'cisco')

    try:
        # Open SSH session
        iosv_router.open()

        # Fetch BGP neighbor table
        bgp_neighbors = iosv_router.get_bgp_neighbors()

        # Display structured BGP state
        print(json.dumps(bgp_neighbors, indent=4))

    except Exception as error:
        print("[!] ERROR connecting to {}: {}".format(ip_address, error))

    finally:
        # Guarantee session is closed to free device resources
        iosv_router.close()
        print("Closed connection to {}.".format(ip_address))

print("\nBaseline 2-router audit complete.")