# Advanced Hockey Stats API Server

FastAPI-based REST server for comprehensive hockey statistics with LLM-friendly responses.

## Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Set Database Path (Optional)

By default, the server uses the most recent database in `hockey_scraper_repo/output/`. To override:

```bash
export HOCKEY_DB_PATH="/path/to/your/hockey.db"
```

### 3. Start the Server

```bash
# Development mode with auto-reload
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Access API Documentation

Once running, visit:
- **Interactive API Docs (Swagger UI):** http://localhost:8000/docs
- **Alternative Docs (ReDoc):** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

---

## API Endpoints Overview

### Season & Division Endpoints

```
GET /api/v1/seasons/{season_id}
→ Season info, divisions, teams count

GET /api/v1/seasons/{season_id}/divisions
→ All divisions with team counts

GET /api/v1/divisions/{division_id}/standings
→ Division standings with ALL calculated stats

GET /api/v1/divisions/{division_id}/teams
→ All teams in division with basic info
```

### Team Endpoints

```
GET /api/v1/teams/{team_id}
→ Basic team information

GET /api/v1/teams/{team_id}/stats
→ Complete team statistics (record, scoring, special teams, etc.)

GET /api/v1/teams/{team_id}/schedule
→ All games (past & future) with results

GET /api/v1/teams/{team_id}/roster
→ Current roster with player stats

GET /api/v1/teams/{team_id}/leaders
→ Team leaders in all categories
```

### Player Endpoints

```
GET /api/v1/players/{player_id}
→ Basic player information

GET /api/v1/players/{player_id}/stats
→ Complete player statistics

GET /api/v1/players/search?number={num}&team={team_id}&name={name}
→ Search for players by number, team, or name
```

### Game Endpoints

```
GET /api/v1/games/{game_id}
→ Complete game information

GET /api/v1/games/{game_id}/summary
→ Game summary statistics
```

### League-Wide Leader Endpoints

```
GET /api/v1/seasons/{season_id}/leaders/points
→ League scoring leaders

GET /api/v1/seasons/{season_id}/leaders/goals
→ Goal scoring leaders

GET /api/v1/seasons/{season_id}/leaders/assists
→ Assist leaders

Query Parameters:
- division_id: Filter by division (optional)
- limit: Number of leaders (default 20, max 100)
- min_games: Minimum games played (default 0)
```

---

## Testing the API

### Using curl

```bash
# Get season info
curl http://localhost:8000/api/v1/seasons/10776

# Get all divisions
curl http://localhost:8000/api/v1/seasons/10776/divisions

# Get division standings
curl http://localhost:8000/api/v1/divisions/60040/standings

# Get team stats
curl http://localhost:8000/api/v1/teams/386299/stats

# Get team schedule
curl http://localhost:8000/api/v1/teams/386299/schedule

# Get team roster
curl http://localhost:8000/api/v1/teams/386299/roster

# Get team leaders
curl http://localhost:8000/api/v1/teams/386299/leaders?limit=10

# Search for player by number
curl "http://localhost:8000/api/v1/players/search?number=41&team_id=386299"

# Get player stats
curl http://localhost:8000/api/v1/players/5958147/stats

# Get league points leaders
curl "http://localhost:8000/api/v1/seasons/10776/leaders/points?limit=20&min_games=5"

# Get division-specific leaders
curl "http://localhost:8000/api/v1/seasons/10776/leaders/goals?division_id=60040&limit=10"
```

### Using Python requests

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Get season info
response = requests.get(f"{BASE_URL}/seasons/10776")
season = response.json()
print(f"Season: {season['title']}")
print(f"Divisions: {season['divisions_count']}")
print(f"Teams: {season['teams_count']}")

# Get division standings
response = requests.get(f"{BASE_URL}/divisions/60040/standings")
standings = response.json()
print(f"\n{standings['division']['division_name']} Standings:")
for team in standings['standings'][:5]:
    print(f"{team['rank']}. {team['team']['team_name']} - {team['record']['record_string']}")

# Get team stats
response = requests.get(f"{BASE_URL}/teams/386299/stats")
team_stats = response.json()
print(f"\nTeam: {team_stats['team']['team_name']}")
print(f"Record: {team_stats['record']['record_string']}")
print(f"Goals For: {team_stats['scoring']['goals_for']['value']}")
print(f"Goals Against: {team_stats['scoring']['goals_against']['value']}")
print(f"Current Streak: {team_stats['recent_form']['current_streak']}")

# Get league leaders
response = requests.get(f"{BASE_URL}/seasons/10776/leaders/points?limit=10")
leaders = response.json()
print(f"\nTop 10 Point Scorers:")
for leader in leaders['leaders']:
    player = leader['player']
    print(f"{leader['rank']}. #{player['player_number']} ({player['team_name']}) - {leader['value']} pts")
```

### Using JavaScript/Fetch

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';

// Get team stats
async function getTeamStats(teamId) {
  const response = await fetch(`${BASE_URL}/teams/${teamId}/stats`);
  const teamStats = await response.json();

  console.log(`Team: ${teamStats.team.team_name}`);
  console.log(`Record: ${teamStats.record.record_string}`);
  console.log(`Points: ${teamStats.record.points}`);
  console.log(`Division Rank: ${teamStats.record.division_rank}`);

  return teamStats;
}

// Get league leaders
async function getLeaders(category, limit = 20) {
  const response = await fetch(
    `${BASE_URL}/seasons/10776/leaders/${category}?limit=${limit}`
  );
  const leaders = await response.json();

  console.log(`Top ${limit} ${category} leaders:`);
  leaders.leaders.forEach(leader => {
    console.log(`${leader.rank}. #${leader.player.player_number} - ${leader.value}`);
  });

  return leaders;
}

// Search for player
async function findPlayer(number, teamId) {
  const response = await fetch(
    `${BASE_URL}/players/search?number=${number}&team_id=${teamId}`
  );
  const results = await response.json();

  results.forEach(result => {
    console.log(`Found: #${result.player.player_number} on ${result.team.team_name}`);
    console.log(`Confidence: ${result.confidence_score}`);
  });

  return results;
}

// Usage
getTeamStats(386299);
getLeaders('points', 10);
findPlayer('41', 386299);
```

---

## LLM-Friendly Features

All responses include contextual information designed for LLM interpretation:

### StatWithContext Objects

```json
{
  "value": 26.7,
  "rank": 3,
  "rank_suffix": "3rd",
  "total_teams": 8,
  "percentile": 75.0,
  "league_average": 22.1,
  "division_average": 23.4,
  "interpretation": "Above Average - Top 25%",
  "context": "3rd out of 8 teams"
}
```

### Leader Entries with Percentiles

```json
{
  "rank": 1,
  "player": {...},
  "team": {...},
  "value": 45,
  "games_played": 15,
  "percentile": 100.0,
  "interpretation": "Elite - Top 10%"
}
```

---

## Response Caching (Future Enhancement)

To add caching for frequently accessed data:

```python
# Install: pip3 install fastapi-cache2[redis]

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="hockey-api-cache")

@app.get("/api/v1/teams/{team_id}/stats")
@cache(expire=300)  # Cache for 5 minutes
async def get_team_stats(...):
    ...
```

---

## Database Schema Compatibility

The API works with databases containing these tables:

### Required Tables
- `divisions` - Division information
- `teams` - Team roster and stats
- `games` - Game schedule and results
- `players` - Player information and stats

### Database Location

Default: `hockey_scraper_repo/output/complete_gamesheet_api_10776_20250915_181652.db`

Override with environment variable:
```bash
export HOCKEY_DB_PATH="/path/to/custom.db"
```

---

## Error Handling

The API returns standard HTTP status codes with detailed error messages:

```json
// 404 Not Found
{
  "error": {
    "code": "NOT_FOUND",
    "message": "The requested resource was not found",
    "details": {"path": "/api/v1/teams/999999"}
  },
  "timestamp": "2025-11-08T15:30:00.000Z"
}

// 500 Internal Server Error
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An internal server error occurred",
    "details": {"error": "..."}
  },
  "timestamp": "2025-11-08T15:30:00.000Z"
}
```

---

## Performance Optimization

### Pagination Support

Many endpoints support pagination via query parameters:

```bash
# Get teams with pagination
curl "http://localhost:8000/api/v1/divisions/60040/teams?limit=10&offset=0"

# Get leaders with limit
curl "http://localhost:8000/api/v1/seasons/10776/leaders/points?limit=50"
```

### Database Connection Pooling

For production, use a connection pool:

```python
# In api_server.py, replace get_db() with:
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

engine = create_engine(
    f"sqlite:///{DEFAULT_DB_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
```

---

## CORS Configuration

CORS is currently configured to allow all origins for development. For production:

```python
# In api_server.py, update CORS middleware:
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://app.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api_server.py api_models.py ./
COPY hockey_scraper_repo/output/*.db ./data/

ENV HOCKEY_DB_PATH=/app/data/complete_gamesheet_api_10776_20250915_181652.db

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t hockey-api .
docker run -p 8000:8000 hockey-api
```

### Systemd Service (Linux)

```ini
# /etc/systemd/system/hockey-api.service
[Unit]
Description=Hockey Stats API Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Hockey_Scraper
Environment="HOCKEY_DB_PATH=/path/to/hockey.db"
ExecStart=/usr/bin/python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable hockey-api
sudo systemctl start hockey-api
```

---

## Extending the API

### Adding New Endpoints

```python
@app.get("/api/v1/custom-endpoint", response_model=YourModel)
async def custom_endpoint(
    param: str = Query(..., description="Parameter description"),
    db=Depends(get_db_connection)
):
    """
    Endpoint description for auto-generated docs
    """
    cursor = db.cursor()

    # Your query logic
    data = cursor.execute("SELECT ...").fetchall()

    # Return Pydantic model
    return YourModel(...)
```

### Adding Response Models

```python
# In api_models.py
class YourModel(BaseModel):
    """Model description"""
    field1: str
    field2: int
    field3: Optional[List[str]] = None
```

---

## Troubleshooting

### Server won't start

```bash
# Check if port is already in use
lsof -i :8000

# Use different port
uvicorn api_server:app --reload --port 8001
```

### Database connection errors

```bash
# Verify database exists
ls -la "hockey_scraper_repo/output/complete_gamesheet_api_10776_20250915_181652.db"

# Test database
sqlite3 "/path/to/db" "SELECT COUNT(*) FROM teams;"

# Set correct path
export HOCKEY_DB_PATH="/absolute/path/to/database.db"
```

### CORS errors in browser

```javascript
// Check browser console for CORS errors
// Update allow_origins in api_server.py to include your domain
```

---

## Support & Documentation

- **API Documentation:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health
- **Reference:** `ADVANCED_STATS_API_DESIGN.md`

---

## Summary of Implemented Endpoints

✅ **Season/Division** (4 endpoints)
- Get season info
- Get divisions
- Get division standings
- Get division teams

✅ **Team** (5 endpoints)
- Get team info
- Get team stats (complete)
- Get team schedule
- Get team roster
- Get team leaders

✅ **Player** (3 endpoints)
- Get player info
- Get player stats
- Search players

✅ **Game** (2 endpoints)
- Get game info
- Get game summary

✅ **League Leaders** (3 endpoints)
- Points leaders
- Goals leaders
- Assists leaders

✅ **Health/Info** (3 endpoints)
- Root/info
- Health check
- Auto-generated docs

**Total: 20 implemented endpoints** with full Pydantic validation, LLM-friendly responses, CORS support, and comprehensive error handling.
