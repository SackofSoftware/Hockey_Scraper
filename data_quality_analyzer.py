#!/usr/bin/env python3
"""
Data Quality Analyzer for Hockey Stats System

Analyzes player number consistency, calculates confidence scores,
detects missing/suspect data, and flags games with incomplete data.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import argparse
from pathlib import Path


@dataclass
class PlayerNumberIssue:
    """Track player number inconsistencies"""
    player_id: str
    player_name: str
    team_id: int
    team_name: str
    numbers_used: List[str]
    games_count: int
    consistency_score: float
    issue_type: str
    details: str


@dataclass
class GameDataQualityIssue:
    """Track game-level data quality issues"""
    game_id: str
    game_date: str
    home_team: str
    visitor_team: str
    issue_type: str
    severity: str  # 'critical', 'warning', 'info'
    description: str
    affected_entities: List[str]


@dataclass
class PlayerConfidenceScore:
    """Calculate overall confidence score for a player"""
    player_id: str
    player_name: str
    team_name: str
    number_consistency: float  # 0.0 to 1.0
    name_available: bool
    games_played: int
    goals: int
    assists: int
    overall_confidence: float  # 0.0 to 1.0
    flags: List[str]


class DataQualityAnalyzer:
    """Analyze hockey stats data quality"""

    def __init__(self, db_path: str):
        """Initialize analyzer with database path"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.issues = []
        self.player_scores = []

    def analyze_all(self) -> Dict[str, Any]:
        """Run complete data quality analysis"""
        print("🔍 Starting Data Quality Analysis")
        print("=" * 70)

        results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "database": self.db_path,
            "player_number_issues": [],
            "game_quality_issues": [],
            "player_confidence_scores": [],
            "duplicate_players": [],
            "missing_data_summary": {},
            "overall_quality_score": 0.0
        }

        # 1. Analyze player number consistency
        print("\n📊 Phase 1: Analyzing Player Number Consistency...")
        results["player_number_issues"] = self.analyze_player_number_consistency()

        # 2. Calculate player confidence scores
        print("\n📈 Phase 2: Calculating Player Confidence Scores...")
        results["player_confidence_scores"] = self.calculate_player_confidence_scores()

        # 3. Detect duplicate players
        print("\n🔎 Phase 3: Detecting Duplicate Players...")
        results["duplicate_players"] = self.detect_duplicate_players()

        # 4. Analyze game data quality
        print("\n🏒 Phase 4: Analyzing Game Data Quality...")
        results["game_quality_issues"] = self.analyze_game_quality()

        # 5. Missing data summary
        print("\n📋 Phase 5: Summarizing Missing Data...")
        results["missing_data_summary"] = self.analyze_missing_data()

        # 6. Calculate overall quality score
        print("\n🎯 Phase 6: Calculating Overall Quality Score...")
        results["overall_quality_score"] = self.calculate_overall_quality_score(results)

        print("\n✅ Analysis Complete!")
        return results

    def analyze_player_number_consistency(self) -> List[Dict]:
        """
        Analyze if players consistently wear the same number across games.
        Returns list of players with number inconsistencies.
        """
        issues = []

        # Check if goals table exists
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='goals'"
        )
        has_goals_table = cursor.fetchone() is not None

        if not has_goals_table:
            print("  ⚠️  Goals table not found - cannot analyze number consistency from box scores")
            # Fall back to basic player table analysis
            return self._analyze_player_number_from_roster()

        # Query to find players with multiple numbers
        query = """
        WITH all_player_appearances AS (
            SELECT
                scorer_player_id as player_id,
                scorer_name as player_name,
                scorer_number as number,
                team_name,
                game_id
            FROM goals
            WHERE scorer_player_id IS NOT NULL AND scorer_number IS NOT NULL

            UNION ALL

            SELECT
                assist1_player_id as player_id,
                assist1_name as player_name,
                assist1_number as number,
                team_name,
                game_id
            FROM goals
            WHERE assist1_player_id IS NOT NULL AND assist1_number IS NOT NULL

            UNION ALL

            SELECT
                assist2_player_id as player_id,
                assist2_name as player_name,
                assist2_number as number,
                team_name,
                game_id
            FROM goals
            WHERE assist2_player_id IS NOT NULL AND assist2_number IS NOT NULL
        ),
        player_number_counts AS (
            SELECT
                player_id,
                number,
                MAX(player_name) as player_name,
                team_name,
                COUNT(DISTINCT game_id) as games_with_number
            FROM all_player_appearances
            GROUP BY player_id, number, team_name
        ),
        player_summary AS (
            SELECT
                player_id,
                MAX(player_name) as player_name,
                MAX(team_name) as team_name,
                COUNT(DISTINCT number) as different_numbers,
                GROUP_CONCAT(DISTINCT number || '(' || games_with_number || 'g)') as numbers_detail,
                SUM(games_with_number) as total_games
            FROM player_number_counts
            GROUP BY player_id
            HAVING COUNT(DISTINCT number) > 1
        )
        SELECT * FROM player_summary
        ORDER BY different_numbers DESC, total_games DESC
        """

        cursor = self.conn.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            numbers = row['numbers_detail'].split(',')
            consistency_score = 1.0 / row['different_numbers']  # More numbers = lower score

            issue = PlayerNumberIssue(
                player_id=row['player_id'],
                player_name=row['player_name'] or "Unknown",
                team_id=0,  # Not available from this query
                team_name=row['team_name'],
                numbers_used=[n.strip() for n in numbers],
                games_count=row['total_games'],
                consistency_score=round(consistency_score, 3),
                issue_type="number_inconsistency",
                details=f"Player wore {row['different_numbers']} different numbers across {row['total_games']} games"
            )
            issues.append(asdict(issue))

        print(f"  Found {len(issues)} players with number inconsistencies")
        return issues

    def _analyze_player_number_from_roster(self) -> List[Dict]:
        """Fall back to analyzing player numbers from roster table"""
        issues = []

        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='players'"
        )
        if not cursor.fetchone():
            print("  ⚠️  Players table not found")
            return []

        # This is simpler - just check if same player_id has different jersey numbers
        # (In current schema, each player_api_id should have one number)
        return []

    def calculate_player_confidence_scores(self) -> List[Dict]:
        """
        Calculate comprehensive confidence score for each player.
        Score based on: number consistency, name availability, stats reasonableness.
        """
        scores = []

        # Check if we have advanced tables
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='goals'"
        )
        has_goals = cursor.fetchone() is not None

        if not has_goals:
            return self._calculate_basic_confidence_scores()

        # Get all unique players with their stats
        query = """
        WITH player_goal_stats AS (
            SELECT
                scorer_player_id as player_id,
                scorer_name as player_name,
                scorer_number as number,
                team_name,
                COUNT(*) as goals
            FROM goals
            WHERE scorer_player_id IS NOT NULL
            GROUP BY scorer_player_id, team_name
        ),
        player_assist_stats AS (
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
        player_number_consistency AS (
            SELECT
                player_id,
                COUNT(DISTINCT number) as different_numbers,
                COUNT(DISTINCT game_id) as games
            FROM (
                SELECT scorer_player_id as player_id, scorer_number as number, game_id FROM goals WHERE scorer_player_id IS NOT NULL
                UNION ALL
                SELECT assist1_player_id as player_id, assist1_number as number, game_id FROM goals WHERE assist1_player_id IS NOT NULL
                UNION ALL
                SELECT assist2_player_id as player_id, assist2_number as number, game_id FROM goals WHERE assist2_player_id IS NOT NULL
            )
            GROUP BY player_id
        )
        SELECT
            g.player_id,
            g.player_name,
            g.team_name,
            g.number,
            g.goals,
            COALESCE(a.assists, 0) as assists,
            nc.different_numbers,
            nc.games
        FROM player_goal_stats g
        LEFT JOIN player_assist_stats a ON g.player_id = a.player_id
        LEFT JOIN player_number_consistency nc ON g.player_id = nc.player_id
        ORDER BY (g.goals + COALESCE(a.assists, 0)) DESC
        """

        cursor = self.conn.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            # Calculate number consistency (1.0 = always same number)
            number_consistency = 1.0
            if row['different_numbers'] and row['different_numbers'] > 1:
                number_consistency = 1.0 / row['different_numbers']

            # Check name availability
            name_available = bool(row['player_name'] and len(row['player_name'].strip()) > 0)

            # Calculate overall confidence
            # Factors: number consistency (50%), name available (30%), reasonable stats (20%)
            confidence = 0.0
            flags = []

            # Number consistency component
            confidence += number_consistency * 0.5
            if number_consistency < 0.5:
                flags.append(f"inconsistent_number ({row['different_numbers']} different)")

            # Name availability component
            if name_available:
                confidence += 0.3
            else:
                flags.append("no_name")

            # Stats reasonableness component (0.2 points)
            total_points = row['goals'] + row['assists']
            if total_points > 0 and total_points < 100:  # Reasonable range
                confidence += 0.2
            elif total_points >= 100:
                confidence += 0.1
                flags.append(f"suspiciously_high_points ({total_points})")
            elif total_points == 0:
                confidence += 0.1
                flags.append("no_points")

            score = PlayerConfidenceScore(
                player_id=row['player_id'],
                player_name=row['player_name'] or "",
                team_name=row['team_name'],
                number_consistency=round(number_consistency, 3),
                name_available=name_available,
                games_played=row['games'] or 0,
                goals=row['goals'] or 0,
                assists=row['assists'] or 0,
                overall_confidence=round(confidence, 3),
                flags=flags
            )
            scores.append(asdict(score))

        print(f"  Calculated confidence scores for {len(scores)} players")
        avg_confidence = sum(s['overall_confidence'] for s in scores) / len(scores) if scores else 0
        print(f"  Average confidence score: {avg_confidence:.3f}")

        return scores

    def _calculate_basic_confidence_scores(self) -> List[Dict]:
        """Calculate basic confidence scores from simple player table"""
        scores = []

        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='players'"
        )
        if not cursor.fetchone():
            return []

        query = """
        SELECT
            p.player_api_id as player_id,
            p.player_name,
            p.jersey_number,
            t.team_name,
            p.goals,
            p.assists,
            p.games_played
        FROM players p
        JOIN teams t ON p.team_api_id = t.team_api_id
        """

        cursor = self.conn.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            name_available = bool(row['player_name'] and len(row['player_name'].strip()) > 0)
            number_available = bool(row['jersey_number'] and len(str(row['jersey_number']).strip()) > 0)

            confidence = 0.0
            flags = []

            # Number available (50%)
            if number_available:
                confidence += 0.5
            else:
                flags.append("no_number")

            # Name available (30%)
            if name_available:
                confidence += 0.3
            else:
                flags.append("no_name")

            # Stats reasonableness (20%)
            total_points = (row['goals'] or 0) + (row['assists'] or 0)
            if total_points > 0 and total_points < 100:
                confidence += 0.2
            elif total_points == 0:
                confidence += 0.1
                flags.append("no_points")
            elif total_points >= 100:
                confidence += 0.1
                flags.append(f"suspiciously_high_points ({total_points})")

            score = PlayerConfidenceScore(
                player_id=str(row['player_id']),
                player_name=row['player_name'] or "",
                team_name=row['team_name'],
                number_consistency=1.0 if number_available else 0.0,
                name_available=name_available,
                games_played=row['games_played'] or 0,
                goals=row['goals'] or 0,
                assists=row['assists'] or 0,
                overall_confidence=round(confidence, 3),
                flags=flags
            )
            scores.append(asdict(score))

        print(f"  Calculated basic confidence scores for {len(scores)} players")
        return scores

    def detect_duplicate_players(self) -> List[Dict]:
        """
        Detect potential duplicate player entries.
        Look for: same name + team, same number + team, suspiciously similar entries.
        """
        duplicates = []

        # Check if we have goals table
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='goals'"
        )
        has_goals = cursor.fetchone() is not None

        if not has_goals:
            return self._detect_basic_duplicates()

        # Find players with same number on same team
        query = """
        WITH player_info AS (
            SELECT DISTINCT
                scorer_player_id as player_id,
                scorer_name as player_name,
                scorer_number as number,
                team_name
            FROM goals
            WHERE scorer_player_id IS NOT NULL AND scorer_number IS NOT NULL
        ),
        number_conflicts AS (
            SELECT
                team_name,
                number,
                COUNT(DISTINCT player_id) as player_count,
                GROUP_CONCAT(player_id || ':' || COALESCE(player_name, 'Unknown')) as players
            FROM player_info
            GROUP BY team_name, number
            HAVING COUNT(DISTINCT player_id) > 1
        )
        SELECT * FROM number_conflicts
        ORDER BY player_count DESC
        """

        cursor = self.conn.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            duplicates.append({
                "issue_type": "same_number_multiple_players",
                "team": row['team_name'],
                "number": row['number'],
                "player_count": row['player_count'],
                "players": row['players'],
                "severity": "warning",
                "description": f"{row['player_count']} different players wore #{row['number']} for {row['team_name']}"
            })

        print(f"  Found {len(duplicates)} potential duplicate/number conflicts")
        return duplicates

    def _detect_basic_duplicates(self) -> List[Dict]:
        """Detect duplicates in basic player table"""
        duplicates = []

        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='players'"
        )
        if not cursor.fetchone():
            return []

        # Find players with same number on same team
        query = """
        SELECT
            t.team_name,
            p.jersey_number,
            COUNT(*) as count,
            GROUP_CONCAT(p.player_api_id || ':' || COALESCE(p.player_name, 'Unknown')) as players
        FROM players p
        JOIN teams t ON p.team_api_id = t.team_api_id
        WHERE p.jersey_number IS NOT NULL
        GROUP BY t.team_name, p.jersey_number
        HAVING COUNT(*) > 1
        """

        cursor = self.conn.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            duplicates.append({
                "issue_type": "same_number_multiple_players",
                "team": row['team_name'],
                "number": row['jersey_number'],
                "player_count": row['count'],
                "players": row['players'],
                "severity": "warning",
                "description": f"{row['count']} players have #{row['jersey_number']} for {row['team_name']}"
            })

        return duplicates

    def analyze_game_quality(self) -> List[Dict]:
        """
        Analyze data quality for each game.
        Flag games with: missing scores, incomplete rosters, no goals/penalties data.
        """
        issues = []

        # Check what tables we have
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='games'"
        )
        if not cursor.fetchone():
            print("  ⚠️  Games table not found")
            return []

        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='goals'"
        )
        has_goals = cursor.fetchone() is not None

        # Analyze games - detect column names
        cursor = self.conn.execute("PRAGMA table_info(games)")
        columns = [row[1] for row in cursor.fetchall()]

        # Adapt query based on available columns
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
            game_issues = []
            severity = "info"

            # Check for missing scores
            if game['home_score'] is None or game['visitor_score'] is None:
                game_issues.append("missing_scores")
                severity = "critical"

            # Check if box score flag is set but no box score data exists
            if game['has_box_score'] and has_goals:
                goal_count = self.conn.execute(
                    "SELECT COUNT(*) as cnt FROM goals WHERE game_id = ?",
                    (str(game['game_id']),)
                ).fetchone()['cnt']

                if goal_count == 0 and (game['home_score'] or 0) + (game['visitor_score'] or 0) > 0:
                    game_issues.append("box_score_missing")
                    severity = "warning"

            # Check for unrealistic scores
            total_goals = (game['home_score'] or 0) + (game['visitor_score'] or 0)
            if total_goals > 20:
                game_issues.append(f"unusually_high_scoring ({total_goals} total goals)")
                severity = "warning"

            if game_issues:
                issue = GameDataQualityIssue(
                    game_id=str(game['game_id']),
                    game_date=game['game_date'] or "Unknown",
                    home_team=game['home_team_name'] or "Unknown",
                    visitor_team=game['visitor_team_name'] or "Unknown",
                    issue_type="incomplete_game_data",
                    severity=severity,
                    description=", ".join(game_issues),
                    affected_entities=game_issues
                )
                issues.append(asdict(issue))

        print(f"  Found {len(issues)} games with quality issues")
        return issues

    def analyze_missing_data(self) -> Dict[str, Any]:
        """
        Summarize missing data across all tables.
        Returns counts and percentages of missing key fields.
        """
        summary = {
            "players": {},
            "games": {},
            "goals": {},
            "penalties": {}
        }

        # Players missing data
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='players'"
        )
        if cursor.fetchone():
            total_players = self.conn.execute("SELECT COUNT(*) as cnt FROM players").fetchone()['cnt']
            missing_names = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM players WHERE player_name IS NULL OR player_name = ''"
            ).fetchone()['cnt']
            missing_numbers = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM players WHERE jersey_number IS NULL OR jersey_number = ''"
            ).fetchone()['cnt']

            summary["players"] = {
                "total": total_players,
                "missing_names": missing_names,
                "missing_names_pct": round(100 * missing_names / max(1, total_players), 1),
                "missing_numbers": missing_numbers,
                "missing_numbers_pct": round(100 * missing_numbers / max(1, total_players), 1)
            }

        # Games missing data
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='games'"
        )
        if cursor.fetchone():
            total_games = self.conn.execute("SELECT COUNT(*) as cnt FROM games").fetchone()['cnt']
            missing_scores = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM games WHERE home_score IS NULL OR visitor_score IS NULL"
            ).fetchone()['cnt']
            missing_dates = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM games WHERE game_date IS NULL OR game_date = ''"
            ).fetchone()['cnt']

            summary["games"] = {
                "total": total_games,
                "missing_scores": missing_scores,
                "missing_scores_pct": round(100 * missing_scores / max(1, total_games), 1),
                "missing_dates": missing_dates,
                "missing_dates_pct": round(100 * missing_dates / max(1, total_games), 1)
            }

        # Goals missing data (if table exists)
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='goals'"
        )
        if cursor.fetchone():
            total_goals = self.conn.execute("SELECT COUNT(*) as cnt FROM goals").fetchone()['cnt']
            missing_scorer_names = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM goals WHERE scorer_name IS NULL OR scorer_name = ''"
            ).fetchone()['cnt']

            summary["goals"] = {
                "total": total_goals,
                "missing_scorer_names": missing_scorer_names,
                "missing_scorer_names_pct": round(100 * missing_scorer_names / max(1, total_goals), 1)
            }

        print(f"  Analyzed missing data across {len(summary)} entity types")
        return summary

    def calculate_overall_quality_score(self, results: Dict[str, Any]) -> float:
        """
        Calculate an overall data quality score (0.0 to 1.0).
        Higher = better quality.
        """
        score = 1.0
        penalties = []

        # Penalty for player number inconsistencies
        num_inconsistent = len(results.get("player_number_issues", []))
        if num_inconsistent > 0:
            penalty = min(0.2, num_inconsistent * 0.01)
            score -= penalty
            penalties.append(f"number_inconsistencies: -{penalty:.3f}")

        # Penalty for low confidence players
        low_confidence_players = [
            p for p in results.get("player_confidence_scores", [])
            if p.get("overall_confidence", 1.0) < 0.5
        ]
        if low_confidence_players:
            penalty = min(0.2, len(low_confidence_players) * 0.005)
            score -= penalty
            penalties.append(f"low_confidence_players: -{penalty:.3f}")

        # Penalty for critical game issues
        critical_game_issues = [
            g for g in results.get("game_quality_issues", [])
            if g.get("severity") == "critical"
        ]
        if critical_game_issues:
            penalty = min(0.3, len(critical_game_issues) * 0.02)
            score -= penalty
            penalties.append(f"critical_game_issues: -{penalty:.3f}")

        # Penalty for missing data
        missing = results.get("missing_data_summary", {})
        for entity_type, data in missing.items():
            if isinstance(data, dict) and "total" in data:
                for field, pct in data.items():
                    if field.endswith("_pct") and pct > 50:
                        penalty = 0.1
                        score -= penalty
                        penalties.append(f"{entity_type}_{field}: -{penalty:.3f}")
                        break

        score = max(0.0, score)  # Don't go below 0

        print(f"  Overall Quality Score: {score:.3f}")
        if penalties:
            print(f"  Penalties applied: {', '.join(penalties)}")

        return round(score, 3)

    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save analysis results to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_path}")

    def save_to_database(self, results: Dict[str, Any]):
        """Save quality issues to data_quality_issues table"""
        # Check if table exists, create if not
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='data_quality_issues'"
        )

        if not cursor.fetchone():
            print("\n📊 Creating data_quality_issues table...")
            self.conn.execute("""
                CREATE TABLE data_quality_issues (
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
            self.conn.commit()

        # Clear old issues (optional - you might want to keep them)
        # self.conn.execute("DELETE FROM data_quality_issues WHERE is_resolved = 0")

        # Insert player number issues
        for issue in results.get("player_number_issues", []):
            self.conn.execute("""
                INSERT INTO data_quality_issues
                (entity_type, entity_id, issue_type, issue_description, confidence_impact)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "player",
                issue["player_id"],
                issue["issue_type"],
                issue["details"],
                1.0 - issue["consistency_score"]
            ))

        # Insert game quality issues
        for issue in results.get("game_quality_issues", []):
            self.conn.execute("""
                INSERT INTO data_quality_issues
                (entity_type, entity_id, game_id, issue_type, issue_description, confidence_impact)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "game",
                issue["game_id"],
                issue["game_id"],
                issue["issue_type"],
                issue["description"],
                0.5 if issue["severity"] == "critical" else 0.2
            ))

        # Insert duplicate player issues
        for issue in results.get("duplicate_players", []):
            self.conn.execute("""
                INSERT INTO data_quality_issues
                (entity_type, entity_id, issue_type, issue_description, confidence_impact)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "player",
                issue.get("players", ""),
                issue["issue_type"],
                issue["description"],
                0.3
            ))

        self.conn.commit()
        print(f"✅ Saved {len(results.get('player_number_issues', [])) + len(results.get('game_quality_issues', []))} issues to database")

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description="Analyze hockey stats data quality")
    parser.add_argument("--db", required=True, help="Path to SQLite database")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--save-to-db", action="store_true", help="Save issues to database")

    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"❌ Database not found: {args.db}")
        return 1

    # Run analysis
    analyzer = DataQualityAnalyzer(args.db)
    results = analyzer.analyze_all()

    # Save results
    if args.output:
        analyzer.save_results(results, args.output)
    else:
        # Default output path
        db_name = Path(args.db).stem
        output_path = f"data_quality_report_{db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        analyzer.save_results(results, output_path)

    # Optionally save to database
    if args.save_to_db:
        analyzer.save_to_database(results)

    # Print summary
    print("\n" + "=" * 70)
    print("📊 DATA QUALITY SUMMARY")
    print("=" * 70)
    print(f"Overall Quality Score: {results['overall_quality_score']:.3f} / 1.0")
    print(f"\nPlayer Issues:")
    print(f"  - Number Inconsistencies: {len(results['player_number_issues'])}")
    print(f"  - Low Confidence Players: {len([p for p in results['player_confidence_scores'] if p['overall_confidence'] < 0.5])}")
    print(f"  - Duplicate/Conflicts: {len(results['duplicate_players'])}")
    print(f"\nGame Issues:")
    print(f"  - Total: {len(results['game_quality_issues'])}")
    print(f"  - Critical: {len([g for g in results['game_quality_issues'] if g['severity'] == 'critical'])}")
    print(f"  - Warning: {len([g for g in results['game_quality_issues'] if g['severity'] == 'warning'])}")

    if results.get('missing_data_summary'):
        print(f"\nMissing Data:")
        for entity, data in results['missing_data_summary'].items():
            if isinstance(data, dict) and data.get('total', 0) > 0:
                print(f"  {entity.capitalize()}: {data.get('total', 0)} records")

    analyzer.close()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
