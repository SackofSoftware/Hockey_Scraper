# SSC Hockey Comprehensive Scraping Session Report

**Date:** November 8, 2025
**League:** South Shore Conference (SSC Hockey)
**League ID:** 224428
**Subseason ID:** 948564

---

## Executive Summary

This report documents a comprehensive scraping session for SSC Hockey, analyzing the current scraper capabilities and identifying opportunities for expansion. The scraping session successfully collected baseline schedule data and explored multiple page types to identify additional data sources.

---

## 1. Baseline Scrape Results

### 1.1 Scrape Summary

**Command:**
```bash
python3 ssc_hockey_scraper.py --league-id 224428 --subseason-id 948564 --out data/ssc_full_scrape
```

**Results:**
- **Games Scraped:** 74
- **Teams Identified:** 148 (visitor and home teams counted separately)
- **Players Collected:** 0 (roster scraping not yet implemented)
- **Output Files:**
  - `data/ssc_full_scrape/schedules.json`
  - `data/ssc_full_scrape/teams.json`

### 1.2 Data Quality Analysis

**Schedule Data Fields:**
- `game_id` - Unique identifier (e.g., "44492111")
- `date` - Game date (e.g., "11/8/2025")
- `time` - Game time (e.g., "6:50 AM EST") or empty string for cancelled games
- `visitor_team` - Away team name with division prefix (e.g., "8BH - NRI Vikings White")
- `home_team` - Home team name with division prefix
- `visitor_score` - Score (null for future/unplayed games)
- `home_score` - Score (null for future/unplayed games)
- `location` - Full rink address (e.g., "Foxboro Rink 3 - 10 E Belcher Rd, Foxborough, MA, 02035")
- `status` - Game status ("Cancelled", time string, etc.)
- `division` - Division code (e.g., "8BH", "10BR", "10A")
- `game_url` - Link to game detail page
- `source_url` - Source schedule page URL

**Issues/Missing Fields:**
- No final scores for completed games (all games have `null` scores)
- Some games have empty `time` field when status is "Cancelled"
- Team data lacks URLs and IDs (team_url: "", team_id: null)

**Divisions Identified:**
- 8A, 8BH, 8BR, 8B2H, 8B2R
- 10A, 10BH, 10BR, 10B2H, 10B2R
- 12AH, 12AR, 12BH, 12BR, 12B2H, 12B2R
- 14A, 14BH, 14BR, 14B2
- 18A, 18BR

---

## 2. Game Detail Page Analysis

### 2.1 Probe Script Results

**Command:**
```bash
python3 ssc_probe_script.py --game-urls data/ssc_full_scrape/schedules.json --out data/ssc_probe --num-samples 10
```

**Success Rate:**
- 7 out of 10 pages loaded successfully (3 timeouts)
- Timeout issues likely due to network/server load

### 2.2 Available Data on Game Detail Pages

**Sections Found:**
- Game Details
- General Info
- Location & Weather
- Team names with division
- Page Search

**Data Types Detected:**
- **Period Scores:** Line score table with columns for periods 1, 2, 3, and Total (T)
- **Player Statistics:** Player stats are available (detected via keywords)
- **Goalie Statistics:** Goalie leader stats available
- **Game Notes:** Notes/recap section available

**Tables Found:**
- **Line Score Table:**
  - Class: `stat_table line_score_v2 player_stats-list`
  - Columns: [blank], 1, 2, 3, T
  - Rows: 3 (header + 2 team rows)

### 2.3 Sample Data from Game Detail Pages

**Example Game:** 10BH - Canton at 10BH - Milton Red (Game ID: 44491353)
- **URL:** https://www.ssc-hockey.org/game/show/44491353?subseason=948564&referrer=9115690
- **Available Data:**
  - Period-by-period scores (1st, 2nd, 3rd, Total)
  - Player stat leaders (top performers)
  - Goalie leader stats
  - Location details
  - Weather information
  - Game notes/recap

**HTML File Locations:**
- `/path/to/Hockey_Scraper/data/ssc_probe/game_*.html`
- Full analysis in: `data/ssc_probe/findings.json` and `summary.txt`

---

## 3. Additional Page Types Discovered

### 3.1 Page Explorer Results

**Command:**
```bash
python3 ssc_explore_pages.py --league-id 224428 --subseason-id 948564 --out data/ssc_exploration
```

### 3.2 Standings Pages

**Working URL:**
✅ `https://www.ssc-hockey.org/stats/league_instance/224428?subseason=948564&tab=league_instance_standings`
- Has standings data
- Contains tables
- Title: "Statistics - 2025-2026 Regular Season - South Shore Conference"

**Non-Working URLs:**
❌ `https://www.ssc-hockey.org/standings/league_instance/224428?subseason=948564` (404)
❌ `https://www.ssc-hockey.org/standings/division/league_instance/224428?subseason=948564` (404)

### 3.3 Statistics Pages

**All Working URLs:**
✅ `https://www.ssc-hockey.org/stats/league_instance/224428?subseason=948564`
- Has stats data
- Contains tables

✅ `https://www.ssc-hockey.org/stats/league_instance/224428?subseason=948564&tab=league_instance_player_stats`
- Player statistics available
- Contains sortable tables

✅ `https://www.ssc-hockey.org/stats/league_instance/224428?subseason=948564&tab=league_instance_goalie_stats`
- Goalie statistics available
- Contains sortable tables

### 3.4 Team/Roster Pages

**Status:** ❌ Not Available
- All attempted team page URLs returned 404
- Team roster links not found in current implementation
- Team URLs stored in teams.json are empty strings

### 3.5 Playoff/Bracket Pages

**Status:** ❌ Not Available
- All attempted playoff/bracket URLs returned 404
- May not be active during regular season
- Could become available during playoff period

---

## 4. URL Patterns Discovered

### 4.1 Working URL Patterns

```
Schedule Page:
https://www.ssc-hockey.org/schedule/day/league_instance/{league_id}?subseason={subseason_id}

Game Detail Page:
https://www.ssc-hockey.org/game/show/{game_id}?subseason={subseason_id}&referrer={referrer_id}

Statistics Pages:
https://www.ssc-hockey.org/stats/league_instance/{league_id}?subseason={subseason_id}
https://www.ssc-hockey.org/stats/league_instance/{league_id}?subseason={subseason_id}&tab=league_instance_player_stats
https://www.ssc-hockey.org/stats/league_instance/{league_id}?subseason={subseason_id}&tab=league_instance_goalie_stats
https://www.ssc-hockey.org/stats/league_instance/{league_id}?subseason={subseason_id}&tab=league_instance_standings
```

### 4.2 Non-Working URL Patterns

```
Team Pages:
https://www.ssc-hockey.org/teams/league_instance/{league_id}?subseason={subseason_id}
https://www.ssc-hockey.org/teams/league_instance/{league_id}

Standings Pages (alternate):
https://www.ssc-hockey.org/standings/league_instance/{league_id}?subseason={subseason_id}
https://www.ssc-hockey.org/standings/division/league_instance/{league_id}?subseason={subseason_id}

Playoff Pages:
https://www.ssc-hockey.org/playoffs/league_instance/{league_id}?subseason={subseason_id}
https://www.ssc-hockey.org/brackets/league_instance/{league_id}?subseason={subseason_id}
```

---

## 5. Recommendations for Expanding the Scraper

### 5.1 High Priority Enhancements

1. **Game Detail Scraping**
   - Parse period-by-period scores from line score table
   - Extract player stat leaders (goals, assists, points)
   - Extract goalie leaders (saves, shots against)
   - Capture game notes/recap text
   - Add to existing `_scrape_game_details()` method

2. **Statistics Page Scraping**
   - Create new method `_scrape_league_stats()`
   - Parse player statistics table:
     - Player name, number, team
     - Goals, assists, points
     - Games played
     - Other available stats
   - Parse goalie statistics table:
     - Goalie name, team
     - Games played, wins, losses
     - Saves, shots against, save percentage
     - Goals against average

3. **Standings Page Scraping**
   - Create new method `_scrape_standings()`
   - Parse standings by division
   - Extract: team name, wins, losses, ties, points, goals for/against

### 5.2 Medium Priority Enhancements

4. **Enhanced Schedule Scraping**
   - The current scraper only gets one day's schedule
   - Modify to iterate through multiple dates
   - Add date range parameters (--start-date, --end-date)
   - Could scrape entire season schedule

5. **Score Updates**
   - Revisit game detail pages for completed games
   - Update schedule data with final scores
   - Parse scoring summary for goal details (scorer, assists, time)

6. **Data Enrichment**
   - Cross-reference player stats with game data
   - Calculate aggregate team statistics
   - Build player profiles combining roster + stats

### 5.3 Low Priority / Future Enhancements

7. **Team Roster Pages**
   - Investigate alternative methods to find team pages
   - May require examining schedule page HTML for team links
   - Parse from team stats pages instead

8. **Playoff Data** (when available)
   - Monitor for playoff bracket availability
   - Scrape playoff game results
   - Track tournament progression

9. **Historical Data**
   - Archive completed season data
   - Compare season-over-season stats
   - Track player development across seasons

---

## 6. Technical Implementation Notes

### 6.1 Platform Details

- **Website:** SSC Hockey (www.ssc-hockey.org)
- **Platform:** SportsEngine (Ngin platform)
- **Technology:** Server-rendered HTML (not a SPA)
- **Scraping Method:** Playwright + BeautifulSoup
- **Data Format:** HTML tables with class `statTable`

### 6.2 HTML Structure Patterns

**Schedule Table:**
- Class: `statTable`
- Row ID pattern: `game_list_row_{game_id}`
- Cells: [Visitor, Score, Home, Score, Location, Status]

**Line Score Table:**
- Class: `stat_table line_score_v2 player_stats-list`
- Row ID pattern: `lineScore-team-{team_id}`
- Columns: Team, Period 1, Period 2, Period 3, Total

**Stats Tables:**
- Class: `dataTable statTable theme-stat-table`
- Uses NginTable JavaScript for sorting
- Pagination may be present

### 6.3 Scraping Challenges

1. **Timeout Issues:**
   - Some pages take >60 seconds to load
   - May need to increase timeout or implement retry logic
   - Could be rate-limiting or server performance

2. **Dynamic Content:**
   - Some content may load via JavaScript
   - Current wait strategy: 2 seconds after domcontentloaded
   - May need to wait for specific elements

3. **Session Management:**
   - No authentication required (public data)
   - No obvious rate limiting detected
   - Consider adding delays between requests as courtesy

---

## 7. Sample Code Snippets for Enhancements

### 7.1 Parsing Line Scores

```python
def _parse_line_score(self, soup: BeautifulSoup, game: Game):
    """Parse period-by-period scores from game detail page."""
    line_score_table = soup.find('table', class_='line_score_v2')
    if not line_score_table:
        return None

    rows = line_score_table.find_all('tr', id=lambda x: x and 'lineScore-team' in x)

    scores = {}
    for row in rows:
        team_id = row.get('id').replace('lineScore-team-', '')
        cells = row.find_all('td')

        if len(cells) >= 4:
            scores[team_id] = {
                'period_1': cells[0].text.strip(),
                'period_2': cells[1].text.strip(),
                'period_3': cells[2].text.strip(),
                'total': cells[3].text.strip()
            }

    return scores
```

### 7.2 Scraping Player Statistics

```python
async def _scrape_player_stats(self, page: Page):
    """Scrape league-wide player statistics."""
    stats_url = f"{self.BASE_URL}/stats/league_instance/{self.league_id}?subseason={self.subseason_id}&tab=league_instance_player_stats"

    await page.goto(stats_url, wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(2000)

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    stats_table = soup.find('table', class_='statTable')
    if not stats_table:
        return

    rows = stats_table.find('tbody').find_all('tr')

    for row in rows:
        cells = row.find_all('td')
        # Parse: Player Name, Team, GP, G, A, PTS, etc.
        # Add to self.players list with stats
```

### 7.3 Scraping Standings

```python
async def _scrape_standings(self, page: Page):
    """Scrape division standings."""
    standings_url = f"{self.BASE_URL}/stats/league_instance/{self.league_id}?subseason={self.subseason_id}&tab=league_instance_standings"

    await page.goto(standings_url, wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(2000)

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    # Find all standings tables (one per division)
    standings_tables = soup.find_all('table', class_='statTable')

    for table in standings_tables:
        # Extract division name from nearby header
        # Parse table rows for team standings
        # Store in new Standings dataclass
```

---

## 8. Data Storage Recommendations

### 8.1 Additional Dataclasses Needed

```python
@dataclass
class GameDetails:
    """Extended game information from detail page."""
    game_id: str
    period_1_visitor: int
    period_1_home: int
    period_2_visitor: int
    period_2_home: int
    period_3_visitor: int
    period_3_home: int
    final_visitor: int
    final_home: int
    game_notes: str
    source_url: str

@dataclass
class PlayerStats:
    """Player statistics."""
    player_name: str
    team: str
    division: str
    games_played: int
    goals: int
    assists: int
    points: int
    source_url: str

@dataclass
class GoalieStats:
    """Goalie statistics."""
    goalie_name: str
    team: str
    division: str
    games_played: int
    wins: int
    losses: int
    saves: int
    shots_against: int
    save_percentage: float
    goals_against_avg: float
    source_url: str

@dataclass
class Standings:
    """Team standings."""
    team: str
    division: str
    wins: int
    losses: int
    ties: int
    points: int
    goals_for: int
    goals_against: int
    source_url: str
```

### 8.2 Output Files

Recommended additional JSON files:
- `game_details.json` - Extended game information
- `player_stats.json` - Player statistics
- `goalie_stats.json` - Goalie statistics
- `standings.json` - Team standings by division

---

## 9. Estimated Implementation Effort

| Enhancement | Effort | Lines of Code | Testing Time |
|-------------|--------|---------------|--------------|
| Game Details Parsing | 2-3 hours | ~100 lines | 1 hour |
| Player Stats Scraping | 2-3 hours | ~80 lines | 1 hour |
| Goalie Stats Scraping | 1-2 hours | ~60 lines | 30 min |
| Standings Scraping | 2-3 hours | ~80 lines | 1 hour |
| Multi-Date Schedule | 1-2 hours | ~50 lines | 30 min |
| Total | 8-13 hours | ~370 lines | 4 hours |

---

## 10. Scripts Created During This Session

1. **`ssc_probe_script.py`**
   - Purpose: Probe game detail pages to identify available data
   - Location: `/path/to/Hockey_Scraper/ssc_probe_script.py`
   - Usage: `python3 ssc_probe_script.py --game-urls schedules.json --out output_dir --num-samples N`

2. **`ssc_explore_pages.py`**
   - Purpose: Explore different page types (standings, stats, teams, playoffs)
   - Location: `/path/to/Hockey_Scraper/ssc_explore_pages.py`
   - Usage: `python3 ssc_explore_pages.py --league-id ID --subseason-id ID --out output_dir`

---

## 11. Key Findings Summary

### What Works
✅ Schedule scraping (single day)
✅ Basic team extraction from games
✅ Game detail pages load successfully (with some timeouts)
✅ Statistics pages are accessible and contain data
✅ Standings page is accessible via stats tab

### What Doesn't Work
❌ Team roster pages (404)
❌ Playoff/bracket pages (404 - may be seasonal)
❌ Direct standings URLs (404)
❌ Multi-date schedule scraping (not implemented)
❌ Final score collection (not implemented)

### What's Missing
⚠️ Player roster data
⚠️ Game scores (period-by-period and final)
⚠️ Individual player statistics
⚠️ Goalie statistics
⚠️ Team standings
⚠️ Scoring details (who scored, when, assists)
⚠️ Penalty information

---

## 12. Conclusion

The SSC Hockey scraping infrastructure is functional and successfully collects baseline schedule data. The website contains a wealth of additional data including:

- **Game Details:** Period scores, player leaders, game notes
- **Statistics:** Comprehensive player and goalie statistics
- **Standings:** Division standings with team records

The main opportunities for expansion are:

1. **Immediate Value:** Implement game detail scraping to collect scores
2. **High Value:** Add statistics and standings scraping for complete league picture
3. **Future Value:** Multi-date scheduling and historical data archiving

All necessary URL patterns have been identified and validated. The HTML structure is consistent and parseable. Implementation should be straightforward using the existing Playwright/BeautifulSoup framework.

---

## Appendix: File Locations

**Scraped Data:**
- `/path/to/Hockey_Scraper/data/ssc_full_scrape/schedules.json`
- `/path/to/Hockey_Scraper/data/ssc_full_scrape/teams.json`

**Probe Results:**
- `/path/to/Hockey_Scraper/data/ssc_probe/findings.json`
- `/path/to/Hockey_Scraper/data/ssc_probe/summary.txt`
- `/path/to/Hockey_Scraper/data/ssc_probe/game_*.html`

**Exploration Results:**
- `/path/to/Hockey_Scraper/data/ssc_exploration/exploration_findings.json`
- `/path/to/Hockey_Scraper/data/ssc_exploration/exploration_summary.txt`
- `/path/to/Hockey_Scraper/data/ssc_exploration/standings_*.html`
- `/path/to/Hockey_Scraper/data/ssc_exploration/stats_*.html`
