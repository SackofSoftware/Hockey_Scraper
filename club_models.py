#!/usr/bin/env python3
"""
Club Data Models

Dataclass definitions for all club-related entities scraped from
SportsEngine-powered youth hockey club websites.

Used by club_scraper.py and club_importer.py.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ClubInfo:
    """Represents an SSC member club/organization."""
    club_name: str
    club_slug: str                          # derived from URL, e.g. "whk-hawks"
    website_url: str
    sportsengine_org_id: Optional[str] = None
    town: Optional[str] = None
    abbreviation: Optional[str] = None
    conference: str = "SSC"
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()

    def to_dict(self):
        return asdict(self)


@dataclass
class ClubTeam:
    """A team within a club (e.g., WHK Hawks U10B)."""
    club_name: str
    team_name: str                          # full name: "WHK U10 - B"
    age_group: Optional[str] = None         # e.g., "U10", "U12", "U14"
    division_level: Optional[str] = None    # e.g., "A", "B", "C"
    season: Optional[str] = None            # e.g., "2025-2026"
    team_page_url: Optional[str] = None     # /page/show/{id}
    roster_url: Optional[str] = None        # /roster/show/{id}?subseason={id}
    schedule_url: Optional[str] = None      # /schedule/team_instance/{id}?subseason={id}
    sportsengine_page_id: Optional[str] = None
    sportsengine_team_instance_id: Optional[str] = None
    subseason_id: Optional[str] = None
    source_url: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ClubPlayer:
    """A player on a club roster."""
    club_name: str
    team_name: str
    name: str                               # full display name
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    jersey_number: Optional[str] = None
    position: Optional[str] = None          # F, D, G
    usah_number: Optional[str] = None       # USA Hockey registration number
    player_profile_url: Optional[str] = None
    source_url: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ClubCoach:
    """A coach/staff member associated with a team."""
    club_name: str
    name: str
    team_name: Optional[str] = None
    role: Optional[str] = None              # "Head Coach", "Assistant Coach", "Manager"
    email: Optional[str] = None
    phone: Optional[str] = None
    source_url: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ClubBoardMember:
    """A board member of a club organization."""
    club_name: str
    name: str
    title: Optional[str] = None             # "President", "Treasurer", etc.
    email: Optional[str] = None
    phone: Optional[str] = None
    source_url: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ClubGame:
    """A game from a club team's schedule."""
    club_name: str
    team_name: str
    date: str                               # YYYY-MM-DD
    opponent: str
    time: Optional[str] = None              # e.g., "7:00 AM EST"
    location: Optional[str] = None
    is_home: Optional[bool] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str = "scheduled"               # scheduled, final, cancelled, postponed
    game_id: Optional[str] = None           # SportsEngine game ID
    game_url: Optional[str] = None
    source_url: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ClubContact:
    """Contact information found on a club site."""
    club_name: str
    contact_type: str                       # "email", "phone", "address"
    value: str
    context: Optional[str] = None           # where found: "footer", "contact page", "board page"
    source_url: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ClubScrapeResult:
    """Complete result of scraping one club website."""
    club: ClubInfo
    teams: List[ClubTeam] = field(default_factory=list)
    players: List[ClubPlayer] = field(default_factory=list)
    coaches: List[ClubCoach] = field(default_factory=list)
    board_members: List[ClubBoardMember] = field(default_factory=list)
    games: List[ClubGame] = field(default_factory=list)
    contacts: List[ClubContact] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    pages_visited: int = 0
    scrape_duration_seconds: float = 0.0

    def to_dict(self):
        return {
            'club': self.club.to_dict(),
            'teams': [t.to_dict() for t in self.teams],
            'players': [p.to_dict() for p in self.players],
            'coaches': [c.to_dict() for c in self.coaches],
            'board_members': [b.to_dict() for b in self.board_members],
            'games': [g.to_dict() for g in self.games],
            'contacts': [c.to_dict() for c in self.contacts],
            'errors': self.errors,
            'pages_visited': self.pages_visited,
            'scrape_duration_seconds': self.scrape_duration_seconds,
        }

    def summary(self) -> str:
        """Return a human-readable summary."""
        return (
            f"{self.club.club_name}: "
            f"{len(self.teams)} teams, "
            f"{len(self.players)} players, "
            f"{len(self.coaches)} coaches, "
            f"{len(self.board_members)} board members, "
            f"{len(self.games)} games, "
            f"{len(self.contacts)} contacts, "
            f"{len(self.errors)} errors"
        )
