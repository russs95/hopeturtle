#!/usr/bin/env python3
"""
HopeTurtle Button Trigger
- Waits for momentary button press on GPIO22.
- When pressed, triggers GPS snapshot and OLED status display.
"""

import RPi.GPIO as GPIO
import subprocess
import time

BUTTON_PIN = 22  # Pin 15
DEBOUNCE_MS = 300

def take_snapshot():
    print("🐢 Button pressed — capturing GPS snapshot…")
    subprocess.run(["python3", "/home/hopeturtle/hopeturtle/src/gps_snapshot.py"])
    subprocess.run(["python3", "/home/hopeturtle/hopeturtle/src/oled_status.py", "brief"])

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("✅ HopeTurtle button listener active (press to trigger snapshot)…")

try:
    while True:
        GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING, bouncetime=DEBOUNCE_MS)
        take_snapshot()
        time.sleep(0.2)
except KeyboardInterrupt:
    print("\n👋 Exiting cleanly…")
finally:
    GPIO.cleanup()
