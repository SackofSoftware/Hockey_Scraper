#!/usr/bin/env python3
"""
SSC Hockey HTML Scraper

Scrapes schedule and game data from SSC Hockey (SportsEngine) website.
Unlike GameSheet Stats, this site uses server-rendered HTML, so we parse the DOM.

Usage:
    python3 ssc_hockey_scraper.py --league-id 224428 --subseason-id 948564 --out data
"""

import asyncio
import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse, parse_qs
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup


@dataclass
class Game:
    """Represents a hockey game."""
    game_id: str
    date: str
    time: str
    visitor_team: str
    home_team: str
    visitor_score: Optional[str]
    home_score: Optional[str]
    location: str
    status: str
    division: Optional[str]
    game_url: str
    source_url: str
    period_scores: Optional[Dict] = None  # {"1st": {"visitor": 2, "home": 1}, "2nd": {...}, "3rd": {...}}
    scoring_summary: Optional[List[Dict]] = None  # [{"period": "1st", "time": "5:23", "team": "...", "player": "...", "assists": [...]}]
    penalties: Optional[List[Dict]] = None  # [{"period": "1st", "time": "12:34", "team": "...", "player": "...", "penalty": "...", "minutes": 2}]
    shots_on_goal: Optional[Dict] = None  # {"1st": {"visitor": 10, "home": 8}, "2nd": {...}, "3rd": {...}, "total": {...}}

    def to_dict(self):
        return asdict(self)


@dataclass
class Team:
    """Represents a team."""
    name: str
    division: Optional[str]
    team_url: str
    team_id: Optional[str]

    def to_dict(self):
        return asdict(self)


@dataclass
class Player:
    """Represents a player."""
    name: str
    number: Optional[str]
    position: Optional[str]
    team: str
    source_url: str

    def to_dict(self):
        return asdict(self)


@dataclass
class PlayerStats:
    """Represents player statistics."""
    name: str
    team: str
    games_played: int
    goals: int
    assists: int
    points: int
    penalty_minutes: Optional[int]
    plus_minus: Optional[int]
    power_play_goals: Optional[int]
    short_handed_goals: Optional[int]
    game_winning_goals: Optional[int]
    division: Optional[str]
    source_url: str

    def to_dict(self):
        return asdict(self)


@dataclass
class TeamStanding:
    """Represents team standings."""
    team_name: str
    team_abbrev: str
    division: Optional[str]
    points: int
    games_played: int
    wins: int
    losses: int
    ties: int
    goals_for: int
    goals_against: int
    record: str  # e.g., "7-0-0"
    source_url: str

    def to_dict(self):
        return asdict(self)


class SSCHockeyScraper:
    """Scraper for SSC Hockey website (SportsEngine platform)."""

    BASE_URL = "https://www.ssc-hockey.org"

    def __init__(self, league_id: str, subseason_id: str, output_dir: Path, headless: bool = True,
                 all_dates: bool = False, max_dates: Optional[int] = None, specific_date: Optional[str] = None,
                 scrape_game_details: bool = False, scrape_stats: bool = False, scrape_standings: bool = False):
        self.league_id = league_id
        self.subseason_id = subseason_id
        self.output_dir = Path(output_dir)
        self.headless = headless
        self.all_dates = all_dates
        self.max_dates = max_dates
        self.specific_date = specific_date
        self.scrape_game_details = scrape_game_details
        self.scrape_stats = scrape_stats
        self.scrape_standings = scrape_standings

        self.games: List[Game] = []
        self.teams: Dict[str, Team] = {}  # keyed by team name
        self.players: List[Player] = []
        self.player_stats: List[PlayerStats] = []
        self.standings: List[TeamStanding] = []
        self.game_ids_seen = set()  # For deduplication

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def scrape(self):
        """Main scraping method."""
        print("[*] Starting SSC Hockey scraper")
        print(f"[*] League ID: {self.league_id}")
        print(f"[*] Subseason ID: {self.subseason_id}")
        print(f"[*] Output directory: {self.output_dir}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()

            # Determine scraping strategy
            if self.all_dates or self.specific_date:
                # Multi-date scraping
                date_urls = await self._scrape_calendar_dates(page)

                if self.specific_date:
                    # Filter to specific date
                    date_urls = [(d, u) for d, u in date_urls if d == self.specific_date]
                    if not date_urls:
                        print(f"[!] Warning: Date {self.specific_date} not found in calendar")

                if self.max_dates:
                    date_urls = date_urls[:self.max_dates]

                await self._scrape_multiple_dates(page, date_urls)
            else:
                # Default: scrape current schedule page
                await self._scrape_schedule(page)

            # Optional: scrape individual game details
            if self.scrape_game_details:
                await self._scrape_game_details(page)

            # Optional: scrape player statistics
            if self.scrape_stats:
                await self._scrape_player_stats(page)

            # Optional: scrape standings
            if self.scrape_standings:
                await self._scrape_standings(page)

            # Optional: scrape team rosters
            # await self._scrape_rosters(page)

            await browser.close()

        # Save results
        self._save_results()

        print(f"\n[✓] Scraping complete!")
        print(f"    Games: {len(self.games)}")
        print(f"    Teams: {len(self.teams)}")
        print(f"    Players: {len(self.players)}")
        print(f"    Player Stats: {len(self.player_stats)}")
        print(f"    Standings: {len(self.standings)}")

    async def _scrape_schedule(self, page: Page):
        """Scrape the schedule page."""
        schedule_url = f"{self.BASE_URL}/schedule/day/league_instance/{self.league_id}?subseason={self.subseason_id}"

        print(f"\n[*] Scraping schedule: {schedule_url}")
        await page.goto(schedule_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(2000)

        # Get page title to extract date
        title = await page.title()
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', title)
        page_date = date_match.group(1) if date_match else None

        # Get HTML content
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Find the schedule table
        table = soup.find('table', class_='statTable')
        if not table:
            print("[!] Warning: Could not find schedule table")
            return

        # Parse game rows
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]

        print(f"[*] Found {len(rows)} game rows")

        for row in rows:
            try:
                game = self._parse_game_row(row, page_date, schedule_url)
                if game:
                    self.games.append(game)

                    # Extract teams
                    self._add_team_from_game(game)

            except Exception as e:
                print(f"[!] Error parsing game row: {e}")
                continue

        print(f"[✓] Scraped {len(self.games)} games")

    async def _scrape_calendar_dates(self, page: Page) -> List[tuple]:
        """Extract all date links from the calendar slider.

        Returns:
            List of (date_string, url) tuples, e.g., [("2024_01_15", "https://..."), ...]
        """
        schedule_url = f"{self.BASE_URL}/schedule/day/league_instance/{self.league_id}?subseason={self.subseason_id}"

        print(f"\n[*] Extracting calendar dates from: {schedule_url}")
        await page.goto(schedule_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(2000)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Find calendar slider items
        slider = soup.find('ul', class_='games-slider-inner')
        if not slider:
            print("[!] Warning: Could not find calendar slider")
            return []

        date_items = slider.find_all('li', id=lambda x: x and x.startswith('slider_day_'))

        date_urls = []
        for item in date_items:
            # Extract date from ID (e.g., slider_day_2024_01_15)
            item_id = item.get('id', '')
            date_match = re.search(r'slider_day_(\d{4})_(\d{2})_(\d{2})', item_id)
            if not date_match:
                continue

            year, month, day = date_match.groups()
            date_str = f"{year}_{month}_{day}"

            # Find link in this item
            link = item.find('a')
            if not link or not link.get('href'):
                continue

            url = urljoin(self.BASE_URL, link.get('href'))
            date_urls.append((date_str, url))

        print(f"[✓] Found {len(date_urls)} dates in calendar")
        return date_urls

    async def _scrape_multiple_dates(self, page: Page, date_urls: List[tuple]):
        """Scrape schedule data from multiple dates.

        Args:
            page: Playwright page object
            date_urls: List of (date_string, url) tuples
        """
        total = len(date_urls)
        print(f"\n[*] Scraping {total} dates...")

        for idx, (date_str, url) in enumerate(date_urls, 1):
            print(f"\n[{idx}/{total}] Scraping date {date_str}...")

            try:
                # Navigate to date page
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(500)  # 500ms rate limit

                # Get page title to extract formatted date
                title = await page.title()
                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', title)
                page_date = date_match.group(1) if date_match else None

                # Get HTML content
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Find the schedule table
                table = soup.find('table', class_='statTable')
                if not table:
                    print(f"    [!] No schedule table found for {date_str}")
                    continue

                # Parse game rows
                rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]

                games_found = 0
                for row in rows:
                    try:
                        game = self._parse_game_row(row, page_date, url)
                        if game:
                            # Deduplication check
                            if game.game_id and game.game_id in self.game_ids_seen:
                                continue

                            self.games.append(game)
                            if game.game_id:
                                self.game_ids_seen.add(game.game_id)
                            games_found += 1

                            # Extract teams
                            self._add_team_from_game(game)

                    except Exception as e:
                        print(f"    [!] Error parsing game row: {e}")
                        continue

                print(f"    [✓] Found {games_found} games")

            except Exception as e:
                print(f"    [!] Error scraping date {date_str}: {e}")
                continue

        print(f"\n[✓] Completed multi-date scraping: {len(self.games)} total games")

    def _parse_game_row(self, row, page_date: Optional[str], source_url: str) -> Optional[Game]:
        """Parse a game row from the schedule table."""
        cells = row.find_all('td')
        if len(cells) < 6:
            return None

        # Extract game ID from row ID
        row_id = row.get('id', '')
        game_id_match = re.search(r'game_list_row_(\d+)', row_id)
        game_id = game_id_match.group(1) if game_id_match else None

        # Extract data from cells
        visitor_cell = cells[0]
        visitor_score_cell = cells[1]
        home_cell = cells[2]
        home_score_cell = cells[3]
        location_cell = cells[4]
        status_cell = cells[5]

        # Team names
        visitor_link = visitor_cell.find('a', class_='teamName')
        home_link = home_cell.find('a', class_='teamName')

        visitor_team = visitor_link.text.strip() if visitor_link else visitor_cell.text.strip()
        home_team = home_link.text.strip() if home_link else home_cell.text.strip()

        # Scores (may be "-" for unplayed games)
        visitor_score = visitor_score_cell.text.strip()
        home_score = home_score_cell.text.strip()

        if visitor_score == '-':
            visitor_score = None
        if home_score == '-':
            home_score = None

        # Location
        location = location_cell.text.strip()

        # Status/Time
        status = status_cell.text.strip()

        # Division (extract from team name, e.g., "8BH - Team Name")
        division = None
        if ' - ' in visitor_team:
            division = visitor_team.split(' - ')[0]

        # Game URL
        game_url = None
        game_link = row.find('a', href=lambda x: x and 'game/show' in x)
        if game_link:
            game_url = urljoin(self.BASE_URL, game_link.get('href'))

        return Game(
            game_id=game_id or '',
            date=page_date or '',
            time=status if 'AM' in status or 'PM' in status else '',
            visitor_team=visitor_team,
            home_team=home_team,
            visitor_score=visitor_score,
            home_score=home_score,
            location=location,
            status=status,
            division=division,
            game_url=game_url or '',
            source_url=source_url
        )

    def _add_team_from_game(self, game: Game):
        """Extract and add teams from a game."""
        # Visitor team
        if game.visitor_team not in self.teams:
            self.teams[game.visitor_team] = Team(
                name=game.visitor_team,
                division=game.division,
                team_url='',
                team_id=None
            )

        # Home team
        if game.home_team not in self.teams:
            self.teams[game.home_team] = Team(
                name=game.home_team,
                division=game.division,
                team_url='',
                team_id=None
            )

    async def _scrape_game_details(self, page: Page):
        """Scrape individual game detail pages for box scores and statistics.

        Parses:
        - Period scores
        - Scoring summary (goals, assists)
        - Penalties
        - Shots on goal
        """
        # Filter games with URLs
        games_with_urls = [g for g in self.games if g.game_url]
        total_games = len(games_with_urls)

        print(f"\n[*] Scraping game details: {total_games} games with URLs")

        for i, game in enumerate(games_with_urls, 1):
            print(f"[{i}/{total_games}] Scraping: {game.visitor_team} @ {game.home_team}")

            try:
                # Navigate to game page
                await page.goto(game.game_url, wait_until='domcontentloaded', timeout=45000)
                await page.wait_for_timeout(1500)  # Give time for content to load

                # Get HTML content
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Check if game has been played (look for "No Player Data Available")
                no_data = soup.find('p', class_='noEntry')
                if no_data and 'No Player Data Available' in no_data.text:
                    print(f"    [!] No game data available (game not yet played)")
                    await page.wait_for_timeout(500)  # Short delay before next request
                    continue

                # Parse game details
                period_scores = self._parse_period_scores(soup, game)
                scoring_summary = self._parse_scoring_summary(soup, game)
                penalties = self._parse_penalties(soup, game)
                shots_on_goal = self._parse_shots_on_goal(soup, game)

                # Update game object
                if period_scores:
                    game.period_scores = period_scores
                if scoring_summary:
                    game.scoring_summary = scoring_summary
                if penalties:
                    game.penalties = penalties
                if shots_on_goal:
                    game.shots_on_goal = shots_on_goal

                # Report what was found
                details_found = []
                if period_scores:
                    details_found.append("periods")
                if scoring_summary:
                    details_found.append(f"{len(scoring_summary)} goals")
                if penalties:
                    details_found.append(f"{len(penalties)} penalties")
                if shots_on_goal:
                    details_found.append("shots")

                if details_found:
                    print(f"    [OK] Found: {', '.join(details_found)}")
                else:
                    print(f"    [!] No detailed stats available")

                # Rate limiting
                await page.wait_for_timeout(1000)  # 1 second between requests

            except Exception as e:
                print(f"    [!] Error scraping game details: {e}")
                await page.wait_for_timeout(500)
                continue

    def _parse_period_scores(self, soup: BeautifulSoup, game: Game) -> Optional[Dict]:
        """Parse period-by-period scores from the box score table.

        Looks for tables with headers like: 1, 2, 3, OT, T (periods and total)
        """
        try:
            # Look for score tables with various class names
            score_tables = soup.find_all('table', class_=['scoreTable', 'statTable', 'boxscore'])

            for table in score_tables:
                # Find headers row
                thead = table.find('thead')
                if not thead:
                    continue

                headers = [th.text.strip() for th in thead.find_all('th')]

                # Check if this looks like a period score table (has numbered periods)
                period_cols = []
                for idx, header in enumerate(headers):
                    if header in ['1', '2', '3', 'OT', 'SO', 'F', 'T', 'Total']:
                        period_cols.append((idx, header))

                if len(period_cols) < 2:  # Need at least 2 periods
                    continue

                # Parse team rows
                tbody = table.find('tbody')
                if not tbody:
                    tbody = table  # Sometimes no tbody

                rows = tbody.find_all('tr')
                if len(rows) < 2:
                    continue

                # Extract scores
                period_scores = {}

                for period_idx, period_name in period_cols:
                    if period_name in ['F', 'T', 'Total']:
                        continue  # Skip total column

                    # Map period number to name
                    period_key = period_name
                    if period_name == '1':
                        period_key = '1st'
                    elif period_name == '2':
                        period_key = '2nd'
                    elif period_name == '3':
                        period_key = '3rd'

                    # Get scores from rows
                    visitor_cells = rows[0].find_all(['td', 'th'])
                    home_cells = rows[1].find_all(['td', 'th'])

                    if period_idx < len(visitor_cells) and period_idx < len(home_cells):
                        visitor_score = visitor_cells[period_idx].text.strip()
                        home_score = home_cells[period_idx].text.strip()

                        # Convert to int if possible
                        try:
                            visitor_score = int(visitor_score)
                            home_score = int(home_score)
                            period_scores[period_key] = {
                                'visitor': visitor_score,
                                'home': home_score
                            }
                        except (ValueError, TypeError):
                            pass  # Not a valid score

                if period_scores:
                    return period_scores

            return None

        except Exception as e:
            print(f"    [!] Error parsing period scores: {e}")
            return None

    def _parse_scoring_summary(self, soup: BeautifulSoup, game: Game) -> Optional[List[Dict]]:
        """Parse scoring summary with goals, assists, and times.

        Looks for sections with "Scoring Summary" or lists of goals.
        """
        try:
            goals = []

            # Look for scoring summary sections
            summary_divs = soup.find_all(['div', 'section'], class_=lambda x: x and ('scoring' in x.lower() if x else False))
            summary_divs += soup.find_all(['div', 'section'], id=lambda x: x and ('scoring' in x.lower() if x else False))

            # Also check for headings
            headings = soup.find_all(['h2', 'h3', 'h4'], string=lambda x: x and 'Scoring' in x)
            for heading in headings:
                parent = heading.parent
                if parent:
                    summary_divs.append(parent)

            for div in summary_divs:
                # Look for lists or tables
                lists = div.find_all(['ul', 'ol', 'table'])

                for list_elem in lists:
                    items = list_elem.find_all(['li', 'tr'])

                    for item in items:
                        goal_text = item.text.strip()

                        # Parse goal format examples:
                        # "1st - 5:23 - Player Name (Assist1, Assist2) - Team"
                        # "2nd Period - 12:45 - #15 John Doe (Unassisted)"

                        # Extract period
                        period = None
                        period_match = re.search(r'(\d+)(?:st|nd|rd|th)\s*(?:Period)?', goal_text, re.IGNORECASE)
                        if period_match:
                            period_num = period_match.group(1)
                            if period_num == '1':
                                period = '1st'
                            elif period_num == '2':
                                period = '2nd'
                            elif period_num == '3':
                                period = '3rd'
                        elif 'OT' in goal_text or 'Overtime' in goal_text:
                            period = 'OT'

                        # Extract time
                        time = None
                        time_match = re.search(r'(\d{1,2}:\d{2})', goal_text)
                        if time_match:
                            time = time_match.group(1)

                        # Extract player name (simple heuristic)
                        player = None
                        player_match = re.search(r'(?:#\d+\s+)?([A-Z][a-z]+\s+[A-Z][a-z]+)', goal_text)
                        if player_match:
                            player = player_match.group(1)

                        # Extract assists
                        assists = []
                        assist_match = re.search(r'\((.*?)\)', goal_text)
                        if assist_match:
                            assist_text = assist_match.group(1)
                            if 'Unassisted' not in assist_text:
                                # Split by comma
                                assists = [a.strip() for a in assist_text.split(',')]

                        if period and time and player:
                            goals.append({
                                'period': period,
                                'time': time,
                                'player': player,
                                'assists': assists,
                                'team': None  # Could be extracted if team info is in the item
                            })

            return goals if goals else None

        except Exception as e:
            print(f"    [!] Error parsing scoring summary: {e}")
            return None

    def _parse_penalties(self, soup: BeautifulSoup, game: Game) -> Optional[List[Dict]]:
        """Parse penalty summary with player, time, and penalty type."""
        try:
            penalties = []

            # Look for penalty sections
            penalty_divs = soup.find_all(['div', 'section'], class_=lambda x: x and ('penalty' in x.lower() if x else False))
            penalty_divs += soup.find_all(['div', 'section'], id=lambda x: x and ('penalty' in x.lower() if x else False))

            # Also check for headings
            headings = soup.find_all(['h2', 'h3', 'h4'], string=lambda x: x and 'Penalt' in x)
            for heading in headings:
                parent = heading.parent
                if parent:
                    penalty_divs.append(parent)

            for div in penalty_divs:
                # Look for lists or tables
                lists = div.find_all(['ul', 'ol', 'table'])

                for list_elem in lists:
                    items = list_elem.find_all(['li', 'tr'])

                    for item in items:
                        penalty_text = item.text.strip()

                        # Parse penalty format examples:
                        # "1st - 8:15 - Player Name - Tripping - 2 min"
                        # "2nd Period - 14:23 - #12 John Doe - Roughing"

                        # Extract period
                        period = None
                        period_match = re.search(r'(\d+)(?:st|nd|rd|th)\s*(?:Period)?', penalty_text, re.IGNORECASE)
                        if period_match:
                            period_num = period_match.group(1)
                            if period_num == '1':
                                period = '1st'
                            elif period_num == '2':
                                period = '2nd'
                            elif period_num == '3':
                                period = '3rd'

                        # Extract time
                        time = None
                        time_match = re.search(r'(\d{1,2}:\d{2})', penalty_text)
                        if time_match:
                            time = time_match.group(1)

                        # Extract player
                        player = None
                        player_match = re.search(r'(?:#\d+\s+)?([A-Z][a-z]+\s+[A-Z][a-z]+)', penalty_text)
                        if player_match:
                            player = player_match.group(1)

                        # Extract penalty type
                        penalty_type = None
                        common_penalties = ['Tripping', 'Hooking', 'Slashing', 'Roughing', 'High-Sticking',
                                           'Interference', 'Holding', 'Cross-Checking', 'Boarding', 'Charging']
                        for pen in common_penalties:
                            if pen in penalty_text:
                                penalty_type = pen
                                break

                        # Extract minutes
                        minutes = None
                        min_match = re.search(r'(\d+)\s*min', penalty_text, re.IGNORECASE)
                        if min_match:
                            minutes = int(min_match.group(1))

                        if period and time:
                            penalties.append({
                                'period': period,
                                'time': time,
                                'player': player or 'Unknown',
                                'penalty': penalty_type or 'Unknown',
                                'minutes': minutes,
                                'team': None
                            })

            return penalties if penalties else None

        except Exception as e:
            print(f"    [!] Error parsing penalties: {e}")
            return None

    def _parse_shots_on_goal(self, soup: BeautifulSoup, game: Game) -> Optional[Dict]:
        """Parse shots on goal by period."""
        try:
            # Look for shots table (often in box score)
            tables = soup.find_all('table', class_=['statTable', 'boxscore', 'scoreTable'])

            for table in tables:
                # Check if table has "Shots" in it
                table_text = table.text.lower()
                if 'shot' not in table_text:
                    continue

                # Find headers
                thead = table.find('thead')
                if not thead:
                    continue

                headers = [th.text.strip() for th in thead.find_all('th')]

                # Look for period columns
                period_cols = []
                for idx, header in enumerate(headers):
                    if header in ['1', '2', '3', 'OT', 'Total']:
                        period_cols.append((idx, header))

                if len(period_cols) < 2:
                    continue

                # Find row with "Shots" label
                rows = table.find_all('tr')
                for row in rows:
                    row_text = row.text.strip()
                    if 'shot' in row_text.lower():
                        cells = row.find_all(['td', 'th'])

                        shots = {}
                        for period_idx, period_name in period_cols:
                            period_key = period_name
                            if period_name == '1':
                                period_key = '1st'
                            elif period_name == '2':
                                period_key = '2nd'
                            elif period_name == '3':
                                period_key = '3rd'
                            elif period_name == 'Total':
                                period_key = 'total'

                            if period_idx < len(cells):
                                shot_text = cells[period_idx].text.strip()
                                try:
                                    shots[period_key] = int(shot_text)
                                except (ValueError, TypeError):
                                    pass

                        if shots:
                            return shots

            return None

        except Exception as e:
            print(f"    [!] Error parsing shots on goal: {e}")
            return None

    async def _scrape_player_stats(self, page: Page):
        """Scrape player statistics from the league stats page.

        URL: /stats/league_instance/{league_id}?subseason={subseason_id}&tab=league_instance_player_stats
        """
        stats_url = f"{self.BASE_URL}/stats/league_instance/{self.league_id}?subseason={self.subseason_id}"

        print(f"\n[*] Scraping player statistics: {stats_url}")

        try:
            # Navigate to stats page with longer timeout
            await page.goto(stats_url, wait_until='commit', timeout=90000)
            await page.wait_for_timeout(5000)  # Wait for page to settle

            # Look for and click Player Stats tab if present
            player_stats_link = page.locator('a:has-text("Player Stats")')
            if await player_stats_link.count() > 0:
                print("[*] Clicking Player Stats tab...")
                await player_stats_link.first.click()
                await page.wait_for_timeout(3000)

            # Get HTML content
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Find all stat tables (there may be multiple for different stat categories)
            tables = soup.find_all('table', class_='statTable')
            print(f"[*] Found {len(tables)} stat tables")

            for table_idx, table in enumerate(tables):
                print(f"\n[*] Processing table {table_idx + 1}...")

                # Get headers
                thead = table.find('thead')
                if not thead:
                    print(f"    [!] No thead found in table {table_idx + 1}")
                    continue

                headers = [th.get_text(strip=True) for th in thead.find_all('th')]
                print(f"    Headers: {headers}")

                # Map headers to indices
                header_map = {h.lower(): idx for idx, h in enumerate(headers)}

                # Parse tbody
                tbody = table.find('tbody')
                if not tbody:
                    print(f"    [!] No tbody found in table {table_idx + 1}")
                    continue

                rows = tbody.find_all('tr')
                print(f"    Found {len(rows)} player rows")

                for row in rows:
                    try:
                        stat = self._parse_player_stat_row(row, headers, header_map, stats_url)
                        if stat:
                            self.player_stats.append(stat)
                    except Exception as e:
                        print(f"    [!] Error parsing player stat row: {e}")
                        continue

            print(f"[✓] Scraped {len(self.player_stats)} player statistics")

        except Exception as e:
            print(f"[!] Error scraping player statistics: {e}")

    def _parse_player_stat_row(self, row, headers: List[str], header_map: Dict[str, int], source_url: str) -> Optional[PlayerStats]:
        """Parse a single player statistics row."""
        cells = row.find_all('td')
        if len(cells) < 3:
            return None

        try:
            # Helper function to get cell value
            def get_value(key: str, default=None):
                idx = header_map.get(key.lower())
                if idx is not None and idx < len(cells):
                    value = cells[idx].get_text(strip=True)
                    return value if value else default
                return default

            def get_int(key: str, default=0):
                val = get_value(key)
                if val:
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return default
                return default

            # Extract player name (usually first column with a link)
            player_name = None
            team_name = None

            # Try to find player name in first few cells
            for cell in cells[:3]:
                link = cell.find('a', class_='playerName')
                if link:
                    player_name = link.get_text(strip=True)
                    break
                # Sometimes player name is just text
                text = cell.get_text(strip=True)
                if text and len(text) > 2 and not text.isdigit():
                    player_name = text
                    break

            # Extract team (often has class 'teamName' or is in a specific column)
            for cell in cells:
                team_link = cell.find('a', class_='teamName')
                if team_link:
                    team_name = team_link.get_text(strip=True)
                    break

            if not player_name:
                return None

            # Get statistics from common column names
            games_played = get_int('gp') or get_int('games played') or get_int('games')
            goals = get_int('g') or get_int('goals')
            assists = get_int('a') or get_int('assists')
            points = get_int('pts') or get_int('points') or get_int('p')
            penalty_minutes = get_int('pim') or get_int('penalty minutes') or get_int('pen')
            plus_minus = get_int('+/-') or get_int('plus/minus')
            power_play_goals = get_int('ppg') or get_int('pp goals')
            short_handed_goals = get_int('shg') or get_int('sh goals')
            game_winning_goals = get_int('gwg') or get_int('game winning goals')

            # Extract division from team name if present (e.g., "8A - Team")
            division = None
            if team_name and ' - ' in team_name:
                division = team_name.split(' - ')[0]

            return PlayerStats(
                name=player_name,
                team=team_name or 'Unknown',
                games_played=games_played,
                goals=goals,
                assists=assists,
                points=points,
                penalty_minutes=penalty_minutes,
                plus_minus=plus_minus,
                power_play_goals=power_play_goals,
                short_handed_goals=short_handed_goals,
                game_winning_goals=game_winning_goals,
                division=division,
                source_url=source_url
            )

        except Exception as e:
            print(f"    [!] Error parsing player stat: {e}")
            return None

    async def _scrape_standings(self, page: Page):
        """Scrape team standings from the league stats page.

        URL: /stats/league_instance/{league_id}?subseason={subseason_id}&tab=league_instance_standings
        """
        standings_url = f"{self.BASE_URL}/stats/league_instance/{self.league_id}?subseason={self.subseason_id}"

        print(f"\n[*] Scraping team standings: {standings_url}")

        try:
            # Navigate to stats page with longer timeout
            await page.goto(standings_url, wait_until='commit', timeout=90000)
            await page.wait_for_timeout(5000)  # Wait for page to settle

            # Look for and click Standings tab if present
            standings_link = page.locator('a:has-text("Standings")')
            if await standings_link.count() > 0:
                print("[*] Clicking Standings tab...")
                await standings_link.first.click()
                await page.wait_for_timeout(3000)

            # Get HTML content
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Find all stat tables (may have multiple divisions)
            tables = soup.find_all('table', class_='statTable')
            print(f"[*] Found {len(tables)} standings tables")

            for table_idx, table in enumerate(tables):
                print(f"\n[*] Processing standings table {table_idx + 1}...")

                # Get headers
                thead = table.find('thead')
                if not thead:
                    print(f"    [!] No thead found in table {table_idx + 1}")
                    continue

                headers = [th.get_text(strip=True) for th in thead.find_all('th')]
                print(f"    Headers: {headers}")

                # Map headers to indices
                header_map = {h.lower(): idx for idx, h in enumerate(headers)}

                # Parse tbody
                tbody = table.find('tbody')
                if not tbody:
                    print(f"    [!] No tbody found in table {table_idx + 1}")
                    continue

                rows = tbody.find_all('tr')
                print(f"    Found {len(rows)} team rows")

                # Try to determine division from context (previous heading, etc.)
                division_name = None
                prev_heading = table.find_previous(['h2', 'h3', 'h4'])
                if prev_heading:
                    division_name = prev_heading.get_text(strip=True)

                for row in rows:
                    try:
                        standing = self._parse_standing_row(row, headers, header_map, division_name, standings_url)
                        if standing:
                            self.standings.append(standing)
                    except Exception as e:
                        print(f"    [!] Error parsing standing row: {e}")
                        continue

            print(f"[✓] Scraped {len(self.standings)} team standings")

        except Exception as e:
            print(f"[!] Error scraping standings: {e}")

    def _parse_standing_row(self, row, headers: List[str], header_map: Dict[str, int], division: Optional[str], source_url: str) -> Optional[TeamStanding]:
        """Parse a single standings row."""
        cells = row.find_all('td')
        if len(cells) < 3:
            return None

        try:
            # Helper function to get cell value
            def get_value(key: str, default=None):
                idx = header_map.get(key.lower())
                if idx is not None and idx < len(cells):
                    value = cells[idx].get_text(strip=True)
                    return value if value else default
                return default

            def get_int(key: str, default=0):
                val = get_value(key)
                if val:
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return default
                return default

            # Extract team name (usually in first column or cell with class 'teamName')
            team_name = None
            team_abbrev = None

            # Look for team name link
            for cell in cells[:3]:
                team_link = cell.find('a', class_='teamName')
                if team_link:
                    team_name = team_link.get_text(strip=True)
                    break

            # If no team name found, use first cell
            if not team_name and cells:
                team_name = cells[0].get_text(strip=True)

            if not team_name:
                return None

            # Team abbreviation might be in a separate column
            team_abbrev = get_value('team') or get_value('abbrev')
            if not team_abbrev:
                # Sometimes it's in the second occurrence of "Team" column
                for idx, cell in enumerate(cells):
                    if idx > 0 and len(cell.get_text(strip=True)) <= 10:
                        potential_abbrev = cell.get_text(strip=True)
                        if potential_abbrev and potential_abbrev != team_name:
                            team_abbrev = potential_abbrev
                            break

            if not team_abbrev:
                team_abbrev = team_name[:10] if team_name else 'N/A'

            # Get standings statistics
            points = get_int('pts') or get_int('points')
            games_played = get_int('gp') or get_int('games played')
            wins = get_int('w') or get_int('wins')
            losses = get_int('l') or get_int('losses')
            ties = get_int('t') or get_int('ties') or get_int('otl')
            goals_for = get_int('gf') or get_int('goals for')
            goals_against = get_int('ga') or get_int('goals against')

            # Record string (e.g., "7-0-0")
            record = get_value('division') or get_value('record') or f"{wins}-{losses}-{ties}"

            # Extract division from team name or record column
            team_division = division
            if not team_division and team_name and ' - ' in team_name:
                team_division = team_name.split(' - ')[0]

            return TeamStanding(
                team_name=team_name,
                team_abbrev=team_abbrev,
                division=team_division,
                points=points,
                games_played=games_played,
                wins=wins,
                losses=losses,
                ties=ties,
                goals_for=goals_for,
                goals_against=goals_against,
                record=record,
                source_url=source_url
            )

        except Exception as e:
            print(f"    [!] Error parsing standing: {e}")
            return None

    async def _scrape_rosters(self, page: Page):
        """Scrape team rosters."""
        print(f"\n[*] Scraping rosters for {len(self.teams)} teams...")

        for i, (team_name, team) in enumerate(list(self.teams.items())[:5], 1):
            if not team.team_url:
                continue

            print(f"[{i}] {team_name}")

            try:
                await page.goto(team.team_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(1000)

                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # TODO: Parse roster table
                # Look for player names, numbers, positions

            except Exception as e:
                print(f"    [!] Error: {e}")
                continue

    def _save_results(self):
        """Save scraped data to JSON files."""
        # Save games
        games_file = self.output_dir / 'schedules.json'
        with open(games_file, 'w') as f:
            json.dump([g.to_dict() for g in self.games], f, indent=2)
        print(f"[✓] Saved games to {games_file}")

        # Save teams
        teams_file = self.output_dir / 'teams.json'
        with open(teams_file, 'w') as f:
            json.dump([t.to_dict() for t in self.teams.values()], f, indent=2)
        print(f"[✓] Saved teams to {teams_file}")

        # Save players (if any)
        if self.players:
            players_file = self.output_dir / 'players.json'
            with open(players_file, 'w') as f:
                json.dump([p.to_dict() for p in self.players], f, indent=2)
            print(f"[✓] Saved players to {players_file}")

        # Save player statistics (if any)
        if self.player_stats:
            stats_file = self.output_dir / 'player_stats.json'
            with open(stats_file, 'w') as f:
                json.dump([s.to_dict() for s in self.player_stats], f, indent=2)
            print(f"[✓] Saved player stats to {stats_file}")

        # Save standings (if any)
        if self.standings:
            standings_file = self.output_dir / 'standings.json'
            with open(standings_file, 'w') as f:
                json.dump([s.to_dict() for s in self.standings], f, indent=2)
            print(f"[✓] Saved standings to {standings_file}")


async def main():
    parser = argparse.ArgumentParser(
        description='Scrape SSC Hockey schedule and game data from HTML'
    )
    parser.add_argument('--league-id', required=True, help='League instance ID (e.g., 224428)')
    parser.add_argument('--subseason-id', required=True, help='Subseason ID (e.g., 948564)')
    parser.add_argument('--out', default='data', help='Output directory')
    parser.add_argument('--headed', action='store_true', help='Run browser in headed mode')
    parser.add_argument('--all-dates', action='store_true', help='Scrape all dates from calendar slider')
    parser.add_argument('--max-dates', type=int, help='Limit number of dates to scrape (for testing)')
    parser.add_argument('--date', help='Scrape a specific date (format: YYYY_MM_DD, e.g., 2024_01_15)')
    parser.add_argument('--scrape-game-details', action='store_true', help='Scrape detailed game statistics (period scores, scoring summary, penalties, shots)')
    parser.add_argument('--scrape-stats', action='store_true', help='Scrape player statistics')
    parser.add_argument('--scrape-standings', action='store_true', help='Scrape team standings')

    args = parser.parse_args()

    scraper = SSCHockeyScraper(
        league_id=args.league_id,
        subseason_id=args.subseason_id,
        output_dir=Path(args.out),
        headless=not args.headed,
        all_dates=args.all_dates,
        max_dates=args.max_dates,
        specific_date=args.date,
        scrape_game_details=args.scrape_game_details,
        scrape_stats=args.scrape_stats,
        scrape_standings=args.scrape_standings
    )

    await scraper.scrape()


if __name__ == '__main__':
    asyncio.run(main())
