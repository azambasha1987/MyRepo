import json
from napalm import get_network_driver

devicelist = ['192.168.122.72',
           '192.168.122.73',
           ]


for ip_address in devicelist:
    print ("Connecting to " + str(ip_address))
    driver = get_network_driver('ios')
    iosv = driver(ip_address, 'azam', 'cisco')
    iosv.open()
    iosv.load_merge_candidate(filename='ACL1.cfg')
    diffs = iosv.compare_config()
    if len(diffs) > 0:
        print(diffs)
        iosv.commit_config()
    else:
        print('No ACL changes required.')
    
    
    iosv.load_merge_candidate(filename='ospf1.cfg')
    if len(diffs) > 0:
        print(diffs)
        iosv.commit_config()
    else:
        print('No OSPF changes required.')
        iosv.discard_config()
    
    iosv.close()


"""
===============================================================================
STUDENT STUDY & TEACHING GUIDE
Script: napalmconfig4.py
Topic: Multi-Device Configuration & THE CLASSIC "STALE VARIABLE" LOGIC BUG
===============================================================================

1. WHAT IS THIS SCRIPT TRYING TO DO?
-----------------------------------
This script combines multi-device looping with multi-feature configuration:
  a) Loops through a list of devices: ['192.168.122.72', '192.168.122.73'].
  b) Connects to each device.
  c) Attempts to load and commit `ACL1.cfg`.
  d) Attempts to load and commit `ospf1.cfg`.
  e) Closes the connection and repeats for the next device.


2. THE CRITICAL TEACHING MOMENT: SPOT THE FATAL LOGIC BUG!
----------------------------------------------------------
**Ask the students to look closely at lines 23 through 29:**

    iosv.load_merge_candidate(filename='ospf1.cfg')
    if len(diffs) > 0:
        print(diffs)
        iosv.commit_config()
    else:
        print('No OSPF changes required.')
        iosv.discard_config()

QUESTION TO STUDENTS: "What is wrong with line 24?"
ANSWER: **`diffs = iosv.compare_config()` WAS NEVER CALLED FOR OSPF!**

Because of a copy-paste error, the programmer forgot to call `compare_config()`
after loading `ospf1.cfg`. The variable `diffs` is STALE—it still holds the result
from the ACL comparison on line 15!

TRACE THE TWO DISASTROUS REAL-WORLD OUTCOMES:
---------------------------------------------
Scenario 1: `ACL1.cfg` had changes (`len(diffs) > 0` was True):
  - The script loaded OSPF on line 23.
  - On line 24, `len(diffs) > 0` evaluates to True (using the ACL diff!).
  - Line 25 prints the OLD ACL diff (NOT the OSPF diff!).
  - Line 26 blindly commits OSPF without ever validating what is changing!

Scenario 2: `ACL1.cfg` had NO changes (`len(diffs) == 0` was False):
  - The script loaded OSPF on line 23.
  - On line 24, `len(diffs) > 0` evaluates to False (because ACL had 0 diffs).
  - The script drops into the `else` block on line 27.
  - It prints: 'No OSPF changes required.'  <-- FALSE!
  - It calls `iosv.discard_config()`.
  - Result: OSPF changes are SILENTLY THROWN AWAY and never applied!

This is one of the most famous categories of software bugs: the "Stale Variable"
bug caused by copy-pasting code without proper refactoring.


3. OTHER TRAPS IN THIS SCRIPT:
------------------------------
TRAP 2: Missing `discard_config()` on ACL Else-Branch:
  - On line 20, if ACL had no changes, it prints the message but forgot to call
    `iosv.discard_config()` before loading OSPF.

TRAP 3: Driver Reloaded in Loop:
  - Line 11: `driver = get_network_driver('ios')` is repeatedly called inside
    the device loop. Move it outside!

TRAP 4: No Per-Device Error Isolation:
  - If device 192.168.122.72 fails to connect, the whole script crashes.
    Device 192.168.122.73 is never configured!


4. HOW TO WRITE THIS LIKE A PROFESSIONAL (CLEAN REFERENCE):
-----------------------------------------------------------
from pathlib import Path
from napalm import get_network_driver

BASE_DIR = Path(__file__).resolve().parent
DEVICES = ['192.168.122.72', '192.168.122.73']

# Pre-load driver once
driver = get_network_driver('ios')

CONFIG_JOBS = [
    ('Access-List', BASE_DIR / 'ACL1.cfg'),
    ('OSPF', BASE_DIR / 'ospf1.cfg'),
]

for ip in DEVICES:
    print(f"\n{'='*25} Configuring {ip} {'='*25}")
    device = driver(ip, 'azam', 'cisco')
    
    try:
        device.open()
        
        for job_name, config_file in CONFIG_JOBS:
            if not config_file.exists():
                print(f"[!] File not found: {config_file}")
                continue
                
            print(f"\n--> Staging {job_name} on {ip}...")
            device.load_merge_candidate(filename=str(config_file))
            
            # MUST compute diff fresh for EACH configuration!
            diffs = device.compare_config()
            
            if len(diffs) > 0:
                print(f"[{job_name} Diff on {ip}]:\n{diffs}")
                device.commit_config()
                print(f"[+] {job_name} committed successfully on {ip}.")
            else:
                print(f"[i] No {job_name} changes required on {ip}.")
                device.discard_config()
                
    except Exception as err:
        print(f"[!] Error configuring device {ip}: {err}")
        try:
            device.discard_config()
        except Exception:
            pass
            
    finally:
        try:
            device.close()
            print(f"[-] Session closed for {ip}.")
        except Exception:
            pass
===============================================================================
"""