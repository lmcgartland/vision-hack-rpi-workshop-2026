#!/bin/bash
# ============================================
# Pi Workshop Setup Script
# Run this ONCE on each Pi before the workshop
# Usage: sudo bash setup-pi.sh <pi-number> <hub-ip>
# Example: sudo bash setup-pi.sh 3 192.168.8.100
# ============================================

set -e

PI_NUM=${1:?"Usage: sudo bash setup-pi.sh <pi-number> <hub-ip>"}
HUB_IP=${2:?"Usage: sudo bash setup-pi.sh <pi-number> <hub-ip>"}

PI_HOSTNAME="pi-$(printf '%02d' $PI_NUM)"
PI_IP="192.168.8.1$(printf '%02d' $PI_NUM)"

echo "========================================="
echo "Setting up $PI_HOSTNAME ($PI_IP)"
echo "Hub IP: $HUB_IP"
echo "========================================="

# --- Set hostname ---
echo "$PI_HOSTNAME" > /etc/hostname
sed -i "s/127.0.1.1.*/127.0.1.1\t$PI_HOSTNAME/" /etc/hosts
hostnamectl set-hostname "$PI_HOSTNAME"
echo "✅ Hostname set to $PI_HOSTNAME"

# --- Configure static IP (for dhcpcd-based systems) ---
if [ -f /etc/dhcpcd.conf ]; then
    # Remove any existing static config for wlan0
    sed -i '/^# WORKSHOP-STATIC-BEGIN/,/^# WORKSHOP-STATIC-END/d' /etc/dhcpcd.conf

    cat >> /etc/dhcpcd.conf << EOF
# WORKSHOP-STATIC-BEGIN
interface wlan0
static ip_address=${PI_IP}/24
static routers=192.168.8.1
static domain_name_servers=8.8.8.8
# WORKSHOP-STATIC-END
EOF
    echo "✅ Static IP configured: $PI_IP (dhcpcd)"
else
    echo "⚠️  No /etc/dhcpcd.conf found — configure static IP manually via nmtui or netplan"
fi

# --- Ensure SSH is enabled ---
systemctl enable ssh
systemctl start ssh
echo "✅ SSH enabled"

# --- Install shellinabox as browser-based SSH fallback ---
apt-get update -qq
apt-get install -y -qq shellinabox > /dev/null 2>&1
systemctl enable shellinabox
systemctl start shellinabox
echo "✅ shellinabox installed (browser SSH on port 4200)"

# --- Set up the chat server directory ---
CHAT_DIR="/home/pi/chat-server"
mkdir -p "$CHAT_DIR/templates" "$CHAT_DIR/static"

# Create virtual environment and install deps
cd "$CHAT_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --quiet flask requests
deactivate
echo "✅ Virtual environment created with flask + requests"

# --- Copy server files ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cp "$SCRIPT_DIR/app.py" "$CHAT_DIR/app.py"
cp "$SCRIPT_DIR/templates/chat.html" "$CHAT_DIR/templates/chat.html"
cp "$SCRIPT_DIR/start.sh" "$CHAT_DIR/start.sh"
cp "$SCRIPT_DIR/requirements.txt" "$CHAT_DIR/requirements.txt"
chmod +x "$CHAT_DIR/start.sh"

# --- Set the hub URL in app.py ---
sed -i "s|http://192.168.8.100:5000|http://${HUB_IP}:5000|g" "$CHAT_DIR/app.py"
echo "✅ Hub URL set to http://${HUB_IP}:5000"

# --- Set ownership ---
chown -R pi:pi "$CHAT_DIR"
echo "✅ File ownership set to pi user"

# --- Set password to 'workshop' ---
echo "pi:workshop" | chpasswd
echo "✅ Password set to 'workshop'"

echo ""
echo "========================================="
echo "✅ $PI_HOSTNAME is ready!"
echo ""
echo "  Hostname:     $PI_HOSTNAME"
echo "  Static IP:    $PI_IP"
echo "  SSH:          ssh pi@$PI_IP"
echo "  Password:     workshop"
echo "  ShellInABox:  https://$PI_IP:4200"
echo "  Chat Server:  http://$PI_IP:5000"
echo ""
echo "  To start:     cd chat-server && bash start.sh"
echo "========================================="
echo ""
echo "⚠️  Reboot the Pi for hostname and IP changes to take effect:"
echo "    sudo reboot"
