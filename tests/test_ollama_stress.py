#!/usr/bin/env python3
"""
Hockey Stats Ollama Stress Test Suite
Tests edge cases, ambiguities, and complex reasoning to find failure points
"""

import sqlite3
import json
from typing import Dict, List, Any
from pathlib import Path

# Test configuration
DB_PATH = "advanced_hockey_stats_full.db"

class HockeyStressTest:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.results = []

    def run_all_tests(self):
        """Run all test categories"""
        print("=" * 80)
        print("HOCKEY STATS OLLAMA STRESS TEST SUITE")
        print("=" * 80)
        print()

        self.test_ambiguous_queries()
        self.test_multi_team_disambiguation()
        self.test_complex_comparisons()
        self.test_temporal_queries()
        self.test_edge_cases()
        self.test_aggregation_queries()
        self.test_player_queries()
        self.test_narrative_queries()

        self.print_summary()

    # ========================================================================
    # Test Category 1: Ambiguous Queries (Should Ask for Clarification)
    # ========================================================================

    def test_ambiguous_queries(self):
        """Test queries that need clarification"""
        print("\n" + "=" * 80)
        print("TEST CATEGORY 1: AMBIGUOUS QUERIES")
        print("Expected: System should ask for clarification")
        print("=" * 80)

        tests = [
            {
                "prompt": "show me all the WHK teams in a list",
                "expected_behavior": "List all WHK teams with division tags",
                "query": """
                    SELECT DISTINCT
                        t.team_name,
                        d.division_name,
                        t.club_name
                    FROM teams t
                    JOIN divisions d ON t.division_id = d.division_id
                    WHERE t.club_name LIKE '%WHK%' OR t.team_name LIKE '%WHK%'
                    ORDER BY d.division_name, t.team_name
                """,
                "test_type": "list_all_club_teams"
            },
            {
                "prompt": "whats the WHK u12 team PK %",
                "expected_behavior": "Should ask which U12 team (might be multiple)",
                "query": """
                    SELECT
                        t.team_name,
                        d.division_name,
                        ts.pk_percentage
                    FROM team_stats ts
                    JOIN teams t ON ts.team_id = t.team_id
                    JOIN divisions d ON t.division_id = d.division_id
                    WHERE (t.team_name LIKE '%WHK%' OR t.club_name LIKE '%WHK%')
                      AND (d.division_name LIKE '%U12%' OR d.division_name LIKE '%12U%')
                """,
                "test_type": "ambiguous_age_group"
            },
            {
                "prompt": "who's the best player",
                "expected_behavior": "Ask: best by what metric? (goals, assists, points, +/-)",
                "query": "SELECT * FROM player_stats ORDER BY points DESC LIMIT 10",
                "test_type": "undefined_superlative"
            },
            {
                "prompt": "how did they do last game",
                "expected_behavior": "Ask: which team?",
                "query": None,
                "test_type": "missing_context"
            },
            {
                "prompt": "compare the two top teams",
                "expected_behavior": "Ask: top by what? (points, wins, goal differential)",
                "query": "SELECT * FROM team_stats ORDER BY points DESC LIMIT 2",
                "test_type": "undefined_ranking"
            }
        ]

        for test in tests:
            self._run_test(test)

    # ========================================================================
    # Test Category 2: Multi-Team Disambiguation
    # ========================================================================

    def test_multi_team_disambiguation(self):
        """Test when multiple teams match criteria"""
        print("\n" + "=" * 80)
        print("TEST CATEGORY 2: MULTI-TEAM DISAMBIGUATION")
        print("Expected: Identify all matches, ask user to clarify")
        print("=" * 80)

        tests = [
            {
                "prompt": "Bay State Breakers stats",
                "expected_behavior": "Multiple teams named 'Bay State Breakers' in different divisions - list all, ask which one",
                "query": """
                    SELECT
                        t.team_name,
                        d.division_name,
                        ts.wins,
                        ts.losses,
                        ts.points
                    FROM teams t
                    JOIN divisions d ON t.division_id = d.division_id
                    LEFT JOIN team_stats ts ON t.team_id = ts.team_id
                    WHERE t.team_name LIKE '%Bay State Breakers%'
                """,
                "test_type": "duplicate_team_names"
            },
            {
                "prompt": "show me the Silver Lake team",
                "expected_behavior": "Multiple Silver Lake teams - list all divisions",
                "query": """
                    SELECT
                        t.team_name,
                        d.division_name,
                        t.club_name
                    FROM teams t
                    JOIN divisions d ON t.division_id = d.division_id
                    WHERE t.team_name LIKE '%Silver Lake%'
                """,
                "test_type": "multiple_divisions"
            }
        ]

        for test in tests:
            self._run_test(test)

    # ========================================================================
    # Test Category 3: Complex Comparisons
    # ========================================================================

    def test_complex_comparisons(self):
        """Test complex multi-team comparisons"""
        print("\n" + "=" * 80)
        print("TEST CATEGORY 3: COMPLEX COMPARISONS")
        print("Expected: Multi-step reasoning, aggregate multiple data points")
        print("=" * 80)

        tests = [
            {
                "prompt": "which WHK team has the best offense and defense combined",
                "expected_behavior": "Rank by (goals_for - goals_against) or goal_differential",
                "query": """
                    SELECT
                        t.team_name,
                        d.division_name,
                        ts.goals_for,
                        ts.goals_against,
                        ts.goal_differential,
                        ts.points
                    FROM team_stats ts
                    JOIN teams t ON ts.team_id = t.team_id
                    JOIN divisions d ON t.division_id = d.division_id
                    WHERE t.team_name LIKE '%WHK%' OR t.club_name LIKE '%WHK%'
                    ORDER BY ts.goal_differential DESC
                """,
                "test_type": "composite_metric"
            },
            {
                "prompt": "compare Bay State Breakers and Silver Lake head to head",
                "expected_behavior": "Find H2H records, but there are multiple teams with these names - need clarification",
                "query": """
                    SELECT
                        h2h.team_a_name,
                        h2h.team_b_name,
                        h2h.team_a_wins,
                        h2h.team_b_wins,
                        h2h.team_a_goals_for,
                        h2h.team_b_goals_for
                    FROM head_to_head h2h
                    WHERE (h2h.team_a_name LIKE '%Bay State Breakers%' AND h2h.team_b_name LIKE '%Silver Lake%')
                       OR (h2h.team_a_name LIKE '%Silver Lake%' AND h2h.team_b_name LIKE '%Bay State Breakers%')
                """,
                "test_type": "head_to_head_ambiguous"
            },
            {
                "prompt": "which teams have gotten better over time",
                "expected_behavior": "Analyze recent form (last 5 games) vs overall record",
                "query": """
                    SELECT
                        t.team_name,
                        d.division_name,
                        ts.wins,
                        ts.losses,
                        ts.last_5_record
                    FROM team_stats ts
                    JOIN teams t ON ts.team_id = t.team_id
                    JOIN divisions d ON t.division_id = d.division_id
                    WHERE ts.last_5_record IS NOT NULL
                    ORDER BY t.team_name
                """,
                "test_type": "temporal_trend_analysis"
            }
        ]

        for test in tests:
            self._run_test(test)

    # ========================================================================
    # Test Category 4: Temporal Queries
    # ========================================================================

    def test_temporal_queries(self):
        """Test time-based queries"""
        print("\n" + "=" * 80)
        print("TEST CATEGORY 4: TEMPORAL QUERIES")
        print("Expected: Understand time context, recent vs historical")
        print("=" * 80)

        tests = [
            {
                "prompt": "how have the Breakers been doing lately",
                "expected_behavior": "Show last 5 games (recent form)",
                "query": """
                    SELECT
                        t.team_name,
                        d.division_name,
                        ts.last_5_record,
                        ts.current_streak
                    FROM team_stats ts
                    JOIN teams t ON ts.team_id = t.team_id
                    JOIN divisions d ON t.division_id = d.division_id
                    WHERE t.team_name LIKE '%Breakers%'
                """,
                "test_type": "recent_form"
            },
            {
                "prompt": "show me teams on a winning streak",
                "expected_behavior": "Filter by current_streak > 0",
                "query": """
                    SELECT
                        t.team_name,
                        d.division_name,
                        ts.current_streak,
                        ts.last_5_record
                    FROM team_stats ts
                    JOIN teams t ON ts.team_id = t.team_id
                    JOIN divisions d ON t.division_id = d.division_id
                    WHERE ts.current_streak > 0
                    ORDER BY ts.current_streak DESC
                """,
                "test_type": "streak_filter"
            }
        ]

        for test in tests:
            self._run_test(test)

    # ========================================================================
    # Test Category 5: Edge Cases
    # ========================================================================

    def test_edge_cases(self):
        """Test edge cases and unusual scenarios"""
        print("\n" + "=" * 80)
        print("TEST CATEGORY 5: EDGE CASES")
        print("Expected: Handle gracefully, provide helpful feedback")
        print("=" * 80)

        tests = [
            {
                "prompt": "show me teams that don't exist",
                "expected_behavior": "Return no results, suggest similar teams",
                "query": "SELECT * FROM teams WHERE team_name LIKE '%NONEXISTENT%'",
                "test_type": "no_results"
            },
            {
                "prompt": "compare Bruins and Capitals",
                "expected_behavior": "These are NHL teams, not in our database - politely explain we only have Bay State/EHF data",
                "query": "SELECT * FROM teams WHERE team_name LIKE '%Bruins%' OR team_name LIKE '%Capitals%'",
                "test_type": "wrong_league"
            },
            {
                "prompt": "who won the championship",
                "expected_behavior": "Youth leagues don't have championships - explain structure, show top teams by division",
                "query": None,
                "test_type": "invalid_concept"
            },
            {
                "prompt": "what's the playoff schedule",
                "expected_behavior": "We only have regular season data, no playoff info",
                "query": None,
                "test_type": "missing_data_type"
            }
        ]

        for test in tests:
            self._run_test(test)

    # ========================================================================
    # Test Category 6: Aggregation Queries
    # ========================================================================

    def test_aggregation_queries(self):
        """Test queries requiring aggregation"""
        print("\n" + "=" * 80)
        print("TEST CATEGORY 6: AGGREGATION QUERIES")
        print("Expected: Aggregate across multiple records correctly")
        print("=" * 80)

        tests = [
            {
                "prompt": "which club has the most teams",
                "expected_behavior": "COUNT teams grouped by club_name",
                "query": """
                    SELECT
                        club_name,
                        COUNT(*) as team_count
                    FROM teams
                    GROUP BY club_name
                    ORDER BY team_count DESC
                    LIMIT 10
                """,
                "test_type": "club_aggregation"
            },
            {
                "prompt": "average goals per game in U12 divisions",
                "expected_behavior": "Calculate avg(goals_for) for U12 divisions",
                "query": """
                    SELECT
                        d.division_name,
                        AVG(ts.goals_for) as avg_goals_for,
                        AVG(ts.goals_against) as avg_goals_against,
                        COUNT(ts.team_id) as team_count
                    FROM team_stats ts
                    JOIN teams t ON ts.team_id = t.team_id
                    JOIN divisions d ON t.division_id = d.division_id
                    WHERE d.division_name LIKE '%U12%' OR d.division_name LIKE '%12U%'
                    GROUP BY d.division_name
                """,
                "test_type": "division_aggregation"
            },
            {
                "prompt": "total penalty minutes across all WHK teams",
                "expected_behavior": "SUM penalty_minutes for all WHK teams",
                "query": """
                    SELECT
                        SUM(ts.penalty_minutes) as total_pim,
                        COUNT(DISTINCT t.team_id) as team_count
                    FROM team_stats ts
                    JOIN teams t ON ts.team_id = t.team_id
                    WHERE t.team_name LIKE '%WHK%' OR t.club_name LIKE '%WHK%'
                """,
                "test_type": "sum_aggregation"
            }
        ]

        for test in tests:
            self._run_test(test)

    # ========================================================================
    # Test Category 7: Player Queries
    # ========================================================================

    def test_player_queries(self):
        """Test player-specific queries"""
        print("\n" + "=" * 80)
        print("TEST CATEGORY 7: PLAYER QUERIES")
        print("Expected: Handle player searches, stats, and comparisons")
        print("=" * 80)

        tests = [
            {
                "prompt": "top 10 goal scorers",
                "expected_behavior": "ORDER BY goals DESC LIMIT 10",
                "query": """
                    SELECT
                        ps.player_name,
                        t.team_name,
                        d.division_name,
                        ps.goals,
                        ps.assists,
                        ps.points
                    FROM player_stats ps
                    JOIN teams t ON ps.team_id = t.team_id
                    JOIN divisions d ON t.division_id = d.division_id
                    ORDER BY ps.goals DESC
                    LIMIT 10
                """,
                "test_type": "top_scorers"
            },
            {
                "prompt": "find player named Smith",
                "expected_behavior": "Likely multiple Smiths - show all, ask for clarification",
                "query": """
                    SELECT
                        ps.player_name,
                        t.team_name,
                        d.division_name,
                        ps.goals,
                        ps.assists,
                        ps.points
                    FROM player_stats ps
                    JOIN teams t ON ps.team_id = t.team_id
                    JOIN divisions d ON t.division_id = d.division_id
                    WHERE ps.player_name LIKE '%Smith%'
                    ORDER BY ps.points DESC
                """,
                "test_type": "common_name_search"
            },
            {
                "prompt": "who has the most penalty minutes",
                "expected_behavior": "ORDER BY penalty_minutes DESC",
                "query": """
                    SELECT
                        ps.player_name,
                        t.team_name,
                        d.division_name,
                        ps.penalty_minutes,
                        ps.games_played
                    FROM player_stats ps
                    JOIN teams t ON ps.team_id = t.team_id
                    JOIN divisions d ON t.division_id = d.division_id
                    ORDER BY ps.penalty_minutes DESC
                    LIMIT 10
                """,
                "test_type": "penalty_leaders"
            }
        ]

        for test in tests:
            self._run_test(test)

    # ========================================================================
    # Test Category 8: Narrative/Conversational Queries
    # ========================================================================

    def test_narrative_queries(self):
        """Test natural language narrative queries"""
        print("\n" + "=" * 80)
        print("TEST CATEGORY 8: NARRATIVE/CONVERSATIONAL QUERIES")
        print("Expected: Understand intent, provide context-aware responses")
        print("=" * 80)

        tests = [
            {
                "prompt": "tell me about the best defensive team",
                "expected_behavior": "Find team with best goals_against, provide narrative context",
                "query": """
                    SELECT
                        t.team_name,
                        d.division_name,
                        ts.goals_against,
                        ts.games_played,
                        ROUND(CAST(ts.goals_against AS FLOAT) / ts.games_played, 2) as goals_against_per_game
                    FROM team_stats ts
                    JOIN teams t ON ts.team_id = t.team_id
                    JOIN divisions d ON t.division_id = d.division_id
                    WHERE ts.games_played > 0
                    ORDER BY goals_against_per_game ASC
                    LIMIT 5
                """,
                "test_type": "narrative_best"
            },
            {
                "prompt": "why is team X ranked higher than team Y",
                "expected_behavior": "Compare points, wins, goal_differential, tiebreakers",
                "query": None,  # Would need specific teams
                "test_type": "explanation_query"
            },
            {
                "prompt": "should I be worried about our PK",
                "expected_behavior": "Need team context - ask which team, then compare PK% to league average",
                "query": """
                    SELECT
                        AVG(pk_percentage) as league_avg_pk
                    FROM team_stats
                    WHERE pk_percentage IS NOT NULL
                """,
                "test_type": "contextual_concern"
            }
        ]

        for test in tests:
            self._run_test(test)

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _run_test(self, test: Dict[str, Any]):
        """Run a single test"""
        print(f"\nTest: {test['test_type']}")
        print(f"Prompt: \"{test['prompt']}\"")
        print(f"Expected: {test['expected_behavior']}")

        if test['query']:
            try:
                cursor = self.conn.cursor()
                cursor.execute(test['query'])
                results = cursor.fetchall()

                print(f"Results: {len(results)} rows")

                # Show first 3 results
                for i, row in enumerate(results[:3]):
                    print(f"  Row {i+1}: {dict(row)}")

                if len(results) > 3:
                    print(f"  ... and {len(results) - 3} more")

                test['actual_results'] = len(results)
                test['sample_data'] = [dict(row) for row in results[:3]]
                test['status'] = 'PASS' if len(results) > 0 else 'NO_RESULTS'

            except Exception as e:
                print(f"ERROR: {str(e)}")
                test['status'] = 'ERROR'
                test['error'] = str(e)
        else:
            print("  [No query - behavioral test]")
            test['status'] = 'MANUAL_CHECK'

        self.results.append(test)
        print("-" * 80)

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        total = len(self.results)
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        no_results = len([r for r in self.results if r['status'] == 'NO_RESULTS'])
        errors = len([r for r in self.results if r['status'] == 'ERROR'])
        manual = len([r for r in self.results if r['status'] == 'MANUAL_CHECK'])

        print(f"\nTotal Tests: {total}")
        print(f"  ✓ Passed (returned data): {passed}")
        print(f"  ⚠ No Results: {no_results}")
        print(f"  ✗ Errors: {errors}")
        print(f"  ⊙ Manual Check Required: {manual}")

        # Export detailed results
        results_file = "test_results_ollama_stress.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\nDetailed results exported to: {results_file}")

        # Critical failures
        print("\n" + "=" * 80)
        print("CRITICAL FINDINGS FOR OLLAMA PROMPT ENGINEERING")
        print("=" * 80)

        print("\n1. Ambiguous Queries Needing Clarification:")
        for r in self.results:
            if r['test_type'] in ['ambiguous_age_group', 'duplicate_team_names', 'undefined_superlative']:
                print(f"   - {r['prompt']}")
                print(f"     → {r['expected_behavior']}")

        print("\n2. Queries With No Results (Edge Cases):")
        for r in self.results:
            if r['status'] == 'NO_RESULTS':
                print(f"   - {r['prompt']}")
                print(f"     → Should: {r['expected_behavior']}")

        print("\n3. Complex Multi-Step Reasoning Required:")
        for r in self.results:
            if r['test_type'] in ['composite_metric', 'temporal_trend_analysis', 'explanation_query']:
                print(f"   - {r['prompt']}")
                print(f"     → {r['expected_behavior']}")

if __name__ == "__main__":
    tester = HockeyStressTest(DB_PATH)
    tester.run_all_tests()
