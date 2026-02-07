"""
Pydantic models for Hockey Stats API
LLM-friendly response models with context, interpretation, and comparisons
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime


# ============================================================================
# COMMON MODELS
# ============================================================================

class StatWithContext(BaseModel):
    """Statistical value with contextual information for LLM interpretation"""
    value: float | int
    rank: Optional[int] = None
    rank_suffix: Optional[str] = None  # "1st", "2nd", "3rd", etc.
    total_teams: Optional[int] = None
    percentile: Optional[float] = None
    league_average: Optional[float] = None
    division_average: Optional[float] = None
    interpretation: Optional[str] = None
    context: Optional[str] = None


class TeamBasic(BaseModel):
    """Basic team information"""
    team_id: int
    team_name: str
    division_id: Optional[int] = None
    division_name: Optional[str] = None
    logo_url: Optional[str] = None


class PlayerBasic(BaseModel):
    """Basic player information"""
    player_id: str
    player_number: Optional[str] = None
    player_name: Optional[str] = None
    position: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None


# ============================================================================
# SEASON & DIVISION MODELS
# ============================================================================

class SeasonInfo(BaseModel):
    """Season information"""
    season_id: str
    title: str
    sport: str
    association: Optional[str] = None
    divisions_count: int
    teams_count: int
    games_count: int
    assist_value: Optional[int] = None
    goal_value: Optional[int] = None
    max_goal_differential: Optional[int] = None


class DivisionInfo(BaseModel):
    """Division information"""
    division_id: int
    division_name: str
    season_id: str
    teams_count: int
    games_count: int
    assist_value: Optional[int] = None
    goal_value: Optional[int] = None


class DivisionsList(BaseModel):
    """List of divisions"""
    season_id: str
    divisions: List[DivisionInfo]


# ============================================================================
# TEAM MODELS
# ============================================================================

class TeamRecord(BaseModel):
    """Team record statistics"""
    games_played: int
    wins: int
    losses: int
    ties: int
    otw: int = 0
    otl: int = 0
    sow: int = 0
    sol: int = 0
    points: int
    points_pct: float
    row: int = 0  # Regulation + OT wins
    division_rank: Optional[int] = None

    # Context
    record_string: str = Field(description="Human-readable record like '10-4-1'")
    interpretation: Optional[str] = None


class TeamScoring(BaseModel):
    """Team scoring statistics"""
    goals_for: StatWithContext
    goals_against: StatWithContext
    goal_differential: StatWithContext
    goals_per_game: StatWithContext
    goals_against_per_game: StatWithContext

    # By period
    period_1_for: Optional[int] = None
    period_1_against: Optional[int] = None
    period_2_for: Optional[int] = None
    period_2_against: Optional[int] = None
    period_3_for: Optional[int] = None
    period_3_against: Optional[int] = None
    overtime_for: Optional[int] = None
    overtime_against: Optional[int] = None


class SpecialTeamsStats(BaseModel):
    """Special teams statistics"""
    power_play_goals: int
    power_play_opportunities: int
    power_play_pct: StatWithContext

    penalty_kill_goals_against: int
    times_shorthanded: int
    penalty_kill_pct: StatWithContext

    short_handed_goals: int
    short_handed_goals_against: int


class DisciplineStats(BaseModel):
    """Discipline statistics"""
    penalty_minutes: int
    pim_per_game: StatWithContext
    penalties_taken: int
    major_penalties: int
    game_misconducts: int


class HomeAwayStats(BaseModel):
    """Home/Away split statistics"""
    record: str
    goals_for: int
    goals_against: int
    points: int
    goal_differential: int


class RecentFormGame(BaseModel):
    """Single recent game result"""
    date: str
    opponent: str
    opponent_id: int
    result: str  # "W", "L", "T"
    score: str
    is_home: bool


class RecentForm(BaseModel):
    """Recent form statistics"""
    last_10: str
    current_streak: str
    streak_count: int
    last_5_games: List[RecentFormGame]


class StrengthOfSchedule(BaseModel):
    """Strength of schedule analysis"""
    sos: float
    sos_rank: int
    adjusted_sos: Optional[float] = None
    strength_of_victory: Optional[float] = None

    games_vs_top_third: int
    games_vs_middle_third: int
    games_vs_bottom_third: int
    points_vs_top_third: int
    points_vs_middle_third: int
    points_vs_bottom_third: int

    rest_differential: Optional[int] = None
    interpretation: Optional[str] = None


class TeamStatsComplete(BaseModel):
    """Complete team statistics"""
    team: TeamBasic
    record: TeamRecord
    scoring: TeamScoring
    special_teams: SpecialTeamsStats
    discipline: DisciplineStats
    home_stats: HomeAwayStats
    away_stats: HomeAwayStats
    recent_form: RecentForm
    strength_of_schedule: Optional[StrengthOfSchedule] = None

    data_quality: Optional[Dict[str, Any]] = None


class StandingsEntry(BaseModel):
    """Single standings entry"""
    rank: int
    team: TeamBasic
    record: TeamRecord
    scoring: Dict[str, int]
    special_teams: Optional[Dict[str, Any]] = None


class DivisionStandings(BaseModel):
    """Division standings"""
    division: DivisionInfo
    standings: List[StandingsEntry]
    last_updated: Optional[datetime] = None


# ============================================================================
# PLAYER MODELS
# ============================================================================

class PlayerIdentity(BaseModel):
    """Player identity information with data quality"""
    player_number: str
    player_name: Optional[str] = None
    position: Optional[str] = None
    number_variations: List[str]
    number_consistency_score: float
    name_available: bool


class PlayerStats(BaseModel):
    """Player statistics"""
    games_played: int
    goals: int
    assists: int
    points: int
    points_per_game: float

    # Special teams
    power_play_goals: int
    power_play_assists: int
    power_play_points: int
    short_handed_goals: int
    short_handed_assists: int
    game_winning_goals: int
    empty_net_goals: int

    # Discipline
    penalties: int
    penalty_minutes: int
    pim_per_game: float
    major_penalties: int

    # Context
    team_rank_points: Optional[int] = None
    division_rank_points: Optional[int] = None


class GoalDetail(BaseModel):
    """Individual goal detail"""
    game_id: str
    date: str
    opponent: str
    opponent_id: int
    period: str
    time: str
    assists: List[str]
    goal_type: List[str]  # ["PP", "SHG", "GWG", "EN"]
    game_result: str


class PenaltyDetail(BaseModel):
    """Individual penalty detail"""
    game_id: str
    date: str
    opponent: str
    opponent_id: int
    period: str
    time: str
    penalty_type: str
    duration: int
    is_major: bool


class PlayerGameLog(BaseModel):
    """Single game performance"""
    game_id: str
    date: str
    opponent: str
    opponent_id: int
    is_home_game: bool

    goals: int
    assists: int
    points: int
    pim: int
    plus_minus: Optional[int] = None

    pp_goals: int
    sh_goals: int
    gwg: int

    number_used: str
    number_matches_usual: bool


class DataQuality(BaseModel):
    """Data quality information"""
    confidence_score: float
    issues: List[str]
    notes: str


class PlayerProfile(BaseModel):
    """Complete player profile"""
    player: PlayerBasic
    identity: PlayerIdentity
    stats: PlayerStats
    goal_details: List[GoalDetail]
    penalty_log: List[PenaltyDetail]
    data_quality: DataQuality


# ============================================================================
# GAME MODELS
# ============================================================================

class GameInfo(BaseModel):
    """Game information"""
    game_id: str
    season_id: str
    division_id: int
    division_name: str
    game_number: str
    game_type: str
    date: str
    time: str
    location: str
    status: str

    home_team: TeamBasic
    visitor_team: TeamBasic

    home_score: Optional[int] = None
    visitor_score: Optional[int] = None


class GoalEvent(BaseModel):
    """Goal event detail"""
    period: str
    time: str
    team: TeamBasic

    scorer: PlayerBasic
    scorer_total_goals: Optional[int] = None

    assist1: Optional[PlayerBasic] = None
    assist2: Optional[PlayerBasic] = None

    is_power_play: bool
    is_short_handed: bool
    is_game_winning: bool
    is_empty_net: bool


class PenaltyEvent(BaseModel):
    """Penalty event detail"""
    period: str
    time: str
    team: TeamBasic

    player: PlayerBasic
    penalty_type: str
    penalty_class: str
    duration_minutes: int
    is_major: bool

    served_by: Optional[PlayerBasic] = None


class RosterPlayer(BaseModel):
    """Player roster entry for game"""
    player: PlayerBasic
    status: str
    is_starting: bool

    goals: int
    assists: int
    points: int
    pim: int

    # Goalie stats if applicable
    goals_against: Optional[int] = None
    shots_against: Optional[int] = None
    save_pct: Optional[float] = None


class GameBoxScore(BaseModel):
    """Complete game box score"""
    game: GameInfo

    goals_by_period: List[GoalEvent]
    penalties_by_period: List[PenaltyEvent]

    home_roster: List[RosterPlayer]
    visitor_roster: List[RosterPlayer]

    period_summary: Dict[str, Dict[str, int]]  # Period -> {home_goals, visitor_goals}


class GameSummary(BaseModel):
    """Game summary statistics"""
    game: GameInfo

    total_goals: int
    total_penalties: int
    total_pim: int

    home_pp_goals: int
    home_pp_opportunities: int
    visitor_pp_goals: int
    visitor_pp_opportunities: int

    three_stars: Optional[List[PlayerBasic]] = None


# ============================================================================
# HEAD-TO-HEAD MODELS
# ============================================================================

class HeadToHeadGame(BaseModel):
    """Single head-to-head game"""
    game_id: str
    date: str
    location: str
    result: str
    home_team: str
    visitor_team: str
    home_score: int
    visitor_score: int
    top_scorers: List[Dict[str, Any]]


class SpecialTeamsMatchup(BaseModel):
    """Special teams matchup analysis"""
    team1_pp_pct: float
    team2_pk_pct: float
    edge: str
    interpretation: str


class HeadToHead(BaseModel):
    """Head-to-head record"""
    team1: TeamBasic
    team2: TeamBasic

    games_played: int
    team1_wins: int
    team1_losses: int
    team1_ties: int
    team1_points: int
    team1_points_pct: float

    goals_for: int
    goals_against: int
    goal_differential: int

    games: List[HeadToHeadGame]
    special_teams_matchup: Dict[str, SpecialTeamsMatchup]

    player_performance: List[Dict[str, Any]]


# ============================================================================
# LEADER MODELS
# ============================================================================

class LeaderEntry(BaseModel):
    """Single leader entry"""
    rank: int
    player: PlayerBasic
    team: TeamBasic
    value: int | float
    games_played: int

    # Context
    percentile: Optional[float] = None
    interpretation: Optional[str] = None


class LeaderBoard(BaseModel):
    """Leader board"""
    category: str
    season_id: str
    division_id: Optional[int] = None
    leaders: List[LeaderEntry]
    minimum_games: Optional[int] = None
    total_qualified_players: int


# ============================================================================
# RANKINGS MODELS
# ============================================================================

class TeamRankingEntry(BaseModel):
    """Team ranking entry"""
    rank: int
    team: TeamBasic
    value: float | int
    percentile: float
    interpretation: str


class TeamRankings(BaseModel):
    """Team rankings by various metrics"""
    season_id: str
    division_id: Optional[int] = None

    by_points_pct: List[TeamRankingEntry]
    by_goal_differential: List[TeamRankingEntry]
    by_goals_per_game: List[TeamRankingEntry]
    by_power_play_pct: List[TeamRankingEntry]
    by_penalty_kill_pct: List[TeamRankingEntry]
    by_sos: List[TeamRankingEntry]


# ============================================================================
# SEARCH & QUERY MODELS
# ============================================================================

class PlayerSearchResult(BaseModel):
    """Player search result with confidence"""
    player: PlayerBasic
    team: TeamBasic
    confidence_score: float
    matches: List[str]  # What matched (number, name, etc.)
    data_quality_notes: Optional[str] = None


class PlayerNumberLookup(BaseModel):
    """Player lookup by number"""
    team: TeamBasic
    number: str
    game_date: Optional[str] = None

    players: List[PlayerSearchResult]
    notes: Optional[str] = None


# ============================================================================
# DATA QUALITY MODELS
# ============================================================================

class DataQualityIssue(BaseModel):
    """Data quality issue"""
    id: int
    entity_type: str
    entity_id: str
    game_id: Optional[str] = None

    issue_type: str
    issue_description: str
    confidence_impact: float

    is_resolved: bool
    resolution_notes: Optional[str] = None
    created_at: datetime


class PlayerDataQualityReport(BaseModel):
    """Player data quality report"""
    player: PlayerBasic
    number_consistency: float
    number_variations: List[str]
    name_variations: List[str]
    games_with_issues: int
    total_games: int
    confidence_scores: List[float]
    issues: List[DataQualityIssue]


class GameDataQualityReport(BaseModel):
    """Game data quality report"""
    game: GameInfo
    overall_confidence: float
    missing_data_fields: List[str]
    suspect_player_numbers: List[Dict[str, Any]]
    issues: List[DataQualityIssue]


# ============================================================================
# PAGINATION & RESPONSE WRAPPERS
# ============================================================================

class PaginationInfo(BaseModel):
    """Pagination information"""
    total: int
    limit: int
    offset: int
    has_more: bool


class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    data: List[Any]
    pagination: PaginationInfo


# ============================================================================
# ERROR MODELS
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: ErrorDetail
    request_id: Optional[str] = None
    timestamp: datetime


# ============================================================================
# WHK HAWKS SPECIFIC MODELS
# ============================================================================

class WHKPlayerBasic(BaseModel):
    """Basic WHK player information"""
    id: int
    player_id: str
    first_name: str
    last_name: str
    jersey_number: Optional[str] = None
    position: Optional[str] = None
    division: Optional[str] = None
    age_group: Optional[str] = None
    photo_url: Optional[str] = None


class WHKPlayer(BaseModel):
    """Full WHK player profile"""
    id: int
    player_id: str
    first_name: str
    last_name: str
    dob: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    jersey_number: Optional[str] = None
    position: Optional[str] = None
    player_type: Optional[str] = None  # Player or Full-Time Goalie
    division: Optional[str] = None
    age_group: Optional[str] = None
    team_id: Optional[int] = None
    registration_status: Optional[str] = None
    registration_date: Optional[str] = None
    order_number: Optional[str] = None
    tryout_color: Optional[str] = None
    tryout_number: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PlayerEvaluation(BaseModel):
    """Player skill evaluation from tryouts"""
    id: int
    player_id: Optional[str] = None
    evaluator_name: Optional[str] = None
    evaluation_date: Optional[str] = None
    tryout_color: Optional[str] = None
    tryout_number: Optional[int] = None
    forward_skating: Optional[int] = None  # 0-5 scale
    backward_skating: Optional[int] = None
    puck_control: Optional[int] = None
    hockey_sense: Optional[int] = None
    shooting: Optional[int] = None
    total_score: Optional[int] = None
    notes: Optional[str] = None


class WHKPlayerWithEvaluations(BaseModel):
    """Player profile with evaluations and game stats"""
    player: WHKPlayer
    evaluations: List[PlayerEvaluation] = []
    game_stats: Optional[PlayerStats] = None
    data_quality_note: Optional[str] = Field(
        default="Player jersey numbers from game data may be inaccurate. "
                "Event data (time, period, penalty type) is reliable."
    )


class WHKTeam(BaseModel):
    """WHK team information"""
    id: int
    team_id: int
    team_name: str
    division: Optional[str] = None
    age_group: Optional[str] = None
    level: Optional[str] = None  # A, B, C, Bronze, Silver
    season: Optional[str] = None
    head_coach_id: Optional[int] = None
    ical_feed_url: Optional[str] = None
    sportsengine_team_id: Optional[str] = None


class WHKTeamWithRoster(BaseModel):
    """Team with full roster"""
    team: WHKTeam
    players: List[WHKPlayerBasic] = []
    coaches: List["Coach"] = []
    record: Optional[TeamRecord] = None
    next_game: Optional[GameInfo] = None


class Coach(BaseModel):
    """Coach information"""
    id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    role: Optional[str] = None  # Head Coach, Assistant Coach, Manager, Trainer
    certifications: Optional[str] = None  # JSON string
    team_ids: Optional[str] = None  # JSON array of team IDs
    is_active: bool = True


class BoardMember(BaseModel):
    """Board member information"""
    id: int
    name: str
    position: str
    phone: Optional[str] = None
    email: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: bool = True


class Venue(BaseModel):
    """Venue/rink information"""
    id: int
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    google_maps_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rink_count: int = 1
    notes: Optional[str] = None


class Announcement(BaseModel):
    """News/announcement"""
    id: int
    title: str
    content: Optional[str] = None
    author: Optional[str] = None
    priority: str = "normal"  # low, normal, high, urgent
    target_audience: str = "all"
    target_team_ids: Optional[str] = None  # JSON array
    publish_date: Optional[datetime] = None
    expire_date: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


class PushSubscription(BaseModel):
    """Push notification subscription"""
    id: int
    expo_push_token: str
    user_email: Optional[str] = None
    player_ids: Optional[str] = None  # JSON array
    team_ids: Optional[str] = None  # JSON array
    notify_game_start: bool = True
    notify_score_update: bool = True
    notify_schedule_change: bool = True
    notify_announcements: bool = True


class PushSubscriptionCreate(BaseModel):
    """Create push subscription request"""
    expo_push_token: str
    user_email: Optional[str] = None
    player_ids: Optional[List[str]] = None
    team_ids: Optional[List[int]] = None
    notify_game_start: bool = True
    notify_score_update: bool = True
    notify_schedule_change: bool = True
    notify_announcements: bool = True


class CalendarEvent(BaseModel):
    """Calendar event (practice, skills session, etc.)"""
    id: int
    event_type: str  # practice, skills, meeting, tryout, tournament, other
    title: str
    description: Optional[str] = None
    team_id: Optional[int] = None
    venue_id: Optional[int] = None
    venue: Optional[Venue] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    is_recurring: bool = False


class ScheduleItem(BaseModel):
    """Unified schedule item (game or event)"""
    item_type: str  # "game" or "event"
    id: str  # game_id or event_id prefixed
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    venue: Optional[Venue] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    opponent: Optional[str] = None
    score: Optional[str] = None  # "3-2" or None if not played
    status: Optional[str] = None  # scheduled, in_progress, final


class DataReliabilityNote(BaseModel):
    """Data reliability information"""
    data_source: str
    field_name: str
    reliability: str  # high, medium, low, unreliable
    notes: Optional[str] = None


class WHKDashboard(BaseModel):
    """Home dashboard data"""
    todays_games: List[ScheduleItem] = []
    upcoming_games: List[ScheduleItem] = []  # Next 7 days
    recent_announcements: List[Announcement] = []
    teams: List[WHKTeam] = []
    data_reliability_notes: List[DataReliabilityNote] = []


# ============================================================================
# LOGO MODELS
# ============================================================================

class LogoInfo(BaseModel):
    """Logo information for a single team"""
    team_name: str
    team_id: Optional[int] = None
    local_logo: Optional[str] = None        # filename in logos/ dir
    gamesheet_url: Optional[str] = None     # imagedelivery.net URL
    source: str = "none"                    # "local", "gamesheet", "both", "none"
    match_confidence: Optional[float] = None


class LogoManifest(BaseModel):
    """Cross-reference manifest of all teams and their logo sources"""
    season_id: int
    season_name: str
    generated_at: str
    total_teams: int
    matched_local: int
    matched_gamesheet: int
    unmatched: int
    teams: List[LogoInfo] = []


class LogoSearchResult(BaseModel):
    """Search result for logo queries"""
    query: str
    results: List[LogoInfo] = []
    total_results: int = 0


# ============================================================================
# CLUB MODELS (Multi-club SSC data)
# ============================================================================

class ClubBasic(BaseModel):
    """Basic club/organization info"""
    id: int
    club_name: str
    club_slug: Optional[str] = None
    website_url: Optional[str] = None
    town: Optional[str] = None
    abbreviation: Optional[str] = None
    conference: Optional[str] = "SSC"
    last_scraped: Optional[str] = None


class ClubTeamBasic(BaseModel):
    """Basic club team info"""
    id: int
    club_id: Optional[int] = None
    team_name: str
    age_group: Optional[str] = None
    division_level: Optional[str] = None
    season: Optional[str] = None
    team_page_url: Optional[str] = None
    roster_url: Optional[str] = None
    schedule_url: Optional[str] = None


class ClubPlayerBasic(BaseModel):
    """Club player from roster scraping"""
    id: int
    club_id: Optional[int] = None
    club_team_id: Optional[int] = None
    first_name: str
    last_name: str
    jersey_number: Optional[str] = None
    position: Optional[str] = None
    usah_number: Optional[str] = None
    player_profile_url: Optional[str] = None
    gamesheet_player_id: Optional[str] = None
    team_name: Optional[str] = None
    team_page_url: Optional[str] = None


class ClubCoachInfo(BaseModel):
    """Club coach info"""
    id: int
    club_id: Optional[int] = None
    club_team_id: Optional[int] = None
    name: str
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    team_name: Optional[str] = None
    team_page_url: Optional[str] = None


class ClubBoardMemberInfo(BaseModel):
    """Club board member info"""
    id: int
    club_id: Optional[int] = None
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True


class ClubGameInfo(BaseModel):
    """Club schedule game"""
    id: int
    club_id: Optional[int] = None
    club_team_id: Optional[int] = None
    game_id: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    opponent: Optional[str] = None
    location: Optional[str] = None
    is_home: Optional[bool] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str = "scheduled"
    game_url: Optional[str] = None


class ClubContactInfo(BaseModel):
    """Contact info found on club website"""
    id: int
    club_id: Optional[int] = None
    contact_type: str
    value: str
    context: Optional[str] = None


class ClubDetail(BaseModel):
    """Full club detail with counts"""
    club: ClubBasic
    team_count: int = 0
    player_count: int = 0
    coach_count: int = 0
    board_member_count: int = 0
    game_count: int = 0
    contact_count: int = 0


class ClubTeamWithRoster(BaseModel):
    """Club team with full roster"""
    team: ClubTeamBasic
    players: List[ClubPlayerBasic] = []
    coaches: List[ClubCoachInfo] = []
