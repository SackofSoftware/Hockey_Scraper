# GameSheet API Complete Documentation

**Base URL:** `https://gamesheetstats.com/api`

**Date:** 2025-11-08

This document provides a comprehensive breakdown of ALL discovered GameSheet API endpoints and the data they provide across season, division, team, game, and player levels.

---

## **SEASON-LEVEL APIs** ✅

### 1. Get Season Information
```
GET /useSeasonDivisions/getSeason/{season_id}
```

**Example:** `/useSeasonDivisions/getSeason/10776`

**Returns:**
- `id`: Season ID
- `title`: Season name (e.g., "Bay State Hockey League - 2025-26")
- `sport`: Sport type ("hockey")
- `associationTitle`: Governing body (e.g., "USAH - Massachusetts District")
- `assistValue`, `goalValue`: Scoring system values
- `maxGoalDifferential`: Max goal diff tracking
- `playerStatsDisplay`: Boolean flag
- `fppEnabled`: Fair Play Points enabled
- `penaltyCodes[]`: **Complete penalty code reference** (100+ penalty types)
  - `code`: Penalty code (e.g., "INT-MIN")
  - `label`: Full description (e.g., "Interference - Minor")
  - `duration`: Minutes (2, 5, 10)
  - `penalty_class`: "minor", "major", "misconduct", "game_misconduct", "match"

---

## **DIVISION-LEVEL APIs** ✅

### 2. Get All Divisions
```
GET /useSeasonDivisions/getDivisions/{season_id}
```

**Example:** `/useSeasonDivisions/getDivisions/10776`

**Returns:** Array of divisions with:
- `id`: Division ID
- `title`: Division name (e.g., "U12B", "HIGH SCHOOL - JV")
- `assistValue`, `goalValue`: Scoring values
- `playerStatsDisplay`: Boolean
- `maxGoalDifferential`: Number
- `fppEnabled`: Boolean

---

### 3. Get Division Standings (WITH TEAM STATS)
```
GET /useStandings/getDivisionStandings/{season_id}?filter[divisions]={div_ids}&filter[limit]={limit}&filter[offset]={offset}&filter[timeZoneOffset]={tz}
```

**Example:**
```
/useStandings/getDivisionStandings/10776?filter[divisions]=60040,60042,60041&filter[limit]=100&filter[offset]=0&filter[timeZoneOffset]=-240
```

**Returns:** Array of divisions, each containing `tableData` with parallel arrays for all teams:

**Team Identity:**
- `teamIds[]`: Team IDs
- `teamTitles[]`: Team objects with `{title, id}`
- `teamLogos[]`: Logo URLs
- `ranks[]`: Current standings position

**Record & Points:**
- `gp[]`: Games Played
- `w[]`: Wins
- `l[]`: Losses
- `t[]`: Ties
- `otw[]`: Overtime Wins
- `otl[]`: Overtime Losses
- `sow[]`: Shootout Wins
- `sol[]`: Shootout Losses
- `rw[]`: Regulation Wins
- `row[]`: Regulation + OT Wins (excludes SO wins)
- `pts[]`: Total Points
- `ppct[]`: Points Percentage

**Scoring:**
- `gf[]`: Goals For
- `ga[]`: Goals Against
- `diff[]`: Goal Differential (GF - GA)

**Special Teams:**
- `ppg[]`: Power Play Goals
- `ppo[]`: Power Play Opportunities
- `ppp[]`: Power Play Percentage
- `ppga[]`: Power Play Goals Against
- `shg[]`: Short-Handed Goals
- `shga[]`: Short-Handed Goals Against
- `pkp[]`: Penalty Kill Percentage
- `tsh[]`: Total Shots

**Discipline:**
- `pim[]`: Penalty Minutes
- `yc[]`: Yellow Cards
- `rc[]`: Red Cards

**Recent Form:**
- `p10[]`: Last 10 games record (e.g., "5-4-1")
- `stk[]`: Current streak (e.g., "W2", "L1")

**Other:**
- `fpp[]`: Fair Play Points
- `statRankReason[]`: Ranking methodology explanation

---

### 4. Get Division Schedule
```
GET /useSchedule/getSeasonSchedule/{season_id}?filter[divisions]={div_ids}&filter[gametype]={type}&filter[limit]={limit}&filter[offset]={offset}&filter[start]={date}&filter[timeZoneOffset]={tz}
```

**Example:**
```
/useSchedule/getSeasonSchedule/10776?filter[divisions]=60040,60042,60041&filter[gametype]=overall&filter[limit]=10&filter[offset]=0&filter[start]=2025-09-04&filter[timeZoneOffset]=-240
```

**Parameters:**
- `filter[gametype]`: "overall", "regular_season", "playoffs"
- `filter[limit]`: Results per page (default 10)
- `filter[offset]`: Pagination offset
- `filter[start]`: Start date (YYYY-MM-DD)

**Returns:** Paginated schedule grouped by offset keys (e.g., "10_0")

Each day group contains:
- `date`: "Sat, Sep 6, 2025 - 2 Games"
- `games[]`: Array of game objects:
  - `id`: Game ID (e.g., "2416955")
  - `number`: Game number (e.g., "8000031")
  - `scheduleStartTime`: ISO timestamp
  - `status`: "scheduled", "in_progress", "final"
  - `time`: Formatted time (e.g., "6:50 PM")
  - `date`: Formatted date
  - `location`: Venue name
  - `type`: "Regular Season", "Playoff"
  - `broadcaster`: Streaming info (usually empty)
  - `homeTeam`:
    - `id`: Team ID
    - `name`: Team name
    - `logo`: Logo URL
    - `division`: Division name
  - `visitorTeam`: (same structure as homeTeam)

---

## **TEAM-LEVEL APIs** ⚠️

### 5. Get Team Roster (EMPTY FOR CURRENT SEASON)
```
GET /useRoster/getTeamRoster/{team_id}  [404 - endpoint not confirmed]
```

**Status:** Structure exists in data but endpoint pattern unclear. Roster data appears in box scores instead.

**Expected Structure (from box score data):**
```json
{
  "playerData": {
    "names[]": [...],
    "ids[]": [...],
    "jersey[]": [...],
    "positions[]": [...],
    "gp[]": [...],  // Games Played
    "g[]": [...],   // Goals
    "a[]": [...],   // Assists
    "pts[]": [...], // Points
    "ppg[]": [...], // Power Play Goals
    "ppa[]": [...], // Power Play Assists
    "shg[]": [...], // Short-Handed Goals
    "sha[]": [...], // Short-Handed Assists
    "pim[]": [...], // Penalty Minutes
    "birthdate[]": [...],
    "height[]": [...],
    "weight[]": [...],
    "shotHand[]": [...],
    "hometown[]": [...]
  },
  "goalieData": {
    "names[]": [...],
    "gp[]": [...], // Games Played
    "gs[]": [...], // Games Started
    "sa[]": [...], // Shots Against
    "ga[]": [...], // Goals Against
    "gaa[]": [...], // Goals Against Average
    "svPct[]": [...], // Save Percentage
    "so[]": [...], // Shutouts
    "min[]": [...], // Minutes
    "wins[]": [...],
    "losses[]": [...],
    "ties[]": [...],
    ...
  },
  "coachData": {
    "names[]": [...],
    "positions[]": [...]
  }
}
```

---

## **GAME-LEVEL APIs** ✅

### 6. Get Game Box Score (COMPREHENSIVE GAME DETAILS)
```
GET /useBoxScore/getGameStats/{season_id}/games/{game_id}
```

**Example:** `/useBoxScore/getGameStats/10776/games/2416969`

**Returns:** Complete box score with ALL game details:

#### **Game Information:**
```json
{
  "liveId": "",
  "gameId": "",
  "gameNumber": "Game 8000045",
  "gameType": "Regular Season",
  "date": "Sep 7, 2025, 5:00 PM",
  "location": "Armstrong",
  "gameStatus": "Final",  // "Scheduled", "In Progress", "Final"
  "attendance": null,
  "periods": {
    "1": 13,  // Period length in minutes
    "2": 13,
    "3": 14,
    "OT1": 10
  }
}
```

#### **Team Information:**
```json
{
  "home": {
    "id": 386305,
    "title": "WHK",
    "division": "U12B",
    "record": "6-2-1",
    "logo": "https://...",
    "finalScore": "4",
    "sog": 0  // Shots on Goal (often not tracked)
  },
  "visitor": {
    // Same structure as home
  }
}
```

#### **Complete Roster (IN-GAME):**
```json
{
  "home": {
    "roster": {
      "players": [
        {
          "id": "5901630",          // Player ID
          "firstName": "",          // Usually empty (privacy)
          "lastName": "",           // Usually empty (privacy)
          "number": "11",           // Jersey number
          "position": "",           // Position (often empty)
          "status": "playing",      // "playing", "scratched", "injured"
          "duty": "",               // Captain, alternate, etc.
          "affiliated": false,      // Affiliate player flag
          "added_at_game_time": false,
          "starting": false,        // Starting lineup

          // Game Stats
          "g": 0,                   // Goals
          "a": 0,                   // Assists
          "pts": 0,                 // Points
          "pim": 2,                 // Penalty Minutes
          "yc": 0,                  // Yellow Cards
          "rc": 0,                  // Red Cards

          // Goalie Stats (if goalie)
          "ga": null,               // Goals Against
          "sa": null,               // Shots Against
          "svpct": null,            // Save %
          "toi": null,              // Time on Ice

          // Season Totals (cumulative)
          "season": {
            "goals": 0,
            "assists": 0
          }
        }
      ],
      "coaches": [
        {
          "id": "1348173",
          "firstName": "JOSEPH",
          "lastName": "DEVINE",
          "position": "assistant_coach",  // "head_coach", "assistant_coach"
          "status": "coaching",
          "signature": ""  // Digital signature URL
        }
      ]
    }
  }
}
```

#### **Goals by Period:**
```json
{
  "tables": {
    "goalsByPeriod": [
      {
        "period": "1ST Period",
        "type": "goals",
        "periodEvents": [
          {
            "eventType": "goal",
            "time": "11:08",
            "period": "1",
            "homeTeam": false,        // true if home team scored
            "powerPlay": false,       // PP goal
            "gameWinningGoal": false, // GWG
            "shg": true,              // Short-handed goal
            "en": false,              // Empty net goal
            "plus": [],               // Players on ice (plus)
            "minus": [],              // Players on ice (minus)

            // Goal Scorer
            "goalScorer": {
              "id": "5958147",         // Player ID
              "title": " ",            // Name (usually empty)
              "number": "41",          // Jersey number
              "trackingNumber": "1",   // Goal count this game
              "totalGoalCount": "1"    // Season goal count
            },

            // Primary Assist
            "assist1By": {
              "id": "5958138",
              "title": " ",
              "number": "12",
              "trackingNumber": "1",
              "totalGoalCount": "1"  // Their goal count
            },

            // Secondary Assist (optional)
            "assist2By": {
              "id": "",
              "title": "",
              "number": ""
            },

            // Team Info
            "team": {
              "id": 386299,
              "title": "Duxbury U12B",
              "logo": "https://..."
            }
          }
        ]
      }
    ]
  }
}
```

#### **Penalties by Period:**
```json
{
  "tables": {
    "penaltiesByPeriod": [
      {
        "period": "1ST Period",
        "type": "penalty",
        "periodEvents": [
          {
            "eventType": "penalty",
            "time": "03:46",
            "period": "1",
            "homeTeam": false,
            "major": false,

            // Player Who Committed Penalty
            "commitedBy": {
              "type": "players",
              "id": "5958143",
              "title": " ",
              "number": "5"
            },

            // Player Serving Penalty (if different)
            "servedBy": {
              "id": "",
              "title": " ",
              "number": "5"
            },

            // Penalty Details
            "penaltyType": {
              "title": "Interference - Minor",
              "duration": "2",       // Minutes
              "class": "minor"       // "minor", "major", "misconduct", "game_misconduct", "match"
            },

            // Team Info
            "team": {
              "id": 386299,
              "title": "Duxbury U12B",
              "logo": "https://..."
            }
          }
        ]
      }
    ]
  }
}
```

---

## **PLAYER-LEVEL APIs** ❌

### 7. Player Stats by Division
```
GET /usePlayerStats/getDivisionPlayerStats/{season_id}?filter[divisions]={div_id}&filter[limit]={limit}&filter[offset]={offset}
```

**Status:** Returns 404. Player stats only available aggregated through box scores.

---

### 8. Goalie Stats
```
GET /useGoalieStats/getGoalieStats/{season_id}?filter[limit]={limit}&filter[offset]={offset}
```

**Status:** Returns 404. Goalie stats only available through box scores.

---

## **DATA AVAILABILITY SUMMARY**

| Level | Endpoint | Status | Data Quality |
|-------|----------|--------|--------------|
| **Season** | `getSeason` | ✅ Working | Complete |
| **Division List** | `getDivisions` | ✅ Working | Complete |
| **Division Standings** | `getDivisionStandings` | ✅ Working | **Complete - ALL team stats** |
| **Division Schedule** | `getSeasonSchedule` | ✅ Working | Complete |
| **Game Box Score** | `getGameStats` | ✅ Working | **Complete - Goals, penalties, rosters, player IDs** |
| **Team Roster** | `getTeamRoster` | ❌ Not Found | Structure exists, endpoint unclear |
| **Player Stats** | `getPlayerStats` | ❌ 404 | Must aggregate from box scores |
| **Goalie Stats** | `getGoalieStats` | ❌ 404 | Must aggregate from box scores |

---

## **CALCULATING ADVANCED STATS FROM AVAILABLE DATA**

Based on the available APIs, here's what CAN be calculated:

### ✅ **Available from Standings API:**
- GP, W, L, T, OTW, OTL, SOW, SOL, RW, ROW
- PTS, PTS%
- GF, GA, Goal Differential (+/-)
- PPG, PPO, PP%
- PPGA, SHG, SHGA, PK%
- TSH (Total Shots - often 0)
- PIM, YC, RC
- P10 (Last 10 record)
- STK (Current streak)

### ✅ **Available from Box Scores:**
- **Player-level:**
  - G, A, PTS (goals, assists, points)
  - PIM (penalty minutes)
  - PPG, SHG (power play goals, short-handed goals)
  - GWG (game-winning goals)
  - Penalty details (type, class, duration, time, period)
  - Goal details (time, period, assists, type)

- **Team-level (aggregated):**
  - W-L-T record
  - GF, GA per game
  - Goals by period
  - Penalties by period
  - Special teams effectiveness (PP goals, SH goals)

### ⚠️ **Limited/Not Available:**
- **Shots on Goal** (SOG) - Field exists but often shows 0
- **Faceoff Stats** (FO, FO%)
- **Hits, Blocked Shots, Takeaways, Giveaways**
- **Corsi, Fenwick** (advanced possession metrics)
- **Expected Goals (xG, xGA)**
- **Time on Ice (TOI)** - Field exists but often null

### ✅ **CAN Calculate with Data Munging:**
- **PDO** = (Team S% + Team SV%) × 10 *[if SOG data available]*
- **S%** (Shooting %) = Goals / SOG *[if SOG tracked]*
- **SV%** (Save %) = (SA - GA) / SA *[if SA tracked]*
- **Strength of Schedule (SOS)** = Average opponents' PTS%
- **Head-to-Head Records** - Extract from box scores
- **Rest Differentials** - Calculate from schedule dates
- **Home/Away Splits** - Parse from game data
- **Goals For/Against by Period** - Aggregate from box scores
- **Player Points Per Game (PPG)** = Total Points / GP
- **Player +/-** - Track from box score "plus/minus" arrays (often empty)

---

## **PRACTICAL USAGE EXAMPLES**

### Get Complete Season Data:
```python
season_id = "10776"

# 1. Get season info and penalty codes
season = GET f"/useSeasonDivisions/getSeason/{season_id}"

# 2. Get all divisions
divisions = GET f"/useSeasonDivisions/getDivisions/{season_id}"

# 3. For each division, get standings (team stats)
for div in divisions:
    standings = GET f"/useStandings/getDivisionStandings/{season_id}?filter[divisions]={div['id']}"

# 4. Get full schedule (paginated)
offset = 0
while True:
    schedule = GET f"/useSchedule/getSeasonSchedule/{season_id}?filter[divisions]={div_ids}&filter[offset]={offset}&filter[limit]=100"
    if not schedule:
        break
    offset += 100

# 5. For each completed game, get box score
for game in completed_games:
    box_score = GET f"/useBoxScore/getGameStats/{season_id}/games/{game['id']}"
    # Extract goals, penalties, player stats
```

---

## **NOTES ON DATA QUALITY**

### Player Names:
- **Privacy Protection:** Player names often return as empty strings `" "` or single spaces
- **Jersey Numbers:** Always reliable identifier
- **Player IDs:** Unique and consistent across games/seasons
- **Recommendation:** Use combination of `player_id` + `number` + `team_id` for tracking

### Youth League Data Quality:
- **Inconsistent Entry:** User mentioned kids/refs enter data at rink, leading to errors
- **Wrong Jersey Numbers:** Players may be credited with wrong #
- **Missing Data:** Assists sometimes not recorded
- **Shots on Goal:** Often shows 0 (not tracked consistently)

### Completeness:
- **Completed Games Only:** Box scores only available for games with "Final" status
- **Future Games:** Schedule shows upcoming games but no stats
- **Real-time:** Games may show "In Progress" with partial data

---

## **CONCLUSION**

The GameSheet API provides:
- ✅ **Excellent** season/division organization
- ✅ **Comprehensive** team-level standings with all standard stats
- ✅ **Complete** game schedules with team info
- ✅ **Detailed** box scores with player-by-player goal/penalty tracking
- ⚠️ **Limited** shot tracking and advanced possession metrics
- ❌ **No direct** player/goalie leaderboard endpoints (must aggregate manually)

**Best Approach for Advanced Stats:**
1. Extract all box scores for completed games
2. Aggregate player stats manually from goals/penalties/roster data
3. Calculate team stats from game results
4. Cross-reference with standings API for validation
5. Build custom endpoints with calculated advanced metrics
