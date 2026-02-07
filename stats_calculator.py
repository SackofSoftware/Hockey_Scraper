#!/usr/bin/env python3
"""
Advanced Stats Calculator
Calculates basic and advanced statistics from raw game data.

This module handles:
- Player basic stats (G, A, PTS, PIM, PPG, SHG, GWG)
- Team stats (W-L-T, GF-GA, PP%, PK%, goal differential)
- Goals/penalties by period
- Home/away splits
- Special teams stats

Usage:
    calculator = AdvancedStatsCalculator("path/to/database.db")
    calculator.calculate_all_stats(season_id="10776")
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdvancedStatsCalculator:
    """Calculate all statistics from raw game data"""

    def __init__(self, db_path: str):
        """
        Initialize calculator with database path

        Args:
            db_path: Path to SQLite database containing game data
        """
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        """Context manager entry"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.conn:
            self.conn.close()

    def calculate_all_stats(self, season_id: str) -> None:
        """
        Run complete calculation pipeline

        Args:
            season_id: Season ID to calculate stats for (e.g., "10776")
        """
        logger.info(f"Starting stats calculation for season {season_id}")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 1. Create stats tables if they don't exist
            self._create_stats_tables(cursor)

            # 2. Basic aggregations
            logger.info("Calculating player basic stats...")
            self.calculate_player_basic_stats(cursor, season_id)

            logger.info("Calculating team basic stats...")
            self.calculate_team_basic_stats(cursor, season_id)

            # 3. Period breakdowns
            logger.info("Calculating goals by period...")
            self.calculate_goals_by_period(cursor, season_id)

            # 4. Special teams
            logger.info("Calculating power play stats...")
            self.calculate_power_play_stats(cursor, season_id)

            logger.info("Calculating penalty kill stats...")
            self.calculate_penalty_kill_stats(cursor, season_id)

            # 5. Home/away splits
            logger.info("Calculating home/away splits...")
            self.calculate_home_away_splits(cursor, season_id)

            conn.commit()

        logger.info("Stats calculation complete!")

    def _create_stats_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create player_stats and team_stats tables if they don't exist"""

        # Player stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_stats (
                player_id TEXT,
                team_id INTEGER,
                season_id TEXT,

                -- Identity
                player_number TEXT,
                player_name TEXT,
                position TEXT,

                -- Games
                games_played INTEGER DEFAULT 0,
                games_started INTEGER DEFAULT 0,

                -- Scoring
                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                points_per_game REAL DEFAULT 0.0,

                -- Special teams
                power_play_goals INTEGER DEFAULT 0,
                power_play_assists INTEGER DEFAULT 0,
                power_play_points INTEGER DEFAULT 0,
                short_handed_goals INTEGER DEFAULT 0,
                short_handed_assists INTEGER DEFAULT 0,
                short_handed_points INTEGER DEFAULT 0,
                game_winning_goals INTEGER DEFAULT 0,
                empty_net_goals INTEGER DEFAULT 0,

                -- Discipline
                penalties INTEGER DEFAULT 0,
                penalty_minutes INTEGER DEFAULT 0,
                pim_per_game REAL DEFAULT 0.0,
                major_penalties INTEGER DEFAULT 0,
                game_misconducts INTEGER DEFAULT 0,

                -- Shooting (if available)
                shots_on_goal INTEGER DEFAULT 0,
                shooting_pct REAL DEFAULT 0.0,

                -- Advanced
                plus_minus INTEGER DEFAULT 0,

                -- Goalie stats
                games_started_goalie INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                goals_against INTEGER DEFAULT 0,
                save_pct REAL DEFAULT 0.0,
                goals_against_avg REAL DEFAULT 0.0,
                shutouts INTEGER DEFAULT 0,

                -- Data quality
                number_consistency_score REAL DEFAULT 1.0,
                total_number_variations INTEGER DEFAULT 1,
                confidence_score REAL DEFAULT 1.0,

                PRIMARY KEY (player_id, team_id, season_id)
            )
        ''')

        # Team stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_stats (
                team_id INTEGER,
                season_id TEXT,
                division_id INTEGER,

                -- Record
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                otw INTEGER DEFAULT 0,
                otl INTEGER DEFAULT 0,
                sow INTEGER DEFAULT 0,
                sol INTEGER DEFAULT 0,

                -- Points
                points INTEGER DEFAULT 0,
                points_pct REAL DEFAULT 0.0,
                row INTEGER DEFAULT 0,

                -- Standings position
                division_rank INTEGER,

                -- Scoring
                goals_for INTEGER DEFAULT 0,
                goals_against INTEGER DEFAULT 0,
                goal_differential INTEGER DEFAULT 0,
                goals_per_game REAL DEFAULT 0.0,
                goals_against_per_game REAL DEFAULT 0.0,

                -- By period
                goals_period_1 INTEGER DEFAULT 0,
                goals_period_2 INTEGER DEFAULT 0,
                goals_period_3 INTEGER DEFAULT 0,
                goals_overtime INTEGER DEFAULT 0,
                goals_allowed_period_1 INTEGER DEFAULT 0,
                goals_allowed_period_2 INTEGER DEFAULT 0,
                goals_allowed_period_3 INTEGER DEFAULT 0,
                goals_allowed_overtime INTEGER DEFAULT 0,

                -- Special teams
                power_play_goals INTEGER DEFAULT 0,
                power_play_opportunities INTEGER DEFAULT 0,
                power_play_pct REAL DEFAULT 0.0,
                power_play_goals_against INTEGER DEFAULT 0,
                times_shorthanded INTEGER DEFAULT 0,
                penalty_kill_pct REAL DEFAULT 0.0,
                short_handed_goals INTEGER DEFAULT 0,
                short_handed_goals_against INTEGER DEFAULT 0,

                -- Discipline
                penalty_minutes INTEGER DEFAULT 0,
                pim_per_game REAL DEFAULT 0.0,
                penalties_taken INTEGER DEFAULT 0,
                major_penalties INTEGER DEFAULT 0,

                -- Shooting (if available)
                shots_for INTEGER DEFAULT 0,
                shots_against INTEGER DEFAULT 0,
                shooting_pct REAL DEFAULT 0.0,
                save_pct REAL DEFAULT 0.0,
                pdo REAL DEFAULT 0.0,

                -- Recent form
                last_10_record TEXT,
                current_streak TEXT,

                -- Home/Away splits
                home_wins INTEGER DEFAULT 0,
                home_losses INTEGER DEFAULT 0,
                home_ties INTEGER DEFAULT 0,
                away_wins INTEGER DEFAULT 0,
                away_losses INTEGER DEFAULT 0,
                away_ties INTEGER DEFAULT 0,
                home_goals_for INTEGER DEFAULT 0,
                home_goals_against INTEGER DEFAULT 0,
                away_goals_for INTEGER DEFAULT 0,
                away_goals_against INTEGER DEFAULT 0,

                PRIMARY KEY (team_id, season_id)
            )
        ''')

        logger.info("Stats tables created/verified")

    def calculate_player_basic_stats(self, cursor: sqlite3.Cursor, season_id: str) -> None:
        """
        Calculate basic player statistics from goal and penalty events

        Aggregates:
        - Goals (scorer in goal_events or goal_details)
        - Assists (assist1/assist2 in goal_events or goal_details)
        - Points (goals + assists)
        - PPG, SHG, GWG (from goal flags)
        - Penalties and PIM
        """

        # Check which tables exist (support both schema versions)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        has_goal_events = 'goal_events' in tables
        has_goal_details = 'goals' in tables
        has_penalty_events = 'penalty_events' in tables
        has_penalty_details = 'penalties' in tables
        has_player_entities = 'player_entities' in tables
        has_player_statistics = 'player_statistics' in tables

        # Clear existing stats for this season
        cursor.execute("DELETE FROM player_stats WHERE season_id = ?", (season_id,))

        # Get all unique players
        players = []

        if has_player_entities:
            # Use enhanced entity schema
            cursor.execute("""
                SELECT DISTINCT player_entity_id, player_gamesheet_id, jersey_number,
                       team_entity_id, team_name, division_name
                FROM player_entities
                WHERE season_id = ?
            """, (season_id,))

            for row in cursor.fetchall():
                players.append({
                    'player_id': row[0],
                    'gamesheet_id': row[1],
                    'number': row[2],
                    'team_id': row[3],
                    'team_name': row[4],
                    'division': row[5]
                })

        elif has_player_statistics:
            # Use existing player_statistics table
            cursor.execute("""
                SELECT DISTINCT ps.player_id, ps.player_number, ps.team_name,
                       t.team_id, d.division_name
                FROM player_statistics ps
                LEFT JOIN teams t ON ps.team_name = t.team_name
                LEFT JOIN divisions d ON t.division_id = d.division_id
                JOIN games g ON (g.home_team_id = t.team_id OR g.visitor_team_id = t.team_id)
                WHERE g.season_id = ?
            """, (season_id,))

            for row in cursor.fetchall():
                players.append({
                    'player_id': row[0],
                    'gamesheet_id': row[0],
                    'number': row[1],
                    'team_name': row[2],
                    'team_id': row[3],
                    'division': row[4]
                })

        logger.info(f"Processing {len(players)} players...")

        # Calculate stats for each player
        for idx, player in enumerate(players):
            if idx % 50 == 0:
                logger.info(f"  Progress: {idx}/{len(players)} players")

            player_id = player['player_id']
            team_id = player['team_id']

            stats = {
                'goals': 0,
                'assists': 0,
                'pp_goals': 0,
                'sh_goals': 0,
                'gw_goals': 0,
                'en_goals': 0,
                'pp_assists': 0,
                'sh_assists': 0,
                'penalties': 0,
                'pim': 0,
                'major_penalties': 0,
                'games': set()
            }

            # Count goals
            if has_goal_events:
                # Enhanced entity schema
                cursor.execute("""
                    SELECT COUNT(*),
                           SUM(CASE WHEN power_play THEN 1 ELSE 0 END),
                           SUM(CASE WHEN short_handed THEN 1 ELSE 0 END),
                           SUM(CASE WHEN game_winning THEN 1 ELSE 0 END),
                           SUM(CASE WHEN empty_net THEN 1 ELSE 0 END)
                    FROM goal_events
                    WHERE scorer_player_id = ?
                """, (player_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    stats['goals'] = row[0]
                    stats['pp_goals'] = row[1] or 0
                    stats['sh_goals'] = row[2] or 0
                    stats['gw_goals'] = row[3] or 0
                    stats['en_goals'] = row[4] or 0

                # Count assists
                cursor.execute("""
                    SELECT COUNT(*),
                           SUM(CASE WHEN power_play THEN 1 ELSE 0 END),
                           SUM(CASE WHEN short_handed THEN 1 ELSE 0 END)
                    FROM goal_events
                    WHERE assist1_player_id = ? OR assist2_player_id = ?
                """, (player_id, player_id))
                row = cursor.fetchone()
                if row and row[0]:
                    stats['assists'] = row[0]
                    stats['pp_assists'] = row[1] or 0
                    stats['sh_assists'] = row[2] or 0

                # Get unique games
                cursor.execute("""
                    SELECT DISTINCT game_entity_id
                    FROM goal_events
                    WHERE scorer_player_id = ? OR assist1_player_id = ? OR assist2_player_id = ?
                """, (player_id, player_id, player_id))
                stats['games'].update(row[0] for row in cursor.fetchall())

            elif has_goal_details:
                # Original schema
                # Match by player number and team
                cursor.execute("""
                    SELECT COUNT(*),
                           SUM(CASE WHEN gd.is_power_play THEN 1 ELSE 0 END),
                           SUM(CASE WHEN gd.is_short_handed THEN 1 ELSE 0 END),
                           SUM(CASE WHEN gd.is_game_winning THEN 1 ELSE 0 END),
                           SUM(CASE WHEN gd.is_empty_net THEN 1 ELSE 0 END)
                    FROM goals gd
                    JOIN games ag ON gd.game_id = ag.game_id
                    WHERE (gd.scorer_player_id = ? OR gd.scorer_number = ?)
                      AND gd.team_name = ?
                      AND ag.season_id = ?
                """, (player['gamesheet_id'], player['number'], player['team_name'], season_id))
                row = cursor.fetchone()
                if row and row[0]:
                    stats['goals'] = row[0]
                    stats['pp_goals'] = row[1] or 0
                    stats['sh_goals'] = row[2] or 0
                    stats['gw_goals'] = row[3] or 0
                    stats['en_goals'] = row[4] or 0

                # Count assists
                cursor.execute("""
                    SELECT COUNT(*),
                           SUM(CASE WHEN gd.is_power_play THEN 1 ELSE 0 END),
                           SUM(CASE WHEN gd.is_short_handed THEN 1 ELSE 0 END)
                    FROM goals gd
                    JOIN games ag ON gd.game_id = ag.game_id
                    WHERE ((gd.assist1_player_id = ? OR gd.assist1_number = ?)
                       OR (gd.assist2_player_id = ? OR gd.assist2_number = ?))
                      AND gd.team_name = ?
                      AND ag.season_id = ?
                """, (player['gamesheet_id'], player['number'],
                      player['gamesheet_id'], player['number'],
                      player['team_name'], season_id))
                row = cursor.fetchone()
                if row and row[0]:
                    stats['assists'] = row[0]
                    stats['pp_assists'] = row[1] or 0
                    stats['sh_assists'] = row[2] or 0

                # Get unique games
                cursor.execute("""
                    SELECT DISTINCT gd.game_id
                    FROM goals gd
                    JOIN games ag ON gd.game_id = ag.game_id
                    WHERE ((gd.scorer_player_id = ? OR gd.scorer_number = ?)
                       OR (gd.assist1_player_id = ? OR gd.assist1_number = ?)
                       OR (gd.assist2_player_id = ? OR gd.assist2_number = ?))
                      AND gd.team_name = ?
                      AND ag.season_id = ?
                """, (player['gamesheet_id'], player['number'],
                      player['gamesheet_id'], player['number'],
                      player['gamesheet_id'], player['number'],
                      player['team_name'], season_id))
                stats['games'].update(row[0] for row in cursor.fetchall())

            # Count penalties
            if has_penalty_events:
                cursor.execute("""
                    SELECT COUNT(*),
                           SUM(duration_minutes),
                           SUM(CASE WHEN major THEN 1 ELSE 0 END)
                    FROM penalty_events
                    WHERE penalized_player_id = ?
                """, (player_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    stats['penalties'] = row[0]
                    stats['pim'] = row[1] or 0
                    stats['major_penalties'] = row[2] or 0

                # Get games with penalties
                cursor.execute("""
                    SELECT DISTINCT game_entity_id
                    FROM penalty_events
                    WHERE penalized_player_id = ?
                """, (player_id,))
                stats['games'].update(row[0] for row in cursor.fetchall())

            elif has_penalty_details:
                cursor.execute("""
                    SELECT COUNT(*),
                           SUM(pd.duration_minutes),
                           SUM(CASE WHEN pd.is_major THEN 1 ELSE 0 END)
                    FROM penalties pd
                    JOIN games ag ON pd.game_id = ag.game_id
                    WHERE (pd.player_id = ? OR pd.player_number = ?)
                      AND pd.team_name = ?
                      AND ag.season_id = ?
                """, (player['gamesheet_id'], player['number'], player['team_name'], season_id))
                row = cursor.fetchone()
                if row and row[0]:
                    stats['penalties'] = row[0]
                    stats['pim'] = row[1] or 0
                    stats['major_penalties'] = row[2] or 0

                # Get games with penalties
                cursor.execute("""
                    SELECT DISTINCT pd.game_id
                    FROM penalties pd
                    JOIN games ag ON pd.game_id = ag.game_id
                    WHERE (pd.player_id = ? OR pd.player_number = ?)
                      AND pd.team_name = ?
                      AND ag.season_id = ?
                """, (player['gamesheet_id'], player['number'], player['team_name'], season_id))
                stats['games'].update(row[0] for row in cursor.fetchall())

            # Calculate derived stats
            games_played = len(stats['games'])
            points = stats['goals'] + stats['assists']
            pp_points = stats['pp_goals'] + stats['pp_assists']
            sh_points = stats['sh_goals'] + stats['sh_assists']
            ppg = points / games_played if games_played > 0 else 0.0
            pim_pg = stats['pim'] / games_played if games_played > 0 else 0.0

            # Insert player stats
            cursor.execute("""
                INSERT INTO player_stats (
                    player_id, team_id, season_id, player_number, player_name, position,
                    games_played, goals, assists, points, points_per_game,
                    power_play_goals, power_play_assists, power_play_points,
                    short_handed_goals, short_handed_assists, short_handed_points,
                    game_winning_goals, empty_net_goals,
                    penalties, penalty_minutes, pim_per_game, major_penalties
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                player_id, team_id, season_id, player.get('number'), '', '',
                games_played, stats['goals'], stats['assists'], points, ppg,
                stats['pp_goals'], stats['pp_assists'], pp_points,
                stats['sh_goals'], stats['sh_assists'], sh_points,
                stats['gw_goals'], stats['en_goals'],
                stats['penalties'], stats['pim'], pim_pg, stats['major_penalties']
            ))

        logger.info(f"Calculated stats for {len(players)} players")

    def calculate_team_basic_stats(self, cursor: sqlite3.Cursor, season_id: str) -> None:
        """
        Calculate basic team statistics from game results

        Aggregates:
        - Record (W-L-T)
        - Goals for/against
        - Points
        """

        # Check which schema version we have
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        has_game_entities = 'game_entities' in tables
        has_team_entities = 'team_entities' in tables
        has_all_games = 'games' in tables
        has_teams = 'teams' in tables

        # Clear existing stats
        cursor.execute("DELETE FROM team_stats WHERE season_id = ?", (season_id,))

        # Get all teams
        teams = []

        if has_team_entities:
            cursor.execute("""
                SELECT team_entity_id, team_name, division_id, division_name
                FROM team_entities
                WHERE season_id = ?
            """, (season_id,))

            for row in cursor.fetchall():
                teams.append({
                    'team_id': row[0],
                    'team_name': row[1],
                    'division_id': row[2],
                    'division_name': row[3]
                })

        elif has_teams:
            # Get teams that have games in this season
            cursor.execute("""
                SELECT DISTINCT t.team_id, t.team_name, t.division_id, d.division_name
                FROM teams t
                JOIN divisions d ON t.division_id = d.division_id
                JOIN games g ON (g.home_team_id = t.team_id OR g.visitor_team_id = t.team_id)
                WHERE g.season_id = ?
            """, (season_id,))

            for row in cursor.fetchall():
                teams.append({
                    'team_id': row[0],
                    'team_name': row[1],
                    'division_id': row[2],
                    'division_name': row[3]
                })

        logger.info(f"Calculating stats for {len(teams)} teams...")

        for team in teams:
            team_id = team['team_id']

            stats = {
                'games_played': 0,
                'wins': 0,
                'losses': 0,
                'ties': 0,
                'goals_for': 0,
                'goals_against': 0
            }

            if has_game_entities:
                # Enhanced entity schema
                cursor.execute("""
                    SELECT
                        COUNT(*) as games,
                        SUM(CASE
                            WHEN (home_team_entity_id = ? AND home_score > visitor_score)
                              OR (visitor_team_entity_id = ? AND visitor_score > home_score)
                            THEN 1 ELSE 0 END) as wins,
                        SUM(CASE
                            WHEN (home_team_entity_id = ? AND home_score < visitor_score)
                              OR (visitor_team_entity_id = ? AND visitor_score < home_score)
                            THEN 1 ELSE 0 END) as losses,
                        SUM(CASE
                            WHEN (home_team_entity_id = ? OR visitor_team_entity_id = ?)
                              AND home_score = visitor_score
                            THEN 1 ELSE 0 END) as ties,
                        SUM(CASE
                            WHEN home_team_entity_id = ? THEN home_score
                            WHEN visitor_team_entity_id = ? THEN visitor_score
                            ELSE 0 END) as goals_for,
                        SUM(CASE
                            WHEN home_team_entity_id = ? THEN visitor_score
                            WHEN visitor_team_entity_id = ? THEN home_score
                            ELSE 0 END) as goals_against
                    FROM game_entities
                    WHERE (home_team_entity_id = ? OR visitor_team_entity_id = ?)
                      AND (played = 1 OR has_box_score = 1)
                      AND home_score IS NOT NULL
                      AND visitor_score IS NOT NULL
                """, (team_id, team_id, team_id, team_id, team_id, team_id,
                      team_id, team_id, team_id, team_id, team_id, team_id))

            elif has_all_games:
                # Original schema
                team_name = team['team_name']
                cursor.execute("""
                    SELECT
                        COUNT(*) as games,
                        SUM(CASE
                            WHEN (home_team_name = ? AND home_score > visitor_score)
                              OR (visitor_team_name = ? AND visitor_score > home_score)
                            THEN 1 ELSE 0 END) as wins,
                        SUM(CASE
                            WHEN (home_team_name = ? AND home_score < visitor_score)
                              OR (visitor_team_name = ? AND visitor_score < home_score)
                            THEN 1 ELSE 0 END) as losses,
                        SUM(CASE
                            WHEN (home_team_name = ? OR visitor_team_name = ?)
                              AND home_score = visitor_score
                            THEN 1 ELSE 0 END) as ties,
                        SUM(CASE
                            WHEN home_team_name = ? THEN home_score
                            WHEN visitor_team_name = ? THEN visitor_score
                            ELSE 0 END) as goals_for,
                        SUM(CASE
                            WHEN home_team_name = ? THEN visitor_score
                            WHEN visitor_team_name = ? THEN home_score
                            ELSE 0 END) as goals_against
                    FROM games
                    WHERE (home_team_name = ? OR visitor_team_name = ?)
                      AND season_id = ?
                      AND status = 'final'
                      AND home_score IS NOT NULL
                      AND visitor_score IS NOT NULL
                """, (team_name, team_name, team_name, team_name, team_name, team_name,
                      team_name, team_name, team_name, team_name, team_name, team_name, season_id))

            row = cursor.fetchone()
            if row and row[0]:
                stats['games_played'] = row[0]
                stats['wins'] = row[1] or 0
                stats['losses'] = row[2] or 0
                stats['ties'] = row[3] or 0
                stats['goals_for'] = row[4] or 0
                stats['goals_against'] = row[5] or 0

            # Calculate derived stats
            goal_diff = stats['goals_for'] - stats['goals_against']
            points = (stats['wins'] * 2) + stats['ties']
            max_points = stats['games_played'] * 2
            points_pct = points / max_points if max_points > 0 else 0.0
            gpg = stats['goals_for'] / stats['games_played'] if stats['games_played'] > 0 else 0.0
            gapg = stats['goals_against'] / stats['games_played'] if stats['games_played'] > 0 else 0.0
            row_wins = stats['wins']  # Regulation + OT wins (no shootouts in youth hockey typically)

            # Insert team stats
            cursor.execute("""
                INSERT INTO team_stats (
                    team_id, season_id, division_id,
                    games_played, wins, losses, ties,
                    points, points_pct, row,
                    goals_for, goals_against, goal_differential,
                    goals_per_game, goals_against_per_game
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                team_id, season_id, team['division_id'],
                stats['games_played'], stats['wins'], stats['losses'], stats['ties'],
                points, points_pct, row_wins,
                stats['goals_for'], stats['goals_against'], goal_diff,
                gpg, gapg
            ))

        logger.info(f"Calculated stats for {len(teams)} teams")

    def calculate_goals_by_period(self, cursor: sqlite3.Cursor, season_id: str) -> None:
        """
        Calculate goals scored and allowed by period for each team

        Updates team_stats with period-by-period breakdowns
        """

        # Check schema version
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        has_goal_events = 'goal_events' in tables
        has_goal_details = 'goals' in tables
        has_team_entities = 'team_entities' in tables

        # Get all teams
        if has_team_entities:
            cursor.execute("""
                SELECT team_entity_id, team_name, division_name
                FROM team_entities
                WHERE season_id = ?
            """, (season_id,))
        else:
            cursor.execute("""
                SELECT DISTINCT t.team_id, t.team_name, d.division_name
                FROM teams t
                JOIN divisions d ON t.division_id = d.division_id
                JOIN games g ON (g.home_team_id = t.team_id OR g.visitor_team_id = t.team_id)
                WHERE g.season_id = ?
            """, (season_id,))

        teams = cursor.fetchall()

        for team in teams:
            team_id = team[0]
            team_name = team[1]
            division_name = team[2]

            period_stats = {
                'p1_for': 0, 'p1_against': 0,
                'p2_for': 0, 'p2_against': 0,
                'p3_for': 0, 'p3_against': 0,
                'ot_for': 0, 'ot_against': 0
            }

            if has_goal_events:
                # Goals FOR by period
                cursor.execute("""
                    SELECT period, COUNT(*)
                    FROM goal_events ge
                    WHERE scoring_team_entity_id = ?
                    GROUP BY period
                """, (team_id,))

                for row in cursor.fetchall():
                    period = (row[0] or '').upper()
                    count = row[1]
                    if '1ST' in period or 'FIRST' in period:
                        period_stats['p1_for'] = count
                    elif '2ND' in period or 'SECOND' in period:
                        period_stats['p2_for'] = count
                    elif '3RD' in period or 'THIRD' in period:
                        period_stats['p3_for'] = count
                    elif 'OT' in period or 'OVERTIME' in period:
                        period_stats['ot_for'] = count

                # Goals AGAINST by period
                cursor.execute("""
                    SELECT ge.period, COUNT(*)
                    FROM goal_events ge
                    JOIN game_entities gm ON ge.game_entity_id = gm.game_entity_id
                    WHERE (gm.home_team_entity_id = ? OR gm.visitor_team_entity_id = ?)
                      AND ge.scoring_team_entity_id != ?
                    GROUP BY ge.period
                """, (team_id, team_id, team_id))

                for row in cursor.fetchall():
                    period = (row[0] or '').upper()
                    count = row[1]
                    if '1ST' in period or 'FIRST' in period:
                        period_stats['p1_against'] = count
                    elif '2ND' in period or 'SECOND' in period:
                        period_stats['p2_against'] = count
                    elif '3RD' in period or 'THIRD' in period:
                        period_stats['p3_against'] = count
                    elif 'OT' in period or 'OVERTIME' in period:
                        period_stats['ot_against'] = count

            elif has_goal_details:
                # Goals FOR by period
                cursor.execute("""
                    SELECT gd.period, COUNT(*)
                    FROM goals gd
                    JOIN games ag ON gd.game_id = ag.game_id
                    WHERE gd.team_name = ?
                      AND ag.season_id = ?
                    GROUP BY gd.period
                """, (team_name, season_id))

                for row in cursor.fetchall():
                    period = (row[0] or '').upper()
                    count = row[1]
                    if '1ST' in period or 'FIRST' in period:
                        period_stats['p1_for'] = count
                    elif '2ND' in period or 'SECOND' in period:
                        period_stats['p2_for'] = count
                    elif '3RD' in period or 'THIRD' in period:
                        period_stats['p3_for'] = count
                    elif 'OT' in period or 'OVERTIME' in period:
                        period_stats['ot_for'] = count

                # Goals AGAINST by period
                cursor.execute("""
                    SELECT gd.period, COUNT(*)
                    FROM goals gd
                    JOIN games ag ON gd.game_id = ag.game_id
                    WHERE (ag.home_team_name = ? OR ag.visitor_team_name = ?)
                      AND gd.team_name != ?
                      AND ag.season_id = ?
                    GROUP BY gd.period
                """, (team_name, team_name, team_name, season_id))

                for row in cursor.fetchall():
                    period = (row[0] or '').upper()
                    count = row[1]
                    if '1ST' in period or 'FIRST' in period:
                        period_stats['p1_against'] = count
                    elif '2ND' in period or 'SECOND' in period:
                        period_stats['p2_against'] = count
                    elif '3RD' in period or 'THIRD' in period:
                        period_stats['p3_against'] = count
                    elif 'OT' in period or 'OVERTIME' in period:
                        period_stats['ot_against'] = count

            # Update team stats
            cursor.execute("""
                UPDATE team_stats SET
                    goals_period_1 = ?,
                    goals_period_2 = ?,
                    goals_period_3 = ?,
                    goals_overtime = ?,
                    goals_allowed_period_1 = ?,
                    goals_allowed_period_2 = ?,
                    goals_allowed_period_3 = ?,
                    goals_allowed_overtime = ?
                WHERE team_id = ? AND season_id = ?
            """, (
                period_stats['p1_for'], period_stats['p2_for'], period_stats['p3_for'], period_stats['ot_for'],
                period_stats['p1_against'], period_stats['p2_against'], period_stats['p3_against'], period_stats['ot_against'],
                team_id, season_id
            ))

        logger.info(f"Calculated period stats for {len(teams)} teams")

    def calculate_power_play_stats(self, cursor: sqlite3.Cursor, season_id: str) -> None:
        """
        Calculate power play percentage for each team

        Formula: PP% = (PP Goals / PP Opportunities) * 100

        PP Goals = Goals scored while on power play
        PP Opportunities = Penalties against opponent
        """

        # Check schema version
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        has_goal_events = 'goal_events' in tables
        has_penalty_events = 'penalty_events' in tables
        has_team_entities = 'team_entities' in tables

        # Get all teams
        if has_team_entities:
            cursor.execute("""
                SELECT team_entity_id, team_name, division_name
                FROM team_entities
                WHERE season_id = ?
            """, (season_id,))
        else:
            cursor.execute("""
                SELECT DISTINCT t.team_id, t.team_name, d.division_name
                FROM teams t
                JOIN divisions d ON t.division_id = d.division_id
                JOIN games g ON (g.home_team_id = t.team_id OR g.visitor_team_id = t.team_id)
                WHERE g.season_id = ?
            """, (season_id,))

        teams = cursor.fetchall()

        for team in teams:
            team_id = team[0]
            team_name = team[1]

            pp_goals = 0
            pp_opportunities = 0

            if has_goal_events and has_penalty_events:
                # Count PP goals
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM goal_events
                    WHERE scoring_team_entity_id = ?
                      AND power_play = 1
                """, (team_id,))
                pp_goals = cursor.fetchone()[0] or 0

                # Count opponent penalties (PP opportunities)
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM penalty_events pe
                    JOIN game_entities ge ON pe.game_entity_id = ge.game_entity_id
                    WHERE (ge.home_team_entity_id = ? OR ge.visitor_team_entity_id = ?)
                      AND pe.penalized_team_entity_id != ?
                      AND pe.duration_minutes >= 2
                """, (team_id, team_id, team_id))
                pp_opportunities = cursor.fetchone()[0] or 0

            else:
                # Use current schema (goals, penalties, games tables)
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM goals g
                    JOIN games ga ON g.game_id = ga.game_id
                    WHERE g.team_id = ?
                      AND ga.season_id = ?
                      AND g.is_power_play = 1
                """, (team_id, season_id))
                pp_goals = cursor.fetchone()[0] or 0

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM penalties p
                    JOIN games g ON p.game_id = g.game_id
                    WHERE g.season_id = ?
                      AND (g.home_team_id = ? OR g.visitor_team_id = ?)
                      AND p.team_id != ?
                      AND p.duration_minutes >= 2
                """, (season_id, team_id, team_id, team_id))
                pp_opportunities = cursor.fetchone()[0] or 0

            # Calculate PP%
            pp_pct = (pp_goals / pp_opportunities * 100) if pp_opportunities > 0 else 0.0

            # Update team stats
            cursor.execute("""
                UPDATE team_stats SET
                    power_play_goals = ?,
                    power_play_opportunities = ?,
                    power_play_pct = ?
                WHERE team_id = ? AND season_id = ?
            """, (pp_goals, pp_opportunities, pp_pct, team_id, season_id))

        logger.info(f"Calculated PP% for {len(teams)} teams")

    def calculate_penalty_kill_stats(self, cursor: sqlite3.Cursor, season_id: str) -> None:
        """
        Calculate penalty kill percentage for each team

        Formula: PK% = 1 - (PP Goals Against / Times Shorthanded) * 100

        PP Goals Against = Goals allowed while shorthanded
        Times Shorthanded = Penalties taken by team
        """

        # Check schema version
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        has_goal_events = 'goal_events' in tables
        has_penalty_events = 'penalty_events' in tables
        has_team_entities = 'team_entities' in tables

        # Get all teams
        if has_team_entities:
            cursor.execute("""
                SELECT team_entity_id, team_name, division_name
                FROM team_entities
                WHERE season_id = ?
            """, (season_id,))
        else:
            cursor.execute("""
                SELECT DISTINCT t.team_id, t.team_name, d.division_name
                FROM teams t
                JOIN divisions d ON t.division_id = d.division_id
                JOIN games g ON (g.home_team_id = t.team_id OR g.visitor_team_id = t.team_id)
                WHERE g.season_id = ?
            """, (season_id,))

        teams = cursor.fetchall()

        for team in teams:
            team_id = team[0]
            team_name = team[1]

            pp_goals_against = 0
            times_shorthanded = 0

            if has_goal_events and has_penalty_events:
                # Count PP goals against (goals scored by opponent on power play)
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM goal_events ge
                    JOIN game_entities gm ON ge.game_entity_id = gm.game_entity_id
                    WHERE (gm.home_team_entity_id = ? OR gm.visitor_team_entity_id = ?)
                      AND ge.scoring_team_entity_id != ?
                      AND ge.power_play = 1
                """, (team_id, team_id, team_id))
                pp_goals_against = cursor.fetchone()[0] or 0

                # Count penalties taken (times shorthanded)
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM penalty_events
                    WHERE penalized_team_entity_id = ?
                      AND duration_minutes >= 2
                """, (team_id,))
                times_shorthanded = cursor.fetchone()[0] or 0

            else:
                # Use original schema
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM goals gd
                    JOIN games ag ON gd.game_id = ag.game_id
                    WHERE (ag.home_team_name = ? OR ag.visitor_team_name = ?)
                      AND gd.team_name != ?
                      AND ag.season_id = ?
                      AND gd.is_power_play = 1
                """, (team_name, team_name, team_name, season_id))
                pp_goals_against = cursor.fetchone()[0] or 0

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM penalties pd
                    JOIN games ag ON pd.game_id = ag.game_id
                    WHERE pd.team_name = ?
                      AND ag.season_id = ?
                      AND pd.duration_minutes >= 2
                """, (team_name, season_id))
                times_shorthanded = cursor.fetchone()[0] or 0

            # Calculate PK%
            pk_pct = ((times_shorthanded - pp_goals_against) / times_shorthanded * 100) if times_shorthanded > 0 else 0.0

            # Update team stats
            cursor.execute("""
                UPDATE team_stats SET
                    power_play_goals_against = ?,
                    times_shorthanded = ?,
                    penalty_kill_pct = ?
                WHERE team_id = ? AND season_id = ?
            """, (pp_goals_against, times_shorthanded, pk_pct, team_id, season_id))

        logger.info(f"Calculated PK% for {len(teams)} teams")

    def calculate_home_away_splits(self, cursor: sqlite3.Cursor, season_id: str) -> None:
        """
        Calculate home and away splits for each team

        Records W-L-T and GF-GA for home and away games separately
        """

        # Check schema version
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        has_game_entities = 'game_entities' in tables
        has_team_entities = 'team_entities' in tables

        # Get all teams
        if has_team_entities:
            cursor.execute("""
                SELECT team_entity_id, team_name
                FROM team_entities
                WHERE season_id = ?
            """, (season_id,))
        else:
            cursor.execute("""
                SELECT DISTINCT t.team_id, t.team_name
                FROM teams t
                JOIN games g ON (g.home_team_id = t.team_id OR g.visitor_team_id = t.team_id)
                WHERE g.season_id = ?
            """, (season_id,))

        teams = cursor.fetchall()

        for team in teams:
            team_id = team[0]
            team_name = team[1]

            home_stats = {'wins': 0, 'losses': 0, 'ties': 0, 'gf': 0, 'ga': 0}
            away_stats = {'wins': 0, 'losses': 0, 'ties': 0, 'gf': 0, 'ga': 0}

            if has_game_entities:
                # Home games
                cursor.execute("""
                    SELECT
                        SUM(CASE WHEN home_score > visitor_score THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN home_score < visitor_score THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN home_score = visitor_score THEN 1 ELSE 0 END) as ties,
                        SUM(home_score) as gf,
                        SUM(visitor_score) as ga
                    FROM game_entities
                    WHERE home_team_entity_id = ?
                      AND (played = 1 OR has_box_score = 1)
                      AND home_score IS NOT NULL
                      AND visitor_score IS NOT NULL
                """, (team_id,))
                row = cursor.fetchone()
                if row:
                    home_stats = {
                        'wins': row[0] or 0,
                        'losses': row[1] or 0,
                        'ties': row[2] or 0,
                        'gf': row[3] or 0,
                        'ga': row[4] or 0
                    }

                # Away games
                cursor.execute("""
                    SELECT
                        SUM(CASE WHEN visitor_score > home_score THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN visitor_score < home_score THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN visitor_score = home_score THEN 1 ELSE 0 END) as ties,
                        SUM(visitor_score) as gf,
                        SUM(home_score) as ga
                    FROM game_entities
                    WHERE visitor_team_entity_id = ?
                      AND (played = 1 OR has_box_score = 1)
                      AND home_score IS NOT NULL
                      AND visitor_score IS NOT NULL
                """, (team_id,))
                row = cursor.fetchone()
                if row:
                    away_stats = {
                        'wins': row[0] or 0,
                        'losses': row[1] or 0,
                        'ties': row[2] or 0,
                        'gf': row[3] or 0,
                        'ga': row[4] or 0
                    }

            else:
                # Use original schema
                # Home games
                cursor.execute("""
                    SELECT
                        SUM(CASE WHEN home_score > visitor_score THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN home_score < visitor_score THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN home_score = visitor_score THEN 1 ELSE 0 END) as ties,
                        SUM(home_score) as gf,
                        SUM(visitor_score) as ga
                    FROM games
                    WHERE home_team_name = ?
                      AND season_id = ?
                      AND status = 'final'
                      AND home_score IS NOT NULL
                      AND visitor_score IS NOT NULL
                """, (team_name, season_id))
                row = cursor.fetchone()
                if row:
                    home_stats = {
                        'wins': row[0] or 0,
                        'losses': row[1] or 0,
                        'ties': row[2] or 0,
                        'gf': row[3] or 0,
                        'ga': row[4] or 0
                    }

                # Away games
                cursor.execute("""
                    SELECT
                        SUM(CASE WHEN visitor_score > home_score THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN visitor_score < home_score THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN visitor_score = home_score THEN 1 ELSE 0 END) as ties,
                        SUM(visitor_score) as gf,
                        SUM(home_score) as ga
                    FROM games
                    WHERE visitor_team_name = ?
                      AND season_id = ?
                      AND status = 'final'
                      AND home_score IS NOT NULL
                      AND visitor_score IS NOT NULL
                """, (team_name, season_id))
                row = cursor.fetchone()
                if row:
                    away_stats = {
                        'wins': row[0] or 0,
                        'losses': row[1] or 0,
                        'ties': row[2] or 0,
                        'gf': row[3] or 0,
                        'ga': row[4] or 0
                    }

            # Update team stats
            cursor.execute("""
                UPDATE team_stats SET
                    home_wins = ?,
                    home_losses = ?,
                    home_ties = ?,
                    home_goals_for = ?,
                    home_goals_against = ?,
                    away_wins = ?,
                    away_losses = ?,
                    away_ties = ?,
                    away_goals_for = ?,
                    away_goals_against = ?
                WHERE team_id = ? AND season_id = ?
            """, (
                home_stats['wins'], home_stats['losses'], home_stats['ties'],
                home_stats['gf'], home_stats['ga'],
                away_stats['wins'], away_stats['losses'], away_stats['ties'],
                away_stats['gf'], away_stats['ga'],
                team_id, season_id
            ))

        logger.info(f"Calculated home/away splits for {len(teams)} teams")


def main():
    """Example usage of the AdvancedStatsCalculator"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 stats_calculator.py <database_path> [season_id]")
        print("\nExample:")
        print("  python3 stats_calculator.py output/hockey_stats.db 10776")
        sys.exit(1)

    db_path = sys.argv[1]
    season_id = sys.argv[2] if len(sys.argv) > 2 else "10776"

    print(f"Calculating stats for database: {db_path}")
    print(f"Season ID: {season_id}")
    print()

    calculator = AdvancedStatsCalculator(db_path)
    calculator.calculate_all_stats(season_id)

    print("\n✅ Stats calculation complete!")
    print(f"   Database: {db_path}")
    print(f"   Tables updated: player_stats, team_stats")


if __name__ == "__main__":
    main()
