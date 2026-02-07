#!/usr/bin/env python3
"""
SSC Weekly Scraper - Incremental Update Script

Handles incremental updates by:
- Tracking last run timestamp
- Scraping only new dates since last run
- Merging new data with existing data
- Deduplicating games by game_id
- Updating games that now have scores (were scheduled, now final)
- Generating change reports

Usage:
    python3 ssc_weekly_scraper.py --league-id 224428 --subseason-id 948564 --out data/weekly
"""

import asyncio
import argparse
import json
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Optional
from ssc_hockey_scraper import SSCHockeyScraper, Game, PlayerStats, TeamStanding


@dataclass
class ScrapeMetadata:
    """Metadata about a scrape run."""
    timestamp: str
    league_id: str
    subseason_id: str
    total_games: int
    total_player_stats: int
    total_standings: int
    new_games: int
    updated_games: int
    dates_scraped: List[str]


class IncrementalSSCScraper:
    """Wrapper around SSCHockeyScraper for incremental updates."""

    def __init__(self, league_id: str, subseason_id: str, output_dir: Path, headless: bool = True):
        self.league_id = league_id
        self.subseason_id = subseason_id
        self.output_dir = Path(output_dir)
        self.headless = headless

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.output_dir / 'scrape_metadata.json'
        self.previous_data_dir = self.output_dir / 'previous'

    def load_previous_metadata(self) -> Optional[ScrapeMetadata]:
        """Load metadata from previous scrape run."""
        if not self.metadata_file.exists():
            return None

        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
                return ScrapeMetadata(**data)
        except Exception as e:
            print(f"[!] Warning: Could not load previous metadata: {e}")
            return None

    def load_previous_games(self) -> Dict[str, Game]:
        """Load games from previous scrape run, indexed by game_id."""
        prev_schedules = self.output_dir / 'schedules.json'
        if not prev_schedules.exists():
            return {}

        try:
            with open(prev_schedules, 'r') as f:
                games_data = json.load(f)

            games = {}
            for g in games_data:
                game = Game(**g)
                if game.game_id:
                    games[game.game_id] = game

            return games

        except Exception as e:
            print(f"[!] Warning: Could not load previous games: {e}")
            return {}

    def merge_and_deduplicate(self, new_games: List[Game], previous_games: Dict[str, Game]) -> tuple:
        """Merge new games with previous games and identify changes.

        Returns:
            (merged_games, new_count, updated_count)
        """
        merged = {}
        new_count = 0
        updated_count = 0

        # Start with previous games
        for game_id, game in previous_games.items():
            merged[game_id] = game

        # Process new games
        for game in new_games:
            if not game.game_id:
                # Game without ID - add it anyway (shouldn't happen often)
                unique_key = f"{game.date}_{game.time}_{game.visitor_team}_{game.home_team}"
                merged[unique_key] = game
                new_count += 1
                continue

            if game.game_id not in previous_games:
                # Brand new game
                merged[game.game_id] = game
                new_count += 1
            else:
                # Game exists - check if it was updated
                prev_game = previous_games[game.game_id]
                if self._is_game_updated(prev_game, game):
                    merged[game.game_id] = game
                    updated_count += 1
                else:
                    # Keep the previous version if no changes
                    merged[game.game_id] = prev_game

        return list(merged.values()), new_count, updated_count

    def _is_game_updated(self, prev_game: Game, new_game: Game) -> bool:
        """Check if a game has been updated (e.g., scores added, details added)."""
        # Check if scores were added
        if prev_game.visitor_score is None and new_game.visitor_score is not None:
            return True
        if prev_game.home_score is None and new_game.home_score is not None:
            return True

        # Check if scores changed
        if prev_game.visitor_score != new_game.visitor_score:
            return True
        if prev_game.home_score != new_game.home_score:
            return True

        # Check if game details were added
        if prev_game.period_scores is None and new_game.period_scores is not None:
            return True
        if prev_game.scoring_summary is None and new_game.scoring_summary is not None:
            return True
        if prev_game.penalties is None and new_game.penalties is not None:
            return True
        if prev_game.shots_on_goal is None and new_game.shots_on_goal is not None:
            return True

        # Check if status changed
        if prev_game.status != new_game.status:
            return True

        return False

    def generate_change_report(self, new_count: int, updated_count: int,
                              total_games: int, previous_total: int,
                              new_player_stats: int, new_standings: int) -> Dict:
        """Generate a report of changes since last run."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'new_games': new_count,
                'updated_games': updated_count,
                'total_games': total_games,
                'previous_total': previous_total,
                'games_change': total_games - previous_total,
                'player_stats_count': new_player_stats,
                'standings_count': new_standings
            }
        }

        return report

    def backup_previous_data(self):
        """Backup previous scrape data before overwriting."""
        if not (self.output_dir / 'schedules.json').exists():
            return

        # Create backup directory with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = self.previous_data_dir / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Copy files
        files_to_backup = ['schedules.json', 'teams.json', 'player_stats.json',
                          'standings.json', 'scrape_metadata.json']

        for filename in files_to_backup:
            src = self.output_dir / filename
            if src.exists():
                shutil.copy2(src, backup_dir / filename)

        print(f"[✓] Backed up previous data to {backup_dir}")

        # Clean old backups (keep last 10)
        self._cleanup_old_backups()

    def _cleanup_old_backups(self, keep_count: int = 10):
        """Remove old backup directories, keeping only the most recent ones."""
        if not self.previous_data_dir.exists():
            return

        backup_dirs = sorted([d for d in self.previous_data_dir.iterdir() if d.is_dir()])

        if len(backup_dirs) > keep_count:
            for old_dir in backup_dirs[:-keep_count]:
                shutil.rmtree(old_dir)
                print(f"[*] Removed old backup: {old_dir.name}")

    async def scrape_incremental(self, scrape_game_details: bool = False,
                                 scrape_stats: bool = False,
                                 scrape_standings: bool = False,
                                 force_full: bool = False) -> ScrapeMetadata:
        """Perform incremental scrape and merge with existing data.

        Args:
            scrape_game_details: Whether to scrape individual game details
            scrape_stats: Whether to scrape player statistics
            scrape_standings: Whether to scrape team standings
            force_full: Force full scrape of all dates instead of incremental
        """
        print("[*] Starting incremental SSC Hockey scrape")

        # Load previous data
        prev_metadata = self.load_previous_metadata()
        prev_games = self.load_previous_games()

        if prev_metadata:
            print(f"[*] Previous scrape: {prev_metadata.timestamp}")
            print(f"    - {prev_metadata.total_games} games")
            print(f"    - {prev_metadata.total_player_stats} player stats")
            print(f"    - {prev_metadata.total_standings} standings")
        else:
            print("[*] No previous scrape found - performing full scrape")
            force_full = True

        # Backup previous data
        self.backup_previous_data()

        # Run scraper (always scrape all dates to catch updates)
        scraper = SSCHockeyScraper(
            league_id=self.league_id,
            subseason_id=self.subseason_id,
            output_dir=self.output_dir / 'temp',
            headless=self.headless,
            all_dates=True,  # Always scrape all dates
            scrape_game_details=scrape_game_details,
            scrape_stats=scrape_stats,
            scrape_standings=scrape_standings
        )

        await scraper.scrape()

        # Load new data
        temp_schedules = self.output_dir / 'temp' / 'schedules.json'
        with open(temp_schedules, 'r') as f:
            new_games_data = json.load(f)
        new_games = [Game(**g) for g in new_games_data]

        # Merge and deduplicate
        print("\n[*] Merging data...")
        merged_games, new_count, updated_count = self.merge_and_deduplicate(new_games, prev_games)

        print(f"[✓] Merge complete:")
        print(f"    - {new_count} new games")
        print(f"    - {updated_count} updated games")
        print(f"    - {len(merged_games)} total games")

        # Save merged data
        schedules_file = self.output_dir / 'schedules.json'
        with open(schedules_file, 'w') as f:
            json.dump([asdict(g) for g in merged_games], f, indent=2)

        # Copy other files from temp
        for filename in ['teams.json', 'player_stats.json', 'standings.json']:
            src = self.output_dir / 'temp' / filename
            dst = self.output_dir / filename
            if src.exists():
                shutil.copy2(src, dst)

        # Clean up temp directory
        shutil.rmtree(self.output_dir / 'temp')

        # Generate change report
        prev_total = prev_metadata.total_games if prev_metadata else 0
        change_report = self.generate_change_report(
            new_count, updated_count, len(merged_games), prev_total,
            len(scraper.player_stats), len(scraper.standings)
        )

        # Save change report
        report_file = self.output_dir / 'change_report.json'
        with open(report_file, 'w') as f:
            json.dump(change_report, f, indent=2)

        print(f"\n[✓] Change report saved to {report_file}")

        # Save metadata
        metadata = ScrapeMetadata(
            timestamp=datetime.now().isoformat(),
            league_id=self.league_id,
            subseason_id=self.subseason_id,
            total_games=len(merged_games),
            total_player_stats=len(scraper.player_stats),
            total_standings=len(scraper.standings),
            new_games=new_count,
            updated_games=updated_count,
            dates_scraped=[]  # Could track this if needed
        )

        with open(self.metadata_file, 'w') as f:
            json.dump(asdict(metadata), f, indent=2)

        return metadata


async def main():
    parser = argparse.ArgumentParser(
        description='Incremental SSC Hockey scraper for weekly updates'
    )
    parser.add_argument('--league-id', required=True, help='League instance ID (e.g., 224428)')
    parser.add_argument('--subseason-id', required=True, help='Subseason ID (e.g., 948564)')
    parser.add_argument('--out', default='data/weekly', help='Output directory')
    parser.add_argument('--headed', action='store_true', help='Run browser in headed mode')
    parser.add_argument('--scrape-game-details', action='store_true',
                       help='Scrape detailed game statistics')
    parser.add_argument('--scrape-stats', action='store_true', help='Scrape player statistics')
    parser.add_argument('--scrape-standings', action='store_true', help='Scrape team standings')
    parser.add_argument('--force-full', action='store_true',
                       help='Force full scrape instead of incremental')

    args = parser.parse_args()

    scraper = IncrementalSSCScraper(
        league_id=args.league_id,
        subseason_id=args.subseason_id,
        output_dir=Path(args.out),
        headless=not args.headed
    )

    metadata = await scraper.scrape_incremental(
        scrape_game_details=args.scrape_game_details,
        scrape_stats=args.scrape_stats,
        scrape_standings=args.scrape_standings,
        force_full=args.force_full
    )

    print("\n" + "="*60)
    print("SCRAPE COMPLETE")
    print("="*60)
    print(f"Timestamp: {metadata.timestamp}")
    print(f"Total Games: {metadata.total_games}")
    print(f"New Games: {metadata.new_games}")
    print(f"Updated Games: {metadata.updated_games}")
    print(f"Player Stats: {metadata.total_player_stats}")
    print(f"Standings: {metadata.total_standings}")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
