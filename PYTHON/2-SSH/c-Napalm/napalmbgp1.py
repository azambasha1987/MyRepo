
import json
from napalm import get_network_driver
driver = get_network_driver('ios')
iosvl2 = driver('192.168.122.72', 'azam', 'cisco')
iosvl2.open()

bgp_neighbors = iosvl2.get_bgp_neighbors()
print (json.dumps(bgp_neighbors, indent=4))

iosvl2.close()


"""
===============================================================================
STUDENT STUDY & TEACHING GUIDE
Script: napalmbgp1.py
Topic: Resource Cleanup & "The Happy Path Fallacy"
===============================================================================

1. WHAT IS THIS SCRIPT TRYING TO DO?
-----------------------------------
This script connects to a device at `192.168.122.72` (management subnet),
queries its BGP neighbor table, prints the output in formatted JSON, and
closes the session.


2. STEP-BY-STEP EXPLANATION FOR STUDENTS:
-----------------------------------------
- Line 4: `driver = get_network_driver('ios')`
  Prepares the Cisco IOS driver.

- Line 5: `iosvl2 = driver('192.168.122.72', 'azam', 'cisco')`
  Instantiates the device connection object.

- Line 6: `iosvl2.open()`
  Opens the SSH session.

- Line 8: `bgp_neighbors = iosvl2.get_bgp_neighbors()`
  Extracts structured BGP data.

- Line 9: `print (json.dumps(bgp_neighbors, indent=4))`
  Displays the data formatted.

- Line 11: `iosvl2.close()`
  Closes the SSH session.


3. MISTAKES & TRAPS IN THIS SCRIPT (TEACHING POINTS):
-----------------------------------------------------
WHAT IMPROVED:
  + Great improvement! The student remembered to include `iosvl2.close()`!

THE CRITICAL TEACHING LESSON: "The Happy Path Fallacy"
  - Look at lines 6 through 11:
      iosvl2.open()
      bgp_neighbors = iosvl2.get_bgp_neighbors()
      print (json.dumps(bgp_neighbors, indent=4))
      iosvl2.close()
  - Ask students: "Under what condition will line 11 (close) actually run?"
  - Answer: Line 11 ONLY runs if lines 6, 8, and 9 execute with ZERO errors!
    This is called "The Happy Path".
  - What if line 8 crashes because:
      * The device does not have BGP enabled?
      * The SSH connection drops halfway through?
      * A network timeout occurs?
  - If line 8 raises an exception, Python aborts immediately. Line 11 is NEVER
    reached, leaving the SSH session dangling!
  - The Fix: Use `try ... finally`. The `finally` block is guaranteed to run,
    whether there was an error or not.

TRAP 2: Misleading Variable Naming:
  - The variable is called `iosvl2` (Layer 2 switch).
  - But BGP is a Layer 3 routing protocol. While MLS switches can run routing,
    naming a BGP device `iosvl2` is confusing to anyone reading your code.
    Use meaningful names like `router`, `ios_device`, or `bgp_peer`.

TRAP 3: Hardcoded Credentials:
  - 'azam' / 'cisco' should not be hardcoded in production scripts.


4. HOW TO WRITE THIS LIKE A PROFESSIONAL (CLEAN REFERENCE):
-----------------------------------------------------------
import json
import sys
from napalm import get_network_driver

driver = get_network_driver('ios')
device = driver('192.168.122.72', 'azam', 'cisco')

try:
    print("Connecting to device...")
    device.open()

    print("Gathering BGP neighbor status...")
    bgp_neighbors = device.get_bgp_neighbors()
    print(json.dumps(bgp_neighbors, indent=4))

except Exception as err:
    print(f"Failed to retrieve BGP data: {err}", file=sys.stderr)

finally:
    # This block is GUARANTEED to execute, even if an exception occurs above!
    device.close()
    print("Device connection closed successfully.")
===============================================================================
"""