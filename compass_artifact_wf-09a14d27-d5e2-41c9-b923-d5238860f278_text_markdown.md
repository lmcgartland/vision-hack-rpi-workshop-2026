# Build a chat network on Raspberry Pis in 90 minutes

**Ten teens, ten Pis, one instructor, and a star-topology chat network that makes HTTP click.** This workshop gives non-technical teens the "I built something cool" thrill while embedding genuine understanding of client-server architecture. Each teen runs a Flask chat server on their Raspberry Pi, connects from their phone, and all servers sync messages through a central hub — making the invisible web visible and tangible. Below is the complete, battle-tested blueprint.

---

## The core philosophy: visible HTTP, not magic

The single most important design decision in this workshop is **HTTP polling over WebSockets/Socket.IO**. Flask-SocketIO introduces 8–10 package dependencies, documented Raspberry Pi compatibility issues (module import errors, eventlet conflicts, version mismatches between JS client and Python server), and — most critically — it hides the request/response cycle behind an abstraction. HTTP polling with `fetch()` and `setInterval()` means every message exchange is a standard GET or POST request that teens can see in their browser's Network tab. **The 1–2 second polling delay is a feature, not a bug** — it makes the mechanism visible and teachable. Total dependency count: just `flask` and `requests`.

---

## Pre-flight checklist: what the instructor must do before anyone arrives

### 1–2 days before the event

- Flash all Pi SD cards with identical Raspberry Pi OS Lite image (use Raspberry Pi Imager with pre-configured WiFi credentials, SSH enabled, username `pi`, password `workshop`)
- Set unique hostnames: `pi-01` through `pi-10`
- Configure static IPs: `192.168.8.101` through `192.168.8.110` (via `/etc/dhcpcd.conf` or `nmtui`)
- On each Pi, create virtual environment and install dependencies:
  ```bash
  mkdir -p /home/pi/chat-server/templates /home/pi/chat-server/static
  cd /home/pi/chat-server
  python3 -m venv venv
  source venv/bin/activate
  pip install flask requests
  ```
- Copy `app.py`, `templates/chat.html`, and `start.sh` onto each Pi (files detailed below)
- Install `shellinabox` on every Pi as a browser-based SSH fallback: `sudo apt-get install -y shellinabox` (auto-starts on port 4200)
- **Physically label each Pi** with tape or sticker: `Pi-03 | IP: 192.168.8.103 | http://192.168.8.103:5000`
- Set up one dedicated Pi (or the instructor's laptop) to run `hub.py` — the central relay server
- Prepare 10 printed cheat sheets (one per seat) with platform-specific SSH instructions and the per-Pi connection details
- Load PuTTY portable `.exe` onto a USB stick as backup for old Windows machines
- Prepare a slide deck or whiteboard diagrams for the restaurant analogy and star-topology architecture

### Morning of the event (arrive 45–60 minutes early)

**Network setup (do this first — it's the highest-risk item):**

- Deploy your **travel router** (a GL.iNet Beryl AX or similar, ~$60–70). This is non-negotiable. Venue WiFi almost always has AP/client isolation enabled, which blocks device-to-device traffic and will silently break the entire workshop. Your own router creates a private subnet you fully control.
- Configure DHCP reservations for all Pis by MAC address (ensures IPs stay fixed)
- Write on the whiteboard: WiFi SSID, password, and IP assignment table
- Connect your instructor laptop to the workshop WiFi
- Verify internet access through the router (optional but nice for teens to Google things)

**Pi verification (systematic, do not skip):**

- Power on all Pis, wait 90 seconds
- From instructor laptop, batch-ping all Pis:
  ```bash
  for i in $(seq 101 110); do ping -c1 -W1 192.168.8.$i && echo "Pi $i OK" || echo "Pi $i FAILED"; done
  ```
- SSH into at least 3 Pis to verify login works
- On 2 Pis, start Flask: `cd chat-server && source venv/bin/activate && python3 app.py` — then load the page from your phone browser to confirm
- Start the hub server on the designated Pi/laptop
- Verify shellinabox is reachable: open `https://192.168.8.101:4200` in a browser (accept the self-signed cert warning)
- Stop any Flask servers you started (Ctrl+C) — teens will start these themselves

**Room setup:**

- Place one powered Pi at each seat, with its printed cheat sheet
- Place two sticky notes at each seat: one green, one orange
- Set the whiteboard up with: WiFi credentials, IP table, and the restaurant analogy diagram (draw this in advance)

---

## Recommended pre-loaded code structure

Each Pi gets this identical file tree under `/home/pi/chat-server/`:

```
chat-server/
├── app.py                 ← Main server (35 lines — teens edit this)
├── templates/
│   └── chat.html          ← Chat UI (60 lines — teens customize this)
├── start.sh               ← One-command launcher
├── venv/                  ← Pre-created virtual environment
└── requirements.txt       ← flask, requests
```

The hub server (on instructor Pi or laptop) has a separate `hub.py`.

### app.py — the teen's chat server (~35 lines)

```python
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
    msg = {'user': data['user'], 'text': data['text'],
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
```

### templates/chat.html — the chat interface (~60 lines)

```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ server_name }} Chat</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 10px; background: #f5f5f5; }
        h2 { color: #1565c0; }  /* TODO: Change this color! */
        #messages { height: 50vh; overflow-y: scroll; border: 2px solid #333;
                    padding: 10px; margin: 10px 0; border-radius: 8px; background: white; }
        .msg { margin: 5px 0; padding: 8px; background: #e3f2fd; border-radius: 5px; }
        .msg .user { font-weight: bold; color: #1565c0; }
        .msg .server { font-size: 0.8em; color: #999; }
        input[type=text] { font-size: 16px; padding: 8px; width: 65%; border-radius: 5px; border: 1px solid #ccc; }
        button { font-size: 16px; padding: 8px 16px; background: #1565c0; color: white;
                 border: none; border-radius: 5px; cursor: pointer; }
    </style>
</head>
<body>
    <h2>💬 {{ server_name }} Chat</h2>
    <input type="text" id="username" placeholder="Your name">
    <div id="messages"></div>
    <input type="text" id="msgInput" placeholder="Type a message..."
           onkeypress="if(event.key==='Enter')sendMsg()">
    <button onclick="sendMsg()">Send</button>

    <script>
        let seen = 0;

        // Ask the server for new messages every 2 seconds
        setInterval(fetchMessages, 2000);

        function fetchMessages() {
            fetch('/api/messages?after=' + seen)
                .then(r => r.json())
                .then(msgs => {
                    msgs.forEach(m => {
                        let div = document.createElement('div');
                        div.className = 'msg';
                        div.innerHTML = '<span class="user">' + m.user + '</span> ' +
                                       '<span class="server">@' + m.server + '</span>: ' + m.text;
                        document.getElementById('messages').appendChild(div);
                    });
                    seen += msgs.length;
                    let box = document.getElementById('messages');
                    box.scrollTop = box.scrollHeight;
                });
        }

        function sendMsg() {
            let user = document.getElementById('username').value || 'Anonymous';
            let text = document.getElementById('msgInput').value;
            if (!text) return;
            fetch('/api/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user: user, text: text})
            });
            document.getElementById('msgInput').value = '';
        }

        fetchMessages();  // Load any existing messages on page load
    </script>
</body>
</html>
```

### hub.py — the central relay (~35 lines, runs on instructor's machine)

```python
from flask import Flask, request, jsonify
import requests as http_client
import threading

app = Flask(__name__)
servers = {}      # {"CoolPi": "http://192.168.8.101:5000", ...}
all_messages = []

@app.route('/')
def home():
    return jsonify({'hub': 'Chat Hub', 'servers': list(servers.keys()),
                    'messages': len(all_messages)})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    servers[data['name']] = data['url']
    print(f"📡 Registered: {data['name']} at {data['url']}")
    return jsonify({'status': 'ok', 'servers': list(servers.keys())})

@app.route('/relay', methods=['POST'])
def relay():
    msg = request.json
    all_messages.append(msg)
    sender = msg.get('server', '')
    for name, url in servers.items():
        if name != sender:
            threading.Thread(target=forward, args=(url, msg)).start()
    return jsonify({'status': 'relayed', 'to': len(servers) - 1})

def forward(url, msg):
    try:
        http_client.post(f"{url}/incoming", json=msg, timeout=3)
    except Exception as e:
        print(f"⚠️  Failed to reach {url}: {e}")

if __name__ == '__main__':
    print("🌐 Chat Hub Server running!")
    app.run(host='0.0.0.0', port=5000)
```

### start.sh — one-command launcher

```bash
#!/bin/bash
cd /home/pi/chat-server
source venv/bin/activate
echo "🚀 Starting your chat server..."
python3 app.py
```

---

## Minute-by-minute workshop plan

### Phase 0 — Arrival and settle (minutes 0–5)

**What to say:** "Welcome! Find a seat — there's a Raspberry Pi and a cheat sheet waiting for you. Grab the two sticky notes. Green means 'I'm good.' Orange means 'I need help.' We'll use these all session. Connect your laptop to the WiFi on the board."

**What teens do:** Sit down, connect laptops to workshop WiFi.

**Instructor does:** Circulate, help WiFi connections, verify the hub server is running.

**Checkpoint:** "Hold up your green sticky when you're on the WiFi." Scan the room — every seat should show green within 2 minutes. If anyone shows orange, troubleshoot immediately (wrong password is the usual culprit).

---

### Phase 1 — The restaurant that explains the internet (minutes 5–15)

**What to say (the restaurant analogy — this is the conceptual anchor for the whole workshop):**

"Raise your hand if you've ordered food at a restaurant. Great. Here's the thing — you just described how the entire internet works. Let me show you.

You sit down at a table. You're the **client** — a phone, a laptop, a browser. You want something. You look at the **menu** — that's like a list of URLs or web addresses, things you can ask for. You tell the **waiter** what you want — that's your **HTTP request**. The waiter walks to the **kitchen** — that's the **server**, the computer that has what you need. The kitchen prepares your order and the waiter brings it back — that's the **HTTP response**.

Now here's the key: you can't walk into the kitchen yourself. You have to ask through the waiter. Every single time you load Instagram, watch YouTube, or send a Snap, your phone is sitting at a table, sending a request to a kitchen somewhere, and getting a response back. Thousands of times a day.

Today? **You're going to build the kitchen.** Each of you will run a real web server on that Raspberry Pi in front of you. Your phone will be the customer. And by the end, all your kitchens will be connected together into a chat network."

**Draw on the whiteboard while speaking:**

```
📱 Phone (Client)  ──request──▶  🍳 Pi (Server)
                   ◀──response──
```

Then extend it to the star topology:

```
         📱──[Pi-Alice]──┐
                          │
         📱──[Pi-Bob]────[HUB]
                          │
         📱──[Pi-Charlie]─┘
```

**Map HTTP status codes to restaurant situations** (this always gets laughs):
- **200 OK** — "Here's your food!"
- **404 Not Found** — "We don't serve that here."
- **500 Internal Server Error** — "The kitchen is on fire."
- **403 Forbidden** — "VIP area only."

**Checkpoint:** "Quick check — in our restaurant analogy, what is the server? What is the client?" Get 2–3 verbal answers. Don't proceed until this is solid.

---

### Phase 2 — SSH: your tunnel into the Pi (minutes 15–25)

**What to say:** "That Raspberry Pi in front of you is a real Linux computer — it's just running without a screen. To talk to it, we use something called SSH — Secure Shell. Think of it as a phone call to your Pi. You type commands on your laptop, and the Pi executes them."

**What teens do (guided, step-by-step with instructor projecting their screen):**

1. Open a terminal:
   - **Windows:** Open PowerShell (search "PowerShell" in Start menu)
   - **Mac:** Open Terminal (Cmd+Space, type "Terminal")
   - **Chromebook:** Open the Secure Shell extension or Linux terminal
2. Type the SSH command (displayed on cheat sheet and whiteboard):
   ```
   ssh pi@192.168.8.10X
   ```
   (where X is their Pi number from the label)
3. **Pre-brief two gotchas before they hit them:**
   - "It will ask 'Are you sure you want to continue connecting?' Type the full word **yes** and press Enter. This is normal."
   - "When you type the password, **nothing will appear on screen** — no dots, no stars, nothing. This is a security feature. Type **workshop** carefully and press Enter."

**Contingency — SSH fails for someone:**
- If "Connection timed out": verify they typed the right IP, check Pi is powered, ping from instructor laptop
- If "Connection refused": SSH service down — instructor SSHes in from their own machine and runs `sudo systemctl start ssh`, or have teen use `https://192.168.8.10X:4200` (shellinabox) in their browser instead
- If student has no SSH client (old Windows): hand them the USB stick with PuTTY, or pivot to shellinabox in browser
- If more than 3 students are stuck: **immediately pivot everyone to shellinabox browser access** — don't burn time debugging individual SSH clients

**Checkpoint (critical):** "When you see `pi@pi-XX:~ $` on your screen, hold up your green sticky." **Do not proceed until every student shows green or has been paired with a neighbor.** This is the highest-risk chokepoint. Budget the full 10 minutes. If it's going well and finishes early, great — you've banked buffer time.

**Quick orientation commands (1 minute):** Have everyone type:
```bash
hostname        # Shows their Pi's name
hostname -I     # Shows their Pi's IP address
ls              # Lists files — they'll see chat-server/
```

---

### Phase 3 — Launch your server and see magic (minutes 25–40)

This is the "magic moment" — the payoff that hooks engagement for the rest of the workshop. The entire design prioritizes getting teens to **a working chat page on their phone within 5 minutes of SSHing in**.

**What to say:** "You're inside your Pi now. Let's fire up your chat server. Type exactly what I type."

**Step 1 — Start the server (minutes 25–28):**

Instructor types live on the projected screen, teens follow:
```bash
cd chat-server
bash start.sh
```

They should see:
```
🚀 CHANGE-ME's chat server starting!
 * Running on http://0.0.0.0:5000
```

**What to say:** "See that? Your Raspberry Pi is now a web server. It's running right now, listening for requests — just like a restaurant kitchen waiting for orders. The address `0.0.0.0` means 'accept orders from anyone on this network.' Port `5000` is like the table number."

**Checkpoint:** "If you see 'Running on' in your terminal, green sticky up." Handle orange stickies. Most common issue: `Address already in use` — have teen type `sudo fuser -k 5000/tcp` then re-run `bash start.sh`.

**Step 2 — Connect from your phone (minutes 28–33):**

**What to say:** "Now pull out your phone. Make sure it's on the workshop WiFi. Open your browser — Chrome, Safari, whatever — and type in: `http://` then your Pi's IP, colon, `5000`. It's on your cheat sheet and your Pi's label."

Example: `http://192.168.8.103:5000`

**The magic moment:** A chat interface loads. On their phone. Served from their Pi. Their eyes go wide.

**What to say:** "That web page you're looking at? It's not on the internet. It's not on any cloud. It is coming directly from that tiny computer in front of you, across the WiFi, to your phone. **You are running a web server.** Type a message and hit Send."

Let them send a few messages to themselves. Give them 60 seconds to play.

**Checkpoint:** "If you can see the chat page on your phone and send a message, green sticky up!" This should produce near-universal green. If someone's phone can't connect: verify they're on workshop WiFi, verify they typed `http://` not `https://`, try a different browser.

**Step 3 — Cross-server chat revelation (minutes 33–40):**

**What to say:** "Right now, each of you can only see messages on your own server. But look at the whiteboard — see the hub in the middle? I started a hub server before you arrived. Your servers are already registered with it. When you send a message, your Pi forwards it to the hub, and the hub sends it to everyone else's Pi. Let's test it."

Ask one teen to send a message. Wait 2–3 seconds (the polling delay — use this pedagogically). Ask another teen: "Did you see it?" The room should react.

**What to say:** "That 2-second delay you noticed? That's not a bug. Your phone is literally asking your Pi every 2 seconds: 'Got any new messages?' That's called **polling**. It's the same thing your email app does. Every few seconds, it checks: anything new? Let me show you."

**Live demo — open browser DevTools** (on the projected screen): Open the chat page on the instructor's laptop browser, press F12, go to the Network tab. Let students see the `/api/messages` requests repeating every 2 seconds.

**What to say:** "See those requests? Every one is like a customer asking the waiter, 'Any food ready yet?' And the server responds either with new messages or an empty plate. This is the actual HTTP protocol happening in real time."

**Checkpoint:** "Can everyone see messages from OTHER people's servers on their phone? Green sticky if yes." Troubleshoot any orange stickies — most likely cause is the hub server not running or a Pi didn't register (have them restart their Flask server).

---

### Phase 4 — Make it yours (minutes 40–60)

This phase flips from guided to exploratory. It's where the pair programming strategy pays off — **pair teens who are confident with those who are struggling** for mutual benefit.

**What to say:** "Your server works. Now let's make it yours. To edit the code, you'll need a second SSH connection. Open a new terminal window and SSH in again with the same command. Keep the first window running — that's your server."

**Critical instruction:** "To stop your server, press Ctrl+C in the first terminal. After editing, start it again with `bash start.sh`. Stop, edit, restart."

**Teach nano basics (2 minutes):**
```bash
nano app.py          # Opens the file editor
# Arrow keys to move, type to edit
# Ctrl+O then Enter to save
# Ctrl+X to exit
```

### Modification levels (printed on cheat sheet)

**Level 1 — Personalize (everyone does this, 5 minutes):**
- Open `app.py`, change `MY_NAME = "CHANGE-ME"` to their name or something fun
- Restart server, refresh phone — see their name in the chat header
- Open `templates/chat.html`, find `color: #1565c0` and change it to any hex color (write a few color options on the whiteboard: `#e91e63` pink, `#4caf50` green, `#ff9800` orange, `#9c27b0` purple)
- Restart, refresh — see their custom color

**Checkpoint:** "Green sticky when your server shows YOUR name and YOUR color."

**Level 2 — Modify behavior (optional, 8–10 minutes):**
- Change the polling interval: in `chat.html`, find `setInterval(fetchMessages, 2000)` and change `2000` to `500`. Restart. "What changed? Why?" (Messages appear faster. Discuss: more requests = more load on server, but more responsive.)
- Add emoji prefix: in `app.py`, in the `send_message` function, add a line before `messages.append(msg)`:
  ```python
  msg['text'] = '🔥 ' + msg['text']
  ```
  Now every message from their server gets a fire emoji.
- **Teach cause-and-effect:** "Change one thing. Predict what will happen. Then test."

**Level 3 — Add a feature (for fast finishers, 10 minutes):**
- Add a `/api/status` endpoint that returns JSON:
  ```python
  @app.route('/api/status')
  def status():
      return jsonify({'server': MY_NAME, 'messages': len(messages), 'uptime': 'running!'})
  ```
  Then visit `http://192.168.8.10X:5000/api/status` in a browser — see raw JSON. "This is what APIs look like. Every app you use calls APIs just like this."
- Change the chat HTML to show timestamps or user colors

**Instructor during this phase:** Circulate continuously. Spend no more than 2 minutes with any one student. If someone is deeply stuck, pair them with a neighbor. If someone is racing ahead, give them Level 3 challenges. Use orange/green stickies to triage.

---

### Phase 5 — Concept consolidation (minutes 60–70)

Bring attention back to the group. This phase locks in understanding.

**What to say:** "Let's zoom out. You've been running web servers for 30 minutes. Let me show you what was actually happening."

**Whiteboard walkthrough — trace a message's full journey:**

1. You type "hello" on your phone and tap Send
2. Your phone (client) sends an HTTP **POST request** to `http://192.168.8.103:5000/api/send` with JSON data `{"user": "Alex", "text": "hello"}`
3. Your Pi (server) receives the request, saves the message to its list, and forwards it to the Hub
4. The Hub receives it and sends HTTP POST requests to every other Pi
5. Each other Pi saves the message to its list
6. Every 2 seconds, each phone sends an HTTP **GET request** to `/api/messages?after=X`
7. The Pi responds with any new messages as JSON
8. The phone's JavaScript renders them on screen

**Draw this on the whiteboard as a numbered sequence diagram.** This is the moment where the code they modified snaps into conceptual clarity.

**Interactive check:** Point to a step in the diagram. "What HTTP method is this? GET or POST?" Do 3–4 of these rapid-fire. "What would happen if the hub crashed?" (Answer: local chat still works, but cross-server messages stop. Because the code has `try/except` around the hub call.) "What would happen if you changed the polling from 2 seconds to 60 seconds?" (Answer: messages would take up to a minute to appear.)

**What to say:** "Every website you use works exactly like this. When you scroll Instagram, your phone is making GET requests. When you post a photo, that's a POST request. You just built a simplified version of the exact same thing."

---

### Phase 6 — Freeplay and show-and-tell (minutes 70–85)

**What to say:** "You've got 15 minutes. Make your server the coolest one in the room. Change colors, add features, break things and fix them. At minute 85, we're going to do a quick show-and-tell."

**Instructor does:** Circulate. Help. Let teens explore. This is where engagement peaks for curious students. Suggest challenges:
- "Can you make your chat page have a dark mode?"
- "Can you add a welcome message that appears when someone first loads your chat?"
- "Can you figure out how to add a `/about` page?"

**Show-and-tell (minutes 82–85):** Quick round — each teen holds up their phone and says one thing they changed or learned in one sentence. Keep it to **30 seconds per teen maximum**. Celebrate everything. "Your server has a custom theme? Awesome. You figured out how to add an emoji to every message? That's actual server-side logic."

---

### Phase 7 — Wrap-up and takeaways (minutes 85–90)

**What to say:** "Let's recap what you actually did today — not what you think you did, what you actually did."

Write on the whiteboard as you say each:
- "You **SSHed into a remote Linux server** — that's how real engineers manage servers in data centers"
- "You **ran a web server** that handled real HTTP requests"
- "You **read and modified Python code** running in production"
- "You **debugged a distributed system** — multiple servers talking through a hub"
- "You **built a networked application** from actual client-server architecture"

**What to say:** "The gap between what you did today and what runs Instagram or Discord is scale, not concept. They have millions of servers instead of ten. They use databases instead of a Python list. But the request-response cycle, the client-server model, the APIs — identical."

**Close:** "The code is on your Pi. If you want to keep playing with it at home, a Raspberry Pi costs about $35. Everything you need to learn more is free online. Thank you for building with me today."

---

## Contingency playbook: when things break

| Failure | Symptom | 30-second fix |
|---------|---------|---------------|
| Student can't connect to WiFi | No network on laptop | Verify SSID/password; try forgetting and reconnecting; check router is on |
| SSH times out | `Connection timed out` | Verify IP (check label), ping Pi from instructor laptop, power-cycle Pi if no response |
| SSH "Connection refused" | Port 22 not listening | Instructor connects via shellinabox or direct and runs `sudo systemctl start ssh` |
| SSH password invisible | "I'm typing but nothing shows" | Reassure: this is by design. Type `workshop` carefully, press Enter |
| Host key warning | Scary `@@@@ WARNING @@@@` | Run `ssh-keygen -R <IP>` on the student's laptop, then reconnect |
| No SSH client on laptop | `ssh: command not found` | Give PuTTY from USB, or use `https://192.168.8.10X:4200` in browser |
| Flask "Address already in use" | `OSError: [Errno 98]` | `sudo fuser -k 5000/tcp` then re-run `bash start.sh` |
| Phone can't load chat page | Browser says "can't connect" | Verify phone is on workshop WiFi; use `http://` not `https://`; try IP in another browser |
| Cross-server messages not appearing | Local chat works, hub relay doesn't | Restart teen's Flask server (re-registers with hub); verify hub is running |
| Pi unresponsive | Ping fails, SSH hangs | Power-cycle: unplug and replug USB power, wait 60 seconds |
| Hub server crashes | No cross-server messages for anyone | Instructor restarts hub; all teens restart their Flask servers to re-register |
| **More than 3 students stuck at once** | Multiple orange stickies | **Stop and regroup.** Project your screen, walk through the step together. Do not try to fix individually. |

### The nuclear option

If venue networking is completely broken (travel router fails, no device-to-device traffic possible): pair students 2-per-Pi using shellinabox from any device, reduce to 5 working stations. The workshop still works — just with pairs instead of individuals. The star topology still functions with 5 servers instead of 10.

---

## Key teaching techniques deployed throughout

**The sticky note system** (from The Carpentries): Green = "I'm good," orange = "I need help." Teens keep the relevant color displayed on their laptop lid. The instructor can scan the room in 2 seconds and triage. This is the single most important classroom management tool for a solo instructor.

**Pair programming as force multiplier**: When a student is stuck for more than 2 minutes, pair them with a neighbor. The confident student reinforces their knowledge by teaching; the stuck student gets peer help without waiting for the instructor.

**Written cheat sheets as "second instructor"**: Every step is on paper at their seat. When the instructor is helping someone else, other students can self-serve from the cheat sheet. This is non-negotiable for solo instruction.

**Predict-then-observe**: Before running modified code, ask "What do you think will happen?" The moment of surprise when the prediction is wrong (or right) creates stronger memory encoding than passive observation.

**Time-buffer rule**: Every task estimate is doubled. If you think a step takes 5 minutes, allocate 10. The schedule above has **15 minutes of built-in buffer** (the freeplay phase can expand or contract). If SSH setup goes fast, freeplay gets longer. If SSH setup is painful, freeplay shrinks — but the core learning remains intact.

**The "works immediately" principle**: Teens never write code from scratch. They run working code first, experience the magic, then modify. This eliminates the frustrating "cold start" where nothing works for 20 minutes. Research from Hack Club and maker education consistently shows this approach produces both higher engagement and better conceptual retention than blank-slate coding.

---

## Summary timing at a glance

| Phase | Minutes | Mode | Core outcome |
|-------|---------|------|-------------|
| 0. Settle + WiFi | 0–5 | Setup | Everyone connected |
| 1. Restaurant analogy | 5–15 | Lecture + Q&A | Client-server concept anchored |
| 2. SSH into Pis | 15–25 | Guided hands-on | Everyone has a terminal on their Pi |
| 3. Launch + magic moment | 25–40 | Guided hands-on | Chat server running, phone connected, cross-server messages flowing |
| 4. Make it yours | 40–60 | Self-directed | Code modified, ownership felt |
| 5. Concept consolidation | 60–70 | Interactive lecture | Full request lifecycle understood |
| 6. Freeplay + show-and-tell | 70–85 | Self-directed + social | Creative expression, peer sharing |
| 7. Wrap-up | 85–90 | Closing | Accomplishment framed, next steps given |

The workshop alternates between **never more than 10 minutes of lecture** and **hands-on doing**, consistent with research showing teen attention drops sharply after 10–15 minutes of passive listening. The conceptual explanation comes in two waves — once as a preview (Phase 1, before they have context) and once as a consolidation (Phase 5, after they have experience). This dual-pass approach means teens hear the same concepts twice: once abstract, once grounded in their own experience. The second pass is where real understanding forms.