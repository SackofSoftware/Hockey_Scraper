# SSC Hockey Game Detail Scraping - Quick Start

## What's New

Enhanced the SSC Hockey scraper to capture detailed game statistics including:
- Period-by-period scores
- Scoring summary (goals with assists)
- Penalties
- Shots on goal

## Quick Usage

### Basic Schedule Scraping (No Changes)
```bash
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data
```

### NEW: Schedule + Game Details
```bash
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data \
  --scrape-game-details
```

### Test with Limited Data
```bash
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data/test \
  --max-dates 1 \
  --scrape-game-details
```

## Validate Results

```bash
python3 validate_game_details.py data/test/schedules.json
```

## Output Format

Games now include these additional fields in `schedules.json`:

```json
{
  "game_id": "43817649",
  "visitor_team": "8B2R - Tri-County Black",
  "home_team": "8B2R - WHK",
  "visitor_score": "2",
  "home_score": "1",

  "period_scores": {
    "1st": {"visitor": 1, "home": 0},
    "2nd": {"visitor": 0, "home": 1},
    "3rd": {"visitor": 1, "home": 0}
  },

  "scoring_summary": [
    {
      "period": "1st",
      "time": "5:23",
      "player": "John Smith",
      "assists": ["Mike Jones", "Tom Wilson"]
    }
  ],

  "penalties": [
    {
      "period": "1st",
      "time": "8:15",
      "player": "Tom Wilson",
      "penalty": "Tripping",
      "minutes": 2
    }
  ],

  "shots_on_goal": {
    "1st": 10,
    "2nd": 8,
    "3rd": 12,
    "total": 30
  }
}
```

## Files

- `ssc_hockey_scraper.py` - Main scraper (enhanced)
- `validate_game_details.py` - Validation script
- `test_game_details_output.json` - Example output
- `IMPLEMENTATION_SUMMARY.md` - Detailed documentation
- `GAME_DETAILS_IMPLEMENTATION.md` - Technical details

## Notes

- Game details are only scraped for games with URLs
- Unplayed games will have `null` for all detail fields
- Rate limiting: 1 second between game detail requests
- Some games may not have statistics entered (shows "No Player Data Available")

## Testing

Run the validation script to check data quality:

```bash
python3 validate_game_details.py data/test/schedules.json
```

Expected output:
```
[*] Validating game details from: data/test/schedules.json
[*] Loaded 57 games

============================================================
VALIDATION SUMMARY
============================================================
Total games:                    57
Games with scores:              12
Unplayed games:                 45

Games with period scores:       8 (66.7%)
Games with scoring summary:     8 (66.7%)
Games with penalties:           6 (50.0%)
Games with shots on goal:       8 (66.7%)

[OK] No validation errors found!
```

## Troubleshooting

### Timeout errors
The SSC Hockey website can be slow. Try:
- Using `--max-dates 1` for smaller tests
- Running during off-peak hours
- Using `--headed` to see what's happening

### No statistics found
Not all games have detailed statistics entered. This is normal for:
- Future/unplayed games
- Recently completed games (stats not yet entered)
- Some leagues may not enter detailed stats

## Command-Line Arguments

```
Required:
  --league-id ID          League instance ID (e.g., 224428)
  --subseason-id ID       Subseason ID (e.g., 948564)

Optional:
  --out DIR               Output directory (default: data)
  --scrape-game-details   Scrape detailed game statistics (NEW)
  --max-dates N           Limit number of dates to scrape
  --date YYYY_MM_DD       Scrape specific date
  --all-dates             Scrape all dates from calendar
  --headed                Run browser in headed mode (see what's happening)
```

## Performance

- Schedule scraping: ~2-5 seconds per date
- Game details: ~2-3 seconds per game (including 1 second rate limit)
- Example: 50 games = ~2-3 minutes for details

## Support

For detailed implementation information, see:
- `IMPLEMENTATION_SUMMARY.md` - Complete overview
- `GAME_DETAILS_IMPLEMENTATION.md` - Technical deep dive
