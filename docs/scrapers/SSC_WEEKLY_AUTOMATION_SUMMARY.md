# SSC Hockey Weekly Automation System - Summary

## Overview

A complete automated system for weekly scraping and monitoring of SSC Hockey league data. The system handles incremental updates, deduplication, change tracking, and archiving with production-ready error handling and logging.

## Files Created

### 1. Core Scripts

#### `ssc_weekly_scraper.py` (Python)
**Purpose**: Incremental scraper with intelligent data merging

**Key Features**:
- Loads previous scrape data and metadata
- Performs full season scrape
- Merges new data with existing data
- Deduplicates games by game_id
- Detects score updates and status changes
- Generates change reports
- Backs up previous data automatically
- Maintains scrape metadata

**Usage**:
```bash
python3 ssc_weekly_scraper.py \
    --league-id 224428 \
    --subseason-id 948564 \
    --out data/weekly \
    --scrape-game-details \
    --scrape-stats \
    --scrape-standings
```

**Options**:
- `--league-id`: League instance ID (required)
- `--subseason-id`: Subseason ID (required)
- `--out`: Output directory (default: data/weekly)
- `--headed`: Run browser in visible mode (debugging)
- `--scrape-game-details`: Get period scores, goals, penalties
- `--scrape-stats`: Get player statistics
- `--scrape-standings`: Get team standings
- `--force-full`: Force full scrape instead of incremental

#### `ssc_weekly_update.sh` (Bash)
**Purpose**: Complete weekly update workflow with logging and reporting

**Key Features**:
- Runs incremental scraper
- Creates dated archive directories
- Generates summary statistics
- Compares with previous week
- Cleans up old archives (keeps last 12 weeks)
- Optional email notifications
- Comprehensive logging

**Configuration**:
```bash
LEAGUE_ID="224428"
SUBSEASON_ID="948564"
SEND_EMAIL="false"  # Set to "true" to enable
EMAIL_TO="your-email@example.com"
```

**Usage**:
```bash
./ssc_weekly_update.sh
```

**Cron Example**:
```cron
# Sundays at 2 AM
0 2 * * 0 /path/to/ssc_weekly_update.sh
```

#### `compare_ssc_data.py` (Python)
**Purpose**: Compare two scrape outputs and generate diff reports

**Key Features**:
- Identifies new games
- Detects score changes
- Tracks score additions (scheduled → final)
- Monitors player stat updates
- Tracks standings changes
- Generates JSON and console reports
- Shows sample changes

**Usage**:
```bash
python3 compare_ssc_data.py \
    --old-dir data/ssc_2025_01_08 \
    --new-dir data/ssc_2025_01_15 \
    --output comparison_report.json
```

**Options**:
- `--old-dir`: Path to old scrape directory (required)
- `--new-dir`: Path to new scrape directory (required)
- `--output`: Output file for JSON report (optional)
- `--quiet`: Suppress console output

#### `ssc_cron_setup.sh` (Bash)
**Purpose**: Helper script for managing cron jobs

**Key Features**:
- Interactive cron installation
- Custom schedule configuration
- Status checking
- Test runs
- Uninstallation
- Log rotation setup

**Usage**:
```bash
./ssc_cron_setup.sh install     # Install cron job
./ssc_cron_setup.sh uninstall   # Remove cron job
./ssc_cron_setup.sh status      # Check status
./ssc_cron_setup.sh test        # Test run
./ssc_cron_setup.sh logrotate   # Setup log rotation
```

### 2. Test Scripts

#### `test_ssc_weekly_automation.py` (Python)
**Purpose**: Automated testing of the weekly automation system

**Key Features**:
- Creates mock data for two weekly runs
- Simulates new games and score updates
- Tests deduplication logic
- Validates change detection
- Verifies merge behavior
- Generates test reports

**Usage**:
```bash
python3 test_ssc_weekly_automation.py
```

**Test Coverage**:
- New game detection
- Score update detection
- Player stat changes
- Standings updates
- Deduplication
- Data merging

### 3. Documentation

#### `WEEKLY_AUTOMATION_GUIDE.md`
Comprehensive guide covering:
- Setup instructions
- Configuration options
- Running manually
- Cron setup and management
- Monitoring and logging
- Troubleshooting
- Data management and archiving
- Best practices

#### `INCREMENTAL_SCRAPING.md`
Technical documentation covering:
- How incremental scraping works
- Data structures
- Scraping strategy
- Deduplication logic
- Update detection algorithms
- Data merging strategies
- Change tracking
- Edge cases and handling

## Directory Structure

```
Hockey_Scraper/
├── ssc_weekly_scraper.py          # Incremental scraper
├── ssc_weekly_update.sh           # Weekly update script
├── compare_ssc_data.py            # Data comparison tool
├── ssc_cron_setup.sh              # Cron management tool
├── test_ssc_weekly_automation.py  # Test script
├── WEEKLY_AUTOMATION_GUIDE.md     # User guide
├── INCREMENTAL_SCRAPING.md        # Technical docs
├── SSC_WEEKLY_AUTOMATION_SUMMARY.md  # This file
│
├── data/
│   ├── weekly/                    # Current week's data
│   │   ├── schedules.json
│   │   ├── teams.json
│   │   ├── player_stats.json
│   │   ├── standings.json
│   │   ├── change_report.json
│   │   ├── scrape_metadata.json
│   │   └── previous/              # Backup directories
│   │       ├── 20250115_140530/
│   │       └── 20250108_140215/
│   ├── ssc_2025_01_15/           # Dated archives
│   ├── ssc_2025_01_08/
│   └── ssc_2025_01_01/
│
└── logs/
    ├── ssc_weekly_2025_01_15.log
    ├── ssc_weekly_2025_01_08.log
    └── ssc_weekly_2025_01_01.log
```

## Quick Start

### 1. Install and Configure

```bash
# Make scripts executable
chmod +x ssc_weekly_update.sh
chmod +x ssc_cron_setup.sh

# Edit configuration in ssc_weekly_update.sh
nano ssc_weekly_update.sh
# Set LEAGUE_ID, SUBSEASON_ID, EMAIL settings
```

### 2. Test Manual Run

```bash
# Run a test scrape
./ssc_cron_setup.sh test

# Review output
cat data/weekly/change_report.json
tail logs/ssc_weekly_*.log
```

### 3. Install Cron Job

```bash
# Interactive installation
./ssc_cron_setup.sh install

# Choose schedule (e.g., "0 2 * * 0" for Sundays at 2 AM)
```

### 4. Monitor

```bash
# Check cron status
./ssc_cron_setup.sh status

# View latest log
tail -f logs/ssc_weekly_$(date +%Y_%m_%d).log

# Review change report
cat data/weekly/change_report.json | python3 -m json.tool
```

## How It Works

### Incremental Update Process

1. **Load Previous Data**
   - Reads `data/weekly/schedules.json`
   - Indexes games by `game_id`
   - Loads metadata from previous run

2. **Backup**
   - Copies previous data to timestamped backup
   - Keeps last 10 backups
   - Ensures recovery is possible

3. **Full Season Scrape**
   - Scrapes all dates in calendar
   - Gets game details (optional)
   - Gets player stats (optional)
   - Gets team standings (optional)

4. **Merge and Deduplicate**
   - Compares new games with previous
   - Identifies new games
   - Detects updated games (scores added, status changed)
   - Preserves unchanged games
   - Uses `game_id` as unique identifier

5. **Generate Reports**
   - Counts new games
   - Counts updated games
   - Tracks stat changes
   - Creates change_report.json

6. **Save and Archive**
   - Saves merged data to `data/weekly/`
   - Creates dated archive copy
   - Updates metadata
   - Cleans old archives (keeps last 12 weeks)

### Update Detection

A game is marked as "updated" if:
- Scores added (was scheduled, now has final score)
- Scores changed (correction)
- Game details added (period scores, goals, etc.)
- Status changed (e.g., "Scheduled" → "Final")
- Date changed (postponement)

### Deduplication Strategy

- **Primary**: Use `game_id` field
- **Fallback**: Composite key from (date, time, teams)
- **Merge Logic**: Keep newest version if updated, otherwise preserve previous

## Key Features

### Production-Ready

✓ **Error Handling**: Try-catch blocks, error logging
✓ **Logging**: Comprehensive logs with timestamps
✓ **Backups**: Automatic backup before each run
✓ **Validation**: Metadata tracking and consistency checks
✓ **Recovery**: Easy restoration from backups

### Automation

✓ **Cron Integration**: Helper scripts for setup
✓ **Scheduling**: Flexible schedule configuration
✓ **Monitoring**: Status checks and log review
✓ **Notifications**: Optional email alerts

### Data Management

✓ **Incremental Updates**: Only process changed data
✓ **Deduplication**: Prevent duplicate games
✓ **Archiving**: Dated snapshots with retention policy
✓ **Change Tracking**: Detailed diff reports

### Testing

✓ **Automated Tests**: Test suite for validation
✓ **Mock Data**: Simulated weekly runs
✓ **Verification**: Assert expected outcomes

## Usage Examples

### Example 1: Weekly Update

```bash
# Automated run via cron (Sundays at 2 AM)
0 2 * * 0 /path/to/ssc_weekly_update.sh

# Output:
# - data/weekly/schedules.json (merged data)
# - data/weekly/change_report.json (what changed)
# - data/ssc_2025_01_15/ (dated archive)
# - logs/ssc_weekly_2025_01_15.log
```

### Example 2: Manual Scrape

```bash
# Run incremental scraper manually
python3 ssc_weekly_scraper.py \
    --league-id 224428 \
    --subseason-id 948564 \
    --out data/weekly \
    --scrape-game-details \
    --scrape-stats \
    --scrape-standings

# View change report
cat data/weekly/change_report.json
```

### Example 3: Compare Two Weeks

```bash
# Compare week 1 vs week 2
python3 compare_ssc_data.py \
    --old-dir data/ssc_2025_01_08 \
    --new-dir data/ssc_2025_01_15 \
    --output comparison.json

# Output shows:
# - 5 new games
# - 12 updated games (scores added)
# - 87 player stat updates
# - 12 team standing updates
```

### Example 4: Restore from Backup

```bash
# List backups
ls -lt data/weekly/previous/

# Restore from specific backup
cp -r data/weekly/previous/20250115_140530/* data/weekly/

# Verify
cat data/weekly/scrape_metadata.json
```

### Example 5: Test Before Deploying

```bash
# Run automated test
python3 test_ssc_weekly_automation.py

# Output:
# ✓ Correct number of new games (2)
# ✓ Correct number of updated games (2)
# ✓ Correct total games (7)
# ✓ ALL TESTS PASSED!
```

## Change Report Example

```json
{
  "timestamp": "2025-01-15T14:30:45.123456",
  "summary": {
    "new_games": 5,
    "updated_games": 12,
    "total_games": 127,
    "previous_total": 120,
    "games_change": 7,
    "player_stats_count": 245,
    "standings_count": 16
  }
}
```

## Comparison Report Example

```json
{
  "games_comparison": {
    "total_old": 120,
    "total_new": 127,
    "new_games": 5,
    "updated_games": 12,
    "changes_by_type": {
      "new": [...],
      "score_added": [
        {
          "game_id": "1004",
          "description": "Score added: Team A 4 @ Team C 1"
        }
      ],
      "score_changed": [...],
      "details_added": [...],
      "status_changed": [...]
    }
  },
  "player_stats_comparison": {
    "updated_players": 87,
    "updated_players_list": [
      {
        "player": "John Doe",
        "team": "Team A",
        "changes": {
          "goals": {"old": 5, "new": 9},
          "assists": {"old": 3, "new": 5},
          "points": {"old": 8, "new": 14}
        }
      }
    ]
  },
  "standings_comparison": {
    "updated_teams": 12,
    "updated_teams_list": [...]
  }
}
```

## Common Tasks

### View Latest Results

```bash
# View games
cat data/weekly/schedules.json | python3 -m json.tool | less

# Count games by status
python3 -c "
import json
games = json.load(open('data/weekly/schedules.json'))
played = sum(1 for g in games if g['visitor_score'])
print(f'Played: {played}, Scheduled: {len(games) - played}')
"

# View change summary
cat data/weekly/change_report.json | python3 -m json.tool
```

### Monitor Scraping

```bash
# Check cron status
./ssc_cron_setup.sh status

# View recent logs
ls -lt logs/ | head -5

# Follow current log
tail -f logs/ssc_weekly_$(date +%Y_%m_%d).log

# Search for errors
grep ERROR logs/ssc_weekly_*.log
```

### Manage Archives

```bash
# List archives
ls -lth data/ssc_*

# Count games in each archive
for dir in data/ssc_*; do
    count=$(python3 -c "import json; print(len(json.load(open('$dir/schedules.json'))))")
    echo "$dir: $count games"
done

# Clean old archives (keep last 8 weeks)
cd data && ls -dt ssc_* | tail -n +9 | xargs rm -rf
```

### Database Integration

```bash
# Load into SQLite database (if you have load_to_sqlite.py)
python3 load_to_sqlite.py \
    --in-dir data/weekly \
    --db hockey.db

# Query database
sqlite3 hockey.db "SELECT COUNT(*) FROM schedules;"
```

## Troubleshooting

### Cron Not Running

```bash
# Check cron status
./ssc_cron_setup.sh status

# View crontab
crontab -l

# Check system logs
grep CRON /var/log/system.log  # macOS
grep CRON /var/log/syslog      # Linux
```

### Scraper Failing

```bash
# Check logs for errors
tail -50 logs/ssc_weekly_*.log | grep ERROR

# Run test
./ssc_cron_setup.sh test

# Check Python environment
python3 --version
pip list | grep playwright
```

### Duplicates

```bash
# Check for duplicates
python3 -c "
import json
games = json.load(open('data/weekly/schedules.json'))
ids = [g['game_id'] for g in games]
print(f'Total: {len(games)}, Unique: {len(set(ids))}')
if len(games) != len(set(ids)):
    print('WARNING: Duplicates detected!')
"
```

### Missing Updates

```bash
# Compare with previous backup
python3 compare_ssc_data.py \
    --old-dir data/weekly/previous/$(ls -t data/weekly/previous | head -1) \
    --new-dir data/weekly
```

## Best Practices

1. **Test First**: Always run `./ssc_cron_setup.sh test` before deploying
2. **Monitor Initially**: Check logs after first 2-3 automated runs
3. **Review Changes**: Examine change reports for anomalies
4. **Backup Configuration**: Keep copies of customized scripts
5. **Regular Maintenance**: Clean old archives quarterly
6. **Document Customizations**: Note any configuration changes

## Advanced Configuration

### Multiple Leagues

```bash
# Copy and customize for each league
cp ssc_weekly_update.sh ssc_weekly_league1.sh
cp ssc_weekly_update.sh ssc_weekly_league2.sh

# Edit each with different LEAGUE_ID and SUBSEASON_ID
# Install separate cron jobs
```

### Conditional Scraping

```bash
# Only scrape during season (add to ssc_weekly_update.sh)
SEASON_START="2025-01-01"
SEASON_END="2025-04-30"
if [[ "$(date +%Y-%m-%d)" < "$SEASON_START" ]]; then
    exit 0  # Skip outside season
fi
```

### Webhook Notifications

```bash
# Add to ssc_weekly_update.sh
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK"
MESSAGE="SSC scrape complete: $NEW_GAMES new, $UPDATED_GAMES updated"
curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"$MESSAGE\"}" "$WEBHOOK_URL"
```

## Dependencies

- **Python 3.7+**
- **playwright** (browser automation)
- **beautifulsoup4** (HTML parsing)
- **Bash** (shell scripts)
- **Cron** (scheduling)
- **mail** (optional, for email notifications)

## License and Credits

Part of the Hockey Scraper project. Uses the existing `ssc_hockey_scraper.py` as the base scraper.

## Support

For issues:
1. Check logs in `logs/` directory
2. Run `./ssc_cron_setup.sh test`
3. Review troubleshooting sections in documentation
4. Check `WEEKLY_AUTOMATION_GUIDE.md` and `INCREMENTAL_SCRAPING.md`

## Future Enhancements

Potential improvements:
- Database integration in weekly script
- Web dashboard for monitoring
- Slack/Discord webhook notifications
- Advanced analytics on changes
- API endpoint for accessing latest data
- Automated anomaly detection
