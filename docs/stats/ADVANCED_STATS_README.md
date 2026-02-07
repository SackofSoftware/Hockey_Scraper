# Advanced Hockey Stats Database System

## Overview

This system provides a complete database schema and data import pipeline for advanced hockey statistics. It extracts data from the GameSheet API and stores it in a normalized SQLite database with comprehensive tracking of games, goals, penalties, rosters, and calculated statistics.

## Components

### 1. `advanced_stats_database.py`

**Purpose:** Complete SQLite database schema implementation

**Features:**
- **Raw Data Tables:** games, goals, penalties, game_rosters, teams, divisions
- **Calculated Stats Tables:** player_stats, team_stats, strength_of_schedule, head_to_head, player_game_log
- **Data Quality Tracking:** data_quality_issues table
- **Foreign key relationships** with cascade deletes
- **Performance indexes** on all commonly queried columns
- **Context manager support** for clean resource management

**Key Tables:**

```sql
games            -- Complete game information with scores and metadata
goals            -- Every goal with scorer, assists, and special teams flags
penalties        -- Every penalty with player, type, and duration
game_rosters     -- Player participation and in-game statistics
teams            -- Team master data with division assignments
divisions        -- Division configuration and rules
player_stats     -- Aggregated player statistics by season
team_stats       -- Comprehensive team statistics and standings
```

**Usage:**
```python
from advanced_stats_database import create_database

# Create new database
db = create_database('hockey_stats.db')

# Use context manager
with db:
    stats = db.get_stats()
    print(stats)
```

### 2. `data_importer.py`

**Purpose:** Import data from GameSheet API into database

**Features:**
- **Multi-phase import:** divisions → teams → schedule → box scores
- **Automatic pagination** for large datasets
- **Progress reporting** with detailed statistics
- **Error handling** with API call tracking
- **Rate limiting** to be respectful to API
- **Batch insertion** for performance
- **Automatic stats calculation** from raw data

**Import Process:**

1. **Phase 1: Divisions** - Import all divisions for season
2. **Phase 2: Teams** - Extract teams from standings API
3. **Phase 3: Schedule** - Import all games with pagination
4. **Phase 4: Box Scores** - Extract goals, penalties, rosters for completed games
5. **Phase 5: Statistics** - Calculate player and team statistics

**Usage:**
```python
from advanced_stats_database import create_database
from data_importer import DataImporter

# Create database
db = create_database('hockey_stats.db')

# Create importer
importer = DataImporter(db, season_id="10776")

# Import all data (or specific divisions)
importer.import_all(division_ids=[60038])  # Optional filter

# Get import statistics
importer._print_statistics()
```

**Data Sources:**

| API Endpoint | Data Extracted |
|--------------|----------------|
| `getSeason` | Season metadata, penalty codes |
| `getDivisions` | Division list and configuration |
| `getDivisionStandings` | Teams, logos, standings |
| `getSeasonSchedule` | Game schedule with teams and venues |
| `getGameStats` | Complete box scores with goals, penalties, rosters |

### 3. `test_database.py`

**Purpose:** Verify database functionality and demonstrate queries

**Features:**
- Database statistics summary
- Sample game data
- Goal details with special teams flags
- Top scorers with advanced stats
- Penalty summaries
- Team standings with metrics
- Goals by period breakdown
- Special teams effectiveness
- Player game logs

**Usage:**
```bash
python3 test_database.py
```

## Database Schema Details

### Games Table

Stores complete game information:
- Game identification (game_id, game_number)
- Teams (home/visitor IDs and names)
- Scores (home_score, visitor_score)
- Timing (date, time, location)
- Status (scheduled, in_progress, final)
- Data quality tracking

### Goals Table

Every goal with complete details:
- Timing (period, time_remaining, game_time_seconds)
- Scorer (player_id, number, name)
- Assists (up to 2 assists with full details)
- Special teams flags (power_play, short_handed, game_winning, empty_net)
- Data verification flags

### Penalties Table

Every penalty with full context:
- Player who committed penalty
- Penalty type and class (minor, major, misconduct)
- Duration in minutes
- Time and period
- Served by (if different player)

### Game Rosters Table

Player participation per game:
- Player identification
- Status (playing, scratched, injured)
- In-game statistics (goals, assists, points, PIM)
- Goalie statistics (if applicable)
- Season totals at time of game

### Player Stats Table

Aggregated player statistics:
- Basic stats (goals, assists, points, games_played)
- Special teams (PPG, SHG, GWG, empty net goals)
- Discipline (penalties, PIM, majors)
- Advanced metrics (points_per_game, PIM_per_game)
- Data quality (number_consistency_score, confidence_score)

### Team Stats Table

Comprehensive team statistics:
- Record (W-L-T, OTW, OTL, SOW, SOL)
- Points and percentages
- Scoring (GF, GA, by period)
- Special teams (PP%, PK%)
- Home/away splits
- Recent form (last 10, streak)

## Sample Queries

### Top Scorers
```python
cursor.execute('''
    SELECT player_number, team_id, goals, points, games_played,
           points_per_game, penalty_minutes
    FROM player_stats
    ORDER BY points DESC, goals DESC
    LIMIT 10
''')
```

### Team Standings
```python
cursor.execute('''
    SELECT t.team_name, ts.wins, ts.losses, ts.ties,
           ts.points, ts.goals_for, ts.goals_against
    FROM team_stats ts
    JOIN teams t ON ts.team_id = t.team_id
    ORDER BY ts.points DESC, ts.goal_differential DESC
''')
```

### Goals by Period
```python
cursor.execute('''
    SELECT period, COUNT(*) as goals
    FROM goals
    GROUP BY period
    ORDER BY period
''')
```

### Special Teams Effectiveness
```python
cursor.execute('''
    SELECT
        SUM(CASE WHEN is_power_play THEN 1 ELSE 0 END) as pp_goals,
        SUM(CASE WHEN is_short_handed THEN 1 ELSE 0 END) as sh_goals,
        COUNT(*) as total_goals
    FROM goals
''')
```

## Testing Results

Successfully imported and tested with **U10B - GOLD Division (ID: 60038)**:

| Metric | Count |
|--------|-------|
| Games | 56 (30 completed) |
| Goals | 263 |
| Penalties | 63 |
| Rosters | 793 player-game records |
| Players | 93 unique players |
| Teams | 6 |
| API Calls | 33 |
| Success Rate | 100% (0 errors) |

**Sample Top Scorer:**
- Player #87: 20 goals, 20 points in 7 games (2.86 PPG)
- 3 power play goals, 2 game-winning goals

**Sample Team Standing:**
- Seahawks Squirt Blue: 6-0-1 (13 points, .929 PTS%)
- 60 goals for, 13 goals against (+47 differential)

## Data Quality Features

### Verification Flags
- `scorer_number_verified`: Jersey number accuracy confirmed
- `data_confidence`: Overall confidence score (0.0 to 1.0)
- `number_consistency_score`: Player number consistency tracking

### Data Quality Issues Table
Tracks suspect data:
- Entity type and ID
- Issue type (wrong_number, missing_name, duplicate_player, etc.)
- Confidence impact
- Resolution status and notes

### Privacy Considerations
Player names are often withheld by GameSheet API for privacy:
- Player IDs are reliable and unique
- Jersey numbers serve as primary identifier
- Names may be empty strings or single spaces

## Performance Optimizations

### Indexes
- Game lookups by season, division, date, status
- Goal/penalty lookups by game, player, team
- Player stats by season, team, points
- Foreign key indexes for joins

### Batch Operations
- Bulk inserts for games, goals, penalties
- Transaction management for consistency
- VACUUM for database optimization

### API Efficiency
- Pagination with configurable limits
- Rate limiting (0.1s delay between calls)
- Error handling and retry logic
- API call tracking

## Future Enhancements

### Calculated Stats (Not Yet Implemented)
- Strength of Schedule (SOS)
- Head-to-Head records
- Player game logs
- Advanced metrics (PDO, Corsi, Fenwick - requires shot data)

### Data Quality Improvements
- Automated number consistency checking
- Duplicate player detection
- Cross-reference with roster data

### API Additions
- Real-time game updates
- Playoff bracket tracking
- Historical season comparison

## Requirements

```
python >= 3.8
requests >= 2.31.0
sqlite3 (built-in)
```

## Installation

```bash
# No additional packages needed beyond Python standard library + requests
pip install requests
```

## Quick Start

```bash
# 1. Create database schema
python3 advanced_stats_database.py

# 2. Import data for season
python3 data_importer.py

# 3. Test and verify
python3 test_database.py
```

## Configuration

Edit `data_importer.py` main() function to customize:

```python
# Season ID (Bay State Hockey League 2025-26 = 10776)
season_id = "10776"

# Import specific divisions (or None for all)
division_ids = [60038, 60042]  # U10B-GOLD, U12B

# Database path
db_path = "advanced_hockey_stats.db"
```

## Troubleshooting

### No Completed Games Found
- Check that games have status='final' in schedule
- Try different division IDs
- Verify season is in progress

### API Errors
- Check internet connection
- Verify season_id is valid
- Ensure API endpoints haven't changed

### Database Errors
- Ensure write permissions for database file
- Check disk space
- Verify Python version >= 3.8

## Data Flow Diagram

```
GameSheet API
    │
    ├─→ getDivisions ──→ divisions table
    │
    ├─→ getDivisionStandings ──→ teams table
    │
    ├─→ getSeasonSchedule ──→ games table
    │
    └─→ getGameStats ──→ goals, penalties, game_rosters tables
                           │
                           └─→ CALCULATED
                               ├─→ player_stats
                               └─→ team_stats
```

## License

This system is designed for Bay State Hockey League data analysis and statistics tracking. Respect GameSheet API usage policies and rate limits.

## Support

For issues or questions:
1. Check GAMESHEET_API_DOCUMENTATION.md for API details
2. Review ADVANCED_STATS_API_DESIGN.md for schema design
3. See existing extractor code in ultimate_hockey_stats_extractor.py

## Version History

**v1.0 (2025-11-08)**
- Initial implementation
- Complete database schema
- GameSheet API import pipeline
- Basic statistics calculation
- Test suite and documentation
