import json
from napalm import get_network_driver
driver = get_network_driver('ios')
iosvl2 = driver('192.168.122.72', 'azam', 'cisco')
iosvl2.open()

print ('Accessing 192.168.122.72')
iosvl2.load_merge_candidate(filename='ACL1.cfg')
iosvl2.commit_config()
iosvl2.close()


r"""
===============================================================================
STUDENT STUDY & TEACHING GUIDE
Script: napalmconfig1.py
Topic: Introduction to Configuration Management & The Danger of Blind Commits
===============================================================================

1. WHAT IS THIS SCRIPT TRYING TO DO?
-----------------------------------
This script moves beyond gathering data ("getters") to CHANGING device state:
  a) Connects to a switch/router at 192.168.122.72.
  b) Reads a configuration snippet from an external text file (`ACL1.cfg`).
  c) Loads that snippet as a "merge candidate" configuration.
  d) Immediately commits the configuration change to the device.
  e) Closes the session.


2. STEP-BY-STEP EXPLANATION FOR STUDENTS:
-----------------------------------------
- Line 1: `import json`
  Unused! Imported by habit from previous scripts, but not needed here.

- Line 8: `iosvl2.load_merge_candidate(filename='ACL1.cfg')`
  NAPALM method that loads a local configuration file into the device driver's
  staging buffer.
  * NOTE: "Merge" means new lines will be merged/added into the running
    configuration (similar to going into `conf t` and pasting lines).
    It does NOT wipe out the rest of the configuration.

- Line 9: `iosvl2.commit_config()`
  Permanently writes the staged candidate changes into the active configuration.

- Line 10: `iosvl2.close()`
  Closes the SSH session.


3. MISTAKES & TRAPS IN THIS SCRIPT (TEACHING POINTS):
-----------------------------------------------------
TRAP 1: The "Blind Commit" (Fatal Practice in Network Engineering!):
  - Notice line 8 loads the candidate, and line 9 IMMEDIATELY commits it.
  - Ask students: "What did we just push to the router? Did we inspect it first?"
  - Answer: We have NO IDEA what diff was applied!
    * What if `ACL1.cfg` contained a typo like `access-list 100 deny any any`?
    * The script would blindly commit it, instantly blocking SSH and locking you
      out of your own lab or production network!
  - GOLDEN RULE of Network Automation:
      ALWAYS run `compare_config()` BEFORE calling `commit_config()`!
      Look at the diff, verify it, and only commit if it is safe and expected!

TRAP 2: Fragile Relative File Paths:
  - `filename='ACL1.cfg'` relies on the "current working directory" (where your
    terminal was opened).
  - If a student runs `python e:/Git/PYTHON/2-SSH/c-Napalm/napalmconfig1.py`
    from `C:/Users/Student/`, Python looks for `C:/Users/Student/ACL1.cfg`
    and crashes with `FileNotFoundError`!
  - Best Practice: Use `pathlib.Path(__file__).parent / 'ACL1.cfg'` to ensure
    the file is always found next to the script.

TRAP 3: Unused `import json`:
  - Python style tip: Keep code clean. If you don't use a module, don't import it.

TRAP 4: No Discard or Cleanup on Failure:
  - If `commit_config()` fails, the candidate changes remain pending in memory.
    You should call `device.discard_config()` if something goes wrong.


4. HOW TO WRITE THIS LIKE A PROFESSIONAL (CLEAN REFERENCE):
-----------------------------------------------------------
from pathlib import Path
from napalm import get_network_driver

# Anchor path to where this script lives
CURRENT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = CURRENT_DIR / 'ACL1.cfg'

if not CONFIG_FILE.exists():
    raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")

driver = get_network_driver('ios')
device = driver('192.168.122.72', 'azam', 'cisco')

try:
    print("Connecting to device...")
    device.open()

    print("Loading candidate configuration...")
    device.load_merge_candidate(filename=str(CONFIG_FILE))

    # Inspect the difference BEFORE committing!
    diffs = device.compare_config()

    if len(diffs) > 0:
        print("\n--- Proposed Configuration Changes (Diff) ---")
        print(diffs)
        
        # In a real environment, you can prompt for confirmation:
        # confirm = input("Do you want to commit these changes? (yes/no): ")
        # if confirm.lower() == 'yes':
        device.commit_config()
        print("\n[+] Configuration committed successfully!")
    else:
        print("\n[i] Device already matches candidate config. No changes needed.")
        device.discard_config()

except Exception as err:
    print(f"\n[!] Error during configuration: {err}")
    try:
        device.discard_config()
        print("[*] Staged candidate configuration was discarded.")
    except Exception:
        pass

finally:
    device.close()
    print("[-] Session closed.")
===============================================================================
"""