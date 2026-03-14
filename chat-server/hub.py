from flask import Flask, request, jsonify, render_template_string
import requests as http_client
import threading
import time

app = Flask(__name__)
servers = {}      # {"CoolPi": "http://192.168.8.101:5000", ...}
all_messages = []

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Chat Hub Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace;
            background: #0c0c1d;
            color: #fff;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }
        h1 { color: #a78bfa; margin-bottom: 4px; }
        .subtitle { color: rgba(255,255,255,0.4); margin-bottom: 24px; font-size: 14px; }
        .stats {
            display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap;
        }
        .stat {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 14px 18px;
            flex: 1; min-width: 120px;
        }
        .stat .num { font-size: 28px; font-weight: bold; color: #22d3ee; }
        .stat .label { font-size: 12px; color: rgba(255,255,255,0.4); margin-top: 2px; }
        h2 { color: #a78bfa; font-size: 16px; margin-bottom: 12px; }
        .server-list { margin-bottom: 24px; }
        .server {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 10px 14px;
            margin-bottom: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .server .name { color: #22d3ee; font-weight: bold; }
        .server .url { color: rgba(255,255,255,0.3); font-size: 12px; }
        .server .status { color: #4ade80; font-size: 12px; }
        .messages-feed {
            max-height: 400px;
            overflow-y: auto;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 12px;
        }
        .msg {
            padding: 8px 10px;
            margin-bottom: 4px;
            background: rgba(255,255,255,0.03);
            border-radius: 6px;
            font-size: 13px;
        }
        .msg .user { color: #22d3ee; font-weight: bold; }
        .msg .srv { color: rgba(255,255,255,0.3); font-size: 11px; }
        .msg .text { color: rgba(255,255,255,0.7); margin-top: 2px; }
        .empty { color: rgba(255,255,255,0.2); text-align: center; padding: 40px; }
    </style>
</head>
<body>
    <h1>🌐 Chat Hub Dashboard</h1>
    <p class="subtitle">Instructor view — auto-refreshes every 3 seconds</p>

    <div class="stats">
        <div class="stat">
            <div class="num" id="server-count">0</div>
            <div class="label">Servers Connected</div>
        </div>
        <div class="stat">
            <div class="num" id="msg-count">0</div>
            <div class="label">Total Messages</div>
        </div>
    </div>

    <h2>📡 Connected Servers</h2>
    <div class="server-list" id="server-list">
        <div class="empty">No servers registered yet</div>
    </div>

    <h2>💬 Message Feed</h2>
    <div class="messages-feed" id="messages">
        <div class="empty">No messages yet</div>
    </div>

    <script>
        function refresh() {
            fetch('/api/dashboard')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('server-count').textContent = data.server_count;
                    document.getElementById('msg-count').textContent = data.message_count;

                    let sl = document.getElementById('server-list');
                    if (data.servers.length === 0) {
                        sl.innerHTML = '<div class="empty">No servers registered yet</div>';
                    } else {
                        sl.innerHTML = data.servers.map(s =>
                            '<div class="server">' +
                                '<div><span class="name">' + s.name + '</span></div>' +
                                '<div><span class="url">' + s.url + '</span></div>' +
                                '<div><span class="status">● online</span></div>' +
                            '</div>'
                        ).join('');
                    }

                    let ml = document.getElementById('messages');
                    if (data.recent_messages.length === 0) {
                        ml.innerHTML = '<div class="empty">No messages yet</div>';
                    } else {
                        ml.innerHTML = data.recent_messages.map(m =>
                            '<div class="msg">' +
                                '<span class="user">' + m.user + '</span> ' +
                                '<span class="srv">@' + m.server + '</span>' +
                                '<div class="text">' + m.text + '</div>' +
                            '</div>'
                        ).join('');
                        ml.scrollTop = ml.scrollHeight;
                    }
                });
        }
        setInterval(refresh, 3000);
        refresh();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    """Dashboard showing connected servers and message feed"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/dashboard')
def dashboard():
    """JSON data for the dashboard"""
    server_list = [{'name': n, 'url': u} for n, u in servers.items()]
    recent = all_messages[-50:] if len(all_messages) > 50 else all_messages
    return jsonify({
        'server_count': len(servers),
        'message_count': len(all_messages),
        'servers': server_list,
        'recent_messages': recent,
    })

@app.route('/register', methods=['POST'])
def register():
    """A Pi chat server registers itself with the hub"""
    data = request.json
    name = data.get('name', 'Unknown')
    url = data.get('url', '')
    servers[name] = url
    print(f"📡 Registered: {name} at {url}  ({len(servers)} servers total)")
    return jsonify({'status': 'ok', 'servers': list(servers.keys())})

@app.route('/relay', methods=['POST'])
def relay():
    """Receive a message from one Pi and forward it to all others"""
    msg = request.json
    all_messages.append(msg)
    sender = msg.get('server', '')
    forwarded = 0
    for name, url in servers.items():
        if name != sender:
            threading.Thread(target=forward, args=(name, url, msg), daemon=True).start()
            forwarded += 1
    print(f"💬 [{sender}] {msg.get('user','?')}: {msg.get('text','')[:50]}  → relayed to {forwarded} servers")
    return jsonify({'status': 'relayed', 'to': forwarded})

@app.route('/servers')
def list_servers():
    """List all registered servers"""
    return jsonify({'servers': servers, 'count': len(servers)})

@app.route('/health')
def health():
    """Quick health check endpoint"""
    return jsonify({'status': 'ok', 'servers': len(servers), 'messages': len(all_messages)})

def forward(name, url, msg):
    """Forward a message to a single Pi server"""
    try:
        http_client.post(f"{url}/incoming", json=msg, timeout=3)
    except Exception as e:
        print(f"⚠️  Failed to reach {name} at {url}: {e}")

if __name__ == '__main__':
    print("=" * 50)
    print("🌐 Chat Hub Server starting!")
    print("=" * 50)
    print(f"Dashboard: http://0.0.0.0:5000")
    print(f"Waiting for Pi servers to register...")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000)
