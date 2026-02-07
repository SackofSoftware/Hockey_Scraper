"""
Logo cross-reference service for hockey teams.

Maps team names (from GameSheet API or other sources) to local SVG logos
and/or GameSheet CDN URLs using fuzzy matching with manual alias overrides.
"""
from __future__ import annotations

import json
import re
import subprocess
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional


GAMESHEET_API_BASE = "https://gamesheetstats.com/api"
DEFAULT_SEASON_IDS = [10776, 10477]


@dataclass
class LogoResult:
    """Result of a logo lookup for a single team."""
    team_name: str
    team_id: Optional[int] = None
    local_file: Optional[str] = None       # filename in logos/ dir (e.g. "WHK.svg")
    gamesheet_url: Optional[str] = None     # imagedelivery.net URL
    source: str = "none"                    # "local", "gamesheet", "both", "none"
    match_confidence: Optional[float] = None


@dataclass
class LogoManifestData:
    """Full cross-reference manifest of all teams and their logos."""
    season_id: int
    season_name: str
    generated_at: str = ""
    total_teams: int = 0
    matched_local: int = 0
    matched_gamesheet: int = 0
    unmatched: int = 0
    teams: List[LogoResult] = field(default_factory=list)


# Suffixes and terms to strip from team names before matching
_STRIP_PATTERNS = [
    # Age/division suffixes
    r'\bU\d+[A-Z]?\b',           # U8A, U10C, U12B, U14B
    r'\bSquirt\b', r'\bPeeWee\b', r'\bBantam\b', r'\bMidget\b', r'\bMite\b',
    # Color/variant suffixes
    r'\bRed\b', r'\bBlue\b', r'\bWhite\b', r'\bBlack\b',
    r'\bGold\b', r'\bSilver\b', r'\bGrey\b', r'\bGreen\b', r'\bYellow\b',
    # Misc
    r'\b\d+\b',                   # standalone numbers
    r'\bGirls\b', r'\bBoys\b',
]
_STRIP_RE = re.compile('|'.join(_STRIP_PATTERNS), re.IGNORECASE)


class LogoService:
    """Cross-references local SVG logos with GameSheet team data."""

    def __init__(
        self,
        logos_dir: str | Path = "logos",
        fuzzy_threshold: float = 0.80,
    ) -> None:
        self.logos_dir = Path(logos_dir)
        self.fuzzy_threshold = fuzzy_threshold
        self._index: Dict[str, Path] = {}          # fingerprint -> logo path
        self._aliases: Dict[str, str] = {}          # fingerprint -> logo filename
        self._gamesheet_cache: Dict[int, str] = {}  # team_id -> CDN URL
        self._team_name_cache: Dict[int, str] = {}  # team_id -> team_name
        self._refresh_index()
        self._build_aliases()

    def _refresh_index(self) -> None:
        """Scan logos directory and index all files by fingerprint."""
        self._index.clear()
        if not self.logos_dir.exists():
            return
        for path in sorted(self.logos_dir.iterdir()):
            if path.suffix.lower() in {".svg", ".png", ".jpg", ".jpeg", ".webp"}:
                slug = self._fingerprint(path.stem)
                self._index[slug] = path

    def _build_aliases(self) -> None:
        """Manual overrides for tricky team names."""
        manual = {
            # Bay State Waves / Breakers
            "Bay State Waves": "bay_state_breakers.svg",
            "Bay State Waves 2017 UG": "bay_state_breakers.svg",
            "Bay State Waves 2017": "bay_state_breakers.svg",
            "Bay State Waves UG": "bay_state_breakers.svg",
            "Bay State Breakers": "bay_state_breakers.svg",
            # WHK variants
            "WHK": "WHK.svg",
            "WHK Hawks": "WHK.svg",
            "WHK U10C": "WHK.svg",
            "WHK U10B": "WHK.svg",
            "WHK U12B": "WHK.svg",
            "WHK U12C": "WHK.svg",
            "WHK U14B": "WHK.svg",
            "WHK U8A": "WHK.svg",
            "WHK U8B": "WHK.svg",
            "Whitman Hanson Kingston": "WHK.svg",
            # Silver Lake
            "Silver Lake - White": "silverlake.svg",
            "Silver Lake White": "silverlake.svg",
            "Silver Lake": "silverlake.svg",
            # Hanover girls
            "Hanover 2": "hanover_girls.svg",
            "Hanover Girls": "hanover_girls.svg",
            "Hanover Girls Red": "hanover_girls.svg",
            "Hanover Girls White": "hanover_girls.svg",
            # Hingham girls
            "Hingham Girls": "hingham_girls.svg",
            # Seahawks
            "Seahawks Squirt Grey": "south_shore_seahawks.svg",
            "Seahawks Squirt Yellow": "south_shore_seahawks.svg",
            "Seahawks": "south_shore_seahawks.svg",
            "South Shore Seahawks": "south_shore_seahawks.svg",
            # South Shore Eagles
            "South Shore Eagles": "south_shore_eagles.svg",
            # Tri County
            "Tri County": "tricounty.svg",
            # Cape Cod
            "Cape Cod Gulls": "cape_cod_gulls.svg",
            "Cape Cod Waves": "capecodwaves.svg",
            # Cohasset Hull
            "Cohasset Hull": "cohasset_hull.svg",
            "Cohasset/Hull": "cohasset_hull.svg",
            # Abington
            "Abington": "Abington_youht_hockey.svg",
            "Abington Youth Hockey": "Abington_youht_hockey.svg",
            # KP / Walpole
            "KP Walpole": "kp_walpole.svg",
            "King Philip Walpole": "kp_walpole.svg",
            # North Shore
            "North Shore Shamrocks": "Northshoreshamrocks.svg",
            # Whitman Hanson
            "Whitman Hanson": "whitmanhanson.svg",
            # Beantown
            "Beantown Bullies": "beantown_bullies.svg",
            # Plymouth variants
            "Plymouth Plourde": "plymouth.svg",
            "Plymouth": "plymouth.svg",
            # Braintree
            "Braintree Red": "braintree.svg",
            "Braintree": "braintree.svg",
            # Marshfield
            "Marshfield U10C": "marshfield.svg",
            "Marshfield": "marshfield.svg",
            # SC Panthers
            "SC Panthers": "sc_panthers.svg",
            # Mass Admirals
            "Mass Admirals": "mass_admirals.svg",
            "Massachusetts Admirals": "mass_admirals.svg",
            # Boch Blazers
            "Boch Blazers": "boch_blazers.svg",
            "Boch Blazers - Adams": "boch_blazers.svg",
            "Boch Blazers - Black": "boch_blazers.svg",
            "Boch Blazers - Busch": "boch_blazers.svg",
            "Boch Blazers - Connors": "boch_blazers.svg",
            "Boch Blazers - Dandurand": "boch_blazers.svg",
            "Boch Blazers - Doolin": "boch_blazers.svg",
            "Boch Blazers - Fox": "boch_blazers.svg",
            "Boch Blazers - Gallagher": "boch_blazers.svg",
            "Boch Blazers - Hardiman": "boch_blazers.svg",
            "Boch Blazers - Hartery": "boch_blazers.svg",
            "Boch Blazers - Haviland": "boch_blazers.svg",
            "Boch Blazers - McPhee": "boch_blazers.svg",
            "Boch Blazers - Melanson": "boch_blazers.svg",
            "Boch Blazers - Mellino": "boch_blazers.svg",
            "Boch Blazers - Rice": "boch_blazers.svg",
            "Boch Blazers - Tanguay": "boch_blazers.svg",
            "Boch Blazers- Parker": "boch_blazers.svg",
            # South Shore Kings / Knights (same org)
            "South Shore Kings": "south_shore_kings.svg",
            "South Shore Knights": "south_shore_kings.svg",
            "South Shore Kings  - Lavery": "south_shore_kings.svg",
            "South Shore Kings - Lavery": "south_shore_kings.svg",
            "South Shore Kings - Petherick": "south_shore_kings.svg",
            "South Shore Kings - Szabo": "south_shore_kings.svg",
            "South Shore Kings Sarno": "south_shore_kings.svg",
            "South Shore Kings U15 Mahoney": "south_shore_kings.svg",
            "South Shore Kings U16 Azevedo": "south_shore_kings.svg",
            "South Shore Kings U16 Connolly": "south_shore_kings.svg",
            "South Shore Kings U18 Mahoney": "south_shore_kings.svg",
            "South Shore Kings [hs]": "south_shore_kings.svg",
            # Top Gun
            "Top Gun": "topgun.svg",
            "Top Gun - Buonopane": "topgun.svg",
            "Top Gun - Connors": "topgun.svg",
            "Top Gun - Fairburn": "topgun.svg",
            "Top Gun - Lemire": "topgun.svg",
            "Top Gun - Luccisano": "topgun.svg",
            "Top Gun - Rome": "topgun.svg",
            "Top Gun American": "topgun.svg",
            # Boston Jr Eagles
            "Boston Jr Eagles": "boston_jr_eagles.svg",
            "Boston Jr Eagles (Winter Team)": "boston_jr_eagles.svg",
            "Boston Jr Eagles - Birnbaum": "boston_jr_eagles.svg",
            "Boston Jr Eagles - Fryberger": "boston_jr_eagles.svg",
            "Boston Jr Eagles - Pratt": "boston_jr_eagles.svg",
            "Boston Jr Eagles 2018 Elite": "boston_jr_eagles.svg",
            # Seacoast Spartans
            "Seacoast Spartans": "Spartans.svg",
            # Minuteman Flames / Sparks
            "Minuteman Flames": "Minuteman.svg",
            "Minuteman Flames - Bellefeuille": "Minuteman.svg",
            "Minuteman Flames - Deal": "Minuteman.svg",
            "Minuteman Flames - Enegess": "Minuteman.svg",
            "Minuteman Flames - Fournier": "Minuteman.svg",
            "Minuteman Flames - Gorman": "Minuteman.svg",
            "Minuteman Flames - Graham": "Minuteman.svg",
            "Minuteman Flames - Hayes": "Minuteman.svg",
            "Minuteman Flames - Hogan": "Minuteman.svg",
            "Minuteman Flames - Ingoldsby": "Minuteman.svg",
            "Minuteman Flames - Lefebvre": "Minuteman.svg",
            "Minuteman Flames - Lester": "Minuteman.svg",
            "Minuteman Flames - Markey": "Minuteman.svg",
            "Minuteman Flames - Nute": "Minuteman.svg",
            "Minuteman Flames - Rancourt": "Minuteman.svg",
            "Minuteman Flames - Resnick": "Minuteman.svg",
            "Minuteman Flames - Wall": "Minuteman.svg",
            "Minuteman Flames - Welburn": "Minuteman.svg",
            "Minuteman Flames - Welsh": "Minuteman.svg",
            "Minuteman Flames Anderson": "Minuteman.svg",
            "Minuteman Flames Hannon/Balzarini": "Minuteman.svg",
            "Minuteman Flames Renfroe": "Minuteman.svg",
            "Minuteman Sparks": "Minuteman.svg",
            "Minuteman Sparks - Cardarelli": "Minuteman.svg",
            "Minuteman Sparks - Griffin": "Minuteman.svg",
            "Minuteman Sparks - ONeil": "Minuteman.svg",
            # Islanders Hockey Club
            "Islanders Hockey Club": "ihs_hockey.svg",
            "Islanders Hockey Club (East)": "ihs_hockey.svg",
            "Islanders Hockey Club (West)": "ihs_hockey.svg",
            "Islanders Hockey Club (Winter Team)": "ihs_hockey.svg",
            "IHC": "ihs_hockey.svg",
            "IHC West - Enwright": "ihs_hockey.svg",
            # Boston Jr Terriers
            "Boston Jr Terriers": "bu_terrier.svg",
            "Boston Jr Terriers (Red)": "bu_terrier.svg",
            "Boston Jr Terriers (Red) - OLeary": "bu_terrier.svg",
            "Boston Jr Terriers (Red) - Tsanotelis": "bu_terrier.svg",
            "Boston Jr Terriers (White)": "bu_terrier.svg",
            "Boston Jr Terriers (White) - Jordan": "bu_terrier.svg",
            "Boston Jr Terriers 18U Elite - Pinkham": "bu_terrier.svg",
            "Boston Jr Terriers Red - Carroll": "bu_terrier.svg",
            "Boston Jr Terriers Red - Karlberg": "bu_terrier.svg",
            "Boston Jr Terriers Red Davis": "bu_terrier.svg",
            "Boston Jr Terriers Red Healy": "bu_terrier.svg",
            "Boston Jr Terriers Red MacQuade": "bu_terrier.svg",
            "Boston Jr Terriers Red-White Richardi": "bu_terrier.svg",
            "Boston Jr Terriers U16 Lanno/Curtis": "bu_terrier.svg",
            "Boston Jr Terriers White": "bu_terrier.svg",
            "Boston Jr Terriers White - Barravecchio": "bu_terrier.svg",
            "Boston Jr Terriers White - Darcy": "bu_terrier.svg",
            "Boston Jr Terriers White - Darmetko": "bu_terrier.svg",
            "Boston Jr Terriers White - Malone": "bu_terrier.svg",
            "Boston Jr Terriers White - Nones": "bu_terrier.svg",
            "Boston Jr Terriers White - Trudeau": "bu_terrier.svg",
            "Boston Jr Terriers White Carroll": "bu_terrier.svg",
            "Boston Jr Terriers White Macdonald": "bu_terrier.svg",
            "Boston Jr Terriers White Thurston": "bu_terrier.svg",
            # Boston Jr Dogs (same org as Terriers)
            "Boston Jr Dogs (Red)": "bu_terrier.svg",
            "Boston Jr Dogs (Red) - Black": "bu_terrier.svg",
            "Boston Jr Dogs (White)": "bu_terrier.svg",
            "Boston Jr Dogs Red": "bu_terrier.svg",
            "Boston Jr Dogs White": "bu_terrier.svg",
            # MC Selects
            "MC Selects": "mc_select.svg",
            "MC Selects - Gajda": "mc_select.svg",
            # NorthStars Hockey Club
            "NorthStars Hockey Club": "Northstars.svg",
            "NorthStars - Boyer": "Northstars.svg",
            "NorthStars - Conley": "Northstars.svg",
            "NorthStars - Forde": "Northstars.svg",
            "NorthStars - Fournier": "Northstars.svg",
            "NorthStars - Frutman": "Northstars.svg",
            "NorthStars - Greene": "Northstars.svg",
            "NorthStars - Kimpland": "Northstars.svg",
            "NorthStars - Macmillan": "Northstars.svg",
            "NorthStars - Oram": "Northstars.svg",
            "NorthStars - Stamuli": "Northstars.svg",
            "NorthStars - Tuccio": "Northstars.svg",
            "NorthStars - Zina": "Northstars.svg",
            "NorthStars Hockey Club - Dolesh [hs]": "Northstars.svg",
            # Northeast Generals / Spitfires (same org)
            "Northeast Generals": "northeast_generals.svg",
            "Northeast Generals - Cottreau": "northeast_generals.svg",
            "Northeast Generals - Enos": "northeast_generals.svg",
            "Northeast Generals - Hickey": "northeast_generals.svg",
            "Northeast Generals - Manley": "northeast_generals.svg",
            "Northeast Generals - McCarthy": "northeast_generals.svg",
            "Northeast Generals - Miller": "northeast_generals.svg",
            "Northeast Generals - Remes": "northeast_generals.svg",
            "Northeast Generals - Rollock": "northeast_generals.svg",
            "Northeast Generals - Ruggiero": "northeast_generals.svg",
            "Northeast Generals 18U": "northeast_generals.svg",
            "Northeast Generals Bradford": "northeast_generals.svg",
            "Northeast Generals Cape": "northeast_generals.svg",
            "Northeast Generals UG": "northeast_generals.svg",
            "Spitfires": "spitfires.svg",
            # Northern Cyclones / Cyclones Academy
            "Cyclones Academy": "cyclones_academy.png",
            "Northern Cyclones": "cyclones_academy.png",
            "Northern Cyclones - Abbis": "cyclones_academy.png",
            "Northern Cyclones - Bartlett": "cyclones_academy.png",
            "Northern Cyclones - Chase": "cyclones_academy.png",
            "Northern Cyclones - Chiulli": "cyclones_academy.png",
            "Northern Cyclones - Conover": "cyclones_academy.png",
            "Northern Cyclones - Corbett": "cyclones_academy.png",
            "Northern Cyclones - Ellis": "cyclones_academy.png",
            "Northern Cyclones - LaMarche": "cyclones_academy.png",
            "Northern Cyclones - Lenti": "cyclones_academy.png",
            "Northern Cyclones - McLaughlin": "cyclones_academy.png",
            "Northern Cyclones - Mowder": "cyclones_academy.png",
            "Northern Cyclones - Philipp": "cyclones_academy.png",
            # MassConn United
            "MassConn United Hockey Club": "massconn_united.png",
            "MassConn United Hockey Club - Cornish": "massconn_united.png",
            "MassConn United Hockey Club - Gajda": "massconn_united.png",
            "MassConn United Hockey Club - Grimson": "massconn_united.png",
            "MassConn United Hockey Club McNair - Graham": "massconn_united.png",
            # Bulldogs Hockey Club
            "Bulldogs Hockey Club": "bulldogs_hockey.png",
            "Bulldogs Hockey Club - Longo": "bulldogs_hockey.png",
            "Bulldogs Hockey Club - Riley": "bulldogs_hockey.png",
            "Bulldogs Hockey Club U15": "bulldogs_hockey.png",
            "Bulldogs Hockey Club U16": "bulldogs_hockey.png",
            "Bulldogs Hockey Club U18": "bulldogs_hockey.png",
            "Boston Bulldogs": "bulldogs_hockey.png",
            # Young Guns
            "Young Guns": "young_guns.svg",
            "Young Guns - Kent": "young_guns.svg",
        }
        self._manual_aliases = manual  # Store original names for DB import
        for name, filename in manual.items():
            self._aliases[self._fingerprint(name)] = filename

    @staticmethod
    def _fingerprint(value: str) -> str:
        """Normalize a string to an alphanumeric lowercase fingerprint."""
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(ch for ch in normalized.lower() if ch.isalnum())

    @staticmethod
    def _strip_suffixes(team_name: str) -> str:
        """Remove division/color/age suffixes from a team name."""
        stripped = _STRIP_RE.sub("", team_name)
        return re.sub(r'\s+', ' ', stripped).strip()

    def match_local(self, team_name: str) -> tuple[Optional[str], Optional[float]]:
        """
        Match a team name to a local logo file.
        Returns (filename, confidence) or (None, None).
        """
        if not team_name:
            return None, None

        fp = self._fingerprint(team_name)

        # 1. Check alias map (exact overrides)
        if fp in self._aliases:
            filename = self._aliases[fp]
            path = self.logos_dir / filename
            if path.exists():
                return filename, 1.0

        # 2. Exact fingerprint match against index
        if fp in self._index:
            return self._index[fp].name, 1.0

        # 3. Try with stripped suffixes
        stripped = self._strip_suffixes(team_name)
        sfp = self._fingerprint(stripped)
        if sfp in self._aliases:
            filename = self._aliases[sfp]
            path = self.logos_dir / filename
            if path.exists():
                return filename, 0.95
        if sfp in self._index:
            return self._index[sfp].name, 0.95

        # 4. Fuzzy match against index
        best_file: Optional[str] = None
        best_score = 0.0
        for slug, path in self._index.items():
            # Try both original and stripped fingerprints
            for candidate_fp in (fp, sfp):
                score = SequenceMatcher(None, candidate_fp, slug).ratio()
                if score > best_score:
                    best_score = score
                    best_file = path.name
        if best_file and best_score >= self.fuzzy_threshold:
            return best_file, round(best_score, 3)

        return None, None

    def match(self, team_name: str, team_id: Optional[int] = None) -> LogoResult:
        """
        Full logo lookup: local file + GameSheet CDN URL.
        Returns a LogoResult with both sources resolved.
        """
        local_file, confidence = self.match_local(team_name)
        gs_url = self._gamesheet_cache.get(team_id) if team_id else None

        if local_file and gs_url:
            source = "both"
        elif local_file:
            source = "local"
        elif gs_url:
            source = "gamesheet"
        else:
            source = "none"

        return LogoResult(
            team_name=team_name,
            team_id=team_id,
            local_file=local_file,
            gamesheet_url=gs_url,
            source=source,
            match_confidence=confidence,
        )

    def get_logo_path(self, team_name: str) -> Optional[Path]:
        """Return the full local file path for a team's logo, or None."""
        filename, _ = self.match_local(team_name)
        if filename:
            path = self.logos_dir / filename
            if path.exists():
                return path
        return None

    def list_local_logos(self) -> List[str]:
        """List all available local logo filenames."""
        return sorted(p.name for p in self._index.values())

    def search(self, query: str, limit: int = 10) -> List[LogoResult]:
        """
        Fuzzy search across all known team names (from GameSheet cache + local index).
        Returns top matches sorted by confidence.
        """
        results = []
        qfp = self._fingerprint(query)

        # Search local index
        for slug, path in self._index.items():
            score = SequenceMatcher(None, qfp, slug).ratio()
            if score > 0.4:
                results.append(LogoResult(
                    team_name=path.stem,
                    local_file=path.name,
                    source="local",
                    match_confidence=round(score, 3),
                ))

        # Search cached GameSheet teams
        for tid, tname in self._team_name_cache.items():
            tfp = self._fingerprint(tname)
            score = SequenceMatcher(None, qfp, tfp).ratio()
            if score > 0.4:
                local_file, conf = self.match_local(tname)
                gs_url = self._gamesheet_cache.get(tid)
                source = "both" if local_file and gs_url else ("local" if local_file else ("gamesheet" if gs_url else "none"))
                results.append(LogoResult(
                    team_name=tname,
                    team_id=tid,
                    local_file=local_file,
                    gamesheet_url=gs_url,
                    source=source,
                    match_confidence=round(score, 3),
                ))

        # Dedupe by team_name, keep highest confidence
        seen = {}
        for r in results:
            key = self._fingerprint(r.team_name)
            if key not in seen or (r.match_confidence or 0) > (seen[key].match_confidence or 0):
                seen[key] = r
        results = sorted(seen.values(), key=lambda r: r.match_confidence or 0, reverse=True)
        return results[:limit]

    # -------------------------------------------------------------------------
    # GameSheet API integration
    # -------------------------------------------------------------------------

    def _curl_json(self, url: str) -> Optional[dict | list]:
        """Fetch JSON from a URL using curl (avoids urllib 403 issues)."""
        try:
            result = subprocess.run(
                ["curl", "-s", url],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        return None

    def load_gamesheet_teams(self, season_id: int = None) -> int:
        """
        Fetch all divisions and teams from the GameSheet API for a season.
        Populates the internal gamesheet_cache with team_id -> CDN URL mappings.
        Returns the number of teams loaded.
        If season_id is None, loads all seasons from DEFAULT_SEASON_IDS.
        """
        if season_id is None:
            total = 0
            for sid in DEFAULT_SEASON_IDS:
                total += self.load_gamesheet_teams(sid)
            return total

        # 1. Get all divisions
        divisions = self._curl_json(
            f"{GAMESHEET_API_BASE}/useSeasonDivisions/getDivisions/{season_id}"
        )
        if not divisions or not isinstance(divisions, list):
            return 0

        div_ids = ",".join(str(d["id"]) for d in divisions)

        # 2. Get standings for all divisions (contains team names, IDs, logos)
        url = (
            f"{GAMESHEET_API_BASE}/useStandings/getDivisionStandings/{season_id}"
            f"?filter%5Bdivisions%5D={div_ids}"
            f"&filter%5Blimit%5D=200&filter%5Boffset%5D=0"
            f"&filter%5BtimeZoneOffset%5D=-300"
        )
        standings = self._curl_json(url)
        if not standings or not isinstance(standings, list):
            return 0

        count = 0
        for division in standings:
            table = division.get("tableData", {})
            team_ids = table.get("teamIds", [])
            team_titles = table.get("teamTitles", [])
            team_logos = table.get("teamLogos", [])

            for i, tid in enumerate(team_ids):
                name = team_titles[i]["title"] if i < len(team_titles) else f"Team {tid}"
                logo = team_logos[i] if i < len(team_logos) else None

                self._team_name_cache[tid] = name
                if logo:
                    self._gamesheet_cache[tid] = logo
                count += 1

        return count

    def build_manifest(self, season_id: int = None) -> LogoManifestData:
        """
        Build a complete cross-reference manifest for all teams in a season.
        Queries GameSheet API, matches each team to local logos.
        """
        from datetime import datetime

        # Default to first season if not specified
        if season_id is None:
            season_id = DEFAULT_SEASON_IDS[0]

        # Load GameSheet data if not already cached
        if not self._team_name_cache:
            self.load_gamesheet_teams(season_id)

        # Get season name
        season_info = self._curl_json(
            f"{GAMESHEET_API_BASE}/useSeasonDivisions/getSeason/{season_id}"
        )
        season_name = season_info.get("title", f"Season {season_id}") if season_info else f"Season {season_id}"

        manifest = LogoManifestData(
            season_id=season_id,
            season_name=season_name,
            generated_at=datetime.now().isoformat(),
        )

        # Match each team
        for tid, tname in sorted(self._team_name_cache.items(), key=lambda x: x[1]):
            result = self.match(tname, tid)
            manifest.teams.append(result)

        manifest.total_teams = len(manifest.teams)
        manifest.matched_local = sum(1 for t in manifest.teams if t.local_file)
        manifest.matched_gamesheet = sum(1 for t in manifest.teams if t.gamesheet_url)
        manifest.unmatched = sum(1 for t in manifest.teams if t.source == "none")

        return manifest

    # -------------------------------------------------------------------------
    # Database Integration - Consolidated Logo Storage
    # -------------------------------------------------------------------------

    def populate_logo_tables(self, db_path: str = "hockey_stats.db") -> dict:
        """
        Populate the logos and logo_aliases tables from all sources:
        1. Local SVG files in logos/ directory
        2. GameSheet API team data (from teams table)
        3. Manual aliases

        Returns dict with counts of records created.
        """
        import sqlite3
        from datetime import datetime

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        stats = {'logos_created': 0, 'aliases_created': 0, 'updated': 0}

        # Step 1: Import local logo files as canonical logos
        if self.logos_dir.exists():
            for path in sorted(self.logos_dir.iterdir()):
                if path.suffix.lower() in {".svg", ".png", ".jpg", ".jpeg", ".webp"}:
                    canonical = self._fingerprint(path.stem)
                    display = path.stem.replace('_', ' ').replace('-', ' ').title()
                    is_league = 'league' in path.stem.lower() or path.stem in ['BSHL', 'EHF']

                    cursor.execute('''
                        INSERT INTO logos (canonical_name, display_name, local_file, source, is_league_logo)
                        VALUES (?, ?, ?, 'local', ?)
                        ON CONFLICT(canonical_name) DO UPDATE SET
                            local_file = excluded.local_file,
                            source = CASE
                                WHEN logos.gamesheet_url IS NOT NULL THEN 'both'
                                ELSE 'local'
                            END,
                            updated_at = CURRENT_TIMESTAMP
                    ''', (canonical, display, path.name, is_league))
                    stats['logos_created'] += cursor.rowcount

        # Step 2: Import GameSheet URLs from teams table
        cursor.execute('''
            SELECT DISTINCT team_name, team_id, logo_url
            FROM teams
            WHERE logo_url IS NOT NULL AND logo_url != ''
        ''')
        for team_name, team_id, logo_url in cursor.fetchall():
            canonical = self._fingerprint(self._strip_suffixes(team_name))
            display = self._strip_suffixes(team_name)

            # Upsert into logos table
            cursor.execute('''
                INSERT INTO logos (canonical_name, display_name, gamesheet_url, source)
                VALUES (?, ?, ?, 'gamesheet')
                ON CONFLICT(canonical_name) DO UPDATE SET
                    gamesheet_url = COALESCE(logos.gamesheet_url, excluded.gamesheet_url),
                    source = CASE
                        WHEN logos.local_file IS NOT NULL THEN 'both'
                        ELSE 'gamesheet'
                    END,
                    updated_at = CURRENT_TIMESTAMP
            ''', (canonical, display, logo_url))

            # Get the logo_id
            cursor.execute('SELECT id FROM logos WHERE canonical_name = ?', (canonical,))
            logo_id = cursor.fetchone()[0]

            # Create alias for exact team name
            cursor.execute('''
                INSERT INTO logo_aliases (team_name, team_id, logo_id, match_confidence)
                VALUES (?, ?, ?, 1.0)
                ON CONFLICT(team_name, team_id) DO UPDATE SET
                    logo_id = excluded.logo_id
            ''', (team_name, team_id, logo_id))
            stats['aliases_created'] += cursor.rowcount

        # Step 3: Import manual aliases (use original names, not fingerprints)
        for team_name, filename in self._manual_aliases.items():
            # Find the logo_id for this filename
            cursor.execute('SELECT id FROM logos WHERE local_file = ?', (filename,))
            row = cursor.fetchone()
            if row:
                logo_id = row[0]
                cursor.execute('''
                    INSERT OR IGNORE INTO logo_aliases (team_name, team_id, logo_id, is_manual_override)
                    VALUES (?, NULL, ?, 1)
                ''', (team_name, logo_id))
                stats['aliases_created'] += cursor.rowcount

        conn.commit()
        conn.close()

        return stats

    def match_from_db(self, team_name: str, team_id: int = None, db_path: str = "hockey_stats.db") -> LogoResult:
        """
        Look up logo from database tables (faster than API calls).
        Falls back to fuzzy matching if no exact match found.
        """
        import sqlite3

        result = LogoResult(team_name=team_name, team_id=team_id)

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Try exact alias match first
            if team_id:
                cursor.execute('''
                    SELECT l.local_file, l.gamesheet_url, la.match_confidence
                    FROM logo_aliases la
                    JOIN logos l ON la.logo_id = l.id
                    WHERE la.team_name = ? AND la.team_id = ?
                ''', (team_name, team_id))
            else:
                cursor.execute('''
                    SELECT l.local_file, l.gamesheet_url, la.match_confidence
                    FROM logo_aliases la
                    JOIN logos l ON la.logo_id = l.id
                    WHERE la.team_name = ?
                    ORDER BY la.is_manual_override DESC, l.local_file IS NOT NULL DESC, la.match_confidence DESC
                    LIMIT 1
                ''', (team_name,))

            row = cursor.fetchone()
            if row:
                result.local_file = row[0]
                result.gamesheet_url = row[1]
                result.match_confidence = row[2]
                if result.local_file and result.gamesheet_url:
                    result.source = "both"
                elif result.local_file:
                    result.source = "local"
                elif result.gamesheet_url:
                    result.source = "gamesheet"
                conn.close()
                return result

            # Try canonical name match
            canonical = self._fingerprint(self._strip_suffixes(team_name))
            cursor.execute('''
                SELECT local_file, gamesheet_url
                FROM logos
                WHERE canonical_name = ?
            ''', (canonical,))

            row = cursor.fetchone()
            if row:
                result.local_file = row[0]
                result.gamesheet_url = row[1]
                result.match_confidence = 0.9
                if result.local_file and result.gamesheet_url:
                    result.source = "both"
                elif result.local_file:
                    result.source = "local"
                elif result.gamesheet_url:
                    result.source = "gamesheet"
                conn.close()
                return result

            conn.close()

        except Exception:
            pass

        # Fall back to in-memory matching
        return self.match(team_name, team_id)

    def get_logo_stats(self, db_path: str = "hockey_stats.db") -> dict:
        """Get statistics about logo coverage from database."""
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        stats = {}

        cursor.execute('SELECT COUNT(*) FROM logos')
        stats['total_logos'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM logos WHERE local_file IS NOT NULL")
        stats['with_local'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM logos WHERE gamesheet_url IS NOT NULL")
        stats['with_gamesheet'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM logos WHERE source = 'both'")
        stats['with_both'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM logo_aliases')
        stats['total_aliases'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM logo_aliases WHERE is_manual_override = 1')
        stats['manual_overrides'] = cursor.fetchone()[0]

        conn.close()
        return stats
