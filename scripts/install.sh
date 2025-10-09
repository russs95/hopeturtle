#!/bin/bash
set -e

echo "==> HopeTurtle installer starting..."

USER=$(whoami)
HOME_DIR=$(eval echo ~$USER)
REPO_DIR="$HOME_DIR/hopeturtle"
DATA_DIR="$REPO_DIR/data"

echo "==> Repo: $REPO_DIR"
echo "==> Using user: $USER (home: $HOME_DIR)"
echo "==> Data dir: $DATA_DIR"

# ---------------------------------------------------------
# (1) Dependency Installation
# ---------------------------------------------------------
echo "==> Installing dependencies..."
sudo apt-get update

# Note: 'pigpio' is deprecated on Debian 12/Trixie — replaced by python3-pigpio
sudo apt-get install -y \
  python3-serial \
  python3-pigpio \
  python3-pil \
  python3-numpy \
  jq \
  fonts-dejavu-core || echo "⚠️ Some non-critical packages may have failed."

# ---------------------------------------------------------
# (2) Enable pigpiod daemon (for soft-serial GPS)
# ---------------------------------------------------------
echo "==> Enabling pigpiod..."
if systemctl list-unit-files | grep -q pigpiod.service; then
  sudo systemctl enable --now pigpiod
else
  echo "⚠️ pigpiod service not found — installing pigpio tools..."
  sudo apt-get install -y pigpio-tools || true
  sudo systemctl enable --now pigpiod || true
fi

# ---------------------------------------------------------
# (3) Ensure data directory exists
# ---------------------------------------------------------
mkdir -p "$DATA_DIR"
sudo chown "$USER:$USER" "$DATA_DIR"

# ---------------------------------------------------------
# (4) Enable UART for SIM900 (pins 8/10)
# ---------------------------------------------------------
CONFIG_FILE="/boot/firmware/config.txt"
if ! grep -q "^enable_uart=1" "$CONFIG_FILE"; then
  echo "enable_uart=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
  echo "==> Enabled full UART for SIM900 (pins 8/10). Reboot required."
else
  echo "==> UART already enabled."
fi

# ---------------------------------------------------------
# (5) Install systemd services
# ---------------------------------------------------------
echo "==> Installing systemd service + timer..."
sudo cp systemd/hopeturtle-gps.* /etc/systemd/system/
sudo cp systemd/hopeturtle-boot.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now hopeturtle-gps.timer
sudo systemctl enable hopeturtle-boot.service

# ---------------------------------------------------------
# (6) GUI autostart for logs (if running desktop)
# ---------------------------------------------------------
AUTOSTART_DIR="$HOME_DIR/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cp scripts/show_logs.desktop "$AUTOSTART_DIR/" 2>/dev/null || true

# ---------------------------------------------------------
# (7) Trigger one manual GPS run
# ---------------------------------------------------------
echo "==> Triggering one manual GPS run..."
sudo systemctl start hopeturtle-gps.service || true

# ---------------------------------------------------------
# (8) Final Messages (ASCII + OLED)
# ---------------------------------------------------------
cat <<'EOF'

    _________    ____
  /           \ |  o |
 |            |/ ___\|
 |____________|_/
   |__|  |__|

 Fresh Hope Turtle Code installed! 🐢

EOF

# OLED notification (safe fallback if OLED not connected)
if python3 - <<'PY'
try:
    import luma.core, luma.oled
    print("OLED libraries detected.")
    exit(0)
except Exception:
    exit(1)
PY
then
  python3 src/oled_status.py notify-install || true
else
  echo "[OLED] Skipped (no luma.oled installed or device not found)."
fi

# ---------------------------------------------------------
# (9) Summary
# ---------------------------------------------------------
echo "✅ Install complete."
echo "⚠️ If 'enable_uart=1' was just added, please reboot for SIM900 to work."
echo "💡 GPS will read via pigpio soft-serial on GPIO17 (pin 11)."
echo "💡 OLED boot messages will now appear at startup via hopeturtle-boot.service."
