#!/usr/bin/env python3
"""
Club Website Scraper — Orchestrator & CLI

Detects which platform a club website uses (SportsEngine, Crossbar,
LeagueApps, Angular) and dispatches to the appropriate platform-specific
scraper module.

Platform scrapers live in separate files so changes to one platform
can't break another:
  - club_scraper_sportsengine.py  (WHK, Canton, Marshfield, Plymouth, etc.)
  - club_scraper_crossbar.py      (Milton)
  - club_scraper_leagueapps.py    (Seacoast Spartans)
  - club_scraper_angular.py       (Bay State Breakers)

Usage:
    # Single club (auto-detects platform)
    python3 club_scraper.py --url https://www.whkhawks.org --name "WHK Hawks"

    # All SSC clubs from config
    python3 club_scraper.py --all --config config/ssc_clubs.json

    # Discover clubs from network bar
    python3 club_scraper.py --discover --config config/ssc_clubs.json

    # Options
    python3 club_scraper.py --url https://www.whkhawks.org --name "WHK" \\
        --out data/clubs --headed --no-rosters --no-schedules --rate-limit 2000
"""

import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from club_scraper_base import ClubScraperBase, make_slug
from club_scraper_sportsengine import SportsEngineClubScraper
from club_scraper_crossbar import CrossbarClubScraper
from club_scraper_leagueapps import LeagueAppsClubScraper
from club_scraper_angular import AngularClubScraper
from club_scraper_mryha import MRYHAClubScraper
from club_scraper_providence import ProvidenceClubScraper
from club_models import ClubInfo, ClubScrapeResult


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def detect_platform(html: str) -> str:
    """Detect which platform a club website uses from its homepage HTML.

    Returns one of: 'sportsengine', 'crossbar', 'leagueapps', 'angular'
    """
    lower = html.lower()

    # SportsEngine / SRM (most SSC clubs)
    if any(indicator in lower for indicator in
           ('sportngin', 'sportsengine', 'theme-nav-item', 'se-widget')):
        return 'sportsengine'

    # Crossbar (Milton)
    if 'crossbar' in lower:
        return 'crossbar'

    # LeagueApps (Seacoast Spartans)
    if any(indicator in lower for indicator in
           ('leagueapps', '/clubteams/', 'la-team')):
        return 'leagueapps'

    # Angular / custom (Bay State Breakers)
    if any(indicator in lower for indicator in
           ('ng-star-inserted', 'angular', 'ng-version')):
        return 'angular'

    # Check <script src> for platform indicators
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup.find_all('script', src=True):
        src = script.get('src', '').lower()
        if 'sportngin' in src or 'sportsengine' in src:
            return 'sportsengine'
        if 'crossbar' in src:
            return 'crossbar'
        if 'leagueapps' in src:
            return 'leagueapps'

    # Default: assume SportsEngine (most clubs use it)
    return 'sportsengine'


# ---------------------------------------------------------------------------
# Factory — create the right scraper for a platform
# ---------------------------------------------------------------------------

PLATFORM_SCRAPERS = {
    'sportsengine': SportsEngineClubScraper,
    'crossbar': CrossbarClubScraper,
    'leagueapps': LeagueAppsClubScraper,
    'angular': AngularClubScraper,
    'mryha': MRYHAClubScraper,
    'providence': ProvidenceClubScraper,
}


def create_club_scraper(platform: str, **kwargs) -> ClubScraperBase:
    """Create the right scraper instance for a given platform.

    Args:
        platform: One of 'sportsengine', 'crossbar', 'leagueapps', 'angular'
        **kwargs: Passed to the scraper constructor (club_url, club_name, etc.)

    Returns:
        A ClubScraperBase subclass instance ready to call .scrape()
    """
    scraper_class = PLATFORM_SCRAPERS.get(platform, SportsEngineClubScraper)
    return scraper_class(**kwargs)


async def detect_and_create_scraper(
    club_url: str,
    club_name: str,
    platform_override: Optional[str] = None,
    **kwargs
) -> ClubScraperBase:
    """Auto-detect platform and create the right scraper.

    If platform_override is provided (e.g., from config), skip detection.
    Otherwise, fetch the homepage and detect the platform from HTML.
    """
    if platform_override:
        platform = platform_override
        print(f"[*] Platform: {platform} (from config)")
    else:
        # Quick-fetch homepage to detect platform
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(club_url, wait_until='domcontentloaded', timeout=30000)
                html = await page.content()
                platform = detect_platform(html)
                print(f"[*] Platform detected: {platform}")
            except Exception as e:
                print(f"[!] Platform detection failed: {e}, defaulting to sportsengine")
                platform = 'sportsengine'
            finally:
                await browser.close()

    return create_club_scraper(
        platform=platform,
        club_url=club_url,
        club_name=club_name,
        **kwargs
    )


# ---------------------------------------------------------------------------
# SSCCrawler — scrape all SSC clubs
# ---------------------------------------------------------------------------

class SSCCrawler:
    """Orchestrates scraping across all SSC member clubs.

    Reads club list from config JSON, auto-detects each club's platform
    (or uses platform field from config), and dispatches to the appropriate
    platform-specific scraper.
    """

    def __init__(
        self,
        config_path: str,
        output_dir: Path,
        headless: bool = True,
        rate_limit_ms: int = 1000,
        scrape_rosters: bool = True,
        scrape_schedules: bool = False,
        scrape_board: bool = True,
        specific_clubs: Optional[List[str]] = None,
        max_pages_per_club: int = 200,
    ):
        self.config_path = config_path
        self.output_dir = Path(output_dir)
        self.headless = headless
        self.rate_limit_ms = rate_limit_ms
        self.scrape_rosters = scrape_rosters
        self.scrape_schedules = scrape_schedules
        self.scrape_board = scrape_board
        self.specific_clubs = specific_clubs
        self.max_pages_per_club = max_pages_per_club

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_clubs(self) -> List[Dict]:
        """Load club list from config JSON."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)

        clubs = config.get('clubs', [])

        # Filter to specific clubs if requested
        if self.specific_clubs:
            names_lower = {n.lower() for n in self.specific_clubs}
            abbrevs_lower = {n.lower() for n in self.specific_clubs}
            clubs = [
                c for c in clubs
                if c['name'].lower() in names_lower
                or c.get('abbreviation', '').lower() in abbrevs_lower
            ]

        return clubs

    async def scrape_all(self) -> List[ClubScrapeResult]:
        """Scrape all configured clubs sequentially."""
        clubs = self.load_clubs()
        print(f"\n[*] SSC Crawler: {len(clubs)} clubs to scrape")

        results = []
        for i, club_config in enumerate(clubs, 1):
            print(f"\n{'#'*70}")
            print(f"# Club {i}/{len(clubs)}: {club_config['name']}")
            print(f"{'#'*70}")

            try:
                # Use platform from config if available, else auto-detect
                platform = club_config.get('platform')

                scraper_kwargs = dict(
                    club_url=club_config['url'],
                    club_name=club_config['name'],
                    output_dir=self.output_dir,
                    headless=self.headless,
                    rate_limit_ms=self.rate_limit_ms,
                    scrape_rosters=self.scrape_rosters,
                    scrape_schedules=self.scrape_schedules,
                    scrape_board=self.scrape_board,
                    max_pages=self.max_pages_per_club,
                    abbreviation=club_config.get('abbreviation'),
                    town=club_config.get('town'),
                )

                if platform:
                    # Known platform — skip detection
                    scraper = create_club_scraper(platform=platform, **scraper_kwargs)
                else:
                    # Auto-detect (requires a quick homepage fetch)
                    scraper = await detect_and_create_scraper(
                        platform_override=None,
                        **scraper_kwargs
                    )

                result = await scraper.scrape()
                results.append(result)

            except Exception as e:
                print(f"[!] Failed to scrape {club_config['name']}: {e}")
                # Create error result
                error_result = ClubScrapeResult(
                    club=ClubInfo(
                        club_name=club_config['name'],
                        club_slug=make_slug(club_config['name']),
                        website_url=club_config['url'],
                    ),
                    errors=[str(e)],
                )
                results.append(error_result)

        # Save summary
        self._save_summary(results)
        return results

    def _save_summary(self, results: List[ClubScrapeResult]):
        """Save an aggregated summary of all club scrapes."""
        summary = {
            'scraped_at': datetime.now().isoformat(),
            'total_clubs': len(results),
            'totals': {
                'teams': sum(len(r.teams) for r in results),
                'players': sum(len(r.players) for r in results),
                'coaches': sum(len(r.coaches) for r in results),
                'board_members': sum(len(r.board_members) for r in results),
                'games': sum(len(r.games) for r in results),
                'contacts': sum(len(r.contacts) for r in results),
                'errors': sum(len(r.errors) for r in results),
            },
            'clubs': [
                {
                    'name': r.club.club_name,
                    'url': r.club.website_url,
                    'teams': len(r.teams),
                    'players': len(r.players),
                    'coaches': len(r.coaches),
                    'board_members': len(r.board_members),
                    'games': len(r.games),
                    'errors': len(r.errors),
                    'duration_seconds': r.scrape_duration_seconds,
                }
                for r in results
            ],
        }

        summary_file = self.output_dir / 'all_clubs_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\n[OK] Saved summary to {summary_file}")


# ---------------------------------------------------------------------------
# Network bar discovery
# ---------------------------------------------------------------------------

async def discover_clubs_from_network_bar(
    start_url: str = "https://www.ssc-hockey.org",
    headless: bool = True
) -> List[Dict]:
    """
    Parse the SportsEngine network bar to discover all SSC member club URLs.

    Returns list of dicts with 'name' and 'url' keys.
    """
    print(f"[*] Discovering clubs from network bar: {start_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(start_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, 'html.parser')

    # SportsEngine network bar has links to all member orgs
    # Look for the network bar container
    clubs = []
    seen_urls = set()

    # Method 1: network bar links
    network_bar = soup.find('div', class_=lambda c: c and 'network-bar' in c.lower())
    if network_bar:
        for link in network_bar.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if href and text and href.startswith('http') and href not in seen_urls:
                seen_urls.add(href)
                clubs.append({'name': text, 'url': href.rstrip('/')})

    # Method 2: any link in the network/conference section
    if not clubs:
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            parent_class = ' '.join(link.parent.get('class', []))
            if ('network' in parent_class.lower() or 'conference' in parent_class.lower()):
                if href.startswith('http') and text and href not in seen_urls:
                    seen_urls.add(href)
                    clubs.append({'name': text, 'url': href.rstrip('/')})

    print(f"[OK] Discovered {len(clubs)} clubs from network bar")
    return clubs


async def update_config_from_discovery(config_path: str, headless: bool = True):
    """Discover clubs from network bar and merge into the config file."""
    discovered = await discover_clubs_from_network_bar(headless=headless)

    if not discovered:
        print("[!] No clubs discovered, config unchanged")
        return

    # Load existing config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {'conference': 'South Shore Conference', 'season': '2025-2026', 'clubs': []}

    existing_urls = {c['url'].rstrip('/').lower() for c in config.get('clubs', [])}

    new_clubs = []
    for club in discovered:
        if club['url'].rstrip('/').lower() not in existing_urls:
            new_clubs.append({
                'name': club['name'],
                'url': club['url'],
                'abbreviation': '',
                'town': '',
            })

    if new_clubs:
        config['clubs'].extend(new_clubs)
        config['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"[OK] Added {len(new_clubs)} new clubs to {config_path}")
        for c in new_clubs:
            print(f"  + {c['name']} ({c['url']})")
    else:
        print("[OK] Config already up to date, no new clubs found")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description='Scrape SSC youth hockey club websites for teams, rosters, schedules, and board info'
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--url', help='URL of a single club website to scrape')
    mode.add_argument('--all', action='store_true', help='Scrape all clubs from config file')
    mode.add_argument('--discover', action='store_true', help='Discover clubs from network bar and update config')

    parser.add_argument('--name', help='Club name (required with --url)')
    parser.add_argument('--config', default='config/ssc_clubs.json', help='Path to SSC clubs config JSON')
    parser.add_argument('--out', default='data/clubs', help='Output directory')
    parser.add_argument('--headed', action='store_true', help='Run browser in headed mode (visible)')
    parser.add_argument('--rate-limit', type=int, default=1000, help='Milliseconds between page loads (default: 1000)')
    parser.add_argument('--no-rosters', action='store_true', help='Skip roster scraping')
    parser.add_argument('--schedules', action='store_true', help='Include schedule scraping (off by default, we have GameSheet)')
    parser.add_argument('--no-board', action='store_true', help='Skip board member scraping')
    parser.add_argument('--max-pages', type=int, default=200, help='Max pages per club (default: 200)')
    parser.add_argument('--clubs', nargs='+', help='Specific club names/abbreviations to scrape (with --all)')
    parser.add_argument('--platform', choices=['sportsengine', 'crossbar', 'leagueapps', 'angular', 'mryha', 'providence'],
                        help='Force a specific platform scraper (skip auto-detection)')

    args = parser.parse_args()

    if args.discover:
        # Discovery mode
        await update_config_from_discovery(args.config, headless=not args.headed)
        return

    if args.all:
        # All-clubs mode
        crawler = SSCCrawler(
            config_path=args.config,
            output_dir=Path(args.out),
            headless=not args.headed,
            rate_limit_ms=args.rate_limit,
            scrape_rosters=not args.no_rosters,
            scrape_schedules=args.schedules,
            scrape_board=not args.no_board,
            specific_clubs=args.clubs,
            max_pages_per_club=args.max_pages,
        )
        results = await crawler.scrape_all()

        # Print summary
        print(f"\n{'='*70}")
        print(f"FINAL SUMMARY")
        print(f"{'='*70}")
        for r in results:
            print(f"  {r.summary()}")

    else:
        # Single-club mode
        if not args.name:
            parser.error("--name is required with --url")

        scraper_kwargs = dict(
            club_url=args.url,
            club_name=args.name,
            output_dir=Path(args.out),
            headless=not args.headed,
            rate_limit_ms=args.rate_limit,
            scrape_rosters=not args.no_rosters,
            scrape_schedules=args.schedules,
            scrape_board=not args.no_board,
            max_pages=args.max_pages,
        )

        if args.platform:
            # Forced platform
            scraper = create_club_scraper(platform=args.platform, **scraper_kwargs)
        else:
            # Auto-detect platform
            scraper = await detect_and_create_scraper(**scraper_kwargs)

        result = await scraper.scrape()
        print(f"\n{result.summary()}")


if __name__ == '__main__':
    asyncio.run(main())
