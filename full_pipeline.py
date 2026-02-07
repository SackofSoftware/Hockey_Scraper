#!/usr/bin/env python3
"""
Complete Hockey Stats Pipeline Orchestrator
Runs the complete data pipeline from API import to statistics calculation

Usage:
    python3 full_pipeline.py --season-id 10776
    python3 full_pipeline.py --season-id 10776 --phase import
    python3 full_pipeline.py --season-id 10776 --config custom_config.json
"""

import sys
import argparse
import logging
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Import pipeline components
from pipeline_config import PipelineConfig, PresetConfigs
from advanced_stats_database import create_database, AdvancedStatsDatabase
from data_importer import DataImporter
from stats_calculator import AdvancedStatsCalculator
from advanced_metrics import AdvancedMetricsCalculator
from data_quality_analyzer import DataQualityAnalyzer


class PipelineOrchestrator:
    """Orchestrates the complete hockey stats pipeline"""

    def __init__(self, config: PipelineConfig):
        """
        Initialize pipeline with configuration

        Args:
            config: PipelineConfig instance
        """
        self.config = config
        self.db = None
        self.stats = {
            'start_time': None,
            'end_time': None,
            'phases_completed': [],
            'phases_failed': [],
            'total_duration': 0.0
        }

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging based on config"""
        log_level = getattr(logging, self.config.log_level.upper())

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=self.config.log_format,
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )

        # Add file handler if enabled
        if self.config.log_to_file:
            file_handler = logging.FileHandler(self.config.log_file_path)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(self.config.log_format))
            logging.getLogger().addHandler(file_handler)

        self.logger = logging.getLogger(__name__)

    def print_banner(self):
        """Print pipeline banner"""
        print("\n" + "=" * 80)
        print(" " * 20 + "HOCKEY STATS PIPELINE - FULL INTEGRATION")
        print("=" * 80)
        print(f"  Season ID: {self.config.season_id}")
        print(f"  Database:  {self.config.database_path}")
        print(f"  Started:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

    def run_all(self) -> Dict[str, Any]:
        """
        Run complete pipeline - all phases

        Returns:
            Dictionary with pipeline results and statistics
        """
        self.stats['start_time'] = time.time()
        self.print_banner()

        try:
            # Phase 1: Database Setup & Data Import
            if self.config.calculate_basic_stats or self.config.calculate_advanced_metrics:
                self.phase1_database_setup()

            # Phase 2: Calculate Statistics
            if self.config.calculate_basic_stats:
                self.phase2_calculate_stats()

            # Phase 3: Calculate Advanced Metrics
            if self.config.calculate_advanced_metrics:
                self.phase3_advanced_metrics()

            # Phase 4: Data Quality Analysis
            self.phase4_data_quality()

            # Phase 5: Generate Reports
            if self.config.generate_reports:
                self.phase5_generate_reports()

            # Phase 6: Club Website Scraping (optional)
            if self.config.scrape_clubs:
                self.phase6_club_scrape()

            # Phase 7: Club-to-GameSheet Reconciliation (optional)
            if self.config.scrape_clubs and self.config.reconcile_clubs:
                self.phase7_reconcile_clubs()

            # Finalize
            self._finalize()

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.stats['phases_failed'].append('pipeline')
            raise

        finally:
            self.stats['end_time'] = time.time()
            self.stats['total_duration'] = self.stats['end_time'] - self.stats['start_time']

        return self._generate_summary()

    def phase1_database_setup(self):
        """
        Phase 1: Database Setup and Data Import

        - Create database schema
        - Import divisions and teams
        - Import schedule
        - Import box scores
        """
        phase_name = "Phase 1: Database Setup & Import"
        self.logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")

        phase_start = time.time()

        try:
            # Create/backup database
            if os.path.exists(self.config.database_path):
                if self.config.create_backup:
                    backup_path = self.config.backup_path or f"{self.config.database_path}.backup"
                    self.logger.info(f"Creating backup: {backup_path}")
                    import shutil
                    shutil.copy2(self.config.database_path, backup_path)
                else:
                    self.logger.warning("Removing existing database (no backup)")
                    os.remove(self.config.database_path)

            # Create database
            self.logger.info("Initializing database schema...")
            self.db = create_database(self.config.database_path)

            # Import data
            self.logger.info(f"Starting data import for season {self.config.season_id}")
            importer = DataImporter(self.db, self.config.season_id)

            # Configure division filtering
            division_ids = None
            if not self.config.import_all_divisions and self.config.specific_division_ids:
                division_ids = self.config.specific_division_ids
                self.logger.info(f"Filtering to divisions: {division_ids}")

            # Run import
            importer.import_all(division_ids=division_ids)

            # Optimize database
            if self.config.vacuum_database:
                self.logger.info("Optimizing database...")
                self.db.vacuum()

            phase_duration = time.time() - phase_start
            self.stats['phases_completed'].append({
                'name': phase_name,
                'duration': phase_duration
            })

            self.logger.info(f"\n✅ {phase_name} completed in {phase_duration:.1f}s\n")

        except Exception as e:
            self.logger.error(f"Phase 1 failed: {e}", exc_info=True)
            self.stats['phases_failed'].append(phase_name)
            raise

    def phase2_calculate_stats(self):
        """
        Phase 2: Calculate Basic Statistics

        - Player stats (goals, assists, points, PIM)
        - Team stats (record, scoring, discipline)
        - Special teams (PP%, PK%)
        - Home/away splits
        - Period breakdowns
        """
        phase_name = "Phase 2: Calculate Statistics"
        self.logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")

        phase_start = time.time()

        try:
            calculator = AdvancedStatsCalculator(self.config.database_path)
            calculator.calculate_all_stats(self.config.season_id)

            phase_duration = time.time() - phase_start
            self.stats['phases_completed'].append({
                'name': phase_name,
                'duration': phase_duration
            })

            self.logger.info(f"\n✅ {phase_name} completed in {phase_duration:.1f}s\n")

        except Exception as e:
            self.logger.error(f"Phase 2 failed: {e}", exc_info=True)
            self.stats['phases_failed'].append(phase_name)
            raise

    def phase3_advanced_metrics(self):
        """
        Phase 3: Calculate Advanced Metrics

        - Strength of Schedule (SOS)
        - Strength of Victory (SOV)
        - Head-to-head records
        - Rest differential
        - Recent form and streaks
        """
        phase_name = "Phase 3: Advanced Metrics"
        self.logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")

        phase_start = time.time()

        try:
            calculator = AdvancedMetricsCalculator(self.config.database_path)
            calculator.calculate_all_advanced_metrics(self.config.season_id)

            phase_duration = time.time() - phase_start
            self.stats['phases_completed'].append({
                'name': phase_name,
                'duration': phase_duration
            })

            self.logger.info(f"\n✅ {phase_name} completed in {phase_duration:.1f}s\n")

        except Exception as e:
            self.logger.error(f"Phase 3 failed: {e}", exc_info=True)
            self.stats['phases_failed'].append(phase_name)
            raise

    def phase4_data_quality(self):
        """
        Phase 4: Data Quality Analysis

        - Analyze player number consistency
        - Calculate confidence scores
        - Detect duplicates
        - Flag suspicious data
        - Generate quality report
        """
        phase_name = "Phase 4: Data Quality Analysis"
        self.logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")

        phase_start = time.time()

        try:
            analyzer = DataQualityAnalyzer(self.config.database_path)
            results = analyzer.analyze_all()

            # Save to database
            analyzer.save_to_database(results)

            # Save report if configured
            if self.config.generate_reports:
                os.makedirs(self.config.reports_directory, exist_ok=True)
                report_path = os.path.join(
                    self.config.reports_directory,
                    f"data_quality_{self.config.season_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                analyzer.save_results(results, report_path)

            analyzer.close()

            phase_duration = time.time() - phase_start
            self.stats['phases_completed'].append({
                'name': phase_name,
                'duration': phase_duration,
                'quality_score': results['overall_quality_score']
            })

            self.logger.info(f"\n✅ {phase_name} completed in {phase_duration:.1f}s")
            self.logger.info(f"   Overall Quality Score: {results['overall_quality_score']:.3f}\n")

        except Exception as e:
            self.logger.error(f"Phase 4 failed: {e}", exc_info=True)
            self.stats['phases_failed'].append(phase_name)
            # Don't raise - quality analysis is non-critical

    def phase5_generate_reports(self):
        """
        Phase 5: Generate Summary Reports

        - Pipeline execution summary
        - Database statistics
        - Top performers
        - Team standings
        """
        phase_name = "Phase 5: Generate Reports"
        self.logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")

        phase_start = time.time()

        try:
            os.makedirs(self.config.reports_directory, exist_ok=True)

            # Generate summary report
            self._generate_pipeline_report()

            # Generate stats summary
            self._generate_stats_summary()

            phase_duration = time.time() - phase_start
            self.stats['phases_completed'].append({
                'name': phase_name,
                'duration': phase_duration
            })

            self.logger.info(f"\n✅ {phase_name} completed in {phase_duration:.1f}s\n")

        except Exception as e:
            self.logger.error(f"Phase 5 failed: {e}", exc_info=True)
            self.stats['phases_failed'].append(phase_name)
            # Don't raise - reporting is non-critical

    def phase6_club_scrape(self):
        """
        Phase 6: Club Website Scraping (optional)

        Scrape SportsEngine club websites for team/roster/schedule/board data.
        Only runs if config.scrape_clubs is True.
        """
        import asyncio

        phase_name = "Phase 6: Club Website Scraping"
        self.logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")
        phase_start = time.time()

        try:
            from club_scraper import SSCCrawler
            from club_importer import ClubDataImporter

            # Run the async club scraper
            crawler = SSCCrawler(
                config_path=self.config.clubs_config_path,
                output_dir=Path(self.config.clubs_output_dir),
                headless=self.config.club_scrape_headless,
                rate_limit_ms=self.config.club_rate_limit_ms,
                max_pages_per_club=self.config.club_max_pages_per_club,
            )
            results = asyncio.run(crawler.scrape_all())

            # Import into database
            if self.db:
                importer = ClubDataImporter(self.db)
                for result in results:
                    try:
                        importer.import_club_result(result)
                    except Exception as e:
                        self.logger.error(f"Failed to import {result.club.club_name}: {e}")

                self.logger.info(f"Club import stats: {importer._stats_line()}")

            phase_duration = time.time() - phase_start
            self.stats['phases_completed'].append({
                'name': phase_name,
                'duration': phase_duration,
                'clubs_scraped': len(results),
            })

            self.logger.info(f"\n✅ {phase_name} completed in {phase_duration:.1f}s\n")

        except Exception as e:
            self.logger.error(f"Phase 6 failed: {e}", exc_info=True)
            self.stats['phases_failed'].append(phase_name)
            # Don't raise - club scraping is non-critical

    def phase7_reconcile_clubs(self):
        """
        Phase 7: Club-to-GameSheet Reconciliation

        Links club-scraped data (teams, players) to GameSheet data.
        - Matches club_teams → teams by name patterns and roster overlap
        - Matches club_players → game_rosters by jersey number
        - Backfills player names from club rosters to GameSheet data

        Only runs if config.scrape_clubs AND config.reconcile_clubs are True.
        """
        phase_name = "Phase 7: Club-to-GameSheet Reconciliation"
        self.logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")
        phase_start = time.time()

        try:
            from player_reconciler import PlayerReconciler

            if not self.db:
                self.logger.warning("No database connection, skipping reconciliation")
                return

            reconciler = PlayerReconciler(self.db, self.config.season_id)
            stats = reconciler.reconcile_all()

            # Log results
            teams_matched = stats.get('teams_matched', 0)
            teams_unmatched = stats.get('teams_unmatched', 0)
            teams_skipped = stats.get('teams_skipped', 0)
            players_matched = stats.get('players_matched', 0)
            players_unmatched = stats.get('players_unmatched', 0)
            names_backfilled = stats.get('names_backfilled', {})
            total_backfilled = sum(names_backfilled.values()) if names_backfilled else 0

            self.logger.info(f"Teams matched: {teams_matched} ({teams_unmatched} unmatched, {teams_skipped} skipped)")
            self.logger.info(f"Players matched: {players_matched} ({players_unmatched} unmatched)")
            self.logger.info(f"Names backfilled: {total_backfilled}")

            if teams_unmatched > 0:
                self.logger.warning(f"{teams_unmatched} teams could not be matched to GameSheet data")

            if players_unmatched > 0:
                self.logger.warning(f"{players_unmatched} players could not be matched by jersey number")

            phase_duration = time.time() - phase_start
            self.stats['phases_completed'].append({
                'name': phase_name,
                'duration': phase_duration,
                'teams_matched': teams_matched,
                'teams_unmatched': teams_unmatched,
                'players_matched': players_matched,
                'names_backfilled': total_backfilled,
            })

            self.logger.info(f"\n✅ {phase_name} completed in {phase_duration:.1f}s\n")

        except Exception as e:
            self.logger.error(f"Phase 7 failed: {e}", exc_info=True)
            self.stats['phases_failed'].append(phase_name)
            # Don't raise - reconciliation is non-critical

    def _finalize(self):
        """Finalize pipeline execution"""
        if self.db:
            self.db.close()

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate pipeline execution summary"""
        return {
            'season_id': self.config.season_id,
            'database': self.config.database_path,
            'start_time': datetime.fromtimestamp(self.stats['start_time']).isoformat(),
            'end_time': datetime.fromtimestamp(self.stats['end_time']).isoformat(),
            'total_duration_seconds': self.stats['total_duration'],
            'phases_completed': self.stats['phases_completed'],
            'phases_failed': self.stats['phases_failed'],
            'success': len(self.stats['phases_failed']) == 0
        }

    def _generate_pipeline_report(self):
        """Generate detailed pipeline execution report"""
        report_path = os.path.join(
            self.config.reports_directory,
            f"pipeline_execution_{self.config.season_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("HOCKEY STATS PIPELINE - EXECUTION REPORT\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Season ID: {self.config.season_id}\n")
            f.write(f"Database: {self.config.database_path}\n")
            f.write(f"Started: {datetime.fromtimestamp(self.stats['start_time']).strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Ended: {datetime.fromtimestamp(self.stats['end_time']).strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration: {self.stats['total_duration']:.1f} seconds\n\n")

            f.write("PHASES COMPLETED:\n")
            f.write("-" * 80 + "\n")
            for phase in self.stats['phases_completed']:
                f.write(f"  ✅ {phase['name']}: {phase['duration']:.1f}s\n")
                if 'quality_score' in phase:
                    f.write(f"     Quality Score: {phase['quality_score']:.3f}\n")

            if self.stats['phases_failed']:
                f.write("\nPHASES FAILED:\n")
                f.write("-" * 80 + "\n")
                for phase in self.stats['phases_failed']:
                    f.write(f"  ❌ {phase}\n")

            f.write("\n" + "=" * 80 + "\n")

        self.logger.info(f"Pipeline report saved to: {report_path}")

    def _generate_stats_summary(self):
        """Generate statistics summary from database"""
        import sqlite3

        conn = sqlite3.connect(self.config.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        report_path = os.path.join(
            self.config.reports_directory,
            f"stats_summary_{self.config.season_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"STATS SUMMARY - Season {self.config.season_id}\n")
            f.write("=" * 80 + "\n\n")

            # Database record counts
            f.write("DATABASE RECORDS:\n")
            f.write("-" * 80 + "\n")
            for table in ['games', 'goals', 'penalties', 'game_rosters', 'teams', 'divisions', 'player_stats', 'team_stats']:
                try:
                    count = cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()['cnt']
                    f.write(f"  {table:20} {count:6d}\n")
                except:
                    pass

            # Top 10 scorers
            f.write("\nTOP 10 SCORERS:\n")
            f.write("-" * 80 + "\n")
            try:
                scorers = cursor.execute("""
                    SELECT player_number, player_name, team_id, goals, assists, points, games_played
                    FROM player_stats
                    WHERE season_id = ?
                    ORDER BY points DESC, goals DESC
                    LIMIT 10
                """, (self.config.season_id,)).fetchall()

                for i, scorer in enumerate(scorers, 1):
                    f.write(f"  {i:2}. #{scorer['player_number']:3} {scorer['player_name']:25} - {scorer['points']:3} pts ({scorer['goals']}G, {scorer['assists']}A) in {scorer['games_played']} GP\n")
            except:
                f.write("  (Not available)\n")

            # Team standings
            f.write("\nTEAM STANDINGS:\n")
            f.write("-" * 80 + "\n")
            try:
                teams = cursor.execute("""
                    SELECT t.team_name, ts.games_played, ts.wins, ts.losses, ts.ties,
                           ts.points, ts.goals_for, ts.goals_against
                    FROM team_stats ts
                    JOIN teams t ON ts.team_id = t.team_id
                    WHERE ts.season_id = ?
                    ORDER BY ts.points DESC, ts.wins DESC, ts.goal_differential DESC
                    LIMIT 10
                """, (self.config.season_id,)).fetchall()

                f.write(f"  {'Team':25} {'GP':3} {'W':3} {'L':3} {'T':3} {'PTS':4} {'GF':3} {'GA':3}\n")
                f.write("  " + "-" * 76 + "\n")
                for team in teams:
                    f.write(f"  {team['team_name']:25} {team['games_played']:3} {team['wins']:3} {team['losses']:3} {team['ties']:3} {team['points']:4} {team['goals_for']:3} {team['goals_against']:3}\n")
            except:
                f.write("  (Not available)\n")

            f.write("\n" + "=" * 80 + "\n")

        conn.close()
        self.logger.info(f"Stats summary saved to: {report_path}")

    def print_final_summary(self, summary: Dict[str, Any]):
        """Print final execution summary"""
        print("\n" + "=" * 80)
        print(" " * 25 + "PIPELINE EXECUTION SUMMARY")
        print("=" * 80)
        print(f"  Season ID:        {summary['season_id']}")
        print(f"  Database:         {summary['database']}")
        print(f"  Duration:         {summary['total_duration_seconds']:.1f} seconds")
        print(f"  Phases Completed: {len(summary['phases_completed'])}")
        print(f"  Phases Failed:    {len(summary['phases_failed'])}")
        print(f"  Status:           {'✅ SUCCESS' if summary['success'] else '❌ FAILED'}")
        print("=" * 80 + "\n")

        if summary['phases_completed']:
            print("Completed Phases:")
            for phase in summary['phases_completed']:
                print(f"  ✅ {phase['name']} ({phase['duration']:.1f}s)")

        if summary['phases_failed']:
            print("\nFailed Phases:")
            for phase in summary['phases_failed']:
                print(f"  ❌ {phase}")

        print("\n" + "=" * 80 + "\n")


def main():
    """Main entry point for pipeline execution"""
    parser = argparse.ArgumentParser(
        description="Complete Hockey Stats Pipeline - Import, Calculate, Analyze",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete pipeline for season 10776
  python3 full_pipeline.py --season-id 10776

  # Run with custom configuration
  python3 full_pipeline.py --season-id 10776 --config custom_config.json

  # Use development preset
  python3 full_pipeline.py --season-id 10776 --preset development

  # Run specific phases only
  python3 full_pipeline.py --season-id 10776 --phase import
  python3 full_pipeline.py --season-id 10776 --phase stats
  python3 full_pipeline.py --season-id 10776 --phase quality

Available Phases:
  import   - Database setup and data import
  stats    - Basic statistics calculation
  advanced - Advanced metrics calculation
  quality  - Data quality analysis
  reports  - Generate reports
  all      - Run all phases (default)
        """
    )

    parser.add_argument(
        "--season-id",
        required=True,
        help="GameSheet season ID (e.g., 10776)"
    )

    parser.add_argument(
        "--config",
        help="Path to configuration file (JSON or YAML)"
    )

    parser.add_argument(
        "--preset",
        choices=['development', 'production', 'testing', 'minimal'],
        help="Use preset configuration"
    )

    parser.add_argument(
        "--phase",
        choices=['import', 'stats', 'advanced', 'quality', 'reports', 'all'],
        default='all',
        help="Run specific phase only (default: all)"
    )

    parser.add_argument(
        "--api-delay",
        type=float,
        help="Override API delay (seconds)"
    )

    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help="Override log level"
    )

    args = parser.parse_args()

    try:
        # Load configuration
        if args.config:
            config = PipelineConfig.from_file(args.config)
            config.season_id = args.season_id
        elif args.preset:
            preset_map = {
                'development': PresetConfigs.development,
                'production': PresetConfigs.production,
                'testing': PresetConfigs.testing,
                'minimal': PresetConfigs.minimal
            }
            config = preset_map[args.preset](args.season_id)
        else:
            config = PipelineConfig(season_id=args.season_id)

        # Apply overrides
        if args.api_delay:
            config.api_delay = args.api_delay
        if args.log_level:
            config.log_level = args.log_level

        # Validate configuration
        is_valid, errors = config.validate()
        if not is_valid:
            print("Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            return 1

        # Create orchestrator
        orchestrator = PipelineOrchestrator(config)

        # Run pipeline
        if args.phase == 'all':
            summary = orchestrator.run_all()
        else:
            # Run specific phase
            orchestrator.print_banner()
            orchestrator.stats['start_time'] = time.time()

            phase_map = {
                'import': orchestrator.phase1_database_setup,
                'stats': orchestrator.phase2_calculate_stats,
                'advanced': orchestrator.phase3_advanced_metrics,
                'quality': orchestrator.phase4_data_quality,
                'reports': orchestrator.phase5_generate_reports
            }

            phase_map[args.phase]()

            orchestrator.stats['end_time'] = time.time()
            orchestrator.stats['total_duration'] = orchestrator.stats['end_time'] - orchestrator.stats['start_time']
            summary = orchestrator._generate_summary()

        # Print summary
        orchestrator.print_final_summary(summary)

        return 0 if summary['success'] else 1

    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        return 130

    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
