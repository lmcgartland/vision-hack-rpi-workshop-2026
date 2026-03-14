#!/bin/bash
# ============================================
# Workshop Pre-Flight Check
# Run from instructor laptop on workshop WiFi
# Usage: bash preflight.sh [num-pis] [base-ip]
# Example: bash preflight.sh 10 192.168.8
# ============================================

NUM_PIS=${1:-10}
BASE_IP=${2:-"192.168.8"}
HUB_IP="${BASE_IP}.100"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "🔍 Workshop Pre-Flight Check"
echo "========================================="
echo "Checking $NUM_PIS Pis on ${BASE_IP}.101-${BASE_IP}.1$(printf '%02d' $NUM_PIS)"
echo ""

# --- Check hub ---
echo "--- Hub Server (${HUB_IP}) ---"
if ping -c1 -W2 "$HUB_IP" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Hub reachable${NC}"
else
    echo -e "  ${RED}❌ Hub NOT reachable at ${HUB_IP}${NC}"
fi

# Check if hub Flask is running
if curl -s --connect-timeout 2 "http://${HUB_IP}:5000/health" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Hub Flask server running${NC}"
else
    echo -e "  ${YELLOW}⚠️  Hub Flask not running (start with: bash start-hub.sh)${NC}"
fi
echo ""

# --- Check each Pi ---
echo "--- Student Pis ---"
PASS=0
FAIL=0

for i in $(seq 1 $NUM_PIS); do
    PI_IP="${BASE_IP}.1$(printf '%02d' $i)"
    PI_NAME="pi-$(printf '%02d' $i)"
    STATUS=""

    # Ping check
    if ping -c1 -W2 "$PI_IP" > /dev/null 2>&1; then
        STATUS="${GREEN}✅ PING${NC}"
    else
        STATUS="${RED}❌ PING${NC}"
        echo -e "  $PI_NAME ($PI_IP): $STATUS"
        FAIL=$((FAIL + 1))
        continue
    fi

    # SSH check
    if nc -z -w2 "$PI_IP" 22 > /dev/null 2>&1; then
        STATUS="$STATUS  ${GREEN}✅ SSH${NC}"
    else
        STATUS="$STATUS  ${RED}❌ SSH${NC}"
    fi

    # shellinabox check
    if nc -z -w2 "$PI_IP" 4200 > /dev/null 2>&1; then
        STATUS="$STATUS  ${GREEN}✅ SIAB${NC}"
    else
        STATUS="$STATUS  ${YELLOW}⚠️ SIAB${NC}"
    fi

    echo -e "  $PI_NAME ($PI_IP): $STATUS"
    PASS=$((PASS + 1))
done

echo ""
echo "========================================="
echo -e "Results: ${GREEN}${PASS} reachable${NC}, ${RED}${FAIL} unreachable${NC} out of ${NUM_PIS}"
echo "========================================="

if [ $FAIL -gt 0 ]; then
    echo ""
    echo "Troubleshooting unreachable Pis:"
    echo "  1. Check power — is the LED on?"
    echo "  2. Check WiFi — is the SSID/password correct in the Pi config?"
    echo "  3. Check IP — verify static IP in /etc/dhcpcd.conf"
    echo "  4. Try power-cycling the Pi (unplug, wait 5s, replug)"
fi
