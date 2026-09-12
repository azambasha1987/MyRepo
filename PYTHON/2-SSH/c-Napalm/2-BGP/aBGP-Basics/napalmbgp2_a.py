"""
===============================================================================
Script Name   : napalmbgp2_a.py
Description   : Multi-Device BGP Auditor - Iterating through an inventory of routers
                to collect and verify BGP peering health across a multi-hop topology.
Target Devices: 192.168.20.1, 192.168.20.2, 100.100.100.2, 10.10.0.2
===============================================================================

KEY CONCEPTS TAUGHT IN THIS SCRIPT:
1. Inventory Lists:
   - Defining a Python list of device IP addresses to perform automated fleet-wide audits.
2. Iterative Connection Management:
   - Creating, opening, querying, and closing a session for each router in sequence.
3. Fault Tolerance & Exception Handling:
   - In production, if one router is offline or has invalid credentials, your script
     should NOT crash! Using try/except/finally ensures errors on one device are
     reported while allowing the script to continue auditing the remaining routers.
"""

# -----------------------------------------------------------------------------
# STEP 1: Import required modules
# -----------------------------------------------------------------------------
import json
from napalm import get_network_driver

# -----------------------------------------------------------------------------
# STEP 2: Define the target device inventory (BGP routers in topology)
# -----------------------------------------------------------------------------
bgplist = [
    '192.168.20.1',
    '192.168.20.2',
    '100.100.100.2',
    '10.10.0.2'
]

# -----------------------------------------------------------------------------
# STEP 3: Load the driver class
# -----------------------------------------------------------------------------
driver = get_network_driver('ios')

# -----------------------------------------------------------------------------
# STEP 4: Iterate through each router in the inventory list
# -----------------------------------------------------------------------------
print("Starting multi-device BGP audit across {} routers...".format(len(bgplist)))

for ip_address in bgplist:
    print("\n" + "="*60)
    print("Connecting to router: {}".format(ip_address))
    print("="*60)

    # Initialize device connection object
    iosv_router = driver(ip_address, 'azam', 'cisco')

    try:
        # Open SSH session to current router
        iosv_router.open()

        # Retrieve structured BGP neighbor information
        bgp_neighbors = iosv_router.get_bgp_neighbors()

        # Display structured output
        print(json.dumps(bgp_neighbors, indent=4))

    except Exception as error:
        # If a router fails (unreachable, timeout, auth failure), print error and continue
        print("[!] ERROR connecting to or querying {}: {}".format(ip_address, error))

    finally:
        # Ensure connection is closed even if an exception occurred during query
        iosv_router.close()
        print("Completed audit for {} (session closed).".format(ip_address))

print("\nAll routers in inventory have been processed.")