# SSC Hockey Scraper - Quick Reference Guide

## Basic Usage (Original Behavior)
```bash
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data
```
Scrapes the current schedule page only.

## New Multi-Date Features

### Scrape All Calendar Dates
```bash
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data \
  --all-dates
```

### Limit Number of Dates (for Testing)
```bash
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data/test \
  --all-dates \
  --max-dates 3
```

### Scrape Specific Date
```bash
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data \
  --date 2024_01_15
```

### Debug Mode (Show Browser)
```bash
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data \
  --all-dates \
  --max-dates 5 \
  --headed
```

## Output Structure

```
data/
├── schedules.json    # All games (deduplicated)
├── teams.json        # All teams extracted from games
└── players.json      # Player data (if roster scraping enabled)
```

## Date Format
Dates use underscore-separated format: `YYYY_MM_DD`
- Example: `2024_01_15` for January 15, 2024
- Example: `2025_12_31` for December 31, 2025

## Features at a Glance

| Feature | Flag | Description |
|---------|------|-------------|
| Default mode | (none) | Scrapes current schedule page |
| All dates | `--all-dates` | Scrapes all dates from calendar |
| Limit dates | `--max-dates N` | Scrapes only first N dates |
| Specific date | `--date YYYY_MM_DD` | Scrapes single specific date |
| Debug mode | `--headed` | Shows browser window |

## What's New?

1. **Multi-date scraping**: Extract and scrape all dates from the calendar slider
2. **Progress tracking**: See "Scraping date 5/100..." for each date
3. **Rate limiting**: 500ms delay between requests
4. **Deduplication**: Automatically removes duplicate games across dates
5. **Error resilience**: Continues if one date fails
6. **Flexible testing**: Use `--max-dates` to test with subset

## Troubleshooting

### Site Timeout
If you get timeout errors:
```
playwright._impl._errors.TimeoutError: Page.goto: Timeout 60000ms exceeded
```
The SSC Hockey website may be temporarily unavailable. Try again later or check your internet connection.

### No Calendar Found
If you see:
```
[!] Warning: Could not find calendar slider
```
The calendar structure may have changed. Check the HTML with `--headed` flag.

### No Games Found
If scraping completes but finds 0 games:
- Verify league-id and subseason-id are correct
- Check if the schedule page has data for those IDs
- Try `--headed` mode to see what the page looks like

## Development Notes

- Implementation file: `/path/to/Hockey_Scraper/ssc_hockey_scraper.py`
- Test suite: `/path/to/Hockey_Scraper/test_multidate_scraper.py`
- Documentation: `/path/to/Hockey_Scraper/MULTI_DATE_IMPLEMENTATION_SUMMARY.md`
