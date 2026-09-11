"""
===============================================================================
Script Name   : napalmconfig4.py
Description   : Multi-Device Fleet Compliance Audit - Applying ACL and OSPF policies
                across an inventory of switches/routers with full idempotency.
Target Devices: 192.168.1.105, 192.168.122.73
Audience      : Network Engineering Students & Automation Beginners
===============================================================================

KEY LEARNING OBJECTIVES & IMPORTANT BUG FIX:
--------------------------------------------
1. Multi-Device Fleet Configuration Audits:
   Iterating over `devicelist` to enforce uniform configuration across multiple
   enterprise switches/routers.

2. A Classic Automation Bug Fixed (Stale State / Variable Reuse):
   In the uncorrected version of this script, two critical bugs were present:
   - Bug A: When no ACL changes were needed, `iosv.discard_config()` was omitted,
     leaving candidate buffer state un-cleared.
   - Bug B: When loading `ospf1.cfg`, the script forgot to recompute:
       `diffs = iosv.compare_config()`
     Instead, it checked `if len(diffs) > 0:` using the OLD diff result from the
     ACL step! This meant OSPF changes were evaluated against ACL results,
     leading to potential false commits or missing updates.
   - Fix: Recompute `diffs = iosv.compare_config()` after loading each candidate,
     and discard candidate buffers if no changes are required.

3. Robust Error Handling:
   Wrapping device iterations in `try/except/finally` ensures an unreachable
   device does not crash the entire audit of remaining network devices.
"""

# -----------------------------------------------------------------------------
# STEP 1: Import NAPALM driver loader
# -----------------------------------------------------------------------------
from napalm import get_network_driver

# -----------------------------------------------------------------------------
# STEP 2: Define device inventory list
# -----------------------------------------------------------------------------
devicelist = [
    '192.168.1.105',
    '192.168.122.73'
]

# -----------------------------------------------------------------------------
# STEP 3: Load Cisco IOS driver
# -----------------------------------------------------------------------------
driver = get_network_driver('ios')

# -----------------------------------------------------------------------------
# STEP 4: Iterate through each device in the fleet inventory
# -----------------------------------------------------------------------------
print("Starting fleet configuration audit across {} devices...".format(len(devicelist)))

for ip_address in devicelist:
    print("\n" + "="*65)
    print("Connecting to device: {}".format(ip_address))
    print("="*65)

    # Initialize device connection object with credentials
    iosv = driver(ip_address, 'azam', 'cisco')

    try:
        # Open SSH connection
        iosv.open()

        # ---------------------------------------------------------------------
        # [STAGE 1] ACL Policy Audit (ACL1.cfg)
        # ---------------------------------------------------------------------
        print("\n[Stage 1] Auditing ACL Configuration (ACL1.cfg)...")
        iosv.load_merge_candidate(filename='ACL1.cfg')
        diffs_acl = iosv.compare_config()

        if len(diffs_acl) > 0:
            print("[+] ACL differences found on {}:".format(ip_address))
            print(diffs_acl)
            print("Committing ACL changes...")
            iosv.commit_config()
            print("ACL changes committed.")
        else:
            print("[*] No ACL changes required (already compliant).")
            # Always discard candidate if not committing to clear the buffer!
            iosv.discard_config()

        # ---------------------------------------------------------------------
        # [STAGE 2] OSPF Routing Policy Audit (ospf1.cfg)
        # ---------------------------------------------------------------------
        print("\n[Stage 2] Auditing OSPF Configuration (ospf1.cfg)...")
        iosv.load_merge_candidate(filename='ospf1.cfg')

        # IMPORTANT FIX: Re-run compare_config() to calculate diffs for OSPF!
        diffs_ospf = iosv.compare_config()

        if len(diffs_ospf) > 0:
            print("[+] OSPF differences found on {}:".format(ip_address))
            print(diffs_ospf)
            print("Committing OSPF changes...")
            iosv.commit_config()
            print("OSPF changes committed.")
        else:
            print("[*] No OSPF changes required (already compliant).")
            iosv.discard_config()

    except Exception as error:
        print("[!] ERROR during audit of {}: {}".format(ip_address, error))

    finally:
        # Ensure the SSH session is terminated cleanly for every device
        iosv.close()
        print("Completed session for {} (closed).".format(ip_address))

print("\nFleet configuration audit completed.")