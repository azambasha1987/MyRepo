"""
===============================================================================
Script Name   : napalmconfig1.py
Description   : Declarative Configuration Management - Loading a merge candidate
                configuration (ACL1.cfg) and committing it to a Cisco device.
Target Device : Cisco Switch/Router (192.168.122.72)
Audience      : Network Engineering Students & Automation Beginners
===============================================================================

HOW NAPALM MANAGES CONFIGURATION:
---------------------------------
Unlike legacy screen-scraping libraries (which type commands one-by-one into CLI),
NAPALM uses declarative, transactional configuration management:

1. Staging / Candidate Buffer:
   `load_merge_candidate(filename='ACL1.cfg')`
   Reads configuration lines from an external file and loads them into a staging
   candidate buffer on the device. No changes are active yet!
2. Committing:
   `commit_config()`
   Applies the staged candidate configuration into the running configuration.

IMPORTANT TEACHING POINT:
-------------------------
This script demonstrates the most basic configuration workflow. However,
committing blindly without previewing changes is dangerous in production!
The next script (`napalmconfig2.py`) introduces `compare_config()` to safely
audit changes before committing them.
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
    # STEP 4: Stage the configuration from external file 'ACL1.cfg'
    # -------------------------------------------------------------------------
    print("Loading merge candidate from 'ACL1.cfg' into staging buffer...")
    iosvl2.load_merge_candidate(filename='ACL1.cfg')

    # -------------------------------------------------------------------------
    # STEP 5: Commit staged changes to the running configuration
    # -------------------------------------------------------------------------
    print("Committing configuration changes to the device...")
    iosvl2.commit_config()
    print("Configuration committed successfully.")

finally:
    # -------------------------------------------------------------------------
    # STEP 6: Close the session
    # -------------------------------------------------------------------------
    iosvl2.close()
    print("Session closed.")