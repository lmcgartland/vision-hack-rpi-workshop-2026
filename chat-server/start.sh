#!/bin/bash
cd /home/pi/chat-server
source venv/bin/activate
echo ""
echo "========================================="
echo "🚀 Starting your chat server..."
echo "========================================="
echo ""
echo "Once it's running, open this on your phone:"
echo ""
echo "   http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "To stop the server, press Ctrl+C"
echo "========================================="
echo ""
python3 app.py
