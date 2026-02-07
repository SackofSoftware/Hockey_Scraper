# Complete Hockey Stats Deployment Guide
**Updated: November 9, 2025**

## Architecture Overview

```
Raspberry Pi (user@<raspberry-pi-ip>)
    ↓ runs data imports hourly
    ↓ syncs via SSH
Windows PC (user@<windows-pc-ip>)
    ↓ stores in Dropbox folder
    ↓ Dropbox auto-syncs
Mac (/path/to/Dropbox/...)
    ↓ Ollama reads database
```

**Data Flow:**
1. Pi imports data → local database
2. Pi syncs database → Windows PC via SSH/SCP
3. Windows PC → Dropbox syncs to Mac
4. Mac Ollama → reads synced database

---

## Step 1: Enable SSH Server on Windows PC

### Install OpenSSH Server

Open **PowerShell as Administrator** and run:

```powershell
# Install SSH Server
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Start the service
Start-Service sshd

# Set to start automatically
Set-Service -Name sshd -StartupType 'Automatic'

# Verify it's running
Get-Service sshd

# Configure firewall (if needed)
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

### Enable Password Authentication

Edit SSH config (if needed):
```powershell
notepad C:\ProgramData\ssh\sshd_config
```

Find and ensure this line is set:
```
PasswordAuthentication yes
```

Restart SSH:
```powershell
Restart-Service sshd
```

### Test from Mac

```bash
# From your Mac terminal:
ssh user@<windows-pc-ip>
# Enter your Windows password when prompted
```

---

## Step 2: Set Up Pi SSH Keys (from Mac)

### Copy Mac's SSH Key to Pi

From your Mac:

```bash
# If you don't have an SSH key, generate one:
ssh-keygen -t rsa -b 4096

# Copy your public key to the Pi:
ssh-copy-id user@<raspberry-pi-ip>

# Or manually:
cat ~/.ssh/id_rsa.pub | ssh user@<raspberry-pi-ip> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### Copy Pi's SSH Key to Windows PC

On the Pi (SSH into it first):

```bash
# Generate SSH key if needed:
ssh-keygen -t rsa -b 4096

# Copy to Windows PC:
ssh-copy-id user@<windows-pc-ip>
```

---

## Step 3: Deploy to Raspberry Pi

### From Your Windows PC

```bash
cd "/path/to/Hockey_Scraper"

# Make sure Pi has password auth enabled temporarily, OR
# Add your Windows PC's SSH public key to Pi's authorized_keys first

# Then run deployment:
python pi/deploy_to_pi.py
```

### Files Being Deployed

**Python Scripts:**
- `smart_updater.py` - Main update orchestrator (with PC sync)
- `advanced_stats_database.py` - Database schema
- `data_importer.py` - GameSheet API importer
- `normalize_team_names.py` - Team normalization
- `advanced_metrics.py` - Advanced metrics calculator
- `sync_to_pc.sh` - Sync script to Windows PC

**Databases:**
- `advanced_hockey_stats_full.db` - Bay State (4.6 MB)
- `advanced_hockey_stats_ehf_10477.db` - EHF (12+ MB)

**Systemd Services:**
- `hockey-update-baystate.service` - Bay State updater
- `hockey-update-baystate.timer` - Bay State schedule
- `hockey-update-ehf.service` - EHF updater
- `hockey-update-ehf.timer` - EHF schedule

---

## Step 4: Verify Deployment

### Check Services Running

```bash
ssh user@<raspberry-pi-ip> 'systemctl list-timers hockey-update-*'
```

### View Logs

```bash
# Bay State logs
ssh user@<raspberry-pi-ip> 'journalctl -u hockey-update-baystate.service -f'

# EHF logs
ssh user@<raspberry-pi-ip> 'journalctl -u hockey-update-ehf.service -f'
```

### Manual Test

```bash
# Test Bay State update
ssh user@<raspberry-pi-ip> 'cd /home/user/hockey-stats && python3 smart_updater.py --league baystate'

# Test sync to PC
ssh user@<raspberry-pi-ip> 'cd /home/user/hockey-stats && bash sync_to_pc.sh'
```

---

## Step 5: Verify Dropbox Sync to Mac

### Check Database on Mac

```bash
cd "/path/to/Hockey_Scraper"

# List databases
ls -lh *.db

# Check last modified time
stat advanced_hockey_stats_full.db

# Query the database
sqlite3 advanced_hockey_stats_full.db "SELECT COUNT(*) FROM games;"
```

---

## Update Schedule

### Game Days (Fri PM, Sat, Sun)
- **Every 15 minutes**
- Friday: 5 PM - 11 PM
- Saturday: 8 AM - 11 PM
- Sunday: 8 AM - 11 PM

### Weekday Evenings (Mon-Thu, 6-9 PM)
- **Every 30 minutes**

### Off Times
- **Every 4 hours**

---

## System Credentials

### Raspberry Pi
- **Host:** <raspberry-pi-ip>
- **Username:** <your-username>
- **Password:** <your-password>
- **Location:** `/home/user/hockey-stats/`

### Windows PC
- **Host:** <windows-pc-ip>
- **Username:** <your-username>
- **Password:** <your-password>
- **Location:** `/path/to/Hockey_Scraper/`

### Mac
- **Location:** `/path/to/Hockey_Scraper/`
- **Ollama:** Reads databases from this location

---

## Troubleshooting

### SSH Connection Refused (Pi)

```bash
# On the Pi:
sudo systemctl status sshd
sudo systemctl restart sshd

# Enable password auth if needed:
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication yes
sudo systemctl restart sshd
```

### SSH Connection Refused (Windows PC)

```powershell
# On Windows (PowerShell as Admin):
Get-Service sshd
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
```

### Sync Fails from Pi to PC

```bash
# Test SSH connection from Pi:
ssh user@<windows-pc-ip> "echo 'Connection successful'"

# Test SCP:
touch /tmp/test.txt
scp /tmp/test.txt user@<windows-pc-ip>:"/c/Users/user/test.txt"

# Check sync script:
ssh user@<raspberry-pi-ip> 'cd /home/user/hockey-stats && bash -x sync_to_pc.sh'
```

### Database Not Syncing to Mac

```bash
# On Mac, check Dropbox status:
ps aux | grep Dropbox

# Check if Dropbox folder is syncing:
ls -l "/path/to/Dropbox/"

# Force Dropbox sync:
# Open Dropbox app → Preferences → Sync → Selective Sync
```

### Services Not Running on Pi

```bash
ssh user@<raspberry-pi-ip> 'sudo systemctl status hockey-update-baystate.timer'
ssh user@<raspberry-pi-ip> 'sudo systemctl start hockey-update-baystate.timer'
ssh user@<raspberry-pi-ip> 'sudo systemctl enable hockey-update-baystate.timer'
```

---

## Mac: Testing Ollama Integration

### Verify Database Access

```bash
cd "/path/to/Hockey_Scraper"

# Test query
sqlite3 advanced_hockey_stats_full.db <<EOF
SELECT
    t.team_name,
    t.club_name,
    COUNT(DISTINCT g.game_id) as games_played
FROM teams t
LEFT JOIN games g ON (g.home_team_id = t.team_id OR g.visitor_team_id = t.team_id)
WHERE t.club_name = 'WHK'
GROUP BY t.team_id, t.team_name, t.club_name;
EOF
```

### Test with Ollama

```bash
# Example: Query for WHK teams
ollama run <your-model> "How many WHK teams are there in the database at /path/to/Hockey_Scraper/advanced_hockey_stats_full.db?"
```

---

## Next Steps

1. ✅ **Complete SSH Setup**
   - Ensure SSH server running on Windows PC
   - Verify Pi can connect to Windows PC

2. ✅ **Deploy to Pi**
   - Run `python pi/deploy_to_pi.py`
   - Verify services are running

3. ✅ **Test Sync Chain**
   - Manual update on Pi
   - Verify database appears on Windows PC
   - Verify Dropbox syncs to Mac
   - Test Ollama can read database

4. ✅ **Monitor First Weekend**
   - Check logs during game days
   - Verify databases are updating
   - Confirm sync is working

---

## Support

**Common Commands Cheatsheet:**

```bash
# Check Pi services
ssh user@<raspberry-pi-ip> 'systemctl list-timers hockey-update-*'

# View Pi logs
ssh user@<raspberry-pi-ip> 'journalctl -u hockey-update-baystate.service -n 50'

# Manual update on Pi
ssh user@<raspberry-pi-ip> 'cd /home/user/hockey-stats && python3 smart_updater.py --league baystate'

# Manual sync test
ssh user@<raspberry-pi-ip> 'cd /home/user/hockey-stats && bash sync_to_pc.sh'

# Check database on Mac
cd "/path/to/Hockey_Scraper" && ls -lh *.db
```

---

Generated: November 9, 2025
Ready for Complete Deployment
