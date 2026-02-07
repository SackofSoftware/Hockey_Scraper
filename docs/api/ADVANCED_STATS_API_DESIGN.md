# Advanced Hockey Stats API Design
## Multi-Table Architecture with Cross-Referencing & Data Quality Tracking

---

## **🎯 CORE CONCEPT**

Build a **comprehensive stats database** that:
1. ✅ Extracts ALL GameSheet data (even suspect player #s)
2. ✅ Calculates advanced metrics from raw data
3. ✅ Tracks data quality/confidence scores
4. ✅ Provides REST API with multiple views/cross-references
5. ✅ LLM-friendly JSON responses with context

---

## **📊 DATABASE SCHEMA**

### **1. Raw Data Tables (Source of Truth)**

```sql
-- GAMES: Core game information
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    season_id TEXT,
    division_id INTEGER,
    division_name TEXT,
    game_number TEXT,
    game_type TEXT,  -- 'Regular Season', 'Playoff'
    date DATE,
    time TEXT,
    location TEXT,
    status TEXT,  -- 'scheduled', 'in_progress', 'final'

    -- Teams
    home_team_id INTEGER,
    home_team_name TEXT,
    visitor_team_id INTEGER,
    visitor_team_name TEXT,

    -- Scores
    home_score INTEGER,
    visitor_score INTEGER,

    -- Metadata
    extraction_timestamp TIMESTAMP,
    data_quality_score REAL  -- 0.0 to 1.0
);

-- GOALS: Every goal with complete details
CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT REFERENCES games(game_id),

    -- Event details
    period TEXT,
    period_number INTEGER,
    time_remaining TEXT,
    game_time_seconds INTEGER,  -- Calculated for sorting

    -- Scoring team
    team_id INTEGER,
    team_name TEXT,
    is_home_team BOOLEAN,

    -- Scorer
    scorer_player_id TEXT,
    scorer_number TEXT,  -- ⚠️ May be inaccurate
    scorer_name TEXT,    -- Usually empty
    scorer_total_goals INTEGER,  -- Season total at time of goal

    -- Primary assist
    assist1_player_id TEXT,
    assist1_number TEXT,  -- ⚠️ May be inaccurate
    assist1_name TEXT,
    assist1_total_goals INTEGER,

    -- Secondary assist
    assist2_player_id TEXT,
    assist2_number TEXT,  -- ⚠️ May be inaccurate
    assist2_name TEXT,
    assist2_total_goals INTEGER,

    -- Goal types
    is_power_play BOOLEAN,
    is_short_handed BOOLEAN,
    is_game_winning BOOLEAN,
    is_empty_net BOOLEAN,

    -- Data quality flags
    scorer_number_verified BOOLEAN DEFAULT FALSE,
    assist1_number_verified BOOLEAN DEFAULT FALSE,
    assist2_number_verified BOOLEAN DEFAULT FALSE,
    data_confidence REAL  -- 0.0 to 1.0
);

-- PENALTIES: Every penalty with complete details
CREATE TABLE penalties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT REFERENCES games(game_id),

    -- Event details
    period TEXT,
    period_number INTEGER,
    time_remaining TEXT,
    game_time_seconds INTEGER,

    -- Team
    team_id INTEGER,
    team_name TEXT,
    is_home_team BOOLEAN,

    -- Player
    player_id TEXT,
    player_number TEXT,  -- ⚠️ May be inaccurate
    player_name TEXT,    -- Usually empty

    -- Penalty details
    penalty_type TEXT,
    penalty_class TEXT,  -- 'minor', 'major', 'misconduct', etc.
    duration_minutes INTEGER,
    is_major BOOLEAN,

    -- Served by (if different)
    served_by_player_id TEXT,
    served_by_number TEXT,

    -- Data quality
    player_number_verified BOOLEAN DEFAULT FALSE,
    data_confidence REAL
);

-- ROSTERS: Player information per game
CREATE TABLE game_rosters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT REFERENCES games(game_id),
    team_id INTEGER,
    team_name TEXT,

    -- Player info
    player_id TEXT NOT NULL,
    player_number TEXT,  -- ⚠️ May be inaccurate
    first_name TEXT,
    last_name TEXT,
    position TEXT,

    -- Status
    status TEXT,  -- 'playing', 'scratched', 'injured'
    is_starting BOOLEAN,
    is_affiliated BOOLEAN,
    added_at_game_time BOOLEAN,

    -- Game stats
    goals INTEGER,
    assists INTEGER,
    points INTEGER,
    pim INTEGER,
    yellow_cards INTEGER,
    red_cards INTEGER,

    -- Goalie stats
    goals_against INTEGER,
    shots_against INTEGER,
    save_pct REAL,
    time_on_ice TEXT,

    -- Season totals (at time of game)
    season_goals_before INTEGER,
    season_assists_before INTEGER,

    UNIQUE(game_id, team_id, player_id)
);

-- TEAMS: Team master data
CREATE TABLE teams (
    team_id INTEGER PRIMARY KEY,
    team_name TEXT,
    division_id INTEGER,
    division_name TEXT,
    logo_url TEXT,

    -- Updated from standings
    last_updated TIMESTAMP
);

-- DIVISIONS: Division master data
CREATE TABLE divisions (
    division_id INTEGER PRIMARY KEY,
    division_name TEXT,
    season_id TEXT,
    assist_value INTEGER,
    goal_value INTEGER,
    max_goal_differential INTEGER
);
```

---

### **2. Calculated Stats Tables**

```sql
-- PLAYER_STATS: Aggregated player statistics
CREATE TABLE player_stats (
    player_id TEXT,
    team_id INTEGER,
    season_id TEXT,

    -- Identity
    player_number TEXT,  -- Most common # worn
    player_name TEXT,
    position TEXT,

    -- Games
    games_played INTEGER,
    games_started INTEGER,

    -- Scoring
    goals INTEGER,
    assists INTEGER,
    points INTEGER,
    points_per_game REAL,

    -- Special teams
    power_play_goals INTEGER,
    power_play_assists INTEGER,
    power_play_points INTEGER,
    short_handed_goals INTEGER,
    short_handed_assists INTEGER,
    short_handed_points INTEGER,
    game_winning_goals INTEGER,
    empty_net_goals INTEGER,

    -- Discipline
    penalties INTEGER,
    penalty_minutes INTEGER,
    pim_per_game REAL,
    major_penalties INTEGER,
    game_misconducts INTEGER,

    -- Shooting (if available)
    shots_on_goal INTEGER,
    shooting_pct REAL,

    -- Advanced
    plus_minus INTEGER,

    -- Goalie stats
    games_started_goalie INTEGER,
    wins INTEGER,
    losses INTEGER,
    ties INTEGER,
    saves INTEGER,
    goals_against INTEGER,
    save_pct REAL,
    goals_against_avg REAL,
    shutouts INTEGER,

    -- Data quality
    number_consistency_score REAL,  -- How often same # used
    total_number_variations INTEGER,
    confidence_score REAL,

    PRIMARY KEY (player_id, team_id, season_id)
);

-- TEAM_STATS: Comprehensive team statistics
CREATE TABLE team_stats (
    team_id INTEGER,
    season_id TEXT,
    division_id INTEGER,

    -- Record
    games_played INTEGER,
    wins INTEGER,
    losses INTEGER,
    ties INTEGER,
    otw INTEGER,  -- Overtime wins
    otl INTEGER,  -- Overtime losses
    sow INTEGER,  -- Shootout wins
    sol INTEGER,  -- Shootout losses

    -- Points
    points INTEGER,
    points_pct REAL,
    row INTEGER,  -- Regulation + OT wins

    -- Standings position
    division_rank INTEGER,

    -- Scoring
    goals_for INTEGER,
    goals_against INTEGER,
    goal_differential INTEGER,
    goals_per_game REAL,
    goals_against_per_game REAL,

    -- By period
    goals_period_1 INTEGER,
    goals_period_2 INTEGER,
    goals_period_3 INTEGER,
    goals_overtime INTEGER,
    goals_allowed_period_1 INTEGER,
    goals_allowed_period_2 INTEGER,
    goals_allowed_period_3 INTEGER,
    goals_allowed_overtime INTEGER,

    -- Special teams
    power_play_goals INTEGER,
    power_play_opportunities INTEGER,
    power_play_pct REAL,
    power_play_goals_against INTEGER,
    times_shorthanded INTEGER,
    penalty_kill_pct REAL,
    short_handed_goals INTEGER,
    short_handed_goals_against INTEGER,

    -- Discipline
    penalty_minutes INTEGER,
    pim_per_game REAL,
    penalties_taken INTEGER,
    major_penalties INTEGER,

    -- Shooting (if available)
    shots_for INTEGER,
    shots_against INTEGER,
    shooting_pct REAL,
    save_pct REAL,
    pdo REAL,  -- (Shooting% + Save%) * 10

    -- Recent form
    last_10_record TEXT,  -- "6-3-1"
    current_streak TEXT,  -- "W3", "L2"

    -- Home/Away splits
    home_wins INTEGER,
    home_losses INTEGER,
    home_ties INTEGER,
    away_wins INTEGER,
    away_losses INTEGER,
    away_ties INTEGER,
    home_goals_for INTEGER,
    home_goals_against INTEGER,
    away_goals_for INTEGER,
    away_goals_against INTEGER,

    PRIMARY KEY (team_id, season_id)
);

-- STRENGTH_OF_SCHEDULE: Advanced scheduling metrics
CREATE TABLE strength_of_schedule (
    team_id INTEGER,
    season_id TEXT,

    -- Basic SOS
    opponents_avg_points_pct REAL,  -- Average opponent strength
    sos_rank INTEGER,

    -- Adjusted SOS (2-degree)
    opponents_opponents_points_pct REAL,
    adjusted_sos REAL,  -- Weighted combination

    -- Strength of Victory
    beaten_teams_avg_points_pct REAL,
    sov_rank INTEGER,

    -- Games breakdown
    games_vs_top_third INTEGER,
    games_vs_middle_third INTEGER,
    games_vs_bottom_third INTEGER,
    points_vs_top_third INTEGER,
    points_vs_middle_third INTEGER,
    points_vs_bottom_third INTEGER,

    -- Rest analysis
    games_on_rest INTEGER,
    games_back_to_back INTEGER,
    rest_differential INTEGER,

    -- Travel (manual data if available)
    total_travel_distance REAL,
    avg_travel_per_game REAL,

    PRIMARY KEY (team_id, season_id)
);

-- HEAD_TO_HEAD: Team vs Team matchups
CREATE TABLE head_to_head (
    team1_id INTEGER,
    team2_id INTEGER,
    season_id TEXT,

    -- Overall record
    games_played INTEGER,
    team1_wins INTEGER,
    team1_losses INTEGER,
    team1_ties INTEGER,
    team1_points INTEGER,
    team1_points_pct REAL,

    -- Scoring
    team1_goals_for INTEGER,
    team1_goals_against INTEGER,
    goal_differential INTEGER,

    -- Special teams
    team1_pp_goals INTEGER,
    team1_pp_opportunities INTEGER,
    team1_pp_pct REAL,
    team1_pk_pct REAL,

    -- Recent trend
    last_5_record TEXT,
    team1_current_streak TEXT,

    PRIMARY KEY (team1_id, team2_id, season_id)
);

-- PLAYER_GAME_LOG: Individual game performances
CREATE TABLE player_game_log (
    player_id TEXT,
    game_id TEXT,
    team_id INTEGER,

    date DATE,
    opponent_team_id INTEGER,
    is_home_game BOOLEAN,

    -- Stats
    goals INTEGER,
    assists INTEGER,
    points INTEGER,
    pim INTEGER,
    plus_minus INTEGER,

    -- Special
    pp_goals INTEGER,
    sh_goals INTEGER,
    gwg INTEGER,

    -- Quality flags
    number_used TEXT,
    number_matches_usual BOOLEAN,

    PRIMARY KEY (player_id, game_id)
);

-- DATA_QUALITY_LOG: Track suspect data
CREATE TABLE data_quality_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Source
    entity_type TEXT,  -- 'goal', 'penalty', 'roster'
    entity_id TEXT,
    game_id TEXT,

    -- Issue
    issue_type TEXT,  -- 'wrong_number', 'missing_name', 'duplicate_player'
    issue_description TEXT,
    confidence_impact REAL,  -- How much it affects confidence score

    -- Resolution
    is_resolved BOOLEAN DEFAULT FALSE,
    resolution_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## **🔧 CALCULATION ENGINE**

### **Stats Calculation Order:**

```python
class AdvancedStatsCalculator:
    """Calculate all advanced metrics from raw data"""

    def calculate_all(self, season_id):
        """Run complete calculation pipeline"""

        # 1. Basic aggregations
        self.calculate_player_basic_stats(season_id)
        self.calculate_team_basic_stats(season_id)

        # 2. Period breakdowns
        self.calculate_goals_by_period(season_id)

        # 3. Special teams
        self.calculate_power_play_stats(season_id)
        self.calculate_penalty_kill_stats(season_id)

        # 4. Advanced metrics
        self.calculate_strength_of_schedule(season_id)
        self.calculate_head_to_head_records(season_id)
        self.calculate_home_away_splits(season_id)
        self.calculate_rest_differentials(season_id)

        # 5. Data quality
        self.assess_player_number_consistency(season_id)
        self.flag_data_quality_issues(season_id)

        # 6. Rankings
        self.calculate_all_rankings(season_id)
```

### **Example: Power Play % Calculation**

```python
def calculate_power_play_stats(self, season_id):
    """
    Calculate PP% for all teams

    Formula: PP% = (PP Goals / PP Opportunities) * 100

    PP Goals = Count goals where is_power_play = TRUE
    PP Opportunities = Count penalties against opponent
    """

    query = """
    SELECT
        g.team_id,
        g.team_name,
        COUNT(DISTINCT CASE WHEN goal.is_power_play THEN goal.id END) as pp_goals,
        COUNT(DISTINCT p.id) as opponent_penalties,
        CAST(COUNT(DISTINCT CASE WHEN goal.is_power_play THEN goal.id END) AS REAL) /
            NULLIF(COUNT(DISTINCT p.id), 0) * 100 as pp_pct
    FROM games g
    LEFT JOIN goals goal ON goal.game_id = g.game_id
        AND goal.team_id = g.home_team_id
    LEFT JOIN penalties p ON p.game_id = g.game_id
        AND p.team_id != g.home_team_id
    WHERE g.season_id = ?
        AND g.status = 'final'
    GROUP BY g.team_id
    """
```

### **Example: Strength of Schedule**

```python
def calculate_strength_of_schedule(self, season_id):
    """
    SOS = Average of opponents' points percentage
    Adjusted SOS = (Opp PTS% × 2/3) + (Opp's Opp PTS% × 1/3)
    """

    # Get all games
    # For each team, find their opponents
    # Calculate opponents' average points%
    # Calculate opponents' opponents' points%
    # Combine with weighting

    # Rank teams by SOS (higher = harder schedule)
```

---

## **🌐 REST API ENDPOINTS**

### **Base URL:** `http://localhost:5000/api/v1`

### **1. Season/Division Endpoints**

```
GET /seasons/{season_id}
→ Season info, divisions, teams count

GET /seasons/{season_id}/divisions
→ All divisions with team counts

GET /divisions/{division_id}/standings
→ Division standings with ALL calculated stats

GET /divisions/{division_id}/teams
→ All teams in division with basic info
```

### **2. Team Endpoints**

```
GET /teams/{team_id}
→ Complete team profile with all stats

GET /teams/{team_id}/stats
→ Full statistical breakdown:
  - Record (W-L-T, OTL, SOL, ROW, PTS, PTS%)
  - Scoring (GF, GA, +/-, by period)
  - Special teams (PP%, PK%)
  - Discipline (PIM, penalties)
  - Home/Away splits
  - Recent form (Last 10, streak)

GET /teams/{team_id}/schedule
→ All games (past & future) with results

GET /teams/{team_id}/roster
→ Current roster with player stats

GET /teams/{team_id}/sos
→ Strength of schedule analysis:
  - SOS rank
  - Adjusted SOS
  - SOV (Strength of Victory)
  - Games vs top/middle/bottom third
  - Rest differential

GET /teams/{team_id}/vs/{opponent_id}
→ Head-to-head record & stats

GET /teams/{team_id}/leaders
→ Team leaders in all categories
```

### **3. Player Endpoints**

```
GET /players/{player_id}
→ Complete player profile

GET /players/{player_id}/stats
→ Full stats including:
  - Basic (G, A, PTS, PPG)
  - Special teams (PPG, SHG, GWG)
  - Discipline (PIM, penalties)
  - Data quality score
  - Number consistency

GET /players/{player_id}/game-log
→ Game-by-game performance log

GET /players/{player_id}/goals
→ All goals with details (assists, time, type)

GET /players/{player_id}/penalties
→ All penalties with details

GET /players/search?number={num}&team={team_id}
→ Find player by jersey # and team
  ⚠️ Returns confidence score due to data accuracy issues
```

### **4. Game Endpoints**

```
GET /games/{game_id}
→ Complete game info

GET /games/{game_id}/boxscore
→ Full box score with:
  - Final score
  - Goals by period (with scorers, assists)
  - Penalties by period
  - Rosters with game stats

GET /games/{game_id}/goals
→ All goals in chronological order

GET /games/{game_id}/penalties
→ All penalties in chronological order

GET /games/{game_id}/summary
→ Game summary statistics
```

### **5. League-Wide Endpoints**

```
GET /seasons/{season_id}/leaders/points
→ League scoring leaders

GET /seasons/{season_id}/leaders/goals
→ Goal scoring leaders

GET /seasons/{season_id}/leaders/assists
→ Assist leaders

GET /seasons/{season_id}/leaders/pim
→ Penalty minute leaders

GET /seasons/{season_id}/leaders/goalies
→ Goalie leaders (GAA, SV%, Wins)

GET /seasons/{season_id}/teams/rankings
→ All teams ranked by various metrics:
  - Points%
  - Goal differential
  - PP%
  - PK%
  - SOS

GET /seasons/{season_id}/advanced-stats
→ League-wide advanced metrics dashboard
```

### **6. Cross-Reference Endpoints**

```
GET /cross-ref/player-vs-team
?player_id={pid}&vs_team={tid}
→ Player's performance vs specific team

GET /cross-ref/team-special-teams-matchup
?team1={t1}&team2={t2}
→ PP vs PK matchup analysis

GET /cross-ref/division-comparison
?div1={d1}&div2={d2}
→ Compare division strength

GET /cross-ref/player-number-lookup
?number={num}&team={tid}&game_date={date}
→ Find who wore # for team on date
  (Handles multiple players with same #)
```

### **7. Data Quality Endpoints**

```
GET /data-quality/issues
→ All flagged data quality issues

GET /data-quality/player/{player_id}
→ Data quality report for player:
  - Number consistency
  - Name variations
  - Confidence scores

GET /data-quality/game/{game_id}
→ Data quality for specific game
```

---

## **📤 EXAMPLE API RESPONSES**

### **Team Stats (Multi-View)**

```json
GET /teams/386299/stats

{
  "team_id": 386299,
  "team_name": "Duxbury U12B",
  "division": "U12B",
  "logo_url": "https://...",

  "record": {
    "games_played": 15,
    "wins": 10,
    "losses": 4,
    "ties": 1,
    "otw": 2,
    "otl": 1,
    "sow": 0,
    "sol": 0,
    "points": 23,
    "points_pct": 0.767,
    "row": 10,
    "division_rank": 2
  },

  "scoring": {
    "goals_for": 58,
    "goals_against": 32,
    "goal_differential": 26,
    "goals_per_game": 3.87,
    "goals_against_per_game": 2.13,

    "by_period": {
      "period_1": {"for": 18, "against": 10},
      "period_2": {"for": 24, "against": 12},
      "period_3": {"for": 16, "against": 10}
    }
  },

  "special_teams": {
    "power_play": {
      "goals": 12,
      "opportunities": 45,
      "percentage": 26.7,
      "rank_in_division": 3
    },
    "penalty_kill": {
      "goals_against": 8,
      "times_shorthanded": 38,
      "percentage": 78.9,
      "rank_in_division": 5
    },
    "short_handed_goals": 3,
    "short_handed_goals_against": 1
  },

  "discipline": {
    "penalty_minutes": 156,
    "pim_per_game": 10.4,
    "penalties_taken": 78,
    "major_penalties": 2,
    "game_misconducts": 0
  },

  "home_away": {
    "home": {
      "record": "6-1-1",
      "goals_for": 32,
      "goals_against": 15,
      "points": 13
    },
    "away": {
      "record": "4-3-0",
      "goals_for": 26,
      "goals_against": 17,
      "points": 10
    }
  },

  "recent_form": {
    "last_10": "7-2-1",
    "current_streak": "W3",
    "last_5_games": [
      {"date": "2025-11-05", "opponent": "WHK", "result": "W", "score": "5-3"},
      {"date": "2025-11-03", "opponent": "Canton", "result": "W", "score": "4-2"},
      {"date": "2025-10-30", "opponent": "Marshfield", "result": "W", "score": "3-1"},
      {"date": "2025-10-27", "opponent": "Plymouth", "result": "L", "score": "2-4"},
      {"date": "2025-10-25", "opponent": "Pembroke", "result": "T", "score": "3-3"}
    ]
  },

  "strength_of_schedule": {
    "sos": 0.523,
    "sos_rank": 4,
    "adjusted_sos": 0.518,
    "strength_of_victory": 0.556,
    "games_vs_top_third": 6,
    "points_vs_top_third": 7,
    "rest_differential": 2
  },

  "data_quality": {
    "games_with_complete_data": 14,
    "games_with_missing_data": 1,
    "overall_confidence": 0.93
  }
}
```

### **Player Stats with Data Quality**

```json
GET /players/5958147/stats

{
  "player_id": "5958147",
  "team_id": 386299,
  "team_name": "Duxbury U12B",

  "identity": {
    "player_number": "3",
    "player_name": "",
    "position": "",
    "number_variations": ["3"],  // All #s they've worn
    "number_consistency_score": 1.0,  // Always wore #3
    "name_available": false
  },

  "stats": {
    "games_played": 12,
    "goals": 8,
    "assists": 5,
    "points": 13,
    "points_per_game": 1.08,

    "special_teams": {
      "power_play_goals": 2,
      "power_play_assists": 1,
      "short_handed_goals": 1,
      "short_handed_assists": 0,
      "game_winning_goals": 2,
      "empty_net_goals": 0
    },

    "discipline": {
      "penalties": 8,
      "penalty_minutes": 16,
      "pim_per_game": 1.33,
      "major_penalties": 0
    }
  },

  "goal_details": [
    {
      "game_id": "2416969",
      "date": "2025-09-07",
      "opponent": "WHK",
      "period": "1ST Period",
      "time": "11:08",
      "assists": ["#12"],
      "type": ["EV"],
      "game_score": "7-4 W"
    },
    // ... more goals
  ],

  "penalty_log": [
    {
      "game_id": "2416969",
      "date": "2025-09-07",
      "period": "2ND Period",
      "time": "07:41",
      "penalty_type": "Roughing - Minor",
      "duration": 2
    },
    // ... more penalties
  ],

  "data_quality": {
    "confidence_score": 0.95,
    "issues": [],
    "notes": "Player # consistent across all games"
  }
}
```

### **Cross-Reference: Head-to-Head**

```json
GET /teams/386299/vs/386305

{
  "team1": {
    "id": 386299,
    "name": "Duxbury U12B"
  },
  "team2": {
    "id": 386305,
    "name": "WHK"
  },

  "all_time": {
    "games_played": 3,
    "duxbury_record": "2-1-0",
    "duxbury_points": 4,
    "duxbury_points_pct": 0.667,
    "goals_for": 14,
    "goals_against": 11,
    "goal_differential": 3
  },

  "games": [
    {
      "game_id": "2416969",
      "date": "2025-09-07",
      "location": "Armstrong",
      "result": "Duxbury 7, WHK 4",
      "duxbury_scorers": ["#3 (2G)", "#41 (2G)", "#12 (1G)", "#14 (1G)", "#87 (1G)"],
      "whk_scorers": ["#71 (3G)", "#97 (1G)"]
    },
    // ... more games
  ],

  "special_teams_matchup": {
    "duxbury_pp_vs_whk_pk": {
      "duxbury_pp_pct": 25.0,
      "whk_pk_pct": 75.0,
      "edge": "WHK"
    },
    "whk_pp_vs_duxbury_pk": {
      "whk_pp_pct": 33.3,
      "duxbury_pk_pct": 66.7,
      "edge": "Duxbury"
    }
  },

  "player_performance_vs_opponent": [
    {
      "player_id": "5958147",
      "number": "3",
      "team": "Duxbury",
      "games": 3,
      "goals": 4,
      "assists": 2,
      "points": 6,
      "pim": 6
    },
    // ... more players
  ]
}
```

---

## **🤖 LLM-FRIENDLY FEATURES**

### **1. Context-Rich Responses**

Every API response includes:
- Human-readable descriptions
- Rank/percentile context
- League averages for comparison
- Interpretation hints

```json
{
  "stat": "power_play_percentage",
  "value": 26.7,
  "rank_in_division": 3,
  "division_average": 22.1,
  "percentile": 75,
  "interpretation": "Above average - Top 25% in division",
  "context": "3rd best power play out of 8 teams"
}
```

### **2. Bulk Export Endpoints**

```
GET /seasons/{season_id}/export/full-dataset
→ Complete season dump (all tables) as JSON

GET /divisions/{division_id}/export/stats-package
→ Everything for a division
```

### **3. Natural Language Query Support**

```
GET /query?q=top+5+scorers+in+u12b
→ Interprets and routes to appropriate endpoint

GET /query?q=duxbury+power+play+stats
→ Returns team special teams data
```

---

## **⚡ IMPLEMENTATION STACK**

```
FastAPI (REST API)
├── SQLite database (stats.db)
├── Python calculation engine
├── Scheduled refresh (cron job)
└── Data quality monitor

Tech Stack:
- FastAPI (async Python web framework)
- SQLAlchemy (ORM)
- Pandas (data manipulation)
- APScheduler (automated updates)
- Pydantic (data validation)
```

---

## **🔄 UPDATE STRATEGY**

```python
# Automated refresh schedule
@scheduler.scheduled_job('cron', hour=2)  # 2 AM daily
def refresh_stats():
    """Nightly stats update"""

    # 1. Extract new box scores
    extract_new_games()

    # 2. Recalculate all stats
    calculator.calculate_all(season_id)

    # 3. Update rankings
    update_all_rankings()

    # 4. Check data quality
    run_quality_checks()
```

---

This architecture gives you:
✅ **Complete data extraction** (even suspect #s)
✅ **Rich cross-referencing** (team vs team, player vs team, etc.)
✅ **Multiple views** (team-centric, player-centric, division-wide)
✅ **Data quality tracking** (confidence scores, issue logging)
✅ **LLM-friendly** (context-rich, bulk exports, natural language queries)
✅ **Scalable** (add new calculated stats easily)

Want me to start building the calculation engine or API server?
