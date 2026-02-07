#!/usr/bin/env python3
"""
Crossbar Club Scraper

Scrapes Crossbar-powered youth hockey club websites.
Known clubs:
  - Milton Youth Hockey (miltonyouthhockey.org)
  - Lynnfield Youth Hockey (lynnfieldyouthhockey.com)
  - Hingham Youth Hockey (hinghamyouthhockey.com)
  - Pembroke Youth Hockey (pembrokeyouthhockey.com)
  - Mass Admirals (massadmirals.com)

Platform characteristics:
  - REEN template library with Bootstrap/jQuery
  - Teams dropdown nav with click-to-expand menus
  - Team pages at /team/{team_id}
  - **ROSTERS ARE LOGIN-GATED** (401 Unauthorized)
  - **COACHES/STAFF ARE PUBLIC** on team pages

This scraper extracts:
  - Teams from dropdown navigation
  - Coaches/staff from team pages (name, title, phone, email)
  - Schedule/calendar data (optional)

It does NOT extract player rosters (requires authentication).

URL patterns:
  Team page:     /team/{team_id}
  Roster:        /team/{team_id}/roster  (401 - login required)
  Staff:         /team/{team_id}/staff   (401 - login required)
  Calendar:      /team/{team_id}/calendar
  Games:         /team/{team_id}/games

Staff data is embedded on the main team page in <p class="team_staff"> elements.
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


# Regex for team IDs in URLs
RE_TEAM_ID = re.compile(r'/team/(\d+)')


class CrossbarClubScraper(ClubScraperBase):
    """Scrapes Crossbar-powered club websites.

    Key limitations:
    - Player rosters require login (401 Unauthorized)
    - Only coaches/staff data is publicly accessible

    Scraping approach:
    1. Load homepage, click Teams dropdown to reveal team links
    2. Collect /team/{id} URLs from dropdown
    3. Visit each team page, scrape coaches from <p class="team_staff">
    4. Skip roster scraping (not accessible)
    """

    PLATFORM = "crossbar"

    # ------------------------------------------------------------------
    # Phase 1: Navigation discovery
    # ------------------------------------------------------------------

    async def _discover_navigation(self, page: Page):
        """Load homepage and discover teams from dropdown navigation."""
        print(f"\n[*] Phase 1: Discovering navigation (Crossbar)...")
        await self._goto(page, self.club_url)
        await page.wait_for_timeout(2000)

        # Try to expand Teams dropdown by clicking it
        try:
            teams_dropdown = page.locator('a.dropdown-toggle:has-text("Teams")')
            if await teams_dropdown.count() > 0:
                await teams_dropdown.first.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Collect team links
        seen_ids: Set[str] = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if not text:
                continue

            # Team links: /team/{id}
            m = RE_TEAM_ID.search(href)
            if m:
                team_id = m.group(1)
                if team_id not in seen_ids:
                    seen_ids.add(team_id)
                    full_url = urljoin(self.club_url, href)
                    self._nav_links['teams'].append({
                        'text': text,
                        'url': full_url,
                        'team_id': team_id
                    })

            # Board/staff links
            elif RE_BOARD_KEYWORDS.search(text):
                full_url = urljoin(self.club_url, href) if not href.startswith('http') else href
                self._nav_links['board'].append({'text': text, 'url': full_url})

            # Contact links
            elif RE_CONTACT_KEYWORDS.search(text):
                full_url = urljoin(self.club_url, href) if not href.startswith('http') else href
                self._nav_links['contact'].append({'text': text, 'url': full_url})

        # Also extract contacts from homepage
        self._extract_contacts_from_soup(soup, self.club_url)

        print(f"[OK] Navigation: {len(self._nav_links['teams'])} team links found")

    # ------------------------------------------------------------------
    # Phase 2: Team discovery
    # ------------------------------------------------------------------

    async def _discover_teams(self, page: Page):
        """Build team list from navigation links.

        For Crossbar, teams are discovered in Phase 1 from the dropdown.
        This phase just converts the nav links to ClubTeam objects.
        """
        print(f"\n[*] Phase 2: Discovering teams...")

        for link_info in self._nav_links['teams']:
            team_name = link_info['text']
            team_url = link_info['url']
            team_id = link_info.get('team_id', '')

            team = ClubTeam(
                club_name=self.club_name,
                team_name=team_name,
                age_group=extract_age_group(team_name),
                division_level=extract_level(team_name),
                season="2025-2026",
                team_page_url=team_url,
                # Set roster_url to team page — we scrape coaches from main page
                # (actual player rosters are login-gated, but base class needs
                # roster_url set to trigger the per-team scrape loop)
                roster_url=team_url,
                schedule_url=f"{team_url}/calendar" if team_url else None,
                source_url=self.club_url,
            )
            self.teams.append(team)

        print(f"[OK] {len(self.teams)} teams discovered")

    # ------------------------------------------------------------------
    # Phase 3a: Roster scraping (coaches only)
    # ------------------------------------------------------------------

    async def _scrape_roster(self, page: Page, team: ClubTeam):
        """Scrape coaches/staff from the team page.

        Crossbar rosters are login-gated (401), but coach/staff info
        is publicly visible on the main team page in <p class="team_staff">
        elements.

        Staff format:
          <p class="team_staff">
            <strong>Name</strong><br>
            Title<br>
            <a href="tel:...">Phone</a><br>
            <a href="mailto:...">Email</a>
          </p>
        """
        # For Crossbar, roster_url is set to team_page_url (we scrape coaches
        # from the main team page since actual rosters are login-gated)
        team_url = team.roster_url or team.team_page_url
        if not team_url:
            print(f"    [!] No team page URL for {team.team_name}")
            return

        print(f"    [*] Team page: {team_url[:60]}...")

        try:
            await self._goto(page, team_url)
            await page.wait_for_timeout(2000)

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            coaches_found = self._parse_staff_elements(soup, team)
            print(f"    [OK] {coaches_found} coaches (rosters login-gated)")

        except Exception as e:
            error_msg = f"Error scraping team page for {team.team_name}: {e}"
            print(f"    [!] {error_msg}")
            self.errors.append(error_msg)

    def _parse_staff_elements(self, soup: BeautifulSoup, team: ClubTeam) -> int:
        """Parse <p class="team_staff"> elements for coach data."""
        coaches_found = 0

        for staff_p in soup.find_all('p', class_='team_staff'):
            # Extract name from <strong>
            name_tag = staff_p.find('strong')
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True)
            if not name:
                continue

            # Parse the rest of the content for title, phone, email
            title = None
            phone = None
            email = None

            # Get all text and links after the name
            full_text = staff_p.get_text(separator='\n', strip=True)
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]

            # First line is usually the name, second is title
            if len(lines) > 1:
                # Skip the name line, next is usually title
                for i, line in enumerate(lines[1:], 1):
                    # Check if it's a phone or email (skip those for title)
                    if '@' in line or line.startswith('(') or line[0].isdigit():
                        continue
                    # Looks like a title
                    if any(kw in line.lower() for kw in
                           ('coach', 'manager', 'director', 'assistant', 'trainer')):
                        title = line
                        break
                    # First non-phone/email line after name is probably title
                    if not title and len(line) < 50:
                        title = line

            # Extract phone from tel: links
            phone_link = staff_p.find('a', href=re.compile(r'^tel:', re.I))
            if phone_link:
                phone = phone_link.get('href', '').replace('tel:', '').strip()

            # Extract email from mailto: links
            email_link = staff_p.find('a', href=re.compile(r'^mailto:', re.I))
            if email_link:
                email = email_link.get('href', '').replace('mailto:', '').split('?')[0].strip()

            coach = ClubCoach(
                club_name=self.club_name,
                name=name,
                team_name=team.team_name,
                role=title or "Coach",
                email=email,
                phone=phone,
                source_url=team.team_page_url or "",
            )
            self.coaches.append(coach)
            coaches_found += 1

        return coaches_found

    # ------------------------------------------------------------------
    # Phase 3b: Schedule (optional)
    # ------------------------------------------------------------------

    async def _scrape_schedule(self, page: Page, team: ClubTeam):
        """Scrape schedule from Crossbar calendar page.

        Schedule data is in table.calendar on the team page or /calendar subpage.
        Off by default.
        """
        pass

    # ------------------------------------------------------------------
    # Phase 4: Board/staff
    # ------------------------------------------------------------------

    async def _scrape_board(self, page: Page):
        """Scrape organization-level board/staff pages."""
        board_links = self._nav_links.get('board', [])
        if not board_links:
            print(f"\n[*] Phase 4: No board/staff pages found")
            return

        print(f"\n[*] Phase 4: Scraping board/staff ({len(board_links)} links)")

        for link_info in board_links[:3]:
            url = link_info['url']
            text = link_info['text']
            print(f"    [*] {text}: {url}")

            try:
                await self._goto(page, url)
                await page.wait_for_timeout(2000)

                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Try to parse board members from staff elements
                self._parse_board_page(soup, url)

                # Also extract contacts
                self._extract_contacts_from_soup(soup, url)

            except Exception as e:
                error_msg = f"Error scraping board page: {e}"
                print(f"    [!] {error_msg}")
                self.errors.append(error_msg)

    def _parse_board_page(self, soup: BeautifulSoup, source_url: str):
        """Parse board members from a dedicated board/staff page."""
        # Try team_staff elements first
        for staff_p in soup.find_all('p', class_='team_staff'):
            name_tag = staff_p.find('strong')
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True)
            if not name:
                continue

            title = None
            email = None
            phone = None

            # Parse title from text
            full_text = staff_p.get_text(separator='\n', strip=True)
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            if len(lines) > 1:
                for line in lines[1:]:
                    if '@' not in line and not line[0].isdigit() and len(line) < 60:
                        title = line
                        break

            # Extract email/phone
            email_link = staff_p.find('a', href=re.compile(r'^mailto:', re.I))
            if email_link:
                email = email_link.get('href', '').replace('mailto:', '').split('?')[0].strip()

            phone_link = staff_p.find('a', href=re.compile(r'^tel:', re.I))
            if phone_link:
                phone = phone_link.get('href', '').replace('tel:', '').strip()

            board_member = ClubBoardMember(
                club_name=self.club_name,
                name=name,
                title=title or "Staff",
                email=email,
                phone=phone,
                source_url=source_url,
            )
            self.board_members.append(board_member)
