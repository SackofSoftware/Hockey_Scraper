# FastAPI REST Server - Quick Start Guide

## 5-Minute Setup

### Step 1: Install Dependencies (1 minute)

```bash
cd /path/to/Hockey_Scraper
pip3 install fastapi uvicorn pydantic sqlalchemy
```

### Step 2: Start the Server (30 seconds)

```bash
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using StatReload
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 3: Test the API (2 minutes)

Open your browser and visit:

**Interactive API Documentation:**
http://localhost:8000/docs

**Try these endpoints:**

1. **Health Check**
   ```
   http://localhost:8000/health
   ```

2. **Season Info**
   ```
   http://localhost:8000/api/v1/seasons/10776
   ```

3. **Division Standings**
   ```
   http://localhost:8000/api/v1/divisions/60040/standings
   ```

4. **Team Stats** (example team)
   ```
   http://localhost:8000/api/v1/teams/386299/stats
   ```

5. **League Leaders - Points**
   ```
   http://localhost:8000/api/v1/seasons/10776/leaders/points?limit=10
   ```

### Step 4: Run Automated Tests (1 minute)

```bash
python3 test_api.py
```

This will test all endpoints and show results.

---

## Example Queries

### Get Top Scorers in a Division

```bash
curl "http://localhost:8000/api/v1/seasons/10776/leaders/points?division_id=60040&limit=20"
```

### Search for a Player by Jersey Number

```bash
curl "http://localhost:8000/api/v1/players/search?number=41&team_id=386299"
```

### Get Team's Recent Games

```bash
curl "http://localhost:8000/api/v1/teams/386299/schedule"
```

### Get Team Leaders

```bash
curl "http://localhost:8000/api/v1/teams/386299/leaders?limit=10"
```

---

## Using with LLM/AI Tools

The API responses are designed to be LLM-friendly with contextual information:

### Example: Team Stats Response

```json
{
  "team": {
    "team_id": 386299,
    "team_name": "Duxbury U12B",
    "division_name": "U12B"
  },
  "record": {
    "games_played": 15,
    "wins": 10,
    "losses": 4,
    "ties": 1,
    "points": 21,
    "points_pct": 0.700,
    "division_rank": 2,
    "record_string": "10-4-1"
  },
  "scoring": {
    "goals_for": {
      "value": 58,
      "rank": 2,
      "rank_suffix": "2nd",
      "total_teams": 8,
      "percentile": 87.5,
      "interpretation": "Above Average - Top 25%",
      "context": "2nd out of 8 teams"
    },
    "goals_per_game": {
      "value": 3.87,
      "division_average": 3.21
    }
  },
  "recent_form": {
    "current_streak": "W3",
    "streak_count": 3,
    "last_5_games": [...]
  }
}
```

**Key LLM-Friendly Features:**
- `interpretation` field explains the statistic
- `context` provides human-readable comparison
- `percentile` shows where team/player ranks
- `rank_suffix` gives ordinal position (1st, 2nd, 3rd)

---

## Common Use Cases

### 1. Build a Stats Dashboard

```javascript
// Fetch and display team standings
fetch('http://localhost:8000/api/v1/divisions/60040/standings')
  .then(res => res.json())
  .then(data => {
    console.log(`${data.division.division_name} Standings:`);
    data.standings.forEach(team => {
      console.log(`${team.rank}. ${team.team.team_name} - ${team.record.record_string}`);
    });
  });
```

### 2. Find Player Stats

```python
import requests

# Search for player #41 on Duxbury
response = requests.get(
    "http://localhost:8000/api/v1/players/search",
    params={"number": "41", "team_id": 386299}
)

players = response.json()
if players:
    player_id = players[0]['player']['player_id']

    # Get detailed stats
    stats_response = requests.get(
        f"http://localhost:8000/api/v1/players/{player_id}/stats"
    )
    stats = stats_response.json()

    print(f"Goals: {stats['goals']}")
    print(f"Assists: {stats['assists']}")
    print(f"Points: {stats['points']}")
    print(f"PPG: {stats['points_per_game']}")
```

### 3. Compare Teams

```python
import requests

team_ids = [386299, 386305]  # Duxbury vs WHK

for team_id in team_ids:
    response = requests.get(f"http://localhost:8000/api/v1/teams/{team_id}/stats")
    team = response.json()

    print(f"\n{team['team']['team_name']}")
    print(f"  Record: {team['record']['record_string']}")
    print(f"  GF: {team['scoring']['goals_for']['value']}")
    print(f"  GA: {team['scoring']['goals_against']['value']}")
    print(f"  Streak: {team['recent_form']['current_streak']}")
```

---

## Troubleshooting

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn api_server:app --reload --port 8001
```

### Database Not Found

```bash
# Check database exists
ls -la output/*.db

# Set custom database path
export HOCKEY_DB_PATH="/path/to/your/database.db"
uvicorn api_server:app --reload
```

### Module Not Found

```bash
# Install missing dependencies
pip3 install -r requirements.txt
```

---

## Next Steps

1. **Explore the API:** Visit http://localhost:8000/docs for interactive documentation
2. **Read the Full Guide:** See `API_SERVER_README.md` for detailed documentation
3. **Review Design:** Check `ADVANCED_STATS_API_DESIGN.md` for architecture details
4. **Customize:** Add new endpoints by editing `api_server.py`

---

## Quick Reference

| Endpoint | Description |
|----------|-------------|
| `/health` | Health check |
| `/docs` | Interactive API documentation |
| `/api/v1/seasons/{id}` | Season information |
| `/api/v1/divisions/{id}/standings` | Division standings |
| `/api/v1/teams/{id}/stats` | Complete team stats |
| `/api/v1/teams/{id}/schedule` | Team schedule |
| `/api/v1/teams/{id}/roster` | Team roster |
| `/api/v1/teams/{id}/leaders` | Team stat leaders |
| `/api/v1/players/{id}/stats` | Player statistics |
| `/api/v1/players/search` | Search for players |
| `/api/v1/seasons/{id}/leaders/points` | League points leaders |
| `/api/v1/seasons/{id}/leaders/goals` | League goals leaders |
| `/api/v1/seasons/{id}/leaders/assists` | League assists leaders |

**Base URL:** `http://localhost:8000`

**Season ID:** `10776` (Bay State Hockey League 2025-26)

**Example Division IDs:** 60040, 60041, 60042

**Example Team IDs:** 386299 (Duxbury U12B), 386305 (WHK)
