"""
===============================================================================
Script Name   : bgp.py
Description   : Connecting to an intermediate BGP router (Inhouse-ISP: 192.168.1.111) to inspect
                both device identity (facts) and active BGP peering sessions.
Target Device : Cisco Router Inhouse-ISP (192.168.1.111)
===============================================================================

KEY LEARNING OBJECTIVES:
1. Combining Getters in a Single Session:
   - Rather than opening multiple SSH sessions, an automation script should open
     one session, execute all required inspection tasks (`get_facts()`,
     `get_bgp_neighbors()`), and then cleanly close the connection.
2. Python 3 Syntax Compliance:
   - Python 3 mandates parentheses for print statements: `print(...)`.
3. JSON Formatting:
   - Both device metadata and routing state are serialized into clean, readable JSON.
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
iosv = driver('192.168.1.111', 'azam', 'cisco')

# -----------------------------------------------------------------------------
# STEP 3: Establish SSH connection
# -----------------------------------------------------------------------------
print("Connecting to router 192.168.1.111...")
iosv.open()

try:
    # -------------------------------------------------------------------------
    # STEP 4: Retrieve and display general router facts
    # -------------------------------------------------------------------------
    print("\n" + "="*50)
    print("1. ROUTER METADATA & SYSTEM FACTS")
    print("="*50)
    ios_output = iosv.get_facts()
    print(json.dumps(ios_output, indent=4))

    # -------------------------------------------------------------------------
    # STEP 5: Retrieve and display BGP neighbor details
    # -------------------------------------------------------------------------
    # (Fixed: converted Python 2 "print ios_output2" to Python 3 with JSON formatting)
    print("\n" + "="*50)
    print("2. BGP NEIGHBOR RELATIONSHIPS")
    print("="*50)
    ios_output2 = iosv.get_bgp_neighbors()
    print(json.dumps(ios_output2, indent=4))

finally:
    # -------------------------------------------------------------------------
    # STEP 6: Safely terminate the connection
    # -------------------------------------------------------------------------
    iosv.close()
    print("\nConnection closed successfully.")
