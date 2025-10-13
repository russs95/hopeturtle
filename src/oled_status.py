#!/usr/bin/env python3
"""
HopeTurtle OLED Status Display 🐢
- Supports 128x64 and 128x32 OLEDs
- Text messages use size 12 font for readability
- Turtle animation uses size 7 font to fit six lines on screen
"""

import os, sys, time, traceback, glob, csv
from datetime import datetime
from math import radians, sin, cos, asin, sqrt

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
            "    ._______    ___  ",
            " /             \\|  0 | ",
            "|              |/ __\\| ",
            "|____________/      ",
            "  |__|  |__|         ",
        ],
        [
            "    ._______     ___  ",
            " /             \\ |  0 | ",
            "|              |/  __\\| ",
            "|____________ /      ",
            "    |__|  |__|         ",
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
    font_size = 8
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    try:
        while True:
            for frame in turtle_frames:
                img = Image.new("1", (device.width, device.height), 0)
                draw = ImageDraw.Draw(img)
                line_h = int(font_size * 1.3)
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

# ---------- GPS Helpers ----------
def _iter_recent_gps_rows():
    pattern = os.path.join(DATA_DIR, "*_gps.csv")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    for path in files:
        try:
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        for row in reversed(rows):
            if row:
                yield row


def _latest_row(status=None):
    for row in _iter_recent_gps_rows():
        if status is None or row.get("status", "").lower() == status:
            return row
    return None


def _safe_float(val):
    try:
        return float(val)
    except Exception:
        return None


def _km_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    rlat1, rlon1, rlat2, rlon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
    c = 2 * asin(min(1.0, sqrt(a)))
    earth_radius_km = 6371.0
    return earth_radius_km * c


def _format_coord(val, digits=5):
    try:
        return f"{float(val):.{digits}f}"
    except Exception:
        return str(val) if val is not None else "?"


# ---------- Command Handlers ----------
def _show_boot_message(device, waking=True):
    if waking:
        lines = ["HopeTurtle", "Waking up…"]
    else:
        now = datetime.now().strftime("%H:%M:%S")
        lines = ["HopeTurtle", "Systems alive", f"{now}"]
    _show_lines(device, lines, hold_s=4, center=True)


def _show_distance(device):
    row = _latest_row(status="fix") or _latest_row()
    if not row:
        _show_lines(device, ["No GPS data yet", "Run gps_snapshot"], hold_s=4, center=True)
        return

    lat = _safe_float(row.get("lat"))
    lon = _safe_float(row.get("lon"))
    km = _km_distance(lat, lon, REF_LAT, REF_LON)
    ts = row.get("timestamp_utc") or "(no time)"
    status = row.get("status", "?")

    if km is None:
        msg = ["Last GPS entry", status.upper(), ts, "Distance unavailable"]
    else:
        msg = [
            "To Al Mawasi",
            f"{km:.1f} km",
            f"Lat { _format_coord(lat) }",
            f"Lon { _format_coord(lon) }",
            ts,
        ]
    _show_lines(device, msg, hold_s=6, center=True)


def _show_brief(device):
    row = _latest_row(status="fix") or _latest_row()
    if not row:
        _show_lines(device, ["No GPS log yet"], hold_s=4, center=True)
        return

    ts = row.get("timestamp_utc") or "(no time)"
    status = row.get("status", "?").lower()
    sats = row.get("sats") or "?"
    hdop = row.get("hdop") or "?"
    lat = row.get("lat")
    lon = row.get("lon")
    lat_fmt = _format_coord(lat)
    lon_fmt = _format_coord(lon)
    km = _km_distance(_safe_float(lat), _safe_float(lon), REF_LAT, REF_LON)

    if status == "fix" and km is not None:
        lines = [
            "GPS Fix",
            ts,
            f"Lat {lat_fmt}",
            f"Lon {lon_fmt}",
            f"{km:.1f} km → Mawasi",
            f"Sats {sats}  HDOP {hdop}",
        ]
    elif status == "fix":
        lines = [
            "GPS Fix",
            ts,
            f"Lat {lat_fmt}",
            f"Lon {lon_fmt}",
            f"Sats {sats}  HDOP {hdop}",
        ]
    else:
        lines = [
            "Last GPS status",
            status.upper(),
            ts,
            f"Sats {sats}  HDOP {hdop}",
        ]
    _show_lines(device, lines, hold_s=6, center=True)


def _show_notify(device, kind):
    if kind == "install":
        lines = ["HopeTurtle", "Install complete", "🐢 Ready"]
    else:
        lines = ["HopeTurtle", "Update applied", "Reboot soon"]
    _show_lines(device, lines, hold_s=5, center=True)


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
        print("Usage: oled_status.py [swim|custom|boot-waking|boot-alive|distance|brief|notify-install|notify-update]")
        return 0

    device = _init_device()
    cmd = sys.argv[1].lower()

    try:
        if cmd == "swim":
            _swim_animation(device)
        elif cmd == "custom":
            _show_custom(device, sys.argv)
        elif cmd == "boot-waking":
            _show_boot_message(device, waking=True)
        elif cmd == "boot-alive":
            _show_boot_message(device, waking=False)
        elif cmd == "distance":
            _show_distance(device)
        elif cmd == "brief":
            _show_brief(device)
        elif cmd == "notify-install":
            _show_notify(device, "install")
        elif cmd == "notify-update":
            _show_notify(device, "update")
        else:
            _show_lines(device, [f"Unknown cmd:", cmd], hold_s=3, center=True)
    except Exception:
        traceback.print_exc()
    return 0


if __name__ == "__main__":
    sys.exit(main())



