#!/usr/bin/env python3
"""
Club Scraper Base — Shared utilities and abstract base class.

All platform-specific club scrapers (SportsEngine, Crossbar, LeagueApps,
Angular) inherit from ClubScraperBase and override the phase methods.

Shared utilities (regex patterns, name parsing, slug generation) live here
so every platform module can import them without circular dependencies.
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, BrowserContext
from bs4 import BeautifulSoup

from club_models import (
    ClubInfo, ClubTeam, ClubPlayer, ClubCoach, ClubBoardMember,
    ClubGame, ClubContact, ClubScrapeResult
)


# ---------------------------------------------------------------------------
# Regex patterns — shared across all platform scrapers
# ---------------------------------------------------------------------------

RE_PAGE_SHOW = re.compile(r'/page/show/(\d+)')
RE_ROSTER = re.compile(r'/roster/show/(\d+)')
RE_SCHEDULE_TEAM = re.compile(r'/schedule/team_instance/(\d+)')
RE_SUBSEASON = re.compile(r'subseason=(\d+)')
RE_BOARD_KEYWORDS = re.compile(
    r'board|director|officer|staff|leadership|executive|committee',
    re.IGNORECASE
)
RE_CONTACT_KEYWORDS = re.compile(r'contact|about\s*us|connect', re.IGNORECASE)
RE_TEAMS_KEYWORDS = re.compile(r'team|program|division|roster|league', re.IGNORECASE)
RE_COACHES_KEYWORDS = re.compile(r'coach', re.IGNORECASE)

# Age group extraction from team names
RE_AGE_GROUP = re.compile(
    r'(U\d+|Mite|Squirt|Peewee|Pee\s*Wee|Bantam|Midget|Middle\s*School|High\s*School|LTP|Learn\s*to\s*Play)',
    re.IGNORECASE
)
RE_LEVEL = re.compile(r'\b([ABC]\d?)\b|(?:^|\s)(Gold|Silver|Bronze|Black|White|Red|Blue|Green)\b', re.IGNORECASE)

# Names that are NOT actual teams — SportsEngine nav often includes non-team pages
NON_TEAM_NAMES = {
    'calendar', 'home', 'about us', 'aboutus', 'parents', 'coaches',
    'assets', 'sponsors', 'register', 'registration', 'contact', 'news',
    'photos', 'videos', 'code of conduct', 'locker room policy',
    'board of directors', 'edit my account', 'tryout policy',
    'team store', 'teamstore', 'rinks', 'practice schedule',
    'master schedule', 'team pictures',
}


# ---------------------------------------------------------------------------
# Shared utility functions
# ---------------------------------------------------------------------------

def make_slug(name: str) -> str:
    """Convert club name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')


def extract_age_group(team_name: str) -> Optional[str]:
    """Extract age group from a team name string."""
    m = RE_AGE_GROUP.search(team_name)
    return m.group(1) if m else None


def extract_level(team_name: str) -> Optional[str]:
    """Extract division level (A/B/C or color) from a team name string."""
    m = RE_LEVEL.search(team_name)
    if m:
        return m.group(1) or m.group(2)
    return None


def split_name(full_name: str) -> Tuple[str, str]:
    """Split a full name into first and last."""
    parts = full_name.strip().split()
    if len(parts) == 0:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], " ".join(parts[1:]))


# ---------------------------------------------------------------------------
# ClubScraperBase — abstract base for all platform scrapers
# ---------------------------------------------------------------------------

class ClubScraperBase:
    """Abstract base class for platform-specific club website scrapers.

    Subclasses MUST override the phase methods:
      - _discover_navigation()
      - _discover_teams()
      - _scrape_roster()
      - _scrape_schedule()
      - _scrape_board()

    The base class provides:
      - Browser lifecycle management (scrape() template method)
      - Rate-limited page navigation (_goto)
      - Login wall detection (_is_login_gated)
      - Contact extraction from HTML (_extract_contacts_from_soup)
      - JSON output (_save_results)
      - Date parsing (_parse_date)
    """

    PLATFORM = "unknown"  # Override in subclasses

    def __init__(
        self,
        club_url: str,
        club_name: str,
        output_dir: Path,
        headless: bool = True,
        rate_limit_ms: int = 1000,
        scrape_rosters: bool = True,
        scrape_schedules: bool = False,
        scrape_board: bool = True,
        scrape_contacts: bool = True,
        max_pages: int = 200,
        abbreviation: Optional[str] = None,
        town: Optional[str] = None,
    ):
        self.club_url = club_url.rstrip('/')
        self.club_name = club_name
        self.club_slug = make_slug(club_name)
        self.output_dir = Path(output_dir) / self.club_slug
        self.headless = headless
        self.rate_limit_ms = rate_limit_ms
        self.scrape_rosters = scrape_rosters
        self.scrape_schedules = scrape_schedules
        self.scrape_board = scrape_board
        self.scrape_contacts = scrape_contacts
        self.max_pages = max_pages
        self.abbreviation = abbreviation
        self.town = town

        # Collected data
        self.teams: List[ClubTeam] = []
        self.players: List[ClubPlayer] = []
        self.coaches: List[ClubCoach] = []
        self.board_members: List[ClubBoardMember] = []
        self.games: List[ClubGame] = []
        self.contacts: List[ClubContact] = []
        self.errors: List[str] = []
        self.pages_visited: int = 0
        self._visited_urls: Set[str] = set()

        # Navigation links discovered from homepage
        self._nav_links: Dict[str, List[Dict[str, str]]] = {
            'teams': [],
            'board': [],
            'contact': [],
            'coaches': [],
            'other': [],
        }

    # ------------------------------------------------------------------
    # Main entry point (template method)
    # ------------------------------------------------------------------

    async def scrape(self) -> ClubScrapeResult:
        """Scrape the club website and return structured results.

        This is a template method — it manages the browser lifecycle and
        calls the platform-specific phase methods in order.
        """
        start = time.time()
        print(f"\n{'='*70}")
        print(f"[*] Scraping club: {self.club_name}")
        print(f"[*] URL: {self.club_url}")
        print(f"[*] Platform: {self.PLATFORM}")
        print(f"[*] Output: {self.output_dir}")
        print(f"{'='*70}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            try:
                # Phase 1: Discover navigation
                await self._discover_navigation(page)

                # Phase 2: Discover teams
                await self._discover_teams(page)

                # Phase 3: Scrape per-team data
                for i, team in enumerate(self.teams, 1):
                    print(f"\n[{i}/{len(self.teams)}] {team.team_name}")

                    if self.scrape_rosters and team.roster_url:
                        await self._scrape_roster(page, team)

                    if self.scrape_schedules and team.schedule_url:
                        await self._scrape_schedule(page, team)

                    if self.pages_visited >= self.max_pages:
                        print(f"[!] Max pages ({self.max_pages}) reached, stopping")
                        break

                # Phase 4: Board members
                if self.scrape_board:
                    await self._scrape_board(page)

                # Phase 5: Extract contacts from visited pages
                if self.scrape_contacts:
                    await self._scrape_contact_pages(page)

            except Exception as e:
                error_msg = f"Fatal error scraping {self.club_name}: {e}"
                print(f"[!] {error_msg}")
                self.errors.append(error_msg)

            finally:
                await browser.close()

        duration = time.time() - start

        # Build result
        club_info = ClubInfo(
            club_name=self.club_name,
            club_slug=self.club_slug,
            website_url=self.club_url,
            town=self.town,
            abbreviation=self.abbreviation,
        )

        result = ClubScrapeResult(
            club=club_info,
            teams=self.teams,
            players=self.players,
            coaches=self.coaches,
            board_members=self.board_members,
            games=self.games,
            contacts=self.contacts,
            errors=self.errors,
            pages_visited=self.pages_visited,
            scrape_duration_seconds=round(duration, 2),
        )

        # Save JSON output
        self._save_results(result)

        print(f"\n[OK] {result.summary()}")
        print(f"[OK] Duration: {duration:.1f}s, Pages visited: {self.pages_visited}")

        return result

    # ------------------------------------------------------------------
    # Abstract phase methods — subclasses MUST override these
    # ------------------------------------------------------------------

    async def _discover_navigation(self, page: Page):
        """Parse the homepage navigation menu.

        Populate self._nav_links with classified links:
          teams, board, contact, coaches, other
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement _discover_navigation")

    async def _discover_teams(self, page: Page):
        """Discover all teams. Populate self.teams."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _discover_teams")

    async def _scrape_roster(self, page: Page, team: ClubTeam):
        """Scrape roster (players + coaches) for one team."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _scrape_roster")

    async def _scrape_schedule(self, page: Page, team: ClubTeam):
        """Scrape game schedule for one team."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _scrape_schedule")

    async def _scrape_board(self, page: Page):
        """Scrape board of directors / staff pages."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _scrape_board")

    async def _scrape_contact_pages(self, page: Page):
        """Scrape dedicated contact pages. Default: visit nav contact links."""
        contact_links = self._nav_links.get('contact', [])
        if not contact_links:
            return

        print(f"\n[*] Phase 5: Scraping contact pages ({len(contact_links)} links)")

        for link_info in contact_links[:3]:
            url = link_info['url']
            print(f"  [*] Contact page: {link_info['text']} -> {url}")

            try:
                await self._goto(page, url)
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')
                self._extract_contacts_from_soup(soup, url)

            except Exception as e:
                error_msg = f"Error scraping contact page {url}: {e}"
                print(f"  [!] {error_msg}")
                self.errors.append(error_msg)

        print(f"  [OK] {len(self.contacts)} total contacts collected")

    # ------------------------------------------------------------------
    # Shared infrastructure methods
    # ------------------------------------------------------------------

    async def _goto(self, page: Page, url: str):
        """Navigate to a URL with rate limiting and page counting."""
        if self.pages_visited > 0:
            await page.wait_for_timeout(self.rate_limit_ms)

        self.pages_visited += 1
        self._visited_urls.add(url)

        try:
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            return response
        except Exception as e:
            # On timeout, try once more with longer timeout
            if 'timeout' in str(e).lower():
                await page.wait_for_timeout(2000)
                response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                return response
            raise

    async def _is_login_gated(self, page: Page) -> bool:
        """Check if the current page redirects to a login form."""
        current_url = page.url
        if 'login.sportngin.com' in current_url or 'sign_in' in current_url:
            return True

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Check for login form
        login_form = soup.find('form', action=lambda x: x and 'sign_in' in str(x))
        if login_form:
            return True

        # Check for "sign in" prompts
        body_text = soup.get_text(separator=' ', strip=True).lower()
        if 'please sign in' in body_text or 'members only' in body_text:
            return True

        return False

    def _extract_contacts_from_soup(self, soup: BeautifulSoup, source_url: str):
        """Extract mailto: and tel: links from a page."""
        # Email links
        for link in soup.find_all('a', href=re.compile(r'^mailto:', re.IGNORECASE)):
            email = link.get('href', '').replace('mailto:', '').split('?')[0].strip()
            if email and '@' in email:
                # Avoid duplicates
                existing = {c.value for c in self.contacts if c.contact_type == 'email'}
                if email.lower() not in {e.lower() for e in existing}:
                    self.contacts.append(ClubContact(
                        club_name=self.club_name,
                        contact_type='email',
                        value=email,
                        context=self._url_context(source_url),
                        source_url=source_url,
                    ))

        # Phone links
        for link in soup.find_all('a', href=re.compile(r'^tel:', re.IGNORECASE)):
            phone = link.get('href', '').replace('tel:', '').strip()
            if phone:
                existing = {c.value for c in self.contacts if c.contact_type == 'phone'}
                if phone not in existing:
                    self.contacts.append(ClubContact(
                        club_name=self.club_name,
                        contact_type='phone',
                        value=phone,
                        context=self._url_context(source_url),
                        source_url=source_url,
                    ))

    def _url_context(self, url: str) -> str:
        """Derive a short context label from a URL."""
        path = urlparse(url).path.lower()
        if 'board' in path or 'director' in path:
            return 'board page'
        if 'contact' in path or 'about' in path:
            return 'contact page'
        if 'coach' in path:
            return 'coaches page'
        if path == '/' or path == '':
            return 'homepage'
        return 'page'

    def _parse_date(self, text: str) -> Optional[str]:
        """Try to parse a date string into YYYY-MM-DD format."""
        if not text:
            return None

        # Try common formats
        for fmt in (
            '%m/%d/%Y', '%m/%d/%y',
            '%B %d, %Y', '%b %d, %Y',
            '%A, %B %d, %Y', '%A, %b %d, %Y',
            '%Y-%m-%d',
        ):
            try:
                dt = datetime.strptime(text.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # Try extracting from longer strings
        m = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', text)
        if m:
            return self._parse_date(m.group(1))

        return None

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _save_results(self, result: ClubScrapeResult):
        """Save scrape results to JSON files."""
        # Club info
        with open(self.output_dir / 'club_info.json', 'w') as f:
            json.dump(result.club.to_dict(), f, indent=2, default=str)
        print(f"[OK] Saved club_info.json")

        # Teams
        with open(self.output_dir / 'teams.json', 'w') as f:
            json.dump([t.to_dict() for t in result.teams], f, indent=2, default=str)
        print(f"[OK] Saved teams.json ({len(result.teams)} teams)")

        # Players
        with open(self.output_dir / 'players.json', 'w') as f:
            json.dump([p.to_dict() for p in result.players], f, indent=2, default=str)
        print(f"[OK] Saved players.json ({len(result.players)} players)")

        # Coaches
        with open(self.output_dir / 'coaches.json', 'w') as f:
            json.dump([c.to_dict() for c in result.coaches], f, indent=2, default=str)
        print(f"[OK] Saved coaches.json ({len(result.coaches)} coaches)")

        # Board members
        with open(self.output_dir / 'board_members.json', 'w') as f:
            json.dump([b.to_dict() for b in result.board_members], f, indent=2, default=str)
        print(f"[OK] Saved board_members.json ({len(result.board_members)} board members)")

        # Games
        with open(self.output_dir / 'games.json', 'w') as f:
            json.dump([g.to_dict() for g in result.games], f, indent=2, default=str)
        print(f"[OK] Saved games.json ({len(result.games)} games)")

        # Contacts
        with open(self.output_dir / 'contacts.json', 'w') as f:
            json.dump([c.to_dict() for c in result.contacts], f, indent=2, default=str)
        print(f"[OK] Saved contacts.json ({len(result.contacts)} contacts)")

        # Metadata
        metadata = {
            'club_name': result.club.club_name,
            'club_url': result.club.website_url,
            'platform': self.PLATFORM,
            'scraped_at': datetime.now().isoformat(),
            'pages_visited': result.pages_visited,
            'scrape_duration_seconds': result.scrape_duration_seconds,
            'totals': {
                'teams': len(result.teams),
                'players': len(result.players),
                'coaches': len(result.coaches),
                'board_members': len(result.board_members),
                'games': len(result.games),
                'contacts': len(result.contacts),
            },
            'errors': result.errors,
        }
        with open(self.output_dir / 'scrape_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        print(f"[OK] Saved scrape_metadata.json")
