# Pipeline Quick Start Guide

Complete guide for running the hockey stats pipeline from start to finish.

## Table of Contents
- [One-Command Setup](#one-command-setup)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Testing Multiple Leagues](#testing-multiple-leagues)
- [Configuration Options](#configuration-options)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)
- [API Server Usage](#api-server-usage)

---

## One-Command Setup

The fastest way to get started:

```bash
# Complete pipeline for Bay State Hockey League 2025-26 season
python3 full_pipeline.py --season-id 10776
```

That's it! This single command will:
1. Create database and schema
2. Import all divisions, teams, and games
3. Import box scores (goals, penalties, rosters)
4. Calculate player and team statistics
5. Calculate advanced metrics (SOS, H2H, streaks)
6. Analyze data quality
7. Generate reports

**Expected duration:** 10-30 minutes (depending on season size and API response time)

---

## Installation

### Prerequisites

```bash
# Python 3.9 or higher
python3 --version

# Required packages
pip install requests sqlite3 fastapi uvicorn pydantic
```

### Verify Installation

```bash
# Test imports
python3 -c "import requests, sqlite3, fastapi, pydantic; print('✅ All dependencies installed')"
```

---

## Basic Usage

### Run Complete Pipeline

```bash
# Default configuration
python3 full_pipeline.py --season-id 10776

# With development preset (verbose logging)
python3 full_pipeline.py --season-id 10776 --preset development

# With production preset (optimized)
python3 full_pipeline.py --season-id 10776 --preset production

# With custom API delay
python3 full_pipeline.py --season-id 10776 --api-delay 0.2
```

### Run Specific Phases

```bash
# Import data only
python3 full_pipeline.py --season-id 10776 --phase import

# Calculate stats only (requires existing database)
python3 full_pipeline.py --season-id 10776 --phase stats

# Calculate advanced metrics only
python3 full_pipeline.py --season-id 10776 --phase advanced

# Analyze data quality only
python3 full_pipeline.py --season-id 10776 --phase quality

# Generate reports only
python3 full_pipeline.py --season-id 10776 --phase reports
```

### Run Integration Tests

```bash
# Quick test (fast, limited coverage)
python3 test_full_pipeline.py --quick

# Full test suite
python3 test_full_pipeline.py

# Test with specific seasons
python3 test_full_pipeline.py --test-seasons 10776,10477
```

---

## Testing Multiple Leagues

### Process Multiple Seasons

```bash
# Season 1: Bay State Hockey League 2025-26
python3 full_pipeline.py --season-id 10776

# Season 2: Different league/season
python3 full_pipeline.py --season-id 10477

# Season 3: Another league
python3 full_pipeline.py --season-id 12345
```

Each season creates its own isolated database:
- `hockey_stats_10776.db`
- `hockey_stats_10477.db`
- `hockey_stats_12345.db`

### Verify Data Isolation

```bash
# Run integration test with multiple seasons
python3 test_full_pipeline.py --test-seasons 10776,10477

# The test verifies:
# - Each season has its own database
# - No data cross-contamination
# - Same commands work identically for all seasons
```

---

## Configuration Options

### Using Configuration Files

Create `custom_config.json`:

```json
{
  "season_id": "10776",
  "api_delay": 0.15,
  "min_quality_score": 0.9,
  "api_port": 8080,
  "log_level": "DEBUG",
  "generate_reports": true,
  "vacuum_database": true
}
```

Run with config:

```bash
python3 full_pipeline.py --season-id 10776 --config custom_config.json
```

### Preset Configurations

**Development** (verbose, conservative):
```bash
python3 full_pipeline.py --season-id 10776 --preset development
```
- Log level: DEBUG
- API delay: 0.2s (slower, safer)
- Detailed progress bars
- No database vacuum (faster iteration)

**Production** (optimized):
```bash
python3 full_pipeline.py --season-id 10776 --preset production
```
- Log level: INFO
- API delay: 0.05s (faster)
- Minimal console output
- Database vacuum enabled
- Automatic backups

**Testing** (one division only):
```bash
python3 full_pipeline.py --season-id 10776 --preset testing
```
- Imports only one test division
- Fast execution for debugging
- Log level: DEBUG

**Minimal** (basic stats only):
```bash
python3 full_pipeline.py --season-id 10776 --preset minimal
```
- No advanced metrics
- No data quality analysis
- Fastest execution

### Environment Variables

```bash
# Override default database path
export HOCKEY_DB_PATH=/path/to/custom/location/hockey_stats.db
python3 full_pipeline.py --season-id 10776
```

---

## Troubleshooting

### Common Errors

#### 1. API Connection Timeout

**Error:**
```
requests.exceptions.Timeout: HTTPSConnectionPool
```

**Solution:**
```bash
# Increase API delay
python3 full_pipeline.py --season-id 10776 --api-delay 0.5

# Or use development preset
python3 full_pipeline.py --season-id 10776 --preset development
```

#### 2. Database Locked

**Error:**
```
sqlite3.OperationalError: database is locked
```

**Solution:**
```bash
# Close any other programs using the database
# Or remove lock file
rm hockey_stats_10776.db-journal

# Re-run pipeline
python3 full_pipeline.py --season-id 10776
```

#### 3. Missing Dependencies

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
# Install required packages
pip install fastapi uvicorn pydantic requests

# Verify installation
python3 -c "import fastapi; print('✅ FastAPI installed')"
```

#### 4. Insufficient Memory

**Error:**
```
MemoryError: Unable to allocate array
```

**Solution:**
```bash
# Process one division at a time
# Edit pipeline_config.py:
# specific_division_ids = [60038]  # One division

# Or use testing preset
python3 full_pipeline.py --season-id 10776 --preset testing
```

#### 5. API Rate Limiting

**Error:**
```
HTTP 429: Too Many Requests
```

**Solution:**
```bash
# Increase API delay significantly
python3 full_pipeline.py --season-id 10776 --api-delay 1.0

# The pipeline will automatically retry with backoff
```

### Data Quality Warnings

#### Low Quality Score

**Warning:**
```
Overall Quality Score: 0.65
```

**Causes:**
- Player number inconsistencies
- Missing player names
- Incomplete game data

**Action:**
```bash
# Review quality report
cat reports/data_quality_10776_*.json

# Analyze specific issues
sqlite3 hockey_stats_10776.db "SELECT * FROM data_quality_issues LIMIT 10"
```

#### Missing Box Scores

**Warning:**
```
Box score missing for game 12345
```

**Causes:**
- Game not yet played
- API data not available
- Network error during import

**Action:**
```bash
# Re-run import phase only
python3 full_pipeline.py --season-id 10776 --phase import

# Check game status
sqlite3 hockey_stats_10776.db "SELECT status FROM games WHERE game_id='12345'"
```

### Performance Tuning

#### Slow Import

**Optimize:**
```bash
# Reduce API delay (if no rate limiting)
python3 full_pipeline.py --season-id 10776 --api-delay 0.05

# Disable database vacuum
python3 full_pipeline.py --season-id 10776 --preset minimal

# Disable quality analysis
# Edit pipeline_config.py: flag_suspicious_stats = False
```

#### Large Database

**Optimize:**
```bash
# Enable vacuum to reclaim space
python3 full_pipeline.py --season-id 10776 --preset production

# Or manually optimize
sqlite3 hockey_stats_10776.db "VACUUM"
```

---

## Production Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/hockey-pipeline.service`:

```ini
[Unit]
Description=Hockey Stats Pipeline
After=network.target

[Service]
Type=oneshot
User=hockey
WorkingDirectory=/opt/hockey-stats
ExecStart=/usr/bin/python3 full_pipeline.py --season-id 10776 --preset production
StandardOutput=append:/var/log/hockey-stats/pipeline.log
StandardError=append:/var/log/hockey-stats/pipeline-error.log

[Install]
WantedBy=multi-user.target
```

Enable and run:
```bash
sudo systemctl enable hockey-pipeline
sudo systemctl start hockey-pipeline
sudo systemctl status hockey-pipeline
```

### Cron Job (Scheduled Updates)

Add to crontab:
```bash
# Update stats daily at 2 AM
0 2 * * * cd /opt/hockey-stats && python3 full_pipeline.py --season-id 10776 --preset production >> /var/log/hockey-stats/cron.log 2>&1
```

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY *.py .

CMD ["python3", "full_pipeline.py", "--season-id", "10776", "--preset", "production"]
```

Build and run:
```bash
docker build -t hockey-stats-pipeline .
docker run -v /data/hockey:/app/data hockey-stats-pipeline
```

### Monitoring

**Check Pipeline Health:**
```bash
# View recent logs
tail -f pipeline_10776.log

# Check database stats
python3 -c "
import sqlite3
conn = sqlite3.connect('hockey_stats_10776.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM games')
print(f'Games: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM goals')
print(f'Goals: {cursor.fetchone()[0]}')
"
```

**Set Up Alerts:**
```bash
# Example: Email if quality score drops below threshold
python3 << EOF
import sqlite3
import smtplib

conn = sqlite3.connect('hockey_stats_10776.db')
cursor = conn.cursor()

# Check latest quality metrics
# If score < 0.8, send alert
# (Add your alert logic here)
EOF
```

---

## API Server Usage

### Start API Server

```bash
# Start with default database
uvicorn api_server:app --host 0.0.0.0 --port 8000

# Start with specific database
export HOCKEY_DB_PATH=/path/to/hockey_stats_10776.db
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### Access API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Example API Calls

```bash
# Get season info
curl http://localhost:8000/api/v1/seasons/10776

# Get division standings
curl http://localhost:8000/api/v1/divisions/60038/standings

# Get team stats
curl http://localhost:8000/api/v1/teams/123456/stats

# Get points leaders
curl http://localhost:8000/api/v1/seasons/10776/leaders/points?limit=10

# Search players
curl "http://localhost:8000/api/v1/players/search?number=10&team_id=123456"
```

### Production API Deployment

```bash
# Use gunicorn for production
pip install gunicorn

# Run with workers
gunicorn api_server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or use uvicorn with SSL
uvicorn api_server:app --host 0.0.0.0 --port 443 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

---

## Next Steps

1. **Verify Installation:**
   ```bash
   python3 test_full_pipeline.py --quick
   ```

2. **Run First Pipeline:**
   ```bash
   python3 full_pipeline.py --season-id 10776
   ```

3. **Review Results:**
   ```bash
   # Check logs
   cat pipeline_10776.log

   # View reports
   ls -lh reports/

   # Explore database
   sqlite3 hockey_stats_10776.db ".tables"
   ```

4. **Start API Server:**
   ```bash
   uvicorn api_server:app --reload
   ```

5. **Test API:**
   - Open http://localhost:8000/docs
   - Try example queries

---

## Support and Documentation

- **Full Documentation:** See `ADVANCED_STATS_API_DESIGN.md`
- **API Reference:** http://localhost:8000/docs (when server running)
- **Configuration Reference:** See `pipeline_config.py`
- **Test Suite:** Run `python3 test_full_pipeline.py`

---

## Summary Checklist

- [ ] Install Python 3.9+
- [ ] Install dependencies (`pip install requests sqlite3 fastapi uvicorn pydantic`)
- [ ] Run quick test (`python3 test_full_pipeline.py --quick`)
- [ ] Run pipeline (`python3 full_pipeline.py --season-id 10776`)
- [ ] Review logs and reports
- [ ] Start API server (`uvicorn api_server:app --reload`)
- [ ] Test API endpoints
- [ ] Set up automated updates (cron/systemd)
- [ ] Configure monitoring

---

**Ready to Go!** The pipeline is designed to work with ANY GameSheet season ID. Just change the `--season-id` parameter.
