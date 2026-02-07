# SSC Hockey Incremental Scraping Guide

This guide explains how the incremental scraping system works, including data merging strategies, deduplication logic, and update detection.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Data Structures](#data-structures)
- [Scraping Strategy](#scraping-strategy)
- [Deduplication Logic](#deduplication-logic)
- [Update Detection](#update-detection)
- [Data Merging](#data-merging)
- [Change Tracking](#change-tracking)
- [Edge Cases](#edge-cases)

## Overview

The incremental scraping system is designed to:

1. **Minimize redundant work** by only updating changed data
2. **Preserve historical data** while incorporating new information
3. **Detect updates** to existing games (scores added, status changed)
4. **Avoid duplicates** using game IDs as unique identifiers
5. **Generate reports** showing what changed between runs

## How It Works

### High-Level Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Load Previous Data                                   │
│    - Read schedules.json                                │
│    - Read scrape_metadata.json                          │
│    - Index games by game_id                             │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Backup Previous Data                                 │
│    - Copy to data/weekly/previous/TIMESTAMP/            │
│    - Keep last 10 backups                               │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Run Full Scrape (All Dates)                          │
│    - Scrape entire season schedule                      │
│    - Get game details (if enabled)                      │
│    - Get player stats (if enabled)                      │
│    - Get standings (if enabled)                         │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Merge New Data with Previous                         │
│    - Identify new games                                 │
│    - Identify updated games                             │
│    - Preserve unchanged games                           │
│    - Deduplicate by game_id                             │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Generate Change Report                               │
│    - Count new games                                    │
│    - Count updated games                                │
│    - Track stat changes                                 │
│    - Save to change_report.json                         │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Save Merged Data                                     │
│    - Overwrite schedules.json                           │
│    - Update metadata                                    │
│    - Update stats and standings                         │
└─────────────────────────────────────────────────────────┘
```

### Why Scrape All Dates?

The system scrapes **all dates** on each run (not just new dates) because:

1. **Score Updates**: Games that were scheduled may now have final scores
2. **Status Changes**: Games may be postponed, rescheduled, or cancelled
3. **Detail Additions**: Games may have box scores, stats added later
4. **Corrections**: Scores or game details may be corrected
5. **Consistency**: Ensures complete, up-to-date dataset

This approach is robust but may take longer. For large datasets, consider date-range filtering.

## Data Structures

### Game Object

```python
@dataclass
class Game:
    game_id: str                           # Unique identifier (e.g., "1001")
    date: str                              # Game date (e.g., "11/15/2024")
    time: str                              # Game time (e.g., "7:00 PM")
    visitor_team: str                      # Visiting team name
    home_team: str                         # Home team name
    visitor_score: Optional[str]           # Visitor score (None if not played)
    home_score: Optional[str]              # Home score (None if not played)
    location: str                          # Rink/venue name
    status: str                            # Status/time (e.g., "Final", "7:00 PM")
    division: Optional[str]                # Division (e.g., "8A")
    game_url: str                          # URL to game details page
    source_url: str                        # URL where data was scraped
    period_scores: Optional[Dict]          # Period-by-period scores
    scoring_summary: Optional[List[Dict]]  # Goal details
    penalties: Optional[List[Dict]]        # Penalty details
    shots_on_goal: Optional[Dict]          # Shots by period
```

### Scrape Metadata

```python
@dataclass
class ScrapeMetadata:
    timestamp: str                # ISO timestamp of scrape
    league_id: str                # League ID
    subseason_id: str             # Subseason ID
    total_games: int              # Total games in dataset
    total_player_stats: int       # Total player stat records
    total_standings: int          # Total standings records
    new_games: int                # New games in this run
    updated_games: int            # Updated games in this run
    dates_scraped: List[str]      # Dates processed
```

## Scraping Strategy

### Full Season Approach

The scraper always processes the full season:

```python
scraper = SSCHockeyScraper(
    league_id=self.league_id,
    subseason_id=self.subseason_id,
    all_dates=True,  # ← Always True for incremental scraping
    scrape_game_details=True,
    scrape_stats=True,
    scrape_standings=True
)
```

### Why Not Date Filtering?

Date filtering (scraping only recent dates) has drawbacks:

**Problems:**
- Misses score updates for past games
- Doesn't detect postponements or corrections
- Loses synchronization with source data

**Solution:**
- Scrape full season (relatively fast for HTML scraping)
- Merge intelligently to preserve previous data
- Only update changed fields

### Optimization Options

For very large datasets, you could implement:

1. **Date Range Filtering**:
   ```python
   # Only scrape last 2 weeks
   cutoff_date = datetime.now() - timedelta(days=14)
   ```

2. **Conditional Detail Scraping**:
   ```python
   # Only get details for new/updated games
   if game.game_id not in previous_games:
       scrape_game_details(game)
   ```

3. **Incremental Stats**:
   ```python
   # Only scrape stats if standings changed
   if standings_changed:
       scrape_player_stats()
   ```

## Deduplication Logic

### Game ID as Primary Key

Games are uniquely identified by `game_id`:

```python
# Index previous games
previous_games = {g.game_id: g for g in load_previous_games()}

# Check for duplicates
for new_game in new_games:
    if new_game.game_id in previous_games:
        # Game exists - check for updates
        merge_or_update(previous_games[new_game.game_id], new_game)
    else:
        # New game - add to dataset
        add_game(new_game)
```

### Handling Missing Game IDs

Some games may not have IDs. Fallback strategy:

```python
if not game.game_id:
    # Create composite key from game details
    unique_key = f"{game.date}_{game.time}_{game.visitor_team}_{game.home_team}"
    game.game_id = unique_key
```

### Duplicate Detection Algorithm

```python
def merge_and_deduplicate(new_games, previous_games):
    merged = {}

    # Start with all previous games
    for game_id, game in previous_games.items():
        merged[game_id] = game

    # Process new games
    for new_game in new_games:
        if new_game.game_id not in previous_games:
            # Brand new game
            merged[new_game.game_id] = new_game
        else:
            # Existing game - check if updated
            if is_game_updated(previous_games[new_game.game_id], new_game):
                merged[new_game.game_id] = new_game
            # else: keep previous version

    return list(merged.values())
```

## Update Detection

### Update Detection Logic

A game is considered "updated" if any of these changed:

1. **Scores Added**:
   ```python
   if prev_game.visitor_score is None and new_game.visitor_score is not None:
       return True  # Score added
   ```

2. **Scores Changed**:
   ```python
   if prev_game.visitor_score != new_game.visitor_score:
       return True  # Score corrected
   ```

3. **Details Added**:
   ```python
   if prev_game.period_scores is None and new_game.period_scores is not None:
       return True  # Period scores added
   ```

4. **Status Changed**:
   ```python
   if prev_game.status != new_game.status:
       return True  # Status updated (e.g., "Scheduled" → "Final")
   ```

### Complete Update Check Function

```python
def _is_game_updated(self, prev_game: Game, new_game: Game) -> bool:
    """Check if a game has been updated."""

    # Check if scores were added
    if prev_game.visitor_score is None and new_game.visitor_score is not None:
        return True
    if prev_game.home_score is None and new_game.home_score is not None:
        return True

    # Check if scores changed
    if prev_game.visitor_score != new_game.visitor_score:
        return True
    if prev_game.home_score != new_game.home_score:
        return True

    # Check if game details were added
    if prev_game.period_scores is None and new_game.period_scores is not None:
        return True
    if prev_game.scoring_summary is None and new_game.scoring_summary is not None:
        return True
    if prev_game.penalties is None and new_game.penalties is not None:
        return True
    if prev_game.shots_on_goal is None and new_game.shots_on_goal is not None:
        return True

    # Check if status changed
    if prev_game.status != new_game.status:
        return True

    return False
```

## Data Merging

### Merge Strategy

**Philosophy**: Trust new data, but preserve previous data when new data is incomplete.

**Rules**:
1. **New games**: Always add
2. **Removed games**: Keep from previous (rarely happens)
3. **Updated games**: Replace with new version
4. **Unchanged games**: Keep previous version

### Merge Algorithm

```python
def merge_and_deduplicate(new_games, previous_games):
    merged = {}
    new_count = 0
    updated_count = 0

    # Start with previous games (preserves games that disappeared)
    for game_id, game in previous_games.items():
        merged[game_id] = game

    # Process new games
    for new_game in new_games:
        if not new_game.game_id:
            # Game without ID - add anyway with composite key
            unique_key = f"{new_game.date}_{new_game.time}_{new_game.visitor_team}"
            merged[unique_key] = new_game
            new_count += 1
            continue

        if new_game.game_id not in previous_games:
            # Brand new game
            merged[new_game.game_id] = new_game
            new_count += 1
        else:
            # Check for updates
            if _is_game_updated(previous_games[new_game.game_id], new_game):
                merged[new_game.game_id] = new_game
                updated_count += 1
            # else: keep previous version (no change)

    return list(merged.values()), new_count, updated_count
```

### Handling Player Stats and Standings

Player stats and standings are **replaced entirely** each run:

```python
# Don't merge stats - just use latest
self.player_stats = new_scraper.player_stats
self.standings = new_scraper.standings
```

**Rationale**:
- Stats are cumulative (always include all previous games)
- No need to merge - latest scrape has complete data
- Simplifies logic

## Change Tracking

### Change Report Structure

```json
{
  "timestamp": "2025-01-15T14:30:00",
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

### Detailed Change Report (from compare_ssc_data.py)

```json
{
  "games_comparison": {
    "total_old": 120,
    "total_new": 127,
    "new_games": 5,
    "updated_games": 12,
    "changes_by_type": {
      "new": [...],
      "score_added": [...],
      "score_changed": [...],
      "details_added": [...],
      "status_changed": [...]
    }
  },
  "player_stats_comparison": {
    "total_old": 240,
    "total_new": 245,
    "new_players": 5,
    "updated_players": 87,
    "updated_players_list": [...]
  },
  "standings_comparison": {
    "total_old": 16,
    "total_new": 16,
    "updated_teams": 12,
    "updated_teams_list": [...]
  }
}
```

## Edge Cases

### 1. Game ID Changes

**Problem**: Game ID changes between scrapes (rare but possible).

**Solution**:
- Use composite keys as fallback
- Track by (date, time, teams) if game_id changes
- Manual intervention may be needed

### 2. Postponed Games

**Problem**: Game is postponed, date changes.

**Scenario**:
- Week 1: Game 1001 scheduled for 11/15
- Week 2: Game 1001 rescheduled to 11/22

**Handling**:
```python
# Date change is detected as update
if prev_game.date != new_game.date:
    log(f"Game {game_id} rescheduled: {prev_game.date} → {new_game.date}")
    return True  # Mark as updated
```

### 3. Score Corrections

**Problem**: Score is corrected after initial posting.

**Scenario**:
- Week 1: Game 1001 shows "Team A: 3, Team B: 2"
- Week 2: Corrected to "Team A: 3, Team B: 3"

**Handling**:
```python
# Score change detected
if prev_game.visitor_score != new_game.visitor_score:
    log(f"Score corrected for game {game_id}")
    return True  # Use new score
```

### 4. Missing Games

**Problem**: Game appears in previous scrape but not in new scrape.

**Strategy**:
```python
# Keep games from previous that aren't in new scrape
# This preserves cancelled or postponed games
for game_id, game in previous_games.items():
    if game_id not in new_games_map:
        merged[game_id] = game  # Preserve
        log(f"Game {game_id} not found in new scrape - preserving")
```

### 5. Duplicate Detection Failures

**Problem**: Same game appears with different game_ids.

**Detection**:
```python
# Check for games with same details but different IDs
def find_duplicates(games):
    seen = set()
    duplicates = []

    for game in games:
        key = (game.date, game.time, game.visitor_team, game.home_team)
        if key in seen:
            duplicates.append(game)
        seen.add(key)

    return duplicates
```

**Manual Fix**:
```bash
# Review duplicates
python3 -c "from ssc_weekly_scraper import *; check_duplicates('data/weekly')"

# Remove duplicates manually if needed
```

### 6. Incomplete Detail Scraping

**Problem**: Some games have details in previous scrape but not in new scrape.

**Strategy**:
```python
# Preserve previous details if new scrape didn't get them
if prev_game.period_scores and not new_game.period_scores:
    new_game.period_scores = prev_game.period_scores

if prev_game.scoring_summary and not new_game.scoring_summary:
    new_game.scoring_summary = prev_game.scoring_summary
```

**Implementation**:
This is currently NOT implemented. Consider adding if details mysteriously disappear.

## Best Practices

1. **Always backup before merging**: The system does this automatically
2. **Review change reports**: Check for anomalies after each run
3. **Monitor game counts**: Sudden drops may indicate scraping issues
4. **Validate data periodically**: Compare with source website
5. **Keep historical backups**: Maintain `previous/` directories
6. **Test before deploying**: Use `test_ssc_weekly_automation.py`

## Advanced Topics

### Custom Merge Logic

To implement custom merge logic, extend `IncrementalSSCScraper`:

```python
class CustomScraper(IncrementalSSCScraper):
    def merge_and_deduplicate(self, new_games, previous_games):
        # Custom logic here
        # For example: preserve details from previous games
        merged, new_count, updated_count = super().merge_and_deduplicate(
            new_games, previous_games
        )

        # Enhance with detail preservation
        for game in merged:
            if game.game_id in previous_games:
                prev_game = previous_games[game.game_id]
                if not game.period_scores and prev_game.period_scores:
                    game.period_scores = prev_game.period_scores

        return merged, new_count, updated_count
```

### Date-Range Filtering

For optimization, implement date-range filtering:

```python
from datetime import datetime, timedelta

class OptimizedScraper(IncrementalSSCScraper):
    async def scrape_incremental(self, days_back=14, **kwargs):
        # Only scrape last N days
        cutoff = datetime.now() - timedelta(days=days_back)

        # Filter dates before scraping
        # ... implementation details ...
```

## Troubleshooting

### Duplicates Appearing

**Symptom**: Same game appears multiple times in output.

**Diagnosis**:
```bash
# Check for duplicates
python3 -c "
import json
games = json.load(open('data/weekly/schedules.json'))
ids = [g['game_id'] for g in games]
print(f'Total: {len(games)}, Unique IDs: {len(set(ids))}')
"
```

**Fix**: Review game_id assignment logic in scraper.

### Missing Updates

**Symptom**: Known score changes not detected.

**Diagnosis**:
```bash
# Compare two specific games
python3 compare_ssc_data.py \
    --old-dir data/weekly/previous/20250108_140000 \
    --new-dir data/weekly
```

**Fix**: Check `_is_game_updated()` logic.

### Data Loss

**Symptom**: Games disappearing between runs.

**Diagnosis**:
```bash
# Check game counts
ls -lt data/weekly/previous/
cat data/weekly/previous/*/scrape_metadata.json | grep total_games
```

**Fix**: Review merge logic - ensure previous games are preserved.
