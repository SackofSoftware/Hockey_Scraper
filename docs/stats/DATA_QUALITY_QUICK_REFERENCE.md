# Data Quality System - Quick Reference

## Common Commands

### Analyze Database Quality
```bash
# Basic analysis
python3 data_quality_analyzer.py --db hockey.db

# Save issues to database for tracking
python3 data_quality_analyzer.py --db hockey.db --save-to-db

# Specify output file
python3 data_quality_analyzer.py --db hockey.db --output report.json
```

### Monitor & Track Issues
```bash
# Generate quality report
python3 data_quality_monitor.py --db hockey.db

# List all unresolved issues
python3 data_quality_monitor.py --db hockey.db --list-issues

# List only critical issues
python3 data_quality_monitor.py --db hockey.db --list-issues --severity critical

# Resolve an issue
python3 data_quality_monitor.py --db hockey.db --resolve 5 --resolved-by "Your Name" --notes "Fixed the problem"
```

---

## Quality Scores Explained

| Score | Quality Level | Action |
|-------|---------------|--------|
| 0.9 - 1.0 | Excellent | Production ready |
| 0.8 - 0.9 | Good | Minor fixes recommended |
| 0.7 - 0.8 | Acceptable | Review issues |
| 0.5 - 0.7 | Poor | Needs attention |
| < 0.5 | Critical | Major problems |

---

## Issue Severity Levels

| Severity | Impact | Examples |
|----------|--------|----------|
| **Critical** | >0.5 | Missing game scores, corrupt data |
| **Warning** | 0.2-0.5 | Player number inconsistency, high scoring games |
| **Info** | <0.2 | Missing box scores, minor incompleteness |

---

## Common Issues & Fixes

### Player Number Inconsistency
**Issue**: Player appears with different jersey numbers
```bash
# List the issue
python3 data_quality_monitor.py --db hockey.db --list-issues

# If legitimate number change
python3 data_quality_monitor.py --db hockey.db --resolve [ID] --notes "Player changed number mid-season"

# If data error - fix the source data, then reanalyze
```

### Missing Player Names
**Issue**: Players have empty name fields
```bash
# Identify affected players in report
python3 data_quality_analyzer.py --db hockey.db --output report.json

# Fix by updating player table
sqlite3 hockey.db "UPDATE players SET player_name='John Smith' WHERE player_id='p123'"

# Reanalyze
python3 data_quality_analyzer.py --db hockey.db
```

### Suspiciously High Stats
**Issue**: Player has unrealistic point totals
```bash
# Find in report under player_confidence_scores with flags
# Check for duplicate goal entries
sqlite3 hockey.db "SELECT * FROM goals WHERE scorer_player_id='p123'"

# Remove duplicates if found
# Then rerun analysis
```

### Missing Game Scores
**Issue**: Game has NULL home_score or visitor_score
```bash
# Update the game
sqlite3 hockey.db "UPDATE games SET home_score=5, visitor_score=3 WHERE game_id='game_123'"

# Reanalyze
python3 data_quality_analyzer.py --db hockey.db
```

---

## Report Structure

### Analyzer Output (data_quality_analyzer.py)
```json
{
  "analysis_timestamp": "...",
  "overall_quality_score": 0.970,
  "player_number_issues": [...],
  "player_confidence_scores": [...],
  "duplicate_players": [...],
  "game_quality_issues": [...],
  "missing_data_summary": {...}
}
```

### Monitor Output (data_quality_monitor.py)
```json
{
  "generated_at": "...",
  "player_scores": [...],
  "game_scores": [...],
  "team_scores": [...],
  "issue_summary": {
    "total_unresolved": 10,
    "critical": 2,
    "warnings": 8
  },
  "overall_statistics": {
    "overall_quality": 0.873
  },
  "recommendations": [...]
}
```

---

## Database Tables

### data_quality_issues
Stores all detected issues:
```sql
SELECT * FROM data_quality_issues WHERE is_resolved = 0;
SELECT * FROM data_quality_issues WHERE issue_type = 'number_inconsistency';
SELECT * FROM data_quality_issues ORDER BY confidence_impact DESC LIMIT 10;
```

### quality_scores
Historical quality metrics:
```sql
SELECT entity_type, AVG(score_value) FROM quality_scores GROUP BY entity_type;
```

### quality_monitoring_log
Monitoring history:
```sql
SELECT monitor_timestamp, overall_score, total_issues FROM quality_monitoring_log ORDER BY monitor_timestamp DESC;
```

---

## Integration Example

```python
from data_quality_analyzer import DataQualityAnalyzer
from data_quality_monitor import DataQualityMonitor

# Analyze
analyzer = DataQualityAnalyzer("hockey.db")
results = analyzer.analyze_all()
analyzer.save_to_database(results)
analyzer.close()

# Check quality
if results["overall_quality_score"] < 0.8:
    print("Quality below threshold!")

# Monitor
monitor = DataQualityMonitor("hockey.db")
report = monitor.generate_quality_report()

# Get critical issues
critical = monitor.get_unresolved_issues("critical")
for issue in critical:
    print(f"Fix needed: {issue['description']}")

monitor.close()
```

---

## Troubleshooting

### "No such column: game_api_id"
**Fix**: Scripts auto-detect columns. Ensure you have latest version.

### "Database is locked"
**Fix**: Close other database connections:
```bash
lsof | grep hockey.db  # Find processes
kill [PID]              # Kill if needed
```

### "No tables found"
**Fix**: Verify database has data:
```bash
sqlite3 hockey.db "SELECT name FROM sqlite_master WHERE type='table';"
```

### Large database is slow
**Fix**: Add indexes:
```sql
CREATE INDEX idx_goals_player ON goals(scorer_player_id);
CREATE INDEX idx_goals_game ON goals(game_id);
CREATE INDEX idx_games_date ON games(game_date);
```

---

## Performance Tips

1. **Run analyzer once**, then use monitor for ongoing checks
2. **Save to database** to track issues over time
3. **Filter by severity** to focus on critical issues first
4. **Schedule weekly** automated quality checks
5. **Keep historical reports** for trend analysis

---

## Best Practices

✅ **DO**: Run quality analysis after each data extraction
✅ **DO**: Track and resolve issues systematically
✅ **DO**: Keep resolution notes detailed
✅ **DO**: Export reports for documentation

❌ **DON'T**: Ignore critical issues
❌ **DON'T**: Delete issue records (mark resolved instead)
❌ **DON'T**: Run on production database during peak hours
❌ **DON'T**: Skip verification after fixes

---

## Getting Help

1. Check `DATA_QUALITY_INSTRUCTIONS.md` for detailed usage
2. Review `EXAMPLE_QUALITY_FINDINGS.md` for sample results
3. Read `DATA_QUALITY_SUMMARY.md` for implementation details
4. Test with `test_hockey_data.db` sample database

---

**Version**: 1.0
**Last Updated**: November 2025
**Compatibility**: Python 3.6+, SQLite3
