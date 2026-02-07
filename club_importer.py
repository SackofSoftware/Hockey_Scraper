#!/usr/bin/env python3
"""
Club Data Importer

Imports club scrape results (from JSON files or ClubScrapeResult objects)
into the SQLite database's club_* tables.

Usage:
    # Import from JSON directory
    python3 club_importer.py --json-dir data/clubs/whk-hawks --db hockey_stats_10776.db

    # Import all clubs from data/clubs/
    python3 club_importer.py --json-dir data/clubs --db hockey_stats_10776.db --all
"""

import argparse
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from advanced_stats_database import AdvancedStatsDatabase, create_database
from club_models import (
    ClubInfo, ClubTeam, ClubPlayer, ClubCoach, ClubBoardMember,
    ClubGame, ClubContact, ClubScrapeResult
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClubDataImporter:
    """Import club scrape results into SQLite database."""

    def __init__(self, db: AdvancedStatsDatabase):
        self.db = db
        self.stats = {
            'clubs': 0,
            'teams': 0,
            'players': 0,
            'coaches': 0,
            'board_members': 0,
            'games': 0,
            'contacts': 0,
        }

    # ------------------------------------------------------------------
    # Import from ClubScrapeResult
    # ------------------------------------------------------------------

    def import_club_result(self, result: ClubScrapeResult):
        """
        Import a complete club scrape result into the database.

        Uses UPSERT logic so running multiple times is safe.
        """
        logger.info(f"Importing club: {result.club.club_name}")

        # 1. Upsert club
        club_id = self._upsert_club(result.club)

        # 2. Upsert teams and build team_name -> team_id mapping
        team_id_map: Dict[str, int] = {}
        for team in result.teams:
            team_id = self._upsert_team(club_id, team)
            if team_id:
                team_id_map[team.team_name] = team_id

        # 3. Upsert players
        for player in result.players:
            team_id = team_id_map.get(player.team_name)
            self._upsert_player(club_id, team_id, player)

        # 4. Insert coaches
        for coach in result.coaches:
            team_id = team_id_map.get(coach.team_name)
            self._insert_coach(club_id, team_id, coach)

        # 5. Insert board members
        for member in result.board_members:
            self._upsert_board_member(club_id, member)

        # 6. Insert games
        for game in result.games:
            team_id = team_id_map.get(game.team_name)
            self._insert_game(club_id, team_id, game)

        # 7. Insert contacts
        for contact in result.contacts:
            self._upsert_contact(club_id, contact)

        # Update last_scraped timestamp
        self.db.conn.execute(
            "UPDATE clubs SET last_scraped = ?, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), datetime.now().isoformat(), club_id)
        )

        self.db.conn.commit()
        logger.info(f"Imported {result.club.club_name}: {self._stats_line()}")

    # ------------------------------------------------------------------
    # Import from JSON files
    # ------------------------------------------------------------------

    def import_from_json_dir(self, json_dir: str):
        """
        Import club data from a JSON output directory.

        Expected structure:
            json_dir/
                club_info.json
                teams.json
                players.json
                coaches.json
                board_members.json
                games.json
                contacts.json
        """
        dir_path = Path(json_dir)

        # Load club info
        club_info_path = dir_path / 'club_info.json'
        if not club_info_path.exists():
            logger.warning(f"No club_info.json in {json_dir}, skipping")
            return

        with open(club_info_path) as f:
            club_data = json.load(f)

        club = ClubInfo(**{k: v for k, v in club_data.items() if k in ClubInfo.__dataclass_fields__})

        # Enrich with abbreviation/town from ssc_clubs.json if missing
        self._enrich_club_from_config(club)

        # Load all entity files
        teams = self._load_json_list(dir_path / 'teams.json', ClubTeam)
        players = self._load_json_list(dir_path / 'players.json', ClubPlayer)
        coaches = self._load_json_list(dir_path / 'coaches.json', ClubCoach)
        board_members = self._load_json_list(dir_path / 'board_members.json', ClubBoardMember)
        games = self._load_json_list(dir_path / 'games.json', ClubGame)
        contacts = self._load_json_list(dir_path / 'contacts.json', ClubContact)

        result = ClubScrapeResult(
            club=club,
            teams=teams,
            players=players,
            coaches=coaches,
            board_members=board_members,
            games=games,
            contacts=contacts,
        )

        self.import_club_result(result)

    def import_all_from_dir(self, clubs_dir: str):
        """
        Import all clubs from a directory containing per-club subdirectories.

        Expected structure:
            clubs_dir/
                whk-hawks/
                    club_info.json
                    ...
                canton-youth-hockey/
                    club_info.json
                    ...
        """
        clubs_path = Path(clubs_dir)
        if not clubs_path.exists():
            logger.error(f"Clubs directory not found: {clubs_dir}")
            return

        subdirs = sorted([d for d in clubs_path.iterdir() if d.is_dir()])
        logger.info(f"Found {len(subdirs)} club directories in {clubs_dir}")

        for subdir in subdirs:
            if (subdir / 'club_info.json').exists():
                try:
                    self.import_from_json_dir(str(subdir))
                except Exception as e:
                    logger.error(f"Failed to import {subdir.name}: {e}")
            else:
                logger.debug(f"Skipping {subdir.name} (no club_info.json)")

        logger.info(f"Import complete: {self._stats_line()}")

    # ------------------------------------------------------------------
    # UPSERT methods
    # ------------------------------------------------------------------

    def _upsert_club(self, club: ClubInfo) -> int:
        """Insert or update a club, return its ID."""
        cursor = self.db.conn.cursor()

        cursor.execute('''
            INSERT INTO clubs (club_name, club_slug, website_url, sportsengine_org_id,
                             town, abbreviation, conference, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(club_slug) DO UPDATE SET
                club_name = excluded.club_name,
                website_url = excluded.website_url,
                sportsengine_org_id = excluded.sportsengine_org_id,
                town = excluded.town,
                abbreviation = excluded.abbreviation,
                conference = excluded.conference,
                updated_at = excluded.updated_at
        ''', (
            club.club_name, club.club_slug, club.website_url,
            club.sportsengine_org_id, club.town, club.abbreviation,
            club.conference,
            datetime.now().isoformat(), datetime.now().isoformat()
        ))

        # Get the club ID
        cursor.execute("SELECT id FROM clubs WHERE club_slug = ?", (club.club_slug,))
        row = cursor.fetchone()
        club_id = row[0] if row else cursor.lastrowid

        self.stats['clubs'] += 1
        return club_id

    def _upsert_team(self, club_id: int, team: ClubTeam) -> Optional[int]:
        """Insert or update a team, return its ID."""
        cursor = self.db.conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO club_teams (
                    club_id, team_name, age_group, division_level, season,
                    team_page_url, roster_url, schedule_url,
                    sportsengine_page_id, sportsengine_team_instance_id,
                    subseason_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(club_id, team_name, season) DO UPDATE SET
                    age_group = excluded.age_group,
                    division_level = excluded.division_level,
                    team_page_url = excluded.team_page_url,
                    roster_url = excluded.roster_url,
                    schedule_url = excluded.schedule_url,
                    sportsengine_page_id = excluded.sportsengine_page_id,
                    sportsengine_team_instance_id = excluded.sportsengine_team_instance_id,
                    subseason_id = excluded.subseason_id,
                    updated_at = excluded.updated_at
            ''', (
                club_id, team.team_name, team.age_group, team.division_level,
                team.season, team.team_page_url, team.roster_url, team.schedule_url,
                team.sportsengine_page_id, team.sportsengine_team_instance_id,
                team.subseason_id,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))

            # Get the team ID
            cursor.execute(
                "SELECT id FROM club_teams WHERE club_id = ? AND team_name = ? AND season = ?",
                (club_id, team.team_name, team.season)
            )
            row = cursor.fetchone()
            team_id = row[0] if row else cursor.lastrowid

            self.stats['teams'] += 1
            return team_id

        except Exception as e:
            logger.warning(f"Failed to upsert team {team.team_name}: {e}")
            return None

    def _upsert_player(self, club_id: int, team_id: Optional[int], player: ClubPlayer):
        """Insert or update a player."""
        cursor = self.db.conn.cursor()

        first_name = player.first_name or ""
        last_name = player.last_name or ""

        if not first_name and not last_name:
            # Split from full name
            parts = player.name.strip().split()
            if parts:
                first_name = parts[0]
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        try:
            cursor.execute('''
                INSERT INTO club_players (
                    club_id, club_team_id, first_name, last_name,
                    jersey_number, position, usah_number,
                    player_profile_url, source_url, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(club_id, club_team_id, first_name, last_name) DO UPDATE SET
                    jersey_number = excluded.jersey_number,
                    position = excluded.position,
                    usah_number = excluded.usah_number,
                    player_profile_url = excluded.player_profile_url,
                    source_url = excluded.source_url,
                    updated_at = excluded.updated_at
            ''', (
                club_id, team_id, first_name, last_name,
                player.jersey_number, player.position, player.usah_number,
                player.player_profile_url, player.source_url,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            self.stats['players'] += 1

        except Exception as e:
            logger.warning(f"Failed to upsert player {player.name}: {e}")

    def _insert_coach(self, club_id: int, team_id: Optional[int], coach: ClubCoach):
        """Insert a coach (no unique constraint, so we check for duplicates)."""
        cursor = self.db.conn.cursor()

        # Check for existing
        cursor.execute(
            "SELECT id FROM club_coaches WHERE club_id = ? AND name = ? AND COALESCE(club_team_id, 0) = COALESCE(?, 0)",
            (club_id, coach.name, team_id)
        )
        if cursor.fetchone():
            # Update existing
            cursor.execute('''
                UPDATE club_coaches SET role = ?, email = ?, phone = ?,
                    source_url = ?, updated_at = ?
                WHERE club_id = ? AND name = ? AND COALESCE(club_team_id, 0) = COALESCE(?, 0)
            ''', (
                coach.role, coach.email, coach.phone, coach.source_url,
                datetime.now().isoformat(),
                club_id, coach.name, team_id
            ))
        else:
            cursor.execute('''
                INSERT INTO club_coaches (
                    club_id, club_team_id, name, role, email, phone,
                    source_url, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                club_id, team_id, coach.name, coach.role, coach.email,
                coach.phone, coach.source_url,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))

        self.stats['coaches'] += 1

    def _upsert_board_member(self, club_id: int, member: ClubBoardMember):
        """Insert or update a board member."""
        cursor = self.db.conn.cursor()

        # Check for existing by name
        cursor.execute(
            "SELECT id FROM club_board_members WHERE club_id = ? AND name = ?",
            (club_id, member.name)
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute('''
                UPDATE club_board_members SET title = ?, email = ?, phone = ?,
                    source_url = ?, updated_at = ?
                WHERE id = ?
            ''', (
                member.title, member.email, member.phone, member.source_url,
                datetime.now().isoformat(), existing[0]
            ))
        else:
            cursor.execute('''
                INSERT INTO club_board_members (
                    club_id, name, title, email, phone, source_url,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                club_id, member.name, member.title, member.email,
                member.phone, member.source_url,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))

        self.stats['board_members'] += 1

    def _insert_game(self, club_id: int, team_id: Optional[int], game: ClubGame):
        """Insert a game (deduplication via game_id if available)."""
        cursor = self.db.conn.cursor()

        # Check for existing by game_id or by (team, date, opponent)
        if game.game_id:
            cursor.execute(
                "SELECT id FROM club_games WHERE club_id = ? AND game_id = ?",
                (club_id, game.game_id)
            )
        else:
            cursor.execute(
                "SELECT id FROM club_games WHERE club_id = ? AND club_team_id = ? AND date = ? AND opponent = ?",
                (club_id, team_id, game.date, game.opponent)
            )

        existing = cursor.fetchone()

        if existing:
            # Update scores/status
            cursor.execute('''
                UPDATE club_games SET time = ?, location = ?, is_home = ?,
                    home_score = ?, away_score = ?, status = ?, game_url = ?,
                    source_url = ?
                WHERE id = ?
            ''', (
                game.time, game.location, game.is_home,
                game.home_score, game.away_score, game.status,
                game.game_url, game.source_url, existing[0]
            ))
        else:
            cursor.execute('''
                INSERT INTO club_games (
                    club_id, club_team_id, game_id, date, time, opponent,
                    location, is_home, home_score, away_score, status,
                    game_url, source_url, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                club_id, team_id, game.game_id, game.date, game.time,
                game.opponent, game.location, game.is_home,
                game.home_score, game.away_score, game.status,
                game.game_url, game.source_url,
                datetime.now().isoformat()
            ))

        self.stats['games'] += 1

    def _upsert_contact(self, club_id: int, contact: ClubContact):
        """Insert contact info if not already present."""
        cursor = self.db.conn.cursor()

        cursor.execute(
            "SELECT id FROM club_contacts WHERE club_id = ? AND contact_type = ? AND value = ?",
            (club_id, contact.contact_type, contact.value)
        )
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO club_contacts (
                    club_id, contact_type, value, context, source_url, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                club_id, contact.contact_type, contact.value,
                contact.context, contact.source_url,
                datetime.now().isoformat()
            ))
            self.stats['contacts'] += 1

    # ------------------------------------------------------------------
    # Config enrichment
    # ------------------------------------------------------------------

    def _enrich_club_from_config(self, club: ClubInfo):
        """Populate abbreviation and town from config/ssc_clubs.json if missing."""
        if club.abbreviation and club.town:
            return

        config_path = Path(__file__).parent / 'config' / 'ssc_clubs.json'
        if not config_path.exists():
            return

        try:
            with open(config_path) as f:
                config = json.load(f)

            for entry in config.get('clubs', []):
                # Match by URL or club name
                if (club.website_url and entry.get('url')
                        and club.website_url.rstrip('/') == entry['url'].rstrip('/')):
                    if not club.abbreviation:
                        club.abbreviation = entry.get('abbreviation')
                    if not club.town:
                        club.town = entry.get('town')
                    return

                # Fallback: match by name similarity
                if entry.get('name', '').lower() == club.club_name.lower():
                    if not club.abbreviation:
                        club.abbreviation = entry.get('abbreviation')
                    if not club.town:
                        club.town = entry.get('town')
                    return

        except Exception as e:
            logger.debug(f"Could not read ssc_clubs.json: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_json_list(self, path: Path, dataclass_type) -> list:
        """Load a JSON array file and convert to dataclass instances."""
        if not path.exists():
            return []

        try:
            with open(path) as f:
                data = json.load(f)

            if not isinstance(data, list):
                return []

            # Filter dict keys to match dataclass fields
            valid_fields = set(dataclass_type.__dataclass_fields__.keys())
            items = []
            for item in data:
                if isinstance(item, dict):
                    filtered = {k: v for k, v in item.items() if k in valid_fields}
                    try:
                        items.append(dataclass_type(**filtered))
                    except TypeError as e:
                        logger.warning(f"Skipping item in {path.name}: {e}")
            return items

        except Exception as e:
            logger.warning(f"Failed to load {path}: {e}")
            return []

    def _stats_line(self) -> str:
        """Format import stats as a compact string."""
        return (
            f"{self.stats['clubs']} clubs, "
            f"{self.stats['teams']} teams, "
            f"{self.stats['players']} players, "
            f"{self.stats['coaches']} coaches, "
            f"{self.stats['board_members']} board members, "
            f"{self.stats['games']} games, "
            f"{self.stats['contacts']} contacts"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Import club scrape data into SQLite database'
    )
    parser.add_argument('--json-dir', required=True, help='Path to club JSON output directory')
    parser.add_argument('--db', required=True, help='Path to SQLite database file')
    parser.add_argument('--all', action='store_true',
                        help='Import all club subdirectories (json-dir contains per-club dirs)')

    args = parser.parse_args()

    # Open or create database
    db = create_database(args.db)

    try:
        importer = ClubDataImporter(db)

        if args.all:
            importer.import_all_from_dir(args.json_dir)
        else:
            importer.import_from_json_dir(args.json_dir)

        print(f"\n[OK] Import complete: {importer._stats_line()}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
