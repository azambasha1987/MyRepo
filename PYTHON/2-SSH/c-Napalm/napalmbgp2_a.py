
import json
from napalm import get_network_driver

bgplist = ['17.1.1.1',
           '17.1.1.2',
           '8.8.8.2',
           '15.1.1.2'
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
Script: napalmbgp2_a.py
Topic: Multi-Hop Topology Challenges & Introduction to Concurrent Automation
===============================================================================

1. WHAT IS THIS SCRIPT TRYING TO DO?
-----------------------------------
This script expands on `napalmbgp2.py` by targeting a larger, 4-router lab topology:
  - R1: 17.1.1.1
  - R2: 17.1.1.2
  - R3: 8.8.8.2
  - R4: 15.1.1.2
It loops through each router, connects over SSH, retrieves BGP neighbor tables,
and prints the JSON output.


2. STEP-BY-STEP EXPLANATION FOR STUDENTS:
-----------------------------------------
- Lines 5-9: `bgplist = [...]`
  Contains 4 router IP addresses traversing 3 different subnets (17.x, 8.x, 15.x).

- Line 11: `for ip_address in bgplist:`
  Processes each router sequentially.

- Lines 13-18: Repeatedly loads driver, connects, pulls BGP table, prints, and closes.


3. MISTAKES & TRAPS IN THIS SCRIPT (TEACHING POINTS):
-----------------------------------------------------
TRAP 1: Network Dependency & Multi-Hop Reachability:
  - In a lab environment (as noted in "BGP topology configuraiton.txt"), your
    Python management host (e.g., Ubuntu VM) might only be physically attached
    to 192.168.122.0/24.
  - To reach 8.8.8.2 and 15.1.1.2, static routes or BGP routing MUST be fully
    converged across intermediate routers.
  - If R2 (17.1.1.2) drops BGP or fails to advertise 8.8.8.0/24, R3 (8.8.8.2)
    becomes unreachable from the script host!

TRAP 2: The Cascading Timeout Disaster (Compounding Delays):
  - Because execution is strictly sequential and lacks `try...except`:
    * If R2 is down, the script waits for an SSH timeout (30-60 seconds).
    * Then Python crashes with an exception!
    * R3 and R4 are completely abandoned!
  - If there were 50 routers and 5 were down, a script without error handling
    would waste minutes before crashing without completing its job.

TRAP 3: Repeated Inefficiency:
  - `driver = get_network_driver('ios')` is still placed inside the loop.
    Move it before the loop.


4. THE PRO WAY: INTRODUCTION TO CONCURRENCY (MULTITHREADING):
-------------------------------------------------------------
In production network engineering, you do NOT query routers one by one.
You query them in parallel using Python's `concurrent.futures.ThreadPoolExecutor`.
If each router takes 3 seconds, 4 routers in serial take 12 seconds;
in parallel, ALL 4 finish in just 3 seconds total!

STUDENT REFERENCE CODE (CONCURRENT / MULTI-THREADED):
-----------------------------------------------------
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from napalm import get_network_driver

ROUTER_LIST = ['17.1.1.1', '17.1.1.2', '8.8.8.2', '15.1.1.2']
driver = get_network_driver('ios')

def query_bgp(ip_address):
    \"\"\"Worker function executed in parallel for each router.\"\"\"
    device = driver(ip_address, 'azam', 'cisco')
    try:
        device.open()
        bgp_data = device.get_bgp_neighbors()
        return ip_address, True, bgp_data
    except Exception as error:
        return ip_address, False, str(error)
    finally:
        try:
            device.close()
        except Exception:
            pass

# Run all connections concurrently with a pool of worker threads
print("--- Launching Parallel BGP Audit ---")
with ThreadPoolExecutor(max_workers=5) as executor:
    future_to_ip = {executor.submit(query_bgp, ip): ip for ip in ROUTER_LIST}
    
    for future in as_completed(future_to_ip):
        ip, success, result = future.result()
        if success:
            print(f"\n[+] SUCCESS: {ip} BGP Neighbors:")
            print(json.dumps(result, indent=4))
        else:
            print(f"\n[-] FAILED: {ip} - Error: {result}")
===============================================================================
"""