#!/usr/bin/env python3
"""
Advanced Stats Database Schema
Complete SQLite database schema for hockey stats system
Based on ADVANCED_STATS_API_DESIGN.md
"""

import sqlite3
from typing import Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedStatsDatabase:
    """
    Complete database schema for advanced hockey statistics.

    This class creates and manages the SQLite database with all tables
    for raw data, calculated stats, and data quality tracking.
    """

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Establish database connection with foreign key support"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        logger.info(f"Connected to database: {self.db_path}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def initialize_schema(self):
        """Create all database tables and indexes"""
        logger.info("Initializing database schema...")

        self._create_raw_data_tables()
        self._create_calculated_stats_tables()
        self._create_whk_tables()
        self._create_club_tables()
        self._create_gamesheet_roster_tables()
        self._create_logo_tables()
        self._create_indexes()

        self.conn.commit()
        logger.info("Database schema initialized successfully")

    def _create_raw_data_tables(self):
        """Create raw data tables (source of truth)"""
        cursor = self.conn.cursor()

        # GAMES table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                season_id TEXT NOT NULL,
                division_id INTEGER,
                division_name TEXT,
                game_number TEXT,
                game_type TEXT,
                date DATE,
                time TEXT,
                location TEXT,
                status TEXT,

                home_team_id INTEGER,
                home_team_name TEXT,
                visitor_team_id INTEGER,
                visitor_team_name TEXT,

                home_score INTEGER,
                visitor_score INTEGER,

                extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_quality_score REAL DEFAULT 1.0,

                CHECK (status IN ('scheduled', 'in_progress', 'final')),
                CHECK (data_quality_score >= 0.0 AND data_quality_score <= 1.0)
            )
        ''')

        # GOALS table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,

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
                assist1_total_goals INTEGER,

                assist2_player_id TEXT,
                assist2_number TEXT,
                assist2_name TEXT,
                assist2_total_goals INTEGER,

                is_power_play BOOLEAN DEFAULT FALSE,
                is_short_handed BOOLEAN DEFAULT FALSE,
                is_game_winning BOOLEAN DEFAULT FALSE,
                is_empty_net BOOLEAN DEFAULT FALSE,

                scorer_number_verified BOOLEAN DEFAULT FALSE,
                assist1_number_verified BOOLEAN DEFAULT FALSE,
                assist2_number_verified BOOLEAN DEFAULT FALSE,
                data_confidence REAL DEFAULT 1.0,

                CHECK (data_confidence >= 0.0 AND data_confidence <= 1.0)
            )
        ''')

        # PENALTIES table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS penalties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,

                period TEXT,
                period_number INTEGER,
                time_remaining TEXT,
                game_time_seconds INTEGER,

                team_id INTEGER,
                team_name TEXT,
                is_home_team BOOLEAN,

                player_id TEXT,
                player_number TEXT,
                player_name TEXT,

                penalty_type TEXT,
                penalty_class TEXT,
                duration_minutes INTEGER,
                is_major BOOLEAN DEFAULT FALSE,

                served_by_player_id TEXT,
                served_by_number TEXT,

                player_number_verified BOOLEAN DEFAULT FALSE,
                data_confidence REAL DEFAULT 1.0,

                CHECK (penalty_class IN ('minor', 'major', 'misconduct', 'game_misconduct', 'match', NULL)),
                CHECK (data_confidence >= 0.0 AND data_confidence <= 1.0)
            )
        ''')

        # GAME_ROSTERS table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_rosters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                team_id INTEGER,
                team_name TEXT,

                player_id TEXT NOT NULL,
                player_number TEXT,
                first_name TEXT,
                last_name TEXT,
                position TEXT,

                status TEXT DEFAULT 'playing',
                is_starting BOOLEAN DEFAULT FALSE,
                is_affiliated BOOLEAN DEFAULT FALSE,
                added_at_game_time BOOLEAN DEFAULT FALSE,

                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                pim INTEGER DEFAULT 0,
                yellow_cards INTEGER DEFAULT 0,
                red_cards INTEGER DEFAULT 0,

                goals_against INTEGER,
                shots_against INTEGER,
                save_pct REAL,
                time_on_ice TEXT,

                season_goals_before INTEGER,
                season_assists_before INTEGER,

                UNIQUE(game_id, team_id, player_id),
                CHECK (status IN ('playing', 'scratched', 'injured'))
            )
        ''')

        # TEAMS table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                team_id INTEGER,
                season_id TEXT,
                team_name TEXT NOT NULL,
                division_id INTEGER,
                division_name TEXT,
                logo_url TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_id, season_id)
            )
        ''')

        # DIVISIONS table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS divisions (
                division_id INTEGER PRIMARY KEY,
                division_name TEXT NOT NULL,
                season_id TEXT,
                assist_value INTEGER DEFAULT 1,
                goal_value INTEGER DEFAULT 1,
                max_goal_differential INTEGER
            )
        ''')

        logger.info("Raw data tables created")

    def _create_calculated_stats_tables(self):
        """Create calculated statistics tables"""
        cursor = self.conn.cursor()

        # PLAYER_STATS table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_stats (
                player_id TEXT,
                team_id INTEGER,
                season_id TEXT,

                player_number TEXT,
                player_name TEXT,
                position TEXT,

                games_played INTEGER DEFAULT 0,
                games_started INTEGER DEFAULT 0,

                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                points_per_game REAL DEFAULT 0.0,

                power_play_goals INTEGER DEFAULT 0,
                power_play_assists INTEGER DEFAULT 0,
                power_play_points INTEGER DEFAULT 0,
                short_handed_goals INTEGER DEFAULT 0,
                short_handed_assists INTEGER DEFAULT 0,
                short_handed_points INTEGER DEFAULT 0,
                game_winning_goals INTEGER DEFAULT 0,
                empty_net_goals INTEGER DEFAULT 0,

                penalties INTEGER DEFAULT 0,
                penalty_minutes INTEGER DEFAULT 0,
                pim_per_game REAL DEFAULT 0.0,
                major_penalties INTEGER DEFAULT 0,
                game_misconducts INTEGER DEFAULT 0,

                shots_on_goal INTEGER,
                shooting_pct REAL,
                plus_minus INTEGER,

                games_started_goalie INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                goals_against INTEGER DEFAULT 0,
                save_pct REAL,
                goals_against_avg REAL,
                shutouts INTEGER DEFAULT 0,

                number_consistency_score REAL DEFAULT 1.0,
                total_number_variations INTEGER DEFAULT 0,
                confidence_score REAL DEFAULT 1.0,

                PRIMARY KEY (player_id, team_id, season_id),
                CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)
            )
        ''')

        # TEAM_STATS table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_stats (
                team_id INTEGER,
                season_id TEXT,
                division_id INTEGER,

                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                otw INTEGER DEFAULT 0,
                otl INTEGER DEFAULT 0,
                sow INTEGER DEFAULT 0,
                sol INTEGER DEFAULT 0,

                points INTEGER DEFAULT 0,
                points_pct REAL DEFAULT 0.0,
                row INTEGER DEFAULT 0,

                division_rank INTEGER,

                goals_for INTEGER DEFAULT 0,
                goals_against INTEGER DEFAULT 0,
                goal_differential INTEGER DEFAULT 0,
                goals_per_game REAL DEFAULT 0.0,
                goals_against_per_game REAL DEFAULT 0.0,

                goals_period_1 INTEGER DEFAULT 0,
                goals_period_2 INTEGER DEFAULT 0,
                goals_period_3 INTEGER DEFAULT 0,
                goals_overtime INTEGER DEFAULT 0,
                goals_allowed_period_1 INTEGER DEFAULT 0,
                goals_allowed_period_2 INTEGER DEFAULT 0,
                goals_allowed_period_3 INTEGER DEFAULT 0,
                goals_allowed_overtime INTEGER DEFAULT 0,

                power_play_goals INTEGER DEFAULT 0,
                power_play_opportunities INTEGER DEFAULT 0,
                power_play_pct REAL DEFAULT 0.0,
                power_play_goals_against INTEGER DEFAULT 0,
                times_shorthanded INTEGER DEFAULT 0,
                penalty_kill_pct REAL DEFAULT 0.0,
                short_handed_goals INTEGER DEFAULT 0,
                short_handed_goals_against INTEGER DEFAULT 0,

                penalty_minutes INTEGER DEFAULT 0,
                pim_per_game REAL DEFAULT 0.0,
                penalties_taken INTEGER DEFAULT 0,
                major_penalties INTEGER DEFAULT 0,

                shots_for INTEGER,
                shots_against INTEGER,
                shooting_pct REAL,
                save_pct REAL,
                pdo REAL,

                last_10_record TEXT,
                current_streak TEXT,

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

        # STRENGTH_OF_SCHEDULE table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strength_of_schedule (
                team_id INTEGER,
                season_id TEXT,

                opponents_avg_points_pct REAL,
                sos_rank INTEGER,

                opponents_opponents_points_pct REAL,
                adjusted_sos REAL,

                beaten_teams_avg_points_pct REAL,
                sov_rank INTEGER,

                games_vs_top_third INTEGER DEFAULT 0,
                games_vs_middle_third INTEGER DEFAULT 0,
                games_vs_bottom_third INTEGER DEFAULT 0,
                points_vs_top_third INTEGER DEFAULT 0,
                points_vs_middle_third INTEGER DEFAULT 0,
                points_vs_bottom_third INTEGER DEFAULT 0,

                games_on_rest INTEGER DEFAULT 0,
                games_back_to_back INTEGER DEFAULT 0,
                rest_differential INTEGER DEFAULT 0,

                total_travel_distance REAL,
                avg_travel_per_game REAL,

                PRIMARY KEY (team_id, season_id)
            )
        ''')

        # HEAD_TO_HEAD table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS head_to_head (
                team1_id INTEGER,
                team2_id INTEGER,
                season_id TEXT,

                games_played INTEGER DEFAULT 0,
                team1_wins INTEGER DEFAULT 0,
                team1_losses INTEGER DEFAULT 0,
                team1_ties INTEGER DEFAULT 0,
                team1_points INTEGER DEFAULT 0,
                team1_points_pct REAL DEFAULT 0.0,

                team1_goals_for INTEGER DEFAULT 0,
                team1_goals_against INTEGER DEFAULT 0,
                goal_differential INTEGER DEFAULT 0,

                team1_pp_goals INTEGER DEFAULT 0,
                team1_pp_opportunities INTEGER DEFAULT 0,
                team1_pp_pct REAL DEFAULT 0.0,
                team1_pk_pct REAL DEFAULT 0.0,

                last_5_record TEXT,
                team1_current_streak TEXT,

                PRIMARY KEY (team1_id, team2_id, season_id)
            )
        ''')

        # PLAYER_GAME_LOG table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_game_log (
                player_id TEXT,
                game_id TEXT,
                team_id INTEGER,

                date DATE,
                opponent_team_id INTEGER,
                is_home_game BOOLEAN,

                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                pim INTEGER DEFAULT 0,
                plus_minus INTEGER,

                pp_goals INTEGER DEFAULT 0,
                sh_goals INTEGER DEFAULT 0,
                gwg INTEGER DEFAULT 0,

                number_used TEXT,
                number_matches_usual BOOLEAN DEFAULT TRUE,

                PRIMARY KEY (player_id, game_id)
            )
        ''')

        # DATA_QUALITY_ISSUES table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_quality_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                entity_type TEXT,
                entity_id TEXT,
                game_id TEXT,

                issue_type TEXT,
                issue_description TEXT,
                confidence_impact REAL DEFAULT 0.0,

                is_resolved BOOLEAN DEFAULT FALSE,
                resolution_notes TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CHECK (entity_type IN ('goal', 'penalty', 'roster', 'game', NULL)),
                CHECK (issue_type IN ('wrong_number', 'missing_name', 'duplicate_player',
                                      'inconsistent_data', 'missing_data', NULL))
            )
        ''')

        logger.info("Calculated stats tables created")

    def _create_whk_tables(self):
        """Create WHK Hawks-specific tables for the mobile app"""
        cursor = self.conn.cursor()

        # WHK Players - organization-specific player profiles
        # Links to existing player_stats via player_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whk_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT UNIQUE,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                dob DATE,
                email TEXT,
                phone TEXT,
                photo_url TEXT,
                jersey_number TEXT,
                position TEXT,
                player_type TEXT,
                division TEXT,
                age_group TEXT,
                team_id INTEGER,
                registration_status TEXT,
                registration_date DATE,
                order_number TEXT,
                tryout_color TEXT,
                tryout_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (position IN ('F', 'D', 'G', NULL)),
                CHECK (player_type IN ('Player', 'Full-Time Goalie', NULL)),
                CHECK (registration_status IN ('Paid', 'Pending', 'Cancelled', NULL))
            )
        ''')

        # Player skill evaluations from tryouts
        # Scores are 0-5 scale
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT,
                evaluator_name TEXT,
                evaluation_date DATE,
                tryout_color TEXT,
                tryout_number INTEGER,
                forward_skating INTEGER,
                backward_skating INTEGER,
                puck_control INTEGER,
                hockey_sense INTEGER,
                shooting INTEGER,
                total_score INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (forward_skating >= 0 AND forward_skating <= 5),
                CHECK (backward_skating >= 0 AND backward_skating <= 5),
                CHECK (puck_control >= 0 AND puck_control <= 5),
                CHECK (hockey_sense >= 0 AND hockey_sense <= 5),
                CHECK (shooting >= 0 AND shooting <= 5)
            )
        ''')

        # WHK Teams - extends existing teams with org-specific data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whk_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER UNIQUE,
                team_name TEXT NOT NULL,
                division TEXT,
                age_group TEXT,
                level TEXT,
                season TEXT,
                head_coach_id INTEGER,
                assistant_coaches TEXT,
                ical_feed_url TEXT,
                sportsengine_team_id TEXT,
                gamesheet_team_id INTEGER,
                gamesheet_division_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (division IN ('Mites', 'Squirts', 'Peewee', 'Bantam', 'Midget', 'Middle School', NULL)),
                CHECK (level IN ('A', 'B', 'C', 'Bronze', 'Silver', NULL))
            )
        ''')

        # Coaches and staff
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coaches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                photo_url TEXT,
                role TEXT,
                certifications TEXT,
                team_ids TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (role IN ('Head Coach', 'Assistant Coach', 'Manager', 'Trainer', NULL))
            )
        ''')

        # Board members
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS board_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                photo_url TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Venues/Rinks
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS venues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                city TEXT,
                state TEXT DEFAULT 'MA',
                zip TEXT,
                phone TEXT,
                website TEXT,
                google_maps_url TEXT,
                latitude REAL,
                longitude REAL,
                rink_count INTEGER DEFAULT 1,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Announcements/News
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                author TEXT,
                priority TEXT DEFAULT 'normal',
                target_audience TEXT DEFAULT 'all',
                target_team_ids TEXT,
                publish_date TIMESTAMP,
                expire_date TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
            )
        ''')

        # Push notification subscriptions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expo_push_token TEXT UNIQUE NOT NULL,
                user_email TEXT,
                player_ids TEXT,
                team_ids TEXT,
                notify_game_start BOOLEAN DEFAULT TRUE,
                notify_score_update BOOLEAN DEFAULT TRUE,
                notify_schedule_change BOOLEAN DEFAULT TRUE,
                notify_announcements BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Merchandise orders (holiday orders, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS merchandise_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT,
                player_first_name TEXT,
                player_last_name TEXT,
                coach_name TEXT,
                billing_name TEXT,
                billing_email TEXT,
                billing_phone TEXT,
                billing_address TEXT,
                product_name TEXT,
                size TEXT,
                player_number TEXT,
                hoodie_size TEXT,
                short_size TEXT,
                order_date DATE,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled'))
            )
        ''')

        # Calendar events (practices, team events - not games)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                team_id INTEGER,
                venue_id INTEGER,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                is_recurring BOOLEAN DEFAULT FALSE,
                recurrence_rule TEXT,
                ical_uid TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (event_type IN ('practice', 'skills', 'meeting', 'tryout', 'tournament', 'other'))
            )
        ''')

        # Data quality notes for player number reliability
        # NOTE: Player jersey numbers in goals/penalties from GameSheet are often inaccurate
        # Event data (time, period, penalty type) is reliable
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_reliability_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_source TEXT NOT NULL,
                field_name TEXT NOT NULL,
                reliability TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (reliability IN ('high', 'medium', 'low', 'unreliable'))
            )
        ''')

        # Insert known data reliability notes
        cursor.execute('''
            INSERT OR IGNORE INTO data_reliability_notes (data_source, field_name, reliability, notes)
            VALUES
                ('gamesheet', 'goal_time', 'high', 'Time of goal is accurately recorded'),
                ('gamesheet', 'goal_period', 'high', 'Period is accurately recorded'),
                ('gamesheet', 'penalty_type', 'high', 'Penalty call type is accurate'),
                ('gamesheet', 'penalty_time', 'high', 'Penalty time is accurately recorded'),
                ('gamesheet', 'scorer_number', 'low', 'Player jersey numbers for goals may be inaccurate'),
                ('gamesheet', 'assist_number', 'low', 'Player jersey numbers for assists may be inaccurate'),
                ('gamesheet', 'penalty_player_number', 'low', 'Player jersey numbers for penalties may be inaccurate'),
                ('sportsengine', 'schedule', 'high', 'Game schedules are accurate'),
                ('sportsengine', 'roster', 'high', 'Team rosters are accurate'),
                ('excel_import', 'player_profile', 'high', 'Player registration data is accurate')
        ''')

        logger.info("WHK-specific tables created")

    def _create_club_tables(self):
        """Create multi-club tables for SSC club website scraping data"""
        cursor = self.conn.cursor()

        # Club organizations (SSC member clubs)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_name TEXT NOT NULL,
                club_slug TEXT UNIQUE,
                website_url TEXT,
                sportsengine_org_id TEXT,
                town TEXT,
                abbreviation TEXT,
                conference TEXT DEFAULT 'SSC',
                last_scraped TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Club teams (generalized multi-club version)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS club_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER REFERENCES clubs(id),
                team_name TEXT NOT NULL,
                age_group TEXT,
                division_level TEXT,
                season TEXT,
                team_page_url TEXT,
                roster_url TEXT,
                schedule_url TEXT,
                sportsengine_page_id TEXT,
                sportsengine_team_instance_id TEXT,
                subseason_id TEXT,
                gamesheet_team_id INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(club_id, team_name, season)
            )
        ''')

        # Club players (from roster table scraping)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS club_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER REFERENCES clubs(id),
                club_team_id INTEGER REFERENCES club_teams(id),
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                jersey_number TEXT,
                position TEXT,
                usah_number TEXT,
                player_profile_url TEXT,
                gamesheet_player_id TEXT,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(club_id, club_team_id, first_name, last_name)
            )
        ''')

        # Club coaches
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS club_coaches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER REFERENCES clubs(id),
                club_team_id INTEGER REFERENCES club_teams(id),
                name TEXT NOT NULL,
                role TEXT,
                email TEXT,
                phone TEXT,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Club board members
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS club_board_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER REFERENCES clubs(id),
                name TEXT NOT NULL,
                title TEXT,
                email TEXT,
                phone TEXT,
                source_url TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Club schedule games
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS club_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER REFERENCES clubs(id),
                club_team_id INTEGER REFERENCES club_teams(id),
                game_id TEXT,
                date DATE,
                time TEXT,
                opponent TEXT,
                location TEXT,
                is_home BOOLEAN,
                home_score INTEGER,
                away_score INTEGER,
                status TEXT DEFAULT 'scheduled',
                game_url TEXT,
                gamesheet_game_id TEXT,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (status IN ('scheduled', 'final', 'cancelled', 'postponed'))
            )
        ''')

        # Club contacts (emails, phones, addresses found on site)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS club_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER REFERENCES clubs(id),
                contact_type TEXT NOT NULL,
                value TEXT NOT NULL,
                context TEXT,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (contact_type IN ('email', 'phone', 'address', 'website'))
            )
        ''')

        logger.info("Club tables created")

    def _create_gamesheet_roster_tables(self):
        """Create tables for GameSheet roster API data (for divisions with public names)"""
        cursor = self.conn.cursor()

        # GameSheet rosters - fetched from /useTeamRoster/getPlayerStandings endpoint
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gamesheet_rosters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                player_id TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                jersey_number TEXT,
                position TEXT,
                -- Season stats from API
                gp INTEGER DEFAULT 0,
                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                pim INTEGER DEFAULT 0,
                ppg INTEGER DEFAULT 0,
                shg INTEGER DEFAULT 0,
                gwg INTEGER DEFAULT 0,
                -- Bio fields (often null for youth)
                photo_url TEXT,
                birthdate TEXT,
                height TEXT,
                weight TEXT,
                shot_hand TEXT,
                hometown TEXT,
                -- Metadata
                is_goalie BOOLEAN DEFAULT 0,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(season_id, team_id, player_id)
            )
        ''')

        # GameSheet coaches - from same endpoint
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gamesheet_coaches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                first_name TEXT,
                last_name TEXT,
                position TEXT,  -- 'head_coach' or 'assistant_coach'
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(season_id, team_id, first_name, last_name)
            )
        ''')

        logger.info("GameSheet roster tables created")

    def _create_logo_tables(self):
        """Create consolidated logo tables - single source of truth for all logo data"""
        cursor = self.conn.cursor()

        # Master logo table - canonical logos indexed by organization/team name
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_name TEXT NOT NULL UNIQUE,  -- normalized org name (e.g., "whk_hawks")
                display_name TEXT,                     -- human-readable (e.g., "WHK Hawks")
                local_file TEXT,                       -- filename in logos/ dir (e.g., "WHK.svg")
                gamesheet_url TEXT,                    -- CDN URL from GameSheet
                source TEXT DEFAULT 'unknown',         -- 'local', 'gamesheet', 'both', 'manual'
                is_league_logo BOOLEAN DEFAULT 0,      -- true for BSHL, EHF league logos
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Team-to-logo mapping - handles team name variations and aliases
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logo_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,               -- exact team name from GameSheet/other sources
                team_id INTEGER,                       -- GameSheet team_id (if known)
                logo_id INTEGER REFERENCES logos(id),  -- link to canonical logo
                match_confidence REAL DEFAULT 1.0,     -- 0.0-1.0 confidence score
                is_manual_override BOOLEAN DEFAULT 0,  -- true if manually set
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_name, team_id)
            )
        ''')

        logger.info("Logo tables created")

    def _create_indexes(self):
        """Create indexes for performance optimization"""
        cursor = self.conn.cursor()

        # Games indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_season ON games(season_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_division ON games(division_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_date ON games(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_status ON games(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_home_team ON games(home_team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_visitor_team ON games(visitor_team_id)')

        # Teams indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_teams_season ON teams(season_id)')

        # Goals indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_goals_game ON goals(game_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_goals_scorer ON goals(scorer_player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_goals_team ON goals(team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_goals_period ON goals(period_number)')

        # Penalties indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_penalties_game ON penalties(game_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_penalties_player ON penalties(player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_penalties_team ON penalties(team_id)')

        # Game rosters indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rosters_game ON game_rosters(game_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rosters_player ON game_rosters(player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rosters_team ON game_rosters(team_id)')

        # Player stats indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_stats_season ON player_stats(season_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_stats_team ON player_stats(team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_stats_points ON player_stats(points DESC)')

        # Team stats indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_team_stats_season ON team_stats(season_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_team_stats_division ON team_stats(division_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_team_stats_points ON team_stats(points DESC)')

        # Data quality indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_quality_game ON data_quality_issues(game_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_quality_entity ON data_quality_issues(entity_type, entity_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_quality_resolved ON data_quality_issues(is_resolved)')

        # WHK-specific indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_whk_players_name ON whk_players(last_name, first_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_whk_players_team ON whk_players(team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_whk_players_division ON whk_players(division)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_whk_players_age_group ON whk_players(age_group)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_evals_player ON player_evaluations(player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_whk_teams_division ON whk_teams(division)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_whk_teams_season ON whk_teams(season)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_coaches_team ON coaches(team_ids)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_calendar_events_team ON calendar_events(team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON calendar_events(start_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_announcements_active ON announcements(is_active, publish_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_push_subs_token ON push_subscriptions(expo_push_token)')

        # Club tables indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clubs_slug ON clubs(club_slug)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_teams_club ON club_teams(club_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_teams_season ON club_teams(season)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_players_club ON club_players(club_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_players_team ON club_players(club_team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_players_name ON club_players(last_name, first_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_players_gamesheet_id ON club_players(gamesheet_player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_coaches_club ON club_coaches(club_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_board_members_club ON club_board_members(club_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_games_club ON club_games(club_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_games_team ON club_games(club_team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_games_date ON club_games(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_contacts_club ON club_contacts(club_id)')

        # GameSheet roster tables indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gs_rosters_season ON gamesheet_rosters(season_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gs_rosters_team ON gamesheet_rosters(team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gs_rosters_player ON gamesheet_rosters(player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gs_rosters_name ON gamesheet_rosters(last_name, first_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gs_coaches_season ON gamesheet_coaches(season_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gs_coaches_team ON gamesheet_coaches(team_id)')

        # Logo tables indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logos_canonical ON logos(canonical_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logos_local_file ON logos(local_file)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logo_aliases_name ON logo_aliases(team_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logo_aliases_team_id ON logo_aliases(team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logo_aliases_logo ON logo_aliases(logo_id)')

        logger.info("Database indexes created")

    def vacuum(self):
        """Optimize database and reclaim space"""
        self.conn.execute("VACUUM")
        self.conn.commit()
        logger.info("Database optimized")

    def get_stats(self) -> dict:
        """Get database statistics"""
        cursor = self.conn.cursor()

        stats = {}
        tables = [
            # Core tables
            'games', 'goals', 'penalties', 'game_rosters', 'teams', 'divisions',
            'player_stats', 'team_stats', 'data_quality_issues',
            # WHK-specific tables
            'whk_players', 'player_evaluations', 'whk_teams', 'coaches',
            'board_members', 'venues', 'announcements', 'push_subscriptions',
            'merchandise_orders', 'calendar_events', 'data_reliability_notes',
            # Club tables (multi-club SSC scraping)
            'clubs', 'club_teams', 'club_players', 'club_coaches',
            'club_board_members', 'club_games', 'club_contacts',
            # GameSheet roster API tables
            'gamesheet_rosters', 'gamesheet_coaches',
            # Logo tables
            'logos', 'logo_aliases'
        ]

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                # Table doesn't exist yet
                stats[table] = 0

        return stats


def create_database(db_path: str) -> AdvancedStatsDatabase:
    """
    Create and initialize a new advanced stats database.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Initialized AdvancedStatsDatabase instance

    Example:
        >>> db = create_database('hockey_stats.db')
        >>> with db:
        ...     stats = db.get_stats()
        ...     print(stats)
    """
    db = AdvancedStatsDatabase(db_path)
    db.connect()
    db.initialize_schema()
    return db


def main():
    """Test database creation"""
    import os

    db_path = "advanced_hockey_stats.db"

    # Remove existing database for fresh start
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"Removed existing database: {db_path}")

    # Create new database
    logger.info("Creating new database...")
    with create_database(db_path) as db:
        stats = db.get_stats()
        logger.info(f"Database created successfully: {db_path}")
        logger.info(f"Table counts: {stats}")

        # Optimize
        db.vacuum()

    logger.info("Database initialization complete!")


if __name__ == "__main__":
    main()
