#!/usr/bin/env python3
"""
Team Name Normalization Script

Adds normalized club/organization names to all tables in the database.
This allows grouping teams by their parent organization (e.g., all WHK teams, all Hingham teams)
"""

import sqlite3
import re
import logging
from pathlib import Path
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def extract_club_name(team_name: str) -> str:
    """
    Extract clean club/organization name from team name.

    Examples:
        "Canton - U10B (White)" -> "Canton"
        "Hingham-Red" -> "Hingham"
        "WHK Black" -> "WHK"
        "Duxbury U10 B1" -> "Duxbury"
        "HANOVER 1" -> "Hanover"
    """
    if not team_name:
        return ""

    # Start with original name
    club = team_name.strip()

    # Remove everything after hyphen
    if ' - ' in club:
        club = club.split(' - ')[0].strip()
    elif '-' in club and not club.startswith('U'):
        # "Hingham-Red" but not "U-14"
        club = club.split('-')[0].strip()

    # Remove parentheses content: "Team (White)" -> "Team"
    club = re.sub(r'\s*\([^)]*\)', '', club)

    # Remove age groups: "Duxbury U10 B1" -> "Duxbury"
    club = re.sub(r'\s+U\d+[ABC]?\d?', '', club, flags=re.IGNORECASE)

    # Remove "Girls" suffix: "Hingham Girls" -> "Hingham"
    club = re.sub(r'\s+Girls?$', '', club, flags=re.IGNORECASE)

    # Remove colors: "WHK Red", "Hingham Black"
    colors = ['Red', 'Blue', 'White', 'Black', 'Green', 'Gold', 'Silver', 'Gray', 'Grey', 'Orange', 'Purple']
    for color in colors:
        club = re.sub(rf'\s+{color}$', '', club, flags=re.IGNORECASE)

    # Remove single letter/number suffixes: "Hanover A", "Team 1"
    club = re.sub(r'\s+[A-Z]$', '', club)
    club = re.sub(r'\s+\d$', '', club)

    # Remove age level names
    age_levels = ['Squirt', 'Pee ?Wee', 'PeeWee', 'Bantam', 'Midget', 'Mite']
    for level in age_levels:
        club = re.sub(rf'\s+{level}.*$', '', club, flags=re.IGNORECASE)

    # Normalize case: "HANOVER" -> "Hanover"
    # But preserve known acronyms
    acronyms = ['WHK', 'SSC', 'NRI', 'KP', 'YD', 'CC', 'GU10', 'GU12']
    if club.upper() not in acronyms:
        club = club.title()
    else:
        club = club.upper()

    # Clean up extra spaces
    club = ' '.join(club.split())

    return club


def add_club_columns(db_path: str):
    """Add club_name columns to all relevant tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Map each column to its club equivalent
    column_mapping = {
        'team_name': 'club_name',
        'home_team_name': 'home_club',
        'visitor_team_name': 'visitor_club',
        'team': 'club'
    }

    tables_to_update = [
        ('teams', 'team_name'),
        ('games', 'home_team_name'),
        ('games', 'visitor_team_name'),
        ('goals', 'team_name'),
        ('penalties', 'team_name'),
        ('game_rosters', 'team_name'),
        ('team_stats', 'team_name'),
        ('player_stats', 'team')
    ]

    for table, column in tables_to_update:
        try:
            # Check if club column already exists
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]

            club_col = column_mapping.get(column, f"{column}_club")

            if club_col not in columns:
                logger.info(f"Adding {club_col} column to {table} table...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {club_col} TEXT")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not update {table}: {e}")

    conn.commit()
    conn.close()


def normalize_teams_table(db_path: str):
    """Normalize team names in teams table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("Normalizing teams table...")

    # Get all teams
    cursor.execute("SELECT team_id, team_name FROM teams")
    teams = cursor.fetchall()

    updates = []
    for team_id, team_name in teams:
        club_name = extract_club_name(team_name)
        updates.append((club_name, team_id))

    # Update teams
    cursor.executemany("UPDATE teams SET club_name = ? WHERE team_id = ?", updates)

    logger.info(f"Updated {len(updates)} teams")

    conn.commit()
    conn.close()


def normalize_games_table(db_path: str):
    """Normalize team names in games table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("Normalizing games table...")

    # Get all games
    cursor.execute("SELECT game_id, home_team_name, visitor_team_name FROM games")
    games = cursor.fetchall()

    updates = []
    for game_id, home_team, visitor_team in games:
        home_club = extract_club_name(home_team)
        visitor_club = extract_club_name(visitor_team)
        updates.append((home_club, visitor_club, game_id))

    # Update games
    cursor.executemany("""
        UPDATE games
        SET home_club = ?, visitor_club = ?
        WHERE game_id = ?
    """, updates)

    logger.info(f"Updated {len(updates)} games")

    conn.commit()
    conn.close()


def normalize_goals_table(db_path: str):
    """Normalize team names in goals table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("Normalizing goals table...")

    cursor.execute("SELECT id, team_name FROM goals")
    goals = cursor.fetchall()

    updates = []
    for goal_id, team_name in goals:
        club_name = extract_club_name(team_name)
        updates.append((club_name, goal_id))

    cursor.executemany("UPDATE goals SET club_name = ? WHERE id = ?", updates)

    logger.info(f"Updated {len(updates)} goals")

    conn.commit()
    conn.close()


def normalize_penalties_table(db_path: str):
    """Normalize team names in penalties table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("Normalizing penalties table...")

    cursor.execute("SELECT id, team_name FROM penalties")
    penalties = cursor.fetchall()

    updates = []
    for penalty_id, team_name in penalties:
        club_name = extract_club_name(team_name)
        updates.append((club_name, penalty_id))

    cursor.executemany("UPDATE penalties SET club_name = ? WHERE id = ?", updates)

    logger.info(f"Updated {len(updates)} penalties")

    conn.commit()
    conn.close()


def normalize_rosters_table(db_path: str):
    """Normalize team names in game_rosters table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("Normalizing game_rosters table...")

    cursor.execute("SELECT id, team_name FROM game_rosters")
    rosters = cursor.fetchall()

    updates = []
    for roster_id, team_name in rosters:
        club_name = extract_club_name(team_name)
        updates.append((club_name, roster_id))

    cursor.executemany("UPDATE game_rosters SET club_name = ? WHERE id = ?", updates)

    logger.info(f"Updated {len(updates)} roster entries")

    conn.commit()
    conn.close()


def normalize_stats_tables(db_path: str):
    """Normalize team names in stats tables using team_id joins."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Team stats - use JOIN to get club_name from teams table
    logger.info("Normalizing team_stats table...")
    cursor.execute("""
        UPDATE team_stats
        SET club_name = (
            SELECT t.club_name
            FROM teams t
            WHERE t.team_id = team_stats.team_id
        )
        WHERE EXISTS (
            SELECT 1 FROM teams t
            WHERE t.team_id = team_stats.team_id
        )
    """)
    logger.info(f"Updated {cursor.rowcount} team stats")

    # Player stats - use JOIN to get club_name from teams table
    logger.info("Normalizing player_stats table...")
    cursor.execute("""
        UPDATE player_stats
        SET club = (
            SELECT t.club_name
            FROM teams t
            WHERE t.team_id = player_stats.team_id
        )
        WHERE EXISTS (
            SELECT 1 FROM teams t
            WHERE t.team_id = player_stats.team_id
        )
    """)
    logger.info(f"Updated {cursor.rowcount} player stats")

    conn.commit()
    conn.close()


def create_indexes(db_path: str):
    """Create indexes on club columns for fast lookups."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("Creating indexes on club columns...")

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_teams_club ON teams(club_name)",
        "CREATE INDEX IF NOT EXISTS idx_games_home_club ON games(home_club)",
        "CREATE INDEX IF NOT EXISTS idx_games_visitor_club ON games(visitor_club)",
        "CREATE INDEX IF NOT EXISTS idx_goals_club ON goals(club_name)",
        "CREATE INDEX IF NOT EXISTS idx_penalties_club ON penalties(club_name)",
        "CREATE INDEX IF NOT EXISTS idx_rosters_club ON game_rosters(club_name)",
        "CREATE INDEX IF NOT EXISTS idx_team_stats_club ON team_stats(club_name)",
        "CREATE INDEX IF NOT EXISTS idx_player_stats_club ON player_stats(club)"
    ]

    for idx_sql in indexes:
        try:
            cursor.execute(idx_sql)
        except sqlite3.OperationalError as e:
            logger.warning(f"Index creation: {e}")

    conn.commit()
    conn.close()

    logger.info("Indexes created")


def show_club_stats(db_path: str):
    """Show statistics about clubs/organizations."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "=" * 70)
    print("CLUB/ORGANIZATION STATISTICS")
    print("=" * 70)

    # Count teams per club
    cursor.execute("""
        SELECT club_name, COUNT(*) as team_count
        FROM teams
        WHERE club_name IS NOT NULL AND club_name != ''
        GROUP BY club_name
        ORDER BY team_count DESC, club_name
        LIMIT 30
    """)

    print("\nTop 30 Clubs by Team Count:")
    print("-" * 70)
    print(f"{'Club Name':<30} {'Teams':>10}")
    print("-" * 70)
    for club, count in cursor.fetchall():
        print(f"{club:<30} {count:>10}")

    # Show example teams for specific clubs
    print("\n" + "=" * 70)
    print("EXAMPLE: WHK Teams")
    print("=" * 70)
    cursor.execute("""
        SELECT team_name, club_name
        FROM teams
        WHERE club_name = 'WHK'
        ORDER BY team_name
    """)
    for team_name, club_name in cursor.fetchall():
        print(f"  {team_name} → {club_name}")

    print("\n" + "=" * 70)
    print("EXAMPLE: Hingham Teams")
    print("=" * 70)
    cursor.execute("""
        SELECT team_name, club_name
        FROM teams
        WHERE club_name = 'Hingham'
        ORDER BY team_name
    """)
    for team_name, club_name in cursor.fetchall():
        print(f"  {team_name} → {club_name}")

    print("\n" + "=" * 70)
    print("EXAMPLE: Canton Teams")
    print("=" * 70)
    cursor.execute("""
        SELECT team_name, club_name
        FROM teams
        WHERE club_name = 'Canton'
        ORDER BY team_name
    """)
    for team_name, club_name in cursor.fetchall():
        print(f"  {team_name} → {club_name}")

    conn.close()


def main():
    """Main normalization process."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python normalize_team_names.py <database_path>")
        print("\nExample:")
        print('  python normalize_team_names.py advanced_hockey_stats_full.db')
        sys.exit(1)

    db_path = sys.argv[1]

    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    logger.info(f"Normalizing team names in: {db_path}")
    logger.info("=" * 70)

    # Step 1: Add club columns
    add_club_columns(db_path)

    # Step 2: Normalize each table
    normalize_teams_table(db_path)
    normalize_games_table(db_path)
    normalize_goals_table(db_path)
    normalize_penalties_table(db_path)
    normalize_rosters_table(db_path)
    normalize_stats_tables(db_path)

    # Step 3: Create indexes
    create_indexes(db_path)

    # Step 4: Show results
    show_club_stats(db_path)

    logger.info("=" * 70)
    logger.info("Normalization complete!")
    logger.info(f"Database updated: {db_path}")
    logger.info("\nYou can now query by club name:")
    logger.info("  SELECT * FROM teams WHERE club_name = 'WHK'")
    logger.info("  SELECT * FROM goals WHERE club_name = 'Hingham'")
    logger.info("  SELECT * FROM games WHERE home_club = 'Canton' OR visitor_club = 'Canton'")


if __name__ == '__main__':
    main()
