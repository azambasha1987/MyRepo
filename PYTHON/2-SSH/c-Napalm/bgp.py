
import json
from napalm import get_network_driver
driver = get_network_driver('ios')
iosv = driver('17.1.1.2', 'azam', 'cisco')
iosv.open()
 
#ios_output = iosv.get_facts()
#print (json.dumps(ios_output, indent=4)) 
 
ios_output2 = iosv.get_bgp_neighbors()
print (json.dumps(ios_output2, indent=4))


"""
===============================================================================
STUDENT STUDY & TEACHING GUIDE
Script: bgp_modified.py
Topic: Code Evolution & Formatting BGP Output with JSON
===============================================================================

1. WHAT IS THIS SCRIPT TRYING TO DO?
-----------------------------------
This script is an evolution of `bgp.py`. The student or developer:
  a) Removed the device facts retrieval to focus purely on BGP.
  b) Fixed the Python 2 print statement error found in `bgp.py`.
  c) Changed the username from 'azam' to 'david'.
  d) Formats the BGP neighbors dictionary as pretty-printed JSON.


2. STEP-BY-STEP EXPLANATION FOR STUDENTS:
-----------------------------------------
- Line 2-6: Standard NAPALM initialization and SSH session opening.
  `driver('17.1.1.2', 'david', 'cisco')` sets the target router IP and credentials.

- Lines 8-9: `#ios_output = iosv.get_facts()`
  These lines were commented out with `#` so Python ignores them.

- Line 11: `ios_output2 = iosv.get_bgp_neighbors()`
  Fetches BGP neighbor details (local AS, remote AS, router ID, uptime, peer state).

- Line 12: `print (json.dumps(ios_output2, indent=4))`
  `json.dumps()` turns the Python dictionary into an easy-to-read JSON string
  indented by 4 spaces.


3. MISTAKES & TRAPS IN THIS SCRIPT (TEACHING POINTS):
-----------------------------------------------------
WHAT IMPROVED:
  + Python 3 Compatibility: Used `print(...)` with parentheses.
  + Visual Clarity: Output is formatted as structured JSON instead of a raw
    single-line dictionary dump.

WHAT IS STILL BROKEN OR DANGEROUS:
TRAP 1: The Missing Connection Close (Resource Leak)!
  - `iosv.open()` is called on line 6, but `iosv.close()` is NEVER called.
  - Question to ask students: "What happens to the router's SSH session when
    your script finishes running?"
  - Answer: In quick test scripts, the OS socket eventually closes on script exit,
    but in Cisco IOS, the VTY line can remain tied up until an idle-timeout
    kicks in. In longer automation workflows, omitting `.close()` quickly leads to
    "Connection refused / VTY lines busy" errors.

TRAP 2: "Zombie Code" (Commented-out Code):
  - Lines 8-9 are commented out.
  - Teaching lesson: In production, do not leave old code commented out.
    Use Git version control to remember past versions. Clean code is easier to read!

TRAP 3: Hardcoded Plaintext Passwords:
  - 'david' and 'cisco' are hardcoded.

TRAP 4: Fragile Execution (No `try...finally`):
  - If the router is unreachable or BGP is not configured, the script crashes.


4. HOW TO WRITE THIS LIKE A PROFESSIONAL (CLEAN REFERENCE):
-----------------------------------------------------------
import json
import sys
from napalm import get_network_driver

driver = get_network_driver('ios')
router = driver('17.1.1.2', 'david', 'cisco')

try:
    print("Connecting to 17.1.1.2...")
    router.open()

    print("Fetching BGP neighbors...")
    bgp_neighbors = router.get_bgp_neighbors()
    print(json.dumps(bgp_neighbors, indent=4))

except Exception as err:
    print(f"Error querying router: {err}", file=sys.stderr)
finally:
    router.close()
    print("Session disconnected.")
===============================================================================
"""

