# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Hockey data platform for the Bay State Hockey League (Season 10776). Scrapes from GameSheet Stats API and SportsEngine, calculates advanced stats, and serves via REST API with logo support. Runs on macOS with python3 (M2 Pro, 16GB).

## Project Structure

Production Python files live at the root level (to preserve their mutual import chains). Everything else is organized into subdirectories:

- `docs/` - 45 documentation files in subdirs: api/, pipeline/, scrapers/, stats/, deployment/, setup/, llm/
- `tests/` - Test files and `fixtures/` for JSON test data
- `research/` - Exploratory/probe scripts (not production)
- `scripts/` - Runner and automation scripts (ehf_data_import.py, cron setup, etc.)
- `config/` - JSON config files (bshl_divisions.json)
- `logos/` - 40 SVG team logos (single source of truth)
- `data/` - Output data (gitignored, .gitkeep preserves structure)
- `archive/` - Old versions (gitignored): v0.1, v0.2, v2, hockey_scraper_repo, etc.

## Core Production Files

### Scrapers
- `Gamesheet_All_Scrape.py` - GameSheet API scraper for all divisions
- `ssc_hockey_scraper.py` - Playwright-based SportsEngine scraper
- `ssc_weekly_scraper.py` - Weekly incremental update wrapper

### Pipeline & Database
- `full_pipeline.py` - Orchestrator: import -> stats -> metrics -> quality
- `pipeline_config.py` - Configuration with season/league presets
- `data_importer.py` - GameSheet API data -> SQLite
- `advanced_stats_database.py` - SQLite schema and operations
- `stats_calculator.py` - Basic stats (G, A, PTS, PP%, PK%)
- `advanced_metrics.py` - SOS, streaks, H2H, trends
- `smart_updater.py` - Time-aware update scheduling

### API & Models
- `api_server.py` - FastAPI REST server (run with uvicorn)
- `api_models.py` - Pydantic models for all API responses
- `logo_service.py` - Logo cross-reference (local SVGs + GameSheet CDN)

### Data Quality
- `data_quality_analyzer.py` - Confidence scoring, missing data detection
- `data_quality_monitor.py` - Continuous quality monitoring
- `normalize_team_names.py` - Club/organization name normalization

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt
playwright install

# Run GameSheet scraper
python3 Gamesheet_All_Scrape.py

# Run full pipeline
python3 full_pipeline.py

# Start API server
python3 -m uvicorn api_server:app --reload --host 0.0.0.0 --port 8000

# Run tests
python3 -m pytest tests/ -v
```

## Key Data Sources

- **GameSheet Stats API**: `gamesheetstats.com/api` - Season 10776 (BSHL 2025-26)
  - Divisions, standings, schedules, box scores
  - Team logos via `imagedelivery.net` CDN
- **SportsEngine/SSC**: Playwright-scraped HTML schedules and rosters

## GameSheet API

Base: `https://gamesheetstats.com/api`

Key endpoints (season_id = 10776):
- `/useSeasonDivisions/getDivisions/{season_id}` - All divisions
- `/useStandings/getDivisionStandings/{season_id}?filter[divisions]={ids}` - Standings
- `/useSchedule/getSeasonSchedule/{season_id}?filter[divisions]={ids}` - Schedules
- `/useBoxScore/getGameStats/{season_id}/games/{game_id}` - Box scores
- `/useUnifiedGames/{season_id}?filter[teams]={team_id}` - Team games

Full reference: `docs/scrapers/GAMESHEET_API_DOCUMENTATION.md`

## Import Dependency Graph

```
full_pipeline.py -> pipeline_config, advanced_stats_database, data_importer,
                    stats_calculator, advanced_metrics, data_quality_analyzer
api_server.py -> api_models
data_importer.py -> advanced_stats_database, advanced_metrics
smart_updater.py -> advanced_stats_database, data_importer
ssc_weekly_scraper.py -> ssc_hockey_scraper
```

All production files must stay at root to preserve these bare-module imports.
