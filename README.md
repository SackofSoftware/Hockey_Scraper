# Hockey Scraper

Reverse-engineered documentation and Python tooling for the **GameSheet Stats API** (`gamesheetstats.com/api`) -- an undocumented REST API used by youth and amateur hockey leagues across North America to manage seasons, standings, schedules, and box scores.

This project provides a complete reference of discovered API endpoints, a working scraper, and a data pipeline that imports everything into SQLite for analysis.

## GameSheet API -- Discovered Endpoints

Base URL: `https://gamesheetstats.com/api`

All endpoints are unauthenticated and return JSON. The API uses a consistent pattern of `use{Feature}/{action}/{season_id}` with query-string filters for pagination and filtering.

### Season & Division Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /useSeasonDivisions/getSeason/{season_id}` | Season metadata, penalty codes, scoring rules |
| `GET /useSeasonDivisions/getDivisions/{season_id}` | All divisions in a season |

### Standings

| Endpoint | Description |
|----------|-------------|
| `GET /useStandings/getDivisionStandings/{season_id}?filter[divisions]={ids}` | Full team standings with GP, W, L, T, OTW, OTL, SOW, SOL, PTS, PP%, PK%, PIM, streaks, last-10 record |

The standings response uses **parallel arrays** -- `teamIds[]`, `w[]`, `l[]`, `gf[]`, etc. -- where index `i` across all arrays represents one team.

### Schedule

| Endpoint | Description |
|----------|-------------|
| `GET /useSchedule/getSeasonSchedule/{season_id}?filter[divisions]={ids}&filter[gametype]={type}&filter[limit]={n}&filter[offset]={n}` | Paginated game schedule |

Filter options: `gametype` = `overall`, `regular_season`, `playoffs`. Pagination via `limit`/`offset`.

### Box Scores (the richest endpoint)

| Endpoint | Description |
|----------|-------------|
| `GET /useBoxScore/getGameStats/{season_id}/games/{game_id}` | Complete box score for a single game |

Returns:
- **Game info** -- date, location, status, period lengths
- **Team info** -- names, logos, records, final scores
- **Full rosters** -- player IDs, jersey numbers, per-game G/A/PTS/PIM
- **Goals by period** -- scorer, assists, time, PP/SH/EN/GWG flags, plus/minus players
- **Penalties by period** -- player, infraction type/class/duration, time
- **Coach info** -- names, roles

### Team Games

| Endpoint | Description |
|----------|-------------|
| `GET /useUnifiedGames/{season_id}?filter[teams]={team_id}` | All games for a specific team |

### Endpoints That Return 404

These patterns were tested but do not resolve:

- `GET /useRoster/getTeamRoster/{team_id}` -- roster data only available via box scores
- `GET /usePlayerStats/getDivisionPlayerStats/{season_id}` -- must aggregate from box scores
- `GET /useGoalieStats/getGoalieStats/{season_id}` -- must aggregate from box scores

### Data Availability Summary

| Data | Source | Quality |
|------|--------|---------|
| Season/division metadata | `getSeason`, `getDivisions` | Complete |
| Team standings (W/L/T, PP%, PK%, streaks) | `getDivisionStandings` | Complete |
| Game schedules | `getSeasonSchedule` | Complete |
| Box scores (goals, penalties, rosters) | `getGameStats` | Complete for finished games |
| Player names | Box scores | Often blank (privacy) -- use jersey # + player ID |
| Shots on goal | Box scores | Field exists but usually 0 |
| Player/goalie leaderboards | N/A | Must aggregate manually from box scores |

See [`docs/scrapers/GAMESHEET_API_DOCUMENTATION.md`](docs/scrapers/GAMESHEET_API_DOCUMENTATION.md) for full endpoint documentation with response schemas and example payloads.

## Scraping Methodology

### Step 1: Discover divisions

```python
GET /useSeasonDivisions/getDivisions/{season_id}
# Returns array of {id, title} for every division
```

### Step 2: Fetch standings for team metadata

```python
GET /useStandings/getDivisionStandings/{season_id}?filter[divisions]={all_div_ids}
# Returns team IDs, names, logos, full stat lines
```

### Step 3: Paginate through the schedule

```python
offset = 0
while has_data:
    GET /useSchedule/getSeasonSchedule/{season_id}?filter[divisions]={ids}&filter[limit]=100&filter[offset]={offset}
    offset += 100
```

### Step 4: Fetch box scores for completed games

```python
for game in games_with_status_final:
    GET /useBoxScore/getGameStats/{season_id}/games/{game_id}
    # Extract goals, penalties, rosters
```

### Step 5: Aggregate player stats

Since there are no player leaderboard endpoints, player stats must be built by iterating over all box scores and summing per-player totals keyed by `(player_id, jersey_number, team_id)`.

## Quick Start

```bash
pip install -r requirements.txt

# Fetch all divisions for a season
python Gamesheet_All_Scrape.py --season-id 10776

# Run the full pipeline (import + stats + quality analysis)
python full_pipeline.py

# Start the REST API
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000
# Docs at http://localhost:8000/docs
```

## Project Structure

```
Hockey_Scraper/
├── Gamesheet_All_Scrape.py         # GameSheet API scraper
├── data_importer.py                # Box score importer -> SQLite
├── full_pipeline.py                # Pipeline orchestrator
├── stats_calculator.py             # Basic stats (G, A, PTS, PP%, PK%)
├── advanced_metrics.py             # SOS, streaks, H2H, trends
├── api_server.py                   # FastAPI REST server (20+ endpoints)
├── api_models.py                   # Pydantic response models
├── logo_service.py                 # Logo cross-reference service
├── advanced_stats_database.py      # SQLite schema (13 tables)
├── data_quality_analyzer.py        # Confidence scoring, gap detection
├── normalize_team_names.py         # Club/organization name normalization
├── smart_updater.py                # Time-aware incremental updates
├── ssc_hockey_scraper.py           # SportsEngine HTML scraper (Playwright)
├── ssc_weekly_scraper.py           # Weekly incremental wrapper
├── pipeline_config.py              # Season/league configuration
├── config/                         # Division config files
├── logos/                          # 40 SVG team logos
├── docs/
│   └── scrapers/
│       └── GAMESHEET_API_DOCUMENTATION.md   # Full API reference
├── tests/                          # Test suite + fixtures
└── scripts/                        # Automation scripts
```

## Configuration

- **Season ID**: Pass `--season-id` to scripts (default: `10776` for BSHL 2025-26)
- **Database**: Set `HOCKEY_DB_PATH` env var or use default local SQLite path
- **Divisions**: Auto-discovered from the API, or configure in `config/bshl_divisions.json`

## Data Quality Notes

GameSheet is used by youth hockey leagues where data is often entered manually at rinks by volunteers:

- **Player names** are frequently blank (privacy settings) -- jersey numbers and player IDs are reliable
- **Shots on goal** fields exist but are rarely populated
- **Assists** may not always be recorded
- **Jersey number errors** occur when the wrong player is credited

The `data_quality_analyzer.py` module scores data completeness and flags inconsistencies.

## License

MIT
