#!/usr/bin/env python3
"""
HopeTurtle Button Trigger 🐢
- Waits for button press on GPIO22 (pin 15)
- When pressed:
    1️⃣ Shows “Checking GPS position at HH:MM:SS...”
    2️⃣ Runs gps_snapshot.py repeatedly every few seconds
    3️⃣ Shows turtle swimming on OLED while waiting
    4️⃣ Displays GPS fix info for 5 seconds once obtained
"""

import RPi.GPIO as GPIO
import subprocess
import time
import os
import glob
import csv
from datetime import datetime

BUTTON_PIN = 22  # GPIO22 (pin 15)
DEBOUNCE_MS = 300
DATA_DIR = os.path.expanduser("~/hopeturtle/data")

# ---------- OLED Helper ----------
def oled_show(lines, hold_s=4):
    """Show text on OLED via oled_status.py custom"""
    try:
        subprocess.run(
            ["python3", "/home/hopeturtle/hopeturtle/src/oled_status.py", "custom"] + lines,
            check=False,
        )
        if hold_s:
            time.sleep(hold_s)
    except Exception as e:
        print(f"[WARN] OLED display failed: {e}")

def oled_swim_loop():
    """Start continuous swimming animation until interrupted."""
    try:
        swim_proc = subprocess.Popen(
            ["python3", "/home/hopeturtle/hopeturtle/src/oled_status.py", "swim"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return swim_proc
    except Exception as e:
        print(f"[WARN] Swim animation failed: {e}")
        return None

# ---------- Latest Fix Parser ----------
def latest_fix():
    """Return latest GPS fix info from CSV logs."""
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
                        "sats": row.get("sats") or "?",
                    }
        except Exception:
            continue
    return None

# ---------- Snapshot Routine ----------
def take_snapshot():
    print("🐢 Button pressed — initiating GPS sequence…")

    # 1️⃣ Show timestamped check message
    now = datetime.now().strftime("%H:%M:%S")
    oled_show([f"Checking GPS position", f"at {now}..."], hold_s=4)

    # 2️⃣ Start swim animation loop
    swim_proc = oled_swim_loop()
    print("[OLED] Swimming until GPS fix detected...")

    # 3️⃣ Loop until GPS fix found
    fix = None
    for attempt in range(15):  # ~15 attempts (~30-45 sec total)
        subprocess.run(
            ["python3", "/home/hopeturtle/hopeturtle/src/gps_snapshot.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        fix = latest_fix()
        if fix:
            break
        time.sleep(3)

    # 4️⃣ Stop swim animation
    if swim_proc:
        swim_proc.terminate()
        time.sleep(0.5)

    # 5️⃣ Display result
    if fix:
        msg = [
            f"Fix: {fix['lat'][:7]},",
            f"{fix['lon'][:7]}",
            f"{fix['km_to_mawasi']} km → Mawasi",
            f"Sats: {fix['sats']}",
        ]
        oled_show(msg, hold_s=5)
        print(f"✅ Fix displayed: {msg}")
    else:
        oled_show(["No GPS fix yet", "Check sky view…"], hold_s=5)
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
