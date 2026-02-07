# SSC Hockey Scraper - Quick Reference Guide

## Key Findings Summary

### 1. JavaScript Embedded Data
**Location:** `<head>` section, lines 169-174

**Extract This:**
```javascript
league_instance_id: 224428
league_id: 112200
season_id: 868328
site_id: 63823
```

**Why:** Provides authoritative IDs for constructing URLs

---

### 2. Date Calendar Navigation
**Location:** `.games-slider` section

**Pattern:**
```
/schedule/day/league_instance/{league_id}/{year}/{month}/{day}?subseason={subseason_id}
```

**Impact:**
- Current scraper: 1 day = ~75 games
- Enhanced scraper: 100+ days = 1000s of games

**CSS Selectors:**
```css
.games-slider-inner
.games-slider-group
li[id^="slider_day_"]
.games-slider-count  /* "75 Gms" */
```

---

### 3. Game Table Structure

**Row ID Pattern:** `game_list_row_{game_id}`

**Row Classes:**
- `scheduled` - future game
- `cancelled` - cancelled game
- `final` - completed game

**Cell Order:**
| 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Visitor | V Score | Home | H Score | Location | Status/Time |

**Key Links in Each Row:**
```html
<!-- Cell 0: Visitor Team -->
<a class="teamName" href="/page/show/9176202-8bh-nri-vikings-white?subseason=948564">
  8BH - NRI Vikings White
</a>

<!-- Cell 2: Home Team -->
<a class="teamName" href="/page/show/9176200-8bh-franklin?subseason=948564">
  8BH - Franklin
</a>

<!-- Cell 4: Location -->
<a href="https://maps.app.goo.gl/4FqvhuvKERiPKrEu6">
  Foxboro Rink 3 - 10 E Belcher Rd, Foxborough, MA
</a>

<!-- Cell 5: Game Details -->
<a class="game_link_referrer" href="/game/show/44492111?subseason=948564">
  6:50 AM EST
</a>
```

---

### 4. Additional Data Endpoints

| Endpoint | URL Pattern | Data |
|----------|-------------|------|
| **Standings** | `/standings/show/{page_id}?subseason={subseason_id}` | Division standings, W/L/T records |
| **Player Stats** | `/stats/league_instance/{league_id}?subseason={subseason_id}&tab=league_instance_player_stats` | Goals, assists, points |
| **Team Stats** | `/stats/league_instance/{league_id}?subseason={subseason_id}&tab=league_instance_team_stats` | Team totals |
| **Box Scores** | `/schedule/tab_boxscores/league_instance/day/{league_id}?subseason={subseason_id}&view=boxscores` | Completed games |
| **Team Pages** | `/page/show/{team_id}-{slug}?subseason={subseason_id}` | Rosters, team info |
| **Game Details** | `/game/show/{game_id}?subseason={subseason_id}` | Period scores, scoring, penalties |

---

### 5. Division Pages

**Discovered Divisions:**
- 8U: `/page/show/9176097-youth-8u?subseason=948564`
- 10U: `/page/show/9176098-youth-10u?subseason=948564`
- 12U: `/page/show/9176099-youth-12u?subseason=948564`
- 14U: `/page/show/9176100-youth-14u?subseason=948564`
- 18U: `/page/show/9176101-youth-18u?subseason=948564`
- Girls: `/page/show/9211175-girls?subseason=948564`

**Use Case:** Filter schedule/standings by specific age group

---

## Implementation Priority

### Phase 1: Must Have (Week 1)
1. **Multi-date scraping** - Extract calendar dates and iterate
2. **Team URLs** - Store team page links for roster scraping
3. **Location maps URLs** - Extract Google Maps links
4. **Enhanced status** - Parse scheduled/cancelled/final

### Phase 2: High Value (Week 2)
5. **Standings** - Division standings tables
6. **Player/Team Stats** - League-wide statistics
7. **Team Rosters** - Player names, numbers, positions

### Phase 3: Nice to Have (Week 3+)
8. **Game Details** - Period scores, scoring summary
9. **Box Score View** - Alternative completed games view
10. **Division Filtering** - Age-group specific data

---

## CSS Selectors Cheat Sheet

### Schedule Page
```css
/* Main table */
table.statTable.sortable.noSortImages

/* Game rows */
tr[id^="game_list_row_"]
tr.scheduled
tr.cancelled
tr.final

/* Teams */
.teamName

/* Location */
td:nth-child(5) a[href*="maps.app.goo.gl"]

/* Game link */
.game_link_referrer

/* Calendar */
.games-slider-inner
li[id^="slider_day_"]
```

### Team/Roster Pages
```css
/* Roster table */
table.statTable
table[class*="roster"]

/* Player rows */
tbody tr

/* Player name with link */
td a[href*="/player/"]
```

### Standings Page
```css
/* Standings tables */
table.statTable

/* Division headers */
h2, h3

/* Team rows */
tbody tr

/* Team link */
td:first-child a
```

---

## XPath Alternatives

### Game Rows
```xpath
//tr[starts-with(@id, 'game_list_row_')]
```

### Team Links
```xpath
//a[@class='teamName']
```

### Google Maps Links
```xpath
//td[5]//a[contains(@href, 'maps.app.goo.gl')]
```

### Game Detail Links
```xpath
//a[@class='game_link_referrer']
```

---

## Regular Expression Patterns

### Extract Game ID from Row
```python
game_id = re.search(r'game_list_row_(\d+)', row_id).group(1)
```

### Extract Division from Team Name
```python
# "8BH - Franklin" -> "8BH"
division = team_name.split(' - ')[0] if ' - ' in team_name else None
```

### Detect Time vs Status
```python
is_time = bool(re.search(r'\d+:\d+\s*(AM|PM)', status_text))
```

### Extract Date from Slider ID
```python
# "slider_day_2025_11_8" -> (2025, 11, 8)
date_parts = slider_id.replace('slider_day_', '').split('_')
year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
```

### Extract Game Count
```python
# "75 Gms" -> 75
game_count = int(re.search(r'(\d+)', count_text).group(1))
```

---

## URL Construction Examples

### Schedule for Specific Date
```python
url = f"{base_url}/schedule/day/league_instance/{league_id}/{year}/{month}/{day}?subseason={subseason_id}"

# Example:
# https://www.ssc-hockey.org/schedule/day/league_instance/224428/2025/11/8?subseason=948564
```

### Team Page
```python
url = f"{base_url}/page/show/{team_page_id}?subseason={subseason_id}"

# Example:
# https://www.ssc-hockey.org/page/show/9176200-8bh-franklin?subseason=948564
```

### Game Details
```python
url = f"{base_url}/game/show/{game_id}?subseason={subseason_id}&referrer={referrer_page_id}"

# Example:
# https://www.ssc-hockey.org/game/show/44492111?subseason=948564&referrer=9115690
```

### Standings
```python
url = f"{base_url}/standings/show/{page_id}?subseason={subseason_id}"

# Example:
# https://www.ssc-hockey.org/standings/show/9115690?subseason=948564
```

### Player Stats
```python
url = f"{base_url}/stats/league_instance/{league_id}?subseason={subseason_id}&tab=league_instance_player_stats"

# Example:
# https://www.ssc-hockey.org/stats/league_instance/224428?subseason=948564&tab=league_instance_player_stats
```

---

## Data Quality Observations

### Game Status Values
- Scheduled games: Show time (e.g., "6:50 AM EST")
- Cancelled games: Show "Cancelled" in `<span class="status_in_progress">`
- Completed games: Show final score in columns 1 and 3

### Division Naming Convention
Format: `{Age}{Gender}{Tier} - Team Name`

Examples:
- `8BH - Franklin` = 8U Boys House
- `10BR - Milton White` = 10U Boys Rec
- `12A - Marshfield` = 12U A (top tier)
- `14B2H - Coyotes` = 14U B2 House

**Pattern:**
- Age: 8, 10, 12, 14, 18
- Gender: B (boys), G (girls)
- Tier: H (house), R (rec), A/B/B2 (competitive levels)

### Location Format
```
Rink Name - Street Address, City, State, Zip
```

Example:
```
Foxboro Rink 3 - 10 E Belcher Rd, Foxborough, MA, 02035
```

---

## Performance Estimates

| Task | Page Count | Time (with 500ms delay) | Notes |
|------|------------|------------------------|-------|
| Single day | 1 | 2-3 sec | Current implementation |
| Full season (100 dates) | 100 | 5-10 min | Primary enhancement |
| 20 team rosters | 20 | 1-2 min | Secondary enhancement |
| 1000 game details | 1000 | 15-30 min | Optional, intensive |
| Standings | 1 | 5 sec | Quick add |
| Player stats | 1 | 5-10 sec | May load via AJAX |

---

## Error Handling Recommendations

### Common Issues

1. **Date with no games:** Calendar shows date but table is empty
   - Check for empty tbody
   - Skip gracefully

2. **Team page without roster:** Some teams may not publish rosters
   - Try multiple table selectors
   - Log missing rosters

3. **Game page not found:** Future games may not have detail pages yet
   - Check HTTP status
   - Skip scheduled games

4. **AJAX-loaded content:** Stats pages may load dynamically
   - Increase wait_for_timeout
   - Look for loading indicators

### Rate Limiting Strategy

```python
# Basic: Fixed 500ms delay
await page.wait_for_timeout(500)

# Advanced: Adaptive delay
delay = 500 if request_count < 100 else 1000
await page.wait_for_timeout(delay)

# Conservative: Exponential backoff on errors
for attempt in range(3):
    try:
        await page.goto(url)
        break
    except:
        await page.wait_for_timeout(2000 * (attempt + 1))
```

---

## Testing Checklist

- [ ] Extract config data from JavaScript
- [ ] Parse calendar slider (100+ dates)
- [ ] Parse game table with all 6 columns
- [ ] Extract team URLs from team name links
- [ ] Extract Google Maps URLs from location
- [ ] Detect game status (scheduled/cancelled/final)
- [ ] Parse game IDs from row IDs
- [ ] Extract division from team names
- [ ] Scrape standings page
- [ ] Scrape player stats page
- [ ] Scrape team roster page
- [ ] Handle pagination (if applicable)
- [ ] Handle missing/empty tables
- [ ] Rate limit requests appropriately

---

## Files Reference

| File | Purpose |
|------|---------|
| `ssc_schedule_page.html` | Raw HTML for analysis |
| `ssc_html_analysis.json` | Structural summary |
| `ssc_hockey_scraper.py` | Current implementation |
| `SSC_ENHANCEMENT_ANALYSIS.md` | Detailed analysis (this file's parent) |
| `ssc_enhancements_code.py` | Copy-paste code snippets |
| `SSC_QUICK_REFERENCE.md` | This quick reference |

---

## Next Steps

1. Read `SSC_ENHANCEMENT_ANALYSIS.md` for detailed explanations
2. Review code snippets in `ssc_enhancements_code.py`
3. Start with Phase 1 (multi-date scraping)
4. Test with small date range first
5. Expand to full season once validated
6. Add Phase 2 features (standings, rosters)
7. Consider Phase 3 if needed (game details)
