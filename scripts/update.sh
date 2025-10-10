#!/bin/bash
set -e

echo "==> HopeTurtle updater starting..."

REPO_DIR="$HOME/hopeturtle"

# ---- Go to repo and update ----
cd "$REPO_DIR"
echo "==> Pulling latest from Git..."
git fetch origin
git reset --hard origin/main

# ---- Ensure scripts are executable ----
chmod +x scripts/install.sh scripts/update.sh

# ---- Stop running services safely ----
echo "==> Stopping existing services..."
sudo systemctl stop hopeturtle-gps.timer || true
sudo systemctl stop hopeturtle-gps.service || true
sudo systemctl stop hopeturtle-boot.service || true
sudo systemctl stop pigpiod || true
sudo killall pigpiod || true
sudo rm -f /var/run/pigpio.pid /run/pigpio.pid || true

# ---- Re-run full installer ----
echo "==> Running installer..."
./scripts/install.sh

# ---- Restart key services ----
sudo systemctl restart hopeturtle-gps.timer || true
sudo systemctl restart hopeturtle-boot.service || true
sudo systemctl restart pigpiod || true

# ---- OLED notify ----
python3 src/oled_status.py notify-update || true

# ---- Final banner ----
cat <<'EOF'

    _________    ____
  /           \ |  o |
 |            |/ ___\|
 |____________|_/
   |__|  |__|

 Hope Turtle Code is updated! 🐢

EOF

echo "✅ Update complete."
echo "💡 GPS and OLED services restarted."
