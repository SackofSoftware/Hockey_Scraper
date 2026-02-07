# SSC Hockey Weekly Automation - Quick Start Guide

## 5-Minute Setup

### Step 1: Make Scripts Executable

```bash
cd "/path/to/Hockey_Scraper"
chmod +x ssc_weekly_update.sh
chmod +x ssc_cron_setup.sh
```

### Step 2: Configure Your League

Edit `ssc_weekly_update.sh`:

```bash
nano ssc_weekly_update.sh
```

Change these lines:

```bash
LEAGUE_ID="224428"           # Your league ID
SUBSEASON_ID="948564"        # Your subseason ID
SEND_EMAIL="false"           # Set to "true" for email notifications
EMAIL_TO="your@email.com"    # Your email address
```

### Step 3: Test It Works

```bash
./ssc_cron_setup.sh test
```

This will:
- Run a complete scrape
- Generate all output files
- Show you what the weekly run will produce

### Step 4: Review Output

```bash
# View games
cat data/weekly/schedules.json | python3 -m json.tool | head -50

# View change report
cat data/weekly/change_report.json

# View log
tail logs/ssc_weekly_*.log
```

### Step 5: Install Cron Job

```bash
./ssc_cron_setup.sh install
```

When prompted, enter a schedule:
- **Sundays at 2 AM**: `0 2 * * 0` (recommended)
- **Mondays at 2 AM**: `0 2 * * 1`
- **Every day at 3 AM**: `0 3 * * *`

### Done!

Your scraper will now run automatically every week.

## Verify It's Running

```bash
# Check status
./ssc_cron_setup.sh status

# View cron jobs
crontab -l
```

## Monitor Results

### View Latest Data

```bash
# Games scraped
cat data/weekly/schedules.json | python3 -m json.tool | less

# Quick stats
python3 -c "
import json
games = json.load(open('data/weekly/schedules.json'))
played = sum(1 for g in games if g.get('visitor_score'))
print(f'Total: {len(games)} | Played: {played} | Scheduled: {len(games)-played}')
"
```

### Check What Changed

```bash
# View change summary
cat data/weekly/change_report.json | python3 -m json.tool

# Quick summary
python3 -c "
import json
r = json.load(open('data/weekly/change_report.json'))
s = r['summary']
print(f\"New Games: {s['new_games']}\")
print(f\"Updated Games: {s['updated_games']}\")
print(f\"Total Games: {s['total_games']}\")
"
```

### Review Logs

```bash
# Latest log
ls -t logs/ssc_weekly_*.log | head -1 | xargs tail -50

# Follow current log
tail -f logs/ssc_weekly_$(date +%Y_%m_%d).log

# Find errors
grep ERROR logs/ssc_weekly_*.log
```

## Common Commands

### Manual Run

```bash
# Run weekly update manually
./ssc_weekly_update.sh

# Run just the scraper
python3 ssc_weekly_scraper.py \
    --league-id 224428 \
    --subseason-id 948564 \
    --out data/weekly \
    --scrape-game-details \
    --scrape-stats \
    --scrape-standings
```

### Compare Two Weeks

```bash
# Compare this week vs last week
python3 compare_ssc_data.py \
    --old-dir data/ssc_2025_01_08 \
    --new-dir data/ssc_2025_01_15
```

### Manage Cron Job

```bash
./ssc_cron_setup.sh status      # Check status
./ssc_cron_setup.sh uninstall   # Remove cron job
./ssc_cron_setup.sh install     # Reinstall with new schedule
```

### Archive Management

```bash
# List archives
ls -lth data/ssc_*

# Count games in each archive
for dir in data/ssc_*; do
    count=$(python3 -c "import json; print(len(json.load(open('$dir/schedules.json'))))" 2>/dev/null || echo "0")
    echo "$dir: $count games"
done

# Clean old archives (keep last 8 weeks)
cd data && ls -dt ssc_* | tail -n +9 | xargs rm -rf
```

## Troubleshooting

### Cron Not Running

```bash
# Check if cron is installed
./ssc_cron_setup.sh status

# View system logs
grep CRON /var/log/system.log  # macOS
```

### Scraper Failing

```bash
# Check logs
tail -50 logs/ssc_weekly_*.log | grep ERROR

# Test manually
./ssc_cron_setup.sh test

# Check Python packages
pip list | grep playwright
playwright install
```

### No New Data

```bash
# Check change report
cat data/weekly/change_report.json

# Verify source website is up
open https://www.ssc-hockey.org/schedule/day/league_instance/224428?subseason=948564
```

## File Locations

```
data/
├── weekly/                      # Current data
│   ├── schedules.json          # All games
│   ├── change_report.json      # What changed
│   ├── scrape_metadata.json    # Metadata
│   └── previous/               # Backups
├── ssc_2025_01_15/             # Weekly archives
└── ssc_2025_01_08/

logs/
├── ssc_weekly_2025_01_15.log   # Weekly logs
└── ssc_weekly_2025_01_08.log
```

## What Gets Scraped

By default, the weekly update scrapes:
- ✓ All games (full season schedule)
- ✓ Game details (period scores, goals, penalties, shots)
- ✓ Player statistics
- ✓ Team standings

## Data Updates

The system automatically:
- ✓ Adds new games as they're scheduled
- ✓ Updates games when scores are added
- ✓ Detects status changes (postponements, etc.)
- ✓ Updates player stats and standings
- ✓ Removes duplicates
- ✓ Backs up previous data
- ✓ Archives weekly snapshots

## Email Notifications

To enable email alerts:

1. Edit `ssc_weekly_update.sh`:
   ```bash
   SEND_EMAIL="true"
   EMAIL_TO="your-email@example.com"
   ```

2. Test email:
   ```bash
   echo "Test" | mail -s "Test" your@email.com
   ```

3. Run weekly update to test

## Further Reading

- **WEEKLY_AUTOMATION_GUIDE.md** - Complete setup guide
- **INCREMENTAL_SCRAPING.md** - Technical details
- **SSC_WEEKLY_AUTOMATION_SUMMARY.md** - Full feature list

## Support

If something doesn't work:

1. Check logs: `tail logs/ssc_weekly_*.log`
2. Run test: `./ssc_cron_setup.sh test`
3. Review docs: `WEEKLY_AUTOMATION_GUIDE.md`
4. Verify config: Check `ssc_weekly_update.sh` settings

## Next Steps

After setup:

1. ✓ Let it run for a week
2. ✓ Check logs next week
3. ✓ Review change report
4. ✓ Verify data looks correct
5. ✓ Set up email notifications (optional)
6. ✓ Integrate with database (optional)

Enjoy automated hockey data scraping! 🏒
