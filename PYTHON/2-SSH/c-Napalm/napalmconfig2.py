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
    print('No changes required.')
    iosvl2.discard_config()

iosvl2.close()


"""
===============================================================================
STUDENT STUDY & TEACHING GUIDE
Script: napalmconfig2.py
Topic: The 5-Step NAPALM Workflow & The Concept of Idempotency
===============================================================================

1. WHAT IS THIS SCRIPT TRYING TO DO?
-----------------------------------
This script fixes the dangerous "blind commit" flaw from `napalmconfig1.py`:
  a) Connects to the switch/router at 192.168.122.72.
  b) Loads `ACL1.cfg` into the staging candidate buffer.
  c) Compares candidate configuration against the device's running configuration.
  d) If differences exist (`len(diffs) > 0`), it prints the diff and commits.
  e) If no differences exist, it prints "No changes required" and discards the candidate.
  f) Closes the connection.


2. THE 5-STEP NAPALM CONFIGURATION LIFECYCLE (TEACH THIS PATTERN!):
-------------------------------------------------------------------
This is the textbook, industry-standard pattern for NAPALM configuration changes:

  Step 1: CONNECT          --> `device.open()`
  Step 2: STAGE CANDIDATE  --> `device.load_merge_candidate(filename=...)`
  Step 3: AUDIT / DIFF     --> `diffs = device.compare_config()`
  Step 4: CONDITIONAL EXEC -->
             if len(diffs) > 0:
                 print(diffs)
                 device.commit_config()    # Apply changes
             else:
                 device.discard_config()   # Clear staging buffer
  Step 5: TEARDOWN         --> `device.close()`


3. KEY CONCEPT TO TEACH STUDENTS: IDEMPOTENCY
---------------------------------------------
- Ask students: "What happens if we run this script TWICE in a row?"
- Demonstration:
    * Run 1: The ACL doesn't exist on the router yet.
      `diffs` shows the 4 ACL lines. The script commits them.
    * Run 2 (5 seconds later): The ACL already exists in running config!
      `compare_config()` detects that the device already has these exact lines!
      `diffs` is EMPTY (`len(diffs) == 0`).
      The script prints "No changes required." and discards the candidate!
- Definition: "Idempotency" means executing an operation multiple times produces
  the exact same result as executing it once, without making redundant changes
  or causing network disruption.


4. REMAINING TRAPS & IMPROVEMENTS:
----------------------------------
TRAP 1: Unhandled Exceptions Still Bypass Discard and Close:
  - If a network blip occurs during `compare_config()`, lines 16 and 18 are skipped.
  - A dirty candidate config might stay locked on the router.
  - Fix: Wrap the entire block in `try ... finally: device.discard_config(); device.close()`.

TRAP 2: Unused `import json`:
  - `import json` is not used in this file and can be removed.

TRAP 3: Hardcoded IP & Credentials:
  - Still using hardcoded IP `192.168.122.72` and credentials `azam`/`cisco`.


5. CLEAN & ROBUST CODE PATTERN:
-------------------------------
from pathlib import Path
from napalm import get_network_driver

cfg_path = Path(__file__).resolve().parent / 'ACL1.cfg'
driver = get_network_driver('ios')
device = driver('192.168.122.72', 'azam', 'cisco')

try:
    device.open()
    device.load_merge_candidate(filename=str(cfg_path))
    diffs = device.compare_config()
    
    if len(diffs) > 0:
        print(f"Diffs detected:\n{diffs}")
        device.commit_config()
        print("Commit complete.")
    else:
        print("Idempotent check passed: No changes required.")
        device.discard_config()
        
except Exception as e:
    print(f"Error during configuration: {e}")
    try:
        device.discard_config()
    except Exception:
        pass
finally:
    device.close()
===============================================================================
"""