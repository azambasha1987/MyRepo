"""
===============================================================================
Script Name   : napalm1.py
Description   : Introduction to NAPALM - Connecting to a Cisco IOS switch/router
                and retrieving fundamental device facts.
Target Device : Cisco IOSvL2 Switch (192.168.122.72)
Audience      : Network Engineering Students & Automation Beginners
===============================================================================

WHAT IS NAPALM?
---------------
NAPALM (Network Automation and Programmability Abstraction Layer with Multivendor
support) is a vendor-neutral Python library that provides a unified, consistent
API to interact with devices from different vendors (Cisco, Juniper, Arista, etc.).

KEY CONCEPTS TAUGHT IN THIS SCRIPT:
1. Drivers: NAPALM uses vendor-specific drivers (e.g., 'ios', 'eos', 'junos', 'nxos')
   so the exact same getter commands work across different device types.
2. Connection Lifecycle:
   - .open()  : Initiates the underlying SSH/NETCONF connection.
   - .close() : Terminating the session is mandatory in production to prevent
                exhausting available VTY lines on Cisco gear!
3. Getters: 'get_facts()' fetches basic system information (uptime, vendor,
   model, OS version, serial number) returned as a standard Python dictionary.
"""

# -----------------------------------------------------------------------------
# STEP 1: Import the NAPALM driver loader
# -----------------------------------------------------------------------------
# get_network_driver is a factory function that loads the proper class
# based on the network operating system name we pass it.
from napalm import get_network_driver

# -----------------------------------------------------------------------------
# STEP 2: Select the appropriate driver for Cisco IOS devices
# -----------------------------------------------------------------------------
driver = get_network_driver('ios')

# -----------------------------------------------------------------------------
# STEP 3: Define the target device credentials and connection parameters
# -----------------------------------------------------------------------------
# Syntax: driver(hostname_or_ip, username, password, optional_args)
# Note: Ensure the username matches the local user configured on the Cisco device.
iosvl2 = driver('192.168.122.72', 'azam', 'cisco')

# -----------------------------------------------------------------------------
# STEP 4: Open the SSH connection to the device
# -----------------------------------------------------------------------------
print("Connecting to 192.168.122.72...")
iosvl2.open()

try:
    # -------------------------------------------------------------------------
    # STEP 5: Retrieve device facts using a NAPALM getter
    # -------------------------------------------------------------------------
    # get_facts() returns a dictionary with keys:
    # 'uptime', 'vendor', 'model', 'os_version', 'serial_number', 'hostname', etc.
    ios_output = iosvl2.get_facts()

    # -------------------------------------------------------------------------
    # STEP 6: Display the output
    # -------------------------------------------------------------------------
    # (Fixed: Python 3 requires parentheses for print function)
    print("\n--- Device Facts (Raw Python Dictionary) ---")
    print(ios_output)

finally:
    # -------------------------------------------------------------------------
    # STEP 7: Always close the connection
    # -------------------------------------------------------------------------
    # Cisco IOS devices have a limited number of VTY (virtual terminal) lines.
    # Leaving sessions open can lock engineers out of the device!
    iosvl2.close()
    print("\nConnection closed successfully.")