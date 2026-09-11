"""
===============================================================================
Script Name   : napalm2.py
Description   : Inspecting Layer 2 MAC tables, Layer 3 ARP tables, and running
                synthetic ICMP ping tests from a Cisco device.
Target Device : Cisco IOSvL2 Switch (192.168.122.72)
===============================================================================

KEY NETWORKING CONCEPTS COVERED:
1. get_mac_address_table():
   - Inspects the Layer 2 CAM (Content Addressable Memory) table.
   - Shows which MAC addresses are learned on which VLANs and switch interfaces.
2. get_arp_table():
   - Inspects the Layer 3 ARP (Address Resolution Protocol) cache.
   - Shows the IP-to-MAC address mapping needed for IP packet forwarding.
3. ping('destination'):
   - Performs a synthetic reachability test executed directly from the Cisco device.
   - Returns statistics such as packet loss, round-trip times (rtt_min, rtt_avg, rtt_max).
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
print("Connecting to 192.168.122.72...")
iosvl2.open()

try:
    # -------------------------------------------------------------------------
    # STEP 4: Retrieve and display MAC address table (Layer 2)
    # -------------------------------------------------------------------------
    print("\n" + "="*50)
    print("1. MAC ADDRESS TABLE (Layer 2 Switching)")
    print("="*50)
    ios_output = iosvl2.get_mac_address_table()
    print(json.dumps(ios_output, indent=4))

    # -------------------------------------------------------------------------
    # STEP 5: Retrieve and display ARP table (Layer 3)
    # -------------------------------------------------------------------------
    print("\n" + "="*50)
    print("2. ARP TABLE (Layer 3 IP-to-MAC Resolution)")
    print("="*50)
    ios_output = iosvl2.get_arp_table()
    print(json.dumps(ios_output, indent=4))

    # -------------------------------------------------------------------------
    # STEP 6: Execute synthetic ping test from the device
    # -------------------------------------------------------------------------
    print("\n" + "="*50)
    print("3. SYNTHETIC REACHABILITY TEST (Ping to google.com)")
    print("="*50)
    # The device sends ICMP echo requests from its own perspective
    ios_output = iosvl2.ping('google.com')
    print(json.dumps(ios_output, indent=4))

finally:
    # -------------------------------------------------------------------------
    # STEP 7: Close the session to release the device VTY line
    # -------------------------------------------------------------------------
    iosvl2.close()
    print("\nConnection closed successfully.")