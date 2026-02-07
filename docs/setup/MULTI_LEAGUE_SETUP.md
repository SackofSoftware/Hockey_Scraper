# 🏒 Multi-League Setup Guide
## Supporting Multiple Hockey Leagues in One System

Your system is **already built** to handle multiple leagues! GameSheet is used by many leagues, and your database can store them all.

---

## 🎯 Supported Leagues

Any league using GameSheet Stats can be imported. Examples:

### **Bay State Hockey League**
- **Season ID:** 10776
- **Divisions:** 25
- **Teams:** 188
- **Status:** ✅ Already imported (628 games)

### **Eastern Hockey Federation (EHF)**
- **Season ID:** 10477
- **Divisions:** 47
- **Teams:** ~470 (estimated)
- **Status:** Ready to import

### **Other Leagues**
Any league on https://gamesheetstats.com/ can be added by finding its season ID in the URL.

---

## 📊 Database Strategy Options

### **Option 1: Separate Databases (Recommended)**
Best for clean organization and easier management.

```bash
# Bay State Hockey
python3 full_pipeline.py --season-id 10776 --db-path hockey_bay_state_10776.db

# Eastern Hockey Federation
python3 full_pipeline.py --season-id 10477 --db-path hockey_ehf_10477.db

# Result:
# - hockey_bay_state_10776.db (4.2 MB)
# - hockey_ehf_10477.db (~10 MB estimated)
```

**Pros:**
- Clean separation of leagues
- Easier to backup individual leagues
- Smaller file sizes
- Can delete old seasons easily

**Cons:**
- Need to query multiple databases for cross-league comparisons
- Slightly more complex API routing

### **Option 2: Combined Database**
All leagues in one database, filtered by season_id.

```bash
# Import both to same database
python3 full_pipeline.py --season-id 10776 --db-path hockey_all_leagues.db
python3 full_pipeline.py --season-id 10477 --db-path hockey_all_leagues.db

# Result:
# - hockey_all_leagues.db (~14 MB with both leagues)
```

**Pros:**
- Single database to manage
- Easier cross-league queries
- Simpler deployment

**Cons:**
- Larger database file
- Slower queries (more data to scan)
- Harder to remove old data

---

## 🚀 Quick Setup - Import Both Leagues

### **1. Import Bay State Hockey (Already Done)**
```bash
# Already completed - 628 games imported
ls -lh hockey_stats_10776.db
# -rw-r--r-- 4.2M hockey_stats_10776.db
```

### **2. Import Eastern Hockey Federation**
```bash
# Full import (will take ~20-30 minutes)
python3 full_pipeline.py --season-id 10477 --db-path hockey_ehf_10477.db --phase all

# Check results
python3 validate_system.py
```

### **3. Test EHF Data**
```bash
# Start API server for EHF
python3 api_server.py --db hockey_ehf_10477.db

# Query EHF teams
curl http://localhost:8000/api/v1/seasons/10477/divisions
curl http://localhost:8000/api/v1/divisions/57863/standings
```

---

## 🔄 Multi-League API Server

### **Option A: Multiple Servers (Different Ports)**

Run separate API servers for each league:

```bash
# Terminal 1 - Bay State on port 8000
python3 api_server.py --db hockey_bay_state_10776.db --port 8000

# Terminal 2 - EHF on port 8001
python3 api_server.py --db hockey_ehf_10477.db --port 8001
```

Access:
- Bay State: `http://localhost:8000/api/v1/...`
- EHF: `http://localhost:8001/api/v1/...`

### **Option B: Single Server with Combined Database**

```bash
# One server, all leagues
python3 api_server.py --db hockey_all_leagues.db

# Query by season_id
curl http://localhost:8000/api/v1/seasons/10776/leaders/points  # Bay State
curl http://localhost:8000/api/v1/seasons/10477/leaders/points  # EHF
```

---

## 🍓 Raspberry Pi Deployment - Multi-League

### **Setup 1: Separate Systemd Services**

Create two independent services:

```bash
# Service 1: Bay State Hockey
sudo tee /etc/systemd/system/hockey-api-baystate.service > /dev/null << 'EOF'
[Unit]
Description=Hockey Stats API - Bay State
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/hockey-stats
ExecStart=/home/pi/hockey-stats/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000
Environment="DB_PATH=/home/pi/hockey-stats/hockey_bay_state_10776.db"
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Service 2: Eastern Hockey Federation
sudo tee /etc/systemd/system/hockey-api-ehf.service > /dev/null << 'EOF'
[Unit]
Description=Hockey Stats API - EHF
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/hockey-stats
ExecStart=/home/pi/hockey-stats/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8001
Environment="DB_PATH=/home/pi/hockey-stats/hockey_ehf_10477.db"
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable both
sudo systemctl daemon-reload
sudo systemctl enable hockey-api-baystate hockey-api-ehf
sudo systemctl start hockey-api-baystate hockey-api-ehf
```

### **Setup 2: Separate Sync Timers**

```bash
# Bay State sync timer (hourly)
sudo tee /etc/systemd/system/hockey-sync-baystate.timer > /dev/null << 'EOF'
[Unit]
Description=Sync Bay State Hockey Stats Hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
EOF

# EHF sync timer (hourly, offset by 30 mins)
sudo tee /etc/systemd/system/hockey-sync-ehf.timer > /dev/null << 'EOF'
[Unit]
Description=Sync EHF Hockey Stats Hourly

[Timer]
OnCalendar=*:30:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable timers
sudo systemctl enable hockey-sync-baystate.timer hockey-sync-ehf.timer
sudo systemctl start hockey-sync-baystate.timer hockey-sync-ehf.timer
```

---

## 🌐 Nginx Configuration - Multi-League

Route different paths to different league servers:

```nginx
server {
    listen 80;
    server_name _;

    # Bay State Hockey - /baystate/*
    location /baystate/api/ {
        rewrite ^/baystate/(.*)$ /$1 break;
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }

    # Eastern Hockey Federation - /ehf/*
    location /ehf/api/ {
        rewrite ^/ehf/(.*)$ /$1 break;
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
    }

    # Default - Bay State
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
    }

    location / {
        return 301 /baystate/docs;
    }
}
```

Access:
- Bay State: `http://your-pi/baystate/api/v1/...`
- EHF: `http://your-pi/ehf/api/v1/...`

---

## 📈 Resource Usage - Multiple Leagues

### **Bay State (Already Tested)**
- **Games:** 628
- **Database:** 4.2 MB
- **RAM:** ~150 MB
- **Import Time:** 4.5 minutes

### **EHF (Estimated)**
- **Games:** ~1,500 (estimated)
- **Database:** ~10 MB
- **RAM:** ~200 MB
- **Import Time:** ~15-20 minutes

### **Both Leagues Together**
- **Total Database:** ~14 MB
- **Total RAM:** ~350 MB
- **Raspberry Pi 4 (4GB):** Plenty of headroom! ✅

---

## 🎯 Recommended Setup

For your use case, I recommend:

### **Development (Your PC):**
```bash
# Keep separate databases for testing
python3 full_pipeline.py --season-id 10776 --db-path hockey_bay_state_10776.db
python3 full_pipeline.py --season-id 10477 --db-path hockey_ehf_10477.db

# Test each independently
python3 api_server.py --db hockey_bay_state_10776.db --port 8000
python3 api_server.py --db hockey_ehf_10477.db --port 8001
```

### **Production (Raspberry Pi):**
```bash
# Option 1: Separate services (Recommended)
# - Easier to manage
# - Can enable/disable leagues independently
# - Clearer logs

# Option 2: Combined database
# - Simpler deployment
# - Single sync job
# - Easier for cross-league queries
```

---

## 🔄 Adding More Leagues

To add any GameSheet league:

1. **Find the Season ID**
   - Go to the league's GameSheet page
   - Look in the URL: `gamesheetstats.com/seasons/XXXXX`
   - XXXXX is the season ID

2. **Import the Data**
   ```bash
   python3 full_pipeline.py --season-id XXXXX --db-path hockey_league_XXXXX.db
   ```

3. **Add to Auto-Sync**
   - Create systemd timer
   - Add to incremental sync script

4. **Deploy to Pi**
   ```bash
   ./deploy.sh
   sudo systemctl restart hockey-api-*
   ```

---

## 📊 Example Queries - Cross-League

If using combined database:

```bash
# Compare top scorers across leagues
curl 'http://localhost:8000/api/v1/seasons/10776/leaders/points?limit=10' # Bay State
curl 'http://localhost:8000/api/v1/seasons/10477/leaders/points?limit=10' # EHF

# Get all seasons in database
curl 'http://localhost:8000/api/v1/seasons'

# Get divisions for each league
curl 'http://localhost:8000/api/v1/seasons/10776/divisions'
curl 'http://localhost:8000/api/v1/seasons/10477/divisions'
```

---

## ✅ Next Steps

1. **Test EHF Import Locally**
   ```bash
   # Small test - import one division
   python3 test_ehf_import.py
   ```

2. **Decide on Database Strategy**
   - Separate databases (recommended)
   - Combined database

3. **Deploy to Raspberry Pi**
   - Follow RASPBERRY_PI_DEPLOYMENT.md
   - Add EHF service/timer
   - Configure Nginx routing

4. **Set Up Auto-Sync**
   - Bay State: Every hour
   - EHF: Every hour (offset by 30 minutes)

---

## 🎉 Summary

Your system **already supports multiple leagues** - no code changes needed! Just:

1. Run the pipeline with different `--season-id` values
2. Choose separate or combined database strategy
3. Deploy to Pi with multiple services (if using separate DBs)
4. Set up auto-sync for each league

**The system is league-agnostic and will work with ANY GameSheet league!** 🏒📊
