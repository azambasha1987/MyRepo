#!/usr/bin/env python3
"""
================================================================================
Azam Basha 3 Months (Quarterly) Upstream Intelligence Scanner Entrypoint
================================================================================
Canonical entrypoint wrapper for the 3 Months Update Check Scanner, ensuring
both quarterly and legacy weekly CLI invocations execute cleanly.
================================================================================
"""
import sys
import os
import runpy

script_dir = os.path.dirname(os.path.abspath(__file__))
scanner_script = os.path.join(script_dir, "azambasha-weekly-codeberg-scanner.py")

if __name__ == "__main__":
    runpy.run_path(scanner_script, run_name="__main__")
