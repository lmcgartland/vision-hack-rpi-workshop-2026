# 🍕 Pi Chat Workshop — File Kit

Everything you need to run the 90-minute Raspberry Pi chat server workshop.

## What's in this kit

```
chat-server/
├── app.py              ← Chat server (runs on each student's Pi)
├── hub.py              ← Central relay server (runs on instructor machine)
├── templates/
│   └── chat.html       ← Chat web interface (served to phones)
├── start.sh            ← One-command server launcher for students
├── start-hub.sh        ← Hub launcher for the instructor
├── setup-pi.sh         ← Automated Pi setup script (run once per Pi)
├── preflight.sh        ← Morning-of verification script
├── requirements.txt    ← Python dependencies (flask, requests)
└── README.md           ← This file
```

## Setup timeline

### 1-2 days before: Prepare the Pis

1. Flash each Pi with **Raspberry Pi OS Lite** using Raspberry Pi Imager
   - Pre-configure: WiFi credentials, SSH enabled, username `pi`, password `workshop`

2. Copy this entire `chat-server/` folder to a USB drive

3. For each Pi, boot it up, plug in the USB, and run:
   ```bash
   sudo bash /media/pi/USB_DRIVE/chat-server/setup-pi.sh <PI_NUMBER> <HUB_IP>
   ```
   Example for Pi #3 with hub at 192.168.8.100:
   ```bash
   sudo bash setup-pi.sh 3 192.168.8.100
   ```
   Then reboot: `sudo reboot`

4. This script automatically:
   - Sets the hostname to `pi-03`
   - Configures static IP `192.168.8.103`
   - Creates the Python virtual environment
   - Installs Flask and requests
   - Copies all server files
   - Sets the hub URL in app.py
   - Installs shellinabox (browser-based SSH fallback)
   - Sets the password to `workshop`

5. **Label each Pi** with tape: `Pi-03 | IP: 192.168.8.103`

### Morning of: Pre-flight

1. Set up your travel router (GL.iNet or similar)
   - SSID and password matching what you configured on the Pis
   - DHCP range avoiding 192.168.8.100-192.168.8.110 (those are static)

2. Power on all Pis, wait 90 seconds

3. From your laptop on the workshop WiFi, run:
   ```bash
   bash preflight.sh 10 192.168.8
   ```
   This checks ping, SSH, and shellinabox for all Pis.

4. Start the hub server on your laptop (or a dedicated Pi):
   ```bash
   pip install flask requests   # if not in a venv
   bash start-hub.sh
   ```
   Open `http://YOUR_IP:5000` — you'll see the instructor dashboard.

5. Print cheat sheets (one per seat) with:
   - WiFi name + password
   - Their Pi's IP address
   - SSH command: `ssh pi@192.168.8.10X`
   - Password: `workshop`
   - Chat URL: `http://192.168.8.10X:5000`

## During the workshop

### What students do

```bash
# 1. SSH in from their laptop
ssh pi@192.168.8.103      # (their Pi's IP)
# password: workshop

# 2. Start the server
cd chat-server
bash start.sh

# 3. Open on phone: http://192.168.8.103:5000

# 4. To edit code, open a SECOND terminal and SSH in again
nano app.py               # edit server code
nano templates/chat.html  # edit the chat page
# Ctrl+O, Enter, Ctrl+X to save and exit

# 5. Restart: Ctrl+C in the server terminal, then bash start.sh
```

### What you (instructor) do

- Keep the hub running (you'll see registrations and messages in the terminal)
- Open `http://YOUR_IP:5000` for the dashboard view
- Circulate, help with SSH issues, and use the green/orange sticky system

## Troubleshooting

| Problem | Fix |
|---------|-----|
| SSH times out | Check IP, ping the Pi, verify it's powered on |
| SSH "Connection refused" | `sudo systemctl start ssh` (from shellinabox or another connection) |
| Password invisible when typing | Normal! It's a security feature. Type `workshop` and Enter. |
| "Address already in use" | `sudo fuser -k 5000/tcp` then `bash start.sh` |
| Phone can't load chat | Verify phone is on workshop WiFi; use `http://` not `https://` |
| No cross-server messages | Restart the student's Flask server (re-registers with hub) |
| Hub crashed | Restart hub; have all students restart their Flask servers |
| Can't SSH at all | Use shellinabox: `https://192.168.8.10X:4200` in any browser |

## Network architecture

```
                    ┌─────────────────┐
                    │   HUB SERVER    │
                    │  192.168.8.100  │
                    │    (your PC)    │
                    └──┬───┬───┬───┬─┘
                       │   │   │   │
          ┌────────────┘   │   │   └────────────┐
          │                │   │                │
    ┌─────┴─────┐   ┌─────┴───┴──┐      ┌──────┴────┐
    │  Pi-01    │   │  Pi-02     │ ...  │  Pi-10    │
    │  .101     │   │  .102      │      │  .110     │
    └─────┬─────┘   └─────┬──────┘      └─────┬─────┘
          │               │                    │
        📱             📱                   📱
    (phone)         (phone)              (phone)
```

- Each phone connects to its own Pi via HTTP (client → server)
- Each Pi registers with the hub on startup
- When a message is sent, the Pi forwards it to the hub
- The hub relays it to all other Pis
- Phones poll their Pi every 2 seconds for new messages
