# SSC Hockey Scraper - Usage Guide

## Overview

The `ssc_hockey_scraper.py` scrapes schedule and game data from SSC Hockey (SportsEngine platform) websites using HTML parsing with Playwright and BeautifulSoup.

**Key Difference from GameSheet Stats:**
- GameSheet Stats: API interception (JSON responses)
- SSC Hockey: HTML parsing (server-rendered pages)

## Quick Start

### Basic Usage

```bash
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data/ssc_hockey
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--league-id` | Yes | League instance ID from URL | `224428` |
| `--subseason-id` | Yes | Subseason ID from URL | `948564` |
| `--out` | No | Output directory (default: `data`) | `data/ssc_hockey` |
| `--headed` | No | Run browser in visible mode (for debugging) | N/A (flag) |

### Finding IDs

IDs are found in the schedule URL:

```
https://www.ssc-hockey.org/schedule/day/league_instance/224428?subseason=948564
                                                          ^^^^^^            ^^^^^^
                                                        league-id      subseason-id
```

## Output Files

The scraper creates JSON files in the output directory:

### 1. `schedules.json`

Array of game objects:

```json
{
  "game_id": "44492111",
  "date": "11/8/2025",
  "time": "6:50 AM EST",
  "visitor_team": "8BH - NRI Vikings White",
  "home_team": "8BH - Franklin",
  "visitor_score": null,
  "home_score": null,
  "location": "Foxboro Rink 3 - 10 E Belcher Rd, Foxborough, MA, 02035",
  "status": "6:50 AM EST",
  "division": "8BH",
  "game_url": "https://www.ssc-hockey.org/game/show/44492111?subseason=948564&referrer=9115690",
  "source_url": "https://www.ssc-hockey.org/schedule/day/league_instance/224428?subseason=948564"
}
```

**Fields:**
- `game_id`: Unique game identifier
- `date`: Game date (from page title)
- `time`: Game time
- `visitor_team`: Away team name
- `home_team`: Home team name
- `visitor_score`: Away team score (null if not played)
- `home_score`: Home team score (null if not played)
- `location`: Rink/arena location
- `status`: Game status or time
- `division`: Division code extracted from team name
- `game_url`: Link to game detail page
- `source_url`: Schedule page URL

### 2. `teams.json`

Array of team objects:

```json
{
  "name": "8BH - NRI Vikings White",
  "division": "8BH",
  "team_url": "",
  "team_id": null
}
```

**Note:** Currently, team URLs and IDs are placeholders. These can be populated by enabling roster scraping.

## Current Limitations

The current version scrapes **schedule data only**. Additional features are stubbed out but not yet implemented:

### Not Yet Implemented:

1. **Game Detail Scraping** (`_scrape_game_details`)
   - Box scores
   - Detailed stats
   - Game summaries

2. **Roster Scraping** (`_scrape_rosters`)
   - Player names
   - Jersey numbers
   - Positions

3. **Multi-Date Scraping**
   - Currently scrapes one day's schedule
   - No date navigation implemented

### To Enable (Requires Development):

Uncomment these lines in `scrape()` method (line ~61-65):

```python
# Optional: scrape individual game details
# await self._scrape_game_details(page)

# Optional: scrape team rosters
# await self._scrape_rosters(page)
```

Then implement the HTML parsing logic for those pages.

## Architecture

### HTML Structure

SSC Hockey uses this table structure:

```html
<table class="statTable sortable noSortImages">
  <thead>
    <tr>
      <th>Visitor</th>
      <th>V</th>
      <th>Home</th>
      <th>H</th>
      <th>Location</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    <tr class="odd scheduled compactGameList" id="game_list_row_44492111">
      <td>
        <a class="teamName" href="...">8BH - NRI Vikings White</a>
      </td>
      <td>-</td>
      <td>
        <a class="teamName" href="...">8BH - Franklin</a>
      </td>
      <td>-</td>
      <td>Foxboro Rink 3 - 10 E Belcher Rd...</td>
      <td>6:50 AM EST</td>
    </tr>
    <!-- more rows -->
  </tbody>
</table>
```

### Key Selectors

| Element | Selector | Purpose |
|---------|----------|---------|
| Schedule table | `table.statTable` | Main game schedule |
| Game rows | `tr.compactGameList` | Individual games |
| Team links | `a.teamName` | Team names and URLs |
| Game ID | `tr[id^="game_list_row_"]` | Extract game ID from row ID |
| Game detail link | `a[href*="game/show"]` | Link to game page |

## Extending the Scraper

### Adding Game Detail Scraping

1. Navigate to a game URL (from `game.game_url`)
2. Parse the page HTML
3. Look for box score tables, player stats, etc.
4. Add data to game object or create new data structures

Example:

```python
async def _scrape_game_details(self, page: Page):
    for game in self.games:
        await page.goto(game.game_url)
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Find box score
        boxscore = soup.find('div', class_='boxscore')
        # Parse stats...
```

### Adding Roster Scraping

1. Find roster/team page URLs
2. Navigate to roster pages
3. Parse player tables
4. Create Player objects

## Comparison with sprocket_scraper.py

| Feature | sprocket_scraper.py | ssc_hockey_scraper.py |
|---------|---------------------|------------------------|
| **Target Site** | GameSheet Stats | SSC Hockey (SportsEngine) |
| **Method** | API interception | HTML parsing |
| **Data Format** | JSON (from API) | HTML (from server) |
| **Approach** | Capture XHR responses | BeautifulSoup parsing |
| **Complexity** | Moderate | Simple |
| **Reliability** | High (JSON schema) | Medium (HTML changes) |

## Troubleshooting

### "Could not find schedule table"

- The page structure may have changed
- Check if the league/subseason IDs are correct
- Run with `--headed` to see the page visually

### Incorrect Data

- View the raw HTML: `ssc_schedule_page.html` (created by `analyze_ssc_html.py`)
- Check the HTML structure and update selectors

### Timeout Errors

- Increase timeout in `page.goto()` calls
- Check internet connection
- SSC Hockey site may be slow or down

## Example Workflow

1. **Find the schedule URL** on SSC Hockey website
2. **Extract IDs** from the URL
3. **Run the scraper:**
   ```bash
   python3 ssc_hockey_scraper.py --league-id 224428 --subseason-id 948564 --out data/ssc
   ```
4. **Check output:**
   ```bash
   cat data/ssc/schedules.json
   ```
5. **Load to SQLite** (using existing loader):
   ```bash
   python3 load_to_sqlite.py --in-dir data/ssc --db ssc_hockey.db
   ```

## Future Enhancements

- [ ] Multi-date schedule scraping
- [ ] Game detail/boxscore scraping
- [ ] Roster/player scraping
- [ ] Standing/stats scraping
- [ ] Automatic date iteration
- [ ] Error recovery and retry logic
- [ ] Progress tracking for large scrapes
