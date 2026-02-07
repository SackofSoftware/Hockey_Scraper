# Hockey Stats API Endpoints

## Core Stats Endpoints

### Standings & Team Stats
```
GET /api/v1/leagues/{league_id}/seasons/{season_id}/standings
GET /api/v1/teams/{team_id}/stats
GET /api/v1/divisions/{division_id}/standings
```

**Returns**: GP, W, L, OTL, PTS, PTS%, ROW, GF, GA, +/-, PP%, PK%, home/away splits

### Games
```
GET /api/v1/games/{game_id}
GET /api/v1/teams/{team_id}/games
GET /api/v1/teams/{team_id}/schedule
```

**Returns**: Game details, scores, status, date/time

### Player Stats
```
GET /api/v1/players/{player_id}/stats
GET /api/v1/teams/{team_id}/players
GET /api/v1/teams/{team_id}/leaders?stat=goals
```

**Returns**: Goals, assists, points, PIM, PPG, SHG, GWG

### Box Scores
```
GET /api/v1/games/{game_id}/boxscore
GET /api/v1/games/{game_id}/goals
GET /api/v1/games/{game_id}/penalties
GET /api/v1/games/{game_id}/rosters
```

**Returns**: Period-by-period scoring, player numbers, goal details, penalty details

---

## Advanced Metrics Endpoints

### Strength of Schedule
```
GET /api/v1/teams/{team_id}/sos
GET /api/v1/divisions/{division_id}/sos-rankings
```

**Returns**:
- `opponents_avg_points_pct` - Average opponent PTS%
- `sos_rank` - Division rank by SOS (1 = hardest)
- `adjusted_sos` - 2-degree SOS (includes opp's opponents)
- `opponents_opponents_points_pct` - Indirect schedule difficulty
- `beaten_teams_avg_points_pct` - Strength of Victory (SOV)
- `sov_rank` - Division rank by SOV
- `games_vs_top_third` - Games vs top tier teams
- `games_vs_middle_third` - Games vs mid tier teams
- `games_vs_bottom_third` - Games vs bottom tier teams
- `points_vs_top_third` - Points earned vs top tier
- `points_vs_middle_third` - Points earned vs mid tier
- `points_vs_bottom_third` - Points earned vs bottom tier
- `games_on_rest` - Games with 2+ days rest
- `games_back_to_back` - Back-to-back games
- `rest_differential` - Games on rest minus B2B

**Example**:
```json
{
  "team_id": 386151,
  "team_name": "WHK",
  "season_id": "10776",
  "sos": 0.548,
  "sos_rank": 3,
  "adjusted_sos": 0.542,
  "sov": 0.456,
  "sov_rank": 8,
  "games_vs_top_third": 8,
  "points_vs_top_third": 6,
  "games_back_to_back": 4,
  "rest_differential": 2
}
```

### Head-to-Head Records
```
GET /api/v1/teams/{team1_id}/vs/{team2_id}
GET /api/v1/teams/{team_id}/matchups
```

**Returns**:
- `games_played` - Total games between teams
- `team1_wins`, `team1_losses`, `team1_ties`
- `team1_points` - Total points earned
- `team1_points_pct` - Points percentage in matchup
- `team1_goals_for`, `team1_goals_against`
- `goal_differential` - GF - GA in matchup
- `team1_pp_goals`, `team1_pp_opportunities`, `team1_pp_pct`
- `team1_pk_pct` - Penalty kill %
- `last_5_record` - Record in last 5 meetings
- `team1_current_streak` - Current streak vs opponent

**Example**:
```json
{
  "team1": "WHK",
  "team2": "Hingham",
  "games_played": 4,
  "record": "2-1-1",
  "points_pct": 0.625,
  "goal_differential": +3,
  "pp_pct": 22.5,
  "last_5_record": "2-1-1",
  "current_streak": "W1"
}
```

### Recent Form & Trends
```
GET /api/v1/teams/{team_id}/form
GET /api/v1/teams/{team_id}/streaks
```

**Returns** (from `team_stats`):
- `last_10_record` - Record in last 10 games (e.g., "6-3-1")
- `current_streak` - Active streak (e.g., "W3", "L1")
- `home_record` - Home W-L-T
- `away_record` - Away W-L-T

---

## Composite Metrics Endpoints

### Division Power Rankings
```
GET /api/v1/divisions/{division_id}/power-rankings
GET /api/v1/divisions/{division_id}/rpi
```

**Calculated Metrics**:
- **RPI** (Rating Percentage Index)
  - Formula: `(0.25 × Team PTS%) + (0.50 × Opp PTS%) + (0.25 × Opp Opp PTS%)`
  - Composite strength metric

- **HPI** (Hockey Power Index)
  - Formula: `(0.4 × PTS%) + (0.3 × GF/GA Ratio) + (0.2 × SOS) + (0.1 × Last10%)`
  - Blended power ranking

- **Momentum Index**
  - Formula: `(Last10% × 0.6) + (Goal Diff × 0.4)`
  - Recent success + scoring dominance

- **Clutch Index**
  - Formula: `Wins in 1-goal games ÷ Total 1-goal games`
  - Ability to perform under pressure

- **Efficiency Index**
  - Formula: `PTS ÷ GF`
  - Points earned per goal scored

- **Consistency Index**
  - Formula: `1 - (Std Dev of GF/GA per game)`
  - Lower variance = more consistent

**Example**:
```json
{
  "team_id": 386151,
  "team_name": "WHK",
  "rpi": 0.612,
  "hpi": 0.687,
  "momentum_index": 0.723,
  "clutch_index": 0.667,
  "efficiency_index": 0.385,
  "consistency_index": 0.842
}
```

### Game Context
```
GET /api/v1/games/{game_id}/context
```

**Returns**:
- `home_rest_days` - Days since home team's last game
- `visitor_rest_days` - Days since visitor's last game
- `home_back_to_back` - Boolean
- `visitor_back_to_back` - Boolean
- `margin` - Final score margin
- `is_one_goal_game` - Boolean
- `is_overtime` - Boolean

---

## Query Parameters

All endpoints support filtering and sorting:

### Filters
```
?season_id=10776
?division_id=60037
?team_id=386151
?status=complete
?date_from=2025-01-01
?date_to=2025-03-01
?club_name=WHK
```

### Sorting
```
?sort_by=points_pct
?sort_by=sos
?sort_by=hpi
?order=desc
```

### Pagination
```
?page=1
?per_page=25
?limit=100
```

---

## Club Data API (SSC Member Organizations)

Club data comes from scraping SportsEngine and other club websites. It includes
team rosters, coaches, board members, and contact info that isn't in GameSheet.

### List All Clubs
```
GET /api/v1/clubs
```

**Returns**: Array of `ClubBasic`
- `id`, `club_name`, `club_slug`, `website_url`
- `abbreviation`, `town`, `conference`
- `last_scraped` timestamp

### Search Clubs
```
GET /api/v1/clubs/search/{query}
```

**Returns**: Clubs matching by name, abbreviation, or town

### Club Detail
```
GET /api/v1/clubs/{club_id}
```

**Returns**: `ClubDetail` with entity counts
- Club info plus `team_count`, `player_count`, `coach_count`, `board_member_count`, `contact_count`, `game_count`

### Club Teams
```
GET /api/v1/clubs/{club_id}/teams
GET /api/v1/clubs/{club_id}/teams/{team_id}
```

**Returns**:
- List: Array of `ClubTeamBasic` (id, team_name, age_group, division_level, season)
- Detail: `ClubTeamWithRoster` including players and coaches for that team

### Club Players
```
GET /api/v1/clubs/{club_id}/players?team_id={optional}
```

**Returns**: Array of `ClubPlayerBasic`
- `first_name`, `last_name`, `jersey_number`, `position`
- `team_name`, `team_id` (which club team they're on)
- `gamesheet_player_id` (if reconciled to GameSheet data)

### Search All Club Players
```
GET /api/v1/clubs/player-search?query=Smith&club_name=WHK
```

**Parameters**:
- `query` (required): Name to search
- `club_name` (optional): Filter to specific club

**Returns**: Players matching across all clubs with club context

### Club Coaches
```
GET /api/v1/clubs/{club_id}/coaches
```

**Returns**: Array of `ClubCoachInfo`
- `name`, `role`, `email`, `phone`
- `team_name` (which team they coach)

### Board Members
```
GET /api/v1/clubs/{club_id}/board
```

**Returns**: Array of `ClubBoardMemberInfo`
- `name`, `title`, `email`, `phone`, `is_active`

### Club Contacts
```
GET /api/v1/clubs/{club_id}/contacts
```

**Returns**: Array of `ClubContactInfo`
- `contact_type`, `value`, `context`

### Club Games/Schedule
```
GET /api/v1/clubs/{club_id}/games?team_id={optional}&status={optional}
```

**Parameters**:
- `team_id`: Filter to specific team
- `status`: `scheduled`, `complete`, or `all`

**Returns**: Array of `ClubGameInfo`
- `date`, `time`, `opponent`, `home_away`
- `our_score`, `opponent_score`, `status`
- `gamesheet_game_id` (if reconciled)

---

## Club Tables

- `clubs` - SSC member organizations
- `club_teams` - Teams within clubs (with `gamesheet_team_id` link)
- `club_players` - Roster players (with `gamesheet_player_id` link)
- `club_coaches` - Coaching staff
- `club_board_members` - Club leadership
- `club_games` - Schedule/results (with `gamesheet_game_id` link)
- `club_contacts` - Contact information

---

## Database Tables

### Core Tables
- `teams` - Team info, normalized club names
- `divisions` - Division info
- `games` - All games with scores, status
- `goals` - Goal events with scorer, assists, time
- `penalties` - Penalty events with player, type, duration
- `game_rosters` - Per-game player rosters
- `player_stats` - Aggregated player stats
- `team_stats` - Aggregated team stats

### Advanced Metrics Tables
- `strength_of_schedule` - SOS, SOV, rest differential
- `head_to_head` - All team-vs-team records
- `game_context` - Rest days, B2B flags, game context

---

## Example Queries

### Get team's toughest opponents
```sql
SELECT h2h.team2_id, t.team_name, h2h.team1_points_pct, h2h.goal_differential
FROM head_to_head h2h
JOIN teams t ON t.team_id = h2h.team2_id
WHERE h2h.team1_id = 386151  -- WHK
  AND h2h.season_id = '10776'
ORDER BY h2h.team1_points_pct ASC
LIMIT 5;
```

### Get teams with hardest schedules
```sql
SELECT t.team_name, sos.opponents_avg_points_pct, sos.sos_rank,
       sos.games_vs_top_third, sos.beaten_teams_avg_points_pct
FROM strength_of_schedule sos
JOIN teams t ON t.team_id = sos.team_id
WHERE sos.season_id = '10776'
ORDER BY sos.opponents_avg_points_pct DESC
LIMIT 10;
```

### Get clutch teams (best in 1-goal games)
```sql
SELECT t.team_name,
       SUM(CASE WHEN ABS(g.home_score - g.visitor_score) = 1 THEN 1 ELSE 0 END) as one_goal_games,
       SUM(CASE
           WHEN ABS(g.home_score - g.visitor_score) = 1
             AND ((g.home_team_id = t.team_id AND g.home_score > g.visitor_score)
               OR (g.visitor_team_id = t.team_id AND g.visitor_score > g.home_score))
           THEN 1 ELSE 0 END) as one_goal_wins,
       CAST(SUM(CASE
           WHEN ABS(g.home_score - g.visitor_score) = 1
             AND ((g.home_team_id = t.team_id AND g.home_score > g.visitor_score)
               OR (g.visitor_team_id = t.team_id AND g.visitor_score > g.home_score))
           THEN 1 ELSE 0 END) AS REAL) /
       SUM(CASE WHEN ABS(g.home_score - g.visitor_score) = 1 THEN 1 ELSE 0 END) as clutch_pct
FROM teams t
JOIN games g ON (g.home_team_id = t.team_id OR g.visitor_team_id = t.team_id)
WHERE g.status = 'complete' AND g.season_id = '10776'
GROUP BY t.team_id, t.team_name
HAVING one_goal_games >= 5
ORDER BY clutch_pct DESC;
```

### Get teams on hot streaks
```sql
SELECT t.team_name, ts.current_streak, ts.last_10_record, ts.points_pct
FROM team_stats ts
JOIN teams t ON t.team_id = ts.team_id
WHERE ts.season_id = '10776'
  AND ts.current_streak LIKE 'W%'
ORDER BY CAST(SUBSTR(ts.current_streak, 2) AS INTEGER) DESC;
```

---

## Metrics We Can Calculate

✅ **Have Data For**:
- Core standings (GP, W, L, OTL, PTS, ROW, GF, GA)
- Special teams (PP%, PK%, PPG, PPGA, SHG)
- Shooting stats (Shots, S%, SV%, PDO)
- Home/Away splits
- Period-by-period scoring
- SOS, SOV, RPI, HPI
- Head-to-head records
- Rest differential
- Recent form (Last 10, streaks)
- Clutch performance (1-goal games)
- Momentum, Efficiency, Discipline metrics

❌ **Missing Data** (Not in GameSheet API):
- Corsi/Fenwick (shot attempts)
- Expected Goals (xG) - needs shot location
- High Danger Chances - needs shot quality
- Faceoff Win % - not tracked
- Blocked shots - not tracked
- Hit/takeaway/giveaway stats

---

## Implementation Status

- ✅ **Database Schema**: All tables created (GameSheet + Club data)
- ✅ **Data Import**: GameSheet API integration complete
- ✅ **Basic Stats**: Calculated automatically
- ✅ **Advanced Metrics**: SOS, H2H, streaks calculated
- ✅ **Team Normalization**: Club names normalized
- ✅ **Smart Updates**: Time-aware scheduling
- ✅ **REST API**: FastAPI server with 40+ endpoints
- ✅ **Club Scraping**: 6 platform scrapers (SportsEngine, Crossbar, LeagueApps, Angular, MRYHA, Providence)
- ✅ **Club API**: 11 endpoints for club data
- ✅ **Reconciliation**: Links club data ↔ GameSheet data

### Platform Support

| Platform | Scraper | Rosters | Coaches | Board |
|----------|---------|---------|---------|-------|
| SportsEngine | ✅ | ✅ | ✅ | ✅ |
| Crossbar | ✅ | ❌ (login-gated) | ✅ | ✅ |
| LeagueApps | ✅ | ✅ | ❌ | ✅ |
| Angular (Bay State) | ✅ | ✅ | ✅ | ✅ |
| MRYHA (Manchester) | ✅ | ❌ (login-gated) | ✅ | ✅ |
| Providence | ✅ | ❌ (not exposed) | ❌ | ✅ |

---

Generated: January 2026
Last Updated: January 28, 2026
