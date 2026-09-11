"""
===============================================================================
Script Name   : napalm1_json.py
Description   : Querying device facts and interface telemetry, formatted with JSON.
Target Device : Cisco IOSvL2 Switch (192.168.122.72)
Audience      : Network Engineering Students & Automation Beginners
===============================================================================

WHY USE JSON FORMATTING?
------------------------
When Python retrieves data from network devices via NAPALM, it returns nested
dictionaries and lists. Printing raw Python dictionaries can be hard to read.
Using Python's built-in `json.dumps(..., indent=4)`:
1. Pretty-prints the data with clean indentation.
2. Standardizes data representation across reporting tools, REST APIs, and databases.
3. Allows sorting keys (`sort_keys=True`) for consistent, alphabetical comparisons.

KEY GETTERS DEMONSTRATED:
1. get_facts()               : Basic device identity, hardware, and OS version.
2. get_interfaces()          : Operational status (up/down), MAC addresses, speed, descriptions.
3. get_interfaces_counters() : Real-time packet telemetry (TX/RX packets, errors, discards).
"""

# -----------------------------------------------------------------------------
# STEP 1: Import required modules
# -----------------------------------------------------------------------------
import json
from napalm import get_network_driver

# -----------------------------------------------------------------------------
# STEP 2: Initialize Cisco IOS driver and connection details
# -----------------------------------------------------------------------------
driver = get_network_driver('ios')
iosvl2 = driver('192.168.122.72', 'azam', 'cisco')

# -----------------------------------------------------------------------------
# STEP 3: Open SSH session
# -----------------------------------------------------------------------------
print("Opening connection to 192.168.122.72...")
iosvl2.open()

try:
    # -------------------------------------------------------------------------
    # STEP 4: Retrieve and pretty-print basic device facts
    # -------------------------------------------------------------------------
    print("\n" + "="*50)
    print("1. DEVICE FACTS")
    print("="*50)
    ios_output = iosvl2.get_facts()
    # indent=4 creates readable 4-space indentation for nested JSON blocks
    print(json.dumps(ios_output, indent=4))

    # -------------------------------------------------------------------------
    # STEP 5: Retrieve and pretty-print interface statuses
    # -------------------------------------------------------------------------
    print("\n" + "="*50)
    print("2. INTERFACE STATUS (Operational & Admin State)")
    print("="*50)
    # get_interfaces() returns info like: is_up, is_enabled, description, mac_address
    ios_output = iosvl2.get_interfaces()
    # sort_keys=True sorts interface names alphabetically for easier reading
    print(json.dumps(ios_output, sort_keys=True, indent=4))

    # -------------------------------------------------------------------------
    # STEP 6: Retrieve interface traffic and error counters
    # -------------------------------------------------------------------------
    print("\n" + "="*50)
    print("3. INTERFACE COUNTERS (Packets, Errors, Discards)")
    print("="*50)
    # get_interfaces_counters() is crucial for troubleshooting packet drops or CRC errors
    ios_output = iosvl2.get_interfaces_counters()
    print(json.dumps(ios_output, sort_keys=True, indent=4))

finally:
    # -------------------------------------------------------------------------
    # STEP 7: Close the session to release the device VTY line
    # -------------------------------------------------------------------------
    iosvl2.close()
    print("\nSession closed cleanly.")