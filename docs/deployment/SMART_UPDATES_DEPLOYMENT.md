# Smart Hockey Stats Update System - Deployment Guide

## Overview

The Smart Update System automatically updates hockey stats databases based on current time and game schedules:

- **Game Days** (Fri PM, Sat, Sun): Updates every 15 minutes
- **Weekday Evenings** (6-9 PM): Updates every 30 minutes
- **Off Times**: Updates every 4 hours
- **Smart Detection**: Only fetches box scores for completed games
- **Status Tracking**: Differentiates scheduled vs completed games

## Files Created

1. **`smart_updater.py`** - Main update script with time-aware logic
2. **`pi/systemd/hockey-update-*.service`** - Systemd service files
3. **`pi/systemd/hockey-update-*.timer`** - Systemd timer schedules

## Quick Test

Test the smart updater on your current system:

```bash
# Check current schedule status (no updates)
cd "/path/to/Hockey_Scraper"
python smart_updater.py --league baystate --check-schedule

# Perform a test update
python smart_updater.py --league baystate
```

## Deployment to Raspberry Pi

### Option 1: Systemd Timers (Recommended)

**1. Copy files to Pi:**
```bash
scp smart_updater.py pi@<raspberry-pi-ip>:~/hockey-stats/
scp advanced_stats_database.py pi@<raspberry-pi-ip>:~/hockey-stats/
scp data_importer.py pi@<raspberry-pi-ip>:~/hockey-stats/
scp pi/systemd/hockey-update-*.* pi@<raspberry-pi-ip>:~/
```

**2. Install systemd services:**
```bash
ssh pi@<raspberry-pi-ip>

# Copy service and timer files
sudo cp hockey-update-baystate.service /etc/systemd/system/
sudo cp hockey-update-baystate.timer /etc/systemd/system/

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable hockey-update-baystate.timer
sudo systemctl start hockey-update-baystate.timer

# Check status
sudo systemctl status hockey-update-baystate.timer
sudo systemctl list-timers hockey-update-baystate.timer
```

**3. View logs:**
```bash
# Watch live updates
journalctl -u hockey-update-baystate.service -f

# View recent updates
journalctl -u hockey-update-baystate.service -n 100

# Check specific date
journalctl -u hockey-update-baystate.service --since "2025-11-09"
```

### Option 2: Simple Cron (Alternative)

**Create cron schedule:**
```bash
ssh pi@<raspberry-pi-ip>
crontab -e
```

**Add these lines:**
```cron
# Bay State Hockey League - Smart Updates

# Friday evenings - every 15 minutes from 5 PM to 11 PM
*/15 17-23 * * 5 cd /home/pi/hockey-stats && python3 smart_updater.py --league baystate >> /var/log/hockey-baystate.log 2>&1

# Saturday - every 15 minutes from 8 AM to 11 PM
*/15 8-23 * * 6 cd /home/pi/hockey-stats && python3 smart_updater.py --league baystate >> /var/log/hockey-baystate.log 2>&1

# Sunday - every 15 minutes from 8 AM to 11 PM
*/15 8-23 * * 0 cd /home/pi/hockey-stats && python3 smart_updater.py --league baystate >> /var/log/hockey-baystate.log 2>&1

# Weekday evenings - every 30 minutes from 6-9 PM
*/30 18-21 * * 1-4 cd /home/pi/hockey-stats && python3 smart_updater.py --league baystate >> /var/log/hockey-baystate.log 2>&1

# Off times - every 4 hours
0 */4 * * * cd /home/pi/hockey-stats && python3 smart_updater.py --league baystate >> /var/log/hockey-baystate.log 2>&1
```

## How It Works

### Time-Aware Detection

The system checks current date/time and determines if it's a "game day":

```python
# Friday evening (after 5 PM)
if day_of_week == 4 and current_time >= time(17, 0):
    return True, "Friday evening (games start after 5 PM)"

# All day Saturday
if day_of_week == 5:
    return True, "Saturday (full day of games)"

# All day Sunday
if day_of_week == 6:
    return True, "Sunday (full day of games)"

# Weekday evening (occasional weekday games, 6-9 PM)
if day_of_week in [0, 1, 2, 3] and time(18, 0) <= current_time <= time(21, 0):
    return True, "Weekday evening"
```

### Update Logic

1. **Always**: Update schedule (lightweight, just checks game status changes)
2. **Smart**: Only fetch box scores for games marked as "complete"
3. **Efficient**: Skips games that already have box score data
4. **Incremental**: Only processes new/updated games

### Game Status Tracking

Games have status field that changes over time:

- **`scheduled`** - Game is on the schedule, not yet played
- **`pending`** - Game time has passed, waiting for results
- **`complete`** - Game finished, results available
- **`cancelled`** - Game was cancelled

The updater only fetches detailed stats (goals, assists, penalties) for `complete` games.

## Monitoring

### Check Update Status

```bash
# Check current schedule
python smart_updater.py --league baystate --check-schedule

# Output example:
# Current time: Saturday, November 09, 2025 at 02:30 PM
# Game day: True - Saturday (full day of games)
# Recommended update interval: 15 minutes
# Schedule status:
#   Total games: 1371
#   Completed: 675
#   Scheduled: 696
#   Today: 12
#   Tomorrow: 8
```

### Check Systemd Timer

```bash
# See when next update will run
systemctl list-timers hockey-update-baystate.timer

# See timer calendar schedule
systemctl cat hockey-update-baystate.timer
```

### Database Status

```bash
# Check database for recent updates
sqlite3 advanced_hockey_stats_full.db "
SELECT
    COUNT(*) as total_games,
    SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) as completed,
    COUNT(DISTINCT game_id) as unique_games
FROM games;
"

# Check recent goals
sqlite3 advanced_hockey_stats_full.db "
SELECT COUNT(*), MAX(game_id) as latest_game
FROM goals;
"
```

## Multiple Leagues

To update multiple leagues, create separate timers:

```bash
# Bay State
sudo systemctl enable hockey-update-baystate.timer
sudo systemctl start hockey-update-baystate.timer

# Eastern Hockey Federation (when ready)
sudo systemctl enable hockey-update-ehf.timer
sudo systemctl start hockey-update-ehf.timer
```

## Troubleshooting

### Timer not running

```bash
# Check timer status
sudo systemctl status hockey-update-baystate.timer

# Check service logs
journalctl -u hockey-update-baystate.service --since today

# Manually trigger update
sudo systemctl start hockey-update-baystate.service
```

### Database locked errors

If you see "database is locked" errors:

```bash
# Stop competing processes
sudo systemctl stop hockey-api-baystate.service
sudo systemctl stop hockey-update-baystate.timer

# Run manual update
python smart_updater.py --league baystate

# Restart services
sudo systemctl start hockey-api-baystate.service
sudo systemctl start hockey-update-baystate.timer
```

### Check what's scheduled

```bash
# View all active timers
systemctl list-timers

# Test timer schedule (dry run)
systemd-analyze calendar "Fri 17:00,17:15,17:30,17:45"
```

## Benefits

✅ **Time-Aware**: Updates more frequently during game times
✅ **Efficient**: Only fetches data when games are actually played
✅ **Automatic**: No manual intervention needed
✅ **Smart**: Differentiates scheduled vs completed games
✅ **Reliable**: Systemd restarts on failure
✅ **Logged**: All updates tracked in systemd journal

## Next Steps

1. Deploy Bay State updater to Pi
2. Monitor for one weekend to verify game day updates
3. Add EHF league when database is ready
4. Configure API server to use updated databases
