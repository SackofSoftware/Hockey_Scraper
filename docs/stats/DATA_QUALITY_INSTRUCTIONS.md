# Data Quality Analysis System - Instructions

## Overview

This data quality system provides comprehensive analysis and monitoring of hockey statistics data, including:

- **Player Number Consistency Analysis** - Detects when players wear different jersey numbers across games
- **Confidence Score Calculation** - Assigns quality scores (0.0 to 1.0) for each player, game, and team
- **Missing/Suspect Data Detection** - Flags empty names, duplicate players, wrong numbers, suspicious stats
- **Game Data Quality Analysis** - Identifies games with incomplete or inconsistent data
- **Issue Tracking & Resolution** - Logs all quality issues to database with resolution tracking
- **Quality Reports** - Generates comprehensive JSON reports with actionable recommendations

## Files

1. **`data_quality_analyzer.py`** - One-time analysis tool for deep data quality assessment
2. **`data_quality_monitor.py`** - Continuous monitoring tool with issue tracking and resolution
3. **`DATA_QUALITY_INSTRUCTIONS.md`** - This file

## Installation

No additional dependencies required beyond standard Python 3 and sqlite3 (included in Python).

```bash
# Make scripts executable
chmod +x data_quality_analyzer.py
chmod +x data_quality_monitor.py
```

## Usage

### 1. Initial Data Quality Analysis

Run a comprehensive one-time analysis of your database:

```bash
python3 data_quality_analyzer.py --db path/to/database.db
```

This will:
- Analyze player number consistency across all games
- Calculate confidence scores for all players
- Detect duplicate player entries
- Analyze game data completeness
- Generate missing data summary
- Calculate overall quality score
- Save results to JSON report

**Options:**

```bash
# Specify output file
python3 data_quality_analyzer.py --db database.db --output my_report.json

# Save issues to database for tracking
python3 data_quality_analyzer.py --db database.db --save-to-db
```

### 2. Continuous Quality Monitoring

Run ongoing quality monitoring with issue tracking:

```bash
python3 data_quality_monitor.py --db path/to/database.db
```

This will:
- Calculate quality scores for players, games, and teams
- Track quality metrics over time
- Detect new issues since last check
- Generate prioritized recommendations
- Save monitoring log to database

**Options:**

```bash
# List all unresolved issues
python3 data_quality_monitor.py --db database.db --list-issues

# Filter by severity
python3 data_quality_monitor.py --db database.db --list-issues --severity critical

# Resolve an issue
python3 data_quality_monitor.py --db database.db --resolve 42 --resolved-by "John" --notes "Fixed player number in roster"

# Export to specific file
python3 data_quality_monitor.py --db database.db --output quality_report.json
```

## Quality Metrics Explained

### Player Quality Score (0.0 - 1.0)

Calculated from weighted components:

- **Number Consistency (30%)**: 1.0 = always same number, decreases with more variations
- **Name Availability (20%)**: 1.0 = name present, 0.0 = empty
- **Data Completeness (20%)**: Based on game appearances and stats
- **Stats Reasonableness (25%)**: Flags suspiciously high or low totals
- **Penalty Data Quality (5%)**: Validates penalty minute totals

**Interpretation:**
- **0.8 - 1.0**: High quality, reliable data
- **0.5 - 0.8**: Medium quality, some issues
- **0.0 - 0.5**: Low quality, needs attention

### Game Quality Score (0.0 - 1.0)

Calculated from:

- **Score Completeness (35%)**: Final scores present
- **Box Score Quality (30%)**: Detailed goal/penalty data available
- **Data Consistency (20%)**: Scores are realistic
- **Metadata Completeness (15%)**: Date, teams, venue info present

### Team Quality Score (0.0 - 1.0)

Calculated from:

- **Record Completeness (40%)**: W-L-T matches games played
- **Roster Quality (40%)**: Reasonable number of players (8-25)
- **Stats Consistency (20%)**: Goals for/against are realistic

## Issue Types

### Player Issues

- **`number_inconsistency`**: Player wore multiple jersey numbers
- **`no_name`**: Player name not available
- **`no_number`**: Jersey number missing
- **`suspiciously_high_points`**: Unrealistic point totals (potential duplicates)
- **`duplicate_player`**: Same number worn by multiple players on same team

### Game Issues

- **`missing_scores`**: Final score not recorded
- **`box_score_missing`**: Game marked as having box score but data missing
- **`incomplete_game_data`**: Missing key game information
- **`unusually_high_scoring`**: Total goals > 20 (verify scores)

### Recommendations

Common recommendations generated:

- "Verify correct jersey number with team roster"
- "Update player name from official roster"
- "Check for duplicate goal entries"
- "Extract box score data"
- "Verify final scores"
- "Recalculate team record"

## Database Tables Created

The monitoring system creates these tracking tables:

### `data_quality_issues`

Logs all detected quality issues:

```sql
CREATE TABLE data_quality_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT,              -- 'player', 'game', 'team'
    entity_id TEXT,                -- ID of affected entity
    game_id TEXT,                  -- Related game (if applicable)
    issue_type TEXT,               -- Type of issue
    issue_description TEXT,        -- Human-readable description
    confidence_impact REAL,        -- Impact on quality score (0.0-1.0)
    is_resolved BOOLEAN,           -- Resolution status
    resolution_notes TEXT,         -- How it was fixed
    resolved_by TEXT,              -- Who resolved it
    resolved_at TIMESTAMP,         -- When resolved
    created_at TIMESTAMP           -- When detected
);
```

### `quality_scores`

Tracks quality metrics over time:

```sql
CREATE TABLE quality_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT,              -- 'player', 'game', 'team'
    entity_id TEXT,                -- ID of entity
    score_type TEXT,               -- Type of score metric
    score_value REAL,              -- Score value (0.0-1.0)
    calculated_at TIMESTAMP        -- When calculated
);
```

### `quality_monitoring_log`

Logs each monitoring run:

```sql
CREATE TABLE quality_monitoring_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_timestamp TIMESTAMP,
    overall_score REAL,
    total_issues INTEGER,
    critical_issues INTEGER,
    resolved_issues INTEGER,
    new_issues_since_last INTEGER,
    report_data TEXT               -- Full JSON report
);
```

## Example Workflow

### Daily Quality Check

```bash
# 1. Run monitoring to get current status
python3 data_quality_monitor.py --db hockey.db

# 2. Review critical issues
python3 data_quality_monitor.py --db hockey.db --list-issues --severity critical

# 3. Fix issues in your data

# 4. Mark issues as resolved
python3 data_quality_monitor.py --db hockey.db --resolve 15 --resolved-by "Admin" --notes "Updated player roster from official source"
```

### Weekly Deep Analysis

```bash
# 1. Run full analysis
python3 data_quality_analyzer.py --db hockey.db --save-to-db

# 2. Generate detailed report
python3 data_quality_monitor.py --db hockey.db --output weekly_report_$(date +%Y%m%d).json
```

### Pre-Production Check

```bash
# Before deploying or sharing your database, verify quality
python3 data_quality_analyzer.py --db production.db --output pre_deploy_quality.json

# Review the overall_quality_score in the report
# Aim for > 0.8 for production deployment
```

## Report Structure

### Analyzer Report (`data_quality_analyzer.py`)

```json
{
  "analysis_timestamp": "2025-11-08T10:30:00",
  "database": "path/to/database.db",
  "player_number_issues": [
    {
      "player_id": "5958147",
      "player_name": "John Smith",
      "team_name": "Duxbury U12B",
      "numbers_used": ["3 (10 games)", "5 (2 games)"],
      "consistency_score": 0.5,
      "issue_type": "number_inconsistency",
      "details": "Player wore 2 different numbers across 12 games"
    }
  ],
  "player_confidence_scores": [...],
  "duplicate_players": [...],
  "game_quality_issues": [...],
  "missing_data_summary": {
    "players": {
      "total": 2400,
      "missing_names": 1800,
      "missing_names_pct": 75.0
    },
    "games": {...}
  },
  "overall_quality_score": 0.823
}
```

### Monitor Report (`data_quality_monitor.py`)

```json
{
  "generated_at": "2025-11-08T10:30:00",
  "database": "path/to/database.db",
  "player_scores": [
    {
      "entity_type": "player",
      "entity_id": "5958147",
      "entity_name": "John Smith",
      "quality_score": 0.850,
      "metrics": {
        "number_consistency": 1.0,
        "name_availability": 1.0,
        "data_completeness": 1.0,
        "stats_reasonableness": 0.9
      },
      "issues": [],
      "recommendations": []
    }
  ],
  "game_scores": [...],
  "team_scores": [...],
  "issue_summary": {
    "total_unresolved": 42,
    "critical": 5,
    "warnings": 25,
    "info": 12
  },
  "overall_statistics": {
    "average_player_quality": 0.783,
    "average_game_quality": 0.891,
    "average_team_quality": 0.945,
    "overall_quality": 0.873
  },
  "recommendations": [
    {
      "recommendation": "Verify correct jersey number with team roster",
      "count": 47
    }
  ]
}
```

## Integration with Existing Systems

### With `ultimate_hockey_stats_extractor.py`

```python
# After extraction, run quality analysis
import subprocess

# Extract data
subprocess.run(["python3", "ultimate_hockey_stats_extractor.py"])

# Analyze quality
subprocess.run([
    "python3", "data_quality_analyzer.py",
    "--db", "output/hockey_stats.db",
    "--save-to-db"
])

# Generate report
subprocess.run([
    "python3", "data_quality_monitor.py",
    "--db", "output/hockey_stats.db"
])
```

### API Integration

You can import the classes directly:

```python
from data_quality_analyzer import DataQualityAnalyzer
from data_quality_monitor import DataQualityMonitor

# Analyze
analyzer = DataQualityAnalyzer("hockey.db")
results = analyzer.analyze_all()
analyzer.save_to_database(results)
analyzer.close()

# Monitor
monitor = DataQualityMonitor("hockey.db")
report = monitor.generate_quality_report()
monitor.close()

# Access results
print(f"Overall quality: {report['overall_statistics']['overall_quality']}")
```

## Troubleshooting

### No goals/penalties table found

The scripts automatically detect available tables and adapt:
- If advanced tables (goals, penalties) exist: Full analysis with detailed metrics
- If only basic tables (players, teams, games): Simplified analysis

### Database locked error

Close any other connections to the database before running:

```bash
# Check for processes using the database
lsof | grep database.db
```

### Memory issues with large databases

For very large databases (>1GB), process in batches:

```python
# Modify the scripts to add LIMIT clauses to queries
# Or run separately for each division
```

## Performance

Typical performance on a database with:
- 171 teams
- 2,400 players
- 400 games
- 5,000+ goals

**Analysis time**: ~30 seconds
**Report size**: ~5-10 MB JSON

## Best Practices

1. **Run analyzer first** - Get baseline quality assessment
2. **Monitor regularly** - Weekly or after each data extraction
3. **Prioritize critical issues** - Focus on confidence_impact > 0.5
4. **Track resolution** - Always use --resolved-by and --notes
5. **Version control reports** - Keep historical quality reports
6. **Set quality gates** - Require overall_quality_score > 0.8 for production
7. **Automate checks** - Add to data pipeline/cron jobs

## Support

For issues or questions:
- Check that database schema matches expected structure
- Review ADVANCED_STATS_API_DESIGN.md for schema details
- Verify Python 3.6+ is installed
- Check file permissions on database and output directory
