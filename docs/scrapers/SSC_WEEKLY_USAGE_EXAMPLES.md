# SSC Hockey Weekly Automation - Usage Examples

This document provides real-world usage examples for the weekly automation system.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Initial Setup](#initial-setup)
- [Weekly Operations](#weekly-operations)
- [Data Analysis](#data-analysis)
- [Troubleshooting Examples](#troubleshooting-examples)
- [Advanced Scenarios](#advanced-scenarios)

## Basic Usage

### Example 1: First Time Setup

```bash
# Navigate to project directory
cd "/path/to/Hockey_Scraper"

# Make scripts executable
chmod +x ssc_weekly_update.sh ssc_cron_setup.sh

# Configure your league (edit the file)
nano ssc_weekly_update.sh
# Change LEAGUE_ID and SUBSEASON_ID to your values

# Run a test scrape
./ssc_cron_setup.sh test

# Check the output
ls -l data/weekly/
cat data/weekly/change_report.json
```

**Expected Output**:
```
data/weekly/
├── schedules.json          (120+ games)
├── teams.json             (16 teams)
├── player_stats.json      (200+ players)
├── standings.json         (16 teams)
├── change_report.json     (summary)
└── scrape_metadata.json   (metadata)
```

### Example 2: Install Automated Weekly Scraping

```bash
# Install cron job interactively
./ssc_cron_setup.sh install

# When prompted, enter schedule:
# For Sundays at 2 AM: 0 2 * * 0

# Verify installation
./ssc_cron_setup.sh status
```

**Expected Output**:
```
[INFO] ✓ Cron job is INSTALLED

Current cron entry:
0 2 * * 0 /path/to/ssc_weekly_update.sh # SSC Hockey Weekly Scraper

Schedule: 0 2 * * 0
```

## Initial Setup

### Example 3: Configure for Multiple Leagues

```bash
# Copy script for each league
cp ssc_weekly_update.sh ssc_weekly_northshore.sh
cp ssc_weekly_update.sh ssc_weekly_southshore.sh

# Edit each script with different IDs
nano ssc_weekly_northshore.sh
# LEAGUE_ID="224428"
# SUBSEASON_ID="948564"
# OUTPUT_DIR="${SCRIPT_DIR}/data/northshore_${DATE_SUFFIX}"

nano ssc_weekly_southshore.sh
# LEAGUE_ID="224429"
# SUBSEASON_ID="948565"
# OUTPUT_DIR="${SCRIPT_DIR}/data/southshore_${DATE_SUFFIX}"

# Install separate cron jobs
crontab -e
# Add:
# 0 2 * * 0 /path/to/ssc_weekly_northshore.sh
# 0 3 * * 0 /path/to/ssc_weekly_southshore.sh
```

### Example 4: Enable Email Notifications

```bash
# Test email first
echo "Test message" | mail -s "Test Subject" your@email.com

# Edit weekly update script
nano ssc_weekly_update.sh

# Change:
SEND_EMAIL="true"
EMAIL_TO="your@email.com"

# Test it
./ssc_weekly_update.sh
```

**Expected Email**:
```
Subject: SSC Hockey Weekly Scrape Report - 2025_01_15

SSC Hockey Weekly Scrape Report
Date: 2025_01_15

Summary:
{
  "timestamp": "2025-01-15T14:30:00",
  "summary": {
    "new_games": 5,
    "updated_games": 12,
    "total_games": 127
  }
}

Log file: /path/to/logs/ssc_weekly_2025_01_15.log
Data directory: /path/to/data/ssc_2025_01_15
```

## Weekly Operations

### Example 5: Review This Week's Scrape

```bash
# Find latest log
LATEST_LOG=$(ls -t logs/ssc_weekly_*.log | head -1)

# View summary
tail -50 "$LATEST_LOG"

# Check for errors
grep ERROR "$LATEST_LOG"

# View change report
cat data/weekly/change_report.json | python3 -m json.tool
```

**Expected Output**:
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

### Example 6: Analyze What Changed

```bash
# Quick summary
python3 -c "
import json
r = json.load(open('data/weekly/change_report.json'))
s = r['summary']
print('='*50)
print('WEEKLY SCRAPE SUMMARY')
print('='*50)
print(f'New Games:     {s[\"new_games\"]}')
print(f'Updated Games: {s[\"updated_games\"]}')
print(f'Total Games:   {s[\"total_games\"]} (was {s[\"previous_total\"]})')
print(f'Player Stats:  {s[\"player_stats_count\"]}')
print(f'Standings:     {s[\"standings_count\"]}')
print('='*50)
"
```

**Expected Output**:
```
==================================================
WEEKLY SCRAPE SUMMARY
==================================================
New Games:     5
Updated Games: 12
Total Games:   127 (was 120)
Player Stats:  245
Standings:     16
==================================================
```

### Example 7: Compare This Week vs Last Week

```bash
# Find the two most recent archives
CURRENT=$(ls -dt data/ssc_* | head -1)
PREVIOUS=$(ls -dt data/ssc_* | head -2 | tail -1)

# Compare them
python3 compare_ssc_data.py \
    --old-dir "$PREVIOUS" \
    --new-dir "$CURRENT" \
    --output comparison_$(date +%Y%m%d).json

# View results
cat comparison_$(date +%Y%m%d).json | python3 -m json.tool | less
```

**Expected Output**:
```
======================================================================
SSC DATA COMPARISON REPORT
======================================================================
Old Data: data/ssc_2025_01_08
New Data: data/ssc_2025_01_15
Timestamp: 2025-01-15T14:30:45.123456

GAMES:
  - Old Total: 120
  - New Total: 127
  - New Games: 5
  - Updated Games: 12

  Change Types:
    - new: 5
    - score_added: 8
    - details_added: 4

PLAYER STATISTICS:
  - Old Total: 240
  - New Total: 245
  - New Players: 5
  - Updated Players: 87

STANDINGS:
  - Old Total: 16
  - New Total: 16
  - Updated Teams: 12
```

## Data Analysis

### Example 8: Count Games by Status

```bash
python3 << 'EOF'
import json
from pathlib import Path

games = json.load(open('data/weekly/schedules.json'))

# Count by status
played = sum(1 for g in games if g.get('visitor_score') is not None)
scheduled = len(games) - played

# Count by division
divisions = {}
for g in games:
    div = g.get('division', 'Unknown')
    divisions[div] = divisions.get(div, 0) + 1

print(f"Total Games: {len(games)}")
print(f"  Played: {played}")
print(f"  Scheduled: {scheduled}")
print()
print("By Division:")
for div, count in sorted(divisions.items()):
    print(f"  {div}: {count}")
EOF
```

**Expected Output**:
```
Total Games: 127
  Played: 89
  Scheduled: 38

By Division:
  8A: 32
  8B: 31
  10A: 30
  10B: 34
```

### Example 9: Find Games with Score Changes

```bash
python3 << 'EOF'
import json

# Load comparison report
report = json.load(open('data/weekly/change_report.json'))

# Look at previous comparison
comparison = json.load(open('comparison_report.json'))

# Find score changes
changes = comparison.get('games_comparison', {}).get('changes_by_type', {})

if 'score_changed' in changes:
    print("SCORE CORRECTIONS:")
    for change in changes['score_changed']:
        print(f"  Game {change['game_id']}: {change['description']}")
else:
    print("No score corrections this week")

if 'score_added' in changes:
    print()
    print(f"SCORES ADDED: {len(changes['score_added'])} games")
    for change in changes['score_added'][:5]:  # First 5
        print(f"  {change['description']}")
EOF
```

**Expected Output**:
```
No score corrections this week

SCORES ADDED: 8 games
  Score added: Team A 4 @ Team C 1
  Score added: Team B 2 @ Team D 3
  Score added: Team E 3 @ Team F 2
  Score added: Team A 5 @ Team B 1
  Score added: Team C 2 @ Team E 2
```

### Example 10: Top Scorers Report

```bash
python3 << 'EOF'
import json

stats = json.load(open('data/weekly/player_stats.json'))

# Sort by points
top_scorers = sorted(stats, key=lambda x: x.get('points', 0), reverse=True)[:10]

print("TOP 10 SCORERS")
print("="*70)
print(f"{'Rank':<6} {'Player':<25} {'Team':<20} {'G':<4} {'A':<4} {'Pts':<4}")
print("="*70)

for i, player in enumerate(top_scorers, 1):
    print(f"{i:<6} {player['name']:<25} {player['team']:<20} "
          f"{player.get('goals', 0):<4} {player.get('assists', 0):<4} "
          f"{player.get('points', 0):<4}")
EOF
```

**Expected Output**:
```
TOP 10 SCORERS
======================================================================
Rank   Player                    Team                 G    A    Pts
======================================================================
1      John Doe                  8A - Team Alpha      15   12   27
2      Jane Smith                8B - Team Beta       13   14   27
3      Bob Johnson               10A - Team Gamma     12   10   22
4      Alice Williams            8A - Team Delta      11   10   21
5      Charlie Brown             10B - Team Epsilon   10   11   21
...
```

### Example 11: Standings Report

```bash
python3 << 'EOF'
import json

standings = json.load(open('data/weekly/standings.json'))

# Group by division
divisions = {}
for team in standings:
    div = team.get('division', 'Unknown')
    if div not in divisions:
        divisions[div] = []
    divisions[div].append(team)

# Sort each division by points
for div in divisions:
    divisions[div].sort(key=lambda x: x.get('points', 0), reverse=True)

# Print
for div, teams in sorted(divisions.items()):
    print(f"\n{div} Division Standings")
    print("="*80)
    print(f"{'Rank':<6} {'Team':<30} {'GP':<4} {'W':<4} {'L':<4} {'T':<4} {'Pts':<4}")
    print("-"*80)

    for i, team in enumerate(teams, 1):
        print(f"{i:<6} {team['team_name']:<30} "
              f"{team.get('games_played', 0):<4} "
              f"{team.get('wins', 0):<4} "
              f"{team.get('losses', 0):<4} "
              f"{team.get('ties', 0):<4} "
              f"{team.get('points', 0):<4}")
EOF
```

**Expected Output**:
```
8A Division Standings
================================================================================
Rank   Team                           GP   W    L    T    Pts
--------------------------------------------------------------------------------
1      8A - Team Alpha                12   10   1    1    21
2      8A - Team Beta                 12   9    2    1    19
3      8A - Team Gamma                12   7    4    1    15
...
```

## Troubleshooting Examples

### Example 12: Check for Duplicates

```bash
python3 << 'EOF'
import json
from collections import Counter

games = json.load(open('data/weekly/schedules.json'))

# Check game IDs
game_ids = [g.get('game_id') for g in games if g.get('game_id')]
duplicates = [id for id, count in Counter(game_ids).items() if count > 1]

if duplicates:
    print(f"WARNING: Found {len(duplicates)} duplicate game IDs:")
    for dup_id in duplicates[:5]:
        dup_games = [g for g in games if g.get('game_id') == dup_id]
        print(f"\nGame ID {dup_id} appears {len(dup_games)} times:")
        for g in dup_games:
            print(f"  {g['date']} - {g['visitor_team']} @ {g['home_team']}")
else:
    print(f"✓ No duplicates found. Total unique games: {len(game_ids)}")
EOF
```

### Example 13: Verify Cron is Working

```bash
# Check if cron job exists
crontab -l | grep "SSC Hockey"

# Check recent runs
ls -lt logs/ssc_weekly_*.log | head -5

# Check if scraper ran today
TODAY=$(date +%Y_%m_%d)
if [ -f "logs/ssc_weekly_${TODAY}.log" ]; then
    echo "✓ Scraper ran today"
    tail -20 "logs/ssc_weekly_${TODAY}.log"
else
    echo "✗ No log for today"
fi

# Check system cron logs
grep CRON /var/log/system.log | tail -20  # macOS
```

### Example 14: Restore from Backup

```bash
# List available backups
echo "Available backups:"
ls -lt data/weekly/previous/

# Choose a backup to restore
BACKUP_DIR="data/weekly/previous/20250115_140530"

# Restore it
echo "Restoring from $BACKUP_DIR..."
cp -r "$BACKUP_DIR"/* data/weekly/

# Verify
cat data/weekly/scrape_metadata.json | python3 -m json.tool | head -10
```

### Example 15: Debug Scraper Issues

```bash
# Run scraper in headed mode (visible browser)
python3 ssc_weekly_scraper.py \
    --league-id 224428 \
    --subseason-id 948564 \
    --out data/test \
    --headed \
    --scrape-game-details 2>&1 | tee debug.log

# Check for specific errors
grep -i "error\|exception\|failed" debug.log

# Verify output
ls -lh data/test/
cat data/test/scrape_metadata.json
```

## Advanced Scenarios

### Example 16: Create Monthly Summary

```bash
python3 << 'EOF'
import json
from datetime import datetime
from pathlib import Path

# Find all archives from this month
current_month = datetime.now().strftime('%Y_%m')
archives = sorted(Path('data').glob(f'ssc_{current_month}_*'))

print(f"MONTHLY SUMMARY - {datetime.now().strftime('%B %Y')}")
print("="*70)

for archive in archives:
    metadata_file = archive / 'scrape_metadata.json'
    if metadata_file.exists():
        metadata = json.load(open(metadata_file))
        print(f"\n{archive.name}:")
        print(f"  Total Games: {metadata.get('total_games', 0)}")
        print(f"  New Games: {metadata.get('new_games', 0)}")
        print(f"  Updated Games: {metadata.get('updated_games', 0)}")
        print(f"  Timestamp: {metadata.get('timestamp', 'N/A')}")
EOF
```

### Example 17: Export to CSV

```bash
python3 << 'EOF'
import json
import csv

# Load games
games = json.load(open('data/weekly/schedules.json'))

# Write to CSV
with open('games_export.csv', 'w', newline='') as f:
    writer = csv.writer(f)

    # Header
    writer.writerow(['Date', 'Time', 'Visitor', 'Home', 'V Score', 'H Score',
                     'Location', 'Status', 'Division'])

    # Data
    for game in sorted(games, key=lambda x: x.get('date', '')):
        writer.writerow([
            game.get('date', ''),
            game.get('time', ''),
            game.get('visitor_team', ''),
            game.get('home_team', ''),
            game.get('visitor_score', ''),
            game.get('home_score', ''),
            game.get('location', ''),
            game.get('status', ''),
            game.get('division', '')
        ])

print("Exported to games_export.csv")
EOF

# View in spreadsheet
open games_export.csv  # macOS
```

### Example 18: Slack Webhook Notification

```bash
# Add to ssc_weekly_update.sh after scrape completes

# Read change report
NEW_GAMES=$(python3 -c "import json; print(json.load(open('data/weekly/change_report.json'))['summary']['new_games'])")
UPDATED_GAMES=$(python3 -c "import json; print(json.load(open('data/weekly/change_report.json'))['summary']['updated_games'])")
TOTAL_GAMES=$(python3 -c "import json; print(json.load(open('data/weekly/change_report.json'))['summary']['total_games'])")

# Send to Slack
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"🏒 SSC Hockey Scrape Complete\n• New Games: $NEW_GAMES\n• Updated Games: $UPDATED_GAMES\n• Total Games: $TOTAL_GAMES\"}" \
    "$WEBHOOK_URL"
```

### Example 19: Database Integration

```bash
# After weekly scrape, load to database
python3 << 'EOF'
import json
import sqlite3

# Connect to database
conn = sqlite3.connect('hockey_stats.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS games (
        game_id TEXT PRIMARY KEY,
        date TEXT,
        time TEXT,
        visitor_team TEXT,
        home_team TEXT,
        visitor_score TEXT,
        home_score TEXT,
        location TEXT,
        status TEXT,
        division TEXT
    )
''')

# Load games
games = json.load(open('data/weekly/schedules.json'))

# Insert/update games
for game in games:
    cursor.execute('''
        INSERT OR REPLACE INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        game.get('game_id'),
        game.get('date'),
        game.get('time'),
        game.get('visitor_team'),
        game.get('home_team'),
        game.get('visitor_score'),
        game.get('home_score'),
        game.get('location'),
        game.get('status'),
        game.get('division')
    ))

conn.commit()
conn.close()

print("✓ Database updated")
EOF

# Query database
sqlite3 hockey_stats.db "SELECT COUNT(*) FROM games;"
```

### Example 20: Archive Compression

```bash
# Compress old archives to save space
find data -name "ssc_2024_*" -type d | while read dir; do
    if [ ! -f "${dir}.tar.gz" ]; then
        echo "Compressing $dir..."
        tar -czf "${dir}.tar.gz" "$dir"
        rm -rf "$dir"
        echo "✓ Compressed and removed $dir"
    fi
done

# List compressed archives
ls -lh data/*.tar.gz
```

## Summary

These examples cover:
- ✓ Basic setup and configuration
- ✓ Daily/weekly operations
- ✓ Data analysis and reporting
- ✓ Troubleshooting common issues
- ✓ Advanced integrations

For more information, see:
- **SSC_WEEKLY_QUICK_START.md** - Quick setup guide
- **WEEKLY_AUTOMATION_GUIDE.md** - Complete documentation
- **INCREMENTAL_SCRAPING.md** - Technical details
