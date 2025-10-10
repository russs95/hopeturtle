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

# ---- Ensure dependencies ----
echo "==> Installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3-serial python3-pigpio jq python3-pil python3-numpy python3-pip fonts-dejavu-core

# ---- Ensure pigpiod daemon installed ----
echo "==> Checking pigpiod installation..."
if ! command -v /usr/local/bin/pigpiod >/dev/null 2>&1; then
    echo "⚠️  pigpiod not found in /usr/local/bin — installing from source..."
    cd /tmp
    git clone https://github.com/joan2937/pigpio.git
    cd pigpio
    make
    sudo make install
    cd "$REPO_DIR"
else
    echo "✅ pigpiod already installed."
fi

# ---- Create pigpiod systemd service if missing ----
if [ ! -f /etc/systemd/system/pigpiod.service ]; then
    echo "==> Creating pigpiod systemd service..."
    sudo tee /etc/systemd/system/pigpiod.service > /dev/null <<'EOF'
[Unit]
Description=Pigpio daemon for GPIO access
After=network.target

[Service]
ExecStart=/usr/local/bin/pigpiod -g
ExecStop=/bin/systemctl kill pigpiod
Type=simple
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
fi

# ---- Enable pigpiod daemon ----
sudo systemctl enable --now pigpiod

# ---- Ensure data dir exists ----
mkdir -p "$DATA_DIR"

# ---- Enable UART for SIM900 ----
if ! grep -q "^enable_uart=1" /boot/firmware/config.txt; then
  echo "enable_uart=1" | sudo tee -a /boot/firmware/config.txt
  echo "⚙️  UART enabled (reboot required for SIM900)."
else
  echo "✅ UART already enabled."
fi

# ---- Install Python OLED libraries ----
echo "==> Installing OLED dependencies..."
python3 -m pip install --upgrade --break-system-packages luma.oled luma.core || true

# ---- Install systemd services ----
echo "==> Installing HopeTurtle services..."
sudo cp systemd/hopeturtle-gps.* /etc/systemd/system/
sudo cp systemd/hopeturtle-boot.service /etc/systemd/system/
sudo cp systemd/hopeturtle-button.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now hopeturtle-gps.timer
sudo systemctl enable --now hopeturtle-boot.service
sudo systemctl enable --now hopeturtle-button.service

# ---- GUI Autostart Cleanup ----
# NOTE: The old show_logs.desktop file no longer exists — skipping autostart setup.
# AUTOSTART_DIR="$HOME_DIR/.config/autostart"
# mkdir -p "$AUTOSTART_DIR"
# cp scripts/show_logs.desktop "$AUTOSTART_DIR/" || echo "Skipping missing show_logs.desktop."

# ---- Trigger one manual GPS run ----
echo "==> Triggering one manual GPS run..."
sudo systemctl start hopeturtle-gps.service || true

# ---- Final Summary ----
cat <<'EOF'

    _________    ____
  /           \ |  o |
 |            |/ ___\|
 |____________|_/
   |__|  |__|

🐢 Fresh HopeTurtle Code Installed!

EOF

# ---- OLED Notification ----
python3 src/oled_status.py notify-install || true

echo "✅ Install complete."
echo "💡 Services active: pigpiod, hopeturtle-gps.timer, hopeturtle-boot.service, hopeturtle-button.service"
echo "⚠️  Reboot required if UART was newly enabled."
