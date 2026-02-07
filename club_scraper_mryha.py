#!/usr/bin/env python3
"""
MRYHA / Manchester Inferno Club Scraper

Scrapes mryha.org — Manchester Regional Youth Hockey Association.
Club names:
  - "Inferno" for 6U-8U (development) programs
  - "Flames" for 10U+ competitive programs

Platform characteristics:
  - Angular 16.1.4 + PrimeNG + Sprocket Sports API
  - **ROSTERS ARE LOGIN-GATED** (like Crossbar)
  - **COACHES ARE PUBLIC** on /club/coaches page
  - Board members on /club/bod page

Key differences from Bay State Breakers (other Angular site):
  - No team pages in navigation — teams discovered via coach assignments
  - Uses Sprocket Sports staff components, not navigation mega-menu

This scraper extracts:
  - Teams from coach section headings
  - Coaches (name, role, team, email, phone)
  - Board members from /club/bod

It does NOT extract player rosters (requires authentication).

URL patterns:
  /club/coaches   — Public coaches page with team assignments
  /club/bod       — Board of directors
  /club/schedule  — Schedule (optional)

CSS Selectors:
  .staff-row          — Container for a team's coaches section
  .staff-entry        — Individual coach card
  .staff-entry-info   — Coach name, role, contact info
"""

import re
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin

from playwright.async_api import Page
from bs4 import BeautifulSoup

from club_models import ClubTeam, ClubPlayer, ClubCoach, ClubBoardMember, ClubContact
from club_scraper_base import (
    ClubScraperBase,
    extract_age_group, extract_level, split_name,
    RE_BOARD_KEYWORDS, RE_CONTACT_KEYWORDS,
)


class MRYHAClubScraper(ClubScraperBase):
    """Scrapes mryha.org (Manchester Inferno/Flames).

    Key limitations:
    - Player rosters require login (like Crossbar sites)
    - Only coaches/staff data is publicly accessible

    Scraping approach:
    1. Load /club/coaches, wait for Angular to render
    2. Discover teams from section headings (.staff-row h3 or similar)
    3. Extract coaches from .staff-entry elements under each section
    4. Load /club/bod for board members
    """

    PLATFORM = "mryha"

    # URLs for this site
    COACHES_PATH = "/club/coaches"
    BOARD_PATH = "/club/bod"

    # ------------------------------------------------------------------
    # Phase 1: Navigation discovery
    # ------------------------------------------------------------------

    async def _discover_navigation(self, page: Page):
        """Load coaches page to discover teams and navigation links."""
        print(f"\n[*] Phase 1: Discovering navigation (MRYHA)...")

        # Start at homepage to collect any board/contact links
        await self._goto(page, self.club_url)
        await page.wait_for_timeout(3000)  # Angular render time

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Collect board/contact links from navigation
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if not text:
                continue

            full_url = urljoin(self.club_url, href) if not href.startswith('http') else href

            # Board/staff links
            if RE_BOARD_KEYWORDS.search(text) or '/bod' in href.lower():
                self._nav_links['board'].append({'text': text, 'url': full_url})

            # Contact links
            elif RE_CONTACT_KEYWORDS.search(text):
                self._nav_links['contact'].append({'text': text, 'url': full_url})

        # Extract contacts from homepage
        self._extract_contacts_from_soup(soup, self.club_url)

        # Ensure we have the board page in nav links
        bod_url = urljoin(self.club_url, self.BOARD_PATH)
        if not any(link['url'] == bod_url for link in self._nav_links['board']):
            self._nav_links['board'].append({'text': 'Board of Directors', 'url': bod_url})

        print(f"[OK] Navigation: board={len(self._nav_links['board'])} contact={len(self._nav_links['contact'])}")

    # ------------------------------------------------------------------
    # Phase 2: Team discovery (from coaches page)
    # ------------------------------------------------------------------

    async def _discover_teams(self, page: Page):
        """Discover teams and coaches by walking the coaches page in DOM order.

        Page structure:
          H2: Age group section (e.g., "6U/8U TEAMS")
          H3: Team name (e.g., "8U DEVELOPMENT NSHL/GSL BLUE")
          div.staff-row: Coach for that team
          H3: Next team...

        We walk the DOM and associate each coach with the most recent H3 team header.
        """
        print(f"\n[*] Phase 2: Discovering teams and coaches from coaches page...")

        coaches_url = urljoin(self.club_url, self.COACHES_PATH)
        await self._goto(page, coaches_url)

        # Wait for Angular to render the staff components
        try:
            await page.wait_for_selector('.staff-row, .staff-entry', timeout=10000)
        except Exception:
            print(f"[!] Coaches page may not have loaded fully, continuing...")

        await page.wait_for_timeout(3000)  # Extra time for Angular

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Store the coaches page URL for board scraping
        self._coaches_page_url = coaches_url

        # Walk DOM to build team -> coaches mapping
        team_coaches: Dict[str, List[Dict]] = {}  # team_name -> list of coach dicts
        current_team: Optional[str] = None
        current_section: Optional[str] = None  # H2 section (e.g., "6U/8U TEAMS")

        # Find main content area
        main = soup.find('main') or soup.body

        # Walk all elements in order
        for elem in main.find_all(['h2', 'h3', 'div'], recursive=True):
            classes = ' '.join(elem.get('class', []))

            if elem.name == 'h2':
                text = elem.get_text(strip=True)
                if text and len(text) > 2:
                    current_section = text
                    # H2 sections like "SKILLS & DEVELOPMENT COACHES" may have coaches directly
                    if self._looks_like_team_name(text):
                        current_team = text
                        if current_team not in team_coaches:
                            team_coaches[current_team] = []

            elif elem.name == 'h3':
                text = elem.get_text(strip=True)
                if text and len(text) > 2:
                    # H3 is a specific team
                    if self._is_team_header(text):
                        current_team = text
                        if current_team not in team_coaches:
                            team_coaches[current_team] = []

            elif 'staff-row' in classes and current_team:
                # This is a coach entry under the current team
                # Ensure the team exists in the dict
                if current_team not in team_coaches:
                    team_coaches[current_team] = []
                coach_data = self._extract_coach_from_staff_row(elem, coaches_url)
                if coach_data:
                    team_coaches[current_team].append(coach_data)

        # Also check for Skills & Development coaches (they're in a separate section)
        skills_team = "SKILLS & DEVELOPMENT COACHES"
        if skills_team in team_coaches:
            # Rename to something clearer
            team_coaches["Skills & Development"] = team_coaches.pop(skills_team)

        # Create team objects (only for teams with coaches)
        for team_name, coaches_list in team_coaches.items():
            if not coaches_list:
                continue  # Skip teams with no coaches

            team = ClubTeam(
                club_name=self.club_name,
                team_name=team_name,
                age_group=extract_age_group(team_name),
                division_level=extract_level(team_name),
                season="2025-2026",
                team_page_url=coaches_url,
                roster_url=None,  # Don't trigger per-team scrape loop
                source_url=self.club_url,
            )
            self.teams.append(team)

            # Add coaches for this team
            for coach_data in coaches_list:
                coach = ClubCoach(
                    club_name=self.club_name,
                    name=coach_data['name'],
                    team_name=team_name,
                    role=coach_data.get('role', 'Coach'),
                    email=coach_data.get('email'),
                    phone=coach_data.get('phone'),
                    source_url=coaches_url,
                )
                self.coaches.append(coach)

        print(f"[OK] {len(self.teams)} teams, {len(self.coaches)} coaches discovered")
        for t in self.teams:
            coach_count = sum(1 for c in self.coaches if c.team_name == t.team_name)
            print(f"    - {t.team_name} ({coach_count} coaches)")

    def _looks_like_team_name(self, text: str) -> bool:
        """Check if text looks like a team/program name."""
        return self._is_team_header(text)

    def _is_team_header(self, text: str) -> bool:
        """Check if text is a team header (H3 level)."""
        if not text or len(text) < 3:
            return False

        text_lower = text.lower()

        # Skip generic section headers
        skip_patterns = ['travel team overview', 'learn more', 'head coaches']
        for skip in skip_patterns:
            if skip in text_lower:
                return False

        # Must contain an age group indicator
        age_patterns = [
            r'\b\d+u\b',  # 8U, 10U, etc.
            r'\b(mite|squirt|pee\s*wee|bantam|midget)\b',
            r'\b(6u|8u|10u|12u|14u|15u|16u|18u)\b',
            r'\b(development|full\s*ice|hybrid)\b',
            r'\b(major|minor)\b',  # Major I, Minor II
            r'\bskills\b.*\b(coach|development)\b',  # Skills coaches
        ]

        for pattern in age_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True

        return False

    def _extract_coach_from_staff_row(self, staff_row, source_url: str) -> Optional[Dict]:
        """Extract coach data from a staff-row element."""
        entry = staff_row.find(class_='staff-entry')
        if not entry:
            return None

        name = None
        role = None
        email = None
        phone = None

        # Get all text content
        text_content = entry.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in text_content.split('\n') if l.strip()]

        # First line(s) are typically first name, last name
        name_parts = []
        for i, line in enumerate(lines[:3]):
            # Check if it's a role, email, or phone instead
            if '@' in line or line.lower().startswith('email'):
                continue
            if re.match(r'^\(?\d{3}', line):
                continue
            if any(kw in line.lower() for kw in ['coach', 'director', 'coordinator', 'manager']):
                role = line
                continue

            # Looks like a name part
            if len(line) < 30 and line[0].isupper():
                name_parts.append(line)
                if len(name_parts) >= 2:
                    break

        if name_parts:
            name = ' '.join(name_parts)

        # Look for role if not found yet
        if not role:
            for line in lines:
                if any(kw in line.lower() for kw in ['coach', 'director', 'coordinator', 'manager', 'trainer']):
                    role = line
                    break

        # Look for email
        email_link = entry.find('a', href=re.compile(r'^mailto:', re.I))
        if email_link:
            email = email_link.get('href', '').replace('mailto:', '').split('?')[0].strip()

        # Look for phone
        phone_link = entry.find('a', href=re.compile(r'^tel:', re.I))
        if phone_link:
            phone = phone_link.get('href', '').replace('tel:', '').strip()

        if not name or len(name) < 2:
            return None

        return {
            'name': name,
            'role': role or 'Coach',
            'email': email,
            'phone': phone,
        }

    # ------------------------------------------------------------------
    # Phase 3: Roster scraping (coaches extracted in Phase 2)
    # ------------------------------------------------------------------

    async def _scrape_roster(self, page: Page, team: ClubTeam):
        """Skip - coaches are extracted during team discovery in Phase 2.

        Player rosters are login-gated and not accessible.
        """
        # Coaches were already extracted during _discover_teams()
        # This method is called but does nothing
        pass

    # ------------------------------------------------------------------
    # Phase 3b: Schedule (optional, not implemented)
    # ------------------------------------------------------------------

    async def _scrape_schedule(self, page: Page, team: ClubTeam):
        """Scrape schedule. Not implemented for MRYHA."""
        pass

    # ------------------------------------------------------------------
    # Phase 4: Board members
    # ------------------------------------------------------------------

    async def _scrape_board(self, page: Page):
        """Scrape board members from /club/bod page."""
        board_links = self._nav_links.get('board', [])
        if not board_links:
            print(f"\n[*] Phase 4: No board pages found")
            return

        print(f"\n[*] Phase 4: Scraping board members ({len(board_links)} links)")

        for link_info in board_links[:2]:  # Limit to first 2
            url = link_info['url']
            text = link_info['text']
            print(f"    [*] {text}: {url}")

            try:
                await self._goto(page, url)

                # Wait for Angular to render
                try:
                    await page.wait_for_selector('.staff-entry, .board-member', timeout=10000)
                except Exception:
                    pass

                await page.wait_for_timeout(3000)

                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Parse board members from staff-entry elements
                self._parse_board_page(soup, url)

                # Also extract contacts
                self._extract_contacts_from_soup(soup, url)

            except Exception as e:
                error_msg = f"Error scraping board page: {e}"
                print(f"    [!] {error_msg}")
                self.errors.append(error_msg)

        print(f"    [OK] {len(self.board_members)} board members found")

    def _parse_board_page(self, soup: BeautifulSoup, source_url: str):
        """Parse board members from a board/staff page."""
        # Look for staff-entry elements
        for entry in soup.find_all(class_=['staff-entry', 'board-member']):
            name = None
            title = None
            email = None
            phone = None

            # Find info element
            info_elem = entry.find(class_=['staff-entry-info', 'info'])
            if info_elem:
                text = info_elem.get_text(separator='\n', strip=True)
                lines = [l.strip() for l in text.split('\n') if l.strip()]

                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if '@' in line:
                        email = line
                    elif re.match(r'^\(?\d{3}', line):
                        phone = line
                    elif not name and i == 0:
                        name = line
                    elif not title and any(kw in line_lower for kw in
                                           ['president', 'vice', 'secretary', 'treasurer',
                                            'director', 'chair', 'member', 'coordinator']):
                        title = line
                    elif not title and len(line) < 60:
                        title = line

            # Also try direct child text
            if not name:
                name_elem = entry.find(class_=['name', 'staff-name'])
                if name_elem:
                    name = name_elem.get_text(strip=True)

            # Email/phone links
            if not email:
                email_link = entry.find('a', href=re.compile(r'^mailto:', re.I))
                if email_link:
                    email = email_link.get('href', '').replace('mailto:', '').split('?')[0].strip()

            if not phone:
                phone_link = entry.find('a', href=re.compile(r'^tel:', re.I))
                if phone_link:
                    phone = phone_link.get('href', '').replace('tel:', '').strip()

            if name:
                board_member = ClubBoardMember(
                    club_name=self.club_name,
                    name=name,
                    title=title or "Board Member",
                    email=email,
                    phone=phone,
                    source_url=source_url,
                )
                self.board_members.append(board_member)
