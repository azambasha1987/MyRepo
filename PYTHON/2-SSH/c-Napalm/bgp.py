
import json
from napalm import get_network_driver
driver = get_network_driver('ios')
iosv = driver('17.1.1.2', 'azam', 'cisco')
iosv.open()
 
#ios_output = iosv.get_facts()
#print (json.dumps(ios_output, indent=4)) 
 
ios_output2 = iosv.get_bgp_neighbors()
print (json.dumps(ios_output2, indent=4))


r"""
===============================================================================
STUDENT STUDY & TEACHING GUIDE
Script: bgp.py
Topic: Connecting to Cisco IOS & Gathering BGP Information with NAPALM
===============================================================================

1. WHAT IS THIS SCRIPT TRYING TO DO?
-----------------------------------
This script uses NAPALM to:
  a) Connect to a Cisco IOS router at 17.1.1.2 using username 'azam' and password 'cisco'.
  b) Retrieve BGP neighbor summary details (peer state, AS numbers, packet stats).
  c) Format and display the BGP neighbor information as pretty-printed JSON.


2. STEP-BY-STEP EXPLANATION FOR STUDENTS:
-----------------------------------------
- Line 2-6: Standard NAPALM initialization and SSH session opening.
  `driver('17.1.1.2', 'azam', 'cisco')` sets the target router IP and credentials.

- Lines 8-9: `#ios_output = iosv.get_facts()`
  Device facts retrieval is commented out to focus solely on BGP neighbors.

- Line 11: `ios_output2 = iosv.get_bgp_neighbors()`
  Fetches BGP neighbor details (local AS, remote AS, router ID, uptime, peer state).

- Line 12: `print (json.dumps(ios_output2, indent=4))`
  `json.dumps()` formats the dictionary into clean, indented JSON for readability.


3. MISTAKES & TRAPS IN THIS SCRIPT (TEACHING POINTS):
-----------------------------------------------------
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
  - Username 'azam' and password 'cisco' are hardcoded.
  - In production, always use environment variables (`os.environ`) or `getpass`.

TRAP 4: Fragile Execution (No `try...finally`):
  - If the router is unreachable or BGP is not configured, the script crashes.


4. HOW TO WRITE THIS LIKE A PROFESSIONAL (CLEAN REFERENCE):
-----------------------------------------------------------
import json
import sys
from napalm import get_network_driver

driver = get_network_driver('ios')
router = driver('17.1.1.2', 'azam', 'cisco')

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
#why we use import a network driver in Napalm? 
#import the driver because NAPALM needs to know which vendor 
# translator to load so it can bridge the gap between 
# NAPALM's universal methods and the 
# target device's vendor-specific syntax and communication protocols.