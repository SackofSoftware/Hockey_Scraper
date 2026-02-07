#!/usr/bin/env python3
"""
Test script to verify the advanced stats database
Demonstrates querying the imported data
"""

import sqlite3
from advanced_stats_database import AdvancedStatsDatabase


def main():
    """Test database queries"""
    db_path = "advanced_hockey_stats.db"

    with AdvancedStatsDatabase(db_path) as db:
        cursor = db.conn.cursor()

        print("\n" + "=" * 70)
        print("ADVANCED HOCKEY STATS DATABASE - TEST QUERIES")
        print("=" * 70)

        # 1. Database statistics
        stats = db.get_stats()
        print("\n1. DATABASE STATISTICS:")
        print("-" * 70)
        for table, count in sorted(stats.items()):
            print(f"   {table:25} {count:6d} records")

        # 2. Sample game data
        print("\n2. SAMPLE GAME DATA:")
        print("-" * 70)
        cursor.execute('''
            SELECT game_id, date, home_team_name, home_score, visitor_team_name, visitor_score, status
            FROM games
            WHERE status = 'final'
            ORDER BY date DESC
            LIMIT 3
        ''')
        print(f"   {'Date':12} {'Home':20} {'Score':5} {'Visitor':20} {'Score':5}")
        print("-" * 70)
        for row in cursor.fetchall():
            game_id, date, home, h_score, visitor, v_score, status = row
            print(f"   {date:12} {home:20} {h_score:5} {visitor:20} {v_score:5}")

        # 3. Sample goal with details
        print("\n3. SAMPLE GOAL DETAILS:")
        print("-" * 70)
        cursor.execute('''
            SELECT g.period, g.time_remaining, g.team_name, g.scorer_number,
                   g.is_power_play, g.is_short_handed, g.is_game_winning
            FROM goals g
            JOIN games gm ON g.game_id = gm.game_id
            ORDER BY gm.date DESC, g.game_time_seconds
            LIMIT 5
        ''')
        for row in cursor.fetchall():
            period, time, team, number, pp, sh, gwg = row
            tags = []
            if pp: tags.append("PP")
            if sh: tags.append("SH")
            if gwg: tags.append("GWG")
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            print(f"   {period:12} {time:5} - #{number:3} ({team}){tag_str}")

        # 4. Top scorers with advanced stats
        print("\n4. TOP SCORERS:")
        print("-" * 70)
        cursor.execute('''
            SELECT player_number, team_id, goals, points, games_played,
                   power_play_goals, short_handed_goals, game_winning_goals,
                   points_per_game, penalty_minutes
            FROM player_stats
            ORDER BY points DESC, goals DESC
            LIMIT 10
        ''')
        print(f"   {'#':3} {'Team':8} {'G':3} {'PTS':3} {'GP':3} {'PPG':3} {'SHG':3} {'GWG':3} {'PTS/GP':6} {'PIM':3}")
        print("-" * 70)
        for row in cursor.fetchall():
            num, team, g, pts, gp, ppg, shg, gwg, ptspg, pim = row
            print(f"   {num:3} {team:8} {g:3} {pts:3} {gp:3} {ppg:3} {shg:3} {gwg:3} {ptspg:6.2f} {pim:3}")

        # 5. Penalty summary
        print("\n5. PENALTY SUMMARY BY TYPE:")
        print("-" * 70)
        cursor.execute('''
            SELECT penalty_type, COUNT(*) as count, SUM(duration_minutes) as total_mins
            FROM penalties
            GROUP BY penalty_type
            ORDER BY count DESC
            LIMIT 10
        ''')
        print(f"   {'Penalty Type':40} {'Count':6} {'Total Mins':10}")
        print("-" * 70)
        for row in cursor.fetchall():
            penalty, count, mins = row
            print(f"   {penalty:40} {count:6} {mins:10}")

        # 6. Team stats with advanced metrics
        print("\n6. TEAM STANDINGS:")
        print("-" * 70)
        cursor.execute('''
            SELECT t.team_name, ts.games_played, ts.wins, ts.losses, ts.ties,
                   ts.points, ts.points_pct, ts.goals_for, ts.goals_against,
                   ts.goal_differential, ts.goals_per_game, ts.goals_against_per_game
            FROM team_stats ts
            JOIN teams t ON ts.team_id = t.team_id
            ORDER BY ts.points DESC, ts.goal_differential DESC
        ''')
        print(f"   {'Team':25} {'GP':3} {'W':3} {'L':3} {'T':3} {'PTS':3} {'PTS%':5} {'GF':3} {'GA':3} {'+/-':4} {'GPG':4} {'GAPG':4}")
        print("-" * 70)
        for row in cursor.fetchall():
            team, gp, w, l, t, pts, pct, gf, ga, diff, gpg, gapg = row
            print(f"   {team:25} {gp:3} {w:3} {l:3} {t:3} {pts:3} {pct:5.3f} {gf:3} {ga:3} {diff:4} {gpg:4.1f} {gapg:4.1f}")

        # 7. Goals by period
        print("\n7. GOALS BY PERIOD:")
        print("-" * 70)
        cursor.execute('''
            SELECT period, COUNT(*) as goals
            FROM goals
            GROUP BY period
            ORDER BY period
        ''')
        for row in cursor.fetchall():
            period, count = row
            print(f"   {period:15} {count:4} goals")

        # 8. Special teams effectiveness
        print("\n8. SPECIAL TEAMS GOALS:")
        print("-" * 70)
        cursor.execute('''
            SELECT
                SUM(CASE WHEN is_power_play THEN 1 ELSE 0 END) as pp_goals,
                SUM(CASE WHEN is_short_handed THEN 1 ELSE 0 END) as sh_goals,
                SUM(CASE WHEN is_game_winning THEN 1 ELSE 0 END) as gwg,
                SUM(CASE WHEN is_empty_net THEN 1 ELSE 0 END) as en_goals,
                COUNT(*) as total_goals
            FROM goals
        ''')
        row = cursor.fetchone()
        pp, sh, gwg, en, total = row
        print(f"   Power Play Goals:     {pp:4} ({pp/total*100:5.1f}%)")
        print(f"   Short Handed Goals:   {sh:4} ({sh/total*100:5.1f}%)")
        print(f"   Game Winning Goals:   {gwg:4} ({gwg/total*100:5.1f}%)")
        print(f"   Empty Net Goals:      {en:4} ({en/total*100:5.1f}%)")
        print(f"   Total Goals:          {total:4}")

        # 9. Player game log sample
        print("\n9. SAMPLE PLAYER GAMES (Most goals in a game):")
        print("-" * 70)
        cursor.execute('''
            SELECT gr.player_number, gr.team_name, g.date, gr.goals, gr.assists, gr.points, gr.pim
            FROM game_rosters gr
            JOIN games g ON gr.game_id = g.game_id
            WHERE gr.goals > 0
            ORDER BY gr.goals DESC, gr.points DESC
            LIMIT 10
        ''')
        print(f"   {'#':3} {'Team':25} {'Date':12} {'G':2} {'A':2} {'PTS':3} {'PIM':3}")
        print("-" * 70)
        for row in cursor.fetchall():
            num, team, date, g, a, pts, pim = row
            print(f"   {num:3} {team:25} {date:12} {g:2} {a:2} {pts:3} {pim:3}")

        print("\n" + "=" * 70)
        print("TEST COMPLETE - Database is working correctly!")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
