#!/usr/bin/env python3
"""
Player Reconciler

Links club-scraped player data (names, jersey numbers) to GameSheet API
stats data (player_ids with blank names) by matching teams and then
matching players by jersey number within matched teams.

Three phases:
  1. reconcile_teams()   — Map club_teams → GameSheet teams
  2. reconcile_players() — Match players by jersey number
  3. backfill_names()    — Write names into game_rosters, goals, penalties

Usage:
    python3 player_reconciler.py --db hockey_stats.db --phase all
    python3 player_reconciler.py --db hockey_stats.db --phase teams --dry-run
"""

import argparse
import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from advanced_stats_database import AdvancedStatsDatabase, create_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Age group normalization: club website names → standard U-codes
AGE_GROUP_MAP = {
    "mite": "U8", "mighty mite": "U6", "mini mite": "U6",
    "squirt": "U10", "pee wee": "U12", "peewee": "U12",
    "bantam": "U14", "midget": "U18",
    "u6": "U6", "u8": "U8", "u10": "U10", "u12": "U12",
    "u14": "U14", "u16": "U16", "u18": "U18", "u19": "U19",
    "learn to play": None, "ltp": None,
    "beginner hockey": None,
}


def normalize_age_group(age_group: str) -> Optional[str]:
    """Convert club age group names to standard U-codes."""
    if not age_group:
        return None
    key = age_group.strip().lower()
    if key in AGE_GROUP_MAP:
        return AGE_GROUP_MAP[key]
    # Try prefix matching (e.g., "Squirts" → "Squirt")
    for prefix, ucode in AGE_GROUP_MAP.items():
        if key.startswith(prefix):
            return ucode
    return None


def parse_gamesheet_division(division_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse GameSheet division_name into (age_group, level, tier).

    Examples:
        "U12C - SILVER" → ("U12", "C", "SILVER")
        "U10B - GOLD"   → ("U10", "B", "GOLD")
        "U8B  - SILVER" → ("U8", "B", "SILVER")
        "U14B"          → ("U14", "B", None)
        "HIGH SCHOOL - VARSITY" → (None, None, None)
        "MIDDLE SCHOOL - GOLD"  → (None, None, None)
    """
    if not division_name:
        return (None, None, None)

    # Match patterns like U10B, U12C, U8A etc with optional tier
    m = re.match(r'(U\d+)([A-C])(?:\s*-\s*(.+))?', division_name.strip(), re.IGNORECASE)
    if m:
        age = m.group(1).upper()
        level = m.group(2).upper()
        tier = m.group(3).strip().upper() if m.group(3) else None
        return (age, level, tier)

    # Match GU10, GU12, GU14 (girls divisions)
    m = re.match(r'G(U\d+)(?:\s*-\s*(.+))?', division_name.strip(), re.IGNORECASE)
    if m:
        age = "G" + m.group(1).upper()
        tier = m.group(2).strip().upper() if m.group(2) else None
        return (age, None, tier)

    return (None, None, None)


def roster_overlap_score(set_a: Set[str], set_b: Set[str]) -> float:
    """Jaccard similarity between two jersey number sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def _build_name_patterns(abbreviation: Optional[str], club_name: Optional[str], town: Optional[str]) -> List[str]:
    """
    Build a list of name patterns that could match GameSheet team names.
    Patterns are ordered from most specific to least specific.

    E.g., for SSE / "South Shore Eagles Hockey League" / "South Shore":
      → ["south shore eagles", "south shore eagle", "sse"]
      (NOT "south shore" — too generic, would match Seahawks too)

    For SSH / "South Shore Seahawks" / "South Shore":
      → ["seahawks", "seahawk", "ssh"]

    For WHK / "WHK Hawks" / "Whitman-Hanson-Kingston":
      → ["whk", "whitman hanson", "whitman", "hanson"]
    """
    patterns = []

    if club_name:
        cn = club_name.lower()
        # Remove common suffixes to get the distinctive name
        core = cn
        for suffix in [' youth hockey association', ' youth hockey league',
                       ' hockey league', ' hockey association',
                       ' youth hockey', ' hockey', ' youth', ' league']:
            if core.endswith(suffix):
                core = core[:-len(suffix)].strip()
                break

        if core:
            patterns.append(core)
            # Also try without trailing "s" (Eagles → Eagle, Seahawks → Seahawk)
            if core.endswith('s') and not core.endswith('ss'):
                patterns.append(core[:-1])

    # Add the last distinctive word from the core name as a standalone pattern
    # e.g., "South Shore Eagles" → "eagles", "South Shore Seahawks" → "seahawks"
    # Only if the core has multiple words (single-word cores are already the pattern)
    if core:
        words = core.split()
        if len(words) > 1:
            last_word = words[-1]
            # Skip generic words that could match unrelated teams
            skip_words = {'hawks', 'hawk'}  # WHK Hawks "hawk" would match Seahawks
            if last_word not in patterns and len(last_word) > 3 and last_word not in skip_words:
                patterns.append(last_word)
                # Without trailing 's'
                if last_word.endswith('s') and not last_word.endswith('ss'):
                    singular = last_word[:-1]
                    if singular not in patterns and singular not in skip_words:
                        patterns.append(singular)

    if abbreviation:
        abbr = abbreviation.lower()
        if abbr not in patterns:
            patterns.append(abbr)

    if town:
        t = town.lower()
        # Only add town if it's not already a substring of an existing pattern
        # (avoids "south shore" matching both Eagles and Seahawks)
        already_covered = any(t in p for p in patterns)
        if not already_covered:
            # Only add single-word towns as patterns (e.g., "Marshfield", "Canton", "Plymouth")
            # Multi-word or hyphenated towns (e.g., "Whitman-Hanson-Kingston", "South Shore")
            # are too generic and cause false matches between related clubs
            if '-' not in t and '/' not in t and ' ' not in t and t not in patterns:
                patterns.append(t)

    return patterns


class PlayerReconciler:
    """Link club roster data to GameSheet player IDs."""

    def __init__(self, db: AdvancedStatsDatabase, season_id: str = "10776"):
        self.db = db
        self.season_id = season_id
        self.stats = {
            'teams_matched': 0,
            'teams_unmatched': 0,
            'teams_skipped': 0,
            'players_matched': 0,
            'players_unmatched': 0,
            'names_backfilled': {},
        }

    def reconcile_all(self, dry_run: bool = False) -> dict:
        """Run all three reconciliation phases."""
        logger.info(f"Starting reconciliation for season {self.season_id}")

        self.reconcile_teams(dry_run=dry_run)
        self.reconcile_players(dry_run=dry_run)
        if not dry_run:
            self.backfill_names()

        self._print_report()
        return self.stats

    # ------------------------------------------------------------------
    # Phase 1: Team Matching
    # ------------------------------------------------------------------

    def reconcile_teams(self, dry_run: bool = False):
        """Map club_teams to GameSheet teams."""
        logger.info("Phase 1: Reconciling teams...")
        cursor = self.db.conn.cursor()

        # Get all club_teams that need matching
        club_teams = cursor.execute('''
            SELECT ct.id, ct.club_id, ct.team_name, ct.age_group, ct.division_level,
                   c.abbreviation, c.club_name, c.town
            FROM club_teams ct
            JOIN clubs c ON ct.club_id = c.id
            WHERE ct.gamesheet_team_id IS NULL
        ''').fetchall()

        if not club_teams:
            logger.info("No unmatched club teams found")
            return

        # Get all GameSheet teams for this season
        gs_teams = cursor.execute('''
            SELECT team_id, team_name, division_name, division_id
            FROM teams
            WHERE season_id = ?
        ''', (self.season_id,)).fetchall()

        logger.info(f"Matching {len(club_teams)} club teams against {len(gs_teams)} GameSheet teams")

        for ct in club_teams:
            ct_id, club_id, team_name, age_group, div_level, abbreviation, club_name, town = ct

            # Normalize the age group
            norm_age = normalize_age_group(age_group) if age_group else None

            if norm_age is None:
                # Non-competitive teams (Learn to Play, Beginner Hockey, etc.)
                logger.debug(f"  Skipping non-competitive: {team_name} (age_group={age_group})")
                self.stats['teams_skipped'] += 1
                continue

            # Build list of name patterns to check against GameSheet team names
            name_patterns = _build_name_patterns(abbreviation, club_name, town)

            # Strategy 1: Structured match using name patterns + age + level
            match = self._try_structured_match(
                name_patterns, norm_age, div_level, team_name, gs_teams
            )

            # Strategy 2: Roster overlap heuristic
            if not match:
                match = self._try_roster_overlap(
                    club_id, ct_id, gs_teams, name_patterns, norm_age
                )

            if match:
                gs_team_id, gs_team_name, gs_div_name, method = match
                logger.info(f"  MATCH: \"{team_name}\" → \"{gs_team_name}\" ({gs_div_name}) [{method}]")
                self.stats['teams_matched'] += 1

                if not dry_run:
                    cursor.execute(
                        "UPDATE club_teams SET gamesheet_team_id = ?, updated_at = datetime('now') WHERE id = ?",
                        (gs_team_id, ct_id)
                    )
            else:
                logger.warning(f"  NO MATCH: \"{team_name}\" (patterns={name_patterns[:3]}, age={norm_age}, level={div_level})")
                self.stats['teams_unmatched'] += 1

        if not dry_run:
            self.db.conn.commit()

        logger.info(f"Team matching complete: {self.stats['teams_matched']} matched, "
                     f"{self.stats['teams_unmatched']} unmatched, "
                     f"{self.stats['teams_skipped']} skipped")

    def _try_structured_match(
        self, name_patterns: List[str], norm_age: str, div_level: Optional[str],
        club_team_name: str, gs_teams: list
    ) -> Optional[tuple]:
        """Try to match by name patterns + age group + division level."""
        if not name_patterns:
            return None

        candidates = []

        for gs in gs_teams:
            gs_team_id, gs_team_name, gs_div_name, gs_div_id = gs
            gs_age, gs_level, gs_tier = parse_gamesheet_division(gs_div_name)

            if not gs_age:
                continue

            # Check age group match
            if gs_age != norm_age:
                continue

            # Check if any name pattern appears in the GameSheet team name
            gs_name_lower = gs_team_name.lower()
            if not any(pat in gs_name_lower for pat in name_patterns):
                continue

            # If we have a division level, check it matches
            if div_level and gs_level:
                # Handle numeric suffixes like "B1", "B2"
                clean_level = div_level.rstrip('0123456789').upper()
                if clean_level == gs_level:
                    candidates.append((gs_team_id, gs_team_name, gs_div_name, gs_div_id))
            elif not div_level and gs_level:
                # Club has no level but GameSheet does — still a candidate
                candidates.append((gs_team_id, gs_team_name, gs_div_name, gs_div_id))
            elif div_level and not gs_level:
                candidates.append((gs_team_id, gs_team_name, gs_div_name, gs_div_id))
            else:
                candidates.append((gs_team_id, gs_team_name, gs_div_name, gs_div_id))

        if len(candidates) == 1:
            c = candidates[0]
            return (c[0], c[1], c[2], "structured")
        elif len(candidates) > 1:
            # Multiple candidates — will fall through to roster overlap
            logger.debug(f"    Structured match found {len(candidates)} candidates for "
                         f"{name_patterns[0]} {norm_age}{div_level or ''}")
            return None

        return None

    def _try_roster_overlap(
        self, club_id: int, club_team_id: int, gs_teams: list,
        name_patterns: List[str], norm_age: Optional[str]
    ) -> Optional[tuple]:
        """Match by comparing jersey number sets between club and GameSheet rosters."""
        cursor = self.db.conn.cursor()

        # Get club roster jersey numbers for this team
        club_jerseys = set()
        rows = cursor.execute(
            "SELECT jersey_number FROM club_players WHERE club_team_id = ? AND jersey_number IS NOT NULL",
            (club_team_id,)
        ).fetchall()
        for r in rows:
            if r[0]:
                club_jerseys.add(str(r[0]).strip())

        if len(club_jerseys) < 3:
            # Too few players for reliable overlap matching
            return None

        # Narrow candidates by name patterns and/or age group if available
        candidate_teams = []
        for gs in gs_teams:
            gs_team_id, gs_team_name, gs_div_name, gs_div_id = gs
            gs_age, _, _ = parse_gamesheet_division(gs_div_name)

            # If we have name patterns, the team name should contain one
            if name_patterns:
                gs_name_lower = gs_team_name.lower()
                if not any(pat in gs_name_lower for pat in name_patterns):
                    continue

            # If we have age group, filter by it
            if norm_age and gs_age and gs_age != norm_age:
                continue

            candidate_teams.append(gs)

        if not candidate_teams:
            return None

        # Compare jersey sets
        best_score = 0.0
        best_match = None

        for gs in candidate_teams:
            gs_team_id, gs_team_name, gs_div_name, gs_div_id = gs

            # Get GameSheet roster jersey numbers
            gs_jerseys = set()
            gs_rows = cursor.execute(
                "SELECT DISTINCT player_number FROM game_rosters WHERE team_id = ? AND player_number IS NOT NULL",
                (gs_team_id,)
            ).fetchall()
            for r in gs_rows:
                if r[0]:
                    gs_jerseys.add(str(r[0]).strip())

            if not gs_jerseys:
                continue

            score = roster_overlap_score(club_jerseys, gs_jerseys)
            if score > best_score:
                best_score = score
                best_match = gs

        if best_match and best_score >= 0.5:
            return (best_match[0], best_match[1], best_match[2], f"roster_overlap({best_score:.2f})")

        return None

    # ------------------------------------------------------------------
    # Phase 2: Player Matching
    # ------------------------------------------------------------------

    def reconcile_players(self, dry_run: bool = False):
        """Match club_players to GameSheet player_ids by jersey number."""
        logger.info("Phase 2: Reconciling players...")
        cursor = self.db.conn.cursor()

        # Get matched teams
        matched_teams = cursor.execute('''
            SELECT ct.id, ct.team_name, ct.gamesheet_team_id, c.club_name
            FROM club_teams ct
            JOIN clubs c ON ct.club_id = c.id
            WHERE ct.gamesheet_team_id IS NOT NULL
        ''').fetchall()

        if not matched_teams:
            logger.info("No matched teams to reconcile players for")
            return

        logger.info(f"Reconciling players for {len(matched_teams)} matched teams")

        for ct in matched_teams:
            ct_id, team_name, gs_team_id, club_name = ct

            # Get club roster: jersey → (player_id, first_name, last_name)
            club_roster = cursor.execute('''
                SELECT id, jersey_number, first_name, last_name
                FROM club_players
                WHERE club_team_id = ? AND gamesheet_player_id IS NULL
            ''', (ct_id,)).fetchall()

            if not club_roster:
                continue

            # Get GameSheet roster: jersey → player_id (using most frequent number per player)
            gs_roster = cursor.execute('''
                SELECT player_id, player_number, COUNT(*) as appearances
                FROM game_rosters
                WHERE team_id = ?
                GROUP BY player_id, player_number
                ORDER BY player_id, appearances DESC
            ''', (gs_team_id,)).fetchall()

            # Build jersey → player_id map (use most frequent number for each player_id)
            gs_jersey_map: Dict[str, str] = {}
            seen_players = set()
            for row in gs_roster:
                pid, pnum, _ = row
                if pid not in seen_players:
                    seen_players.add(pid)
                    if pnum and pnum.strip():
                        gs_jersey_map[pnum.strip()] = pid

            # Match by jersey number
            team_matched = 0
            team_unmatched = 0
            for cp in club_roster:
                cp_id, jersey, first_name, last_name = cp
                if not jersey:
                    team_unmatched += 1
                    continue

                jersey_clean = str(jersey).strip()
                gs_player_id = gs_jersey_map.get(jersey_clean)

                if gs_player_id:
                    team_matched += 1
                    self.stats['players_matched'] += 1

                    if not dry_run:
                        cursor.execute(
                            "UPDATE club_players SET gamesheet_player_id = ?, updated_at = datetime('now') WHERE id = ?",
                            (gs_player_id, cp_id)
                        )
                    logger.debug(f"    #{jersey_clean} {first_name} {last_name} → {gs_player_id}")
                else:
                    team_unmatched += 1
                    self.stats['players_unmatched'] += 1
                    logger.debug(f"    #{jersey_clean} {first_name} {last_name} → NO MATCH")

            logger.info(f"  {team_name}: {team_matched} matched, {team_unmatched} unmatched")

        if not dry_run:
            self.db.conn.commit()

        logger.info(f"Player matching complete: {self.stats['players_matched']} matched, "
                     f"{self.stats['players_unmatched']} unmatched")

    # ------------------------------------------------------------------
    # Phase 3: Name Backfill
    # ------------------------------------------------------------------

    def backfill_names(self):
        """Write linked names into GameSheet tables."""
        logger.info("Phase 3: Backfilling names...")
        cursor = self.db.conn.cursor()

        # 1. game_rosters — first_name and last_name
        result = cursor.execute('''
            UPDATE game_rosters
            SET first_name = cp.first_name,
                last_name = cp.last_name
            FROM club_players cp
            WHERE game_rosters.player_id = cp.gamesheet_player_id
              AND cp.gamesheet_player_id IS NOT NULL
              AND (game_rosters.first_name IS NULL OR TRIM(game_rosters.first_name) = '')
        ''')
        count = result.rowcount
        self.stats['names_backfilled']['game_rosters'] = count
        logger.info(f"  game_rosters: {count} rows updated")

        # 2. goals — scorer_name
        result = cursor.execute('''
            UPDATE goals
            SET scorer_name = cp.first_name || ' ' || cp.last_name
            FROM club_players cp
            WHERE goals.scorer_player_id = cp.gamesheet_player_id
              AND cp.gamesheet_player_id IS NOT NULL
              AND (goals.scorer_name IS NULL OR TRIM(goals.scorer_name) = '')
        ''')
        count = result.rowcount
        self.stats['names_backfilled']['goals_scorer'] = count
        logger.info(f"  goals.scorer_name: {count} rows updated")

        # 3. goals — assist1_name
        result = cursor.execute('''
            UPDATE goals
            SET assist1_name = cp.first_name || ' ' || cp.last_name
            FROM club_players cp
            WHERE goals.assist1_player_id = cp.gamesheet_player_id
              AND cp.gamesheet_player_id IS NOT NULL
              AND (goals.assist1_name IS NULL OR TRIM(goals.assist1_name) = '')
        ''')
        count = result.rowcount
        self.stats['names_backfilled']['goals_assist1'] = count
        logger.info(f"  goals.assist1_name: {count} rows updated")

        # 4. goals — assist2_name
        result = cursor.execute('''
            UPDATE goals
            SET assist2_name = cp.first_name || ' ' || cp.last_name
            FROM club_players cp
            WHERE goals.assist2_player_id = cp.gamesheet_player_id
              AND cp.gamesheet_player_id IS NOT NULL
              AND (goals.assist2_name IS NULL OR TRIM(goals.assist2_name) = '')
        ''')
        count = result.rowcount
        self.stats['names_backfilled']['goals_assist2'] = count
        logger.info(f"  goals.assist2_name: {count} rows updated")

        # 5. penalties — player_name
        result = cursor.execute('''
            UPDATE penalties
            SET player_name = cp.first_name || ' ' || cp.last_name
            FROM club_players cp
            WHERE penalties.player_id = cp.gamesheet_player_id
              AND cp.gamesheet_player_id IS NOT NULL
              AND (penalties.player_name IS NULL OR TRIM(penalties.player_name) = '')
        ''')
        count = result.rowcount
        self.stats['names_backfilled']['penalties'] = count
        logger.info(f"  penalties.player_name: {count} rows updated")

        # 6. player_stats — player_name (if table exists)
        try:
            result = cursor.execute('''
                UPDATE player_stats
                SET player_name = cp.first_name || ' ' || cp.last_name
                FROM club_players cp
                WHERE player_stats.player_id = cp.gamesheet_player_id
                  AND cp.gamesheet_player_id IS NOT NULL
                  AND (player_stats.player_name IS NULL OR TRIM(player_stats.player_name) = '')
            ''')
            count = result.rowcount
            self.stats['names_backfilled']['player_stats'] = count
            logger.info(f"  player_stats.player_name: {count} rows updated")
        except sqlite3.OperationalError:
            logger.debug("  player_stats table not found, skipping")

        self.db.conn.commit()

        total = sum(self.stats['names_backfilled'].values())
        logger.info(f"Name backfill complete: {total} total rows updated")

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _print_report(self):
        """Print reconciliation summary."""
        logger.info("\n" + "=" * 60)
        logger.info("RECONCILIATION REPORT")
        logger.info("=" * 60)
        logger.info(f"Teams matched:    {self.stats['teams_matched']}")
        logger.info(f"Teams unmatched:  {self.stats['teams_unmatched']}")
        logger.info(f"Teams skipped:    {self.stats['teams_skipped']}")
        logger.info(f"Players matched:  {self.stats['players_matched']}")
        logger.info(f"Players unmatched:{self.stats['players_unmatched']}")

        if self.stats['names_backfilled']:
            logger.info("Names backfilled:")
            for table, count in self.stats['names_backfilled'].items():
                logger.info(f"  {table}: {count}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Reconcile club roster data with GameSheet player IDs'
    )
    parser.add_argument('--db', required=True, help='Path to SQLite database')
    parser.add_argument('--season-id', default='10776', help='GameSheet season ID (default: 10776)')
    parser.add_argument('--phase', choices=['teams', 'players', 'backfill', 'all'],
                        default='all', help='Which phase to run')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show matches without writing to database')

    args = parser.parse_args()

    db = create_database(args.db)

    try:
        reconciler = PlayerReconciler(db, args.season_id)

        if args.phase == 'all':
            reconciler.reconcile_all(dry_run=args.dry_run)
        elif args.phase == 'teams':
            reconciler.reconcile_teams(dry_run=args.dry_run)
        elif args.phase == 'players':
            reconciler.reconcile_players(dry_run=args.dry_run)
        elif args.phase == 'backfill':
            reconciler.backfill_names()

    finally:
        db.close()


if __name__ == '__main__':
    main()
