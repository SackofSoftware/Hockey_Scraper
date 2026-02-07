#!/usr/bin/env python3
"""
Providence Hockey Club Scraper (Limited)

Scrapes providencehockeyclub.com — Providence Hockey Club (Capitals).

**IMPORTANT LIMITATION:**
This site does NOT expose team rosters or coach data through public pages.
It's primarily a marketing site with registration links to LeagueApps.

Platform characteristics:
  - WordPress + Beaver Builder main site
  - LeagueApps subdomain (providencecapitals.leagueapps.com) for event registration only
  - No team iframes embedded (unlike Seacoast Spartans)
  - No roster pages accessible

Key differences from Seacoast Spartans (other LeagueApps-related site):
  - Seacoast embeds LeagueApps iframes in team pages
  - Providence only links to LeagueApps for event registration
  - No player/coach data is exposed

This scraper extracts:
  - Program names from /program-details/ page
  - Contact information
  - Basic club info

It does NOT extract:
  - Player rosters (not available)
  - Coach information (not available)
  - Team schedules (not available)

URL patterns:
  /program-details/   — Program descriptions (text only)
  /about-us/          — About page with contacts
  /contact-us/        — Contact form
  LeagueApps links    — Direct to event registration, no roster data
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


class ProvidenceClubScraper(ClubScraperBase):
    """Scrapes providencehockeyclub.com (Providence Hockey Club).

    **LIMITED SCRAPER** — This site doesn't expose team/roster data.

    What we can extract:
    - Program names (Mites, Squirts, etc.) from program details page
    - Contact information
    - Club info

    What we cannot extract:
    - Player rosters (not publicly accessible)
    - Coach information (not on public pages)
    - Schedules (registration-only)
    """

    PLATFORM = "providence"

    # Known pages on this site
    PROGRAM_PATHS = [
        "/program-details/",
        "/about-us/",
        "/programs/",
    ]

    # ------------------------------------------------------------------
    # Phase 1: Navigation discovery
    # ------------------------------------------------------------------

    async def _discover_navigation(self, page: Page):
        """Load homepage and discover navigation links."""
        print(f"\n[*] Phase 1: Discovering navigation (Providence HC)...")
        print(f"[*] NOTE: This site has limited public data (no rosters)")

        await self._goto(page, self.club_url)
        await page.wait_for_timeout(2000)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Collect navigation links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if not text or len(text) < 2:
                continue

            full_url = urljoin(self.club_url, href) if not href.startswith('http') else href

            # Program/team links
            if any(kw in href.lower() for kw in ['program', 'team', 'hockey']):
                self._nav_links['teams'].append({'text': text, 'url': full_url})

            # Board/staff links
            elif RE_BOARD_KEYWORDS.search(text) or '/staff' in href.lower():
                self._nav_links['board'].append({'text': text, 'url': full_url})

            # Contact links
            elif RE_CONTACT_KEYWORDS.search(text) or '/contact' in href.lower():
                self._nav_links['contact'].append({'text': text, 'url': full_url})

            # About page might have contacts
            elif '/about' in href.lower():
                self._nav_links['contact'].append({'text': text, 'url': full_url})

        # Extract contacts from homepage
        self._extract_contacts_from_soup(soup, self.club_url)

        print(f"[OK] Navigation: teams={len(self._nav_links['teams'])} board={len(self._nav_links['board'])} contact={len(self._nav_links['contact'])}")

    # ------------------------------------------------------------------
    # Phase 2: Team discovery (program names only)
    # ------------------------------------------------------------------

    async def _discover_teams(self, page: Page):
        """Discover program names from the program details page.

        Since this site doesn't have true team pages, we create
        placeholder team entries based on program descriptions.
        """
        print(f"\n[*] Phase 2: Discovering programs (no roster URLs available)...")

        programs_found: Set[str] = set()

        # Try each program path
        for path in self.PROGRAM_PATHS:
            url = urljoin(self.club_url, path)
            try:
                await self._goto(page, url)
                await page.wait_for_timeout(2000)

                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Look for program names in headings
                new_programs = self._extract_program_names(soup)
                programs_found.update(new_programs)

                # Also extract any contacts
                self._extract_contacts_from_soup(soup, url)

            except Exception as e:
                # Page may not exist, that's okay
                pass

        # Also check team nav links we found
        for link_info in self._nav_links['teams'][:5]:
            url = link_info['url']
            text = link_info['text']

            # The link text itself might be a program name
            if self._looks_like_program(text):
                programs_found.add(text)

            # Visit the page to find more
            try:
                await self._goto(page, url)
                await page.wait_for_timeout(2000)

                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                new_programs = self._extract_program_names(soup)
                programs_found.update(new_programs)

            except Exception:
                pass

        # Create team entries (without roster URLs)
        for program_name in sorted(programs_found):
            team = ClubTeam(
                club_name=self.club_name,
                team_name=program_name,
                age_group=extract_age_group(program_name),
                division_level=extract_level(program_name),
                season="2025-2026",
                team_page_url=None,  # No team pages
                roster_url=None,  # No roster URLs — prevents scrape loop
                source_url=self.club_url,
            )
            self.teams.append(team)

        if self.teams:
            print(f"[OK] {len(self.teams)} programs found (no roster data available)")
            for t in self.teams:
                print(f"    - {t.team_name}")
        else:
            print(f"[OK] No programs discovered (site may not list them publicly)")

    def _extract_program_names(self, soup: BeautifulSoup) -> Set[str]:
        """Extract program names from page content."""
        programs: Set[str] = set()

        # Look in headings
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5']):
            text = heading.get_text(strip=True)
            if self._looks_like_program(text):
                # Clean up the program name
                clean_name = self._clean_program_name(text)
                if clean_name:
                    programs.add(clean_name)

        # Look for program names in structured content
        for elem in soup.find_all(['div', 'section', 'article']):
            # Check class for program indicators
            classes = ' '.join(elem.get('class', []))
            if 'program' in classes.lower():
                # Get heading within this element
                inner_heading = elem.find(['h2', 'h3', 'h4'])
                if inner_heading:
                    text = inner_heading.get_text(strip=True)
                    if len(text) > 2:
                        clean_name = self._clean_program_name(text)
                        if clean_name:
                            programs.add(clean_name)

        return programs

    def _looks_like_program(self, text: str) -> bool:
        """Check if text looks like a hockey program name."""
        if not text or len(text) < 3 or len(text) > 100:
            return False

        text_lower = text.lower()

        # Common hockey age group names
        program_keywords = [
            'mite', 'squirt', 'peewee', 'pee wee', 'bantam', 'midget',
            '8u', '10u', '12u', '14u', '16u', '18u',
            'learn to play', 'ltp', 'learn to skate', 'development',
            'travel', 'house', 'rec', 'recreation',
        ]

        for keyword in program_keywords:
            if keyword in text_lower:
                return True

        return False

    def _clean_program_name(self, text: str) -> Optional[str]:
        """Clean up a program name."""
        # Remove common prefixes/suffixes
        text = text.strip()
        text_lower = text.lower()

        # Skip if it's just a generic label or navigation item
        skip_names = [
            'programs', 'our programs', 'hockey programs', 'registration',
            'directions', 'contact', 'about', 'home', 'schedule',
            'register', 'coaches', 'staff', 'board', 'news',
            'house league',  # Generic, prefer specific house league entries
        ]
        if text_lower in skip_names:
            return None

        return text

    # ------------------------------------------------------------------
    # Phase 3: Roster scraping (NOT AVAILABLE)
    # ------------------------------------------------------------------

    async def _scrape_roster(self, page: Page, team: ClubTeam):
        """Skip roster scraping — not available on this site.

        This method is a no-op because Providence Hockey Club doesn't
        expose player or coach data through public pages.
        """
        # Intentionally empty — no roster data available
        pass

    # ------------------------------------------------------------------
    # Phase 3b: Schedule (NOT AVAILABLE)
    # ------------------------------------------------------------------

    async def _scrape_schedule(self, page: Page, team: ClubTeam):
        """Skip schedule scraping — not available on this site."""
        pass

    # ------------------------------------------------------------------
    # Phase 4: Board members (limited)
    # ------------------------------------------------------------------

    async def _scrape_board(self, page: Page):
        """Try to scrape board/staff info from about pages."""
        board_links = self._nav_links.get('board', [])
        contact_links = self._nav_links.get('contact', [])

        all_links = board_links + contact_links
        if not all_links:
            print(f"\n[*] Phase 4: No board/contact pages found")
            return

        print(f"\n[*] Phase 4: Checking for staff info ({len(all_links)} pages)")

        for link_info in all_links[:5]:  # Limit to first 5
            url = link_info['url']
            text = link_info['text']
            print(f"    [*] {text}: {url}")

            try:
                await self._goto(page, url)
                await page.wait_for_timeout(2000)

                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Try to find staff/board members
                self._parse_staff_page(soup, url)

                # Extract any contacts
                self._extract_contacts_from_soup(soup, url)

            except Exception as e:
                error_msg = f"Error loading page: {e}"
                print(f"    [!] {error_msg}")

        print(f"    [OK] {len(self.board_members)} staff/board found, {len(self.contacts)} contacts")

    def _parse_staff_page(self, soup: BeautifulSoup, source_url: str):
        """Try to parse staff/board members from a page.

        WordPress sites often have staff info in various formats.
        """
        # Look for common staff containers
        staff_containers = soup.find_all(
            class_=lambda c: c and any(kw in str(c).lower() for kw in
                                       ['staff', 'team', 'board', 'person', 'member'])
        )

        for container in staff_containers:
            # Look for name
            name = None
            title = None
            email = None

            # Try heading
            heading = container.find(['h3', 'h4', 'h5', 'strong'])
            if heading:
                name = heading.get_text(strip=True)

            # Try finding role/title
            role_elem = container.find(class_=lambda c: c and 'title' in str(c).lower())
            if role_elem:
                title = role_elem.get_text(strip=True)

            # Look for email
            email_link = container.find('a', href=re.compile(r'^mailto:', re.I))
            if email_link:
                email = email_link.get('href', '').replace('mailto:', '').split('?')[0].strip()

            if name and len(name) > 2 and len(name) < 60:
                # Check if it looks like a name (not a heading like "About Us")
                if not any(kw in name.lower() for kw in ['about', 'contact', 'our', 'the', 'welcome']):
                    board_member = ClubBoardMember(
                        club_name=self.club_name,
                        name=name,
                        title=title or "Staff",
                        email=email,
                        phone=None,
                        source_url=source_url,
                    )
                    self.board_members.append(board_member)

        # Also look for text patterns that indicate staff
        # e.g., "John Smith, President" or "Jane Doe - Director"
        body_text = soup.get_text(separator='\n', strip=True)
        for line in body_text.split('\n'):
            line = line.strip()
            if len(line) < 10 or len(line) > 100:
                continue

            # Pattern: Name, Title or Name - Title
            match = re.match(r'^([A-Z][a-z]+ [A-Z][a-z]+)\s*[,\-–]\s*(.+)$', line)
            if match:
                name = match.group(1)
                title = match.group(2)

                # Check for common board titles
                if any(kw in title.lower() for kw in
                       ['president', 'vice', 'secretary', 'treasurer', 'director', 'chair']):
                    # Avoid duplicates
                    existing = {(b.name.lower(), b.title.lower()) for b in self.board_members}
                    if (name.lower(), title.lower()) not in existing:
                        board_member = ClubBoardMember(
                            club_name=self.club_name,
                            name=name,
                            title=title,
                            email=None,
                            phone=None,
                            source_url=source_url,
                        )
                        self.board_members.append(board_member)
