#!/usr/bin/env python3
"""
LeagueApps Club Scraper

Scrapes LeagueApps-powered youth hockey club websites.
Known clubs: Seacoast Spartans (seacoastspartans.com)

Architecture:
  The Seacoast Spartans site (and likely others) is a Webflow main site
  that embeds team content via iframes from LeagueApps subdomains:
    - Boys:  spartans.leagueapps.com/clubteams/{id}/teams/{teamId}
    - Girls: seacoastspartansgirls.leagueapps.com/clubteams/{id}/teams/{teamId}
  Some teams use SportsEngine iframes instead (academy teams).

  The scraper works by:
  1. Loading the homepage to discover /teams/{slug} links in navigation
  2. Visiting each team page to extract the iframe src URL
  3. For LeagueApps iframes: building a roster URL and loading it directly
     with the ngmp_2023_iframe_transition=1 parameter (renders the monolith app)
  4. For SportsEngine iframes: skipping (handled by SportsEngine scraper)
  5. Parsing the rendered roster table for players

Key URL patterns:
  Parent site team page:  /teams/{slug}  (e.g., /teams/2013-elite)
  LeagueApps iframe:      {host}/clubteams/{clubId}/teams/{teamId}
  LeagueApps roster:      {host}/clubteams/{clubId}/teamRoster?teamId={teamId}&ngmp_2023_iframe_transition=1

Roster page structure:
  - Table with headers: ['', 'Number', 'Name', 'Position', '']
  - div.player-name contains player full names
  - Shot hand info in expandable rows
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


# Regex for extracting clubteam/team IDs from LeagueApps URLs
RE_LA_TEAMS = re.compile(r'/clubteams/(\d+)/teams/(\d+)')


class LeagueAppsClubScraper(ClubScraperBase):
    """Scrapes LeagueApps-powered club websites (e.g., Seacoast Spartans).

    The parent site embeds LeagueApps content via iframes.  This scraper:
    1. Discovers team pages from nav links (/teams/{slug})
    2. Visits each to extract the LeagueApps iframe src
    3. Loads the roster URL directly (with iframe transition param)
    4. Parses the rendered player table

    Notable: LeagueApps rosters include player positions and shot hand.
    """

    PLATFORM = "leagueapps"

    # ------------------------------------------------------------------
    # Phase 1: Navigation discovery
    # ------------------------------------------------------------------

    async def _discover_navigation(self, page: Page):
        """Load homepage and parse navigation for team links."""
        print(f"\n[*] Phase 1: Discovering navigation (LeagueApps)...")
        await self._goto(page, self.club_url)
        await page.wait_for_timeout(3000)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Collect /teams/{slug} links
        seen_hrefs: Set[str] = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if not text:
                continue

            # Team links: /teams/{slug}
            if re.match(r'^/teams/[a-z0-9]', href):
                if href not in seen_hrefs:
                    seen_hrefs.add(href)
                    full_url = urljoin(self.club_url, href)
                    self._nav_links['teams'].append({'text': text, 'url': full_url, 'slug': href})

            # Staff/board links
            elif any(kw in text.lower() for kw in ('staff', 'board', 'director')):
                full_url = urljoin(self.club_url, href) if not href.startswith('http') else href
                self._nav_links['board'].append({'text': text, 'url': full_url})

            # Contact links
            elif 'contact' in text.lower():
                full_url = urljoin(self.club_url, href) if not href.startswith('http') else href
                self._nav_links['contact'].append({'text': text, 'url': full_url})

        # Also extract emails/phones from homepage
        self._extract_contacts_from_soup(soup, self.club_url)

        team_count = len(self._nav_links['teams'])
        print(f"[OK] Navigation: {team_count} team links found")

    # ------------------------------------------------------------------
    # Phase 2: Team discovery
    # ------------------------------------------------------------------

    async def _discover_teams(self, page: Page):
        """Visit each team page to extract the LeagueApps iframe URL.

        Each team page at /teams/{slug} embeds an iframe from either:
        - LeagueApps: {host}.leagueapps.com/clubteams/{id}/teams/{teamId}
        - SportsEngine: seacoast*.sportngin.com/...

        We extract the iframe src, parse out the IDs, and build a roster URL.
        """
        print(f"\n[*] Phase 2: Discovering teams...")

        seen_team_ids: Set[str] = set()

        for link_info in self._nav_links['teams']:
            url = link_info['url']
            text = link_info['text']

            try:
                await self._goto(page, url)
                await page.wait_for_timeout(2000)

                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Find the embedded iframe
                iframe_src = None
                for iframe in soup.find_all('iframe'):
                    src = iframe.get('src', '')
                    if 'leagueapps' in src:
                        iframe_src = src
                        break
                    elif 'sportngin' in src or 'sportsengine' in src:
                        # SportsEngine iframe — skip, handled by SE scraper
                        print(f"    [~] {text}: SportsEngine iframe (skipped)")
                        break

                if not iframe_src:
                    continue

                # Normalize src (may start with // or http)
                if iframe_src.startswith('//'):
                    iframe_src = 'https:' + iframe_src
                elif not iframe_src.startswith('http'):
                    iframe_src = urljoin(url, iframe_src)

                # Extract clubteam ID and team ID
                m = RE_LA_TEAMS.search(iframe_src)
                if not m:
                    continue

                clubteam_id = m.group(1)
                team_id = m.group(2)
                composite_id = f"{clubteam_id}-{team_id}"

                if composite_id in seen_team_ids:
                    continue
                seen_team_ids.add(composite_id)

                # Build roster URL from iframe host
                parsed = urlparse(iframe_src)
                la_host = f"{parsed.scheme}://{parsed.hostname}"
                roster_url = (
                    f"{la_host}/clubteams/{clubteam_id}/teamRoster"
                    f"?teamId={team_id}&ngmp_2023_iframe_transition=1"
                )
                team_page_url = iframe_src

                team = ClubTeam(
                    club_name=self.club_name,
                    team_name=text,
                    age_group=extract_age_group(text),
                    division_level=extract_level(text),
                    season="2025-2026",
                    team_page_url=url,
                    roster_url=roster_url,
                    schedule_url=None,
                    source_url=self.club_url,
                )
                self.teams.append(team)

            except Exception as e:
                error_msg = f"Error discovering team {text}: {e}"
                print(f"    [!] {error_msg}")
                self.errors.append(error_msg)

        print(f"[OK] {len(self.teams)} teams discovered (LeagueApps)")

    # ------------------------------------------------------------------
    # Phase 3a: Roster scraping
    # ------------------------------------------------------------------

    async def _scrape_roster(self, page: Page, team: ClubTeam):
        """Scrape the roster from a LeagueApps team page.

        Navigates to the roster URL (with ngmp_2023_iframe_transition=1)
        which renders the monolith app with a player table.

        Table structure:
          Headers: ['', 'Number', 'Name', 'Position', '']
          Each player row: [initials, number, name, position, expand-arrow]
          Expanded rows contain shot hand info.
        """
        if not team.roster_url:
            print(f"    [!] No roster URL for {team.team_name}")
            return

        print(f"    [*] Roster: {team.roster_url[:80]}...")

        try:
            await self._goto(page, team.roster_url)

            # Wait for the monolith app to render
            try:
                await page.wait_for_selector(
                    '.player-name, table, .team-roster',
                    timeout=15000
                )
            except Exception:
                # May not render — try waiting longer
                await page.wait_for_timeout(5000)

            await page.wait_for_timeout(2000)

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            players_found = self._parse_la_roster(soup, team)
            print(f"    [OK] {players_found} players")

        except Exception as e:
            error_msg = f"Error scraping roster for {team.team_name}: {e}"
            print(f"    [!] {error_msg}")
            self.errors.append(error_msg)

    def _parse_la_roster(self, soup: BeautifulSoup, team: ClubTeam) -> int:
        """Parse the LeagueApps roster table.

        Two parsing strategies:
        1. div.player-name elements (more reliable)
        2. Table with headers ['', 'Number', 'Name', 'Position', '']
        """
        players_found = 0

        # Strategy 1: Use div.player-name (React-rendered components)
        player_name_divs = soup.find_all('div', class_='player-name')
        if player_name_divs:
            # Collect all player data from the structured divs
            # The roster renders as a table where each row has:
            # div.player-profilePic (initials), td with number, div.player-name, td with position
            return self._parse_roster_from_table(soup, team)

        # Strategy 2: Fallback to text-based parsing
        text = soup.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Find "Roster" marker and "Number" / "Name" / "Position" headers
        in_roster = False
        for i, line in enumerate(lines):
            if line == 'Roster' and i + 3 < len(lines):
                # Check if next few lines are column headers
                upcoming = ' '.join(lines[i+1:i+5]).lower()
                if 'name' in upcoming and 'position' in upcoming:
                    in_roster = True
                    continue
            # Player data follows headers in groups
            # This is a fallback — Strategy 1 is preferred

        return players_found

    def _parse_roster_from_table(self, soup: BeautifulSoup, team: ClubTeam) -> int:
        """Parse roster from the HTML table with player-name divs.

        The main roster table has headers: ['', 'Number', 'Name', 'Position', '']
        Each player occupies a main row plus an expandable detail row.
        """
        players_found = 0

        # Find the roster table (the one with 'Number' and 'Name' headers)
        roster_table = None
        for table in soup.find_all('table'):
            headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
            if 'name' in headers and ('number' in headers or 'position' in headers):
                roster_table = table
                break

        if not roster_table:
            # Fallback: try parsing player-name divs without table context
            return self._parse_roster_from_divs(soup, team)

        # Map column indices
        headers = [th.get_text(strip=True).lower() for th in roster_table.find_all('th')]
        col_map = {}
        for i, h in enumerate(headers):
            if 'number' in h:
                col_map['number'] = i
            elif 'name' in h:
                col_map['name'] = i
            elif 'position' in h:
                col_map['position'] = i

        tbody = roster_table.find('tbody') or roster_table
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if not cells or len(cells) < 2:
                continue

            # Skip expandable detail rows (contain "Shot" info)
            row_text = row.get_text(strip=True)
            if row_text.startswith('Shot') or row_text == '':
                continue

            # Extract name
            name = None
            name_div = row.find('div', class_='player-name')
            if name_div:
                name = name_div.get_text(strip=True)
            elif 'name' in col_map and col_map['name'] < len(cells):
                name = cells[col_map['name']].get_text(strip=True)

            if not name:
                continue

            # Extract number
            number = None
            if 'number' in col_map and col_map['number'] < len(cells):
                raw_num = cells[col_map['number']].get_text(strip=True)
                raw_num = raw_num.lstrip('#').strip()
                if raw_num and raw_num.isdigit():
                    number = raw_num

            # Extract position
            position = None
            if 'position' in col_map and col_map['position'] < len(cells):
                pos_text = cells[col_map['position']].get_text(strip=True)
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

    def _parse_roster_from_divs(self, soup: BeautifulSoup, team: ClubTeam) -> int:
        """Fallback: parse player names from div.player-name elements."""
        players_found = 0
        seen_names: Set[str] = set()

        for div in soup.find_all('div', class_='player-name'):
            name = div.get_text(strip=True)
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            first, last = split_name(name)
            player = ClubPlayer(
                club_name=self.club_name,
                team_name=team.team_name,
                name=name,
                first_name=first,
                last_name=last,
                jersey_number=None,
                position=None,
                source_url=team.roster_url or "",
            )
            self.players.append(player)
            players_found += 1

        return players_found

    # ------------------------------------------------------------------
    # Phase 3b: Schedule (off by default)
    # ------------------------------------------------------------------

    async def _scrape_schedule(self, page: Page, team: ClubTeam):
        """Scrape schedule from LeagueApps. Off by default."""
        pass

    # ------------------------------------------------------------------
    # Phase 4: Board/staff
    # ------------------------------------------------------------------

    async def _scrape_board(self, page: Page):
        """Scrape board/staff pages.

        For Seacoast Spartans, the /staff page has staff names, titles,
        bios, and email addresses as plain text.
        """
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
                await page.wait_for_timeout(3000)

                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Extract staff info from page text
                self._parse_staff_page(soup, url)

                # Also extract emails
                self._extract_contacts_from_soup(soup, url)

            except Exception as e:
                error_msg = f"Error scraping board/staff page: {e}"
                print(f"    [!] {error_msg}")
                self.errors.append(error_msg)

    def _parse_staff_page(self, soup: BeautifulSoup, source_url: str):
        """Parse staff/board members from a text-based staff page.

        Staff page structure example:
          STAFF
          FIRST LAST
          Director of Hockey Operations
          <bio text>
          <contact_email>
          FIRST LAST
          General Manager
          <bio text>
          ...
        """
        body_text = soup.get_text(separator='\n', strip=True)
        lines = body_text.split('\n')

        # Find the staff section
        staff_start = None
        for i, line in enumerate(lines):
            if line.strip().lower() == 'staff' and i > len(lines) // 3:
                # The second "Staff" instance (after nav) is the content section
                staff_start = i + 1
                break

        if staff_start is None:
            return

        # Parse staff entries: NAME (all caps), TITLE, bio, email
        i = staff_start
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and navigation text
            if not line:
                i += 1
                continue

            # Stop at footer markers
            if any(kw in line.lower() for kw in ('join our mailing', 'contact us',
                                                   'newsletter', 'copyright')):
                break

            # Staff name: all caps, 2+ words
            if line.isupper() and len(line.split()) >= 2 and len(line) > 4:
                name = line.title()
                role = None
                email = None

                # Next line should be title/role
                j = i + 1
                if j < len(lines):
                    next_line = lines[j].strip()
                    if not next_line.isupper() and len(next_line) > 3:
                        # Check if it looks like a role (not a bio paragraph)
                        if len(next_line) < 80 and '@' not in next_line:
                            role = next_line
                            j += 1

                # Look for email in following lines
                while j < len(lines) and j <= i + 5:
                    check = lines[j].strip()
                    if '@' in check and '.' in check:
                        email = check
                        break
                    if check.isupper() and len(check.split()) >= 2:
                        break  # Next staff member
                    j += 1

                board_member = ClubBoardMember(
                    club_name=self.club_name,
                    name=name,
                    title=role or "Staff",
                    email=email,
                    phone=None,
                    source_url=source_url,
                )
                self.board_members.append(board_member)

            i += 1
