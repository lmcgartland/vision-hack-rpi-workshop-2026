from flask import Flask, request, jsonify, render_template
import requests as http_client
import time, threading, socket

app = Flask(__name__)

# ╔══════════════════════════════════════╗
# ║   🎨 CUSTOMIZE THESE!               ║
# ║   Change MY_NAME to your name!      ║
# ╚══════════════════════════════════════╝
MY_NAME = "CHANGE-ME"                         # TODO: Pick a cool server name!
HUB_URL = "http://192.168.8.100:5000"         # Hub address (don't change)

messages = []  # Every chat message lives here

@app.route('/')
def home():
    """When someone opens your server in a browser, show the chat page"""
    return render_template('chat.html', server_name=MY_NAME)

@app.route('/api/messages')
def get_messages():
    """The browser asks: 'Any new messages?' — this answers."""
    after = int(request.args.get('after', 0))
    return jsonify(messages[after:])

@app.route('/api/send', methods=['POST'])
def send_message():
    """The browser says: 'Here's a new message' — we save it and tell the hub."""
    data = request.json
    msg = {'user': data.get('user', 'Anonymous'), 'text': data.get('text', ''),
           'server': MY_NAME, 'time': time.time()}
    messages.append(msg)
    try:
        http_client.post(f"{HUB_URL}/relay", json=msg, timeout=2)
    except Exception:
        pass  # Hub down? Local chat still works!
    return jsonify({'status': 'ok'})

@app.route('/incoming', methods=['POST'])
def receive_from_hub():
    """The hub forwards messages from OTHER servers to us."""
    msg = request.json
    messages.append(msg)
    return jsonify({'status': 'ok'})

# --- Auto-register with the hub when we start ---
def register():
    my_ip = socket.gethostbyname(socket.gethostname())
    try:
        http_client.post(f"{HUB_URL}/register",
            json={'name': MY_NAME, 'url': f"http://{my_ip}:5000"}, timeout=3)
        print(f"✅ Registered with hub as {MY_NAME}")
    except Exception:
        print("⚠️  Hub not available — local-only mode")

threading.Timer(2, register).start()

if __name__ == '__main__':
    print(f"🚀 {MY_NAME}'s chat server starting!")
    app.run(host='0.0.0.0', port=5000, debug=True)
