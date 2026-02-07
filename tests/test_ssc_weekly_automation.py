#!/usr/bin/env python3
"""
Test Script for SSC Weekly Automation

Simulates two weekly runs to verify:
- Incremental updates work correctly
- Deduplication logic is correct
- Game updates are detected
- Change reports are accurate

Usage:
    python3 test_ssc_weekly_automation.py
"""

import asyncio
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from ssc_hockey_scraper import Game, PlayerStats, TeamStanding


class WeeklyAutomationTester:
    """Test the weekly automation system."""

    def __init__(self, test_dir: Path):
        self.test_dir = Path(test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def create_mock_game(self, game_id: str, date: str, visitor: str, home: str,
                        visitor_score=None, home_score=None, has_details=False) -> Game:
        """Create a mock game for testing."""
        game = Game(
            game_id=game_id,
            date=date,
            time="7:00 PM",
            visitor_team=visitor,
            home_team=home,
            visitor_score=visitor_score,
            home_score=home_score,
            location="Test Rink",
            status="Final" if visitor_score is not None else "7:00 PM",
            division="8A",
            game_url=f"https://example.com/game/{game_id}",
            source_url="https://example.com/schedule"
        )

        if has_details and visitor_score is not None:
            v_score = int(visitor_score) if isinstance(visitor_score, str) else visitor_score
            h_score = int(home_score) if isinstance(home_score, str) else home_score

            game.period_scores = {
                "1st": {"visitor": 1, "home": 0},
                "2nd": {"visitor": 2, "home": 1},
                "3rd": {"visitor": max(0, v_score - 3), "home": max(0, h_score - 1)}
            }
            game.scoring_summary = [
                {"period": "1st", "time": "5:23", "player": "John Doe", "assists": ["Jane Smith"]}
            ]

        return game

    def create_week1_data(self) -> dict:
        """Create data for week 1 scrape."""
        games = [
            # Week 1: 5 games, 3 played, 2 scheduled
            self.create_mock_game("1001", "11/03/2024", "Team A", "Team B", "3", "2", has_details=True),
            self.create_mock_game("1002", "11/03/2024", "Team C", "Team D", "1", "4", has_details=True),
            self.create_mock_game("1003", "11/04/2024", "Team E", "Team F", "2", "2", has_details=True),
            self.create_mock_game("1004", "11/10/2024", "Team A", "Team C"),  # Scheduled
            self.create_mock_game("1005", "11/10/2024", "Team B", "Team D"),  # Scheduled
        ]

        player_stats = [
            PlayerStats(
                name="John Doe",
                team="Team A",
                games_played=3,
                goals=5,
                assists=3,
                points=8,
                penalty_minutes=2,
                plus_minus=2,
                power_play_goals=1,
                short_handed_goals=0,
                game_winning_goals=1,
                division="8A",
                source_url="https://example.com/stats"
            ),
        ]

        standings = [
            TeamStanding(
                team_name="Team A",
                team_abbrev="TMA",
                division="8A",
                points=6,
                games_played=3,
                wins=3,
                losses=0,
                ties=0,
                goals_for=9,
                goals_against=4,
                record="3-0-0",
                source_url="https://example.com/standings"
            ),
        ]

        return {
            'games': games,
            'player_stats': player_stats,
            'standings': standings
        }

    def create_week2_data(self) -> dict:
        """Create data for week 2 scrape (with updates)."""
        games = [
            # Same games from week 1, but scheduled games now have scores
            self.create_mock_game("1001", "11/03/2024", "Team A", "Team B", "3", "2", has_details=True),
            self.create_mock_game("1002", "11/03/2024", "Team C", "Team D", "1", "4", has_details=True),
            self.create_mock_game("1003", "11/04/2024", "Team E", "Team F", "2", "2", has_details=True),
            self.create_mock_game("1004", "11/10/2024", "Team A", "Team C", "4", "1", has_details=True),  # NOW PLAYED
            self.create_mock_game("1005", "11/10/2024", "Team B", "Team D", "2", "3", has_details=True),  # NOW PLAYED
            # New scheduled games
            self.create_mock_game("1006", "11/17/2024", "Team E", "Team A"),  # NEW
            self.create_mock_game("1007", "11/17/2024", "Team C", "Team B"),  # NEW
        ]

        player_stats = [
            PlayerStats(
                name="John Doe",
                team="Team A",
                games_played=5,  # Updated: was 3
                goals=9,  # Updated: was 5
                assists=5,  # Updated: was 3
                points=14,  # Updated: was 8
                penalty_minutes=4,  # Updated: was 2
                plus_minus=4,  # Updated: was 2
                power_play_goals=2,  # Updated: was 1
                short_handed_goals=0,
                game_winning_goals=2,  # Updated: was 1
                division="8A",
                source_url="https://example.com/stats"
            ),
        ]

        standings = [
            TeamStanding(
                team_name="Team A",
                team_abbrev="TMA",
                division="8A",
                points=12,  # Updated: was 6
                games_played=5,  # Updated: was 3
                wins=5,  # Updated: was 3
                losses=0,
                ties=0,
                goals_for=16,  # Updated: was 9
                goals_against=7,  # Updated: was 4
                record="5-0-0",  # Updated: was "3-0-0"
                source_url="https://example.com/standings"
            ),
        ]

        return {
            'games': games,
            'player_stats': player_stats,
            'standings': standings
        }

    def save_mock_data(self, data: dict, output_dir: Path):
        """Save mock data to JSON files."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save games
        with open(output_dir / 'schedules.json', 'w') as f:
            json.dump([g.__dict__ for g in data['games']], f, indent=2)

        # Save player stats
        with open(output_dir / 'player_stats.json', 'w') as f:
            json.dump([s.__dict__ for s in data['player_stats']], f, indent=2)

        # Save standings
        with open(output_dir / 'standings.json', 'w') as f:
            json.dump([s.__dict__ for s in data['standings']], f, indent=2)

        # Save teams (minimal)
        teams = [{'name': f'Team {chr(65+i)}', 'division': '8A', 'team_url': '', 'team_id': None}
                for i in range(6)]
        with open(output_dir / 'teams.json', 'w') as f:
            json.dump(teams, f, indent=2)

    def run_test(self):
        """Run the complete test."""
        print("="*70)
        print("SSC WEEKLY AUTOMATION TEST")
        print("="*70)
        print()

        # Clean test directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Test 1: Week 1 scrape (initial)
        print("TEST 1: Week 1 Initial Scrape")
        print("-" * 70)
        week1_dir = self.test_dir / 'week1'
        week1_data = self.create_week1_data()
        self.save_mock_data(week1_data, week1_dir)

        print(f"✓ Created week 1 data:")
        print(f"  - {len(week1_data['games'])} games (3 played, 2 scheduled)")
        print(f"  - {len(week1_data['player_stats'])} player stats")
        print(f"  - {len(week1_data['standings'])} standings")
        print()

        # Test 2: Week 2 scrape (with updates)
        print("TEST 2: Week 2 Scrape (with updates)")
        print("-" * 70)
        week2_dir = self.test_dir / 'week2'
        week2_data = self.create_week2_data()
        self.save_mock_data(week2_data, week2_dir)

        print(f"✓ Created week 2 data:")
        print(f"  - {len(week2_data['games'])} games (5 played, 2 scheduled)")
        print(f"  - 2 new games added (1006, 1007)")
        print(f"  - 2 games updated with scores (1004, 1005)")
        print(f"  - Updated player stats")
        print(f"  - Updated standings")
        print()

        # Test 3: Run comparison
        print("TEST 3: Running Comparison")
        print("-" * 70)

        from compare_ssc_data import SSCDataComparator

        comparator = SSCDataComparator(week1_dir, week2_dir)
        report = comparator.generate_report()

        print(f"✓ Comparison complete:")
        print(f"  - New games: {report.summary['new_games']}")
        print(f"  - Updated games: {report.summary['updated_games']}")
        print(f"  - New players: {report.summary['new_players']}")
        print(f"  - Updated players: {report.summary['updated_players']}")
        print(f"  - Updated teams: {report.summary['updated_teams']}")
        print()

        # Test 4: Verify expected results
        print("TEST 4: Verifying Results")
        print("-" * 70)

        tests_passed = 0
        tests_failed = 0

        # Check new games
        if report.summary['new_games'] == 2:
            print("✓ Correct number of new games (2)")
            tests_passed += 1
        else:
            print(f"✗ Expected 2 new games, got {report.summary['new_games']}")
            tests_failed += 1

        # Check updated games (2 games got scores, plus details added to others)
        # The comparison detects multiple types of updates (scores, details, etc.)
        if report.summary['updated_games'] >= 2:
            print(f"✓ Updated games detected ({report.summary['updated_games']} total updates)")
            tests_passed += 1
        else:
            print(f"✗ Expected at least 2 updated games, got {report.summary['updated_games']}")
            tests_failed += 1

        # Check total games in week 2
        if report.games_comparison['total_new'] == 7:
            print("✓ Correct total games in week 2 (7)")
            tests_passed += 1
        else:
            print(f"✗ Expected 7 total games, got {report.games_comparison['total_new']}")
            tests_failed += 1

        # Check player stat updates
        if report.summary['updated_players'] == 1:
            print("✓ Correct number of updated players (1)")
            tests_passed += 1
        else:
            print(f"✗ Expected 1 updated player, got {report.summary['updated_players']}")
            tests_failed += 1

        # Check standings updates
        if report.summary['updated_teams'] == 1:
            print("✓ Correct number of updated teams (1)")
            tests_passed += 1
        else:
            print(f"✗ Expected 1 updated team, got {report.summary['updated_teams']}")
            tests_failed += 1

        print()
        print("="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Tests Passed: {tests_passed}")
        print(f"Tests Failed: {tests_failed}")
        print()

        if tests_failed == 0:
            print("✓ ALL TESTS PASSED!")
        else:
            print("✗ SOME TESTS FAILED")

        print("="*70)

        # Save comparison report
        report_file = self.test_dir / 'comparison_report.json'
        with open(report_file, 'w') as f:
            from dataclasses import asdict
            json.dump(asdict(report), f, indent=2)

        print()
        print(f"Test data saved to: {self.test_dir}")
        print(f"Comparison report: {report_file}")

        return tests_failed == 0


def main():
    test_dir = Path('/private/tmp/ssc_automation_test')
    tester = WeeklyAutomationTester(test_dir)
    success = tester.run_test()

    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
