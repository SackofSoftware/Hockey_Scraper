#!/usr/bin/env python3
"""
Angular/Sprocket Sports Club Scraper

Scrapes Angular-based club websites powered by Sprocket Sports.
Known clubs: Bay State Breakers (baystatebreakers.com)

Platform: Angular SPA built on Sprocket Sports
- Server returns bare HTML shell; ALL content rendered client-side
- Must use Playwright with wait_for_selector() for reliable scraping
- Nav items: <span class="p-menuitem-text ng-star-inserted">

URL patterns:
  Team overview: /team/{teamId}/program/{programId}/overview?teamListContentID={contentId}
  Roster:        /team/{teamId}/program/{programId}/roster?teamListContentID={contentId}
  Schedule:      /team/{teamId}/program/{programId}/schedule?teamListContentID={contentId}

Roster page structure:
  - STAFF section above the table: name + role as text blocks
  - ROSTER table: ['', 'Player Name', 'Jersey Number', 'Primary Position']
  - Jersey numbers have '#' prefix, may contain 'Jersey\\n' text to clean
"""

import re
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page
from bs4 import BeautifulSoup

from club_models import ClubTeam, ClubPlayer, ClubCoach, ClubBoardMember, ClubContact
from club_scraper_base import (
    ClubScraperBase,
    extract_age_group, extract_level, split_name,
)


# Regex for extracting team/program IDs from Angular URLs
RE_ANGULAR_TEAM = re.compile(r'/team/(\d+)/program/(\d+)/(overview|roster|schedule)')


class AngularClubScraper(ClubScraperBase):
    """Scrapes Angular/Sprocket Sports club websites (e.g., Bay State Breakers).

    The Angular app renders everything client-side.  Playwright loads the
    page, waits for Angular to hydrate, then we parse the rendered DOM.

    Navigation discovery collects all team links from the mega-menu
    under "PROGRAMS & TEAMS".  Each team link follows the pattern:
        /team/{teamId}/program/{programId}/overview?teamListContentID={id}
    and the roster is at the same URL with 'roster' instead of 'overview'.
    """

    PLATFORM = "angular"

    # ------------------------------------------------------------------
    # Phase 1: Navigation discovery
    # ------------------------------------------------------------------

    async def _discover_navigation(self, page: Page):
        """Load homepage and parse the Angular mega-menu for team links."""
        print(f"\n[*] Phase 1: Discovering navigation (Angular)...")
        await self._goto(page, self.club_url)

        # Wait for Angular to render the menu
        try:
            await page.wait_for_selector('.p-menuitem-text', timeout=15000)
        except Exception:
            print("[!] Angular menu did not render in time")

        await page.wait_for_timeout(3000)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Parse Angular PrimeNG menu items
        # Structure: <li class="p-menuitem"><a class="p-menuitem-link"><span class="p-menuitem-text">
        for menu_link in soup.find_all('a', class_=lambda c: c and 'p-menuitem-link' in c):
            span = menu_link.find('span', class_='p-menuitem-text')
            if not span:
                continue
            text = span.get_text(strip=True)
            href = menu_link.get('href', '')
            if not text:
                continue

            full_url = urljoin(self.club_url, href) if href else ''
            entry = {'text': text, 'url': full_url}

            # Classify: team link or other
            if RE_ANGULAR_TEAM.search(href):
                self._nav_links['teams'].append(entry)
            elif 'contact' in text.lower():
                self._nav_links['contact'].append(entry)
            elif any(kw in text.lower() for kw in ('board', 'staff', 'director')):
                self._nav_links['board'].append(entry)

        # Also pick up mailto/tel from rendered page
        self._extract_contacts_from_soup(soup, self.club_url)

        team_count = len(self._nav_links['teams'])
        print(f"[OK] Navigation: {team_count} team links found")

    # ------------------------------------------------------------------
    # Phase 2: Team discovery
    # ------------------------------------------------------------------

    async def _discover_teams(self, page: Page):
        """Build team list from discovered navigation links.

        Each Angular team link looks like:
          /team/{teamId}/program/{programId}/overview?teamListContentID={contentId}

        We derive the roster URL by swapping 'overview' for 'roster'.
        """
        print(f"\n[*] Phase 2: Discovering teams...")

        seen_team_ids: Set[str] = set()

        for link_info in self._nav_links['teams']:
            url = link_info['url']
            text = link_info['text']

            # Skip links that point to sprocketsports.com subdomain
            # (some teams redirect to a different host)
            parsed = urlparse(url)
            if parsed.hostname and 'sprocketsports' in parsed.hostname and self.club_url not in url:
                # External sprocketsports URL — still try to scrape it
                pass

            m = RE_ANGULAR_TEAM.search(url)
            if not m:
                continue

            team_id = m.group(1)
            program_id = m.group(2)
            composite_id = f"{team_id}-{program_id}"

            if composite_id in seen_team_ids:
                continue
            seen_team_ids.add(composite_id)

            # Build roster URL
            roster_url = re.sub(r'/overview', '/roster', url)
            if '?' not in roster_url:
                roster_url = url.replace('/overview', '/roster')

            team = ClubTeam(
                club_name=self.club_name,
                team_name=text,
                age_group=extract_age_group(text),
                division_level=extract_level(text),
                season="2025-2026",
                team_page_url=url,
                roster_url=roster_url,
                schedule_url=url.replace('/overview', '/schedule'),
                source_url=self.club_url,
            )
            self.teams.append(team)

        print(f"[OK] {len(self.teams)} teams discovered")

    # ------------------------------------------------------------------
    # Phase 3a: Roster scraping
    # ------------------------------------------------------------------

    async def _scrape_roster(self, page: Page, team: ClubTeam):
        """Scrape the roster page for players and coaches.

        Angular roster pages have:
        - A STAFF section (text blocks with name + role)
        - A ROSTER table with columns: [initials, Player Name, Jersey Number, Primary Position]
        """
        if not team.roster_url:
            print(f"    [!] No roster URL for {team.team_name}")
            return

        print(f"    [*] Roster: {team.roster_url}")

        try:
            await self._goto(page, team.roster_url)

            # Wait for Angular to render the roster
            try:
                await page.wait_for_selector('table', timeout=15000)
            except Exception:
                # No table found — might be empty roster
                pass

            await page.wait_for_timeout(2000)

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # --- Parse STAFF section ---
            coaches_found = self._parse_staff_section(soup, team)

            # --- Parse ROSTER table ---
            players_found = self._parse_roster_table(soup, team)

            print(f"    [OK] {players_found} players, {coaches_found} coaches")

        except Exception as e:
            error_msg = f"Error scraping roster for {team.team_name}: {e}"
            print(f"    [!] {error_msg}")
            self.errors.append(error_msg)

    def _parse_staff_section(self, soup: BeautifulSoup, team: ClubTeam) -> int:
        """Parse the STAFF section above the roster table.

        Sprocket Sports renders staff as text blocks between "Staff" and
        "Roster" markers.  Names appear as paired lines (first, last),
        optionally followed by role title, "Email", name-fragment, phone.

        Examples:
            Staff                           Staff
            Brian                           Greg
            Gibbons                         Carr
            Dexter                          Director of Hockey Operations
            Carnot                          Email
            Roster                          Greg
                                            (781) 424-7349
                                            Brian
                                            Boyle
                                            Roster
        """
        coaches_found = 0

        body_text = soup.get_text(separator='\n', strip=True)
        lines = body_text.split('\n')

        # Collect lines between "Staff" and "Roster"
        staff_lines: List[str] = []
        in_staff = False
        for line in lines:
            stripped = line.strip()
            if stripped.lower() == 'staff':
                in_staff = True
                continue
            if in_staff:
                if stripped.lower() == 'roster' or stripped.startswith('Player Name'):
                    break
                staff_lines.append(stripped)

        if not staff_lines:
            return 0

        # Classify each line
        i = 0
        while i < len(staff_lines):
            line = staff_lines[i]

            # Skip non-name lines: "Email", phone numbers, empty
            if not line or line.lower() == 'email':
                i += 1
                continue

            # Phone number (starts with '(' or digits with dashes)
            if re.match(r'^\(?\d{3}', line):
                i += 1
                continue

            # Role/title line (contains Coach, Director, Manager, etc.)
            if self._is_role_line(line):
                i += 1
                continue

            # This should be a first name — pair with next line as last name
            first_name = line
            last_name = ""
            role = "Coach"

            # Look ahead for last name (skip non-name lines)
            j = i + 1
            if j < len(staff_lines) and self._is_name_line(staff_lines[j]):
                last_name = staff_lines[j]
                j += 1

            # Look for optional role title after the name pair
            if j < len(staff_lines) and self._is_role_line(staff_lines[j]):
                role = self._normalize_coach_role(staff_lines[j])
                j += 1

            # Skip trailing Email/phone/name-fragment for this entry
            while j < len(staff_lines):
                peek = staff_lines[j]
                if peek.lower() == 'email' or re.match(r'^\(?\d{3}', peek):
                    j += 1
                    continue
                # Duplicate first name (appears after "Email" as a label)
                if peek.lower() == first_name.lower():
                    j += 1
                    continue
                break

            full_name = f"{first_name} {last_name}".strip()
            if len(full_name) > 2:
                coach = ClubCoach(
                    club_name=self.club_name,
                    name=full_name,
                    team_name=team.team_name,
                    role=role,
                    source_url=team.roster_url or "",
                )
                self.coaches.append(coach)
                coaches_found += 1

            i = j

        return coaches_found

    @staticmethod
    def _is_role_line(line: str) -> bool:
        """Check if a line is a role/title rather than a name."""
        lower = line.lower().strip()
        role_keywords = ('coach', 'director', 'manager', 'trainer',
                         'coordinator', 'instructor', 'supervisor',
                         'operations', 'president', 'vp ')
        return any(kw in lower for kw in role_keywords)

    @staticmethod
    def _is_name_line(line: str) -> bool:
        """Check if a line looks like a name (not a role, phone, or label)."""
        if not line or line.lower() == 'email':
            return False
        if re.match(r'^\(?\d{3}', line):
            return False
        lower = line.lower()
        role_keywords = ('coach', 'director', 'manager', 'trainer',
                         'coordinator', 'instructor', 'supervisor',
                         'operations', 'president', 'vp ')
        if any(kw in lower for kw in role_keywords):
            return False
        return True

    def _parse_roster_table(self, soup: BeautifulSoup, team: ClubTeam) -> int:
        """Parse the ROSTER table for players.

        Table columns: ['', 'Player Name', 'Jersey Number', 'Primary Position']
        - Column 0: initials avatar (skip)
        - Column 1: Player name (e.g., "C Bourget")
        - Column 2: Jersey number with '#' prefix (e.g., "#98") and possible "Jersey\n" noise
        - Column 3: Position (e.g., "Forward", "Defense", "Goalie")
        """
        players_found = 0

        table = soup.find('table')
        if not table:
            return 0

        # Parse header columns
        headers = []
        for th in table.find_all('th'):
            headers.append(th.get_text(strip=True).lower())

        # Map columns
        col_map = {}
        for i, h in enumerate(headers):
            if 'player' in h or 'name' in h:
                col_map['name'] = i
            elif 'jersey' in h or 'number' in h:
                col_map['number'] = i
            elif 'position' in h:
                col_map['position'] = i

        # Fallback: assume [initials, name, number, position]
        if 'name' not in col_map:
            col_map = {'name': 1, 'number': 2, 'position': 3}

        tbody = table.find('tbody') or table
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if not cells or len(cells) < 2:
                continue

            # Extract name
            name_idx = col_map.get('name', 1)
            if name_idx >= len(cells):
                continue
            name = cells[name_idx].get_text(strip=True)
            if not name:
                continue

            # Extract jersey number
            number = None
            num_idx = col_map.get('number')
            if num_idx is not None and num_idx < len(cells):
                raw_num = cells[num_idx].get_text(strip=True)
                # Clean: "Jersey\n#98" or "#98" -> "98"
                raw_num = re.sub(r'Jersey\s*', '', raw_num).strip()
                raw_num = raw_num.lstrip('#').strip()
                if raw_num and raw_num.isdigit():
                    number = raw_num

            # Extract position
            position = None
            pos_idx = col_map.get('position')
            if pos_idx is not None and pos_idx < len(cells):
                pos_text = cells[pos_idx].get_text(strip=True)
                if pos_text in ('Forward', 'Defense', 'Goalie', 'F', 'D', 'G',
                                'Center', 'Left Wing', 'Right Wing', 'LW', 'RW',
                                'Left Defense', 'Right Defense', 'LD', 'RD', 'C'):
                    position = pos_text

            first, last = split_name(name)

            player = ClubPlayer(
                club_name=self.club_name,
                team_name=team.team_name,
                name=name,
                first_name=first,
                last_name=last,
                jersey_number=number,
                position=position,
                source_url=team.roster_url or "",
            )
            self.players.append(player)
            players_found += 1

        return players_found

    # ------------------------------------------------------------------
    # Phase 3b: Schedule (not implemented, off by default)
    # ------------------------------------------------------------------

    async def _scrape_schedule(self, page: Page, team: ClubTeam):
        """Scrape schedule from Angular team page. Off by default."""
        pass

    # ------------------------------------------------------------------
    # Phase 4: Board members (use contact page)
    # ------------------------------------------------------------------

    async def _scrape_board(self, page: Page):
        """No dedicated board page for Angular/Sprocket sites.
        Contact info is scraped from homepage and contact page instead."""
        # Check if there's a contact page
        contact_links = self._nav_links.get('contact', [])
        if contact_links:
            print(f"\n[*] Phase 4: Checking contact page for staff/board info")
            for link_info in contact_links[:2]:
                try:
                    await self._goto(page, link_info['url'])
                    await page.wait_for_timeout(3000)
                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    self._extract_contacts_from_soup(soup, link_info['url'])
                except Exception as e:
                    self.errors.append(f"Error on contact page: {e}")
        else:
            print(f"\n[*] Phase 4: No board/staff pages found")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_coach_role(raw_title: str) -> str:
        """Normalize staff titles, preserving descriptive roles.

        Simple one-word roles get mapped to standard names.
        Descriptive titles like "Director of Hockey Operations" or
        "Mite Minor (15) - Elite Coach" are title-cased and kept.
        """
        lower = raw_title.lower().strip()
        if not lower:
            return "Coach"
        # Simple one-word matches → standardize
        if lower == 'coach':
            return "Coach"
        if lower == 'head coach':
            return "Head Coach"
        if lower in ('assistant coach', 'asst coach', 'asst. coach'):
            return "Assistant Coach"
        if lower == 'manager':
            return "Manager"
        # Multi-word descriptive title → keep it (title-cased)
        return raw_title.strip().title()

    @staticmethod
    def _fix_concatenated_name(name: str) -> str:
        """Fix names that got concatenated: 'EDWARDBOURGET' -> 'Edward Bourget'.

        Sprocket Sports sometimes renders staff names with no space between
        first and last names.  We try to split on CamelCase boundaries or
        uppercase transitions.
        """
        name = name.strip()
        if not name:
            return name

        # Already has a space -> just title-case it
        if ' ' in name:
            return name.title() if name.isupper() else name

        # Try CamelCase split: "EdwardBourget" -> "Edward Bourget"
        parts = re.findall(r'[A-Z][a-z]+', name)
        if len(parts) >= 2:
            return ' '.join(parts)

        # All-caps concatenated: "EDWARDBOURGET"
        # Can't reliably split without a dictionary, return as-is in title case
        if name.isupper() and len(name) > 3:
            # Try to find a split point using common name length heuristics
            # This is best-effort; many names won't split correctly
            return name.title()

        return name
