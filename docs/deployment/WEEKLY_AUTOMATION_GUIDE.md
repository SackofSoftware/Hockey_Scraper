# SSC Hockey Weekly Automation Guide

This guide covers the setup and use of the automated weekly scraping system for SSC Hockey data.

## Table of Contents

- [Overview](#overview)
- [Components](#components)
- [Setup Instructions](#setup-instructions)
- [Configuration](#configuration)
- [Running Manually](#running-manually)
- [Cron Setup](#cron-setup)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Data Management](#data-management)

## Overview

The weekly automation system provides:

- **Incremental Updates**: Only processes new or changed data
- **Deduplication**: Prevents duplicate games using game IDs
- **Update Detection**: Identifies games with new scores or details
- **Change Reporting**: Generates detailed diff reports
- **Automatic Archiving**: Keeps dated snapshots of all data
- **Email Notifications**: Optional alerts for scrape completion (configurable)

## Components

### 1. `ssc_weekly_scraper.py`

Python script that handles incremental scraping and data merging.

**Features:**
- Loads previous scrape data
- Merges new games with existing ones
- Detects score updates and status changes
- Generates change reports
- Backs up previous data
- Maintains scrape metadata

### 2. `ssc_weekly_update.sh`

Bash script for complete weekly update workflow.

**Features:**
- Runs the incremental scraper
- Creates dated archive directories
- Generates summary reports
- Compares with previous week
- Cleans up old archives
- Optional email notifications

### 3. `compare_ssc_data.py`

Comparison tool for analyzing differences between scrapes.

**Features:**
- Identifies new games
- Detects score changes
- Tracks player stat updates
- Monitors standings changes
- Generates JSON and console reports

### 4. `ssc_cron_setup.sh`

Helper script for managing cron jobs.

**Features:**
- Interactive cron installation
- Schedule configuration
- Status checking
- Test runs
- Log rotation setup

## Setup Instructions

### Prerequisites

1. **Python 3.7+** with required packages:
   ```bash
   pip install playwright beautifulsoup4
   playwright install
   ```

2. **Bash shell** (macOS/Linux or WSL on Windows)

3. **Cron daemon** running (usually pre-installed on macOS/Linux)

### Step 1: Verify Scripts

Ensure all scripts are executable:

```bash
chmod +x ssc_weekly_update.sh
chmod +x ssc_cron_setup.sh
```

### Step 2: Test Manual Run

Run a test scrape to verify everything works:

```bash
./ssc_cron_setup.sh test
```

This will:
- Run the weekly scraper manually
- Generate all output files
- Show you what the automated run will produce

### Step 3: Review Configuration

Edit `ssc_weekly_update.sh` to configure:

```bash
# Configuration section
LEAGUE_ID="224428"           # Your league ID
SUBSEASON_ID="948564"        # Your subseason ID
SEND_EMAIL="false"           # Set to "true" for email notifications
EMAIL_TO="your@email.com"    # Your email address
```

### Step 4: Install Cron Job

Use the setup script for interactive installation:

```bash
./ssc_cron_setup.sh install
```

You'll be prompted to enter a schedule. Common options:

- **Sundays at 2 AM**: `0 2 * * 0` (default)
- **Mondays at 2 AM**: `0 2 * * 1`
- **Saturdays at 2 PM**: `0 14 * * 6`
- **Every day at 3 AM**: `0 3 * * *`

## Configuration

### Scraper Options

Edit `ssc_weekly_scraper.py` to customize scraping behavior:

```python
scraper = SSCHockeyScraper(
    league_id=args.league_id,
    subseason_id=args.subseason_id,
    all_dates=True,              # Scrape all dates
    scrape_game_details=True,    # Get period scores, goals, etc.
    scrape_stats=True,            # Get player statistics
    scrape_standings=True         # Get team standings
)
```

### Output Directories

Default directory structure:

```
data/
├── weekly/                      # Current week's data
│   ├── schedules.json
│   ├── teams.json
│   ├── player_stats.json
│   ├── standings.json
│   ├── change_report.json
│   ├── scrape_metadata.json
│   └── previous/                # Backup directories
│       ├── 20250115_140530/
│       └── 20250108_140215/
├── ssc_2025_01_15/             # Archived snapshots
├── ssc_2025_01_08/
└── ssc_2025_01_01/

logs/
├── ssc_weekly_2025_01_15.log
├── ssc_weekly_2025_01_08.log
└── ssc_weekly_2025_01_01.log
```

### Email Configuration

To enable email notifications:

1. Install mail client:
   ```bash
   # macOS (usually pre-installed)
   which mail

   # Linux
   sudo apt-get install mailutils
   ```

2. Configure `ssc_weekly_update.sh`:
   ```bash
   SEND_EMAIL="true"
   EMAIL_TO="your-email@example.com"
   EMAIL_SUBJECT="SSC Hockey Weekly Report"
   ```

## Running Manually

### Run Weekly Update

```bash
./ssc_weekly_update.sh
```

### Run Incremental Scraper Only

```bash
python3 ssc_weekly_scraper.py \
    --league-id 224428 \
    --subseason-id 948564 \
    --out data/weekly \
    --scrape-game-details \
    --scrape-stats \
    --scrape-standings
```

### Compare Two Scrapes

```bash
python3 compare_ssc_data.py \
    --old-dir data/ssc_2025_01_08 \
    --new-dir data/ssc_2025_01_15 \
    --output comparison_report.json
```

## Cron Setup

### Check Status

```bash
./ssc_cron_setup.sh status
```

### Modify Schedule

```bash
# Uninstall current cron job
./ssc_cron_setup.sh uninstall

# Reinstall with new schedule
./ssc_cron_setup.sh install
```

### View Cron Jobs

```bash
crontab -l
```

### Manual Cron Entry

If you prefer to manually edit crontab:

```bash
crontab -e
```

Add this line (adjust path and schedule):

```cron
# SSC Hockey Weekly Scraper
0 2 * * 0 /path/to/Hockey_Scraper/ssc_weekly_update.sh
```

## Monitoring

### Check Logs

View the latest log:

```bash
# Find latest log
ls -lt logs/ssc_weekly_*.log | head -1

# View latest log
tail -f logs/ssc_weekly_$(date +%Y_%m_%d).log

# View specific log
tail -f logs/ssc_weekly_2025_01_15.log
```

### Review Change Reports

```bash
# View latest change report
cat data/weekly/change_report.json | python3 -m json.tool

# Quick summary
python3 -c "
import json
with open('data/weekly/change_report.json') as f:
    r = json.load(f)
    s = r['summary']
    print(f'New Games: {s[\"new_games\"]}')
    print(f'Updated Games: {s[\"updated_games\"]}')
    print(f'Total Games: {s[\"total_games\"]}')
"
```

### Check Scrape Metadata

```bash
cat data/weekly/scrape_metadata.json | python3 -m json.tool
```

## Troubleshooting

### Cron Job Not Running

1. **Check cron is running:**
   ```bash
   # macOS
   sudo launchctl list | grep cron

   # Linux
   systemctl status cron
   ```

2. **Check cron logs:**
   ```bash
   # macOS
   grep CRON /var/log/system.log

   # Linux
   grep CRON /var/log/syslog
   ```

3. **Verify script paths are absolute:**
   ```bash
   ./ssc_cron_setup.sh status
   ```

### Scraper Failing

1. **Check logs:**
   ```bash
   tail -50 logs/ssc_weekly_*.log | grep ERROR
   ```

2. **Run manual test:**
   ```bash
   ./ssc_cron_setup.sh test
   ```

3. **Check Python environment:**
   ```bash
   python3 --version
   pip list | grep playwright
   ```

4. **Verify browser installation:**
   ```bash
   playwright install
   ```

### Email Not Sending

1. **Test mail command:**
   ```bash
   echo "Test" | mail -s "Test" your@email.com
   ```

2. **Check mail logs:**
   ```bash
   tail -f /var/log/mail.log
   ```

3. **Alternative: Use Python for email:**
   Modify script to use Python's `smtplib` instead of `mail` command.

### Disk Space Issues

```bash
# Check disk usage
df -h

# Find large log files
du -sh logs/* | sort -h

# Clean old archives manually
rm -rf data/ssc_2024_*
```

## Data Management

### Archiving

The system automatically:
- Creates dated archives (e.g., `data/ssc_2025_01_15/`)
- Keeps last 12 weeks by default
- Maintains backup of previous runs in `data/weekly/previous/`

### Manual Archive Cleanup

```bash
# Keep only last 8 weeks
cd data
ls -dt ssc_* | tail -n +9 | xargs rm -rf

# Archive to external storage
tar -czf ssc_archives_2025_q1.tar.gz ssc_2025_01_* ssc_2025_02_* ssc_2025_03_*
```

### Backup Previous Runs

Backups are stored in `data/weekly/previous/` with timestamps:

```bash
# List backups
ls -lt data/weekly/previous/

# Restore from backup
cp -r data/weekly/previous/20250115_140530/* data/weekly/
```

### Log Rotation

Set up automatic log rotation:

```bash
sudo ./ssc_cron_setup.sh logrotate
```

Or manually compress old logs:

```bash
# Compress logs older than 30 days
find logs/ -name "ssc_weekly_*.log" -mtime +30 -exec gzip {} \;
```

### Database Integration

To load data into SQLite database:

```bash
# Use existing database loader
python3 load_to_sqlite.py \
    --in-dir data/weekly \
    --db hockey.db
```

Or create a weekly database update:

```bash
# Add to ssc_weekly_update.sh
python3 load_to_sqlite.py --in-dir "$OUTPUT_DIR" --db hockey_stats.db
```

## Advanced Usage

### Custom Schedule for Multiple Leagues

Run different leagues on different schedules:

```bash
# Edit ssc_weekly_update.sh for each league
cp ssc_weekly_update.sh ssc_weekly_update_league1.sh
cp ssc_weekly_update.sh ssc_weekly_update_league2.sh

# Configure each with different LEAGUE_ID and SUBSEASON_ID
# Install separate cron jobs
0 2 * * 0 /path/to/ssc_weekly_update_league1.sh
0 3 * * 0 /path/to/ssc_weekly_update_league2.sh
```

### Conditional Scraping

Only scrape during the season:

```bash
# Add to ssc_weekly_update.sh
SEASON_START="2025-01-01"
SEASON_END="2025-04-30"
CURRENT_DATE=$(date +%Y-%m-%d)

if [[ "$CURRENT_DATE" < "$SEASON_START" ]] || [[ "$CURRENT_DATE" > "$SEASON_END" ]]; then
    log "Outside season dates, skipping scrape"
    exit 0
fi
```

### Webhook Notifications

Send notifications to Slack/Discord:

```bash
# Add to ssc_weekly_update.sh after scrape completes
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
MESSAGE="SSC Hockey scrape complete: $NEW_GAMES new games, $UPDATED_GAMES updated"

curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"$MESSAGE\"}" \
    "$WEBHOOK_URL"
```

## Best Practices

1. **Test before deploying**: Always run `./ssc_cron_setup.sh test` before installing cron job
2. **Monitor first few runs**: Check logs after the first 2-3 automated runs
3. **Set up alerts**: Configure email or webhook notifications
4. **Regular maintenance**: Review and clean old archives quarterly
5. **Backup configuration**: Keep copies of customized scripts
6. **Document changes**: Note any configuration changes in logs

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Run manual test: `./ssc_cron_setup.sh test`
3. Review this guide's troubleshooting section
4. Check the INCREMENTAL_SCRAPING.md for data merging details
