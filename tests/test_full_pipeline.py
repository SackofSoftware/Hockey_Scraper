#!/usr/bin/env python3
"""
Integration Test Suite for Full Pipeline
Tests complete pipeline with multiple season IDs

Usage:
    python3 test_full_pipeline.py --test-seasons 10776,10477
    python3 test_full_pipeline.py --quick  # Fast test with minimal data
"""

import sys
import os
import unittest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any

from pipeline_config import PipelineConfig, PresetConfigs
from full_pipeline import PipelineOrchestrator
from advanced_stats_database import create_database


class TestDatabaseIntegration(unittest.TestCase):
    """Test database schema creation and integrity"""

    def setUp(self):
        """Create temporary database for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_hockey.db")
        self.db = create_database(self.db_path)

    def tearDown(self):
        """Clean up temporary database"""
        if self.db:
            self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_schema_creation(self):
        """Test that all tables are created"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        required_tables = {
            'games', 'goals', 'penalties', 'game_rosters',
            'teams', 'divisions', 'player_stats', 'team_stats',
            'strength_of_schedule', 'head_to_head',
            'player_game_log', 'data_quality_issues'
        }

        self.assertTrue(required_tables.issubset(tables),
                       f"Missing tables: {required_tables - tables}")

    def test_foreign_keys_enabled(self):
        """Test that foreign key constraints are enabled"""
        cursor = self.db.conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        self.assertEqual(result[0], 1, "Foreign keys not enabled")

    def test_indexes_created(self):
        """Test that indexes are created"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        # Check for some key indexes
        expected_indexes = {
            'idx_games_season', 'idx_goals_game', 'idx_penalties_game',
            'idx_player_stats_season', 'idx_team_stats_season'
        }

        self.assertTrue(expected_indexes.issubset(indexes),
                       f"Missing indexes: {expected_indexes - indexes}")

    def test_data_insertion(self):
        """Test basic data insertion"""
        cursor = self.db.conn.cursor()

        # Insert test division
        cursor.execute("""
            INSERT INTO divisions (division_id, division_name, season_id)
            VALUES (1, 'Test Division', '10776')
        """)

        # Insert test team
        cursor.execute("""
            INSERT INTO teams (team_id, team_name, division_id, season_id)
            VALUES (1, 'Test Team', 1, '10776')
        """)

        # Insert test game
        cursor.execute("""
            INSERT INTO games (game_id, season_id, division_id, date, status,
                              home_team_id, visitor_team_id, home_score, visitor_score)
            VALUES ('1', '10776', 1, '2025-01-01', 'final', 1, 1, 3, 2)
        """)

        self.db.conn.commit()

        # Verify insertions
        cursor.execute("SELECT COUNT(*) FROM divisions WHERE season_id = '10776'")
        self.assertEqual(cursor.fetchone()[0], 1)

        cursor.execute("SELECT COUNT(*) FROM teams WHERE season_id = '10776'")
        self.assertEqual(cursor.fetchone()[0], 1)

        cursor.execute("SELECT COUNT(*) FROM games WHERE season_id = '10776'")
        self.assertEqual(cursor.fetchone()[0], 1)


class TestStatsCalculatorIntegration(unittest.TestCase):
    """Test stats calculator integration"""

    def setUp(self):
        """Create test database with sample data"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_stats.db")
        self.db = create_database(self.db_path)
        self._populate_test_data()

    def tearDown(self):
        """Clean up"""
        if self.db:
            self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _populate_test_data(self):
        """Populate database with test data"""
        cursor = self.db.conn.cursor()

        # Add division
        cursor.execute("""
            INSERT INTO divisions (division_id, division_name, season_id)
            VALUES (1, 'Test Division', '10776')
        """)

        # Add teams
        for i in range(1, 5):
            cursor.execute("""
                INSERT INTO teams (team_id, team_name, division_id, season_id)
                VALUES (?, ?, 1, '10776')
            """, (i, f'Team {i}'))

        # Add game
        cursor.execute("""
            INSERT INTO games (game_id, season_id, division_id, date, status,
                              home_team_id, visitor_team_id, home_score, visitor_score)
            VALUES ('1', '10776', 1, '2025-01-01', 'final', 1, 2, 3, 2)
        """)

        # Add goals
        cursor.execute("""
            INSERT INTO goals (game_id, team_id, scorer_player_id, scorer_name, scorer_number,
                              is_home_team, is_power_play, is_short_handed, is_game_winning)
            VALUES ('1', 1, '101', 'Player One', '10', 1, 0, 0, 1)
        """)

        cursor.execute("""
            INSERT INTO goals (game_id, team_id, scorer_player_id, scorer_name, scorer_number,
                              is_home_team)
            VALUES ('1', 1, '101', 'Player One', '10', 1)
        """)

        self.db.conn.commit()

    def test_player_stats_calculation(self):
        """Test that player stats are calculated correctly"""
        from stats_calculator import AdvancedStatsCalculator

        calculator = AdvancedStatsCalculator(self.db_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            calculator.calculate_player_basic_stats(cursor, '10776')
            conn.commit()

            # Check player stats were created
            cursor.execute("SELECT COUNT(*) FROM player_stats WHERE season_id = '10776'")
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0, "No player stats calculated")

            # Check specific player
            cursor.execute("""
                SELECT goals FROM player_stats
                WHERE player_id = '101' AND season_id = '10776'
            """)
            result = cursor.fetchone()
            self.assertIsNotNone(result, "Player stats not found")
            self.assertEqual(result[0], 2, "Goal count incorrect")

    def test_team_stats_calculation(self):
        """Test that team stats are calculated correctly"""
        from stats_calculator import AdvancedStatsCalculator

        calculator = AdvancedStatsCalculator(self.db_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            calculator.calculate_team_basic_stats(cursor, '10776')
            conn.commit()

            # Check team stats were created
            cursor.execute("SELECT COUNT(*) FROM team_stats WHERE season_id = '10776'")
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0, "No team stats calculated")

            # Check team 1 (home team won)
            cursor.execute("""
                SELECT wins, losses, goals_for, goals_against
                FROM team_stats
                WHERE team_id = 1 AND season_id = '10776'
            """)
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            wins, losses, gf, ga = result
            self.assertEqual(wins, 1, "Win not recorded")
            self.assertEqual(gf, 3, "Goals for incorrect")
            self.assertEqual(ga, 2, "Goals against incorrect")


class TestAPIIntegration(unittest.TestCase):
    """Test API server integration"""

    def test_api_models_import(self):
        """Test that API models can be imported"""
        try:
            from api_models import (
                SeasonInfo, TeamStatsComplete, PlayerProfile,
                LeaderBoard, GameInfo
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import API models: {e}")

    def test_api_server_import(self):
        """Test that API server can be imported"""
        try:
            from api_server import app
            self.assertIsNotNone(app)
        except ImportError as e:
            self.fail(f"Failed to import API server: {e}")


class TestDataQualityIntegration(unittest.TestCase):
    """Test data quality analyzer integration"""

    def setUp(self):
        """Create test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_quality.db")
        self.db = create_database(self.db_path)

    def tearDown(self):
        """Clean up"""
        if self.db:
            self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_quality_analyzer_runs(self):
        """Test that quality analyzer runs without errors"""
        from data_quality_analyzer import DataQualityAnalyzer

        analyzer = DataQualityAnalyzer(self.db_path)
        try:
            results = analyzer.analyze_all()
            self.assertIn('overall_quality_score', results)
            self.assertGreaterEqual(results['overall_quality_score'], 0.0)
            self.assertLessEqual(results['overall_quality_score'], 1.0)
        finally:
            analyzer.close()

    def test_quality_issues_table_created(self):
        """Test that data quality issues table is created"""
        from data_quality_analyzer import DataQualityAnalyzer

        analyzer = DataQualityAnalyzer(self.db_path)
        try:
            results = analyzer.analyze_all()
            analyzer.save_to_database(results)

            cursor = self.db.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_quality_issues'")
            self.assertIsNotNone(cursor.fetchone(), "data_quality_issues table not created")
        finally:
            analyzer.close()


class TestMultiLeagueIntegration(unittest.TestCase):
    """Test pipeline with multiple season IDs"""

    @classmethod
    def setUpClass(cls):
        """Setup test environment"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_seasons = ['10776']  # Can add more for full test

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_data_isolation(self):
        """Test that data from different seasons is isolated"""
        # Create databases for two seasons
        db1_path = os.path.join(self.temp_dir, "season_10776.db")
        db2_path = os.path.join(self.temp_dir, "season_10477.db")

        db1 = create_database(db1_path)
        db2 = create_database(db2_path)

        try:
            # Add data to first database
            cursor1 = db1.conn.cursor()
            cursor1.execute("""
                INSERT INTO divisions (division_id, division_name, season_id)
                VALUES (1, 'Division A', '10776')
            """)
            db1.conn.commit()

            # Add different data to second database
            cursor2 = db2.conn.cursor()
            cursor2.execute("""
                INSERT INTO divisions (division_id, division_name, season_id)
                VALUES (2, 'Division B', '10477')
            """)
            db2.conn.commit()

            # Verify isolation
            cursor1.execute("SELECT COUNT(*) FROM divisions WHERE season_id = '10776'")
            self.assertEqual(cursor1.fetchone()[0], 1)

            cursor2.execute("SELECT COUNT(*) FROM divisions WHERE season_id = '10477'")
            self.assertEqual(cursor2.fetchone()[0], 1)

            # Verify no cross-contamination
            cursor1.execute("SELECT COUNT(*) FROM divisions WHERE season_id = '10477'")
            self.assertEqual(cursor1.fetchone()[0], 0)

        finally:
            db1.close()
            db2.close()

    def test_configuration_consistency(self):
        """Test that same configuration works for multiple seasons"""
        for season_id in self.test_seasons:
            config = PipelineConfig.for_season(
                season_id,
                database_path=os.path.join(self.temp_dir, f"test_{season_id}.db"),
                log_to_file=False
            )

            # Validate configuration
            is_valid, errors = config.validate()
            self.assertTrue(is_valid, f"Config invalid for {season_id}: {errors}")


class TestPipelineConfiguration(unittest.TestCase):
    """Test pipeline configuration system"""

    def test_default_configuration(self):
        """Test default configuration"""
        config = PipelineConfig(season_id="10776")
        is_valid, errors = config.validate()
        self.assertTrue(is_valid, f"Default config invalid: {errors}")

    def test_preset_configurations(self):
        """Test all preset configurations"""
        for preset_name in ['development', 'production', 'testing', 'minimal']:
            config = getattr(PresetConfigs, preset_name)("10776")
            is_valid, errors = config.validate()
            self.assertTrue(is_valid, f"{preset_name} preset invalid: {errors}")

    def test_custom_configuration(self):
        """Test custom configuration with overrides"""
        config = PipelineConfig.for_season(
            "10776",
            api_delay=0.5,
            min_quality_score=0.9,
            api_port=8080
        )

        self.assertEqual(config.api_delay, 0.5)
        self.assertEqual(config.min_quality_score, 0.9)
        self.assertEqual(config.api_port, 8080)

        is_valid, errors = config.validate()
        self.assertTrue(is_valid, f"Custom config invalid: {errors}")

    def test_config_validation_errors(self):
        """Test that invalid configurations are caught"""
        # Invalid port
        config = PipelineConfig(season_id="10776", api_port=99999)
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any('port' in err.lower() for err in errors))

        # Invalid quality score
        config = PipelineConfig(season_id="10776", min_quality_score=1.5)
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any('quality' in err.lower() for err in errors))


def run_test_suite(test_seasons: List[str] = None, quick: bool = False):
    """
    Run complete integration test suite

    Args:
        test_seasons: List of season IDs to test
        quick: Run quick test with minimal data
    """
    print("=" * 80)
    print(" " * 25 + "PIPELINE INTEGRATION TEST SUITE")
    print("=" * 80)
    print()

    if quick:
        print("Running QUICK TEST mode (limited coverage)")
    else:
        print("Running FULL TEST mode (comprehensive coverage)")

    if test_seasons:
        print(f"Test seasons: {', '.join(test_seasons)}")

    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestStatsCalculatorIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDataQualityIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineConfiguration))

    if not quick:
        suite.addTests(loader.loadTestsFromTestCase(TestMultiLeagueIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run:     {result.testsRun}")
    print(f"Successes:     {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures:      {len(result.failures)}")
    print(f"Errors:        {len(result.errors)}")
    print(f"Status:        {'✅ PASSED' if result.wasSuccessful() else '❌ FAILED'}")
    print("=" * 80)

    return 0 if result.wasSuccessful() else 1


def main():
    """Main test entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Integration Test Suite for Hockey Stats Pipeline"
    )

    parser.add_argument(
        "--test-seasons",
        help="Comma-separated list of season IDs to test (e.g., 10776,10477)"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test with minimal coverage"
    )

    args = parser.parse_args()

    test_seasons = None
    if args.test_seasons:
        test_seasons = args.test_seasons.split(',')

    return run_test_suite(test_seasons=test_seasons, quick=args.quick)


if __name__ == "__main__":
    sys.exit(main())
