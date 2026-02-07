# Hockey Stats API - Complete Setup Instructions for Claude Code
## Comprehensive Development & Deployment Guide

**Target Environment:** macOS Development → Raspberry Pi Production
**Claude Code Version:** Latest
**Python Version:** 3.10+

---

# 📋 TABLE OF CONTENTS

1. [System Overview](#system-overview)
2. [Project Structure](#project-structure)
3. [Phase 1: Development Setup (PC)](#phase-1-development-setup-pc)
4. [Phase 2: Initial Data Import](#phase-2-initial-data-import)
5. [Phase 3: Testing & Validation](#phase-3-testing--validation)
6. [Phase 4: Raspberry Pi Deployment](#phase-4-raspberry-pi-deployment)
7. [Phase 5: Production Configuration](#phase-5-production-configuration)
8. [Common Operations](#common-operations)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Features](#advanced-features)

---

# 🎯 SYSTEM OVERVIEW

## What This System Does

This is a **professional-grade hockey statistics platform** that:

1. **Extracts data** from GameSheet API (any league, any season)
2. **Stores locally** in SQLite database (fast queries, no re-imports)
3. **Calculates advanced metrics** (SOS, H2H, streaks, special teams)
4. **Serves via REST API** (20+ endpoints, LLM-friendly responses)
5. **Auto-syncs hourly** (only new games, 1-2 minute updates)
6. **Runs 24/7 on Raspberry Pi** (low resource usage)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT (macOS)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Scraper   │→ │   Database   │→ │  API Server  │       │
│  │  (Import)   │  │   (SQLite)   │  │  (FastAPI)   │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│         ↓                ↓                  ↓                │
│    Data Import      Stats Calc         Testing              │
└─────────────────────────────────────────────────────────────┘
                           ↓
                    Git/rsync Deploy
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  PRODUCTION (Raspberry Pi)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Auto-Sync  │→ │   Database   │→ │  API Server  │       │
│  │  (Hourly)   │  │  (Cached)    │  │   (24/7)     │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│         ↑                                  ↓                 │
│    Systemd Timer                      Nginx Proxy           │
│                                            ↓                 │
│                              http://pi.local/api/v1/...      │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

✅ **GameSheet API Integration** - Complete data extraction
✅ **Incremental Sync** - Only fetch new games (fast updates)
✅ **Advanced Statistics** - SOS, H2H, PP%, PK%, streaks
✅ **REST API** - 20+ endpoints with LLM-friendly responses
✅ **Data Quality** - Confidence scores, issue detection
✅ **Club/Team Organization** - Parse team names intelligently
✅ **Production Ready** - Systemd services, auto-restart, backups
✅ **Low Resource Usage** - Perfect for Raspberry Pi

---

# 📁 PROJECT STRUCTURE

```
Hockey_Scraper/
│
├── Core System Components
│   ├── advanced_stats_database.py      # Database schema (13 tables)
│   ├── data_importer.py                # GameSheet API → Database
│   ├── stats_calculator.py             # Basic stats calculation
│   ├── advanced_metrics.py             # SOS, H2H, streaks
│   ├── data_quality_analyzer.py        # Quality monitoring
│   ├── api_server.py                   # FastAPI REST server
│   ├── api_models.py                   # Pydantic response models
│   └── pipeline_config.py              # Configuration system
│
├── Pipeline & Automation
│   ├── full_pipeline.py                # Complete orchestrator
│   ├── incremental_import.py           # Fast sync (new games only)
│   ├── auto_sync.py                    # Hourly sync script
│   └── test_full_pipeline.py           # Integration tests
│
├── Utilities
│   ├── query_team_386316.py            # Example team query
│   ├── create_test_database.py         # Test data generator
│   └── backup.sh                       # Database backup script
│
├── Documentation
│   ├── GAMESHEET_API_DOCUMENTATION.md  # Complete API reference
│   ├── ADVANCED_STATS_API_DESIGN.md    # System architecture
│   ├── PIPELINE_QUICKSTART.md          # Quick start guide
│   ├── RASPBERRY_PI_DEPLOYMENT.md      # Pi deployment guide
│   └── CLAUDE_CODE_SETUP_INSTRUCTIONS.md # This file
│
├── Configuration
│   ├── requirements.txt                # Python dependencies
│   ├── .gitignore                      # Git exclusions
│   └── deploy.sh                       # Deploy to Pi script
│
└── Data & Output (Created at runtime)
    ├── data/
    │   └── databases/
    │       └── hockey_stats_{season_id}.db
    ├── logs/
    │   ├── pipeline_{season_id}.log
    │   ├── auto_sync.log
    │   └── api_server.log
    └── backups/
        └── hockey_stats_{date}.db
```

---

# 🚀 PHASE 1: Development Setup (PC)

## Step 1.1: Verify Environment

**Task:** Check that you have the required tools installed.

```bash
# Check Python version (must be 3.10+)
python3 --version
# Expected: Python 3.10.x or higher

# Check pip
pip3 --version

# Check git
git --version

# Check you're in the right directory
pwd
# Expected: /path/to/Hockey_Scraper
```

**If any tools are missing:**
- Python 3.10+: Install from python.org or use Homebrew (`brew install python@3.10`)
- pip: `python3 -m ensurepip --upgrade`
- git: `brew install git` or download from git-scm.com

## Step 1.2: Install Python Dependencies

**Task:** Install all required Python packages.

```bash
cd "/path/to/Hockey_Scraper"

# Install all dependencies
pip3 install -r requirements.txt

# Verify critical packages
python3 -c "
import fastapi
import uvicorn
import requests
import sqlite3
import pandas
print('✅ All dependencies installed successfully')
"
```

**If requirements.txt is missing or outdated, create it:**

```bash
cat > requirements.txt << 'EOF'
# Core API Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# Database & Data Processing
SQLAlchemy==2.0.23
pandas==2.1.3

# HTTP Requests
requests==2.31.0
httpx==0.25.1

# Data Validation
python-multipart==0.0.6

# Scheduling (for auto-sync)
APScheduler==3.10.4

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1

# Utilities
python-dotenv==1.0.0
tqdm==4.66.1
EOF

pip3 install -r requirements.txt
```

## Step 1.3: Initialize Git Repository

**Task:** Set up version control for deployment.

```bash
cd "/path/to/Hockey_Scraper"

# Initialize git (if not already)
git init

# Create comprehensive .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.egg
*.egg-info/
dist/
build/
.eggs/
pip-log.txt
pip-delete-this-directory.txt

# Databases
*.db
*.db-journal
*.db-shm
*.db-wal
*.sqlite
*.sqlite3

# Logs
*.log
logs/
*.log.*

# Reports
reports/
output/

# Data files
data/
*.csv
*.json.backup
*.json.old

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Environment
.env
.env.local
config.local.json
secrets.json

# Temporary
tmp/
temp/
*.tmp
EOF

# Add all code files (but not data/logs)
git add *.py *.md requirements.txt
git status

# Initial commit
git commit -m "Initial commit - Hockey Stats API System

- Complete GameSheet API integration
- SQLite database with 13 tables
- Stats calculation engine (basic + advanced)
- FastAPI REST server (20+ endpoints)
- Data quality analyzer
- Raspberry Pi deployment setup
"
```

## Step 1.4: Verify Core Files Exist

**Task:** Ensure all necessary files are present.

```bash
# Check for critical files
for file in \
    advanced_stats_database.py \
    data_importer.py \
    stats_calculator.py \
    advanced_metrics.py \
    api_server.py \
    api_models.py \
    full_pipeline.py \
    incremental_import.py \
    pipeline_config.py; do

    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ MISSING: $file"
    fi
done
```

**If any files are missing:** They should have been created by the previous Claude Code session. Review the conversation history or request recreation.

## Step 1.5: Create Required Directories

**Task:** Set up directory structure for data, logs, and backups.

```bash
# Create directory structure
mkdir -p data/databases
mkdir -p data/raw
mkdir -p logs
mkdir -p backups
mkdir -p reports

# Verify
ls -la

echo "✅ Directory structure created"
```

---

# ⚙️ PHASE 2: Initial Data Import

## Step 2.1: Test Database Connection

**Task:** Verify database creation works.

```bash
# Quick test - create empty database
python3 << 'EOF'
from advanced_stats_database import AdvancedStatsDatabase

db_path = "data/databases/test_connection.db"
with AdvancedStatsDatabase(db_path) as db:
    print(f"✅ Database created at: {db_path}")
    print(f"   Tables: {db.get_table_count()}")
EOF

# Check file was created
ls -lh data/databases/test_connection.db

# Clean up test
rm data/databases/test_connection.db
```

## Step 2.2: Run First Import (Small Division)

**Task:** Import data for ONE division to test the pipeline (fast, ~2 minutes).

**IMPORTANT:** Start with a SMALL division for testing!

```bash
# Find a small division first
python3 << 'EOF'
import requests

season_id = "10776"
url = f"https://gamesheetstats.com/api/useSeasonDivisions/getDivisions/{season_id}"
r = requests.get(url, timeout=10)
divisions = r.json()

print("Available divisions:")
for div in divisions[:10]:
    print(f"  {div['id']:5d} - {div['title']}")

print(f"\nTotal divisions: {len(divisions)}")
print("\nRecommendation: Start with one division for testing")
EOF

# Run import for ONE division (example: 60038 - U10B GOLD)
# This should take ~2-5 minutes
python3 full_pipeline.py \
    --season-id 10776 \
    --phase all \
    --log-level INFO \
    2>&1 | tee logs/first_import.log

# The database will be created at:
# data/databases/hockey_stats_10776.db
```

**Expected output:**
```
🚀 PHASE 1: Database Setup
✅ Created database: hockey_stats_10776.db
✅ Initialized 13 tables

📥 PHASE 2: Data Import
✅ Imported 19 divisions
✅ Imported 171 teams
✅ Imported 1234 games (567 completed)
✅ Imported box scores (567/567)
    - 1234 goals
    - 456 penalties
    - 2345 roster entries

📊 PHASE 3: Calculate Statistics
✅ Player stats: 678 players
✅ Team stats: 171 teams

🎯 PHASE 4: Advanced Metrics
✅ Strength of Schedule
✅ Head-to-Head records
✅ Recent form analysis

✅ COMPLETE - Time: 15m 32s
```

## Step 2.3: Verify Import Success

**Task:** Query the database to confirm data was imported.

```bash
# Check database stats
python3 << 'EOF'
import sqlite3

db_path = "data/databases/hockey_stats_10776.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("📊 DATABASE STATISTICS")
print("=" * 50)

tables = [
    ('divisions', 'Divisions'),
    ('teams', 'Teams'),
    ('games', 'Games'),
    ('goals', 'Goals'),
    ('penalties', 'Penalties'),
    ('game_rosters', 'Roster Entries'),
    ('player_stats', 'Players'),
    ('team_stats', 'Team Stats'),
]

for table, label in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {label:20s}: {count:5d}")

conn.close()
EOF

# Quick team query test
python3 << 'EOF'
import sqlite3

db_path = "data/databases/hockey_stats_10776.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("\n🏒 TOP 5 TEAMS BY POINTS")
print("=" * 50)

cursor.execute("""
    SELECT team_name, games_played, wins, losses, ties, points, points_pct
    FROM team_stats
    ORDER BY points DESC, points_pct DESC
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"  {row['team_name']:30s} {row['wins']}-{row['losses']}-{row['ties']} ({row['points']} pts)")

conn.close()
EOF
```

## Step 2.4: Test Incremental Sync

**Task:** Verify that incremental updates work (only new games).

```bash
# Simulate incremental sync
# (This should complete in <1 minute since no new games)

python3 << 'EOF'
import sqlite3
import requests

season_id = "10776"
db_path = "data/databases/hockey_stats_10776.db"

# Get cached game IDs
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT game_id FROM games")
cached = {row[0] for row in cursor.fetchall()}
conn.close()

print(f"Cached games: {len(cached)}")

# Get current schedule
url = f"https://gamesheetstats.com/api/useSchedule/getSeasonSchedule/{season_id}"
params = {'filter[gametype]': 'overall', 'filter[limit]': 2000, 'filter[offset]': 0}
r = requests.get(url, params=params, timeout=30)
schedule_data = r.json()

current = set()
for key, daily_games in schedule_data.items():
    if isinstance(daily_games, list):
        for day_data in daily_games:
            if isinstance(day_data, dict) and 'games' in day_data:
                for game in day_data['games']:
                    if game.get('status') == 'final':
                        current.add(game.get('id'))

print(f"Current completed games: {len(current)}")

new_games = current - cached
print(f"New games to sync: {len(new_games)}")

if new_games:
    print(f"\n🔔 Would import {len(new_games)} new games")
else:
    print(f"\n✅ No new games - cache is up to date")
EOF
```

---

# 🧪 PHASE 3: Testing & Validation

## Step 3.1: Test API Server Locally

**Task:** Start the FastAPI server and test endpoints.

```bash
# Start API server (in background)
python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for startup
sleep 3

# Test health endpoint
curl -s http://localhost:8000/health | python3 -m json.tool

# Test season endpoint
curl -s http://localhost:8000/api/v1/seasons/10776 | python3 -m json.tool

# Test team endpoint
curl -s "http://localhost:8000/api/v1/teams/386316" | python3 -m json.tool

# Open interactive docs in browser
echo "📖 API Documentation: http://localhost:8000/docs"
echo "   (Open this URL in your browser)"

# Stop server when done testing
# kill $API_PID
```

**Expected Response (health check):**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-08T21:30:00.000Z",
  "database": "connected",
  "version": "1.0.0"
}
```

## Step 3.2: Run Integration Tests

**Task:** Verify all components work together.

```bash
# Run test suite
python3 test_full_pipeline.py --quick

# Expected output:
# ✅ Database schema tests: PASS
# ✅ Data import tests: PASS
# ✅ Stats calculation tests: PASS
# ✅ API server tests: PASS
# ✅ Data quality tests: PASS
#
# All tests passed!
```

## Step 3.3: Generate Sample Reports

**Task:** Create test reports to verify data quality.

```bash
# Generate team report for WHK
python3 query_team_386316.py \
    data/databases/hockey_stats_10776.db \
    386316 \
    > reports/team_386316_report.txt

# View report
cat reports/team_386316_report.txt

# Run data quality analysis
python3 data_quality_analyzer.py \
    --db data/databases/hockey_stats_10776.db \
    --output reports/data_quality_report.json

# View quality report
python3 -m json.tool reports/data_quality_report.json | head -50
```

---

# 🥧 PHASE 4: Raspberry Pi Deployment

## Step 4.1: Prepare Deployment Package

**Task:** Create deployment script and configuration.

```bash
# Create deployment script
cat > deploy.sh << 'EOF'
#!/bin/bash
# Deploy to Raspberry Pi

# Configuration
PI_HOST="${PI_HOST:-pi@raspberrypi.local}"  # Change if needed
PI_DIR="/home/pi/hockey-stats"
EXCLUDE_PATTERNS="--exclude '*.db' --exclude '*.log' --exclude 'data/' --exclude '__pycache__' --exclude '.git'"

echo "🚀 Deploying to Raspberry Pi..."
echo "   Target: $PI_HOST"
echo "   Directory: $PI_DIR"

# Test connection
if ! ping -c 1 $(echo $PI_HOST | cut -d@ -f2) > /dev/null 2>&1; then
    echo "❌ Cannot reach Pi. Check network connection."
    exit 1
fi

# Sync code
echo "📦 Syncing code..."
rsync -avz $EXCLUDE_PATTERNS \
    ./ ${PI_HOST}:${PI_DIR}/

if [ $? -ne 0 ]; then
    echo "❌ Sync failed"
    exit 1
fi

echo "✅ Code synced successfully"

# Restart services on Pi
echo "🔄 Restarting services on Pi..."
ssh ${PI_HOST} << 'ENDSSH'
cd /home/pi/hockey-stats

# Activate virtual environment and install dependencies
source venv/bin/activate
pip3 install -q -r requirements.txt

# Restart services
sudo systemctl restart hockey-stats-api 2>/dev/null || echo "   (API service not set up yet)"
sudo systemctl restart hockey-stats-sync.timer 2>/dev/null || echo "   (Sync timer not set up yet)"

echo "✅ Services restarted"
ENDSSH

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Next steps:"
echo "  1. SSH to Pi: ssh $PI_HOST"
echo "  2. Check API: curl http://localhost:8000/health"
echo "  3. View logs: sudo journalctl -u hockey-stats-api -f"
EOF

chmod +x deploy.sh

echo "✅ Deployment script created"
```

## Step 4.2: Test SSH Connection to Pi

**Task:** Verify you can connect to your Raspberry Pi.

```bash
# Test SSH connection
# Replace with your Pi's hostname or IP
PI_HOST="pi@raspberrypi.local"

ssh ${PI_HOST} "echo '✅ SSH connection successful'; python3 --version"

# If this fails:
# 1. Check Pi is on and connected to network
# 2. Try IP address instead: pi@192.168.1.100
# 3. Ensure SSH is enabled on Pi (raspi-config → Interface Options → SSH)
```

## Step 4.3: Initial Pi Setup (One-Time)

**Task:** Prepare Raspberry Pi for first deployment.

```bash
# Run this from your PC - it sets up Pi remotely
ssh ${PI_HOST} << 'ENDSSH'

echo "🥧 Setting up Raspberry Pi for Hockey Stats..."

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "Installing dependencies..."
sudo apt install -y python3-pip python3-venv nginx git sqlite3

# Create project directory
echo "Creating project directory..."
mkdir -p /home/pi/hockey-stats/data/databases
mkdir -p /home/pi/hockey-stats/logs
mkdir -p /home/pi/hockey-stats/backups

cd /home/pi/hockey-stats

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "✅ Raspberry Pi setup complete"
echo ""
echo "Next: Run './deploy.sh' from your PC to deploy code"

ENDSSH
```

## Step 4.4: Deploy to Pi

**Task:** Push code to Raspberry Pi.

```bash
# Deploy from PC
./deploy.sh

# Verify deployment
ssh ${PI_HOST} "ls -la /home/pi/hockey-stats/*.py | head -10"

echo "✅ Code deployed to Pi"
```

---

# ⚙️ PHASE 5: Production Configuration

## Step 5.1: Setup Systemd Services on Pi

**Task:** Configure auto-start services.

```bash
# Run on Pi (SSH in)
ssh ${PI_HOST}

cd /home/pi/hockey-stats

# Create API service
sudo tee /etc/systemd/system/hockey-stats-api.service > /dev/null << 'EOF'
[Unit]
Description=Hockey Stats FastAPI Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/hockey-stats
Environment="PATH=/home/pi/hockey-stats/venv/bin"
ExecStart=/home/pi/hockey-stats/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create sync service
sudo tee /etc/systemd/system/hockey-stats-sync.service > /dev/null << 'EOF'
[Unit]
Description=Hockey Stats Incremental Sync
After=network.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/hockey-stats
Environment="PATH=/home/pi/hockey-stats/venv/bin"
ExecStart=/home/pi/hockey-stats/venv/bin/python3 auto_sync.py
StandardOutput=journal
StandardError=journal
EOF

# Create timer for hourly sync
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

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable hockey-stats-api.service
sudo systemctl enable hockey-stats-sync.timer
sudo systemctl start hockey-stats-api.service
sudo systemctl start hockey-stats-sync.timer

# Check status
sudo systemctl status hockey-stats-api
sudo systemctl status hockey-stats-sync.timer

echo "✅ Systemd services configured"
```

## Step 5.2: Setup Nginx Reverse Proxy on Pi

**Task:** Configure web server for API access.

```bash
# Still on Pi via SSH

# Create nginx config
sudo tee /etc/nginx/sites-available/hockey-stats > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    # API endpoints
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Interactive docs
    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_set_header Host $host;
    }

    location /redoc {
        proxy_pass http://localhost:8000/redoc;
        proxy_set_header Host $host;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8000/health;
    }

    # Root redirect to docs
    location / {
        return 301 /docs;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/hockey-stats /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test config
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

echo "✅ Nginx configured"
echo ""
echo "Access API at:"
echo "  http://$(hostname -I | awk '{print $1}')/docs"
```

## Step 5.3: Setup Auto-Sync Script on Pi

**Task:** Create the incremental sync script.

```bash
# Still on Pi

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

    # Check if games table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
    if not cursor.fetchone():
        conn.close()
        return set()

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

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            log(f"API error: HTTP {response.status_code}")
            return set()

        schedule_data = response.json()
        game_ids = set()

        for key, daily_games in schedule_data.items():
            if isinstance(daily_games, list):
                for day_data in daily_games:
                    if isinstance(day_data, dict) and 'games' in day_data:
                        for game in day_data['games']:
                            if game.get('status') == 'final':
                                game_ids.add(game.get('id'))

        return game_ids
    except Exception as e:
        log(f"Error fetching schedule: {e}")
        return set()

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
        return 0

    log(f"Importing {len(new_games)} new games...")

    # Import new games using data_importer
    import subprocess
    result = subprocess.run([
        '/home/pi/hockey-stats/venv/bin/python3',
        '-c',
        f"""
import sys
sys.path.insert(0, '/home/pi/hockey-stats')
from data_importer import GameSheetDataImporter

importer = GameSheetDataImporter('{DB_PATH}')
game_ids = {list(new_games)}
for game_id in game_ids:
    importer.import_single_game('{SEASON_ID}', game_id)
print('Import complete')
"""
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
            return 0
        else:
            log(f"⚠️  Stats calculation warning: {result.stderr}")
            return 0  # Don't fail on stats calc errors
    else:
        log(f"❌ Import failed: {result.stderr}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = sync_new_games()
        sys.exit(exit_code)
    except Exception as e:
        log(f"❌ Fatal error: {e}")
        sys.exit(1)
EOF

chmod +x /home/pi/hockey-stats/auto_sync.py

echo "✅ Auto-sync script created"

# Test it
python3 /home/pi/hockey-stats/auto_sync.py
```

## Step 5.4: Copy Database from PC to Pi

**Task:** Transfer the initial database you created on PC.

```bash
# Run from PC
scp "data/databases/hockey_stats_10776.db" \
    ${PI_HOST}:/home/pi/hockey-stats/data/databases/

echo "✅ Database transferred to Pi"

# Verify on Pi
ssh ${PI_HOST} "ls -lh /home/pi/hockey-stats/data/databases/hockey_stats_10776.db"
```

---

# 📚 COMMON OPERATIONS

## Daily Development Workflow

```bash
# 1. Make changes on PC
vim api_server.py

# 2. Test locally
python3 -m uvicorn api_server:app --reload

# 3. Commit changes
git add api_server.py
git commit -m "Added new endpoint"

# 4. Deploy to Pi
./deploy.sh
```

## Query Specific Team

```bash
# Quick query from PC (direct API, no database needed)
python3 << 'EOF'
import requests
team_id = 386316
season_id = 10776

url = f"http://raspberrypi.local/api/v1/teams/{team_id}"
r = requests.get(url, timeout=10)
print(r.json())
EOF

# Or query Pi's database via SSH
ssh ${PI_HOST} << 'ENDSSH'
sqlite3 /home/pi/hockey-stats/data/databases/hockey_stats_10776.db \
  "SELECT * FROM team_stats WHERE team_id = 386316"
ENDSSH
```

## Force Manual Sync on Pi

```bash
# Trigger sync immediately (don't wait for hourly timer)
ssh ${PI_HOST} "sudo systemctl start hockey-stats-sync.service"

# Check sync log
ssh ${PI_HOST} "tail -20 /home/pi/hockey-stats/logs/auto_sync.log"
```

## View Logs

```bash
# API server logs
ssh ${PI_HOST} "sudo journalctl -u hockey-stats-api -f"

# Sync logs
ssh ${PI_HOST} "sudo journalctl -u hockey-stats-sync -f"

# Auto-sync log file
ssh ${PI_HOST} "tail -f /home/pi/hockey-stats/logs/auto_sync.log"
```

## Backup Database

```bash
# Manual backup
ssh ${PI_HOST} << 'ENDSSH'
DATE=$(date +%Y%m%d_%H%M%S)
sqlite3 /home/pi/hockey-stats/data/databases/hockey_stats_10776.db \
  ".backup /home/pi/hockey-stats/backups/hockey_stats_${DATE}.db"
echo "✅ Backup created: hockey_stats_${DATE}.db"
ENDSSH

# Download backup to PC
scp ${PI_HOST}:/home/pi/hockey-stats/backups/hockey_stats_*.db ./backups/
```

## Restart All Services

```bash
# Restart API and sync
ssh ${PI_HOST} "sudo systemctl restart hockey-stats-api hockey-stats-sync.timer"

# Check status
ssh ${PI_HOST} "sudo systemctl status hockey-stats-*"
```

---

# 🔧 TROUBLESHOOTING

## Problem: Database locked error

**Symptom:** `sqlite3.OperationalError: database is locked`

**Solution:**
```bash
# Stop services accessing database
ssh ${PI_HOST} "sudo systemctl stop hockey-stats-api"

# Run operation
# ...

# Restart services
ssh ${PI_HOST} "sudo systemctl start hockey-stats-api"
```

## Problem: API not accessible

**Symptom:** Cannot access http://raspberrypi.local/docs

**Solutions:**
```bash
# 1. Check API service is running
ssh ${PI_HOST} "sudo systemctl status hockey-stats-api"

# 2. Check nginx is running
ssh ${PI_HOST} "sudo systemctl status nginx"

# 3. Check port 8000 is listening
ssh ${PI_HOST} "sudo netstat -tulpn | grep 8000"

# 4. Test locally on Pi
ssh ${PI_HOST} "curl http://localhost:8000/health"

# 5. Check firewall
ssh ${PI_HOST} "sudo ufw status"
```

## Problem: Sync not running

**Symptom:** New games not appearing

**Solutions:**
```bash
# 1. Check timer is active
ssh ${PI_HOST} "sudo systemctl status hockey-stats-sync.timer"

# 2. Check last run time
ssh ${PI_HOST} "sudo journalctl -u hockey-stats-sync | tail -20"

# 3. Run manually
ssh ${PI_HOST} "sudo systemctl start hockey-stats-sync.service"

# 4. Check logs
ssh ${PI_HOST} "tail -50 /home/pi/hockey-stats/logs/auto_sync.log"
```

## Problem: Import fails with API errors

**Symptom:** `requests.exceptions.Timeout` or HTTP 429

**Solutions:**
```bash
# Increase API delay in pipeline_config.py
# Change: API_DELAY = 0.1
# To:     API_DELAY = 0.3

# Or reduce batch size
# Change: IMPORT_BATCH_SIZE = 100
# To:     IMPORT_BATCH_SIZE = 50
```

## Problem: Stats calculation errors

**Symptom:** Division by zero, NULL values

**Solution:**
```bash
# Recalculate stats with verbose logging
ssh ${PI_HOST} << 'ENDSSH'
cd /home/pi/hockey-stats
source venv/bin/activate
python3 stats_calculator.py \
  data/databases/hockey_stats_10776.db \
  10776 \
  --verbose
ENDSSH
```

---

# 🚀 ADVANCED FEATURES

## Setup Multiple Seasons

```bash
# Import additional seasons
python3 full_pipeline.py --season-id 10477 --phase all

# Databases created:
# - hockey_stats_10776.db (Bay State Hockey 2025-26)
# - hockey_stats_10477.db (Another league/season)

# API automatically serves all seasons
curl http://raspberrypi.local/api/v1/seasons
```

## Setup Notifications (Optional)

```bash
# Install notification library on Pi
ssh ${PI_HOST} "pip3 install apprise"

# Add to auto_sync.py:
cat >> auto_sync.py << 'EOF'

# At end of sync_new_games():
if new_games:
    from apprise import Apprise
    apobj = Apprise()
    apobj.add('mailto://user:pass@gmail.com')
    apobj.notify(
        title='Hockey Stats Update',
        body=f'{len(new_games)} new games imported'
    )
EOF
```

## Add Custom Endpoints

```bash
# Edit api_server.py to add new endpoints
vim api_server.py

# Example: Add endpoint for club stats
# (See api_server.py for existing patterns)

# Deploy to Pi
./deploy.sh
```

## Performance Tuning

```bash
# For faster imports, increase workers
# In api_server systemd service:
# Change: --workers 2
# To:     --workers 4

# For Pi 4 with 4GB RAM, you can use up to 4 workers
```

---

# ✅ FINAL CHECKLIST

## PC Setup Complete

- [ ] Python 3.10+ installed
- [ ] All dependencies installed (`pip3 install -r requirements.txt`)
- [ ] Git repository initialized
- [ ] Directory structure created (data/, logs/, backups/)
- [ ] Test import completed successfully
- [ ] API server tested locally
- [ ] Integration tests pass

## Raspberry Pi Setup Complete

- [ ] SSH access working
- [ ] Project directory created (`/home/pi/hockey-stats`)
- [ ] Virtual environment created
- [ ] Dependencies installed on Pi
- [ ] Database transferred from PC
- [ ] Systemd services created and enabled
- [ ] Nginx configured and running
- [ ] Auto-sync tested and working
- [ ] API accessible from network

## Deployment Workflow Ready

- [ ] `deploy.sh` script working
- [ ] Git commits being made
- [ ] Services restart after deployment
- [ ] Logs accessible and readable

## Production Ready

- [ ] Hourly sync running automatically
- [ ] API serving requests 24/7
- [ ] Backups scheduled
- [ ] Health checks working
- [ ] Network access confirmed

---

# 🎉 SUCCESS!

If all checklists are complete, you now have:

✅ **Full development environment** on macOS
✅ **Production server** on Raspberry Pi
✅ **Automatic syncing** every hour
✅ **REST API** accessible 24/7
✅ **Complete stats** for any GameSheet league
✅ **One-command deployment** workflow

**Access your API:**
- Local: http://raspberrypi.local/docs
- IP: http://192.168.1.XXX/docs
- Query: `curl http://raspberrypi.local/api/v1/teams/386316`

**Next Game Updates:**
- Automatic sync every hour
- Only fetches new games (1-2 mins)
- Stats auto-calculated
- Available immediately via API

**Make Changes:**
```bash
# On PC
vim api_server.py
./deploy.sh
# Changes live on Pi in 30 seconds!
```

---

# 📖 DOCUMENTATION REFERENCE

- **GAMESHEET_API_DOCUMENTATION.md** - Complete API reference
- **ADVANCED_STATS_API_DESIGN.md** - System architecture
- **PIPELINE_QUICKSTART.md** - Quick start guide
- **RASPBERRY_PI_DEPLOYMENT.md** - Detailed Pi setup
- **CLAUDE_CODE_SETUP_INSTRUCTIONS.md** - This file

---

**Created for Claude Code**
**Last Updated:** 2025-11-08
**Version:** 1.0.0
