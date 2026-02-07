#!/usr/bin/env python3
"""
Quick Test Script for Stats Calculator

Tests both basic and advanced stats calculation on a sample database.
"""

import sqlite3
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stats_calculator import AdvancedStatsCalculator
from advanced_metrics import AdvancedMetricsCalculator


def test_database(db_path: str, season_id: str = "10776"):
    """Run a quick test of the stats calculator"""

    print("=" * 80)
    print("STATS CALCULATOR TEST")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Season ID: {season_id}")
    print()

    # Check database exists
    if not os.path.exists(db_path):
        print(f"❌ ERROR: Database not found: {db_path}")
        return False

    # Check database has data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Detect schema
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    print("📊 Database Schema Detected:")
    print(f"   Tables found: {', '.join(sorted(tables))}")

    has_enhanced = 'game_entities' in tables
    has_original = 'all_games' in tables or 'games' in tables

    if has_enhanced:
        print("   ✅ Enhanced entity schema detected")
        cursor.execute("SELECT COUNT(*) FROM team_entities")
        team_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM player_entities")
        player_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM game_entities")
        game_count = cursor.fetchone()[0]
    elif has_original:
        print("   ✅ Original schema detected")
        cursor.execute("SELECT COUNT(*) FROM teams")
        team_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM players") if 'players' in tables else (0,)
        player_count = cursor.fetchone()[0] if 'players' in tables else 0
        cursor.execute("SELECT COUNT(*) FROM games") if 'games' in tables else cursor.execute("SELECT COUNT(*) FROM all_games")
        game_count = cursor.fetchone()[0]
    else:
        print("   ❌ Unknown schema - no recognized tables")
        conn.close()
        return False

    print(f"   Teams: {team_count}")
    print(f"   Players: {player_count}")
    print(f"   Games: {game_count}")

    conn.close()

    if team_count == 0 or game_count == 0:
        print("\n❌ ERROR: No data in database")
        return False

    print("\n" + "=" * 80)
    print("RUNNING BASIC STATS CALCULATION")
    print("=" * 80)

    try:
        calc = AdvancedStatsCalculator(db_path)
        calc.calculate_all_stats(season_id)
        print("✅ Basic stats calculation complete!")
    except Exception as e:
        print(f"❌ ERROR during basic stats calculation: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("RUNNING ADVANCED METRICS CALCULATION")
    print("=" * 80)

    try:
        metrics = AdvancedMetricsCalculator(db_path)
        metrics.calculate_all_advanced_metrics(season_id)
        print("✅ Advanced metrics calculation complete!")
    except Exception as e:
        print(f"❌ ERROR during advanced metrics calculation: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify results
    print("\n" + "=" * 80)
    print("VERIFYING RESULTS")
    print("=" * 80)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check player_stats
    cursor.execute("SELECT COUNT(*) FROM player_stats WHERE season_id = ?", (season_id,))
    player_stats_count = cursor.fetchone()[0]
    print(f"✅ Player stats records: {player_stats_count}")

    # Check team_stats
    cursor.execute("SELECT COUNT(*) FROM team_stats WHERE season_id = ?", (season_id,))
    team_stats_count = cursor.fetchone()[0]
    print(f"✅ Team stats records: {team_stats_count}")

    # Check SOS
    cursor.execute("SELECT COUNT(*) FROM strength_of_schedule WHERE season_id = ?", (season_id,))
    sos_count = cursor.fetchone()[0]
    print(f"✅ SOS records: {sos_count}")

    # Check H2H
    cursor.execute("SELECT COUNT(*) FROM head_to_head WHERE season_id = ?", (season_id,))
    h2h_count = cursor.fetchone()[0]
    print(f"✅ Head-to-head records: {h2h_count}")

    # Sample top scorer
    cursor.execute("""
        SELECT player_number, team_id, goals, assists, points
        FROM player_stats
        WHERE season_id = ?
        ORDER BY points DESC
        LIMIT 1
    """, (season_id,))

    top_scorer = cursor.fetchone()
    if top_scorer:
        print(f"\n🏆 Top Scorer: #{top_scorer[0]} ({top_scorer[1]}) - {top_scorer[4]} PTS ({top_scorer[2]}G, {top_scorer[3]}A)")

    # Sample top team
    cursor.execute("""
        SELECT team_id, wins, losses, ties, points_pct
        FROM team_stats
        WHERE season_id = ?
        ORDER BY points_pct DESC
        LIMIT 1
    """, (season_id,))

    top_team = cursor.fetchone()
    if top_team:
        print(f"🥇 Top Team: {top_team[0]} - {top_team[1]}-{top_team[2]}-{top_team[3]} ({top_team[4]:.3f} PTS%)")

    conn.close()

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    # Default to a known good database
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Try to find an enhanced entity database
        import glob
        pattern = "hockey_scraper_repo/output/enhanced_entities*.db"
        dbs = glob.glob(pattern)
        if dbs:
            db_path = sorted(dbs)[-1]  # Use most recent
            print(f"Using default database: {db_path}\n")
        else:
            print("Usage: python3 test_stats_calculator.py <database_path> [season_id]")
            print("\nNo default database found. Please specify path.")
            sys.exit(1)

    season_id = sys.argv[2] if len(sys.argv) > 2 else "10776"

    success = test_database(db_path, season_id)
    sys.exit(0 if success else 1)
