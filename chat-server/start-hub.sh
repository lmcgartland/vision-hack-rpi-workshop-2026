#!/bin/bash
# ============================================
# Start the Hub Server (run on instructor machine)
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Try to use venv if it exists (on a Pi), otherwise use system python
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo ""
echo "========================================="
echo "🌐 Starting Chat Hub Server"
echo "========================================="
echo ""
echo "Dashboard:  http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost'):5000"
echo ""
echo "Students' Pis will auto-register when they start their servers."
echo "To stop the hub, press Ctrl+C"
echo "========================================="
echo ""

python3 hub.py
