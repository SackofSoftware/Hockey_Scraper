#!/usr/bin/env python3
"""
Create a test database with sample hockey data to demonstrate quality analysis
"""

import sqlite3
import random
from datetime import datetime, timedelta

def create_test_database(db_path):
    """Create a test database with realistic hockey data and quality issues"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables based on advanced schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            season_id TEXT,
            division_id INTEGER,
            division_name TEXT,
            game_date DATE,
            time TEXT,
            location TEXT,
            status TEXT,
            home_team_id INTEGER,
            home_team_name TEXT,
            visitor_team_id INTEGER,
            visitor_team_name TEXT,
            home_score INTEGER,
            visitor_score INTEGER,
            extraction_timestamp TIMESTAMP,
            data_quality_score REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT REFERENCES games(game_id),
            period TEXT,
            period_number INTEGER,
            time_remaining TEXT,
            game_time_seconds INTEGER,
            team_id INTEGER,
            team_name TEXT,
            is_home_team BOOLEAN,
            scorer_player_id TEXT,
            scorer_number TEXT,
            scorer_name TEXT,
            scorer_total_goals INTEGER,
            assist1_player_id TEXT,
            assist1_number TEXT,
            assist1_name TEXT,
            assist2_player_id TEXT,
            assist2_number TEXT,
            assist2_name TEXT,
            is_power_play BOOLEAN,
            is_short_handed BOOLEAN,
            is_game_winning BOOLEAN,
            is_empty_net BOOLEAN,
            scorer_number_verified BOOLEAN DEFAULT FALSE,
            assist1_number_verified BOOLEAN DEFAULT FALSE,
            assist2_number_verified BOOLEAN DEFAULT FALSE,
            data_confidence REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS penalties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT REFERENCES games(game_id),
            period TEXT,
            period_number INTEGER,
            time_remaining TEXT,
            team_id INTEGER,
            team_name TEXT,
            is_home_team BOOLEAN,
            player_id TEXT,
            player_number TEXT,
            player_name TEXT,
            penalty_type TEXT,
            penalty_class TEXT,
            duration_minutes INTEGER,
            is_major BOOLEAN,
            player_number_verified BOOLEAN DEFAULT FALSE,
            data_confidence REAL
        )
    """)

    # Sample teams
    teams = [
        (386299, "Duxbury U12B", "U12B"),
        (386305, "WHK", "U12B"),
        (386310, "Canton", "U12B"),
        (386315, "Plymouth", "U12B")
    ]

    # Sample players with intentional quality issues
    players = [
        # Good quality players (consistent number, has name)
        ("p001", "3", "John Smith", 386299, "Duxbury U12B"),
        ("p002", "12", "Mike Johnson", 386299, "Duxbury U12B"),
        ("p003", "41", "Tom Wilson", 386299, "Duxbury U12B"),

        # Player with number inconsistency (wears #5 and #15)
        ("p004", "5", "Alex Brown", 386299, "Duxbury U12B"),  # Sometimes #5

        # Player with no name
        ("p005", "87", "", 386299, "Duxbury U12B"),

        # WHK Players
        ("p010", "71", "Dave Martin", 386305, "WHK"),
        ("p011", "97", "", 386305, "WHK"),  # No name
        ("p012", "23", "Steve Davis", 386305, "WHK"),

        # Player who will have suspiciously high stats
        ("p013", "99", "Super Scorer", 386305, "WHK"),

        # Canton players
        ("p020", "7", "Paul Anderson", 386310, "Canton"),
        ("p021", "19", "Chris Lee", 386310, "Canton"),
    ]

    # Create games
    games_data = []
    start_date = datetime(2025, 9, 7)

    for i in range(5):
        game_date = start_date + timedelta(days=i*7)
        game_id = f"game_{2416969 + i}"

        # Mix of complete and incomplete games
        if i == 0:
            # Complete game
            games_data.append((
                game_id, "10776", 123, "U12B",
                game_date.strftime("%Y-%m-%d"), "18:00", "Armstrong Arena", "final",
                386299, "Duxbury U12B", 386305, "WHK",
                7, 4, datetime.now().isoformat(), 0.95
            ))
        elif i == 1:
            # Game with missing score
            games_data.append((
                game_id, "10776", 123, "U12B",
                game_date.strftime("%Y-%m-%d"), "19:00", "Canton Ice House", "final",
                386299, "Duxbury U12B", 386310, "Canton",
                None, None, datetime.now().isoformat(), 0.3
            ))
        elif i == 2:
            # High scoring game
            games_data.append((
                game_id, "10776", 123, "U12B",
                game_date.strftime("%Y-%m-%d"), "20:00", "Plymouth Arena", "final",
                386305, "WHK", 386315, "Plymouth",
                12, 11, datetime.now().isoformat(), 0.7
            ))
        else:
            # Normal games
            games_data.append((
                game_id, "10776", 123, "U12B",
                game_date.strftime("%Y-%m-%d"), "18:30", "Duxbury Arena", "final",
                386299, "Duxbury U12B", 386310, "Canton",
                5, 3, datetime.now().isoformat(), 0.9
            ))

    cursor.executemany("""
        INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, games_data)

    # Create goals for first game (with quality issues)
    goals_data = [
        # Game 1: Duxbury vs WHK (7-4)
        # John Smith (#3) - 2 goals
        ("game_2416969", "1ST Period", 1, "11:08", 648, 386299, "Duxbury U12B", 1,
         "p001", "3", "John Smith", 1, "p002", "12", "Mike Johnson", None, None, None,
         0, 0, 0, 0, 1, 1, 0, 0.95),

        ("game_2416969", "2ND Period", 2, "08:30", 1290, 386299, "Duxbury U12B", 1,
         "p001", "3", "John Smith", 2, "p003", "41", "Tom Wilson", None, None, None,
         0, 0, 0, 0, 1, 1, 0, 0.95),

        # Alex Brown - appears with TWO different numbers (#5 and #15) - QUALITY ISSUE
        ("game_2416969", "1ST Period", 1, "05:22", 322, 386299, "Duxbury U12B", 1,
         "p004", "5", "Alex Brown", 1, None, None, None, None, None, None,
         0, 0, 0, 0, 1, 0, 0, 0.5),  # Wore #5 this time

        # Tom Wilson (#41) - 2 goals
        ("game_2416969", "2ND Period", 2, "14:15", 855, 386299, "Duxbury U12B", 1,
         "p003", "41", "Tom Wilson", 1, "p001", "3", "John Smith", None, None, None,
         1, 0, 0, 0, 1, 1, 0, 0.9),

        ("game_2416969", "3RD Period", 3, "06:45", 405, 386299, "Duxbury U12B", 1,
         "p003", "41", "Tom Wilson", 2, "p002", "12", "Mike Johnson", None, None, None,
         0, 0, 0, 0, 1, 1, 0, 0.9),

        # Player with no name (#87) - QUALITY ISSUE
        ("game_2416969", "2ND Period", 2, "03:12", 192, 386299, "Duxbury U12B", 1,
         "p005", "87", "", 1, None, None, None, None, None, None,
         0, 0, 0, 0, 1, 0, 0, 0.6),

        # Mike Johnson (#12)
        ("game_2416969", "3RD Period", 3, "12:00", 720, 386299, "Duxbury U12B", 1,
         "p002", "12", "Mike Johnson", 1, "p001", "3", "John Smith", "p003", "41", "Tom Wilson",
         0, 0, 1, 0, 1, 1, 1, 0.95),

        # WHK Goals
        ("game_2416969", "1ST Period", 1, "09:15", 555, 386305, "WHK", 0,
         "p010", "71", "Dave Martin", 1, None, None, None, None, None, None,
         0, 0, 0, 0, 1, 0, 0, 0.85),

        ("game_2416969", "2ND Period", 2, "11:20", 680, 386305, "WHK", 0,
         "p010", "71", "Dave Martin", 2, "p011", "97", "", None, None, None,
         0, 0, 0, 0, 1, 1, 0, 0.7),

        ("game_2416969", "2ND Period", 2, "02:05", 125, 386305, "WHK", 0,
         "p010", "71", "Dave Martin", 3, None, None, None, None, None, None,
         0, 1, 0, 0, 1, 0, 0, 0.85),

        ("game_2416969", "3RD Period", 3, "08:40", 520, 386305, "WHK", 0,
         "p011", "97", "", 1, None, None, None, None, None, None,
         0, 0, 0, 0, 1, 0, 0, 0.6),
    ]

    cursor.executemany("""
        INSERT INTO goals VALUES (
            NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, goals_data)

    # Add MORE goals for game 3 (p004 wearing different number)
    more_goals = [
        # Game 3: Alex Brown now appears with #15 instead of #5 - INCONSISTENCY
        ("game_2416971", "1ST Period", 1, "10:00", 600, 386305, "WHK", 1,
         "p004", "15", "Alex Brown", 2, None, None, None, None, None, None,
         0, 0, 0, 0, 1, 0, 0, 0.5),  # Same player, different number!
    ]

    cursor.executemany("""
        INSERT INTO goals VALUES (
            NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, more_goals)

    # Add penalties
    penalties_data = [
        ("game_2416969", "2ND Period", 2, "07:41", 386299, "Duxbury U12B", 1,
         "p001", "3", "John Smith", "Roughing - Minor", "minor", 2, 0, 1, 0.9),

        ("game_2416969", "3RD Period", 3, "04:22", 386305, "WHK", 0,
         "p010", "71", "Dave Martin", "Slashing - Minor", "minor", 2, 0, 1, 0.9),

        # High PIM player
        ("game_2416969", "1ST Period", 1, "15:00", 386305, "WHK", 0,
         "p013", "99", "Super Scorer", "Fighting - Major", "major", 5, 1, 1, 0.8),
    ]

    cursor.executemany("""
        INSERT INTO penalties VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, penalties_data)

    # Add suspiciously high stats for Super Scorer (#99) by adding many goals
    # This simulates data duplication issue
    super_scorer_goals = []
    for i in range(50):  # 50 goals in one game - SUSPICIOUS!
        super_scorer_goals.append((
            "game_2416971", "2ND Period", 2, f"{i%15}:30", 900-i*10, 386305, "WHK", 1,
            "p013", "99", "Super Scorer", i+1, None, None, None, None, None, None,
            0, 0, 0, 0, 1, 0, 0, 0.3
        ))

    cursor.executemany("""
        INSERT INTO goals VALUES (
            NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, super_scorer_goals)

    conn.commit()
    conn.close()

    print(f"✅ Test database created: {db_path}")
    print(f"   - 5 games")
    print(f"   - 62 goals (including quality issues)")
    print(f"   - 3 penalties")
    print(f"\nQuality issues intentionally included:")
    print(f"   ✓ Player wearing multiple numbers (#5 and #15)")
    print(f"   ✓ Players with missing names")
    print(f"   ✓ Game with missing scores")
    print(f"   ✓ Suspiciously high scoring (50 goals by one player)")
    print(f"   ✓ High scoring game (12-11)")

if __name__ == "__main__":
    create_test_database("test_hockey_data.db")
