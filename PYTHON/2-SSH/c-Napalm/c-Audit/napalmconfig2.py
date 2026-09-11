"""
===============================================================================
Script Name   : napalmconfig2.py
Description   : Safe Configuration Audit & Idempotency - Previewing diffs with
                compare_config() before committing or discarding changes.
Target Device : Cisco Switch/Router (192.168.122.72)
Audience      : Network Engineering Students & Automation Beginners
===============================================================================

THE "AUDIT & DRY-RUN" PATTERN:
------------------------------
In enterprise automation, you must never blindly push configurations without
verifying what will change. NAPALM enables safe changes through three methods:

1. `compare_config()`:
   Compares the candidate configuration in the staging buffer against the active
   running configuration. Returns a diff string showing additions (+) and deletions (-).
2. `commit_config()`:
   Only called if meaningful differences exist (`len(diffs) > 0`).
3. `discard_config()`:
   Clears the candidate staging buffer if no changes are required, or if an audit
   fails, ensuring no pending changes linger on the router.

KEY CONCEPT: IDEMPOTENCY
------------------------
An operation is "idempotent" if running it multiple times produces the exact same
result without unintended side-effects.
- Run 1: Applies the ACL if it was missing -> commits changes.
- Run 2: Detects ACL is already present -> diff is empty -> discards candidate.
"""

# -----------------------------------------------------------------------------
# STEP 1: Import NAPALM driver loader
# -----------------------------------------------------------------------------
from napalm import get_network_driver

# -----------------------------------------------------------------------------
# STEP 2: Configure driver and credentials
# -----------------------------------------------------------------------------
driver = get_network_driver('ios')
iosvl2 = driver('192.168.122.72', 'azam', 'cisco')

# -----------------------------------------------------------------------------
# STEP 3: Open SSH session
# -----------------------------------------------------------------------------
print("Accessing 192.168.122.72...")
iosvl2.open()

try:
    # -------------------------------------------------------------------------
    # STEP 4: Stage candidate configuration from 'ACL1.cfg'
    # -------------------------------------------------------------------------
    print("Staging candidate configuration from 'ACL1.cfg'...")
    iosvl2.load_merge_candidate(filename='ACL1.cfg')

    # -------------------------------------------------------------------------
    # STEP 5: Generate diff between candidate and running configuration
    # -------------------------------------------------------------------------
    diffs = iosvl2.compare_config()

    # -------------------------------------------------------------------------
    # STEP 6: Conditionally commit or discard based on diff results
    # -------------------------------------------------------------------------
    if len(diffs) > 0:
        print("\n[+] Differences detected! Proposed changes:")
        print(diffs)
        print("Committing changes to running configuration...")
        iosvl2.commit_config()
        print("Commit completed successfully.")
    else:
        print("\n[*] No changes required (device configuration already compliant).")
        print("Discarding candidate staging buffer...")
        iosvl2.discard_config()

finally:
    # -------------------------------------------------------------------------
    # STEP 7: Close session
    # -------------------------------------------------------------------------
    iosvl2.close()
    print("Session closed.")