#!/bin/bash
set -e

echo "==> HopeTurtle installer starting..."

# Determine which user's home directory should hold the repo. When the
# installer is invoked with sudo we want to keep using the calling user's
# home directory instead of /root.
if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    USER="$SUDO_USER"
else
    USER=$(whoami)
fi

HOME_DIR=$(eval echo ~$USER)
REPO_DIR="$HOME_DIR/hopeturtle"
SCRIPT_REPO_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REPO_URL="https://github.com/russs95/hopeturtle-beta.git"
LOG_FILE="/var/log/hopeturtle-install.log"

# ---- Ensure repository is present and tracking the correct remote ----
# If the script is being run from within a cloned repository, prefer that
# location so we do not attempt to clone over it.
if [ -d "$SCRIPT_REPO_DIR/.git" ]; then
    REPO_DIR="$SCRIPT_REPO_DIR"
    echo "==> Detected existing checkout at $REPO_DIR (running installer from repo)."
fi

DATA_DIR="$REPO_DIR/data"

echo "==> Repo: $REPO_DIR"
echo "==> Repo URL: $REPO_URL"
echo "==> Using user: $USER (home: $HOME_DIR)"
echo "==> Data dir: $DATA_DIR"
echo "==> Logging to $LOG_FILE"

if [ ! -d "$REPO_DIR/.git" ]; then
    if [ -e "$REPO_DIR" ] && [ "$(ls -A "$REPO_DIR" 2>/dev/null)" ]; then
        echo "❌ Existing directory at $REPO_DIR is not a git repository. Please move or remove it and re-run the installer."
        exit 1
    else
        echo "==> Cloning HopeTurtle repository..."
        git clone "$REPO_URL" "$REPO_DIR"
    fi
else
    echo "==> Ensuring HopeTurtle repository remote is up to date..."
    if ! CURRENT_REMOTE=$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null); then
        CURRENT_REMOTE=""
    fi
    if [ "$CURRENT_REMOTE" != "$REPO_URL" ]; then
        echo "➡️  Updating origin remote to $REPO_URL"
        git -C "$REPO_DIR" remote set-url origin "$REPO_URL"
    fi
fi

# ---- Ensure dependencies ----
echo "==> Installing dependencies..."
sudo apt-get update -y
sudo apt-get install -y python3-serial python3-pigpio jq python3-pil python3-numpy python3-pip fonts-dejavu-core git make

# ---- Ensure pigpiod daemon installed ----
echo "==> Checking pigpiod installation..."
if ! command -v /usr/local/bin/pigpiod >/dev/null 2>&1; then
    echo "⚠️  pigpiod not found — installing from source..."
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

# ---- Install HopeTurtle services ----
echo "==> Installing HopeTurtle systemd service files..."
sudo cp systemd/hopeturtle-gps.* /etc/systemd/system/
sudo cp systemd/hopeturtle-boot.service /etc/systemd/system/
sudo cp systemd/hopeturtle-button.service /etc/systemd/system/
sudo systemctl daemon-reload

# ---- Enable services safely (non-blocking) ----
echo "==> Enabling HopeTurtle services (non-blocking)..."
SERVICES=(
  "pigpiod"
  "hopeturtle-gps.timer"
  "hopeturtle-boot.service"
  "hopeturtle-button.service"
)

for svc in "${SERVICES[@]}"; do
    echo "➡️  Enabling $svc..."
    {
        timeout 10 sudo systemctl enable --now "$svc"
        STATUS=$?
        if [ $STATUS -eq 0 ]; then
            echo "✅ $svc enabled successfully."
        else
            echo "⚠️ Failed to enable $svc (exit code $STATUS). Check systemctl status $svc for details."
        fi
    } 2>&1 | tee -a "$LOG_FILE"
done

# ---- Skip GUI autostart (headless mode) ----
echo "==> Skipping GUI autostart setup (headless mode)."

# ---- Trigger one manual GPS run ----
echo "==> Triggering one manual GPS run..."
sudo systemctl start hopeturtle-gps.service || echo "⚠️ Manual GPS run failed."

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

# ---- Refresh OLED + button services ----
echo "==> Reloading OLED and button services..."
for svc in "hopeturtle-oled-boot.service" "hopeturtle-button.service"; do
    echo "➡️  Restarting $svc..."
    if sudo systemctl restart "$svc"; then
        echo "✅ $svc restarted."
    else
        echo "⚠️ Failed to restart $svc. Check with: sudo systemctl status $svc"
    fi
done

echo "✅ Install complete."
echo "💡 Services active: pigpiod, hopeturtle-gps.timer, hopeturtle-boot.service, hopeturtle-button.service"
echo "⚠️ Reboot required if UART was newly enabled."
echo "📜 Detailed log saved to $LOG_FILE"
