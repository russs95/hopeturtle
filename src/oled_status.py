#!/usr/bin/env python3
"""
HopeTurtle OLED Status Display 🐢
- Supports 128x64 and 128x32 OLEDs
- Text messages use size 12 font for readability
- Turtle animation uses size 8 font for proper fit
"""

import os, sys, time, traceback
from datetime import datetime

# ---------- Config ----------
DATA_DIR = os.path.expanduser(os.getenv("HT_DATA_DIR", "~/hopeturtle/data"))
REF_LAT = float(os.getenv("HT_REF_LAT", "31.283"))
REF_LON = float(os.getenv("HT_REF_LON", "34.234"))

# ---------- OLED Setup ----------
def _init_device():
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        serial = i2c(port=1, address=0x3C)
        return ssd1306(serial)
    except Exception as e:
        print(f"[OLED] Not available: {e}")
        return None

def _clear(device):
    """Blank the screen."""
    if device is None:
        return
    from PIL import Image
    img = Image.new("1", (device.width, device.height), 0)
    device.display(img)

# ---------- Text Display ----------
def _show_lines(device, lines, hold_s=None, center=True):
    """Render text messages in size 12."""
    if device is None:
        print("[OLED] (simulated)", " | ".join(lines))
        if hold_s:
            time.sleep(hold_s)
        else:
            while True:
                time.sleep(60)
        return

    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("1", (device.width, device.height), 0)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        font = ImageFont.load_default()

    W, H = device.width, device.height
    line_h = 14
    total_h = len(lines) * line_h
    y0 = (H - total_h) // 2 if center else 0

    for i, t in enumerate(lines[:5]):
        t = str(t)
        l, t0, r, b = draw.textbbox((0, 0), t, font=font)
        w = r - l
        x = (W - w) // 2 if center else 0
        draw.text((x, y0 + i * line_h), t, fill=1, font=font)

    device.display(img)
    if hold_s:
        time.sleep(hold_s)
        _clear(device)

# ---------- Turtle Animation ----------
def _swim_animation(device):
    """Continuously show turtle swim animation until terminated."""
    turtle_frames = [
        [
            "                    "
            "   _________   ____  ",
            " /          \\|  0 | ",
            "|           |/ __\\| ",
            "|_____________/     ",
            "  |__|  |__|        ",
        ],
        [
            "                    "
            "   _________   ____  ",
            " /          \\|  0 | ",
            "|           |/ __\\| ",
            "|_____________/     ",
            "   |__|  |__|      ",
        ],
    ]

    if device is None:
        print("[OLED] Simulated swimming… press Ctrl+C to stop.")
        while True:
            for frame in turtle_frames:
                os.system("clear")
                for line in frame:
                    print(line)
                time.sleep(0.5)
        return

    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 8)
    except Exception:
        font = ImageFont.load_default()

    try:
        while True:
            for frame in turtle_frames:
                img = Image.new("1", (device.width, device.height), 0)
                draw = ImageDraw.Draw(img)
                line_h = 10
                total_h = len(frame) * line_h
                y0 = (device.height - total_h) // 2
                for i, t in enumerate(frame):
                    l, t0, r, b = draw.textbbox((0, 0), t, font=font)
                    w = r - l
                    x = (device.width - w) // 2
                    draw.text((x, y0 + i * line_h), t, fill=1, font=font)
                device.display(img)
                time.sleep(0.5)
    except KeyboardInterrupt:
        _clear(device)

# ---------- Custom Text ----------
def _show_custom(device, args):
    """Display custom text lines from CLI arguments."""
    lines = args[2:]
    if not lines:
        lines = ["(no text)"]
    _show_lines(device, lines, hold_s=4, center=True)

# ---------- Main ----------
def main():
    if len(sys.argv) < 2:
        print("Usage: oled_status.py [swim|custom]")
        return 0

    device = _init_device()
    cmd = sys.argv[1].lower()

    try:
        if cmd == "swim":
            _swim_animation(device)
        elif cmd == "custom":
            _show_custom(device, sys.argv)
        else:
            _show_lines(device, [f"Unknown cmd:", cmd], hold_s=3, center=True)
    except Exception:
        traceback.print_exc()
    return 0


if __name__ == "__main__":
    sys.exit(main())



