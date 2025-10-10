#!/usr/bin/env python3
"""
HopeTurtle Button Trigger
- Waits for a momentary button press on GPIO22 (pin 15).
- When pressed:
    • Shows “Logging GPS…” on OLED
    • Runs gps_snapshot.py
    • Then displays latest fix info on OLED (or 'no fix' message)
"""

import RPi.GPIO as GPIO
import subprocess
import time
import os
import glob
import csv
from datetime import datetime

BUTTON_PIN = 22  # GPIO 22 (pin 15)
DEBOUNCE_MS = 300
DATA_DIR = os.path.expanduser("~/hopeturtle/data")

def latest_fix():
    """Return latest fix info from CSV logs."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*_gps.csv")), key=os.path.getmtime, reverse=True)
    for fp in files:
        try:
            rows = list(csv.DictReader(open(fp)))
            for row in reversed(rows):
                if row.get("status", "").lower() == "fix":
                    return {
                        "timestamp": row.get("timestamp_utc"),
                        "lat": row.get("lat"),
                        "lon": row.get("lon"),
                        "km_to_mawasi": row.get("km_to_ref") or "?",
                        "sats": row.get("sats") or "?"
                    }
        except Exception:
            continue
    return None

def oled_show(lines):
    """Helper to display text on OLED via oled_status.py."""
    try:
        subprocess.run(["python3", "/home/hopeturtle/hopeturtle/src/oled_status.py"] + lines)
    except Exception as e:
        print(f"[WARN] OLED display failed: {e}")

def take_snapshot():
    print("🐢 Button pressed — capturing GPS snapshot…")
    # Step 1: Show message
    oled_show(["boot-waking"])
    time.sleep(0.5)
    # Step 2: Run GPS snapshot
    subprocess.run(["python3", "/home/hopeturtle/hopeturtle/src/gps_snapshot.py"])
    # Step 3: Retrieve fix and show
    fix = latest_fix()
    if fix:
        msg = [
            f"Fix: {fix['lat'][:7]},",
            f"{fix['lon'][:7]}",
            f"{fix['km_to_mawasi']} km → Mawasi",
            f"Sats: {fix['sats']}"
        ]
    else:
        msg = ["No GPS fix yet", "Check sky view…"]
    oled_show(["brief"])
    print("✅ OLED updated with latest GPS status.")

# --- GPIO setup ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("✅ HopeTurtle button listener active (press button to trigger snapshot)…")

try:
    while True:
        GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING, bouncetime=DEBOUNCE_MS)
        take_snapshot()
        time.sleep(0.3)
except KeyboardInterrupt:
    print("\n👋 Exiting cleanly…")
finally:
    GPIO.cleanup()
