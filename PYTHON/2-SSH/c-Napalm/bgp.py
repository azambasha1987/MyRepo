
import json
from napalm import get_network_driver
driver = get_network_driver('ios')
iosv = driver('17.1.1.2', 'azam', 'cisco')
iosv.open()

ios_output = iosv.get_facts()
print (json.dumps(ios_output, indent=4)) 

ios_output2 = iosv.get_bgp_neighbors()
print ios_output2


"""
===============================================================================
STUDENT STUDY & TEACHING GUIDE
Script: bgp.py
Topic: Connecting to a Cisco IOS Router & Gathering BGP Information with NAPALM
===============================================================================

1. WHAT IS THIS SCRIPT TRYING TO DO?
-----------------------------------
This script uses NAPALM (Network Automation and Programmability Abstraction
Layer with Multivendor support) to:
  a) Establish an SSH connection to a Cisco IOS router at 17.1.1.2.
  b) Retrieve general device facts (hostname, model, OS version, uptime, serial).
  c) Format and print those device facts as a neat JSON structure.
  d) Retrieve BGP neighbor summary details (peer state, AS numbers, packet stats).
  e) Print the BGP data to the terminal.


2. STEP-BY-STEP EXPLANATION FOR STUDENTS:
-----------------------------------------
- Line 2: `import json`
  Imports Python's built-in JSON module so dictionary data can be formatted
  and printed nicely with indentation.

- Line 3: `from napalm import get_network_driver`
  Imports the factory function from NAPALM that loads the right driver
  for a specific network operating system (e.g., 'ios', 'eos', 'junos', 'nxos').

- Line 4: `driver = get_network_driver('ios')`
  Loads the Cisco IOS driver class.

- Line 5: `iosv = driver('17.1.1.2', 'azam', 'cisco')`
  Instantiates the device object with (Host IP, Username, Password).

- Line 6: `iosv.open()`
  Actually establishes the underlying SSH connection to the router.

- Line 8: `ios_output = iosv.get_facts()`
  A NAPALM "getter" function that returns a standard Python dictionary containing
  core device info (uptime, vendor, model, os_version, serial_number, etc.).

- Line 9: `print (json.dumps(ios_output, indent=4))`
  Converts the dictionary into an indented, human-readable JSON string.

- Line 11: `ios_output2 = iosv.get_bgp_neighbors()`
  Another NAPALM getter that queries the device's BGP state and returns
  a dictionary of peers, their remote AS, and whether the session is up.

- Line 12: `print ios_output2`
  Prints the raw dictionary output.


3. MISTAKES & TRAPS IN THIS SCRIPT (TEACHING POINTS):
-----------------------------------------------------
TRAP 1: Python 2 vs. Python 3 Fatal Syntax Error!
  - Look at Line 12: `print ios_output2` (no parentheses).
  - In Python 2, `print` was a statement. In Python 3, `print()` is a function.
  - If a student runs this on Python 3, it will immediately crash with:
      SyntaxError: Missing parentheses in call to 'print'. Did you mean print(...)?
  - Lesson: Always use `print(...)` in modern Python.

TRAP 2: The "Dangling Connection" Leak (Missing `.close()`)!
  - Notice there is an `iosv.open()`, but nowhere in the script is there
    an `iosv.close()`.
  - Why this matters in networking: Routers have a limited number of VTY lines
    (usually 5 to 16 lines: line vty 0 4). If automation scripts open sessions
    and never close them, the router's VTY lines get locked or exhausted,
    preventing any other engineer or script from logging in!

TRAP 3: Plaintext Credentials Hardcoded in Code:
  - Username 'azam' and password 'cisco' are written directly in the file.
  - If pushed to GitHub or shared, anyone can see the credentials.
  - Best Practice: Use environment variables (`os.environ`) or `getpass.getpass()`.

TRAP 4: No Error Handling (No Safety Net):
  - If the router is unreachable, or the password is wrong, the script crashes
    with an ugly, confusing traceback.
  - Best Practice: Wrap connections in `try ... except ... finally`.


4. HOW TO WRITE THIS LIKE A PROFESSIONAL (CLEAN REFERENCE):
-----------------------------------------------------------
import json
import sys
from napalm import get_network_driver
from napalm.base.exceptions import ConnectionException, AuthenticationException

driver = get_network_driver('ios')
router = driver('17.1.1.2', 'azam', 'cisco')

try:
    print("Connecting to router...")
    router.open()

    print("\n--- Router Facts ---")
    facts = router.get_facts()
    print(json.dumps(facts, indent=4))

    print("\n--- BGP Neighbors ---")
    bgp_data = router.get_bgp_neighbors()
    print(json.dumps(bgp_data, indent=4))

except AuthenticationException:
    print("Authentication failed! Check username/password.", file=sys.stderr)
except ConnectionException as conn_err:
    print(f"Network error: Could not reach router: {conn_err}", file=sys.stderr)
except Exception as err:
    print(f"An unexpected error occurred: {err}", file=sys.stderr)
finally:
    # Guaranteed to close, even if an error happened above!
    router.close()
    print("\nConnection safely closed.")
===============================================================================
"""

