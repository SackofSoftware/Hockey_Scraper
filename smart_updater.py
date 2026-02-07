#!/usr/bin/env python3
"""
Smart Hockey Stats Updater - Time-Aware Game Day Updates

Updates databases based on current time and game schedule:
- More frequent updates on game days (Fri PM, Sat, Sun)
- Differentiates between scheduled vs completed games
- Only fetches box scores for completed games
- Tracks game status changes
"""

import os
import sys
import logging
import sqlite3
import subprocess
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from advanced_stats_database import AdvancedStatsDatabase
from data_importer import DataImporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmartUpdater:
    """
    Intelligent updater that knows when to fetch data based on game schedules.
    """

    def __init__(self, db_path: str, season_id: str, league_name: str):
        self.db_path = db_path
        self.season_id = season_id
        self.league_name = league_name
        self.db = AdvancedStatsDatabase(db_path)
        self.db.connect()  # Connect to database

    def get_current_schedule_info(self) -> Dict:
        """
        Get information about current schedule and game states.

        Returns:
            Dict with schedule stats
        """
        cursor = self.db.conn.cursor()

        # Count games by status
        cursor.execute('''
            SELECT
                COUNT(*) as total_games,
                SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status IN ('scheduled', 'pending') THEN 1 ELSE 0 END) as scheduled,
                SUM(CASE WHEN date(date) = date('now') THEN 1 ELSE 0 END) as today,
                SUM(CASE WHEN date(date) = date('now', '+1 day') THEN 1 ELSE 0 END) as tomorrow
            FROM games
            WHERE season_id = ?
        ''', (self.season_id,))

        row = cursor.fetchone()

        return {
            'total_games': row[0] or 0,
            'completed': row[1] or 0,
            'scheduled': row[2] or 0,
            'today': row[3] or 0,
            'tomorrow': row[4] or 0,
            'pending_completion': (row[0] or 0) - (row[1] or 0)
        }

    def is_game_day(self, dt: datetime = None) -> Tuple[bool, str]:
        """
        Check if current time is during typical game days/times.

        Returns:
            (is_game_day, reason)
        """
        if dt is None:
            dt = datetime.now()

        day_of_week = dt.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
        current_time = dt.time()

        # Friday evening (after 5 PM)
        if day_of_week == 4 and current_time >= time(17, 0):
            return True, "Friday evening (games start after 5 PM)"

        # All day Saturday
        if day_of_week == 5:
            return True, "Saturday (full day of games)"

        # All day Sunday
        if day_of_week == 6:
            return True, "Sunday (full day of games)"

        # Weekday evening (occasional weekday games, 6-9 PM)
        if day_of_week in [0, 1, 2, 3] and time(18, 0) <= current_time <= time(21, 0):
            return True, f"Weekday evening ({dt.strftime('%A')} 6-9 PM)"

        return False, f"Off time ({dt.strftime('%A %I:%M %p')})"

    def get_update_interval(self, dt: datetime = None) -> Tuple[int, str]:
        """
        Determine appropriate update interval based on current time.

        Returns:
            (minutes, reason)
        """
        if dt is None:
            dt = datetime.now()

        is_game_day, reason = self.is_game_day(dt)

        if is_game_day:
            # During game days: update every 15 minutes
            return 15, f"Game day active: {reason}"
        else:
            # Off times: update every 4 hours
            return 240, f"Off time: {reason}"

    def get_games_needing_update(self) -> List[str]:
        """
        Get list of game IDs that need box score updates.

        Only returns games that:
        1. Are marked as complete in schedule
        2. Don't have box score data yet
        3. Or were recently completed (within last 2 hours)
        """
        cursor = self.db.conn.cursor()

        # Find games that are complete but missing box score data
        cursor.execute('''
            SELECT g.game_id
            FROM games g
            WHERE g.status = 'complete'
              AND g.season_id = ?
              AND NOT EXISTS (
                  SELECT 1 FROM goals WHERE game_id = g.game_id
              )
            ORDER BY g.date DESC, g.time DESC
        ''', (self.season_id,))

        games_to_update = [row[0] for row in cursor.fetchall()]

        logger.info(f"Found {len(games_to_update)} games needing box score updates")
        return games_to_update

    def update_schedule(self) -> int:
        """
        Update game schedule (adds new games, updates game status).

        Returns:
            Number of games updated
        """
        logger.info(f"Updating schedule for {self.league_name} (Season {self.season_id})")

        importer = DataImporter(self.db, self.season_id)

        # Re-import schedule (updates game status)
        # This is lightweight - just fetches schedule JSON
        games_before = self.get_current_schedule_info()

        # Import schedule for all divisions
        importer._import_schedule()

        games_after = self.get_current_schedule_info()

        new_games = games_after['total_games'] - games_before['total_games']
        status_changes = abs(games_after['completed'] - games_before['completed'])

        logger.info(f"Schedule update: {new_games} new games, {status_changes} status changes")

        return new_games + status_changes

    def update_box_scores(self, game_ids: List[str] = None) -> int:
        """
        Update box scores for completed games.

        Args:
            game_ids: Specific games to update, or None for all incomplete

        Returns:
            Number of games updated
        """
        if game_ids is None:
            game_ids = self.get_games_needing_update()

        if not game_ids:
            logger.info("No games need box score updates")
            return 0

        logger.info(f"Updating box scores for {len(game_ids)} games")

        importer = DataImporter(self.db, self.season_id)

        updated_count = 0
        for i, game_id in enumerate(game_ids, 1):
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(game_ids)} ({i*100/len(game_ids):.1f}%)")

            success = importer._import_box_score(game_id)
            if success:
                updated_count += 1

        # Recalculate stats after updates
        if updated_count > 0:
            logger.info("Recalculating player and team statistics...")
            importer._calculate_basic_stats()

        logger.info(f"Updated {updated_count}/{len(game_ids)} box scores")
        return updated_count

    def sync_to_pc(self) -> bool:
        """
        Sync database to Windows PC via SSH.
        PC has Dropbox which will then sync to Mac.

        Returns:
            True if sync succeeded, False otherwise
        """
        try:
            logger.info("Syncing database to Windows PC...")

            # Run the sync script
            script_path = Path(__file__).parent / "sync_to_pc.sh"

            if not script_path.exists():
                logger.warning(f"Sync script not found: {script_path}")
                return False

            result = subprocess.run(
                ['bash', str(script_path)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info("✓ Database synced to PC successfully")
                logger.info("  Dropbox will sync to Mac automatically")
                return True
            else:
                logger.error(f"Sync failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Sync timed out after 60 seconds")
            return False
        except Exception as e:
            logger.error(f"Sync error: {e}")
            return False

    def smart_update(self) -> Dict:
        """
        Perform smart update based on current time and game schedule.

        Returns:
            Dict with update statistics
        """
        now = datetime.now()
        is_game_day, game_day_reason = self.is_game_day(now)
        update_interval, interval_reason = self.get_update_interval(now)

        logger.info("=" * 70)
        logger.info(f"SMART UPDATE - {self.league_name}")
        logger.info("=" * 70)
        logger.info(f"Current time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}")
        logger.info(f"Game day: {is_game_day} - {game_day_reason}")
        logger.info(f"Update interval: {update_interval} minutes - {interval_reason}")
        logger.info("=" * 70)

        # Get current state
        schedule_info = self.get_current_schedule_info()
        logger.info(f"Current state:")
        logger.info(f"  Total games: {schedule_info['total_games']}")
        logger.info(f"  Completed: {schedule_info['completed']}")
        logger.info(f"  Scheduled: {schedule_info['scheduled']}")
        logger.info(f"  Today: {schedule_info['today']}")
        logger.info(f"  Tomorrow: {schedule_info['tomorrow']}")
        logger.info("")

        # Always update schedule (lightweight)
        schedule_changes = self.update_schedule()

        # Update box scores for completed games
        box_scores_updated = self.update_box_scores()

        # Get final state
        final_info = self.get_current_schedule_info()

        # Note: Running directly on Windows PC, no sync needed
        # Databases are already in Dropbox folder which auto-syncs to Mac
        sync_success = True
        if schedule_changes > 0 or box_scores_updated > 0:
            logger.info("✓ Database updated in Dropbox folder (will auto-sync to Mac)")
        else:
            logger.info("No changes made")

        results = {
            'timestamp': now.isoformat(),
            'is_game_day': is_game_day,
            'update_interval_minutes': update_interval,
            'schedule_changes': schedule_changes,
            'box_scores_updated': box_scores_updated,
            'sync_success': sync_success,
            'games_total': final_info['total_games'],
            'games_completed': final_info['completed'],
            'games_scheduled': final_info['scheduled'],
            'games_today': final_info['today'],
            'games_tomorrow': final_info['tomorrow']
        }

        logger.info("=" * 70)
        logger.info("UPDATE COMPLETE")
        logger.info(f"  Schedule changes: {schedule_changes}")
        logger.info(f"  Box scores updated: {box_scores_updated}")
        logger.info(f"  Next update recommended: {update_interval} minutes")
        logger.info("=" * 70)

        return results

    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Main entry point for smart updater."""
    import argparse

    parser = argparse.ArgumentParser(description='Smart Hockey Stats Updater')
    parser.add_argument('--league', required=True, choices=['baystate', 'ehf', 'ssc'],
                       help='League to update')
    parser.add_argument('--db', help='Database path (optional, uses default for league)')
    parser.add_argument('--check-schedule', action='store_true',
                       help='Just check schedule and exit (no updates)')

    args = parser.parse_args()

    # Configure league settings
    leagues = {
        'baystate': {
            'name': 'Bay State Hockey League',
            'season_id': '10776',
            'db_path': 'hockey_stats.db'
        },
        'ehf': {
            'name': 'Eastern Hockey Federation',
            'season_id': '10477',
            'db_path': 'hockey_stats.db'
        },
        'ssc': {
            'name': 'South Shore Conference',
            'season_id': None,  # SportsEngine uses different system
            'db_path': None
        }
    }

    league_config = leagues[args.league]
    db_path = args.db or league_config['db_path']

    if not db_path:
        logger.error(f"No database configured for {args.league}")
        sys.exit(1)

    if not os.path.exists(db_path):
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    # Create updater
    updater = SmartUpdater(
        db_path=db_path,
        season_id=league_config['season_id'],
        league_name=league_config['name']
    )

    try:
        if args.check_schedule:
            # Just show schedule info
            now = datetime.now()
            is_game_day, reason = updater.is_game_day(now)
            interval, interval_reason = updater.get_update_interval(now)
            schedule_info = updater.get_current_schedule_info()

            print(f"\n{league_config['name']}")
            print("=" * 70)
            print(f"Current time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}")
            print(f"Game day: {is_game_day} - {reason}")
            print(f"Recommended update interval: {interval} minutes")
            print(f"\nSchedule status:")
            print(f"  Total games: {schedule_info['total_games']}")
            print(f"  Completed: {schedule_info['completed']}")
            print(f"  Scheduled: {schedule_info['scheduled']}")
            print(f"  Today: {schedule_info['today']}")
            print(f"  Tomorrow: {schedule_info['tomorrow']}")
            print(f"  Pending completion: {schedule_info['pending_completion']}")
            print("=" * 70)
        else:
            # Perform smart update
            results = updater.smart_update()

    finally:
        updater.close()


if __name__ == '__main__':
    main()
