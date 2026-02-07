# Hockey Stats Calculator - Complete Documentation

## Overview

This stats calculation engine provides comprehensive hockey statistics analysis, calculating both basic and advanced metrics from raw game data stored in SQLite databases.

## Architecture

The system consists of two main modules:

### 1. **stats_calculator.py** - Basic Stats Engine
Calculates fundamental statistics from raw game data:
- Player statistics (goals, assists, points, penalties)
- Team records (wins, losses, ties, points)
- Special teams performance (PP%, PK%)
- Period-by-period scoring
- Home/away splits

### 2. **advanced_metrics.py** - Advanced Analytics Engine
Calculates sophisticated scheduling and performance metrics:
- Strength of Schedule (SOS)
- Adjusted SOS (2-degree opponents)
- Strength of Victory (SOV)
- Head-to-head records
- Rest differential analysis
- Recent form tracking (last 10 games, current streaks)

## Database Schema Compatibility

The calculators support **two database schema versions**:

### Enhanced Entity Schema
```
- team_entities
- player_entities
- game_entities
- goal_events
- penalty_events
```

### Original Schema
```
- teams
- players
- all_games
- goal_details
- penalty_details
- player_statistics
```

The calculators automatically detect which schema is present and adapt accordingly.

## Installation

### Prerequisites
```bash
# Python 3.7 or higher
python3 --version

# Required packages (minimal - only SQLite which is built-in)
# No additional dependencies required!
```

### Setup
```bash
cd "/path/to/Hockey_Scraper"

# Make scripts executable
chmod +x stats_calculator.py
chmod +x advanced_metrics.py
chmod +x example_stats_usage.py
```

## Usage

### Quick Start - Complete Pipeline

Run the full calculation pipeline on your database:

```bash
python3 example_stats_usage.py <database_path> [season_id]
```

**Example:**
```bash
python3 example_stats_usage.py \
  hockey_scraper_repo/output/enhanced_entities_10776_20250914_153516.db \
  10776
```

This will:
1. Calculate all basic stats
2. Calculate all advanced metrics
3. Display sample results

### Individual Components

#### Calculate Basic Stats Only
```bash
python3 stats_calculator.py <database_path> [season_id]
```

**Example:**
```bash
python3 stats_calculator.py \
  hockey_scraper_repo/output/enhanced_entities_10776_20250914_153516.db \
  10776
```

#### Calculate Advanced Metrics Only
```bash
python3 advanced_metrics.py <database_path> [season_id]
```

**Note:** Must run `stats_calculator.py` first to populate the `team_stats` table.

### Programmatic Usage

```python
from stats_calculator import AdvancedStatsCalculator
from advanced_metrics import AdvancedMetricsCalculator

# Basic stats
calc = AdvancedStatsCalculator("path/to/database.db")
calc.calculate_all_stats(season_id="10776")

# Advanced metrics
metrics = AdvancedMetricsCalculator("path/to/database.db")
metrics.calculate_all_advanced_metrics(season_id="10776")
```

## Output Tables

### player_stats
Individual player statistics for the season.

**Key Fields:**
- `player_id`, `team_id`, `season_id` (composite primary key)
- `games_played`, `goals`, `assists`, `points`, `points_per_game`
- `power_play_goals`, `short_handed_goals`, `game_winning_goals`
- `penalties`, `penalty_minutes`, `pim_per_game`
- `major_penalties`, `game_misconducts`

**Sample Query:**
```sql
-- Top 10 scorers
SELECT player_number, team_id, goals, assists, points, points_per_game
FROM player_stats
WHERE season_id = '10776'
ORDER BY points DESC, goals DESC
LIMIT 10;
```

### team_stats
Comprehensive team statistics and standings.

**Key Fields:**
- `team_id`, `season_id` (composite primary key)
- Record: `games_played`, `wins`, `losses`, `ties`, `points`, `points_pct`
- Scoring: `goals_for`, `goals_against`, `goal_differential`
- By period: `goals_period_1`, `goals_period_2`, `goals_period_3`
- Special teams: `power_play_pct`, `penalty_kill_pct`
- Home/away: `home_wins`, `away_wins`, etc.
- Recent form: `last_10_record`, `current_streak`

**Sample Query:**
```sql
-- Division standings
SELECT team_id, wins, losses, ties, points, points_pct,
       goals_for, goals_against, goal_differential
FROM team_stats
WHERE season_id = '10776'
  AND division_id = 60041
ORDER BY points_pct DESC, goal_differential DESC;
```

### strength_of_schedule
Advanced scheduling metrics for each team.

**Key Fields:**
- `opponents_avg_points_pct` - Basic SOS (average opponent winning %)
- `adjusted_sos` - Weighted SOS including opponent's opponents
- `beaten_teams_avg_points_pct` - Strength of Victory
- `sos_rank`, `sov_rank` - Rankings within season
- `games_vs_top_third`, `points_vs_top_third` - Performance vs quality opponents
- `games_on_rest`, `games_back_to_back`, `rest_differential` - Rest analysis

**Sample Query:**
```sql
-- Teams with toughest schedules
SELECT team_id, opponents_avg_points_pct, adjusted_sos, sos_rank
FROM strength_of_schedule
WHERE season_id = '10776'
ORDER BY opponents_avg_points_pct DESC
LIMIT 10;
```

### head_to_head
Team vs team matchup records.

**Key Fields:**
- `team1_id`, `team2_id`, `season_id` (composite primary key)
- `games_played`, `team1_wins`, `team1_losses`, `team1_ties`
- `team1_goals_for`, `team1_goals_against`
- `team1_pp_goals`, `team1_pp_pct`
- `last_5_record`, `team1_current_streak`

**Sample Query:**
```sql
-- Head-to-head between two teams
SELECT *
FROM head_to_head
WHERE season_id = '10776'
  AND ((team1_id = 'TeamA_U12C_10776' AND team2_id = 'TeamB_U12C_10776')
    OR (team1_id = 'TeamB_U12C_10776' AND team2_id = 'TeamA_U12C_10776'));
```

## Calculation Formulas

### Basic Stats

#### Player Points
```
Points = Goals + Assists
Points Per Game = Points / Games Played
```

#### Team Points
```
Points = (Wins × 2) + Ties
Points % = Points / (Games Played × 2)
```

#### Power Play %
```
PP% = (PP Goals / PP Opportunities) × 100

Where:
  PP Goals = Goals scored while on power play
  PP Opportunities = Penalties against opponent (≥2 minutes)
```

#### Penalty Kill %
```
PK% = (1 - (PP Goals Against / Times Shorthanded)) × 100

Where:
  PP Goals Against = Goals allowed while shorthanded
  Times Shorthanded = Penalties taken (≥2 minutes)
```

### Advanced Metrics

#### Strength of Schedule (SOS)
```
SOS = Average of all opponents' points%

For each team:
  1. Get list of all opponents played
  2. Calculate each opponent's points%
  3. Average the points%
```

#### Adjusted SOS (2-degree)
```
Adjusted SOS = (Opponent Points% × 2/3) + (Opponent's Opponent Points% × 1/3)

This accounts for not just who you played, but who your opponents played
```

#### Strength of Victory (SOV)
```
SOV = Average points% of teams beaten

For each team:
  1. Get list of all opponents defeated
  2. Calculate each defeated opponent's points%
  3. Average the points%
```

#### Rest Differential
```
Rest Differential = Games On Rest - Games Back-to-Back

Where:
  Games On Rest = Games with 2+ days rest
  Games Back-to-Back = Games on consecutive days
```

#### Current Streak
```
Algorithm:
  1. Get all game results in chronological order (W/L/T)
  2. Start from most recent game
  3. Count consecutive identical results
  4. Format: "W3" = 3-game winning streak, "L2" = 2-game losing streak
```

## Performance Optimization

### Batch Processing
The calculators use batch SQL queries and transactions for optimal performance:

```python
# All updates happen in a single transaction
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    # ... perform all calculations ...
    conn.commit()  # Single commit at end
```

### Progress Reporting
For large datasets, progress is logged every 50 players:

```
Processing 450 players...
  Progress: 0/450 players
  Progress: 50/450 players
  Progress: 100/450 players
  ...
```

### Typical Performance
- **500 players**: ~5-10 seconds
- **20 teams**: ~2-3 seconds
- **Complete season**: ~15-20 seconds total

## Troubleshooting

### "No team stats found"
```
ERROR: No team stats found. Run basic stats calculation first.
```

**Solution:** Run `stats_calculator.py` before `advanced_metrics.py`
```bash
python3 stats_calculator.py database.db 10776
python3 advanced_metrics.py database.db 10776
```

### "Table not found"
```
ERROR: no such table: goal_events
```

**Solution:** The calculators auto-detect schema but need at least one recognized table. Ensure your database has game data in one of the supported schemas.

### Empty Results
If queries return no results:

1. **Check season_id:** Ensure you're using the correct season ID
   ```sql
   SELECT DISTINCT season_id FROM games;
   ```

2. **Check data exists:** Verify you have completed games
   ```sql
   SELECT COUNT(*) FROM games WHERE status = 'final';
   ```

3. **Check dates:** For enhanced entity schema, check the `played` flag
   ```sql
   SELECT COUNT(*) FROM game_entities WHERE played = 1;
   ```

## Advanced Usage Examples

### Custom Queries

#### Top Goal Scorers Per Team
```sql
WITH ranked_players AS (
  SELECT player_number, team_id, goals, assists, points,
         ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY goals DESC) as rn
  FROM player_stats
  WHERE season_id = '10776'
)
SELECT * FROM ranked_players WHERE rn <= 3;
```

#### Division Power Rankings
```sql
SELECT ts.team_id, ts.points_pct,
       ts.power_play_pct, ts.penalty_kill_pct,
       sos.adjusted_sos, sos.beaten_teams_avg_points_pct,
       ts.goal_differential
FROM team_stats ts
JOIN strength_of_schedule sos ON ts.team_id = sos.team_id
WHERE ts.season_id = '10776'
  AND ts.division_id = 60041
ORDER BY ts.points_pct DESC;
```

#### Teams Performing Above/Below Expectation
```sql
SELECT ts.team_id,
       ts.points_pct as actual_pct,
       sos.opponents_avg_points_pct as expected_pct,
       (ts.points_pct - sos.opponents_avg_points_pct) as diff
FROM team_stats ts
JOIN strength_of_schedule sos ON ts.team_id = sos.team_id
WHERE ts.season_id = '10776'
ORDER BY diff DESC;
```

### Programmatic Access

#### Get Team Leaders
```python
import sqlite3

def get_team_leaders(db_path, team_id, season_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Points leader
    cursor.execute("""
        SELECT player_number, goals, assists, points
        FROM player_stats
        WHERE team_id = ? AND season_id = ?
        ORDER BY points DESC
        LIMIT 1
    """, (team_id, season_id))

    points_leader = cursor.fetchone()

    # Goals leader
    cursor.execute("""
        SELECT player_number, goals
        FROM player_stats
        WHERE team_id = ? AND season_id = ?
        ORDER BY goals DESC
        LIMIT 1
    """, (team_id, season_id))

    goals_leader = cursor.fetchone()

    conn.close()

    return {
        'points_leader': points_leader,
        'goals_leader': goals_leader
    }
```

#### Compare Two Teams
```python
def compare_teams(db_path, team1_id, team2_id, season_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get team stats
    cursor.execute("""
        SELECT team_id, wins, losses, ties, points_pct,
               goals_for, goals_against, power_play_pct, penalty_kill_pct
        FROM team_stats
        WHERE team_id IN (?, ?) AND season_id = ?
    """, (team1_id, team2_id, season_id))

    teams = {row[0]: row[1:] for row in cursor.fetchall()}

    # Get head-to-head
    cursor.execute("""
        SELECT team1_wins, team1_losses, team1_ties
        FROM head_to_head
        WHERE team1_id = ? AND team2_id = ? AND season_id = ?
    """, (team1_id, team2_id, season_id))

    h2h = cursor.fetchone()

    conn.close()

    return {
        'team1_stats': teams.get(team1_id),
        'team2_stats': teams.get(team2_id),
        'head_to_head': h2h
    }
```

## Limitations and Future Enhancements

### Current Limitations

1. **Plus/Minus:** Not currently calculated (requires play-by-play data)
2. **Shots on Goal:** Only calculated if available in source data
3. **Time on Ice:** Not available in GameSheet data
4. **Faceoff Stats:** Not available in current data sources
5. **Travel Distance:** SOS table has fields but requires manual input

### Planned Enhancements

1. **Playoff Statistics:** Separate tables for playoff performance
2. **Player Streaks:** Individual player hot/cold streaks
3. **Situational Stats:** Performance when leading/trailing
4. **Corsi/Fenwick:** Advanced possession metrics (if data available)
5. **Expected Goals (xG):** Model-based expected performance

## Support and Contributing

### Getting Help

1. Check this README for common issues
2. Review the example queries in `example_stats_usage.py`
3. Examine the source code - all calculations are well-commented

### Reporting Issues

When reporting issues, include:
- Database schema version (enhanced entity vs original)
- Season ID being calculated
- Sample data that reproduces the issue
- Full error message and stack trace

## License

This stats calculation engine is part of the Hockey_Scraper project.

## Version History

### v1.0.0 (2025-01-08)
- Initial release
- Support for both enhanced entity and original schemas
- Complete basic stats calculation
- Advanced metrics (SOS, SOV, H2H)
- Rest differential analysis
- Recent form tracking
- Comprehensive documentation

---

**Questions?** Review the code in `stats_calculator.py` and `advanced_metrics.py` - all formulas are documented inline!
