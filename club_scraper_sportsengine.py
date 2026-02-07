#!/usr/bin/env python3
"""
SportsEngine Club Scraper

Scrapes SportsEngine-powered youth hockey club websites to extract:
- Team listings with roster/schedule URLs
- Player rosters (name, jersey number, position)
- Coach/staff data (Head Coach, Assistant Coach, Coach)
- Game schedules (date, time, opponent, venue, score)
- Board members and their roles
- Contact information (emails, phones)

Handles two SportsEngine site structures:
- **Flat** (WHK, SS Eagles): Teams page -> individual teams directly
- **Hierarchical** (Marshfield, Seahawks, Plymouth): Teams page ->
  Division pages (Mites, Squirts...) -> individual teams

Tested on: WHK Hawks, Canton, Marshfield, SS Seahawks, SS Eagles, Plymouth
"""

import re
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urljoin

from playwright.async_api import Page
from bs4 import BeautifulSoup, Tag

from club_models import (
    ClubTeam, ClubPlayer, ClubCoach, ClubBoardMember,
    ClubGame, ClubContact
)
from club_scraper_base import (
    ClubScraperBase,
    RE_PAGE_SHOW, RE_ROSTER, RE_SCHEDULE_TEAM, RE_SUBSEASON,
    RE_BOARD_KEYWORDS, RE_CONTACT_KEYWORDS, RE_TEAMS_KEYWORDS,
    RE_COACHES_KEYWORDS, RE_AGE_GROUP, RE_LEVEL,
    NON_TEAM_NAMES,
    extract_age_group, extract_level, split_name,
)


class SportsEngineClubScraper(ClubScraperBase):
    """Scrapes SportsEngine-powered club websites (sportngin.com platform).

    Covers all 20 SSC member clubs plus any SportsEngine site.
    """

    PLATFORM = "sportsengine"

    # ------------------------------------------------------------------
    # Phase 1: Navigation discovery
    # ------------------------------------------------------------------

    async def _discover_navigation(self, page: Page):
        """Navigate to homepage and parse the main navigation menu."""
        print(f"\n[*] Phase 1: Discovering navigation...")
        await self._goto(page, self.club_url)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # SportsEngine nav items have class "theme-nav-item"
        nav_items = soup.find_all('li', class_=lambda c: c and 'theme-nav-item' in c)

        if not nav_items:
            # Fallback: find any nav links
            nav_items = soup.find_all('li', class_=lambda c: c and 'nav-item' in c)

        for item in nav_items:
            link = item.find('a')
            if not link:
                continue

            text = link.get_text(strip=True)
            href = link.get('href', '')
            if not href or href == '#':
                continue

            full_url = urljoin(self.club_url, href)
            entry = {'text': text, 'url': full_url}

            # Classify nav link — check keywords, age groups, and season URLs
            is_team_link = (
                RE_TEAMS_KEYWORDS.search(text)
                or RE_AGE_GROUP.search(text)
                or re.search(r'20\d{2}-20\d{2}', href)  # season year in URL
            )
            if is_team_link and not RE_BOARD_KEYWORDS.search(text):
                self._nav_links['teams'].append(entry)
            elif RE_BOARD_KEYWORDS.search(text):
                self._nav_links['board'].append(entry)
            elif RE_CONTACT_KEYWORDS.search(text):
                self._nav_links['contact'].append(entry)
            elif RE_COACHES_KEYWORDS.search(text):
                self._nav_links['coaches'].append(entry)
            else:
                self._nav_links['other'].append(entry)

            # Also check child links (submenus)
            child_links = item.find_all('a', recursive=True)
            for child in child_links:
                child_text = child.get_text(strip=True)
                child_href = child.get('href', '')
                if not child_href or child_href == '#' or child_text == text:
                    continue
                child_full = urljoin(self.club_url, child_href)
                child_entry = {'text': child_text, 'url': child_full}

                if RE_BOARD_KEYWORDS.search(child_text):
                    self._nav_links['board'].append(child_entry)
                elif RE_CONTACT_KEYWORDS.search(child_text):
                    self._nav_links['contact'].append(child_entry)
                elif RE_COACHES_KEYWORDS.search(child_text):
                    self._nav_links['coaches'].append(child_entry)
                elif RE_TEAMS_KEYWORDS.search(child_text):
                    self._nav_links['teams'].append(child_entry)

        # Also collect mailto: and tel: from homepage
        self._extract_contacts_from_soup(soup, self.club_url)

        team_count = len(self._nav_links['teams'])
        board_count = len(self._nav_links['board'])
        print(f"[OK] Navigation: {team_count} team links, {board_count} board links")

    # ------------------------------------------------------------------
    # Phase 2: Team discovery
    # ------------------------------------------------------------------

    async def _discover_teams(self, page: Page):
        """Discover all teams by following team navigation links.

        Handles two SportsEngine structures:
        - **Flat** (WHK, SS Eagles): Teams page -> individual teams directly
        - **Hierarchical** (Marshfield, Seahawks, Plymouth): Teams page ->
          Division pages (Mites, Squirts...) -> individual teams (Squirt A, B, C)

        After the initial pass we check whether any "team" is really a
        division container (it has child page links but no roster tab).  If
        so, we recurse one level to pick up the real teams.
        """
        print(f"\n[*] Phase 2: Discovering teams...")

        # Strategy: visit a team nav link. SportsEngine team pages have a
        # sub-navigation dropdown listing all other teams in the org.
        # Parse that dropdown to find every team's page_id and subseason_id.

        team_links = self._nav_links['teams']
        if not team_links:
            print("[!] No team links found in navigation, trying common paths")
            # Try common SportsEngine paths
            for path in ['/teams', '/page/show/', '/schedule/day/league_instance/']:
                team_links.append({'text': 'teams', 'url': f"{self.club_url}{path}"})

        # Prioritise links with "team" in the text over "program", "division", etc.
        # This avoids hitting e.g., "Programs" before "MYH Teams"
        def _team_link_priority(entry: Dict[str, str]) -> int:
            t = entry['text'].lower()
            if 'team' in t:
                return 0  # best
            if 'division' in t or 'roster' in t:
                return 1
            return 2  # "program" etc.

        team_links = sorted(team_links, key=_team_link_priority)

        # Deduplicate URLs while preserving order
        seen_urls: Set[str] = set()
        deduped: List[Dict[str, str]] = []
        for tl in team_links:
            if tl['url'] not in seen_urls:
                seen_urls.add(tl['url'])
                deduped.append(tl)
        team_links = deduped

        # Track discovered page IDs to avoid duplicates
        seen_page_ids: Set[str] = set()

        for link_info in team_links[:5]:  # limit to first 5 team nav links
            url = link_info['url']
            print(f"  [*] Checking: {link_info['text']} -> {url}")

            try:
                await self._goto(page, url)
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Look for the team sub-navigation (dropdown listing all teams)
                # SportsEngine uses <select> or <ul> with team links
                teams_found = self._parse_team_subnav(soup, seen_page_ids)

                if teams_found:
                    print(f"  [OK] Found {len(teams_found)} teams from sub-nav")
                    break  # Got the team list, no need to check more nav links

                # Fallback: look for links to /page/show/ pages on this page
                teams_found = self._parse_team_links_from_page(soup, seen_page_ids)
                if teams_found:
                    print(f"  [OK] Found {len(teams_found)} teams from page links")
                    break

            except Exception as e:
                error_msg = f"Error discovering teams from {url}: {e}"
                print(f"  [!] {error_msg}")
                self.errors.append(error_msg)

        # --- Phase 2b: Drill into division containers ---
        # Some clubs use a two-level hierarchy:
        #   Teams page -> Division pages (Mites, Squirts...) -> actual teams
        # Division pages have NO roster tab and contain child team links.
        # Detect and expand them.
        if self.teams:
            await self._expand_division_pages(page, seen_page_ids)

        if not self.teams:
            print("[!] No teams discovered")

    def _parse_team_subnav(self, soup: BeautifulSoup, seen: Set[str]) -> List[ClubTeam]:
        """Parse the team sub-navigation dropdown/list on a SportsEngine team page."""
        found = []

        # Method 1: Look for <select> dropdown with team options
        selects = soup.find_all('select')
        for select in selects:
            options = select.find_all('option')
            for opt in options:
                value = opt.get('value', '')
                text = opt.get_text(strip=True)
                if not value or not text:
                    continue
                # Value is usually a URL like /page/show/9090473?subseason=945073
                page_match = RE_PAGE_SHOW.search(value)
                if page_match:
                    page_id = page_match.group(1)
                    if page_id in seen:
                        continue
                    seen.add(page_id)

                    subseason_match = RE_SUBSEASON.search(value)
                    subseason_id = subseason_match.group(1) if subseason_match else None
                    full_url = urljoin(self.club_url, value)

                    team = self._make_team(
                        team_name=text,
                        page_id=page_id,
                        subseason_id=subseason_id,
                        team_page_url=full_url,
                    )
                    if team:
                        self.teams.append(team)
                        found.append(team)

        # Method 2: Look for sub-nav list items with team links
        # SportsEngine often uses <ul class="sub-nav-list"> or similar
        subnav_links = soup.find_all('a', href=RE_PAGE_SHOW)
        for link in subnav_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if not text:
                continue

            page_match = RE_PAGE_SHOW.search(href)
            if not page_match:
                continue

            page_id = page_match.group(1)
            if page_id in seen:
                continue
            seen.add(page_id)

            subseason_match = RE_SUBSEASON.search(href)
            subseason_id = subseason_match.group(1) if subseason_match else None
            full_url = urljoin(self.club_url, href)

            # Skip non-team links (board pages, etc.)
            if RE_BOARD_KEYWORDS.search(text) or RE_CONTACT_KEYWORDS.search(text):
                continue

            team = self._make_team(
                team_name=text,
                page_id=page_id,
                subseason_id=subseason_id,
                team_page_url=full_url,
            )
            if team:
                self.teams.append(team)
                found.append(team)

        return found

    def _parse_team_links_from_page(self, soup: BeautifulSoup, seen: Set[str]) -> List[ClubTeam]:
        """Fallback: find team links from a general page."""
        found = []
        # Look for links that look like team pages
        content = soup.find('div', class_=lambda c: c and 'content' in c.lower()) or soup
        links = content.find_all('a', href=True)

        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if not text or len(text) > 80:
                continue

            # Must contain age-group-like text or be a /page/show/ link
            page_match = RE_PAGE_SHOW.search(href)
            if not page_match:
                continue

            page_id = page_match.group(1)
            if page_id in seen:
                continue

            # Heuristic: does it look like a team name?
            if not RE_AGE_GROUP.search(text) and not RE_TEAMS_KEYWORDS.search(text):
                continue

            seen.add(page_id)
            subseason_match = RE_SUBSEASON.search(href)
            subseason_id = subseason_match.group(1) if subseason_match else None
            full_url = urljoin(self.club_url, href)

            team = self._make_team(
                team_name=text,
                page_id=page_id,
                subseason_id=subseason_id,
                team_page_url=full_url,
            )
            if team:
                self.teams.append(team)
                found.append(team)

        return found

    # ------------------------------------------------------------------
    # Phase 2b: Expand division containers
    # ------------------------------------------------------------------

    async def _expand_division_pages(self, page: Page, seen: Set[str]):
        """Check discovered 'teams' -- if any are really division containers,
        replace them with their child teams.

        SportsEngine hierarchical clubs (Marshfield, Seahawks, Plymouth) use:
          Teams page -> Division pages (Mites, Squirts...) -> actual team pages

        A **division page** has:
        - Tabs like "Game Schedule | Player Stats | Team Stats" (no Roster tab)
        - Sub-nav links to child team pages

        An **actual team page** has:
        - A "Roster" tab in its tabs

        We visit each discovered team's page. If it's a division, we collect
        its children and remove the division entry.
        """
        originals = list(self.teams)
        divisions_expanded = 0

        for team in originals:
            if not team.team_page_url:
                continue

            # Quick heuristic: single-word age-group names are likely divisions
            # e.g., "Mites", "Squirts", "PeeWees", "Bantams", "Girls", "U6"
            # But "Squirt A", "Mite Grey", "WHK U10 - B" are actual teams.
            name_lower = team.team_name.strip().lower()
            name_words = name_lower.split()
            # Names with >1 meaningful word are likely real teams, skip them
            if len(name_words) > 1 and not name_lower.endswith(' league play'):
                continue

            # Visit the page to check structure
            try:
                await self._goto(page, team.team_page_url)
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                if self._is_division_page(soup):
                    # This is a division -- find child team pages
                    child_teams = self._parse_team_subnav(soup, seen)
                    if not child_teams:
                        child_teams = self._parse_team_links_from_page(soup, seen)

                    if child_teams:
                        print(f"  [*] '{team.team_name}' is a division -> {len(child_teams)} child teams")
                        # Remove the division entry
                        if team in self.teams:
                            self.teams.remove(team)
                        divisions_expanded += 1
                    # If no children found, keep the division as-is (it might still have a roster)

            except Exception as e:
                self.errors.append(f"Error checking division page {team.team_name}: {e}")

        if divisions_expanded:
            print(f"  [OK] Expanded {divisions_expanded} divisions -> {len(self.teams)} total teams")

    @staticmethod
    def _is_division_page(soup: BeautifulSoup) -> bool:
        """Return True if the page looks like a division container, not a team.

        Division pages have tabs like "Game Schedule | Player Stats | Team Stats"
        but no "Roster" tab.  They also have /schedule/day/division_instance/ or
        /stats/division_instance/ links.
        """
        # Check for division_instance in URLs (definitive signal)
        if soup.find('a', href=lambda h: h and 'division_instance' in str(h)):
            return True

        # Check tab structure: division pages typically have these exact 4 tabs
        #   Home | Game Schedule | Player Stats | Team Stats
        # while team pages have: Home | Roster | Game Schedule | ...
        tabs = soup.find_all('a', class_=lambda c: c and ('tab' in str(c).lower()
                                                           or 'nav' in str(c).lower()))
        tab_texts = set()
        for tab in tabs:
            tab_texts.add(tab.get_text(strip=True).lower())

        # Also look for list items that act as tabs
        for li in soup.find_all('li'):
            a = li.find('a')
            if a:
                href = a.get('href', '')
                if '/roster/' in href or '/schedule/' in href or '/stats/' in href:
                    tab_texts.add(a.get_text(strip=True).lower())

        has_roster_tab = 'roster' in tab_texts
        has_division_tabs = ('player stats' in tab_texts or 'team stats' in tab_texts)

        # If there are division-level tabs but NO roster tab -> division container
        if has_division_tabs and not has_roster_tab:
            return True

        return False

    def _is_real_team(self, name: str, has_subseason: bool = False) -> bool:
        """Check if a name looks like an actual team vs a nav page.

        Args:
            name: The display text of the link.
            has_subseason: True if the URL contains a ?subseason= parameter,
                which is a strong signal that this is a team/division page.
        """
        lower = name.lower().strip()
        # Exact matches against known non-team names
        if lower in NON_TEAM_NAMES:
            return False
        # Generic "{Club} Teams" or "{Abbreviation} Teams" are nav pages, not teams
        if re.match(r'^.+\s+teams?\s*$', lower) and not RE_AGE_GROUP.search(name):
            return False
        # Must have some team-like indicator: age group, level, or club-specific name
        if RE_AGE_GROUP.search(name):
            return True
        # Allow names with common team patterns
        if any(kw in lower for kw in ['beginner', 'ltp', 'learn']):
            return True
        # Allow names that contain the club abbreviation AND something else
        if self.abbreviation and self.abbreviation.upper() in name.upper():
            # Must have more than just the abbreviation
            stripped = name.upper().replace(self.abbreviation.upper(), '').strip(' -')
            if stripped:
                return True
        # Accept names starting with age-like codes: "06BSHL", "08BSHLA",
        # "10WISSMAN", "G10", "G12", "18UBSHL" -- common in Plymouth-style naming
        if re.match(r'^(?:0[4-8]|1[0-9]|[Gg]\d)', name.strip()):
            return True
        # If the link has a ?subseason= parameter, trust it as a real team page
        if has_subseason:
            return True
        # Reject short generic names
        if len(name) < 4:
            return False
        # Default: reject ambiguous names to avoid false positives
        return False

    def _make_team(
        self,
        team_name: str,
        page_id: str,
        subseason_id: Optional[str],
        team_page_url: str,
    ) -> Optional[ClubTeam]:
        """Construct a ClubTeam with derived roster/schedule URLs.
        Returns None if the name doesn't look like a real team."""
        if not self._is_real_team(team_name, has_subseason=bool(subseason_id)):
            return None

        # Build roster URL: /roster/show/{page_id}?subseason={subseason_id}
        roster_url = None
        if subseason_id:
            roster_url = urljoin(self.club_url, f"/roster/show/{page_id}?subseason={subseason_id}")

        # Schedule URL requires team_instance_id which differs from page_id.
        # We'll discover it when we visit the team page.
        schedule_url = None

        return ClubTeam(
            club_name=self.club_name,
            team_name=team_name,
            age_group=extract_age_group(team_name),
            division_level=extract_level(team_name),
            season="2025-2026",
            team_page_url=team_page_url,
            roster_url=roster_url,
            schedule_url=schedule_url,
            sportsengine_page_id=page_id,
            subseason_id=subseason_id,
            source_url=self.club_url,
        )

    async def _resolve_team_urls(self, page: Page, team: ClubTeam):
        """Visit a team page to discover its schedule URL (team_instance_id)."""
        if team.schedule_url:
            return  # already resolved

        if not team.team_page_url:
            return

        try:
            await self._goto(page, team.team_page_url)
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Look for schedule tab link
            schedule_link = soup.find('a', href=RE_SCHEDULE_TEAM)
            if schedule_link:
                href = schedule_link.get('href', '')
                team.schedule_url = urljoin(self.club_url, href)
                # Extract team_instance_id
                m = RE_SCHEDULE_TEAM.search(href)
                if m:
                    team.sportsengine_team_instance_id = m.group(1)

            # Also look for roster link if we don't have one
            if not team.roster_url:
                roster_link = soup.find('a', href=RE_ROSTER)
                if roster_link:
                    team.roster_url = urljoin(self.club_url, roster_link.get('href', ''))

        except Exception as e:
            self.errors.append(f"Error resolving URLs for {team.team_name}: {e}")

    # ------------------------------------------------------------------
    # Phase 3a: Roster scraping
    # ------------------------------------------------------------------

    async def _scrape_roster(self, page: Page, team: ClubTeam):
        """Scrape the roster page for a team."""
        if not team.roster_url:
            # Try resolving from team page first
            await self._resolve_team_urls(page, team)
            if not team.roster_url:
                print(f"    [!] No roster URL for {team.team_name}")
                return

        print(f"    [*] Roster: {team.roster_url}")

        try:
            response = await self._goto(page, team.roster_url)

            # Check for login redirect
            if await self._is_login_gated(page):
                msg = f"Roster login-gated for {team.team_name}"
                print(f"    [!] {msg}")
                self.errors.append(msg)
                return

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Find roster table
            table = soup.find('table')
            if not table:
                print(f"    [!] No roster table found for {team.team_name}")
                return

            # Parse header to understand columns
            headers = []
            thead = table.find('thead')
            if thead:
                for th in thead.find_all('th'):
                    headers.append(th.get_text(strip=True).lower())

            # Parse player rows
            tbody = table.find('tbody') or table
            rows = tbody.find_all('tr')
            players_found = 0

            for row in rows:
                try:
                    cells = row.find_all('td')
                    if not cells:
                        continue

                    player = self._parse_roster_row(cells, headers, team)
                    if player:
                        self.players.append(player)
                        players_found += 1

                except Exception as e:
                    self.errors.append(f"Error parsing roster row for {team.team_name}: {e}")

            print(f"    [OK] {players_found} players")

            # --- Scrape Staff tab for coaches ---
            coaches_found = await self._scrape_staff_tab(page, team)
            if coaches_found:
                print(f"    [OK] {coaches_found} coaches")

        except Exception as e:
            error_msg = f"Error scraping roster for {team.team_name}: {e}"
            print(f"    [!] {error_msg}")
            self.errors.append(error_msg)

    async def _scrape_staff_tab(self, page: Page, team: ClubTeam) -> int:
        """Click the Staff tab on a roster page and parse coach/staff data.

        SportsEngine roster pages have Players/Staff tabs.  After clicking
        the Staff tab a second table appears with columns:
            Number | Photo | Name | Title
        Titles like "Head Coach", "Asst. Coach", "Manager", etc.
        """
        try:
            # Look for the Staff tab (an <li> or <a> containing "Staff")
            staff_tab = await page.query_selector('li:has-text("Staff")')
            if not staff_tab:
                staff_tab = await page.query_selector('a:has-text("Staff")')
            if not staff_tab:
                return 0

            await staff_tab.click()
            await page.wait_for_timeout(1500)

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Find the staff table -- the one whose header row contains "Title"
            staff_table = None
            for tbl in soup.find_all('table'):
                thead = tbl.find('thead')
                if thead:
                    header_text = thead.get_text(strip=True).lower()
                    if 'title' in header_text:
                        staff_table = tbl
                        break

            if not staff_table:
                return 0

            # Parse header columns
            headers = []
            thead = staff_table.find('thead')
            if thead:
                headers = [th.get_text(strip=True).lower() for th in thead.find_all('th')]

            # Build column map
            col_map: dict = {}
            for i, h in enumerate(headers):
                if 'name' in h:
                    col_map['name'] = i
                elif 'title' in h:
                    col_map['title'] = i

            # Fallback positional: Number(0), Photo(1), Name(2), Title(3)
            if 'name' not in col_map:
                col_map['name'] = 2
            if 'title' not in col_map:
                col_map['title'] = 3

            tbody = staff_table.find('tbody') or staff_table
            coaches_found = 0

            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if not cells:
                    continue

                # Extract name
                name_idx = col_map.get('name', 2)
                if name_idx >= len(cells):
                    continue
                name_cell = cells[name_idx]
                link = name_cell.find('a')
                name = (link.get_text(strip=True) if link else name_cell.get_text(strip=True))
                if not name:
                    continue

                # Extract title / role
                title_idx = col_map.get('title', 3)
                raw_title = ""
                if title_idx < len(cells):
                    raw_title = cells[title_idx].get_text(strip=True)

                # Normalise role: Head Coach, Assistant Coach, or Coach
                role = self._normalize_coach_role(raw_title)

                coach = ClubCoach(
                    club_name=self.club_name,
                    name=name,
                    team_name=team.team_name,
                    role=role,
                    source_url=team.roster_url or "",
                )
                self.coaches.append(coach)
                coaches_found += 1

            return coaches_found

        except Exception as e:
            self.errors.append(f"Error scraping staff for {team.team_name}: {e}")
            return 0

    @staticmethod
    def _normalize_coach_role(raw_title: str) -> str:
        """Map SportsEngine staff titles to Head Coach / Assistant Coach / Coach."""
        lower = raw_title.lower().strip()
        if not lower:
            return "Coach"
        if 'head coach' in lower:
            return "Head Coach"
        if 'asst' in lower or 'assistant' in lower:
            return "Assistant Coach"
        if 'manager' in lower:
            return "Manager"
        # Anything else (Director, Trainer, etc.) -> just "Coach"
        return "Coach"

    def _parse_roster_row(
        self,
        cells: List[Tag],
        headers: List[str],
        team: ClubTeam
    ) -> Optional[ClubPlayer]:
        """Parse a single roster table row into a ClubPlayer."""
        # Map header names to column indices
        col_map = {}
        for i, h in enumerate(headers):
            if 'number' in h or h == '#' or h == 'no':
                col_map['number'] = i
            elif 'name' in h:
                col_map['name'] = i
            elif 'pos' in h:
                col_map['position'] = i
            elif 'usah' in h or 'registration' in h:
                col_map['usah'] = i

        # If no headers, use positional: Number, Photo, Name, Pos
        if not headers:
            col_map = {'number': 0, 'name': 2, 'position': 3}
            if len(cells) == 3:
                col_map = {'number': 0, 'name': 1, 'position': 2}

        # Extract name (required)
        name_idx = col_map.get('name')
        name = ""
        profile_url = None

        if name_idx is not None and name_idx < len(cells):
            cell = cells[name_idx]
            link = cell.find('a')
            if link:
                name = link.get_text(strip=True)
                href = link.get('href', '')
                if href:
                    profile_url = urljoin(self.club_url, href)
            else:
                name = cell.get_text(strip=True)
        else:
            # Try to find the cell with a name-like link
            for cell in cells:
                link = cell.find('a')
                if link:
                    text = link.get_text(strip=True)
                    if text and len(text) > 2 and not text.isdigit():
                        name = text
                        href = link.get('href', '')
                        if href:
                            profile_url = urljoin(self.club_url, href)
                        break

        if not name:
            return None

        # Extract number
        number = None
        num_idx = col_map.get('number')
        if num_idx is not None and num_idx < len(cells):
            number = cells[num_idx].get_text(strip=True)
            if number and not number.isdigit():
                number = None

        # Extract position
        position = None
        pos_idx = col_map.get('position')
        if pos_idx is not None and pos_idx < len(cells):
            position = cells[pos_idx].get_text(strip=True)
            if position and position not in ('F', 'D', 'G', 'C', 'LW', 'RW', 'LD', 'RD'):
                position = None

        # Extract USAH number
        usah = None
        usah_idx = col_map.get('usah')
        if usah_idx is not None and usah_idx < len(cells):
            usah = cells[usah_idx].get_text(strip=True)

        first, last = split_name(name)

        return ClubPlayer(
            club_name=self.club_name,
            team_name=team.team_name,
            name=name,
            first_name=first,
            last_name=last,
            jersey_number=number,
            position=position,
            usah_number=usah,
            player_profile_url=profile_url,
            source_url=team.roster_url or "",
        )

    # ------------------------------------------------------------------
    # Phase 3b: Schedule scraping
    # ------------------------------------------------------------------

    async def _scrape_schedule(self, page: Page, team: ClubTeam):
        """Scrape the schedule page for a team."""
        if not team.schedule_url:
            await self._resolve_team_urls(page, team)
            if not team.schedule_url:
                print(f"    [!] No schedule URL for {team.team_name}")
                return

        print(f"    [*] Schedule: {team.schedule_url}")

        try:
            await self._goto(page, team.schedule_url)
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # SportsEngine schedule tables use class "statTable"
            table = soup.find('table', class_='statTable')
            if not table:
                # Fallback: any table
                table = soup.find('table')
            if not table:
                print(f"    [!] No schedule table found for {team.team_name}")
                return

            rows = table.find_all('tr')
            games_found = 0
            current_date = ""

            for row in rows:
                try:
                    # Date header rows
                    date_header = row.find('th', colspan=True) or row.find('td', colspan=True)
                    if date_header:
                        date_text = date_header.get_text(strip=True)
                        # Try to parse as date
                        parsed = self._parse_date(date_text)
                        if parsed:
                            current_date = parsed
                        continue

                    cells = row.find_all('td')
                    if not cells or len(cells) < 3:
                        continue

                    game = self._parse_schedule_row(cells, current_date, team)
                    if game:
                        self.games.append(game)
                        games_found += 1

                except Exception as e:
                    self.errors.append(f"Error parsing schedule row for {team.team_name}: {e}")

            print(f"    [OK] {games_found} games")

        except Exception as e:
            error_msg = f"Error scraping schedule for {team.team_name}: {e}"
            print(f"    [!] {error_msg}")
            self.errors.append(error_msg)

    def _parse_schedule_row(
        self,
        cells: List[Tag],
        current_date: str,
        team: ClubTeam
    ) -> Optional[ClubGame]:
        """Parse a single schedule table row into a ClubGame."""
        # SportsEngine schedule rows vary by layout but typically:
        # [Visitor] [Score] [Home] [Location] [Time] or
        # [Date] [Visitor] [Score] [Home] [Location] [Time]

        texts = [c.get_text(strip=True) for c in cells]

        # Try to find score cell (contains "vs" or "-" between numbers)
        score_idx = None
        visitor_name = ""
        home_name = ""
        home_score = None
        away_score = None
        location = ""
        game_time = ""
        game_date = current_date
        game_url = None
        status = "scheduled"

        for i, text in enumerate(texts):
            # Check if this is a date
            parsed_date = self._parse_date(text)
            if parsed_date and not game_date:
                game_date = parsed_date
                continue

            # Check for score pattern like "3 - 2" or "Win 3-2"
            score_match = re.search(r'(\d+)\s*-\s*(\d+)', text)
            if score_match and score_idx is None:
                score_idx = i
                away_score = int(score_match.group(1))
                home_score = int(score_match.group(2))
                status = "final"
                continue

            # Check for time pattern like "7:00 AM" or "7:00 PM EST"
            time_match = re.search(r'\d{1,2}:\d{2}\s*(?:AM|PM)', text, re.IGNORECASE)
            if time_match:
                game_time = text
                continue

        # Try to extract visitor/home from cells
        # Look for team name links
        team_links = []
        for cell in cells:
            link = cell.find('a')
            if link:
                link_text = link.get_text(strip=True)
                if link_text and len(link_text) > 1:
                    href = link.get('href', '')
                    team_links.append({'text': link_text, 'href': href})
                    # Check for game URL
                    if '/game/show/' in href:
                        game_url = urljoin(self.club_url, href)

        if len(team_links) >= 2:
            visitor_name = team_links[0]['text']
            home_name = team_links[1]['text']
        elif len(team_links) == 1:
            # Single opponent listed
            opponent_text = team_links[0]['text']
            # Check if "@" prefix indicates away game
            if texts and '@' in texts[0]:
                visitor_name = team.team_name
                home_name = opponent_text
            else:
                visitor_name = opponent_text
                home_name = team.team_name

        # Determine opponent and home/away
        is_home = None
        opponent = ""
        if team.team_name.lower() in home_name.lower() or self.club_name.lower() in home_name.lower():
            is_home = True
            opponent = visitor_name
        elif team.team_name.lower() in visitor_name.lower() or self.club_name.lower() in visitor_name.lower():
            is_home = False
            opponent = home_name
        else:
            # Can't determine, use first non-matching team
            opponent = visitor_name or home_name

        # Location from remaining text cells
        for text in texts:
            if text and not re.search(r'\d{1,2}:\d{2}', text) and not re.search(r'\d+\s*-\s*\d+', text):
                if len(text) > 3 and text not in (visitor_name, home_name, game_date):
                    if not location or ('rink' in text.lower() or 'arena' in text.lower() or 'ice' in text.lower()):
                        location = text

        if not opponent and not game_date:
            return None

        # Extract game ID from URL
        game_id = None
        if game_url:
            gid_match = re.search(r'/game/show/(\d+)', game_url)
            if gid_match:
                game_id = gid_match.group(1)

        return ClubGame(
            club_name=self.club_name,
            team_name=team.team_name,
            date=game_date,
            opponent=opponent or "TBD",
            time=game_time,
            location=location,
            is_home=is_home,
            home_score=home_score,
            away_score=away_score,
            status=status,
            game_id=game_id,
            game_url=game_url,
            source_url=team.schedule_url or "",
        )

    # ------------------------------------------------------------------
    # Phase 4: Board members
    # ------------------------------------------------------------------

    async def _scrape_board(self, page: Page):
        """Scrape board member pages."""
        board_links = self._nav_links['board']
        if not board_links:
            print(f"\n[*] Phase 4: No board page links found in navigation")
            return

        print(f"\n[*] Phase 4: Scraping board pages ({len(board_links)} links)")

        for link_info in board_links[:3]:  # limit to 3 board pages
            url = link_info['url']
            print(f"  [*] Board page: {link_info['text']} -> {url}")

            try:
                await self._goto(page, url)
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                members = self._parse_board_page(soup, url)
                print(f"  [OK] {len(members)} board members found")

            except Exception as e:
                error_msg = f"Error scraping board page {url}: {e}"
                print(f"  [!] {error_msg}")
                self.errors.append(error_msg)

    def _parse_board_page(self, soup: BeautifulSoup, source_url: str) -> List[ClubBoardMember]:
        """Parse a board/directors page for names and titles."""
        found = []

        # Strategy 1: Look for tables with name/title columns
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    texts = [c.get_text(strip=True) for c in cells]
                    # Heuristic: if one cell looks like a name and another like a title
                    name, title = self._guess_name_and_title(texts)
                    if name:
                        member = ClubBoardMember(
                            club_name=self.club_name,
                            name=name,
                            title=title,
                            source_url=source_url,
                        )
                        self.board_members.append(member)
                        found.append(member)

        if found:
            return found

        # Strategy 2: Look for definition lists (<dl><dt>Title<dd>Name)
        dls = soup.find_all('dl')
        for dl in dls:
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                title_text = dt.get_text(strip=True)
                name_text = dd.get_text(strip=True)
                if name_text and title_text:
                    member = ClubBoardMember(
                        club_name=self.club_name,
                        name=name_text,
                        title=title_text,
                        source_url=source_url,
                    )
                    self.board_members.append(member)
                    found.append(member)

        if found:
            return found

        # Strategy 3: Look for heading + text patterns
        # e.g., <h3>President</h3><p>John Smith</p>
        content = soup.find('div', class_=lambda c: c and 'content' in c.lower()) or soup
        headings = content.find_all(['h2', 'h3', 'h4', 'h5', 'strong'])
        for heading in headings:
            title_text = heading.get_text(strip=True)
            # Check if this looks like a board title
            if RE_BOARD_KEYWORDS.search(title_text) or any(
                kw in title_text.lower() for kw in
                ['president', 'treasurer', 'secretary', 'director', 'coordinator',
                 'registrar', 'vice', 'chair', 'rep']
            ):
                # Get the next sibling text
                next_el = heading.find_next_sibling()
                if next_el:
                    name_text = next_el.get_text(strip=True)
                    if name_text and len(name_text) < 60:
                        member = ClubBoardMember(
                            club_name=self.club_name,
                            name=name_text,
                            title=title_text,
                            source_url=source_url,
                        )
                        self.board_members.append(member)
                        found.append(member)

        # Strategy 4: Look for list items with "Name - Title" or "Title: Name"
        list_items = content.find_all('li')
        for li in list_items:
            text = li.get_text(strip=True)
            name, title = self._parse_name_title_text(text)
            if name:
                member = ClubBoardMember(
                    club_name=self.club_name,
                    name=name,
                    title=title,
                    source_url=source_url,
                )
                self.board_members.append(member)
                found.append(member)

        return found

    def _guess_name_and_title(self, texts: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """From a list of cell texts, guess which is a name and which is a title."""
        if len(texts) < 2:
            return (None, None)

        # Common board titles
        title_keywords = {
            'president', 'treasurer', 'secretary', 'director', 'coordinator',
            'registrar', 'vice president', 'chairman', 'chair', 'representative',
            'rep', 'officer', 'manager', 'head', 'assistant',
        }

        for i, text in enumerate(texts):
            if any(kw in text.lower() for kw in title_keywords):
                # This is likely the title; the other is the name
                other_texts = [t for j, t in enumerate(texts) if j != i and t]
                name = other_texts[0] if other_texts else None
                if name and len(name) < 60 and not any(kw in name.lower() for kw in title_keywords):
                    return (name, text)

        return (None, None)

    def _parse_name_title_text(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse 'Name - Title' or 'Title: Name' from a single string."""
        if not text or len(text) > 120:
            return (None, None)

        # Try "Name - Title" or "Name -- Title"
        for sep in (' - ', ' \u2014 ', ' \u2013 ', ': '):
            if sep in text:
                parts = text.split(sep, 1)
                if len(parts) == 2:
                    a, b = parts[0].strip(), parts[1].strip()
                    if a and b:
                        # Determine which is name vs title
                        title_keywords = {'president', 'director', 'coordinator', 'treasurer', 'secretary', 'registrar'}
                        if any(kw in b.lower() for kw in title_keywords):
                            return (a, b)
                        elif any(kw in a.lower() for kw in title_keywords):
                            return (b, a)

        return (None, None)

    # ------------------------------------------------------------------
    # Phase 5: Contact extraction (override to also visit contact pages)
    # ------------------------------------------------------------------

    async def _scrape_contact_pages(self, page: Page):
        """Scrape dedicated contact pages."""
        contact_links = self._nav_links['contact']
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
