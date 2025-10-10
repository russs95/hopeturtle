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
sudo apt-get update -y
sudo apt-get install -y python3-serial python3-pigpio jq python3-pil python3-numpy python3-pip fonts-dejavu-core git make

# ---- Ensure pigpiod daemon installed ----
echo "==> Checking pigpiod installation..."
if ! command -v /usr/local/bin/pigpiod >/dev/null 2>&1; then
    echo "⚠️  pigpiod not found in /usr/local/bin — installing from source..."
    cd /tmp
    rm -rf pigpio
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
echo "==> Enabling pigpiod daemon..."
sudo systemctl enable --now pigpiod || echo "⚠️ pigpiod failed to start, check with: sudo systemctl status pigpiod"

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
python3 -m pip install --upgrade --break-system-packages luma.oled luma.core || echo "⚠️ OLED libs install failed, continuing..."

# ---- Install systemd services ----
echo "==> Installing HopeTurtle services..."
sudo cp systemd/hopeturtle-gps.* /etc/systemd/system/
sudo cp systemd/hopeturtle-boot.service /etc/systemd/system/
sudo cp systemd/hopeturtle-button.service /etc/systemd/system/

sudo systemctl daemon-reload
echo "==> Enabling HopeTurtle systemd services..."
sudo systemctl enable --now hopeturtle-gps.timer || echo "⚠️ GPS timer failed to enable."
sudo systemctl enable --now hopeturtle-boot.service || echo "⚠️ Boot OLED service failed to enable."
sudo systemctl enable --now hopeturtle-button.service || echo "⚠️ Button trigger service failed to enable."

# ---- Removed GUI autostart block ----
# No autostart setup (headless configuration)
echo "==> Skipping GUI autostart setup (headless mode)."

# ---- Trigger one manual GPS run ----
echo "==> Triggering one manual GPS run..."
sudo systemctl start hopeturtle-gps.service || echo "⚠️ Manual GPS start failed."

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
python3 src/oled_status.py notify-install || echo "⚠️ OLED notification skipped."

echo "✅ Install complete."
echo "💡 Services active: pigpiod, hopeturtle-gps.timer, hopeturtle-boot.service, hopeturtle-button.service"
echo "⚠️ Reboot required if UART was newly enabled."
