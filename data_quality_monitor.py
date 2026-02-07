#!/usr/bin/env python3
"""
Data Quality Monitor for Hockey Stats System

Provides continuous monitoring, quality score calculation, issue detection,
and resolution tracking for hockey statistics data.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import argparse
from pathlib import Path


@dataclass
class QualityMetrics:
    """Quality metrics for different entities"""
    entity_type: str
    entity_id: str
    entity_name: str
    quality_score: float
    metrics: Dict[str, float]
    issues: List[str]
    recommendations: List[str]


@dataclass
class IssueResolution:
    """Track resolution of data quality issues"""
    issue_id: int
    resolved_by: str
    resolution_date: str
    resolution_notes: str
    verification_status: str


class DataQualityMonitor:
    """Monitor and track data quality over time"""

    def __init__(self, db_path: str):
        """Initialize monitor with database path"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_quality_tables()

    def _ensure_quality_tables(self):
        """Ensure data quality tracking tables exist"""
        # Main issues table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS data_quality_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT,
                entity_id TEXT,
                game_id TEXT,
                issue_type TEXT,
                issue_description TEXT,
                confidence_impact REAL,
                is_resolved BOOLEAN DEFAULT FALSE,
                resolution_notes TEXT,
                resolved_by TEXT,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Quality scores tracking table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS quality_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT,
                entity_id TEXT,
                score_type TEXT,
                score_value REAL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Quality monitoring log
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS quality_monitoring_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                overall_score REAL,
                total_issues INTEGER,
                critical_issues INTEGER,
                resolved_issues INTEGER,
                new_issues_since_last INTEGER,
                report_data TEXT
            )
        """)

        self.conn.commit()

    def calculate_player_quality_scores(self) -> List[Dict]:
        """
        Calculate comprehensive quality scores for all players.
        Returns detailed metrics for each player.
        """
        print("📊 Calculating Player Quality Scores...")

        scores = []

        # Check if we have goals table
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='goals'"
        )
        has_goals = cursor.fetchone() is not None

        if not has_goals:
            return self._calculate_basic_player_scores()

        # Get player statistics and quality metrics
        query = """
        WITH player_appearances AS (
            -- All player appearances in goals
            SELECT
                scorer_player_id as player_id,
                scorer_name as name,
                scorer_number as number,
                team_name,
                game_id
            FROM goals
            WHERE scorer_player_id IS NOT NULL

            UNION ALL

            SELECT
                assist1_player_id as player_id,
                assist1_name as name,
                assist1_number as number,
                team_name,
                game_id
            FROM goals
            WHERE assist1_player_id IS NOT NULL

            UNION ALL

            SELECT
                assist2_player_id as player_id,
                assist2_name as name,
                assist2_number as number,
                team_name,
                game_id
            FROM goals
            WHERE assist2_player_id IS NOT NULL
        ),
        player_stats AS (
            SELECT
                player_id,
                MAX(name) as player_name,
                MAX(team_name) as team_name,
                COUNT(DISTINCT number) as different_numbers,
                COUNT(DISTINCT game_id) as games_played,
                GROUP_CONCAT(DISTINCT number) as all_numbers
            FROM player_appearances
            GROUP BY player_id
        ),
        player_goals AS (
            SELECT
                scorer_player_id as player_id,
                COUNT(*) as goals
            FROM goals
            WHERE scorer_player_id IS NOT NULL
            GROUP BY scorer_player_id
        ),
        player_assists AS (
            SELECT
                player_id,
                COUNT(*) as assists
            FROM (
                SELECT assist1_player_id as player_id FROM goals WHERE assist1_player_id IS NOT NULL
                UNION ALL
                SELECT assist2_player_id as player_id FROM goals WHERE assist2_player_id IS NOT NULL
            )
            GROUP BY player_id
        ),
        player_penalties AS (
            SELECT
                player_id,
                COUNT(*) as penalties,
                SUM(duration_minutes) as penalty_minutes
            FROM penalties
            WHERE player_id IS NOT NULL
            GROUP BY player_id
        )
        SELECT
            s.player_id,
            s.player_name,
            s.team_name,
            s.different_numbers,
            s.games_played,
            s.all_numbers,
            COALESCE(g.goals, 0) as goals,
            COALESCE(a.assists, 0) as assists,
            COALESCE(p.penalties, 0) as penalties,
            COALESCE(p.penalty_minutes, 0) as penalty_minutes
        FROM player_stats s
        LEFT JOIN player_goals g ON s.player_id = g.player_id
        LEFT JOIN player_assists a ON s.player_id = a.player_id
        LEFT JOIN player_penalties p ON s.player_id = p.player_id
        ORDER BY (COALESCE(g.goals, 0) + COALESCE(a.assists, 0)) DESC
        """

        # Check if penalties table exists
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='penalties'"
        )
        has_penalties = cursor.fetchone() is not None

        if not has_penalties:
            # Simplified query without penalties
            query = query.replace(
                """player_penalties AS (
            SELECT
                player_id,
                COUNT(*) as penalties,
                SUM(duration_minutes) as penalty_minutes
            FROM penalties
            WHERE player_id IS NOT NULL
            GROUP BY player_id
        ),
        SELECT""",
                "SELECT"
            ).replace(
                "LEFT JOIN player_penalties p ON s.player_id = p.player_id",
                ""
            ).replace(
                "COALESCE(p.penalties, 0) as penalties,\n            COALESCE(p.penalty_minutes, 0) as penalty_minutes",
                "0 as penalties,\n            0 as penalty_minutes"
            )

        cursor = self.conn.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            metrics = {}
            issues = []
            recommendations = []

            # 1. Number Consistency Score
            number_consistency = 1.0 / max(1, row['different_numbers'])
            metrics['number_consistency'] = round(number_consistency, 3)

            if row['different_numbers'] > 1:
                issues.append(f"Wore {row['different_numbers']} different numbers: {row['all_numbers']}")
                recommendations.append("Verify correct jersey number with team roster")

            # 2. Name Availability Score
            name_available = bool(row['player_name'] and len(row['player_name'].strip()) > 0)
            metrics['name_availability'] = 1.0 if name_available else 0.0

            if not name_available:
                issues.append("Player name not available")
                recommendations.append("Update player name from official roster")

            # 3. Data Completeness Score
            total_points = row['goals'] + row['assists']
            games = row['games_played']

            data_completeness = 1.0
            if games == 0:
                data_completeness = 0.0
                issues.append("No game appearances recorded")
            elif total_points == 0:
                data_completeness = 0.5
                # Not necessarily an issue - player might not have scored

            metrics['data_completeness'] = round(data_completeness, 3)

            # 4. Stats Reasonableness Score
            stats_reasonable = 1.0

            # Check for suspiciously high totals
            if total_points > 100:
                stats_reasonable = 0.3
                issues.append(f"Suspiciously high point total: {total_points}")
                recommendations.append("Verify stats - may indicate data duplication")
            elif total_points > 50:
                stats_reasonable = 0.7
                # High but possible

            # Check for unreasonable points-per-game
            if games > 0:
                ppg = total_points / games
                if ppg > 10:
                    stats_reasonable = min(stats_reasonable, 0.2)
                    issues.append(f"Unrealistic PPG: {ppg:.1f}")
                    recommendations.append("Check for duplicate goal entries")

            metrics['stats_reasonableness'] = round(stats_reasonable, 3)

            # 5. Penalty Data Quality (if available)
            penalty_quality = 1.0
            if row['penalty_minutes'] > 100:
                penalty_quality = 0.5
                issues.append(f"Very high PIM: {row['penalty_minutes']}")
                recommendations.append("Verify penalty data")

            metrics['penalty_data_quality'] = round(penalty_quality, 3)

            # Calculate overall quality score
            # Weighted average: number (30%), name (20%), completeness (20%), reasonable (25%), penalties (5%)
            overall_score = (
                number_consistency * 0.30 +
                metrics['name_availability'] * 0.20 +
                data_completeness * 0.20 +
                stats_reasonable * 0.25 +
                penalty_quality * 0.05
            )

            quality_metrics = QualityMetrics(
                entity_type="player",
                entity_id=row['player_id'],
                entity_name=row['player_name'] or f"Player #{row['all_numbers']}",
                quality_score=round(overall_score, 3),
                metrics=metrics,
                issues=issues,
                recommendations=recommendations
            )

            scores.append(asdict(quality_metrics))

        print(f"  Calculated scores for {len(scores)} players")
        avg_score = sum(s['quality_score'] for s in scores) / len(scores) if scores else 0
        print(f"  Average player quality score: {avg_score:.3f}")

        return scores

    def _calculate_basic_player_scores(self) -> List[Dict]:
        """Calculate quality scores from basic player table"""
        scores = []

        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='players'"
        )
        if not cursor.fetchone():
            return []

        query = """
        SELECT
            p.player_api_id,
            p.player_name,
            p.jersey_number,
            t.team_name,
            p.goals,
            p.assists,
            p.penalty_minutes,
            p.games_played
        FROM players p
        JOIN teams t ON p.team_api_id = t.team_api_id
        """

        cursor = self.conn.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            metrics = {}
            issues = []
            recommendations = []

            name_available = bool(row['player_name'] and len(row['player_name'].strip()) > 0)
            number_available = bool(row['jersey_number'] and len(str(row['jersey_number']).strip()) > 0)

            metrics['number_consistency'] = 1.0 if number_available else 0.0
            metrics['name_availability'] = 1.0 if name_available else 0.0
            metrics['data_completeness'] = 1.0 if row['games_played'] > 0 else 0.0

            if not name_available:
                issues.append("No player name")
                recommendations.append("Add player name from roster")

            if not number_available:
                issues.append("No jersey number")
                recommendations.append("Add jersey number from roster")

            total_points = (row['goals'] or 0) + (row['assists'] or 0)
            stats_reasonable = 1.0

            if total_points > 100:
                stats_reasonable = 0.3
                issues.append(f"High point total: {total_points}")

            metrics['stats_reasonableness'] = stats_reasonable

            overall_score = (
                metrics['number_consistency'] * 0.4 +
                metrics['name_availability'] * 0.3 +
                metrics['data_completeness'] * 0.2 +
                stats_reasonable * 0.1
            )

            quality_metrics = QualityMetrics(
                entity_type="player",
                entity_id=str(row['player_api_id']),
                entity_name=row['player_name'] or f"Player #{row['jersey_number']}",
                quality_score=round(overall_score, 3),
                metrics=metrics,
                issues=issues,
                recommendations=recommendations
            )

            scores.append(asdict(quality_metrics))

        return scores

    def calculate_game_quality_scores(self) -> List[Dict]:
        """Calculate quality scores for all games"""
        print("🏒 Calculating Game Quality Scores...")

        scores = []

        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='games'"
        )
        if not cursor.fetchone():
            return []

        # Check for goals table
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='goals'"
        )
        has_goals = cursor.fetchone() is not None

        # Detect column names
        cursor = self.conn.execute("PRAGMA table_info(games)")
        columns = [row[1] for row in cursor.fetchall()]

        game_id_col = "game_api_id" if "game_api_id" in columns else "game_id"
        has_box_score_col = "has_box_score" if "has_box_score" in columns else "1"
        played_col = "played" if "played" in columns else "1"

        query = f"""
        SELECT
            {game_id_col} as game_id,
            game_date,
            home_team_name,
            visitor_team_name,
            home_score,
            visitor_score,
            status,
            {has_box_score_col} as has_box_score,
            {played_col} as played
        FROM games
        """

        if "played" in columns:
            query += " WHERE played = 1"
        elif "status" in columns:
            query += " WHERE status = 'final'"

        cursor = self.conn.execute(query)
        games = cursor.fetchall()

        for game in games:
            metrics = {}
            issues = []
            recommendations = []

            # 1. Score Data Completeness
            score_complete = 1.0
            if game['home_score'] is None or game['visitor_score'] is None:
                score_complete = 0.0
                issues.append("Missing final scores")
                recommendations.append("Update game with final scores")

            metrics['score_completeness'] = score_complete

            # 2. Box Score Data Availability
            box_score_quality = 0.0

            if has_goals and game['has_box_score']:
                goal_count = self.conn.execute(
                    "SELECT COUNT(*) as cnt FROM goals WHERE game_id = ?",
                    (str(game['game_id']),)
                ).fetchone()['cnt']

                expected_goals = (game['home_score'] or 0) + (game['visitor_score'] or 0)

                if goal_count == expected_goals:
                    box_score_quality = 1.0
                elif goal_count > 0:
                    box_score_quality = 0.7
                    issues.append(f"Incomplete box score: {goal_count}/{expected_goals} goals")
                    recommendations.append("Verify goal entries match final score")
                else:
                    box_score_quality = 0.3
                    issues.append("No goal details despite final score")
                    recommendations.append("Extract box score data")
            elif game['has_box_score']:
                box_score_quality = 0.5

            metrics['box_score_quality'] = round(box_score_quality, 3)

            # 3. Data Consistency
            consistency = 1.0

            # Check for unrealistic scores
            total_goals = (game['home_score'] or 0) + (game['visitor_score'] or 0)
            if total_goals > 20:
                consistency = 0.5
                issues.append(f"Unusually high scoring game: {total_goals} total goals")
                recommendations.append("Verify final scores")
            elif total_goals > 15:
                consistency = 0.8

            metrics['data_consistency'] = round(consistency, 3)

            # 4. Metadata Completeness
            metadata_complete = 1.0

            if not game['game_date']:
                metadata_complete -= 0.3
                issues.append("Missing game date")

            if not game['home_team_name'] or not game['visitor_team_name']:
                metadata_complete -= 0.4
                issues.append("Missing team names")

            metrics['metadata_completeness'] = round(max(0, metadata_complete), 3)

            # Calculate overall game quality score
            overall_score = (
                score_complete * 0.35 +
                box_score_quality * 0.30 +
                consistency * 0.20 +
                metadata_complete * 0.15
            )

            quality_metrics = QualityMetrics(
                entity_type="game",
                entity_id=str(game['game_id']),
                entity_name=f"{game['home_team_name']} vs {game['visitor_team_name']} ({game['game_date']})",
                quality_score=round(overall_score, 3),
                metrics=metrics,
                issues=issues,
                recommendations=recommendations
            )

            scores.append(asdict(quality_metrics))

        print(f"  Calculated scores for {len(scores)} games")
        avg_score = sum(s['quality_score'] for s in scores) / len(scores) if scores else 0
        print(f"  Average game quality score: {avg_score:.3f}")

        return scores

    def calculate_team_quality_scores(self) -> List[Dict]:
        """Calculate quality scores for all teams"""
        print("⭐ Calculating Team Quality Scores...")

        scores = []

        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='teams'"
        )
        if not cursor.fetchone():
            return []

        query = """
        SELECT
            t.team_api_id,
            t.team_name,
            t.division_name,
            t.games_played,
            t.wins,
            t.losses,
            t.ties,
            t.goals_for,
            t.goals_against,
            t.points,
            t.players_count
        FROM teams t
        """

        cursor = self.conn.execute(query)
        teams = cursor.fetchall()

        for team in teams:
            metrics = {}
            issues = []
            recommendations = []

            # 1. Record Completeness
            record_complete = 1.0
            games = team['games_played'] or 0

            if games == 0:
                record_complete = 0.0
                issues.append("No games played")
            else:
                recorded_games = (team['wins'] or 0) + (team['losses'] or 0) + (team['ties'] or 0)
                if recorded_games != games:
                    record_complete = 0.7
                    issues.append(f"Win/Loss/Tie doesn't match games played: {recorded_games} vs {games}")
                    recommendations.append("Recalculate team record")

            metrics['record_completeness'] = round(record_complete, 3)

            # 2. Roster Completeness
            roster_quality = 1.0
            player_count = team['players_count'] or 0

            if player_count == 0:
                roster_quality = 0.0
                issues.append("No players in roster")
                recommendations.append("Extract team roster data")
            elif player_count < 8:
                roster_quality = 0.5
                issues.append(f"Small roster: only {player_count} players")
                recommendations.append("Verify roster completeness")
            elif player_count > 25:
                roster_quality = 0.6
                issues.append(f"Unusually large roster: {player_count} players")
                recommendations.append("Check for duplicate players")

            metrics['roster_quality'] = round(roster_quality, 3)

            # 3. Stats Consistency
            stats_consistent = 1.0
            gf = team['goals_for'] or 0
            ga = team['goals_against'] or 0

            if games > 0:
                avg_gf = gf / games
                avg_ga = ga / games

                if avg_gf > 15 or avg_ga > 15:
                    stats_consistent = 0.5
                    issues.append(f"Unusual goals per game: {avg_gf:.1f} for, {avg_ga:.1f} against")
                    recommendations.append("Verify goal totals")

            metrics['stats_consistency'] = round(stats_consistent, 3)

            # Calculate overall team quality score
            overall_score = (
                record_complete * 0.40 +
                roster_quality * 0.40 +
                stats_consistent * 0.20
            )

            quality_metrics = QualityMetrics(
                entity_type="team",
                entity_id=str(team['team_api_id']),
                entity_name=team['team_name'],
                quality_score=round(overall_score, 3),
                metrics=metrics,
                issues=issues,
                recommendations=recommendations
            )

            scores.append(asdict(quality_metrics))

        print(f"  Calculated scores for {len(scores)} teams")
        avg_score = sum(s['quality_score'] for s in scores) / len(scores) if scores else 0
        print(f"  Average team quality score: {avg_score:.3f}")

        return scores

    def detect_new_issues(self) -> List[Dict]:
        """Detect new data quality issues since last check"""
        print("🔍 Detecting New Issues...")

        new_issues = []

        # Get timestamp of last monitoring run
        cursor = self.conn.execute("""
            SELECT MAX(monitor_timestamp) as last_check
            FROM quality_monitoring_log
        """)
        row = cursor.fetchone()
        last_check = row['last_check'] if row and row['last_check'] else None

        if not last_check:
            print("  First run - all issues are new")
            return []

        # Find issues created since last check
        cursor = self.conn.execute("""
            SELECT
                id,
                entity_type,
                entity_id,
                issue_type,
                issue_description,
                confidence_impact,
                created_at
            FROM data_quality_issues
            WHERE created_at > ?
            AND is_resolved = 0
            ORDER BY confidence_impact DESC, created_at DESC
        """, (last_check,))

        for row in cursor:
            new_issues.append({
                "id": row['id'],
                "entity_type": row['entity_type'],
                "entity_id": row['entity_id'],
                "issue_type": row['issue_type'],
                "description": row['issue_description'],
                "impact": row['confidence_impact'],
                "detected_at": row['created_at']
            })

        print(f"  Found {len(new_issues)} new issues since last check")
        return new_issues

    def resolve_issue(self, issue_id: int, resolved_by: str, notes: str) -> bool:
        """Mark an issue as resolved"""
        try:
            self.conn.execute("""
                UPDATE data_quality_issues
                SET is_resolved = 1,
                    resolved_by = ?,
                    resolved_at = ?,
                    resolution_notes = ?
                WHERE id = ?
            """, (resolved_by, datetime.now().isoformat(), notes, issue_id))
            self.conn.commit()

            print(f"✅ Issue #{issue_id} marked as resolved")
            return True
        except Exception as e:
            print(f"❌ Failed to resolve issue #{issue_id}: {e}")
            return False

    def get_unresolved_issues(self, severity: Optional[str] = None) -> List[Dict]:
        """Get all unresolved issues, optionally filtered by severity"""
        query = """
            SELECT
                id,
                entity_type,
                entity_id,
                game_id,
                issue_type,
                issue_description,
                confidence_impact,
                created_at
            FROM data_quality_issues
            WHERE is_resolved = 0
        """

        if severity:
            if severity == "critical":
                query += " AND confidence_impact > 0.5"
            elif severity == "warning":
                query += " AND confidence_impact BETWEEN 0.2 AND 0.5"
            elif severity == "info":
                query += " AND confidence_impact < 0.2"

        query += " ORDER BY confidence_impact DESC, created_at DESC"

        cursor = self.conn.execute(query)
        issues = []

        for row in cursor:
            issues.append({
                "id": row['id'],
                "entity_type": row['entity_type'],
                "entity_id": row['entity_id'],
                "game_id": row['game_id'],
                "issue_type": row['issue_type'],
                "description": row['issue_description'],
                "impact": row['confidence_impact'],
                "created_at": row['created_at']
            })

        return issues

    def generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        print("\n📊 Generating Comprehensive Quality Report")
        print("=" * 70)

        report = {
            "generated_at": datetime.now().isoformat(),
            "database": self.db_path,
            "player_scores": [],
            "game_scores": [],
            "team_scores": [],
            "issue_summary": {},
            "recommendations": [],
            "trends": {}
        }

        # Calculate all quality scores
        report["player_scores"] = self.calculate_player_quality_scores()
        report["game_scores"] = self.calculate_game_quality_scores()
        report["team_scores"] = self.calculate_team_quality_scores()

        # Issue summary
        unresolved = self.get_unresolved_issues()
        critical = self.get_unresolved_issues("critical")
        warnings = self.get_unresolved_issues("warning")

        report["issue_summary"] = {
            "total_unresolved": len(unresolved),
            "critical": len(critical),
            "warnings": len(warnings),
            "info": len(unresolved) - len(critical) - len(warnings)
        }

        # Overall statistics
        avg_player_score = sum(p['quality_score'] for p in report["player_scores"]) / len(report["player_scores"]) if report["player_scores"] else 0
        avg_game_score = sum(g['quality_score'] for g in report["game_scores"]) / len(report["game_scores"]) if report["game_scores"] else 0
        avg_team_score = sum(t['quality_score'] for t in report["team_scores"]) / len(report["team_scores"]) if report["team_scores"] else 0

        report["overall_statistics"] = {
            "average_player_quality": round(avg_player_score, 3),
            "average_game_quality": round(avg_game_score, 3),
            "average_team_quality": round(avg_team_score, 3),
            "overall_quality": round((avg_player_score + avg_game_score + avg_team_score) / 3, 3)
        }

        # Top recommendations
        all_recommendations = []
        for player in report["player_scores"]:
            if player['quality_score'] < 0.7:
                all_recommendations.extend(player['recommendations'])

        for game in report["game_scores"]:
            if game['quality_score'] < 0.7:
                all_recommendations.extend(game['recommendations'])

        # Count and prioritize recommendations
        rec_counts = Counter(all_recommendations)
        report["recommendations"] = [
            {"recommendation": rec, "count": count}
            for rec, count in rec_counts.most_common(10)
        ]

        # Save to monitoring log
        self._save_monitoring_log(report)

        return report

    def _save_monitoring_log(self, report: Dict[str, Any]):
        """Save monitoring results to database"""
        self.conn.execute("""
            INSERT INTO quality_monitoring_log
            (overall_score, total_issues, critical_issues, resolved_issues, report_data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            report["overall_statistics"]["overall_quality"],
            report["issue_summary"]["total_unresolved"],
            report["issue_summary"]["critical"],
            0,  # We'll calculate this later
            json.dumps(report, indent=2)
        ))
        self.conn.commit()

    def export_quality_report(self, output_path: str):
        """Generate and export comprehensive quality report as JSON"""
        report = self.generate_quality_report()

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Quality report exported to: {output_path}")
        return report

    def print_summary(self, report: Dict[str, Any]):
        """Print a human-readable summary of the quality report"""
        print("\n" + "=" * 70)
        print("📊 DATA QUALITY MONITORING SUMMARY")
        print("=" * 70)

        stats = report["overall_statistics"]
        print(f"\nOverall Quality Score: {stats['overall_quality']:.3f} / 1.0")
        print(f"\nEntity-Level Scores:")
        print(f"  Players: {stats['average_player_quality']:.3f}")
        print(f"  Games:   {stats['average_game_quality']:.3f}")
        print(f"  Teams:   {stats['average_team_quality']:.3f}")

        issues = report["issue_summary"]
        print(f"\nIssue Summary:")
        print(f"  Total Unresolved: {issues['total_unresolved']}")
        print(f"  Critical:         {issues['critical']}")
        print(f"  Warnings:         {issues['warnings']}")
        print(f"  Info:             {issues['info']}")

        if report["recommendations"]:
            print(f"\nTop Recommendations:")
            for i, rec in enumerate(report["recommendations"][:5], 1):
                print(f"  {i}. {rec['recommendation']} (affects {rec['count']} entities)")

        # Quality distribution
        low_quality_players = len([p for p in report["player_scores"] if p['quality_score'] < 0.5])
        medium_quality_players = len([p for p in report["player_scores"] if 0.5 <= p['quality_score'] < 0.8])
        high_quality_players = len([p for p in report["player_scores"] if p['quality_score'] >= 0.8])

        print(f"\nPlayer Quality Distribution:")
        print(f"  High (≥0.8):   {high_quality_players}")
        print(f"  Medium (0.5-0.8): {medium_quality_players}")
        print(f"  Low (<0.5):    {low_quality_players}")

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description="Monitor hockey stats data quality")
    parser.add_argument("--db", required=True, help="Path to SQLite database")
    parser.add_argument("--output", help="Output JSON report path")
    parser.add_argument("--resolve", type=int, help="Resolve issue by ID")
    parser.add_argument("--resolved-by", default="admin", help="Name of person resolving issue")
    parser.add_argument("--notes", help="Resolution notes")
    parser.add_argument("--list-issues", action="store_true", help="List all unresolved issues")
    parser.add_argument("--severity", choices=["critical", "warning", "info"], help="Filter issues by severity")

    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"❌ Database not found: {args.db}")
        return 1

    monitor = DataQualityMonitor(args.db)

    # Handle different operations
    if args.resolve:
        if not args.notes:
            print("❌ --notes required when resolving an issue")
            return 1
        monitor.resolve_issue(args.resolve, args.resolved_by, args.notes)

    elif args.list_issues:
        issues = monitor.get_unresolved_issues(args.severity)
        print(f"\n📋 Unresolved Issues ({len(issues)})")
        print("=" * 70)

        for issue in issues:
            severity = "CRITICAL" if issue['impact'] > 0.5 else "WARNING" if issue['impact'] > 0.2 else "INFO"
            print(f"\nIssue #{issue['id']} [{severity}]")
            print(f"  Type: {issue['issue_type']}")
            print(f"  Entity: {issue['entity_type']} {issue['entity_id']}")
            print(f"  Description: {issue['description']}")
            print(f"  Impact: {issue['impact']:.2f}")
            print(f"  Created: {issue['created_at']}")

    else:
        # Generate full quality report
        report = monitor.generate_quality_report()

        # Print summary
        monitor.print_summary(report)

        # Export if requested
        if args.output:
            monitor.export_quality_report(args.output)
        else:
            # Default export path
            db_name = Path(args.db).stem
            output_path = f"quality_report_{db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n💾 Report saved to: {output_path}")

    monitor.close()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
