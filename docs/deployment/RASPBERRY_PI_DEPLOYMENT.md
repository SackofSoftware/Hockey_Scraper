# Raspberry Pi Deployment Guide
## Hockey Stats API Server - Production Setup

---

## 🎯 **Architecture Overview**

```
┌─────────────┐         Git Push         ┌─────────────────┐
│   Your PC   │ ──────────────────────> │  Raspberry Pi   │
│ Development │                          │  Server Hub     │
└─────────────┘                          └─────────────────┘
                                                  │
                                                  ├─ Auto-sync (cron)
                                                  ├─ SQLite database
                                                  ├─ FastAPI server
                                                  └─ Nginx reverse proxy

Access from anywhere:
http://your-pi.local:8000/api/v1/...
```

---

## 📦 **Part 1: PC Setup (Development)**

### **1.1 Initialize Git Repository**

```bash
cd "/path/to/Hockey_Scraper"

# Initialize git
git init

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/

# Databases
*.db
*.db-journal

# Logs
*.log
logs/
reports/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Output files
output/
data/raw/
*.json.backup

# Secrets
.env
config.local.json
EOF

# Add all code files
git add *.py *.md requirements.txt
git commit -m "Initial commit - Hockey Stats API System"
```

### **1.2 Create Deployment Package**

```bash
# Create deployment script
cat > deploy.sh << 'EOF'
#!/bin/bash
# Deploy to Raspberry Pi

PI_HOST="pi@raspberrypi.local"  # Change to your Pi hostname/IP
PI_DIR="/home/pi/hockey-stats"

echo "🚀 Deploying to Raspberry Pi..."

# Sync code (excluding databases and logs)
rsync -avz --exclude '*.db' --exclude '*.log' --exclude 'data/' \
    ./ ${PI_HOST}:${PI_DIR}/

echo "✅ Code synced to Pi"
echo "🔄 Restarting services on Pi..."

# SSH and restart services
ssh ${PI_HOST} << 'ENDSSH'
cd /home/pi/hockey-stats
sudo systemctl restart hockey-stats-api
sudo systemctl restart hockey-stats-sync
echo "✅ Services restarted"
ENDSSH

echo "🎉 Deployment complete!"
EOF

chmod +x deploy.sh
```

---

## 🥧 **Part 2: Raspberry Pi Setup**

### **2.1 Initial Pi Configuration**

SSH into your Pi:

```bash
ssh pi@raspberrypi.local
```

Update system:

```bash
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv nginx git sqlite3

# Install Python 3.10+ (if not available)
python3 --version  # Check version
```

### **2.2 Create Project Directory**

```bash
# Create directory structure
mkdir -p /home/pi/hockey-stats
cd /home/pi/hockey-stats

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Create data directories
mkdir -p data/databases
mkdir -p logs
mkdir -p backups
```

### **2.3 Clone/Pull Code from PC**

Option A - Direct rsync from PC (run on PC):
```bash
./deploy.sh
```

Option B - Git repository (if using GitHub):
```bash
cd /home/pi/hockey-stats
git clone https://github.com/yourusername/hockey-stats.git .
```

### **2.4 Install Dependencies**

```bash
cd /home/pi/hockey-stats
source venv/bin/activate

# Install Python packages
pip3 install -r requirements.txt

# Verify installation
python3 -c "import fastapi, uvicorn, requests; print('✅ All dependencies installed')"
```

---

## ⚙️ **Part 3: Auto-Sync Service**

### **3.1 Create Sync Script**

```bash
cat > /home/pi/hockey-stats/auto_sync.py << 'EOF'
#!/usr/bin/env python3
"""
Automatic incremental sync for hockey stats
Runs hourly via systemd timer
"""

import sys
import sqlite3
import requests
from datetime import datetime
from pathlib import Path

SEASON_ID = "10776"
DB_PATH = "/home/pi/hockey-stats/data/databases/hockey_stats_10776.db"
LOG_PATH = "/home/pi/hockey-stats/logs/auto_sync.log"

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_PATH, "a") as f:
        f.write(log_msg + "\n")

def get_cached_game_ids():
    """Get all game IDs already in database"""
    if not Path(DB_PATH).exists():
        return set()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT game_id FROM games")
    game_ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return game_ids

def get_current_schedule():
    """Fetch current schedule from API"""
    url = f"https://gamesheetstats.com/api/useSchedule/getSeasonSchedule/{SEASON_ID}"
    params = {
        'filter[gametype]': 'overall',
        'filter[limit]': 2000,
        'filter[offset]': 0,
        'filter[timeZoneOffset]': -240
    }

    response = requests.get(url, params=params, timeout=30)
    if response.status_code != 200:
        return []

    schedule_data = response.json()
    game_ids = []

    for key, daily_games in schedule_data.items():
        if isinstance(daily_games, list):
            for day_data in daily_games:
                if isinstance(day_data, dict) and 'games' in day_data:
                    for game in day_data['games']:
                        if game.get('status') == 'final':
                            game_ids.append(game.get('id'))

    return set(game_ids)

def sync_new_games():
    """Sync only new completed games"""
    log("Starting incremental sync...")

    cached = get_cached_game_ids()
    current = get_current_schedule()

    new_games = current - cached

    log(f"Cached games: {len(cached)}")
    log(f"Current completed games: {len(current)}")
    log(f"New games to sync: {len(new_games)}")

    if not new_games:
        log("✅ No updates needed")
        return

    # Import only new games
    log(f"Importing {len(new_games)} new games...")

    # Use existing data_importer with specific game IDs
    import subprocess
    result = subprocess.run([
        '/home/pi/hockey-stats/venv/bin/python3',
        '/home/pi/hockey-stats/incremental_import.py',
        '--season-id', SEASON_ID,
        '--game-ids', ','.join(new_games),
        '--db', DB_PATH
    ], capture_output=True, text=True)

    if result.returncode == 0:
        log(f"✅ Successfully imported {len(new_games)} games")

        # Recalculate stats
        log("Recalculating statistics...")
        result = subprocess.run([
            '/home/pi/hockey-stats/venv/bin/python3',
            '/home/pi/hockey-stats/stats_calculator.py',
            DB_PATH,
            SEASON_ID
        ], capture_output=True, text=True)

        if result.returncode == 0:
            log("✅ Statistics updated")
        else:
            log(f"❌ Stats calculation failed: {result.stderr}")
    else:
        log(f"❌ Import failed: {result.stderr}")

if __name__ == "__main__":
    try:
        sync_new_games()
    except Exception as e:
        log(f"❌ Error: {e}")
        sys.exit(1)
EOF

chmod +x /home/pi/hockey-stats/auto_sync.py
```

### **3.2 Create Systemd Service**

```bash
# Create service file
sudo tee /etc/systemd/system/hockey-stats-sync.service > /dev/null << 'EOF'
[Unit]
Description=Hockey Stats Incremental Sync
After=network.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/hockey-stats
ExecStart=/home/pi/hockey-stats/venv/bin/python3 /home/pi/hockey-stats/auto_sync.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create timer for hourly runs
sudo tee /etc/systemd/system/hockey-stats-sync.timer > /dev/null << 'EOF'
[Unit]
Description=Run Hockey Stats Sync Every Hour

[Timer]
OnCalendar=hourly
OnBootSec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable hockey-stats-sync.timer
sudo systemctl start hockey-stats-sync.timer

# Check timer status
sudo systemctl status hockey-stats-sync.timer
```

---

## 🌐 **Part 4: API Server Service**

### **4.1 Create API Service**

```bash
sudo tee /etc/systemd/system/hockey-stats-api.service > /dev/null << 'EOF'
[Unit]
Description=Hockey Stats FastAPI Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/hockey-stats
ExecStart=/home/pi/hockey-stats/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start API service
sudo systemctl daemon-reload
sudo systemctl enable hockey-stats-api.service
sudo systemctl start hockey-stats-api.service

# Check status
sudo systemctl status hockey-stats-api.service
```

### **4.2 Setup Nginx Reverse Proxy**

```bash
# Create nginx config
sudo tee /etc/nginx/sites-available/hockey-stats > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_set_header Host $host;
    }

    location /redoc {
        proxy_pass http://localhost:8000/redoc;
        proxy_set_header Host $host;
    }

    location / {
        return 301 /docs;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/hockey-stats /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and restart nginx
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔧 **Part 5: Maintenance Scripts**

### **5.1 Daily Backup Script**

```bash
cat > /home/pi/hockey-stats/backup.sh << 'EOF'
#!/bin/bash
# Daily database backup

BACKUP_DIR="/home/pi/hockey-stats/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/home/pi/hockey-stats/data/databases/hockey_stats_10776.db"

# Create backup
sqlite3 $DB_PATH ".backup ${BACKUP_DIR}/hockey_stats_${DATE}.db"

# Keep only last 7 days
find $BACKUP_DIR -name "hockey_stats_*.db" -mtime +7 -delete

echo "[$(date)] Backup created: hockey_stats_${DATE}.db"
EOF

chmod +x /home/pi/hockey-stats/backup.sh

# Add to crontab (run daily at 3 AM)
(crontab -l 2>/dev/null; echo "0 3 * * * /home/pi/hockey-stats/backup.sh >> /home/pi/hockey-stats/logs/backup.log 2>&1") | crontab -
```

### **5.2 Health Check Script**

```bash
cat > /home/pi/hockey-stats/healthcheck.sh << 'EOF'
#!/bin/bash
# Check if API is running

API_URL="http://localhost:8000/health"

if curl -f -s $API_URL > /dev/null; then
    echo "✅ API is healthy"
else
    echo "❌ API is down, restarting..."
    sudo systemctl restart hockey-stats-api
fi
EOF

chmod +x /home/pi/hockey-stats/healthcheck.sh

# Run every 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * /home/pi/hockey-stats/healthcheck.sh >> /home/pi/hockey-stats/logs/health.log 2>&1") | crontab -
```

---

## 📱 **Part 6: Access from Anywhere**

### **6.1 Find Your Pi's IP**

```bash
# On Pi
hostname -I
# Or
ip addr show wlan0 | grep "inet "
```

### **6.2 Access API**

From your PC or phone on same network:

```bash
# Replace with your Pi's IP
http://192.168.1.100/docs              # Swagger UI
http://192.168.1.100/api/v1/seasons/10776
http://192.168.1.100/api/v1/teams/386316/stats
```

### **6.3 Optional: External Access (Port Forwarding)**

On your router:
- Forward port 80 → Pi's IP:80
- Access from anywhere: http://your-public-ip/docs

Or use ngrok for easy tunneling:
```bash
# Install ngrok on Pi
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm.tgz
tar -xvzf ngrok-v3-stable-linux-arm.tgz
sudo mv ngrok /usr/local/bin/

# Start tunnel
ngrok http 80

# Access via: https://random-url.ngrok.io/docs
```

---

## 🚀 **Part 7: Complete Workflow**

### **On PC (Development):**

```bash
# 1. Make changes to code
vim api_server.py

# 2. Test locally
python3 api_server.py

# 3. Commit changes
git add api_server.py
git commit -m "Added new endpoint"

# 4. Deploy to Pi
./deploy.sh
```

### **On Pi (Automatic):**

```bash
# Runs automatically:
✅ Hourly sync (checks for new games)
✅ API server (always running)
✅ Daily backups (3 AM)
✅ Health checks (every 5 min)
```

### **View Logs:**

```bash
# SSH to Pi
ssh pi@raspberrypi.local

# View API logs
sudo journalctl -u hockey-stats-api -f

# View sync logs
sudo journalctl -u hockey-stats-sync -f
tail -f /home/pi/hockey-stats/logs/auto_sync.log

# View all services
sudo systemctl status hockey-stats-*
```

---

## 📊 **Resource Usage (Pi 4 with 4GB RAM)**

Expected usage:
- **RAM:** ~200-400 MB (SQLite + FastAPI)
- **CPU:** ~5-10% idle, ~30% during sync
- **Storage:** ~500 MB per season
- **Network:** ~50 MB/hour during sync

---

## 🔐 **Security Recommendations**

```bash
# 1. Change default Pi password
passwd

# 2. Setup firewall
sudo apt install ufw
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
sudo ufw enable

# 3. Create API key authentication (optional)
# Add to api_server.py:
#   from fastapi.security import APIKeyHeader
#   api_key_header = APIKeyHeader(name="X-API-Key")
```

---

## 📋 **Quick Commands**

```bash
# Restart everything
sudo systemctl restart hockey-stats-api hockey-stats-sync

# Check status
sudo systemctl status hockey-stats-*

# View live logs
sudo journalctl -f -u hockey-stats-api

# Force sync now
sudo systemctl start hockey-stats-sync

# View database
sqlite3 /home/pi/hockey-stats/data/databases/hockey_stats_10776.db

# Test API
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/teams/386316
```

---

## 🎉 **You're Done!**

Your Pi now:
- ✅ Auto-syncs new games every hour
- ✅ Serves API 24/7
- ✅ Backs up daily
- ✅ Self-heals if it crashes
- ✅ Uses minimal resources
- ✅ Accessible from anywhere on your network

**Update from PC:** Just run `./deploy.sh` and changes go live immediately!
