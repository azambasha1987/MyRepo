
import json
from napalm import get_network_driver

bgplist = ['17.1.1.1',
           '17.1.1.2'
          ]

for ip_address in bgplist:
    print ("Connecting to " + str(ip_address))
    driver = get_network_driver('ios')
    iosv_router = driver(ip_address, 'azam', 'cisco')
    iosv_router.open()
    bgp_neighbors = iosv_router.get_bgp_neighbors()
    print (json.dumps(bgp_neighbors, indent=4))
    iosv_router.close()


"""
===============================================================================
STUDENT STUDY & TEACHING GUIDE
Script: napalmbgp2.py
Topic: Multi-Device Automation with Loops & Preventing the "Domino Crash"
===============================================================================

1. WHAT IS THIS SCRIPT TRYING TO DO?
-----------------------------------
This script scales up automation from 1 device to multiple devices:
  a) Defines a Python list (`bgplist`) containing multiple router IP addresses.
  b) Uses a `for` loop to iterate through each IP address.
  c) Connects to each router, retrieves BGP neighbor status, prints the JSON,
     and closes the session.


2. STEP-BY-STEP EXPLANATION FOR STUDENTS:
-----------------------------------------
- Lines 5-7: `bgplist = ['17.1.1.1', '17.1.1.2']`
  A list of target devices.

- Line 9: `for ip_address in bgplist:`
  Iterates over each IP one by one (sequentially).

- Line 11: `driver = get_network_driver('ios')`
  Loads the driver inside the loop (see Trap 1 below).

- Line 12: `iosv_router = driver(ip_address, 'azam', 'cisco')`
  Configures the connection object for the current IP in the loop.

- Lines 13-16: Connects, fetches BGP info, prints JSON, and closes.


3. MISTAKES & TRAPS IN THIS SCRIPT (TEACHING POINTS):
-----------------------------------------------------
TRAP 1: Inefficient Driver Loading inside the Loop:
  - Line 11: `driver = get_network_driver('ios')` is inside the `for` loop.
  - Ask students: "Does the driver class change between router 1 and router 2?"
  - Answer: No! Both are Cisco IOS devices. Calling `get_network_driver('ios')`
    inside the loop forces Python to look up and reload the class definition
    on EVERY iteration.
  - Rule of Thumb: If an action only needs to happen once, place it OUTSIDE the loop.

TRAP 2: The "Domino Crash" (Fatal Lack of Error Isolation):
  - In networking, routers occasionally reboot, drop packets, or have bad links.
  - What happens if router 1 (`17.1.1.1`) is offline?
      * Python throws a `NetMikoTimeoutException` or `ConnectionException`.
      * The script immediately terminates!
      * Router 2 (`17.1.1.2`) is NEVER checked!
  - Real-World Lesson: In network automation, one dead device must NEVER stop
    you from managing the other 99 devices. Every device connection inside a
    loop MUST have its own `try ... except ... finally` block!

TRAP 3: Outdated String Concatenation:
  - Line 10: `print ("Connecting to " + str(ip_address))`
  - Python 3 best practice is to use formatted string literals (f-strings):
      `print(f"Connecting to {ip_address}...")`

TRAP 4: Sequential Delay (Scalability Bottleneck):
  - Connecting sequentially means: (Time per router) x (Number of routers).
  - With 2 routers it takes 4 seconds. With 100 routers, it takes 200+ seconds.
  - Advanced concept to introduce: Concurrency with `ThreadPoolExecutor` or `asyncio`.


4. HOW TO WRITE THIS LIKE A PROFESSIONAL (CLEAN REFERENCE):
-----------------------------------------------------------
import json
from napalm import get_network_driver
from napalm.base.exceptions import ConnectionException, AuthenticationException

# Step 1: Initialize driver ONCE, outside the loop
driver = get_network_driver('ios')
bgp_routers = ['17.1.1.1', '17.1.1.2']

# Step 2: Loop through devices with per-device error isolation
for ip in bgp_routers:
    print(f"\n{'='*20} Connecting to {ip} {'='*20}")
    device = driver(ip, 'azam', 'cisco')
    
    try:
        device.open()
        bgp_neighbors = device.get_bgp_neighbors()
        print(json.dumps(bgp_neighbors, indent=4))
        
    except AuthenticationException:
        print(f"[!] Authentication failed for {ip}. Check credentials.")
    except ConnectionException as conn_err:
        print(f"[!] Could not connect to {ip}: {conn_err}")
    except Exception as err:
        print(f"[!] Unexpected error on {ip}: {err}")
        
    finally:
        try:
            device.close()
            print(f"[-] Closed connection to {ip}.")
        except Exception:
            pass  # If never opened, close might fail; safely ignore
===============================================================================
"""