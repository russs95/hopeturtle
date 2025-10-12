#!/usr/bin/env python3
"""
HopeTurtle OLED Status Display 🐢
- Auto-detects 128x64 vs 128x32 OLED
- Compatible with 0.91" and 0.96" SSD1306 I2C displays
- Displays startup, GPS, and custom messages

Usage examples:
  python3 oled_status.py boot-waking
  python3 oled_status.py boot-alive
  python3 oled_status.py gps-searching
  python3 oled_status.py swim
  python3 oled_status.py distance
  python3 oled_status.py brief
  python3 oled_status.py custom "Line 1" "Line 2"
"""

import os, sys, time, traceback, glob, csv, math
from datetime import datetime, timezone

# ---------- Config ----------
DATA_DIR = os.path.expanduser(os.getenv("HT_DATA_DIR", "~/hopeturtle/data"))
REF_LAT = float(os.getenv("HT_REF_LAT", "31.283"))
REF_LON = float(os.getenv("HT_REF_LON", "34.234"))
BETA_TEST_MODE = os.getenv("HT_OLED_BETA", "NO").upper()

# ---------- OLED Setup ----------
def _init_device():
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        serial = i2c(port=1, address=0x3C)
        return ssd1306(serial)
    except Exception as e:
        print(f"[OLED] Not available: {e.__class__.__name__}: {e}")
        return None

def _prep_canvas(device):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("1", (device.width, device.height), 0)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
    return img, draw, font

def _clear(device):
    if device is None:
        return
    from PIL import Image
    img = Image.new("1", (device.width, device.height), 0)
    device.display(img)

def _show_lines(device, lines, hold_s=4, center=False):
    """Render text lines centered for hold_s seconds"""
    if device is None:
        print("[OLED] (simulated)", " | ".join(lines))
        time.sleep(hold_s)
        return

    from PIL import Image
    img, draw, font = _prep_canvas(device)
    W, H = device.width, device.height

    # Dynamic line spacing
    if H <= 32:
        line_h = 12
    elif H <= 48:
        line_h = 14
    else:
        line_h = 16

    total_h = len(lines) * line_h
    y0 = (H - total_h) // 2 if center else 0

    for i, t in enumerate(lines[:5]):
        t = str(t)
        l, t0, r, b = draw.textbbox((0, 0), t, font=font)
        w = r - l
        x = (W - w) // 2 if center else 0
        draw.text((x, y0 + i * line_h), t, fill=1, font=font)

    device.display(img)
    time.sleep(hold_s)
    _clear(device)

def _swim_animation(device):
    """Show two HopeTurtle ASCII frames for a smooth 2-second 'swim'."""
    turtle_frames = [
        [
            "   _________    ____   ",
            "  /           \\ |  o | ",
            " |            |/ ___\\| ",
            " |____________|_/      ",
            "   |__|  |__|          ",
        ],
        [
            "   _________    ____   ",
            "  /           \\ |  o | ",
            " |            |/ ___\\| ",
            " |____________|_/      ",
            "   |_  |__|  _|        ",
        ],
    ]

    if device is None:
        print("[OLED] (simulated swim)")
        for frame in turtle_frames:
            for line in frame:
                print(line)
            print("—")
            time.sleep(1.0)
        return

    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
    except Exception:
        font = ImageFont.load_default()

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
        time.sleep(1.0)  # 1 second per frame

    _clear(device)

def _show_custom(device, args):
    """
    Display custom text lines from CLI arguments.
    Usage:
      python3 oled_status.py custom "Line 1" "Line 2"
    If called with 'hold_s=None', message stays until overwritten.
    """
    lines = args[2:]
    if not lines:
        lines = ["(no text)"]

    # Keep indefinitely (for "Checking GPS...")
    if any("checking gps" in l.lower() for l in lines):
        _show_lines(device, lines, hold_s=None, center=True)
    else:
        _show_lines(device, lines, hold_s=4, center=True)

def _show_lines(device, lines, hold_s=None, center=False):
    """
    Render text; if hold_s is None, keep the message displayed indefinitely.
    """
    if device is None:
        print("[OLED] (simulated)", " | ".join(lines))
        if hold_s:
            time.sleep(hold_s)
        else:
            print("[OLED] holding indefinitely (no timeout)")
            while True:
                time.sleep(60)
        return

    from PIL import Image
    img, draw, font = _prep_canvas(device)
    W, H = device.width, device.height

    # Smaller font to fit more lines (esp. for 128x64)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except Exception:
        font = ImageFont.load_default()

    line_h = 10 if H <= 64 else 12
    total_h = len(lines) * line_h
    y0 = (H - total_h) // 2 if center else 0

    for i, t in enumerate(lines[:7]):
        t = str(t)
        l, t0, r, b = draw.textbbox((0, 0), t, font=font)
        w = r - l
        x = (W - w) // 2 if center else 0
        draw.text((x, y0 + i * line_h), t, fill=1, font=font)

    device.display(img)

    if hold_s:
        time.sleep(hold_s)
        _clear(device)


# ---------- Custom Text Display ----------
def _show_custom(device, args):
    """Display custom text lines for 4 seconds."""
    lines = args[2:]
    if not lines:
        lines = ["(no text)"]
    _show_lines(device, lines, hold_s=4, center=True)

# ---------- GPS helpers ----------
def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _find_last_fix_from_csvs(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "*_gps.csv")), key=os.path.getmtime, reverse=True)
    for fp in files:
        try:
            rows = list(csv.DictReader(open(fp)))
            for row in reversed(rows):
                if (row.get("status") or "").lower() == "fix" and row.get("lat") and row.get("lon"):
                    return fp, row.get("timestamp_utc"), float(row["lat"]), float(row["lon"]), row.get("sats") or "?"
        except Exception:
            continue
    return None, None, None, None, None

def _show_last_distance(device):
    fp, ts, lat, lon, sats = _find_last_fix_from_csvs(DATA_DIR)
    if not fp:
        _show_lines(device, ["No last fix", "found"], center=True)
        return
    km = _haversine_km(lat, lon, REF_LAT, REF_LON)
    lines = [f"{km:.1f} km → Mawasi", f"({lat:.3f},{lon:.3f})", f"Sats: {sats}", ts]
    _show_lines(device, lines, center=True)

def _show_brief(device):
    fp, ts, lat, lon, sats = _find_last_fix_from_csvs(DATA_DIR)
    if not fp:
        _show_lines(device, ["No fix yet", "Check GPS..."], center=True)
        return
    km = _haversine_km(lat, lon, REF_LAT, REF_LON)
    lines = [f"{lat:.3f},{lon:.3f}", f"{km:.1f} km → Mawasi", f"Sats: {sats}"]
    _show_lines(device, lines, center=True)

# ---------- Main ----------
def main():
    if len(sys.argv) < 2:
        print("Usage: oled_status.py [boot-waking|boot-alive|gps-searching|swim|distance|brief|custom]")
        return 0

    device = _init_device()
    cmd = sys.argv[1].lower()

    try:
        if cmd == "boot-waking":
            _show_lines(device, ["Hope Turtle", "is waking up!"], center=True)
        elif cmd == "boot-alive":
            _show_lines(device, ["Hope Turtle", "is alive!"], center=True)
        elif cmd == "gps-searching":
            _show_lines(device, ["GPS:", "Searching satellites…"], center=True)
        elif cmd == "swim":
            _swim_animation(device)
        elif cmd == "distance":
            _show_last_distance(device)
        elif cmd == "brief":
            _show_brief(device)
        elif cmd == "custom":
            _show_custom(device, sys.argv)
        else:
            _show_lines(device, [f"Unknown cmd:", cmd], center=True)
    except Exception:
        traceback.print_exc()
    return 0


if __name__ == "__main__":
    sys.exit(main())
