#!/usr/bin/env python3
"""
Advanced Stats Data Importer
Imports data from GameSheet API into advanced stats database
Based on ultimate_hockey_stats_extractor.py and GAMESHEET_API_DOCUMENTATION.md
"""

import requests
import sqlite3
import time
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from advanced_stats_database import AdvancedStatsDatabase
from advanced_metrics import AdvancedMetricsCalculator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataImporter:
    """
    Import data from GameSheet API into advanced stats database.

    This class fetches data from the GameSheet API and transforms it
    into the normalized database schema defined in advanced_stats_database.py
    """

    def __init__(self, db: AdvancedStatsDatabase, season_id: str):
        """
        Initialize data importer.

        Args:
            db: Database instance
            season_id: GameSheet season ID (e.g., "10776")
        """
        self.db = db
        self.season_id = season_id
        self.session = requests.Session()
        self.extraction_timestamp = datetime.now()

        # Statistics tracking
        self.stats = {
            'games_imported': 0,
            'goals_imported': 0,
            'penalties_imported': 0,
            'rosters_imported': 0,
            'api_calls': 0,
            'api_errors': 0,
            'duplicates_skipped': 0
        }

    def import_all(self, division_ids: Optional[List[int]] = None):
        """
        Import all data for the season.

        Args:
            division_ids: Optional list of specific division IDs to import.
                         If None, imports all divisions.

        Steps:
            1. Import divisions and teams
            2. Import schedule (games)
            3. Import box scores (goals, penalties, rosters)
            4. Calculate basic player and team stats
        """
        logger.info(f"Starting data import for season {self.season_id}")

        # Step 1: Import divisions
        divisions = self._import_divisions()
        if not divisions:
            logger.error("No divisions found")
            return

        # Filter divisions if specified
        if division_ids:
            divisions = [d for d in divisions if d['division_id'] in division_ids]
            logger.info(f"Filtering to {len(divisions)} specified divisions")

        # Step 2: Import teams from standings
        self._import_teams_from_standings(divisions)

        # Step 3: Import schedule for all divisions
        all_games = []
        for division in divisions:
            games = self._import_division_schedule(division['division_id'])
            all_games.extend(games)

        logger.info(f"Imported {len(all_games)} games from schedule")

        # Step 4: Import box scores for completed games
        # Get completed games from database
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT game_id
            FROM games
            WHERE season_id = ? AND status = 'final'
        ''', (self.season_id,))
        completed_game_ids = [row[0] for row in cursor.fetchall()]
        logger.info(f"Found {len(completed_game_ids)} completed games to process")

        self._import_box_scores(completed_game_ids)

        # Step 5: Calculate basic stats
        self._calculate_basic_stats()

        # Commit all changes
        self.db.conn.commit()

        logger.info("Data import complete!")
        self._print_statistics()

    def _import_divisions(self) -> List[Dict]:
        """
        Import divisions from API.

        Returns:
            List of division dictionaries
        """
        logger.info("Importing divisions...")

        url = f"https://gamesheetstats.com/api/useSeasonDivisions/getDivisions/{self.season_id}"
        self.stats['api_calls'] += 1

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            divisions_data = response.json()

            cursor = self.db.conn.cursor()
            imported = []

            for div in divisions_data:
                division_id = div.get('id')
                division_name = div.get('title', 'Unknown')

                cursor.execute('''
                    INSERT OR REPLACE INTO divisions
                    (division_id, division_name, season_id, assist_value, goal_value, max_goal_differential)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    division_id,
                    division_name,
                    self.season_id,
                    div.get('assistValue', 1),
                    div.get('goalValue', 1),
                    div.get('maxGoalDifferential')
                ))

                imported.append({
                    'division_id': division_id,
                    'division_name': division_name
                })

            self.db.conn.commit()
            logger.info(f"Imported {len(imported)} divisions")
            return imported

        except Exception as e:
            logger.error(f"Error importing divisions: {e}")
            self.stats['api_errors'] += 1
            return []

    def _import_teams_from_standings(self, divisions: List[Dict]):
        """
        Import teams from division standings API.

        Args:
            divisions: List of division dictionaries
        """
        logger.info("Importing teams from standings...")

        division_ids = ','.join(str(d['division_id']) for d in divisions)
        url = f"https://gamesheetstats.com/api/useStandings/getDivisionStandings/{self.season_id}"
        params = {
            'filter[divisions]': division_ids,
            'filter[limit]': 100,
            'filter[offset]': 0,
            'filter[timeZoneOffset]': -240
        }

        self.stats['api_calls'] += 1

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            standings_data = response.json()

            cursor = self.db.conn.cursor()
            teams_imported = 0

            for division_data in standings_data:
                division_id = division_data.get('id')
                division_name = division_data.get('title')
                table_data = division_data.get('tableData', {})

                team_ids = table_data.get('teamIds', [])
                team_titles = table_data.get('teamTitles', [])
                team_logos = table_data.get('teamLogos', [])

                for i, team_id in enumerate(team_ids):
                    team_name = team_titles[i].get('title') if i < len(team_titles) else None
                    logo_url = team_logos[i] if i < len(team_logos) else None

                    if team_name:
                        cursor.execute('''
                            INSERT OR REPLACE INTO teams
                            (team_id, season_id, team_name, division_id, division_name, logo_url, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            team_id,
                            self.season_id,
                            team_name,
                            division_id,
                            division_name,
                            logo_url,
                            self.extraction_timestamp
                        ))
                        teams_imported += 1

            self.db.conn.commit()
            logger.info(f"Imported {teams_imported} teams")

        except Exception as e:
            logger.error(f"Error importing teams: {e}")
            self.stats['api_errors'] += 1

    def _import_division_schedule(self, division_id: int) -> List[Tuple]:
        """
        Import schedule for a division.

        Args:
            division_id: Division ID

        Returns:
            List of game tuples for batch insertion
        """
        logger.info(f"Importing schedule for division {division_id}...")

        all_games = []
        offset = 0
        limit = 100

        while True:
            url = f"https://gamesheetstats.com/api/useSchedule/getSeasonSchedule/{self.season_id}"
            params = {
                'filter[divisions]': str(division_id),
                'filter[gametype]': 'overall',
                'filter[limit]': limit,
                'filter[offset]': offset,
                'filter[timeZoneOffset]': -240
            }

            self.stats['api_calls'] += 1

            try:
                response = self.session.get(url, params=params, timeout=15)
                if response.status_code != 200:
                    break

                batch_data = response.json()
                if not batch_data:
                    break

                batch_games = self._parse_schedule_response(batch_data, division_id)
                all_games.extend(batch_games)

                if len(batch_games) < limit:
                    break

                offset += limit

                # Safety limit
                if offset > 5000:
                    break

                # Be respectful to API
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error importing schedule at offset {offset}: {e}")
                self.stats['api_errors'] += 1
                break

        # Batch insert games
        if all_games:
            cursor = self.db.conn.cursor()
            cursor.executemany('''
                INSERT OR REPLACE INTO games
                (game_id, season_id, division_id, division_name, game_number, game_type,
                 date, time, location, status, home_team_id, home_team_name,
                 visitor_team_id, visitor_team_name, extraction_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', all_games)
            self.db.conn.commit()

        logger.info(f"Imported {len(all_games)} games for division {division_id}")
        return all_games

    def _parse_schedule_response(self, schedule_data: Dict, division_id: int) -> List[Tuple]:
        """
        Parse schedule API response into game tuples.

        Args:
            schedule_data: Raw API response
            division_id: Division ID

        Returns:
            List of game tuples
        """
        games = []

        # Get division name from database
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT division_name FROM divisions WHERE division_id = ?', (division_id,))
        row = cursor.fetchone()
        division_name = row[0] if row else 'Unknown'

        for date_key, daily_games in schedule_data.items():
            if isinstance(daily_games, list):
                for day_data in daily_games:
                    if isinstance(day_data, dict):
                        games_list = day_data.get('games', [])

                        for game in games_list:
                            game_id = game.get('id')
                            if not game_id:
                                continue

                            home_team = game.get('homeTeam', {})
                            visitor_team = game.get('visitorTeam', {})

                            game_tuple = (
                                game_id,
                                self.season_id,
                                division_id,
                                division_name,
                                game.get('number'),
                                game.get('type', 'Regular Season'),
                                game.get('date'),
                                game.get('time'),
                                game.get('location'),
                                game.get('status', 'scheduled').lower(),
                                home_team.get('id'),
                                home_team.get('name'),
                                visitor_team.get('id'),
                                visitor_team.get('name'),
                                self.extraction_timestamp
                            )
                            games.append(game_tuple)

        return games

    def _import_box_scores(self, completed_game_ids: List[str]):
        """
        Import box scores using async concurrent fetching.

        Fetches box scores in parallel chunks using aiohttp, then inserts
        results into SQLite sequentially. This separates network I/O
        (parallelizable) from database I/O (must be sequential for SQLite).

        Args:
            completed_game_ids: List of completed game IDs
        """
        total = len(completed_game_ids)
        concurrency = 20
        chunk_size = 500
        logger.info(f"Importing box scores for {total} games (async, {concurrency} concurrent)...")

        for chunk_start in range(0, total, chunk_size):
            chunk = completed_game_ids[chunk_start:chunk_start + chunk_size]
            chunk_num = chunk_start // chunk_size + 1
            total_chunks = (total + chunk_size - 1) // chunk_size
            logger.info(f"Chunk {chunk_num}/{total_chunks}: Fetching {len(chunk)} box scores...")

            # Phase 1: Async fetch this chunk from API
            start_time = time.time()
            results = asyncio.run(self._fetch_box_scores_async(chunk, concurrency))
            fetch_time = time.time() - start_time

            fetched = sum(1 for _, data in results if data is not None)
            logger.info(f"Chunk {chunk_num}: Fetched {fetched}/{len(chunk)} in {fetch_time:.1f}s")

            # Phase 2: Insert into database sequentially
            for game_id, box_score in results:
                if box_score is None:
                    continue
                self._process_box_score(game_id, box_score)

            self.db.conn.commit()

        logger.info("Box score import complete")

    async def _fetch_box_scores_async(self, game_ids: List[str], concurrency: int = 20) -> List[tuple]:
        """
        Fetch box scores concurrently using aiohttp.

        Args:
            game_ids: List of game IDs to fetch
            concurrency: Max concurrent requests

        Returns:
            List of (game_id, box_score_json_or_None) tuples
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_one(session, game_id):
            url = f"https://gamesheetstats.com/api/useBoxScore/getGameStats/{self.season_id}/games/{game_id}"
            async with semaphore:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return (game_id, data)
                        else:
                            return (game_id, None)
                except Exception as e:
                    logger.error(f"Error fetching box score {game_id}: {e}")
                    return (game_id, None)

        connector = aiohttp.TCPConnector(limit=concurrency, limit_per_host=concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [fetch_one(session, gid) for gid in game_ids]
            results = await asyncio.gather(*tasks)

        return list(results)

    def _process_box_score(self, game_id: str, box_score: Dict):
        """
        Process a fetched box score — insert goals, penalties, rosters into DB.

        Args:
            game_id: Game ID
            box_score: Parsed JSON box score data
        """
        try:
            self._update_game_scores(game_id, box_score)
            self._import_goals(game_id, box_score)
            self._import_penalties(game_id, box_score)
            self._import_rosters(game_id, box_score)
            self.stats['games_imported'] += 1
            self.stats['api_calls'] += 1
        except Exception as e:
            logger.error(f"Error processing box score for game {game_id}: {e}")
            self.stats['api_errors'] += 1

    def _update_game_scores(self, game_id: str, box_score: Dict):
        """Update game with final scores from box score"""
        cursor = self.db.conn.cursor()

        home_score = self._safe_int(box_score.get('home', {}).get('finalScore'))
        visitor_score = self._safe_int(box_score.get('visitor', {}).get('finalScore'))

        cursor.execute('''
            UPDATE games
            SET home_score = ?, visitor_score = ?
            WHERE game_id = ?
        ''', (home_score, visitor_score, game_id))

    def _import_goals(self, game_id: str, box_score: Dict):
        """Import goals from box score"""
        cursor = self.db.conn.cursor()

        # Get home/visitor team IDs for is_home_team flag
        home_team_id = box_score.get('home', {}).get('id')
        visitor_team_id = box_score.get('visitor', {}).get('id')

        tables = box_score.get('tables', {})
        goals_by_period = tables.get('goalsByPeriod', [])

        for period_data in goals_by_period:
            period = period_data.get('period')
            period_number = self._parse_period_number(period)

            for event in period_data.get('periodEvents', []):
                if event.get('eventType') != 'goal':
                    continue

                team = event.get('team', {})
                team_id = team.get('id')
                is_home_team = (team_id == home_team_id)

                scorer = event.get('goalScorer', {})
                assist1 = event.get('assist1By', {})
                assist2 = event.get('assist2By', {})

                time_remaining = event.get('time')
                game_time_seconds = self._calculate_game_time_seconds(period_number, time_remaining)

                cursor.execute('''
                    INSERT INTO goals
                    (game_id, period, period_number, time_remaining, game_time_seconds,
                     team_id, team_name, is_home_team,
                     scorer_player_id, scorer_number, scorer_name, scorer_total_goals,
                     assist1_player_id, assist1_number, assist1_name, assist1_total_goals,
                     assist2_player_id, assist2_number, assist2_name, assist2_total_goals,
                     is_power_play, is_short_handed, is_game_winning, is_empty_net)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_id,
                    period,
                    period_number,
                    time_remaining,
                    game_time_seconds,
                    team_id,
                    team.get('title'),
                    is_home_team,
                    scorer.get('id'),
                    scorer.get('number'),
                    scorer.get('title'),
                    self._safe_int(scorer.get('totalGoalCount')),
                    assist1.get('id'),
                    assist1.get('number'),
                    assist1.get('title'),
                    self._safe_int(assist1.get('totalGoalCount')),
                    assist2.get('id'),
                    assist2.get('number'),
                    assist2.get('title'),
                    self._safe_int(assist2.get('totalGoalCount')),
                    event.get('powerPlay', False),
                    event.get('shg', False),
                    event.get('gameWinningGoal', False),
                    event.get('en', False)
                ))

                self.stats['goals_imported'] += 1

    def _import_penalties(self, game_id: str, box_score: Dict):
        """Import penalties from box score"""
        cursor = self.db.conn.cursor()

        home_team_id = box_score.get('home', {}).get('id')

        tables = box_score.get('tables', {})
        penalties_by_period = tables.get('penaltiesByPeriod', [])

        for period_data in penalties_by_period:
            period = period_data.get('period')
            period_number = self._parse_period_number(period)

            for event in period_data.get('periodEvents', []):
                if event.get('eventType') != 'penalty':
                    continue

                team = event.get('team', {})
                team_id = team.get('id')
                is_home_team = (team_id == home_team_id)

                committed_by = event.get('commitedBy', {})
                served_by = event.get('servedBy', {})
                penalty_type = event.get('penaltyType', {})

                time_remaining = event.get('time')
                game_time_seconds = self._calculate_game_time_seconds(period_number, time_remaining)

                cursor.execute('''
                    INSERT INTO penalties
                    (game_id, period, period_number, time_remaining, game_time_seconds,
                     team_id, team_name, is_home_team,
                     player_id, player_number, player_name,
                     penalty_type, penalty_class, duration_minutes, is_major,
                     served_by_player_id, served_by_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_id,
                    period,
                    period_number,
                    time_remaining,
                    game_time_seconds,
                    team_id,
                    team.get('title'),
                    is_home_team,
                    committed_by.get('id'),
                    committed_by.get('number'),
                    committed_by.get('title'),
                    penalty_type.get('title'),
                    penalty_type.get('class'),
                    self._safe_int(penalty_type.get('duration')),
                    event.get('major', False),
                    served_by.get('id'),
                    served_by.get('number')
                ))

                self.stats['penalties_imported'] += 1

    def _import_rosters(self, game_id: str, box_score: Dict):
        """Import rosters from box score"""
        cursor = self.db.conn.cursor()

        for team_type in ['home', 'visitor']:
            team_data = box_score.get(team_type, {})
            team_id = team_data.get('id')
            team_name = team_data.get('title')

            roster = team_data.get('roster', {})
            players = roster.get('players', [])

            for player in players:
                player_id = player.get('id')
                if not player_id:
                    continue

                season_stats = player.get('season', {})

                cursor.execute('''
                    INSERT OR REPLACE INTO game_rosters
                    (game_id, team_id, team_name, player_id, player_number,
                     first_name, last_name, position, status, is_starting,
                     is_affiliated, added_at_game_time,
                     goals, assists, points, pim, yellow_cards, red_cards,
                     goals_against, shots_against, save_pct, time_on_ice,
                     season_goals_before, season_assists_before)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_id,
                    team_id,
                    team_name,
                    player_id,
                    player.get('number'),
                    player.get('firstName'),
                    player.get('lastName'),
                    player.get('position'),
                    player.get('status', 'playing'),
                    player.get('starting', False),
                    player.get('affiliated', False),
                    player.get('added_at_game_time', False),
                    self._safe_int(player.get('g')),
                    self._safe_int(player.get('a')),
                    self._safe_int(player.get('pts')),
                    self._safe_int(player.get('pim')),
                    self._safe_int(player.get('yc')),
                    self._safe_int(player.get('rc')),
                    self._safe_int(player.get('ga')),
                    self._safe_int(player.get('sa')),
                    player.get('svpct'),
                    player.get('toi'),
                    self._safe_int(season_stats.get('goals')),
                    self._safe_int(season_stats.get('assists'))
                ))

                self.stats['rosters_imported'] += 1

    def _calculate_basic_stats(self):
        """Calculate basic player and team statistics from raw data"""
        logger.info("Calculating basic statistics...")

        self._calculate_player_stats()
        self._calculate_team_stats()

        # Commit and release connection before advanced metrics opens its own
        self.db.conn.commit()

        # Calculate advanced metrics (SOS, SOV, H2H, etc.)
        logger.info("Calculating advanced metrics...")
        try:
            self.db.conn.close()
            metrics_calc = AdvancedMetricsCalculator(self.db.db_path)
            metrics_calc.calculate_all_advanced_metrics(self.season_id)
            logger.info("Advanced metrics calculated")
        except Exception as e:
            logger.warning(f"Advanced metrics calculation failed: {e}")
            logger.warning("Continuing without advanced metrics...")
        finally:
            import sqlite3
            self.db.conn = sqlite3.connect(self.db.db_path)
            self.db.conn.row_factory = sqlite3.Row
        logger.info("Basic statistics calculated")

    def _calculate_player_stats(self):
        """Calculate player statistics from goals, penalties, and rosters"""
        cursor = self.db.conn.cursor()

        # Clear existing stats
        cursor.execute('DELETE FROM player_stats WHERE season_id = ?', (self.season_id,))

        # Aggregate from goals (scorers)
        cursor.execute('''
            INSERT OR IGNORE INTO player_stats
            (player_id, team_id, season_id, player_number, player_name)
            SELECT DISTINCT
                scorer_player_id,
                team_id,
                ?,
                scorer_number,
                scorer_name
            FROM goals
            JOIN games ON goals.game_id = games.game_id
            WHERE scorer_player_id IS NOT NULL
            AND games.season_id = ?
        ''', (self.season_id, self.season_id))

        # Update goals
        cursor.execute('''
            UPDATE player_stats
            SET goals = (
                SELECT COUNT(*)
                FROM goals
                JOIN games ON goals.game_id = games.game_id
                WHERE goals.scorer_player_id = player_stats.player_id
                AND games.season_id = ?
            )
            WHERE season_id = ?
        ''', (self.season_id, self.season_id))

        # Update power play goals
        cursor.execute('''
            UPDATE player_stats
            SET power_play_goals = (
                SELECT COUNT(*)
                FROM goals
                JOIN games ON goals.game_id = games.game_id
                WHERE goals.scorer_player_id = player_stats.player_id
                AND goals.is_power_play = 1
                AND games.season_id = ?
            )
            WHERE season_id = ?
        ''', (self.season_id, self.season_id))

        # Update short handed goals
        cursor.execute('''
            UPDATE player_stats
            SET short_handed_goals = (
                SELECT COUNT(*)
                FROM goals
                JOIN games ON goals.game_id = games.game_id
                WHERE goals.scorer_player_id = player_stats.player_id
                AND goals.is_short_handed = 1
                AND games.season_id = ?
            )
            WHERE season_id = ?
        ''', (self.season_id, self.season_id))

        # Update game winning goals
        cursor.execute('''
            UPDATE player_stats
            SET game_winning_goals = (
                SELECT COUNT(*)
                FROM goals
                JOIN games ON goals.game_id = games.game_id
                WHERE goals.scorer_player_id = player_stats.player_id
                AND goals.is_game_winning = 1
                AND games.season_id = ?
            )
            WHERE season_id = ?
        ''', (self.season_id, self.season_id))

        # Update penalty stats
        cursor.execute('''
            UPDATE player_stats
            SET
                penalties = (
                    SELECT COUNT(*)
                    FROM penalties
                    JOIN games ON penalties.game_id = games.game_id
                    WHERE penalties.player_id = player_stats.player_id
                    AND games.season_id = ?
                ),
                penalty_minutes = (
                    SELECT COALESCE(SUM(duration_minutes), 0)
                    FROM penalties
                    JOIN games ON penalties.game_id = games.game_id
                    WHERE penalties.player_id = player_stats.player_id
                    AND games.season_id = ?
                )
            WHERE season_id = ?
        ''', (self.season_id, self.season_id, self.season_id))

        # Update games played from rosters
        cursor.execute('''
            UPDATE player_stats
            SET games_played = (
                SELECT COUNT(DISTINCT game_rosters.game_id)
                FROM game_rosters
                JOIN games ON game_rosters.game_id = games.game_id
                WHERE game_rosters.player_id = player_stats.player_id
                AND games.season_id = ?
            )
            WHERE season_id = ?
        ''', (self.season_id, self.season_id))

        # Calculate points per game
        cursor.execute('''
            UPDATE player_stats
            SET
                points = goals,
                points_per_game = CAST(goals AS REAL) / NULLIF(games_played, 0),
                pim_per_game = CAST(penalty_minutes AS REAL) / NULLIF(games_played, 0)
            WHERE season_id = ?
        ''', (self.season_id,))

        logger.info("Player statistics calculated")

    def _calculate_team_stats(self):
        """Calculate team statistics from games"""
        cursor = self.db.conn.cursor()

        # Clear existing stats
        cursor.execute('DELETE FROM team_stats WHERE season_id = ?', (self.season_id,))

        # Get all teams
        cursor.execute('''
            SELECT DISTINCT team_id, division_id
            FROM teams
            WHERE team_id IN (
                SELECT home_team_id FROM games WHERE season_id = ?
                UNION
                SELECT visitor_team_id FROM games WHERE season_id = ?
            )
        ''', (self.season_id, self.season_id))

        teams = cursor.fetchall()

        for team_id, division_id in teams:
            # Calculate record
            cursor.execute('''
                SELECT
                    COUNT(*) as games_played,
                    SUM(CASE
                        WHEN (home_team_id = ? AND home_score > visitor_score)
                          OR (visitor_team_id = ? AND visitor_score > home_score)
                        THEN 1 ELSE 0 END) as wins,
                    SUM(CASE
                        WHEN (home_team_id = ? AND home_score < visitor_score)
                          OR (visitor_team_id = ? AND visitor_score < home_score)
                        THEN 1 ELSE 0 END) as losses,
                    SUM(CASE
                        WHEN home_score = visitor_score
                        THEN 1 ELSE 0 END) as ties,
                    SUM(CASE WHEN home_team_id = ? THEN home_score ELSE visitor_score END) as goals_for,
                    SUM(CASE WHEN home_team_id = ? THEN visitor_score ELSE home_score END) as goals_against
                FROM games
                WHERE season_id = ?
                AND status = 'final'
                AND (home_team_id = ? OR visitor_team_id = ?)
            ''', (team_id, team_id, team_id, team_id, team_id, team_id,
                  self.season_id, team_id, team_id))

            stats = cursor.fetchone()

            if stats and stats[0] > 0:  # games_played > 0
                games_played, wins, losses, ties, goals_for, goals_against = stats

                # Handle None values
                wins = wins or 0
                losses = losses or 0
                ties = ties or 0
                goals_for = goals_for or 0
                goals_against = goals_against or 0

                # Calculate points (2 for win, 1 for tie)
                points = (wins * 2) + (ties * 1)
                points_pct = points / (games_played * 2) if games_played > 0 else 0.0
                goal_differential = goals_for - goals_against

                cursor.execute('''
                    INSERT INTO team_stats
                    (team_id, season_id, division_id, games_played, wins, losses, ties,
                     points, points_pct, row, goals_for, goals_against, goal_differential,
                     goals_per_game, goals_against_per_game)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    team_id,
                    self.season_id,
                    division_id,
                    games_played,
                    wins,
                    losses,
                    ties,
                    points,
                    points_pct,
                    wins,  # ROW = wins for now (would need OT/SO tracking for accuracy)
                    goals_for,
                    goals_against,
                    goal_differential,
                    goals_for / games_played if games_played > 0 else 0.0,
                    goals_against / games_played if games_played > 0 else 0.0
                ))

        logger.info(f"Team statistics calculated for {len(teams)} teams")

    def _parse_period_number(self, period_str: str) -> int:
        """Parse period string to number"""
        if not period_str:
            return 0

        period_lower = period_str.lower()
        if '1st' in period_lower or 'first' in period_lower:
            return 1
        elif '2nd' in period_lower or 'second' in period_lower:
            return 2
        elif '3rd' in period_lower or 'third' in period_lower:
            return 3
        elif 'ot' in period_lower or 'overtime' in period_lower:
            return 4
        else:
            return 0

    def _calculate_game_time_seconds(self, period_number: int, time_remaining: str) -> Optional[int]:
        """
        Calculate game time in seconds.

        Args:
            period_number: Period number (1, 2, 3, 4=OT)
            time_remaining: Time remaining in period (MM:SS format)

        Returns:
            Game time in seconds from start of game
        """
        if not time_remaining or period_number == 0:
            return None

        try:
            parts = time_remaining.split(':')
            if len(parts) != 2:
                return None

            minutes = int(parts[0])
            seconds = int(parts[1])

            # Assuming 13-minute periods (common in youth hockey)
            period_length = 13 * 60  # 780 seconds

            # Calculate elapsed time in current period
            elapsed_in_period = period_length - (minutes * 60 + seconds)

            # Calculate total game time
            game_time = ((period_number - 1) * period_length) + elapsed_in_period

            return game_time

        except (ValueError, IndexError):
            return None

    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int"""
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def fetch_gamesheet_rosters(self, division_filter: List[str] = None):
        """
        Fetch rosters from GameSheet API for divisions with public names.

        This uses the /useTeamRoster/getPlayerStandings endpoint which returns
        player names when isPlayerStatsPrivate is false (typically U15+ National
        divisions in EHF).

        Args:
            division_filter: List of division name patterns to filter (e.g., ['National'])
                           If None, attempts to fetch all teams (but privacy-enabled
                           divisions will return empty data)
        """
        logger.info(f"Fetching GameSheet rosters for season {self.season_id}")

        cursor = self.db.conn.cursor()

        # Get teams from database, optionally filtered by division name
        if division_filter:
            placeholders = ' OR '.join(['division_name LIKE ?' for _ in division_filter])
            patterns = [f'%{p}%' for p in division_filter]
            cursor.execute(f'''
                SELECT team_id, team_name, division_name
                FROM teams
                WHERE season_id = ? AND ({placeholders})
                ORDER BY division_name, team_name
            ''', [self.season_id] + patterns)
        else:
            cursor.execute('''
                SELECT team_id, team_name, division_name
                FROM teams
                WHERE season_id = ?
                ORDER BY division_name, team_name
            ''', (self.season_id,))

        teams = cursor.fetchall()
        logger.info(f"Found {len(teams)} teams to fetch rosters for")

        players_imported = 0
        coaches_imported = 0
        teams_with_data = 0

        for team_id, team_name, division_name in teams:
            url = f"https://gamesheetstats.com/api/useTeamRoster/getPlayerStandings/{self.season_id}/players/{team_id}"
            params = {'filter[limit]': 100}

            self.stats['api_calls'] += 1

            try:
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()

                player_data = data.get('playerData', {})
                goalie_data = data.get('goalieData', {})
                coach_data = data.get('coachData', {})

                # Check if we got any data
                names = player_data.get('names', [])
                goalie_names = goalie_data.get('names', [])

                if not names and not goalie_names:
                    # Privacy enabled - skip silently
                    continue

                teams_with_data += 1
                logger.info(f"  {team_name}: {len(names)} players, {len(goalie_names)} goalies")

                # Import players
                for i, name_obj in enumerate(names):
                    player_id = str(player_data.get('ids', [])[i]) if i < len(player_data.get('ids', [])) else None
                    if not player_id:
                        continue

                    cursor.execute('''
                        INSERT OR REPLACE INTO gamesheet_rosters
                        (season_id, team_id, player_id, first_name, last_name, jersey_number,
                         position, gp, goals, assists, points, pim, ppg, shg, gwg,
                         photo_url, birthdate, height, weight, shot_hand, hometown, is_goalie)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ''', (
                        self.season_id,
                        team_id,
                        player_id,
                        name_obj.get('firstName', ''),
                        name_obj.get('lastName', ''),
                        player_data.get('jersey', [])[i] if i < len(player_data.get('jersey', [])) else None,
                        ','.join(player_data.get('positions', [[]])[i]) if i < len(player_data.get('positions', [])) else None,
                        player_data.get('gp', [])[i] if i < len(player_data.get('gp', [])) else 0,
                        player_data.get('g', [])[i] if i < len(player_data.get('g', [])) else 0,
                        player_data.get('a', [])[i] if i < len(player_data.get('a', [])) else 0,
                        player_data.get('pts', [])[i] if i < len(player_data.get('pts', [])) else 0,
                        player_data.get('pim', [])[i] if i < len(player_data.get('pim', [])) else 0,
                        player_data.get('ppg', [])[i] if i < len(player_data.get('ppg', [])) else 0,
                        player_data.get('shg', [])[i] if i < len(player_data.get('shg', [])) else 0,
                        player_data.get('gwg', [])[i] if i < len(player_data.get('gwg', [])) else 0,
                        name_obj.get('photo'),
                        player_data.get('birthdate', [])[i] if i < len(player_data.get('birthdate', [])) else None,
                        player_data.get('height', [])[i] if i < len(player_data.get('height', [])) else None,
                        player_data.get('weight', [])[i] if i < len(player_data.get('weight', [])) else None,
                        player_data.get('shotHand', [])[i] if i < len(player_data.get('shotHand', [])) else None,
                        player_data.get('hometown', [])[i] if i < len(player_data.get('hometown', [])) else None,
                    ))
                    players_imported += 1

                # Import goalies (same structure, different source)
                for i, name_obj in enumerate(goalie_names):
                    goalie_id = str(goalie_data.get('ids', [])[i]) if i < len(goalie_data.get('ids', [])) else None
                    if not goalie_id:
                        continue

                    cursor.execute('''
                        INSERT OR REPLACE INTO gamesheet_rosters
                        (season_id, team_id, player_id, first_name, last_name, jersey_number,
                         position, gp, goals, assists, points, pim, is_goalie)
                        VALUES (?, ?, ?, ?, ?, ?, 'goalie', ?, ?, ?, ?, ?, 1)
                    ''', (
                        self.season_id,
                        team_id,
                        goalie_id,
                        name_obj.get('firstName', ''),
                        name_obj.get('lastName', ''),
                        goalie_data.get('jersey', [])[i] if i < len(goalie_data.get('jersey', [])) else None,
                        goalie_data.get('gp', [])[i] if i < len(goalie_data.get('gp', [])) else 0,
                        goalie_data.get('g', [])[i] if i < len(goalie_data.get('g', [])) else 0,
                        goalie_data.get('a', [])[i] if i < len(goalie_data.get('a', [])) else 0,
                        goalie_data.get('pts', [])[i] if i < len(goalie_data.get('pts', [])) else 0,
                        goalie_data.get('pim', [])[i] if i < len(goalie_data.get('pim', [])) else 0,
                    ))
                    players_imported += 1

                # Import coaches
                coach_names = coach_data.get('names', [])
                coach_positions = coach_data.get('positions', [])
                for i, name_obj in enumerate(coach_names):
                    cursor.execute('''
                        INSERT OR REPLACE INTO gamesheet_coaches
                        (season_id, team_id, first_name, last_name, position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        self.season_id,
                        team_id,
                        name_obj.get('firstName', ''),
                        name_obj.get('lastName', ''),
                        coach_positions[i] if i < len(coach_positions) else 'unknown',
                    ))
                    coaches_imported += 1

                # Rate limit
                time.sleep(0.2)

            except Exception as e:
                logger.warning(f"Error fetching roster for {team_name}: {e}")
                self.stats['api_errors'] += 1

        self.db.conn.commit()
        logger.info(f"Roster import complete: {players_imported} players, {coaches_imported} coaches from {teams_with_data} teams")

        # Backfill names into existing tables
        if players_imported > 0:
            self._backfill_names_from_rosters()

    def _backfill_names_from_rosters(self):
        """Propagate names from gamesheet_rosters into game_rosters, goals, penalties, player_stats"""
        cursor = self.db.conn.cursor()

        # Update game_rosters
        cursor.execute('''
            UPDATE game_rosters
            SET first_name = gr.first_name, last_name = gr.last_name
            FROM gamesheet_rosters gr
            WHERE game_rosters.player_id = gr.player_id
              AND (game_rosters.first_name = '' OR game_rosters.first_name = ' ' OR game_rosters.first_name IS NULL)
        ''')
        rosters_updated = cursor.rowcount
        logger.info(f"  Updated {rosters_updated} game_rosters entries with names")

        # Update player_stats
        cursor.execute('''
            UPDATE player_stats
            SET player_name = gr.first_name || ' ' || gr.last_name
            FROM gamesheet_rosters gr
            WHERE player_stats.player_id = gr.player_id
              AND (player_stats.player_name = '' OR player_stats.player_name IS NULL)
        ''')
        stats_updated = cursor.rowcount
        logger.info(f"  Updated {stats_updated} player_stats entries with names")

        # Update goals - scorer
        cursor.execute('''
            UPDATE goals
            SET scorer_name = gr.first_name || ' ' || gr.last_name
            FROM gamesheet_rosters gr
            WHERE goals.scorer_player_id = gr.player_id
              AND (goals.scorer_name = '' OR goals.scorer_name IS NULL)
        ''')
        scorers_updated = cursor.rowcount

        # Update goals - assist1
        cursor.execute('''
            UPDATE goals
            SET assist1_name = gr.first_name || ' ' || gr.last_name
            FROM gamesheet_rosters gr
            WHERE goals.assist1_player_id = gr.player_id
              AND (goals.assist1_name = '' OR goals.assist1_name IS NULL)
        ''')
        assist1_updated = cursor.rowcount

        # Update goals - assist2
        cursor.execute('''
            UPDATE goals
            SET assist2_name = gr.first_name || ' ' || gr.last_name
            FROM gamesheet_rosters gr
            WHERE goals.assist2_player_id = gr.player_id
              AND (goals.assist2_name = '' OR goals.assist2_name IS NULL)
        ''')
        assist2_updated = cursor.rowcount
        logger.info(f"  Updated {scorers_updated} scorers, {assist1_updated} assist1, {assist2_updated} assist2 in goals")

        # Update penalties
        cursor.execute('''
            UPDATE penalties
            SET player_name = gr.first_name || ' ' || gr.last_name
            FROM gamesheet_rosters gr
            WHERE penalties.player_id = gr.player_id
              AND (penalties.player_name = '' OR penalties.player_name IS NULL)
        ''')
        penalties_updated = cursor.rowcount
        logger.info(f"  Updated {penalties_updated} penalties entries with names")

        self.db.conn.commit()

    def _print_statistics(self):
        """Print import statistics"""
        logger.info("\n" + "=" * 60)
        logger.info("IMPORT STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Games imported:      {self.stats['games_imported']}")
        logger.info(f"Goals imported:      {self.stats['goals_imported']}")
        logger.info(f"Penalties imported:  {self.stats['penalties_imported']}")
        logger.info(f"Rosters imported:    {self.stats['rosters_imported']}")
        logger.info(f"API calls made:      {self.stats['api_calls']}")
        logger.info(f"API errors:          {self.stats['api_errors']}")
        logger.info("=" * 60)

        # Get database stats
        db_stats = self.db.get_stats()
        logger.info("\nDATABASE RECORD COUNTS")
        logger.info("=" * 60)
        for table, count in sorted(db_stats.items()):
            logger.info(f"{table:25} {count:6d}")
        logger.info("=" * 60)


def main():
    """CLI for data import operations"""
    import argparse
    from advanced_stats_database import AdvancedStatsDatabase

    parser = argparse.ArgumentParser(description='Import GameSheet data into hockey stats database')
    parser.add_argument('--db', default='hockey_stats.db', help='Path to SQLite database')
    parser.add_argument('--season', default='10776', help='GameSheet season ID')
    parser.add_argument('--fetch-rosters', action='store_true',
                        help='Fetch rosters from GameSheet API (for divisions with public names)')
    parser.add_argument('--roster-filter', nargs='+', default=['National'],
                        help='Division name patterns to filter roster fetch (default: National)')
    parser.add_argument('--import-all', action='store_true',
                        help='Run full import (divisions, teams, games, box scores)')
    parser.add_argument('--division-ids', nargs='+', type=int,
                        help='Specific division IDs to import')

    args = parser.parse_args()

    # Connect to database
    db = AdvancedStatsDatabase(args.db)
    db.connect()
    db.initialize_schema()

    try:
        importer = DataImporter(db, args.season)

        if args.fetch_rosters:
            logger.info(f"Fetching rosters for season {args.season} with filter: {args.roster_filter}")
            importer.fetch_gamesheet_rosters(division_filter=args.roster_filter)

        elif args.import_all:
            logger.info(f"Running full import for season {args.season}")
            importer.import_all(division_ids=args.division_ids)

        else:
            # Default: show help
            parser.print_help()

    finally:
        db.close()


if __name__ == "__main__":
    main()
