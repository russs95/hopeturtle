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
sudo apt-get install -y \
  python3-serial python3-pil python3-numpy jq git i2c-tools \
  python3-pip fonts-dejavu-core build-essential make gcc g++ \
  libjpeg-dev zlib1g-dev

# ---- Ensure pigpio is built and installed ----
if ! command -v /usr/local/bin/pigpiod &>/dev/null; then
  echo "⚙️ pigpiod not found — building from source..."
  cd $HOME_DIR
  sudo rm -rf pigpio
  git clone https://github.com/joan2937/pigpio.git
  cd pigpio
  make -j4
  sudo make install
else
  echo "✅ pigpiod already installed."
fi

# ---- Install pigpiod systemd service ----
echo "==> Installing pigpiod systemd service..."
sudo tee /etc/systemd/system/pigpiod.service > /dev/null <<'EOF'
[Unit]
Description=Pigpio daemon for GPIO access
After=network.target

[Service]
ExecStart=/usr/local/bin/pigpiod -g
ExecStop=/bin/killall pigpiod
Type=simple
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

# ---- Enable pigpio daemon ----
echo "==> Starting pigpiod daemon..."
sudo systemctl daemon-reload
sudo systemctl stop pigpiod || true
sudo killall pigpiod || true
sudo rm -f /var/run/pigpio.pid /run/pigpio.pid || true
sudo systemctl enable --now pigpiod
sleep 2
sudo systemctl status pigpiod --no-pager || true

# ---- Enable full UART for SIM900 ----
if ! grep -q "^enable_uart=1" /boot/firmware/config.txt; then
  echo "enable_uart=1" | sudo tee -a /boot/firmware/config.txt
  echo "==> Enabled UART (pins 8/10). Reboot required for SIM900."
else
  echo "✅ UART already enabled."
fi

# ---- Ensure data dir exists ----
mkdir -p "$DATA_DIR"

# ---- Install HopeTurtle systemd services ----
echo "==> Installing HopeTurtle services..."
sudo cp systemd/hopeturtle-gps.* /etc/systemd/system/
sudo cp systemd/hopeturtle-boot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hopeturtle-gps.timer
sudo systemctl enable hopeturtle-boot.service

# ---- GUI autostart (optional) ----
AUTOSTART_DIR="$HOME_DIR/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cp scripts/show_logs.desktop "$AUTOSTART_DIR/" || true

# ---- Trigger one manual GPS run ----
echo "==> Triggering first GPS snapshot..."
sudo systemctl start hopeturtle-gps.service || true

# ---- Summary banner ----
cat <<'EOF'

    _________    ____
  /           \ |  o |
 |            |/ ___\|
 |____________|_/
   |__|  |__|

 Fresh Hope Turtle Code installed! 🐢

EOF

# ---- OLED notify (safe fallback) ----
python3 src/oled_status.py notify-install || true

echo "✅ Install complete."
echo "💡 pigpiod should now be active (check: systemctl status pigpiod)"
echo "💡 GPS will log every 5 minutes via hopeturtle-gps.timer"
echo "💡 OLED messages appear on boot via hopeturtle-boot.service"
echo "⚠️ If UART was just enabled, please reboot for SIM900 serial to function."
