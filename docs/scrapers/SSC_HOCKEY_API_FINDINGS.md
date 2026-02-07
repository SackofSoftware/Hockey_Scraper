# SSC Hockey API Investigation Results

## Summary

**Unlike GameSheet Stats, SSC Hockey does NOT use JSON API endpoints for schedule/game data.** The site is built on SportsEngine's proprietary NGIN platform and serves all schedule, game, roster, and player data as server-rendered HTML.

## Key Findings

### 1. Platform Architecture
- **Platform**: SportsEngine Sports Relationship Management (SRM)
- **Framework**: NGIN (proprietary SportsEngine framework)
- **Rendering**: Server-side HTML rendering (NOT a Single Page Application)
- **Data Loading**: Traditional page loads, not dynamic JSON API calls

### 2. API Endpoints Discovered

#### Only One API Endpoint Found:
```
GET https://www.ssc-hockey.org/apigateway/v3/utd
```

**Parameters:**
- `platform=ngin`
- `org_id=181469` (South Shore Conference organization ID)
- `platformSubSec=cms`

**Purpose:** User/Organization metadata and authentication
- Organization details (name, sports, products, billing)
- User authentication status
- Intercom and Elevio support widget configuration

**Response Structure:**
```json
{
  "metadata": {
    "trace_id": "..."
  },
  "result": {
    "organization": {
      "id": 181469,
      "name": "South Shore Conference",
      "sports": ["ice_hockey"],
      "service_level": "Premier",
      "organization_products": ["Platform", "Sitebuilder", "Registration", ...]
    },
    "user": {
      "id": "",
      "logged_in": false,
      ...
    }
  }
}
```

**This endpoint does NOT provide:**
- ❌ Game schedules
- ❌ Team rosters
- ❌ Player statistics
- ❌ Division standings
- ❌ Game results/scores

### 3. How Schedule Data is Served

All schedule, game, roster, and player data is **embedded directly in server-rendered HTML**:

- Schedule page: HTML tables with game information
- Game detail pages: `/game/show/{game_id}?subseason={subseason_id}`
- Stats pages: `/stats/league_instance/{league_id}?subseason={subseason_id}`

### 4. URL Patterns

**Schedule URLs:**
```
https://www.ssc-hockey.org/schedule/day/league_instance/224428?subseason=948564
```

**Game Detail URLs:**
```
https://www.ssc-hockey.org/game/show/44490869?subseason=948564&referrer=9115690
```

**Stats/Roster URLs:**
```
https://www.ssc-hockey.org/stats/league_instance/224428?subseason=948564
```

**Key IDs:**
- `league_instance`: 224428
- `subseason`: 948564
- `org_id`: 181469
- `game_id`: Various (e.g., 44490869, 44491649)

### 5. No GameSheet Stats Integration

**Unlike Bay State Hockey League, SSC Hockey does NOT use GameSheet Stats iframes.**

- No embedded GameSheet widgets found
- No GameSheet API endpoints detected
- No real-time game stats integration

## Comparison: SSC Hockey vs GameSheet Stats

| Feature | SSC Hockey | GameSheet Stats |
|---------|------------|-----------------|
| Platform | SportsEngine NGIN | Custom/Angular SPA |
| Data Loading | Server-rendered HTML | JSON API calls |
| Schedule API | ❌ None | ✅ Yes |
| Roster API | ❌ None | ✅ Yes |
| Game Stats API | ❌ None | ✅ Yes |
| Real-time Updates | ❌ No | ✅ Yes |
| Scraping Approach | HTML parsing | API interception |

## Scraping Strategy for SSC Hockey

Since there are no JSON APIs to intercept, you must use **HTML parsing**:

### Recommended Approach:

1. **Use Playwright for Navigation:**
   - Load pages with Playwright to handle JavaScript rendering
   - Wait for `domcontentloaded` event

2. **Parse HTML Content:**
   - Use BeautifulSoup4 or Playwright's selector API
   - Extract data from HTML tables and elements

3. **Example Scraping Pattern:**

```python
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()

    # Load schedule page
    await page.goto(schedule_url)
    await page.wait_for_load_state('domcontentloaded')

    # Get HTML content
    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    # Parse schedule table
    games = []
    for row in soup.select('table.schedule tbody tr'):
        game = {
            'date': row.select_one('.date').text,
            'time': row.select_one('.time').text,
            'home_team': row.select_one('.home-team').text,
            'away_team': row.select_one('.away-team').text,
            # etc...
        }
        games.append(game)
```

4. **Handle Pagination:**
   - Look for "Next" buttons or date navigation
   - Iterate through pages systematically

5. **Extract IDs from URLs:**
   - Game links contain game IDs
   - Use these for detail pages

## Investigation Artifacts

Created probe scripts:
1. `probe_ssc_hockey.py` - Basic network request capture
2. `probe_ssc_schedule_api.py` - Schedule-specific API detection
3. `probe_ssc_iframes.py` - GameSheet iframe detection
4. `probe_ssc_game_detail.py` - Comprehensive multi-page API discovery

Output files:
- `ssc_probe_results.json` - Initial network capture
- `ssc_schedule_apis.json` - Schedule API analysis
- `ssc_iframe_analysis.json` - Iframe investigation
- `ssc_full_api_discovery.json` - Complete API discovery results

## Conclusion

**SSC Hockey (SportsEngine platform) is fundamentally different from GameSheet Stats.**

- No exploitable JSON APIs for game/schedule data
- All data must be scraped from server-rendered HTML
- Cannot use the same API interception approach as GameSheet Stats
- Requires traditional web scraping with HTML parsing

If you need to scrape this site, you'll need to build an HTML parser, not an API interceptor like the existing `sprocket_scraper.py`.
