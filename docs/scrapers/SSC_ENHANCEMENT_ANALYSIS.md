# SSC Hockey Website Structure Analysis & Scraper Enhancements

## Executive Summary

The SSC Hockey website (SportsEngine platform) is a server-rendered HTML application with rich structured data that can be scraped effectively. This analysis identifies multiple data sources and provides specific implementation recommendations for enhancing the scraper.

---

## 1. HTML Structure Analysis

### 1.1 Embedded JavaScript Configuration Data

**Location:** Lines 159-174 in `<head>`

**Key Variables Found:**
```javascript
NGIN.inlineManual.setVars({
  league_instance_id: 224428,
  league_id: 112200,
  league_name: "South Shore Conference",
  season_id: 868328,
  site_id: 63823,
  site_name: "South Shore Conference",
  site_url: "https://www.ssc-hockey.org"
});
```

**Implementation:**
```python
def extract_config_data(self, html: str) -> Dict[str, Any]:
    """Extract embedded configuration from NGIN.inlineManual.setVars()"""
    soup = BeautifulSoup(html, 'html.parser')

    # Find the script containing NGIN.inlineManual.setVars
    for script in soup.find_all('script'):
        if script.string and 'NGIN.inlineManual.setVars' in script.string:
            # Extract the JavaScript object
            match = re.search(r'setVars\s*\(\s*\{([^}]+)\}\s*\)', script.string, re.DOTALL)
            if match:
                config = {}
                for line in match.group(1).split(','):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().strip('"\'')
                        value = value.strip().strip('"\'')
                        # Try to convert to int if possible
                        try:
                            config[key] = int(value)
                        except ValueError:
                            config[key] = value
                return config
    return {}
```

---

### 1.2 Date Navigation Calendar

**Location:** Lines 811-1303 (games-slider section)

**Pattern:** Date slider with links to all game dates in the season

**CSS Selectors:**
- Container: `.games-slider .games-slider-inner`
- Month groups: `.games-slider-group`
- Individual days: `li[id^="slider_day_"]`
- Date links: `.game_link_referrer` with href pattern `/schedule/day/league_instance/{league_id}/{year}/{month}/{day}`

**Sample HTML:**
```html
<div class="games-slider">
  <div class="games-slider-inner">
    <div class="games-slider-group">
      <div class="games-slider-month">November</div>
      <ul>
        <li id="slider_day_2025_11_8">
          <a class="game game_link_referrer"
             href="/schedule/day/league_instance/224428/2025/11/8?subseason=948564&referrer=9115690">
            <span class="games-slider-day">Fri</span>
            <span class="games-slider-date">8</span>
            <span class="games-slider-count">75 Gms</span>
          </a>
        </li>
      </ul>
    </div>
  </div>
</div>
```

**Implementation:**
```python
async def _extract_all_game_dates(self, page: Page) -> List[Dict[str, Any]]:
    """Extract all available game dates from the calendar slider."""
    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    dates = []
    slider = soup.find('div', class_='games-slider-inner')

    if not slider:
        return dates

    for month_group in slider.find_all('div', class_='games-slider-group'):
        month_name = month_group.find('div', class_='games-slider-month').text.strip()

        for day_item in month_group.find_all('li', id=lambda x: x and x.startswith('slider_day_')):
            link = day_item.find('a', class_='game_link_referrer')
            if link:
                # Parse date from ID: slider_day_2025_11_8
                day_id = day_item.get('id')
                date_parts = day_id.replace('slider_day_', '').split('_')

                game_count_text = day_item.find('span', class_='games-slider-count').text
                game_count = int(re.search(r'(\d+)', game_count_text).group(1))

                dates.append({
                    'year': int(date_parts[0]),
                    'month': int(date_parts[1]),
                    'day': int(date_parts[2]),
                    'month_name': month_name,
                    'day_of_week': day_item.find('span', class_='games-slider-day').text,
                    'game_count': game_count,
                    'url': urljoin(self.BASE_URL, link.get('href'))
                })

    return dates

async def _scrape_all_dates(self, page: Page):
    """Scrape games from all dates in the season."""
    print("\n[*] Extracting game dates from calendar...")

    # Navigate to schedule page to get calendar
    schedule_url = f"{self.BASE_URL}/schedule/day/league_instance/{self.league_id}?subseason={self.subseason_id}"
    await page.goto(schedule_url, wait_until='domcontentloaded', timeout=60000)

    dates = await self._extract_all_game_dates(page)
    print(f"[*] Found {len(dates)} game dates with total of {sum(d['game_count'] for d in dates)} games")

    for i, date_info in enumerate(dates, 1):
        print(f"\n[{i}/{len(dates)}] Scraping {date_info['month_name']} {date_info['day']}, {date_info['year']} ({date_info['game_count']} games)")

        await page.goto(date_info['url'], wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(1000)

        # Parse games from this date
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        page_date = f"{date_info['month']}/{date_info['day']}/{date_info['year']}"

        table = soup.find('table', class_='statTable')
        if table:
            rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
            for row in rows:
                game = self._parse_game_row(row, page_date, date_info['url'])
                if game:
                    self.games.append(game)
                    self._add_team_from_game(game)
```

---

### 1.3 Game Row Structure

**Location:** Table rows starting at line 1357

**Row Classes:**
- `odd` / `even` - alternating row colors
- `scheduled` - game not yet played
- `cancelled` - cancelled game
- Row ID pattern: `game_list_row_{game_id}`

**Cell Structure (6 cells per row):**

| Index | Content | CSS Selector | Notes |
|-------|---------|--------------|-------|
| 0 | Visitor Team | `.teamName` link or text | Team page link available |
| 1 | Visitor Score | text | "-" if not played |
| 2 | Home Team | `.teamName` link or text | Team page link available |
| 3 | Home Score | text | "-" if not played |
| 4 | Location | link to Google Maps | Full address provided |
| 5 | Status/Time | `.game_link_referrer` link | Link to game detail page |

**Enhanced Parsing:**
```python
def _parse_game_row(self, row, page_date: Optional[str], source_url: str) -> Optional[Game]:
    """Parse a game row from the schedule table with enhanced data extraction."""
    cells = row.find_all('td')
    if len(cells) < 6:
        return None

    # Extract game ID from row ID
    row_id = row.get('id', '')
    game_id_match = re.search(r'game_list_row_(\d+)', row_id)
    game_id = game_id_match.group(1) if game_id_match else None

    # Extract row status from class
    row_classes = row.get('class', [])
    game_status_class = None
    if 'cancelled' in row_classes:
        game_status_class = 'cancelled'
    elif 'scheduled' in row_classes:
        game_status_class = 'scheduled'
    elif 'final' in row_classes:
        game_status_class = 'final'

    # Extract data from cells
    visitor_cell = cells[0]
    visitor_score_cell = cells[1]
    home_cell = cells[2]
    home_score_cell = cells[3]
    location_cell = cells[4]
    status_cell = cells[5]

    # Team names and URLs
    visitor_link = visitor_cell.find('a', class_='teamName')
    home_link = home_cell.find('a', class_='teamName')

    visitor_team = visitor_link.text.strip() if visitor_link else visitor_cell.text.strip()
    home_team = home_link.text.strip() if home_link else home_cell.text.strip()

    visitor_team_url = urljoin(self.BASE_URL, visitor_link.get('href')) if visitor_link else None
    home_team_url = urljoin(self.BASE_URL, home_link.get('href')) if home_link else None

    # Scores
    visitor_score = visitor_score_cell.text.strip()
    home_score = home_score_cell.text.strip()

    if visitor_score == '-':
        visitor_score = None
    if home_score == '-':
        home_score = None

    # Location with Google Maps link
    location_link = location_cell.find('a')
    location = location_cell.text.strip()
    location_maps_url = location_link.get('href') if location_link else None

    # Status/Time with game detail link
    status_link = status_cell.find('a', class_='game_link_referrer')
    status_text = status_cell.text.strip()

    game_url = urljoin(self.BASE_URL, status_link.get('href')) if status_link else None

    # Determine if status is a time or status text
    is_time = bool(re.search(r'\d+:\d+\s*(AM|PM)', status_text))
    time = status_text if is_time else None
    status = status_text if not is_time else game_status_class or 'scheduled'

    # Division (extract from team name, e.g., "8BH - Team Name")
    division = None
    if ' - ' in visitor_team:
        division = visitor_team.split(' - ')[0]

    return Game(
        game_id=game_id or '',
        date=page_date or '',
        time=time or '',
        visitor_team=visitor_team,
        home_team=home_team,
        visitor_score=visitor_score,
        home_score=home_score,
        location=location,
        location_maps_url=location_maps_url or '',
        status=status,
        division=division,
        game_url=game_url or '',
        visitor_team_url=visitor_team_url or '',
        home_team_url=home_team_url or '',
        source_url=source_url
    )
```

**Updated Game Dataclass:**
```python
@dataclass
class Game:
    """Represents a hockey game with enhanced fields."""
    game_id: str
    date: str
    time: str
    visitor_team: str
    home_team: str
    visitor_score: Optional[str]
    home_score: Optional[str]
    location: str
    location_maps_url: str  # NEW
    status: str
    division: Optional[str]
    game_url: str
    visitor_team_url: str  # NEW
    home_team_url: str  # NEW
    source_url: str
```

---

### 1.4 Navigation Tabs

**Location:** Lines 787-801

**Available Data Endpoints:**

| Tab | Endpoint | Purpose |
|-----|----------|---------|
| Player Stats | `/stats/league_instance/224428?subseason=948564&tab=league_instance_player_stats` | Individual player statistics |
| Team Stats | `/stats/league_instance/224428?subseason=948564&tab=league_instance_team_stats` | Team statistics |
| Standings | `/standings/show/9115690?subseason=948564` | Division standings |

**Implementation:**
```python
async def _scrape_standings(self, page: Page) -> List[Dict[str, Any]]:
    """Scrape division standings."""
    standings_url = f"{self.BASE_URL}/standings/show/{self.league_id}?subseason={self.subseason_id}"

    print(f"\n[*] Scraping standings: {standings_url}")
    await page.goto(standings_url, wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(2000)

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    standings = []

    # Look for standings tables (one per division)
    tables = soup.find_all('table', class_='statTable')

    for table in tables:
        # Find division name (usually in a header before the table)
        division_header = table.find_previous('h2') or table.find_previous('h3')
        division = division_header.text.strip() if division_header else 'Unknown'

        headers = [th.text.strip() for th in table.find('thead').find_all('th')]

        for row in table.find('tbody').find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                team_cell = cells[0]
                team_link = team_cell.find('a')

                standing = {
                    'division': division,
                    'team': team_cell.text.strip(),
                    'team_url': urljoin(self.BASE_URL, team_link.get('href')) if team_link else '',
                    'stats': {}
                }

                for i, header in enumerate(headers[1:], 1):
                    if i < len(cells):
                        standing['stats'][header] = cells[i].text.strip()

                standings.append(standing)

    return standings

async def _scrape_player_stats(self, page: Page) -> List[Dict[str, Any]]:
    """Scrape league-wide player statistics."""
    stats_url = f"{self.BASE_URL}/stats/league_instance/{self.league_id}?subseason={self.subseason_id}&tab=league_instance_player_stats"

    print(f"\n[*] Scraping player stats: {stats_url}")
    await page.goto(stats_url, wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(3000)  # Stats may load via AJAX

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    stats = []

    # Look for stats table
    table = soup.find('table', class_='statTable')
    if not table:
        return stats

    headers = [th.text.strip() for th in table.find('thead').find_all('th')]

    for row in table.find('tbody').find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 2:
            player_stat = {}

            for i, header in enumerate(headers):
                if i < len(cells):
                    player_stat[header] = cells[i].text.strip()

            stats.append(player_stat)

    return stats
```

---

### 1.5 Box Scores Tab

**Location:** Lines 1315-1321

**Endpoint:** `/schedule/tab_boxscores/league_instance/day/{league_id}?subseason={subseason_id}&view=boxscores`

**Purpose:** Alternative view showing completed games with scores

**Implementation:**
```python
async def _scrape_box_scores_view(self, page: Page, date: str = None):
    """Scrape the box scores view for a specific date or all dates."""

    if date:
        # Format: /schedule/tab_boxscores/league_instance/day/224428/2025/11/8?subseason=948564
        year, month, day = date.split('/')
        url = f"{self.BASE_URL}/schedule/tab_boxscores/league_instance/day/{self.league_id}/{year}/{month}/{day}?subseason={self.subseason_id}&view=boxscores"
    else:
        url = f"{self.BASE_URL}/schedule/tab_boxscores/league_instance/day/{self.league_id}?subseason={self.subseason_id}&view=boxscores"

    print(f"\n[*] Scraping box scores: {url}")
    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(2000)

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    # Parse box score format (implementation depends on actual HTML structure)
    # This view likely shows only completed games with final scores
    # Parse similar to regular schedule but filter for completed games
```

---

### 1.6 Team Pages

**URL Pattern:** `/page/show/{team_page_id}-{team_slug}?subseason={subseason_id}`

**Example:** `https://www.ssc-hockey.org/page/show/9176202-8bh-nri-vikings-white?subseason=948564`

**Contains:**
- Team roster
- Team schedule
- Team statistics
- Player profiles

**Implementation:**
```python
async def _scrape_team_roster(self, page: Page, team_url: str, team_name: str) -> List[Player]:
    """Scrape roster from a team page."""
    print(f"[*] Scraping roster for: {team_name}")

    await page.goto(team_url, wait_until='domcontentloaded', timeout=30000)
    await page.wait_for_timeout(2000)

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    players = []

    # Look for roster table (CSS class may vary)
    roster_table = soup.find('table', class_=lambda x: x and 'roster' in x.lower()) or \
                   soup.find('table', class_='statTable')

    if not roster_table:
        # Try alternative selectors
        roster_section = soup.find('div', id=lambda x: x and 'roster' in x.lower())
        if roster_section:
            roster_table = roster_section.find('table')

    if roster_table:
        headers = [th.text.strip().lower() for th in roster_table.find('thead').find_all('th')]

        for row in roster_table.find('tbody').find_all('tr'):
            cells = row.find_all('td')

            # Map common header names to indices
            name_idx = next((i for i, h in enumerate(headers) if 'name' in h), 0)
            num_idx = next((i for i, h in enumerate(headers) if 'number' in h or '#' in h), None)
            pos_idx = next((i for i, h in enumerate(headers) if 'position' in h or 'pos' in h), None)

            if len(cells) > name_idx:
                name_cell = cells[name_idx]
                player_link = name_cell.find('a')

                player = Player(
                    name=name_cell.text.strip(),
                    number=cells[num_idx].text.strip() if num_idx and len(cells) > num_idx else None,
                    position=cells[pos_idx].text.strip() if pos_idx and len(cells) > pos_idx else None,
                    team=team_name,
                    player_url=urljoin(self.BASE_URL, player_link.get('href')) if player_link else '',
                    source_url=team_url
                )

                players.append(player)

    return players

async def _scrape_all_rosters(self, page: Page):
    """Scrape rosters for all teams."""
    print(f"\n[*] Scraping rosters for {len(self.teams)} teams...")

    for i, (team_name, team) in enumerate(list(self.teams.items()), 1):
        if not team.team_url:
            continue

        print(f"[{i}/{len(self.teams)}] {team_name}")

        try:
            roster = await self._scrape_team_roster(page, team.team_url, team_name)
            self.players.extend(roster)

            # Add delay to avoid rate limiting
            await page.wait_for_timeout(500)

        except Exception as e:
            print(f"    [!] Error: {e}")
            continue

    print(f"[✓] Scraped {len(self.players)} players total")
```

**Updated Player Dataclass:**
```python
@dataclass
class Player:
    """Represents a player with enhanced fields."""
    name: str
    number: Optional[str]
    position: Optional[str]
    team: str
    player_url: str  # NEW
    source_url: str
```

---

### 1.7 Game Detail Pages

**URL Pattern:** `/game/show/{game_id}?subseason={subseason_id}&referrer={page_id}`

**Example:** `https://www.ssc-hockey.org/game/show/44492111?subseason=948564&referrer=9115690`

**Expected Contents:**
- Final score and period breakdowns
- Game officials (referees)
- Scoring summary
- Penalty summary
- Goalie statistics
- Links to GameSheet (if available)

**Implementation:**
```python
async def _scrape_game_details(self, page: Page, game: Game) -> Dict[str, Any]:
    """Scrape detailed information from a game detail page."""
    if not game.game_url:
        return {}

    print(f"[*] Scraping game details: {game.visitor_team} @ {game.home_team}")

    await page.goto(game.game_url, wait_until='domcontentloaded', timeout=30000)
    await page.wait_for_timeout(1500)

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    details = {
        'game_id': game.game_id,
        'periods': [],
        'scoring': [],
        'penalties': [],
        'officials': []
    }

    # Look for period scores
    period_table = soup.find('table', class_=lambda x: x and 'period' in str(x).lower())
    if period_table:
        headers = [th.text.strip() for th in period_table.find('thead').find_all('th')]
        rows = period_table.find('tbody').find_all('tr')

        for row in rows:
            cells = row.find_all('td')
            team = cells[0].text.strip() if cells else ''
            period_scores = [cell.text.strip() for cell in cells[1:]]

            details['periods'].append({
                'team': team,
                'scores': period_scores
            })

    # Look for scoring summary
    scoring_section = soup.find('div', id=lambda x: x and 'scoring' in str(x).lower()) or \
                      soup.find('div', class_=lambda x: x and 'scoring' in str(x).lower())

    if scoring_section:
        # Parse scoring plays
        # Format varies, but typically includes: Period, Time, Team, Scorer, Assists
        pass

    # Look for penalty summary
    penalty_section = soup.find('div', id=lambda x: x and 'penalt' in str(x).lower()) or \
                      soup.find('div', class_=lambda x: x and 'penalt' in str(x).lower())

    if penalty_section:
        # Parse penalties
        pass

    # Look for officials
    officials_section = soup.find('div', class_=lambda x: x and 'official' in str(x).lower())
    if officials_section:
        officials_text = officials_section.text
        # Parse official names
        pass

    return details

async def _scrape_all_game_details(self, page: Page):
    """Scrape details for all games."""
    print(f"\n[*] Scraping game details for {len(self.games)} games...")

    game_details = []

    for i, game in enumerate(self.games, 1):
        # Only scrape completed games or limit to recent games
        if game.status != 'scheduled':
            print(f"[{i}/{len(self.games)}]")

            try:
                details = await self._scrape_game_details(page, game)
                game_details.append(details)

                # Rate limiting
                await page.wait_for_timeout(500)

            except Exception as e:
                print(f"    [!] Error: {e}")
                continue

    return game_details
```

---

### 1.8 Division Filter Pages

**URL Pattern:** `/page/show/{division_page_id}-{division_slug}?subseason={subseason_id}`

**Examples from Navigation:**
- Youth 8U: `/page/show/9176097-youth-8u?subseason=948564`
- Youth 10U: `/page/show/9176098-youth-10u?subseason=948564`
- Youth 12U: `/page/show/9176099-youth-12u?subseason=948564`
- Youth 14U: `/page/show/9176100-youth-14u?subseason=948564`
- Youth 18U: `/page/show/9176101-youth-18u?subseason=948564`
- Girls: `/page/show/9211175-girls?subseason=948564`

**Contains:**
- Division-specific schedules
- Division standings
- Division teams
- Division statistics

**Implementation:**
```python
async def _scrape_division_pages(self, page: Page):
    """Scrape division-specific pages for additional data."""

    division_pages = {
        '8U': ('9176097', 'youth-8u'),
        '10U': ('9176098', 'youth-10u'),
        '12U': ('9176099', 'youth-12u'),
        '14U': ('9176100', 'youth-14u'),
        '18U': ('9176101', 'youth-18u'),
        'Girls': ('9211175', 'girls')
    }

    for division_name, (page_id, slug) in division_pages.items():
        url = f"{self.BASE_URL}/page/show/{page_id}-{slug}?subseason={self.subseason_id}"

        print(f"\n[*] Scraping {division_name} division page: {url}")

        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(2000)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Extract division-specific data
        # Usually contains filtered schedule and standings for this division only
```

---

## 2. Data Extraction Recommendations

### 2.1 Priority Enhancements (High Value)

1. **Multi-Date Scraping** ✅ CRITICAL
   - Extract all dates from calendar slider
   - Iterate through all dates to get complete season schedule
   - Estimated impact: 75+ games per day → thousands of games total

2. **Team URL Extraction** ✅ HIGH VALUE
   - Extract team page URLs from game rows
   - Store in Team dataclass for later roster scraping
   - Update Team dataclass with team_url field

3. **Location Google Maps Links** ✅ USEFUL
   - Extract Google Maps URLs from location cells
   - Provides precise location data

4. **Game Status Tracking** ✅ IMPORTANT
   - Parse row classes (scheduled, cancelled, final)
   - Distinguish between time and status text
   - Better data quality for downstream analysis

### 2.2 Secondary Enhancements (Medium Value)

5. **Team Rosters**
   - Scrape team pages to extract player rosters
   - Player names, numbers, positions
   - Requires rate limiting (20+ teams)

6. **Standings Data**
   - Scrape `/standings/show/{league_id}` endpoint
   - Division standings with W/L/T records
   - Points, goals for/against

7. **Player Statistics**
   - Scrape `/stats/league_instance/{league_id}` endpoint
   - League-wide player stats (goals, assists, points)
   - Can be division-filtered

8. **Box Scores View**
   - Alternative view for completed games
   - May provide additional score details

### 2.3 Advanced Enhancements (Lower Priority)

9. **Game Detail Pages**
   - Period-by-period scores
   - Scoring summary
   - Penalty summary
   - Game officials
   - Requires scraping 1000+ individual pages

10. **Division-Specific Pages**
    - More granular team and player data
    - Division-specific standings and stats

---

## 3. Complete Implementation Roadmap

### Phase 1: Core Enhancements (Week 1)
- [ ] Extract embedded JavaScript config data
- [ ] Implement multi-date scraping from calendar slider
- [ ] Extract team URLs and Google Maps links
- [ ] Enhanced game status parsing
- [ ] Update dataclasses with new fields

### Phase 2: League-Wide Data (Week 2)
- [ ] Implement standings scraper
- [ ] Implement player stats scraper
- [ ] Implement team stats scraper
- [ ] Add data deduplication logic

### Phase 3: Team Rosters (Week 3)
- [ ] Implement team page scraper
- [ ] Extract roster tables
- [ ] Handle different roster formats
- [ ] Add rate limiting and error handling

### Phase 4: Game Details (Week 4)
- [ ] Implement game detail page scraper
- [ ] Extract period scores
- [ ] Extract scoring summary
- [ ] Extract penalty summary
- [ ] Extract officials

---

## 4. Updated Scraper Architecture

### 4.1 Enhanced Main Scraper Method

```python
async def scrape(self):
    """Main scraping method with all enhancements."""
    print("[*] Starting SSC Hockey scraper")
    print(f"[*] League ID: {self.league_id}")
    print(f"[*] Subseason ID: {self.subseason_id}")
    print(f"[*] Output directory: {self.output_dir}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=self.headless)
        context = await browser.new_context()
        page = await context.new_page()

        # Extract configuration data
        schedule_url = f"{self.BASE_URL}/schedule/day/league_instance/{self.league_id}?subseason={self.subseason_id}"
        await page.goto(schedule_url, wait_until='domcontentloaded', timeout=60000)
        html = await page.content()
        config = self.extract_config_data(html)
        print(f"[*] Config: {config}")

        # Phase 1: Scrape all schedules
        await self._scrape_all_dates(page)

        # Phase 2: Scrape league-wide data
        standings = await self._scrape_standings(page)
        player_stats = await self._scrape_player_stats(page)

        # Phase 3: Scrape team rosters
        await self._scrape_all_rosters(page)

        # Phase 4: Scrape game details (optional, time-intensive)
        # game_details = await self._scrape_all_game_details(page)

        await browser.close()

    # Save results
    self._save_results()

    # Save additional data
    if standings:
        self._save_standings(standings)
    if player_stats:
        self._save_player_stats(player_stats)

    print(f"\n[✓] Scraping complete!")
    print(f"    Games: {len(self.games)}")
    print(f"    Teams: {len(self.teams)}")
    print(f"    Players: {len(self.players)}")
```

### 4.2 Rate Limiting Strategy

```python
class RateLimiter:
    """Simple rate limiter to avoid overwhelming the server."""

    def __init__(self, min_delay_ms: int = 500, max_delay_ms: int = 2000):
        self.min_delay = min_delay_ms
        self.max_delay = max_delay_ms
        self.request_count = 0

    async def wait(self, page: Page):
        """Wait appropriate delay between requests."""
        self.request_count += 1

        # Increase delay after many requests
        if self.request_count % 100 == 0:
            delay = self.max_delay
        elif self.request_count % 20 == 0:
            delay = self.min_delay * 2
        else:
            delay = self.min_delay

        await page.wait_for_timeout(delay)
```

### 4.3 Error Handling and Retry Logic

```python
async def scrape_with_retry(self, page: Page, url: str, max_retries: int = 3):
    """Scrape a URL with retry logic."""
    for attempt in range(max_retries):
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(1000)
            return await page.content()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    [!] Attempt {attempt + 1} failed: {e}, retrying...")
                await page.wait_for_timeout(2000 * (attempt + 1))
            else:
                print(f"    [!] All retries failed: {e}")
                raise
```

---

## 5. CSS Selectors Reference

### Schedule Page
```css
/* Calendar Slider */
.games-slider .games-slider-inner
.games-slider-group
.games-slider-month
li[id^="slider_day_"]
.games-slider-day
.games-slider-date
.games-slider-count

/* Game Table */
table.statTable.sortable.noSortImages
tr[id^="game_list_row_"]
tr.scheduled
tr.cancelled
tr.final
.scheduleListTeam
.teamName
.game_link_referrer

/* Navigation Tabs */
#tool-player-stats
#tool-team-stats
#tool-standings
.contentTabs
#tab_gamelist
#tab_boxscores
```

### Team Pages
```css
/* Roster Table */
table.statTable
table[class*="roster"]
div[id*="roster"]

/* Player Links */
a[href*="/player/"]
```

### Game Detail Pages
```css
/* Period Scores */
table[class*="period"]

/* Game Info Sections */
div[id*="scoring"]
div[id*="penalty"]
div[class*="official"]
```

---

## 6. Sample Data Outputs

### Enhanced Game JSON
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
  "location_maps_url": "https://maps.app.goo.gl/4FqvhuvKERiPKrEu6",
  "status": "scheduled",
  "division": "8BH",
  "game_url": "https://www.ssc-hockey.org/game/show/44492111?subseason=948564&referrer=9115690",
  "visitor_team_url": "https://www.ssc-hockey.org/page/show/9176202-8bh-nri-vikings-white?subseason=948564",
  "home_team_url": "https://www.ssc-hockey.org/page/show/9176200-8bh-franklin?subseason=948564",
  "source_url": "https://www.ssc-hockey.org/schedule/day/league_instance/224428/2025/11/8?subseason=948564"
}
```

### Player JSON
```json
{
  "name": "John Smith",
  "number": "15",
  "position": "Forward",
  "team": "8BH - Franklin",
  "player_url": "https://www.ssc-hockey.org/player/show/12345",
  "source_url": "https://www.ssc-hockey.org/page/show/9176200-8bh-franklin?subseason=948564"
}
```

### Standings JSON
```json
{
  "division": "8BH",
  "team": "8BH - Franklin",
  "team_url": "https://www.ssc-hockey.org/page/show/9176200-8bh-franklin?subseason=948564",
  "stats": {
    "GP": "20",
    "W": "15",
    "L": "3",
    "T": "2",
    "PTS": "32",
    "GF": "85",
    "GA": "42"
  }
}
```

---

## 7. Command Line Usage

### Basic Usage (Current)
```bash
python3 ssc_hockey_scraper.py --league-id 224428 --subseason-id 948564 --out data
```

### Enhanced Usage (Recommended)
```bash
# Scrape all dates (full season)
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data \
  --scrape-all-dates \
  --scrape-rosters \
  --scrape-standings

# Scrape specific date range
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data \
  --start-date 2025-09-01 \
  --end-date 2025-11-30

# Scrape game details for completed games only
python3 ssc_hockey_scraper.py \
  --league-id 224428 \
  --subseason-id 948564 \
  --out data \
  --scrape-game-details \
  --completed-only
```

---

## 8. Performance Considerations

### Estimated Scraping Times

| Task | Pages | Est. Time | Notes |
|------|-------|-----------|-------|
| Single day schedule | 1 | 2-5 sec | Current implementation |
| Full season (100 dates) | 100 | 5-10 min | With rate limiting |
| All team rosters (20 teams) | 20 | 1-2 min | 500ms delay |
| All game details (1000 games) | 1000 | 15-30 min | 1s delay |
| Standings + Stats | 2 | 10-15 sec | May have AJAX loading |

### Optimization Strategies

1. **Parallel Scraping:** Use multiple browser contexts for independent data
2. **Caching:** Save raw HTML to avoid re-fetching
3. **Incremental Updates:** Only scrape new/changed games
4. **Smart Filtering:** Skip game details for future games

---

## Summary

The SSC Hockey website provides rich, structured data that can be comprehensively scraped. The highest-value enhancements are:

1. **Multi-date scraping** - Access complete season schedule (75+ games/day)
2. **Team URLs** - Enable roster scraping
3. **Enhanced game metadata** - Location links, status tracking
4. **League-wide statistics** - Standings, player stats, team stats

These enhancements would transform the scraper from a single-day tool to a comprehensive league data platform.
