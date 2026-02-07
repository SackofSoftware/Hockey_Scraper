#!/usr/bin/env python3
"""
Advanced Metrics Calculator
Calculates advanced hockey metrics including SOS, SOV, H2H, streaks, and trends.

This module handles:
- Strength of Schedule (SOS) - average opponent winning percentage
- Adjusted SOS (2-degree) - includes opponent's opponents
- Strength of Victory (SOV) - quality of teams beaten
- Head-to-head records between teams
- Rest differential analysis (back-to-back games)
- Last 10 games trends
- Current streak tracking

Usage:
    calculator = AdvancedMetricsCalculator("path/to/database.db")
    calculator.calculate_all_advanced_metrics(season_id="10776")
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdvancedMetricsCalculator:
    """Calculate advanced scheduling and performance metrics"""

    def __init__(self, db_path: str):
        """
        Initialize calculator with database path

        Args:
            db_path: Path to SQLite database containing game and team data
        """
        self.db_path = db_path

    def calculate_all_advanced_metrics(self, season_id: str) -> None:
        """
        Run complete advanced metrics calculation pipeline

        Args:
            season_id: Season ID to calculate metrics for (e.g., "10776")
        """
        logger.info(f"Starting advanced metrics calculation for season {season_id}")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create advanced metrics tables
            self._create_advanced_tables(cursor)

            # Calculate metrics
            logger.info("Calculating strength of schedule...")
            self.calculate_strength_of_schedule(cursor, season_id)

            logger.info("Calculating head-to-head records...")
            self.calculate_head_to_head(cursor, season_id)

            logger.info("Calculating rest differentials...")
            self.calculate_rest_differential(cursor, season_id)

            logger.info("Calculating recent form (last 10, streaks)...")
            self.calculate_recent_form(cursor, season_id)

            conn.commit()

        logger.info("Advanced metrics calculation complete!")

    def _create_advanced_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create tables for advanced metrics"""

        # Strength of Schedule table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strength_of_schedule (
                team_id INTEGER,
                season_id TEXT,

                -- Basic SOS
                opponents_avg_points_pct REAL DEFAULT 0.0,
                sos_rank INTEGER,

                -- Adjusted SOS (2-degree)
                opponents_opponents_points_pct REAL DEFAULT 0.0,
                adjusted_sos REAL DEFAULT 0.0,

                -- Strength of Victory
                beaten_teams_avg_points_pct REAL DEFAULT 0.0,
                sov_rank INTEGER,

                -- Games breakdown
                games_vs_top_third INTEGER DEFAULT 0,
                games_vs_middle_third INTEGER DEFAULT 0,
                games_vs_bottom_third INTEGER DEFAULT 0,
                points_vs_top_third INTEGER DEFAULT 0,
                points_vs_middle_third INTEGER DEFAULT 0,
                points_vs_bottom_third INTEGER DEFAULT 0,

                -- Rest analysis
                games_on_rest INTEGER DEFAULT 0,
                games_back_to_back INTEGER DEFAULT 0,
                rest_differential INTEGER DEFAULT 0,

                -- Travel (manual data if available)
                total_travel_distance REAL DEFAULT 0.0,
                avg_travel_per_game REAL DEFAULT 0.0,

                PRIMARY KEY (team_id, season_id)
            )
        ''')

        # Head-to-Head table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS head_to_head (
                team1_id INTEGER,
                team2_id INTEGER,
                season_id TEXT,

                -- Overall record
                games_played INTEGER DEFAULT 0,
                team1_wins INTEGER DEFAULT 0,
                team1_losses INTEGER DEFAULT 0,
                team1_ties INTEGER DEFAULT 0,
                team1_points INTEGER DEFAULT 0,
                team1_points_pct REAL DEFAULT 0.0,

                -- Scoring
                team1_goals_for INTEGER DEFAULT 0,
                team1_goals_against INTEGER DEFAULT 0,
                goal_differential INTEGER DEFAULT 0,

                -- Special teams
                team1_pp_goals INTEGER DEFAULT 0,
                team1_pp_opportunities INTEGER DEFAULT 0,
                team1_pp_pct REAL DEFAULT 0.0,
                team1_pk_pct REAL DEFAULT 0.0,

                -- Recent trend
                last_5_record TEXT,
                team1_current_streak TEXT,

                PRIMARY KEY (team1_id, team2_id, season_id)
            )
        ''')

        logger.info("Advanced metrics tables created/verified")

    def calculate_strength_of_schedule(self, cursor: sqlite3.Cursor, season_id: str) -> None:
        """
        Calculate Strength of Schedule metrics

        SOS = Average of opponents' points percentage
        Adjusted SOS = (Opp PTS% × 2/3) + (Opp's Opp PTS% × 1/3)
        SOV = Average points% of teams beaten

        Also calculates games vs top/middle/bottom third of division
        """

        # Check schema version
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        has_game_entities = 'game_entities' in tables
        has_team_stats = 'team_stats' in tables

        # Clear existing SOS data
        cursor.execute("DELETE FROM strength_of_schedule WHERE season_id = ?", (season_id,))

        # Get all teams with their points%
        if not has_team_stats:
            logger.warning("team_stats table not found. Run basic stats calculation first.")
            return

        cursor.execute("""
            SELECT team_id, points_pct
            FROM team_stats
            WHERE season_id = ?
        """, (season_id,))

        teams_points_pct = {row[0]: row[1] for row in cursor.fetchall()}

        if not teams_points_pct:
            logger.warning("No team stats found. Run basic stats calculation first.")
            return

        # Get division teams for ranking
        cursor.execute("""
            SELECT team_id, division_id, points_pct
            FROM team_stats
            WHERE season_id = ?
            ORDER BY division_id, points_pct DESC
        """, (season_id,))

        division_teams = defaultdict(list)
        for team_id, div_id, pts_pct in cursor.fetchall():
            division_teams[div_id].append((team_id, pts_pct))

        # Calculate SOS for each team
        for team_id in teams_points_pct.keys():
            # Get all opponents for this team
            if has_game_entities:
                cursor.execute("""
                    SELECT DISTINCT
                        CASE
                            WHEN home_team_entity_id = ? THEN visitor_team_entity_id
                            ELSE home_team_entity_id
                        END as opponent_id
                    FROM game_entities
                    WHERE (home_team_entity_id = ? OR visitor_team_entity_id = ?)
                      AND (played = 1 OR has_box_score = 1)
                """, (team_id, team_id, team_id))
            else:
                # Get team name for lookup
                cursor.execute("""
                    SELECT t.team_name
                    FROM teams t
                    WHERE t.team_id = ?
                """, (team_id,))
                result = cursor.fetchone()
                if not result:
                    continue
                team_name = result[0]

                cursor.execute("""
                    SELECT DISTINCT
                        CASE
                            WHEN home_team_name = ? THEN visitor_team_name
                            ELSE home_team_name
                        END as opponent_name
                    FROM games
                    WHERE (home_team_name = ? OR visitor_team_name = ?)
                      AND season_id = ?
                      AND status = 'final'
                """, (team_name, team_name, team_name, season_id))

                # Convert opponent names to IDs
                opponent_names = [row[0] for row in cursor.fetchall()]
                cursor.execute(f"""
                    SELECT team_id
                    FROM teams
                    WHERE team_name IN ({','.join('?' * len(opponent_names))})
                """, opponent_names)

            opponents = [row[0] for row in cursor.fetchall()]

            # Calculate basic SOS (average opponent points%)
            opponent_points_pcts = [teams_points_pct.get(opp, 0.0) for opp in opponents]
            sos = sum(opponent_points_pcts) / len(opponent_points_pcts) if opponent_points_pcts else 0.0

            # Calculate 2-degree SOS (opponents' opponents)
            opponents_opponents_pcts = []
            for opponent_id in opponents:
                # Get this opponent's opponents
                if has_game_entities:
                    cursor.execute("""
                        SELECT DISTINCT
                            CASE
                                WHEN home_team_entity_id = ? THEN visitor_team_entity_id
                                ELSE home_team_entity_id
                            END as opp_opp_id
                        FROM game_entities
                        WHERE (home_team_entity_id = ? OR visitor_team_entity_id = ?)
                          AND (played = 1 OR has_box_score = 1)
                    """, (opponent_id, opponent_id, opponent_id))
                    opp_opponents = [row[0] for row in cursor.fetchall()]
                    opp_opp_pcts = [teams_points_pct.get(oo, 0.0) for oo in opp_opponents]
                    if opp_opp_pcts:
                        opponents_opponents_pcts.append(sum(opp_opp_pcts) / len(opp_opp_pcts))

            opp_opp_avg = sum(opponents_opponents_pcts) / len(opponents_opponents_pcts) if opponents_opponents_pcts else 0.0

            # Adjusted SOS = (SOS × 2/3) + (Opp's Opp SOS × 1/3)
            adjusted_sos = (sos * 2/3) + (opp_opp_avg * 1/3)

            # Calculate Strength of Victory (average points% of beaten teams)
            beaten_teams = []
            if has_game_entities:
                cursor.execute("""
                    SELECT
                        CASE
                            WHEN home_team_entity_id = ? AND home_score > visitor_score THEN visitor_team_entity_id
                            WHEN visitor_team_entity_id = ? AND visitor_score > home_score THEN home_team_entity_id
                        END as beaten_team_id
                    FROM game_entities
                    WHERE (home_team_entity_id = ? OR visitor_team_entity_id = ?)
                      AND (played = 1 OR has_box_score = 1)
                      AND home_score IS NOT NULL
                      AND visitor_score IS NOT NULL
                """, (team_id, team_id, team_id, team_id))
                beaten_teams = [row[0] for row in cursor.fetchall() if row[0]]

            beaten_pcts = [teams_points_pct.get(bt, 0.0) for bt in beaten_teams]
            sov = sum(beaten_pcts) / len(beaten_pcts) if beaten_pcts else 0.0

            # Calculate games vs top/middle/bottom third
            # Get division for this team
            cursor.execute("""
                SELECT division_id FROM team_stats WHERE team_id = ? AND season_id = ?
            """, (team_id, season_id))
            div_result = cursor.fetchone()
            if not div_result:
                continue

            div_id = div_result[0]
            div_teams = division_teams.get(div_id, [])

            # Split into thirds
            n = len(div_teams)
            top_third = [t[0] for t in div_teams[:n//3]]
            bottom_third = [t[0] for t in div_teams[-(n//3):]]
            middle_third = [t[0] for t in div_teams if t[0] not in top_third and t[0] not in bottom_third]

            # Count games and points vs each third
            games_vs_top = sum(1 for opp in opponents if opp in top_third)
            games_vs_middle = sum(1 for opp in opponents if opp in middle_third)
            games_vs_bottom = sum(1 for opp in opponents if opp in bottom_third)

            # Count points earned vs each third
            points_vs_top = self._count_points_vs_opponents(cursor, team_id, top_third, has_game_entities)
            points_vs_middle = self._count_points_vs_opponents(cursor, team_id, middle_third, has_game_entities)
            points_vs_bottom = self._count_points_vs_opponents(cursor, team_id, bottom_third, has_game_entities)

            # Calculate rest differential
            rest_stats = self._calculate_rest_for_team(cursor, team_id, has_game_entities, season_id)

            # Insert SOS data
            cursor.execute("""
                INSERT OR REPLACE INTO strength_of_schedule (
                    team_id, season_id,
                    opponents_avg_points_pct, opponents_opponents_points_pct, adjusted_sos,
                    beaten_teams_avg_points_pct,
                    games_vs_top_third, games_vs_middle_third, games_vs_bottom_third,
                    points_vs_top_third, points_vs_middle_third, points_vs_bottom_third,
                    games_on_rest, games_back_to_back, rest_differential
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                team_id, season_id,
                sos, opp_opp_avg, adjusted_sos,
                sov,
                games_vs_top, games_vs_middle, games_vs_bottom,
                points_vs_top, points_vs_middle, points_vs_bottom,
                rest_stats['games_on_rest'], rest_stats['games_b2b'], rest_stats['rest_diff']
            ))

        # Calculate and assign SOS ranks
        cursor.execute("""
            SELECT team_id, opponents_avg_points_pct
            FROM strength_of_schedule
            WHERE season_id = ?
            ORDER BY opponents_avg_points_pct DESC
        """, (season_id,))

        for rank, (team_id, _) in enumerate(cursor.fetchall(), 1):
            cursor.execute("""
                UPDATE strength_of_schedule
                SET sos_rank = ?
                WHERE team_id = ? AND season_id = ?
            """, (rank, team_id, season_id))

        # Calculate and assign SOV ranks
        cursor.execute("""
            SELECT team_id, beaten_teams_avg_points_pct
            FROM strength_of_schedule
            WHERE season_id = ?
            ORDER BY beaten_teams_avg_points_pct DESC
        """, (season_id,))

        for rank, (team_id, _) in enumerate(cursor.fetchall(), 1):
            cursor.execute("""
                UPDATE strength_of_schedule
                SET sov_rank = ?
                WHERE team_id = ? AND season_id = ?
            """, (rank, team_id, season_id))

        logger.info(f"Calculated SOS for {len(teams_points_pct)} teams")

    def _count_points_vs_opponents(self, cursor: sqlite3.Cursor, team_id: int,
                                   opponents: List[int], has_game_entities: bool) -> int:
        """Count points earned against specific opponents"""
        if not opponents:
            return 0

        placeholders = ','.join('?' * len(opponents))

        if has_game_entities:
            cursor.execute(f"""
                SELECT
                    SUM(CASE
                        WHEN (home_team_entity_id = ? AND home_score > visitor_score AND visitor_team_entity_id IN ({placeholders}))
                          OR (visitor_team_entity_id = ? AND visitor_score > home_score AND home_team_entity_id IN ({placeholders}))
                        THEN 2
                        WHEN (home_team_entity_id = ? AND home_score = visitor_score AND visitor_team_entity_id IN ({placeholders}))
                          OR (visitor_team_entity_id = ? AND visitor_score = home_score AND home_team_entity_id IN ({placeholders}))
                        THEN 1
                        ELSE 0
                    END) as points
                FROM game_entities
                WHERE (home_team_entity_id = ? OR visitor_team_entity_id = ?)
                  AND (played = 1 OR has_box_score = 1)
            """, (team_id, *opponents, team_id, *opponents, team_id, *opponents, team_id, *opponents, team_id, team_id))
        else:
            # Would need team names - simplified for now
            return 0

        result = cursor.fetchone()
        return result[0] or 0 if result else 0

    def _calculate_rest_for_team(self, cursor: sqlite3.Cursor, team_id: int,
                                 has_game_entities: bool, season_id: str) -> Dict[str, int]:
        """Calculate rest days between games for a team"""

        # Get all game dates for this team in chronological order
        if has_game_entities:
            cursor.execute("""
                SELECT date
                FROM game_entities
                WHERE (home_team_entity_id = ? OR visitor_team_entity_id = ?)
                  AND (played = 1 OR has_box_score = 1)
                  AND date IS NOT NULL
                ORDER BY date
            """, (team_id, team_id))
        else:
            cursor.execute("""
                SELECT t.team_name FROM teams t WHERE t.team_id = ?
            """, (team_id,))
            result = cursor.fetchone()
            if not result:
                return {'games_on_rest': 0, 'games_b2b': 0, 'rest_diff': 0}

            team_name = result[0]
            cursor.execute("""
                SELECT date
                FROM games
                WHERE (home_team_name = ? OR visitor_team_name = ?)
                  AND season_id = ?
                  AND status = 'final'
                  AND date IS NOT NULL
                ORDER BY date
            """, (team_name, team_name, season_id))

        game_dates = [row[0] for row in cursor.fetchall()]

        games_on_rest = 0
        games_back_to_back = 0

        for i in range(1, len(game_dates)):
            try:
                prev_date = datetime.strptime(game_dates[i-1], '%Y-%m-%d')
                curr_date = datetime.strptime(game_dates[i], '%Y-%m-%d')
                days_rest = (curr_date - prev_date).days - 1

                if days_rest == 0:
                    games_back_to_back += 1
                elif days_rest >= 2:
                    games_on_rest += 1
            except:
                continue

        # Rest differential = games on rest - games back-to-back
        rest_diff = games_on_rest - games_back_to_back

        return {
            'games_on_rest': games_on_rest,
            'games_b2b': games_back_to_back,
            'rest_diff': rest_diff
        }

    def calculate_head_to_head(self, cursor: sqlite3.Cursor, season_id: str) -> None:
        """
        Calculate head-to-head records between all team pairs

        For each pair of teams that have played, track:
        - Record (W-L-T)
        - Goals for/against
        - Special teams performance
        """

        # Check schema version
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        has_game_entities = 'game_entities' in tables
        has_goal_events = 'goal_events' in tables
        has_penalty_events = 'penalty_events' in tables

        # Clear existing H2H data
        cursor.execute("DELETE FROM head_to_head WHERE season_id = ?", (season_id,))

        # Get all teams
        cursor.execute("""
            SELECT team_id FROM team_stats WHERE season_id = ?
        """, (season_id,))
        teams = [row[0] for row in cursor.fetchall()]

        h2h_count = 0

        # For each pair of teams
        for i, team1_id in enumerate(teams):
            for team2_id in teams[i+1:]:
                # Get all games between these teams
                if has_game_entities:
                    cursor.execute("""
                        SELECT game_entity_id, home_team_entity_id, visitor_team_entity_id,
                               home_score, visitor_score
                        FROM game_entities
                        WHERE ((home_team_entity_id = ? AND visitor_team_entity_id = ?)
                            OR (home_team_entity_id = ? AND visitor_team_entity_id = ?))
                          AND (played = 1 OR has_box_score = 1)
                          AND home_score IS NOT NULL
                          AND visitor_score IS NOT NULL
                    """, (team1_id, team2_id, team2_id, team1_id))
                else:
                    # Get team names
                    cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", (team1_id,))
                    team1_name = cursor.fetchone()[0]
                    cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", (team2_id,))
                    team2_name = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT game_id, home_team_name, visitor_team_name,
                               home_score, visitor_score
                        FROM games
                        WHERE ((home_team_name = ? AND visitor_team_name = ?)
                            OR (home_team_name = ? AND visitor_team_name = ?))
                          AND season_id = ?
                          AND status = 'final'
                          AND home_score IS NOT NULL
                          AND visitor_score IS NOT NULL
                    """, (team1_name, team2_name, team2_name, team1_name, season_id))

                games = cursor.fetchall()
                if not games:
                    continue

                h2h_count += 1

                # Calculate stats
                stats = {
                    'games': len(games),
                    'team1_wins': 0,
                    'team1_losses': 0,
                    'team1_ties': 0,
                    'team1_gf': 0,
                    'team1_ga': 0,
                    'team1_pp_goals': 0,
                    'team1_pp_opps': 0,
                    'recent_games': []
                }

                for game in games:
                    game_id = game[0]
                    home_team = game[1]
                    visitor_team = game[2]
                    home_score = game[3]
                    visitor_score = game[4]

                    # Determine team1's role and result
                    if has_game_entities:
                        # Enhanced schema: compare IDs
                        if home_team == team1_id:
                            team1_score = home_score
                            team2_score = visitor_score
                        else:
                            team1_score = visitor_score
                            team2_score = home_score
                    else:
                        # Original schema: compare names
                        if home_team == team1_name:
                            team1_score = home_score
                            team2_score = visitor_score
                        else:
                            team1_score = visitor_score
                            team2_score = home_score

                    stats['team1_gf'] += team1_score
                    stats['team1_ga'] += team2_score

                    if team1_score > team2_score:
                        stats['team1_wins'] += 1
                        result = 'W'
                    elif team1_score < team2_score:
                        stats['team1_losses'] += 1
                        result = 'L'
                    else:
                        stats['team1_ties'] += 1
                        result = 'T'

                    stats['recent_games'].append(result)

                    # Count PP goals and opportunities if available
                    if has_goal_events:
                        cursor.execute("""
                            SELECT COUNT(*)
                            FROM goal_events
                            WHERE game_entity_id = ?
                              AND scoring_team_entity_id = ?
                              AND power_play = 1
                        """, (game_id, team1_id))
                        stats['team1_pp_goals'] += cursor.fetchone()[0] or 0

                    if has_penalty_events:
                        cursor.execute("""
                            SELECT COUNT(*)
                            FROM penalty_events
                            WHERE game_entity_id = ?
                              AND penalized_team_entity_id = ?
                              AND duration_minutes >= 2
                        """, (game_id, team2_id))
                        stats['team1_pp_opps'] += cursor.fetchone()[0] or 0

                # Calculate derived stats
                team1_points = (stats['team1_wins'] * 2) + stats['team1_ties']
                max_points = stats['games'] * 2
                team1_points_pct = team1_points / max_points if max_points > 0 else 0.0
                goal_diff = stats['team1_gf'] - stats['team1_ga']
                pp_pct = (stats['team1_pp_goals'] / stats['team1_pp_opps'] * 100) if stats['team1_pp_opps'] > 0 else 0.0

                # Last 5 record
                recent_5 = stats['recent_games'][-5:]
                last_5_w = recent_5.count('W')
                last_5_l = recent_5.count('L')
                last_5_t = recent_5.count('T')
                last_5_record = f"{last_5_w}-{last_5_l}-{last_5_t}"

                # Current streak
                if stats['recent_games']:
                    streak_type = stats['recent_games'][-1]
                    streak_len = 1
                    for result in reversed(stats['recent_games'][:-1]):
                        if result == streak_type:
                            streak_len += 1
                        else:
                            break
                    current_streak = f"{streak_type}{streak_len}"
                else:
                    current_streak = "N/A"

                # Insert H2H record
                cursor.execute("""
                    INSERT INTO head_to_head (
                        team1_id, team2_id, season_id,
                        games_played, team1_wins, team1_losses, team1_ties,
                        team1_points, team1_points_pct,
                        team1_goals_for, team1_goals_against, goal_differential,
                        team1_pp_goals, team1_pp_opportunities, team1_pp_pct,
                        last_5_record, team1_current_streak
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    team1_id, team2_id, season_id,
                    stats['games'], stats['team1_wins'], stats['team1_losses'], stats['team1_ties'],
                    team1_points, team1_points_pct,
                    stats['team1_gf'], stats['team1_ga'], goal_diff,
                    stats['team1_pp_goals'], stats['team1_pp_opps'], pp_pct,
                    last_5_record, current_streak
                ))

        logger.info(f"Calculated {h2h_count} head-to-head matchups")

    def calculate_rest_differential(self, cursor: sqlite3.Cursor, season_id: str) -> None:
        """
        Calculate rest differential for each team

        Already handled in calculate_strength_of_schedule, but this
        provides a standalone method if needed
        """
        logger.info("Rest differential already calculated in SOS metrics")

    def calculate_recent_form(self, cursor: sqlite3.Cursor, season_id: str) -> None:
        """
        Calculate recent form metrics for each team:
        - Last 10 games record
        - Current streak (W/L/T)

        Updates team_stats table
        """

        # Check schema version
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        has_game_entities = 'game_entities' in tables

        # Get all teams
        cursor.execute("""
            SELECT team_id FROM team_stats WHERE season_id = ?
        """, (season_id,))
        teams = [row[0] for row in cursor.fetchall()]

        for team_id in teams:
            # Get all games for this team in chronological order
            if has_game_entities:
                cursor.execute("""
                    SELECT date, home_team_entity_id, visitor_team_entity_id,
                           home_score, visitor_score
                    FROM game_entities
                    WHERE (home_team_entity_id = ? OR visitor_team_entity_id = ?)
                      AND (played = 1 OR has_box_score = 1)
                      AND home_score IS NOT NULL
                      AND visitor_score IS NOT NULL
                    ORDER BY date
                """, (team_id, team_id))
            else:
                # Get team name
                cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", (team_id,))
                result = cursor.fetchone()
                if not result:
                    continue
                team_name = result[0]

                cursor.execute("""
                    SELECT date, home_team_name, visitor_team_name,
                           home_score, visitor_score
                    FROM games
                    WHERE (home_team_name = ? OR visitor_team_name = ?)
                      AND season_id = ?
                      AND status = 'final'
                      AND home_score IS NOT NULL
                      AND visitor_score IS NOT NULL
                    ORDER BY date
                """, (team_name, team_name, season_id))

            games = cursor.fetchall()
            if not games:
                continue

            # Determine result for each game
            results = []
            for game in games:
                home_team = game[1]
                home_score = game[3]
                visitor_score = game[4]

                # Is current team home or away?
                if has_game_entities:
                    # Enhanced schema: compare IDs
                    if home_team == team_id:
                        team_score = home_score
                        opp_score = visitor_score
                    else:
                        team_score = visitor_score
                        opp_score = home_score
                else:
                    # Original schema: compare names
                    if home_team == team_name:
                        team_score = home_score
                        opp_score = visitor_score
                    else:
                        team_score = visitor_score
                        opp_score = home_score

                if team_score > opp_score:
                    results.append('W')
                elif team_score < opp_score:
                    results.append('L')
                else:
                    results.append('T')

            # Last 10 record
            last_10 = results[-10:]
            last_10_w = last_10.count('W')
            last_10_l = last_10.count('L')
            last_10_t = last_10.count('T')
            last_10_record = f"{last_10_w}-{last_10_l}-{last_10_t}"

            # Current streak
            if results:
                streak_type = results[-1]
                streak_len = 1
                for result in reversed(results[:-1]):
                    if result == streak_type:
                        streak_len += 1
                    else:
                        break
                current_streak = f"{streak_type}{streak_len}"
            else:
                current_streak = "N/A"

            # Update team_stats
            cursor.execute("""
                UPDATE team_stats
                SET last_10_record = ?,
                    current_streak = ?
                WHERE team_id = ? AND season_id = ?
            """, (last_10_record, current_streak, team_id, season_id))

        logger.info(f"Calculated recent form for {len(teams)} teams")


def main():
    """Example usage of the AdvancedMetricsCalculator"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 advanced_metrics.py <database_path> [season_id]")
        print("\nExample:")
        print("  python3 advanced_metrics.py output/hockey_stats.db 10776")
        print("\nNote: Run stats_calculator.py first to populate team_stats table")
        sys.exit(1)

    db_path = sys.argv[1]
    season_id = sys.argv[2] if len(sys.argv) > 2 else "10776"

    print(f"Calculating advanced metrics for database: {db_path}")
    print(f"Season ID: {season_id}")
    print()

    calculator = AdvancedMetricsCalculator(db_path)
    calculator.calculate_all_advanced_metrics(season_id)

    print("\n✅ Advanced metrics calculation complete!")
    print(f"   Database: {db_path}")
    print(f"   Tables updated: strength_of_schedule, head_to_head, team_stats")


if __name__ == "__main__":
    main()
