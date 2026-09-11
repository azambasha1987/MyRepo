import json
from napalm import get_network_driver
driver = get_network_driver('ios')
iosvl2 = driver('192.168.122.72', 'azam', 'cisco')
iosvl2.open()

print ('Accessing 192.168.122.72')
iosvl2.load_merge_candidate(filename='ACL1.cfg')

diffs = iosvl2.compare_config()
if len(diffs) > 0:
    print(diffs)
    iosvl2.commit_config()
else:
    print('No ACL changes required.')
    iosvl2.discard_config()

iosvl2.load_merge_candidate(filename='ospf1.cfg')

diffs =iosvl2.compare_config()
if len(diffs) > 0:
    print(diffs)
    iosvl2.commit_config()
else:
    print('No OSPF changes required.')
    iosvl2.discard_config()

iosvl2.close()


"""
===============================================================================
STUDENT STUDY & TEACHING GUIDE
Script: napalmconfig3.py
Topic: Multi-Feature Configuration, The DRY Principle, and Transaction Atomicity
===============================================================================

1. WHAT IS THIS SCRIPT TRYING TO DO?
-----------------------------------
This script pushes TWO separate network features to the same device:
  Feature 1 (Lines 8-16):  Loads, compares, and commits an Access Control List (`ACL1.cfg`).
  Feature 2 (Lines 18-26): Loads, compares, and commits OSPF routing configuration (`ospf1.cfg`).
Finally, it closes the session.


2. STEP-BY-STEP EXPLANATION FOR STUDENTS:
-----------------------------------------
- The script executes the 5-step NAPALM lifecycle twice in a row:
  * First cycle: loads `ACL1.cfg` -> compares -> commits or discards.
  * Second cycle: loads `ospf1.cfg` -> compares -> commits or discards.
- This achieves multi-feature provisioning on device 192.168.122.72.


3. MISTAKES & TRAPS IN THIS SCRIPT (TEACHING POINTS):
-----------------------------------------------------
TRAP 1: Violation of the DRY Principle ("Don't Repeat Yourself"):
  - Look at lines 8-16 and lines 18-26. They are almost 100% copy-pasted!
  - Why is copy-pasting code dangerous in programming?
    * If you improve your logic (like adding error handling), you must remember
      to update every copy.
    * If you make a mistake in one copy (as we will see in `napalmconfig4.py`),
      it leads to subtle, catastrophic logic bugs!
  - Solution: Use a `for` loop over a list of configuration files, or a helper
    function:
      `for config_file in ['ACL1.cfg', 'ospf1.cfg']:`

TRAP 2: The "Split-Commit" Problem (Lack of Atomicity):
  - In this script, the device commits the ACL first, and commits OSPF second.
  - Ask students: "What happens if ACL commits successfully, but the OSPF file
    contains a syntax error and throws an exception?"
  - Answer: The device is left in a "half-configured" state (ACL is active,
    OSPF is not running).
  - In enterprise networks, network architects prefer "atomic" changes:
    either ALL configuration changes succeed, or NONE of them are applied (rollback).

TRAP 3: Formatting & PEP 8 Style:
  - Line 20: `diffs =iosvl2.compare_config()`
  - Notice the missing space after `=`. Python style guide (PEP 8) recommends
    surrounding assignment operators with single spaces: `diffs = iosvl2...`

TRAP 4: Unused Import:
  - `import json` is present on line 1 but never used.


4. HOW TO WRITE THIS LIKE A PROFESSIONAL (REFACTORED WITH DRY):
---------------------------------------------------------------
from pathlib import Path
from napalm import get_network_driver

BASE_DIR = Path(__file__).resolve().parent
driver = get_network_driver('ios')
device = driver('192.168.122.72', 'azam', 'cisco')

# Define all configurations to apply as a list of (Name, Path) tuples
CONFIG_JOBS = [
    ('Access-List', BASE_DIR / 'ACL1.cfg'),
    ('OSPF Routing', BASE_DIR / 'ospf1.cfg'),
]

try:
    print("Connecting to device...")
    device.open()

    # Reusable loop applies the DRY principle!
    for job_name, file_path in CONFIG_JOBS:
        print(f"\n--- Staging {job_name} ({file_path.name}) ---")
        device.load_merge_candidate(filename=str(file_path))
        
        diffs = device.compare_config()
        if len(diffs) > 0:
            print(f"Diffs found for {job_name}:\n{diffs}")
            device.commit_config()
            print(f"[+] {job_name} committed successfully.")
        else:
            print(f"[i] No changes required for {job_name}.")
            device.discard_config()

except Exception as err:
    print(f"\n[!] Configuration failed: {err}")
    try:
        device.discard_config()
    except Exception:
        pass
finally:
    device.close()
    print("\nSession closed.")
===============================================================================
"""