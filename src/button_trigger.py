#!/usr/bin/env python3
"""
HopeTurtle Button Trigger 🐢
- Waits for a momentary button press on GPIO22 (pin 15).
- When pressed:
    • Shows a 1-second swimming animation
    • Displays “Checking GPS position at HH:MM:SS...”
    • Runs gps_snapshot.py
    • Displays the latest fix or 'no fix' message
"""

import RPi.GPIO as GPIO
import subprocess
import time
import os
import glob
import csv
from datetime import datetime

# --- Configuration ---
BUTTON_PIN = 22  # GPIO22 (pin 15)
DEBOUNCE_MS = 300
DATA_DIR = os.path.expanduser("~/hopeturtle/data")

# ---------- OLED Helper ----------
def oled_show(lines, hold_s=4):
    """Helper to display text on OLED via the 'custom' command."""
    try:
        subprocess.run(
            ["python3", "/home/hopeturtle/hopeturtle/src/oled_status.py", "custom"] + lines,
            check=False,
        )
        time.sleep(hold_s)  # keep message visible
    except Exception as e:
        print(f"[WARN] OLED display failed: {e}")

# ---------- Swimming Animation ----------
def swim_animation(duration_s=1.0):
    """Trigger the turtle swim animation on OLED."""
    print("[OLED] Starting turtle swim animation...")
    try:
        subprocess.run(
            ["python3", "/home/hopeturtle/hopeturtle/src/oled_status.py", "swim"],
            check=False,
            timeout=duration_s + 0.5,
        )
    except subprocess.TimeoutExpired:
        pass  # stop after duration
    except Exception as e:
        print(f"[WARN] Swim animation failed: {e}")

# ---------- Latest Fix Parser ----------
def latest_fix():
    """Return latest GPS fix info from CSV logs."""
    files = sorted(
        glob.glob(os.path.join(DATA_DIR, "*_gps.csv")),
        key=os.path.getmtime,
        reverse=True,
    )
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
                        "sats": row.get("sats") or "?",
                    }
        except Exception:
            continue
    return None

# ---------- Snapshot Routine ----------
def take_snapshot():
    print("🐢 Button pressed — capturing GPS snapshot…")

    # 1️⃣ Show the turtle swimming
    swim_animation(duration_s=1.0)

    # 2️⃣ Display the timestamped check message
    now = datetime.now().strftime("%H:%M:%S")
    oled_show([f"Checking GPS position", f"at {now}..."], hold_s=4)
    print(f"[OLED] Checking GPS position at {now}...")

    # 3️⃣ Run the GPS snapshot
    subprocess.run(
        ["python3", "/home/hopeturtle/hopeturtle/src/gps_snapshot.py"],
        check=False,
    )

    # 4️⃣ Retrieve the latest fix and display the result
    fix = latest_fix()
    if fix:
        msg = [
            f"Fix: {fix['lat'][:7]},",
            f"{fix['lon'][:7]}",
            f"{fix['km_to_mawasi']} km → Mawasi",
            f"Sats: {fix['sats']}",
        ]
        oled_show(msg, hold_s=4)
        print(f"✅ Fix displayed: {msg}")
    else:
        msg = ["No GPS fix yet", "Check sky view…"]
        oled_show(msg, hold_s=4)
        print("⚠️ No fix yet — displayed message on OLED.")

# ---------- GPIO Setup ----------
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("✅ HopeTurtle button listener active (press button to trigger snapshot)…")

try:
    while True:
        GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING, bouncetime=DEBOUNCE_MS)
        take_snapshot()
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\n👋 Exiting cleanly…")
finally:
    GPIO.cleanup()
