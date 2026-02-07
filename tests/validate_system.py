#!/usr/bin/env python3
"""
System Validation Script
Verifies the complete hockey stats pipeline is working correctly
"""

import sqlite3
import sys
from pathlib import Path

def validate_database(db_path: str) -> dict:
    """
    Validate database has all required data
    Returns dict with validation results
    """
    results = {
        'success': True,
        'errors': [],
        'warnings': [],
        'stats': {}
    }

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check all required tables exist
        required_tables = [
            'games', 'goals', 'penalties', 'game_rosters',
            'teams', 'divisions', 'team_stats', 'player_stats',
            'strength_of_schedule', 'head_to_head', 'player_game_log',
            'data_quality_issues'
        ]

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}

        for table in required_tables:
            if table not in existing_tables:
                results['errors'].append(f"Missing required table: {table}")
                results['success'] = False

        # Get record counts
        for table in required_tables:
            if table in existing_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                results['stats'][table] = count

                if count == 0 and table in ['games', 'teams', 'divisions']:
                    results['warnings'].append(f"Table {table} is empty")

        # Validate data integrity
        # 1. All games should have corresponding team records
        cursor.execute("""
            SELECT COUNT(*) FROM games
            WHERE home_team_id NOT IN (SELECT team_id FROM teams)
               OR visitor_team_id NOT IN (SELECT team_id FROM teams)
        """)
        orphaned_games = cursor.fetchone()[0]
        if orphaned_games > 0:
            results['warnings'].append(f"{orphaned_games} games reference non-existent teams")

        # 2. All goals should reference valid games
        cursor.execute("""
            SELECT COUNT(*) FROM goals
            WHERE game_id NOT IN (SELECT game_id FROM games)
        """)
        orphaned_goals = cursor.fetchone()[0]
        if orphaned_goals > 0:
            results['warnings'].append(f"{orphaned_goals} goals reference non-existent games")

        # 3. Team stats should exist for teams with games
        cursor.execute("""
            SELECT COUNT(DISTINCT t.team_id)
            FROM teams t
            JOIN games g ON (g.home_team_id = t.team_id OR g.visitor_team_id = t.team_id)
            WHERE t.team_id NOT IN (SELECT team_id FROM team_stats)
        """)
        teams_without_stats = cursor.fetchone()[0]
        if teams_without_stats > 0:
            results['warnings'].append(f"{teams_without_stats} teams missing stats")

        # Get sample data for verification
        cursor.execute("""
            SELECT t.team_name, ts.games_played, ts.wins, ts.losses, ts.ties,
                   ts.goals_for, ts.goals_against, ts.points_pct
            FROM team_stats ts
            JOIN teams t ON ts.team_id = t.team_id
            ORDER BY ts.points_pct DESC
            LIMIT 5
        """)
        results['top_teams'] = cursor.fetchall()

        conn.close()

    except Exception as e:
        results['success'] = False
        results['errors'].append(f"Database error: {e}")

    return results


def print_validation_report(results: dict):
    """Print formatted validation report"""
    print("\n" + "=" * 80)
    print("SYSTEM VALIDATION REPORT")
    print("=" * 80)

    # Overall status
    if results['success'] and not results['errors']:
        print("\n✅ VALIDATION PASSED")
    else:
        print("\n❌ VALIDATION FAILED")

    # Errors
    if results['errors']:
        print("\nERRORS:")
        for error in results['errors']:
            print(f"  ❌ {error}")

    # Warnings
    if results['warnings']:
        print("\nWARNINGS:")
        for warning in results['warnings']:
            print(f"  ⚠️  {warning}")

    # Database stats
    print("\nDATABASE STATISTICS:")
    print("-" * 80)
    for table, count in sorted(results['stats'].items()):
        print(f"  {table:30s} {count:>10,d} records")

    # Sample data
    if results.get('top_teams'):
        print("\nTOP 5 TEAMS BY POINTS %:")
        print("-" * 80)
        print(f"{'Team':<30s} {'GP':>4s} {'W':>3s} {'L':>3s} {'T':>3s} {'GF':>4s} {'GA':>4s} {'Pts%':>6s}")
        print("-" * 80)
        for team_name, gp, w, l, t, gf, ga, pts_pct in results['top_teams']:
            print(f"{team_name:<30s} {gp:>4d} {w:>3d} {l:>3d} {t:>3d} {gf:>4d} {ga:>4d} {pts_pct:>6.1f}")

    print("\n" + "=" * 80)


def main():
    db_path = "hockey_stats_10776.db"

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        print("Run full_pipeline.py first to create the database")
        return 1

    print(f"Validating database: {db_path}")
    results = validate_database(db_path)
    print_validation_report(results)

    return 0 if results['success'] else 1


if __name__ == "__main__":
    sys.exit(main())
