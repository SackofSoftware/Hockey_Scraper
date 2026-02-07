# Hockey Stats System - Ready for Deployment

## System Status

### ✅ Bay State Hockey League - COMPLETE & NORMALIZED
- **Database**: `advanced_hockey_stats_full.db` (4.6 MB)
- **5,573 goals** with full details
- **1,847 penalties**
- **188 teams** → **30 clubs** (normalized)
- **25 divisions** (U8-High School + Girls)
- **WHK**: 9 teams total

### ✅ Eastern Hockey Federation - COMPLETE & NORMALIZED
- **Database**: `advanced_hockey_stats_ehf_10477.db` (12+ MB)
- **22,764 goals** (4x larger than Bay State!)
- **17,724 penalties**
- **502 teams** → normalized clubs
- **47 divisions**

### ✅ Smart Update System - CONFIGURED
- **Time-aware scheduling** (game days vs off times)
- **Systemd timers** for both leagues
- **15-minute updates** on game days (Fri PM, Sat, Sun)
- **4-hour updates** during off times
- **Status tracking** (scheduled vs completed games)

---

## Deployment Files Ready

### Core System
- `smart_updater.py` - Time-aware update agent
- `advanced_stats_database.py` - Database schema
- `data_importer.py` - GameSheet API importer
- `normalize_team_names.py` - Club normalization

### Systemd Services
- `pi/systemd/hockey-update-baystate.service` - Bay State update service
- `pi/systemd/hockey-update-baystate.timer` - Bay State update schedule
- `pi/systemd/hockey-update-ehf.service` - EHF update service
- `pi/systemd/hockey-update-ehf.timer` - EHF update schedule

### Databases
- `advanced_hockey_stats_full.db` - Bay State (4.6 MB)
- `advanced_hockey_stats_ehf_10477.db` - EHF (12+ MB)

### Deployment Script
- `pi/deploy_to_pi.sh` - Automated deployment to Raspberry Pi

---

## How to Deploy

### Option 1: Automated Deployment (Recommended)

```bash
cd "/path/to/Hockey_Scraper"
bash pi/deploy_to_pi.sh
```

This will:
1. Test connection to Pi
2. Create directories
3. Copy all Python scripts
4. Copy both databases
5. Install systemd services
6. Enable and start timers
7. Show status

### Option 2: Manual Deployment

```bash
# 1. Copy files to Pi
scp smart_updater.py pi@<raspberry-pi-ip>:~/hockey-stats/
scp advanced_stats_database.py pi@<raspberry-pi-ip>:~/hockey-stats/
scp data_importer.py pi@<raspberry-pi-ip>:~/hockey-stats/
scp normalize_team_names.py pi@<raspberry-pi-ip>:~/hockey-stats/

# 2. Copy databases
scp advanced_hockey_stats_full.db pi@<raspberry-pi-ip>:~/hockey-stats/
scp advanced_hockey_stats_ehf_10477.db pi@<raspberry-pi-ip>:~/hockey-stats/

# 3. Copy and install systemd services
scp pi/systemd/hockey-update-*.* pi@<raspberry-pi-ip>:~/
ssh pi@<raspberry-pi-ip>
sudo cp ~/hockey-update-*.service /etc/systemd/system/
sudo cp ~/hockey-update-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hockey-update-baystate.timer hockey-update-ehf.timer
sudo systemctl start hockey-update-baystate.timer hockey-update-ehf.timer
```

---

## Post-Deployment Commands

### View Update Schedule
```bash
ssh pi@<raspberry-pi-ip> 'systemctl list-timers hockey-update-*'
```

### View Logs (Live)
```bash
# Bay State
ssh pi@<raspberry-pi-ip> 'journalctl -u hockey-update-baystate.service -f'

# EHF
ssh pi@<raspberry-pi-ip> 'journalctl -u hockey-update-ehf.service -f'
```

### Manual Update
```bash
# Bay State
ssh pi@<raspberry-pi-ip> 'cd /home/pi/hockey-stats && python3 smart_updater.py --league baystate'

# EHF
ssh pi@<raspberry-pi-ip> 'cd /home/pi/hockey-stats && python3 smart_updater.py --league ehf'
```

### Check Database Status
```bash
ssh pi@<raspberry-pi-ip> 'cd /home/pi/hockey-stats && python3 smart_updater.py --league baystate --check-schedule'
```

### Stop/Start Services
```bash
# Stop all updates
ssh pi@<raspberry-pi-ip> 'sudo systemctl stop hockey-update-*.timer'

# Start all updates
ssh pi@<raspberry-pi-ip> 'sudo systemctl start hockey-update-*.timer'

# Disable updates (survive reboot)
ssh pi@<raspberry-pi-ip> 'sudo systemctl disable hockey-update-*.timer'
```

---

## Update Schedule

### Game Days (Fri PM, Sat, Sun)
- Every **15 minutes**
- Friday: 5 PM - 11 PM
- Saturday: 8 AM - 11 PM
- Sunday: 8 AM - 11 PM

### Weekday Evenings (Mon-Thu, 6-9 PM)
- Every **30 minutes**
- Catches occasional weekday games

### Off Times
- Every **4 hours**
- Minimal overhead, just checks for schedule changes

---

## What Gets Updated

### Schedule Update (Lightweight)
- Fetches game schedule JSON (~100 KB)
- Updates game status (scheduled → complete)
- Adds new games to database
- Runs every time

### Box Score Update (Smart)
- Only fetches for completed games
- Skips games already imported
- Updates goals, assists, penalties, rosters
- Recalculates player/team stats
- Runs only for new completed games

---

## Database Queries

### Query by Club
```sql
-- All WHK teams
SELECT * FROM teams WHERE club_name = 'WHK';

-- All Hingham goals
SELECT * FROM goals WHERE club_name = 'Hingham';

-- All Canton games
SELECT * FROM games WHERE home_club = 'Canton' OR visitor_club = 'Canton';

-- Top scorers by club
SELECT club, player_number, SUM(goals) as total_goals
FROM player_stats
WHERE club = 'WHK'
GROUP BY club, player_number
ORDER BY total_goals DESC
LIMIT 10;
```

---

## Troubleshooting

### Services Not Running
```bash
ssh pi@<raspberry-pi-ip> 'sudo systemctl status hockey-update-baystate.timer'
ssh pi@<raspberry-pi-ip> 'sudo systemctl start hockey-update-baystate.timer'
```

### Database Locked
```bash
# Stop all services
ssh pi@<raspberry-pi-ip> 'sudo systemctl stop hockey-update-*.timer'

# Run manual update
ssh pi@<raspberry-pi-ip> 'cd /home/pi/hockey-stats && python3 smart_updater.py --league baystate'

# Restart services
ssh pi@<raspberry-pi-ip> 'sudo systemctl start hockey-update-*.timer'
```

### Check Last Update
```bash
ssh pi@<raspberry-pi-ip> 'journalctl -u hockey-update-baystate.service --since "1 hour ago"'
```

---

## Next Steps

1. **Deploy to Pi**: Run `bash pi/deploy_to_pi.sh`
2. **Monitor first weekend**: Check logs during game days
3. **Verify updates**: Confirm new games being imported
4. **Add Sprocket scraper**: For Bay State U6 divisions (optional)
5. **Build API layer**: REST API to serve data (optional)
6. **Ollama integration**: Natural language queries (optional)

---

Generated: November 9, 2025
System Ready for Production Deployment
