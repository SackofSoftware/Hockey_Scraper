"""
Advanced Hockey Stats REST API Server
FastAPI-based REST server for hockey statistics with LLM-friendly responses

Run with: uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, HTTPException, Query, Path, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional, List, Dict, Any
import sqlite3
from datetime import datetime, date
from contextlib import contextmanager
import os
from pathlib import Path as FilePath
from functools import lru_cache

from api_models import (
    SeasonInfo, DivisionInfo, DivisionsList, DivisionStandings,
    TeamStatsComplete, TeamBasic, TeamRecord, TeamScoring,
    SpecialTeamsStats, DisciplineStats, HomeAwayStats, RecentForm,
    StrengthOfSchedule, StandingsEntry, StatWithContext,
    PlayerProfile, PlayerBasic, PlayerStats, PlayerIdentity,
    PlayerGameLog, GoalDetail, PenaltyDetail, DataQuality,
    GameInfo, GameBoxScore, GameSummary, GoalEvent, PenaltyEvent,
    RosterPlayer, HeadToHead, HeadToHeadGame, SpecialTeamsMatchup,
    LeaderBoard, LeaderEntry, TeamRankings, TeamRankingEntry,
    PlayerSearchResult, PlayerNumberLookup, DataQualityIssue,
    PlayerDataQualityReport, GameDataQualityReport,
    ErrorResponse, ErrorDetail, PaginatedResponse, PaginationInfo,
    RecentFormGame,
    # WHK-specific models
    WHKPlayer, WHKPlayerBasic, WHKPlayerWithEvaluations, PlayerEvaluation,
    WHKTeam, WHKTeamWithRoster, Coach, BoardMember, Venue, Announcement,
    PushSubscription, PushSubscriptionCreate, CalendarEvent, ScheduleItem,
    DataReliabilityNote, WHKDashboard,
    # Logo models
    LogoInfo, LogoManifest, LogoSearchResult,
    # Club models
    ClubBasic, ClubTeamBasic, ClubPlayerBasic, ClubCoachInfo,
    ClubBoardMemberInfo, ClubGameInfo, ClubContactInfo,
    ClubDetail, ClubTeamWithRoster,
)
from logo_service import LogoService

# ============================================================================
# APP CONFIGURATION
# ============================================================================

app = FastAPI(
    title="Advanced Hockey Stats API",
    description="Comprehensive hockey statistics API with LLM-friendly responses",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Default database path - can be overridden via environment variable
DEFAULT_DB_PATH = os.environ.get(
    "HOCKEY_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "hockey_stats.db")
)

# Season name lookup for multi-league support
SEASON_NAMES = {
    "10776": "Bay State Hockey League 2025-26",
    "10477": "Eastern Hockey Federation 2025-26",
}


@contextmanager
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect(DEFAULT_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_db_connection():
    """Dependency for database connection"""
    with get_db() as conn:
        yield conn


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def ordinal_suffix(n: int) -> str:
    """Get ordinal suffix for number (1st, 2nd, 3rd, etc.)"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def calculate_percentile(rank: int, total: int) -> float:
    """Calculate percentile from rank"""
    if total == 0:
        return 0.0
    return ((total - rank + 1) / total) * 100


def interpret_percentile(percentile: float) -> str:
    """Interpret percentile as human-readable string"""
    if percentile >= 90:
        return "Elite - Top 10%"
    elif percentile >= 75:
        return "Above Average - Top 25%"
    elif percentile >= 50:
        return "Average - Top 50%"
    elif percentile >= 25:
        return "Below Average - Bottom 50%"
    else:
        return "Poor - Bottom 25%"


def create_stat_with_context(
    value: float | int,
    rank: Optional[int] = None,
    total: Optional[int] = None,
    league_avg: Optional[float] = None,
    division_avg: Optional[float] = None
) -> StatWithContext:
    """Create StatWithContext object with all contextual information"""
    percentile = calculate_percentile(rank, total) if rank and total else None

    interpretation = None
    if percentile is not None:
        interpretation = interpret_percentile(percentile)

    context = None
    if rank and total:
        context = f"{ordinal_suffix(rank)} out of {total} teams"

    return StatWithContext(
        value=value,
        rank=rank,
        rank_suffix=ordinal_suffix(rank) if rank else None,
        total_teams=total,
        percentile=percentile,
        league_average=league_avg,
        division_average=division_avg,
        interpretation=interpretation,
        context=context
    )


# ============================================================================
# SEASON & DIVISION ENDPOINTS
# ============================================================================

@app.get("/api/v1/seasons/{season_id}", response_model=SeasonInfo)
async def get_season_info(
    season_id: str = Path(..., description="Season ID"),
    db=Depends(get_db_connection)
):
    """
    Get season information including divisions and teams count
    """
    cursor = db.cursor()

    # Get division and team counts
    divisions = cursor.execute(
        "SELECT COUNT(*) as count FROM divisions WHERE season_id = ?",
        (season_id,)
    ).fetchone()

    teams = cursor.execute(
        "SELECT COUNT(*) as count FROM teams WHERE season_id = ?",
        (season_id,)
    ).fetchone()

    games = cursor.execute(
        "SELECT COUNT(*) as count FROM games WHERE season_id = ?",
        (season_id,)
    ).fetchone()

    return SeasonInfo(
        season_id=season_id,
        title=SEASON_NAMES.get(season_id, f"Season {season_id}"),
        sport="hockey",
        association="USAH - Massachusetts District",
        divisions_count=divisions['count'] if divisions else 0,
        teams_count=teams['count'] if teams else 0,
        games_count=games['count'] if games else 0,
        assist_value=1,
        goal_value=1,
        max_goal_differential=10
    )


@app.get("/api/v1/seasons/{season_id}/divisions", response_model=DivisionsList)
async def get_divisions(
    season_id: str = Path(..., description="Season ID"),
    db=Depends(get_db_connection)
):
    """
    Get all divisions in a season
    """
    cursor = db.cursor()

    divisions = cursor.execute("""
        SELECT
            d.division_api_id as division_id,
            d.division_name,
            d.season_id,
            d.teams_count,
            d.games_count
        FROM divisions d
        WHERE d.season_id = ?
        ORDER BY d.division_name
    """, (season_id,)).fetchall()

    return DivisionsList(
        season_id=season_id,
        divisions=[
            DivisionInfo(
                division_id=div['division_id'],
                division_name=div['division_name'],
                season_id=div['season_id'],
                teams_count=div['teams_count'],
                games_count=div['games_count']
            )
            for div in divisions
        ]
    )


@app.get("/api/v1/divisions/{division_id}/standings", response_model=DivisionStandings)
async def get_division_standings(
    division_id: int = Path(..., description="Division ID"),
    db=Depends(get_db_connection)
):
    """
    Get division standings with all calculated stats
    """
    cursor = db.cursor()

    # Get division info
    div_info = cursor.execute("""
        SELECT division_api_id, division_name, season_id, teams_count, games_count
        FROM divisions
        WHERE division_api_id = ?
    """, (division_id,)).fetchone()

    if not div_info:
        raise HTTPException(status_code=404, detail="Division not found")

    # Get teams standings
    teams = cursor.execute("""
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
            t.points
        FROM teams t
        WHERE t.division_api_id = ?
        ORDER BY t.points DESC, t.wins DESC, t.goals_for DESC
    """, (division_id,)).fetchall()

    standings = []
    for idx, team in enumerate(teams, 1):
        goal_diff = team['goals_for'] - team['goals_against']
        points_pct = team['points'] / (team['games_played'] * 2) if team['games_played'] > 0 else 0.0
        record_string = f"{team['wins']}-{team['losses']}-{team['ties']}"

        standings.append(
            StandingsEntry(
                rank=idx,
                team=TeamBasic(
                    team_id=team['team_api_id'],
                    team_name=team['team_name'],
                    division_name=team['division_name']
                ),
                record=TeamRecord(
                    games_played=team['games_played'],
                    wins=team['wins'],
                    losses=team['losses'],
                    ties=team['ties'],
                    otw=0,
                    otl=0,
                    sow=0,
                    sol=0,
                    points=team['points'],
                    points_pct=round(points_pct, 3),
                    row=team['wins'],
                    division_rank=idx,
                    record_string=record_string
                ),
                scoring={
                    "goals_for": team['goals_for'],
                    "goals_against": team['goals_against'],
                    "goal_differential": goal_diff
                }
            )
        )

    return DivisionStandings(
        division=DivisionInfo(
            division_id=div_info['division_api_id'],
            division_name=div_info['division_name'],
            season_id=div_info['season_id'],
            teams_count=div_info['teams_count'],
            games_count=div_info['games_count']
        ),
        standings=standings,
        last_updated=datetime.now()
    )


@app.get("/api/v1/divisions/{division_id}/teams", response_model=List[TeamBasic])
async def get_division_teams(
    division_id: int = Path(..., description="Division ID"),
    db=Depends(get_db_connection)
):
    """
    Get all teams in a division
    """
    cursor = db.cursor()

    teams = cursor.execute("""
        SELECT team_api_id, team_name, division_api_id, division_name
        FROM teams
        WHERE division_api_id = ?
        ORDER BY team_name
    """, (division_id,)).fetchall()

    return [
        TeamBasic(
            team_id=team['team_api_id'],
            team_name=team['team_name'],
            division_id=team['division_api_id'],
            division_name=team['division_name']
        )
        for team in teams
    ]


# ============================================================================
# TEAM ENDPOINTS
# ============================================================================

@app.get("/api/v1/teams/{team_id}", response_model=TeamBasic)
async def get_team_info(
    team_id: int = Path(..., description="Team ID"),
    db=Depends(get_db_connection)
):
    """
    Get basic team information
    """
    cursor = db.cursor()

    team = cursor.execute("""
        SELECT team_api_id, team_name, division_api_id, division_name
        FROM teams
        WHERE team_api_id = ?
    """, (team_id,)).fetchone()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return TeamBasic(
        team_id=team['team_api_id'],
        team_name=team['team_name'],
        division_id=team['division_api_id'],
        division_name=team['division_name']
    )


@app.get("/api/v1/teams/{team_id}/stats", response_model=TeamStatsComplete)
async def get_team_stats(
    team_id: int = Path(..., description="Team ID"),
    db=Depends(get_db_connection)
):
    """
    Get complete team statistics including record, scoring, special teams, etc.
    """
    cursor = db.cursor()

    # Get team info
    team = cursor.execute("""
        SELECT t.*, d.division_name
        FROM teams t
        LEFT JOIN divisions d ON t.division_api_id = d.division_api_id
        WHERE t.team_api_id = ?
    """, (team_id,)).fetchone()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Calculate stats
    goal_diff = team['goals_for'] - team['goals_against']
    points_pct = team['points'] / (team['games_played'] * 2) if team['games_played'] > 0 else 0.0
    gpg = team['goals_for'] / team['games_played'] if team['games_played'] > 0 else 0.0
    gapg = team['goals_against'] / team['games_played'] if team['games_played'] > 0 else 0.0

    # Get division averages for context
    div_avg = cursor.execute("""
        SELECT
            AVG(CAST(goals_for AS FLOAT) / NULLIF(games_played, 0)) as avg_gpg,
            AVG(CAST(goals_against AS FLOAT) / NULLIF(games_played, 0)) as avg_gapg
        FROM teams
        WHERE division_api_id = ?
    """, (team['division_api_id'],)).fetchone()

    # Get division team count for ranking context
    div_teams = cursor.execute("""
        SELECT COUNT(*) as count FROM teams WHERE division_api_id = ?
    """, (team['division_api_id'],)).fetchone()

    total_teams = div_teams['count']

    # Calculate rank
    team_rank = cursor.execute("""
        SELECT COUNT(*) + 1 as rank
        FROM teams
        WHERE division_api_id = ?
        AND (points > ? OR (points = ? AND goals_for > ?))
    """, (team['division_api_id'], team['points'], team['points'], team['goals_for'])).fetchone()

    # Get recent games (last 5)
    recent_games = cursor.execute("""
        SELECT
            g.game_api_id,
            g.game_date,
            g.home_team_api_id,
            g.visitor_team_api_id,
            g.home_team_name,
            g.visitor_team_name,
            g.home_score,
            g.visitor_score
        FROM games g
        WHERE (g.home_team_api_id = ? OR g.visitor_team_api_id = ?)
        AND g.status = 'Final'
        ORDER BY g.game_date DESC
        LIMIT 5
    """, (team_id, team_id)).fetchall()

    recent_form_games = []
    for game in recent_games:
        is_home = game['home_team_api_id'] == team_id
        opponent = game['visitor_team_name'] if is_home else game['home_team_name']
        opponent_id = game['visitor_team_api_id'] if is_home else game['home_team_api_id']
        team_score = game['home_score'] if is_home else game['visitor_score']
        opp_score = game['visitor_score'] if is_home else game['home_score']

        if team_score > opp_score:
            result = "W"
        elif team_score < opp_score:
            result = "L"
        else:
            result = "T"

        recent_form_games.append(
            RecentFormGame(
                date=game['game_date'],
                opponent=opponent,
                opponent_id=opponent_id,
                result=result,
                score=f"{team_score}-{opp_score}",
                is_home=is_home
            )
        )

    # Calculate streak
    current_streak = "N/A"
    streak_count = 0
    if recent_form_games:
        streak_type = recent_form_games[0].result
        for game in recent_form_games:
            if game.result == streak_type:
                streak_count += 1
            else:
                break
        current_streak = f"{streak_type}{streak_count}"

    return TeamStatsComplete(
        team=TeamBasic(
            team_id=team['team_api_id'],
            team_name=team['team_name'],
            division_id=team['division_api_id'],
            division_name=team['division_name']
        ),
        record=TeamRecord(
            games_played=team['games_played'],
            wins=team['wins'],
            losses=team['losses'],
            ties=team['ties'],
            otw=0,
            otl=0,
            sow=0,
            sol=0,
            points=team['points'],
            points_pct=round(points_pct, 3),
            row=team['wins'],
            division_rank=team_rank['rank'],
            record_string=f"{team['wins']}-{team['losses']}-{team['ties']}"
        ),
        scoring=TeamScoring(
            goals_for=create_stat_with_context(team['goals_for'], division_avg=div_avg['avg_gpg'] * team['games_played'] if div_avg['avg_gpg'] else None),
            goals_against=create_stat_with_context(team['goals_against'], division_avg=div_avg['avg_gapg'] * team['games_played'] if div_avg['avg_gapg'] else None),
            goal_differential=create_stat_with_context(goal_diff),
            goals_per_game=create_stat_with_context(round(gpg, 2), division_avg=div_avg['avg_gpg']),
            goals_against_per_game=create_stat_with_context(round(gapg, 2), division_avg=div_avg['avg_gapg'])
        ),
        special_teams=SpecialTeamsStats(
            power_play_goals=0,
            power_play_opportunities=0,
            power_play_pct=create_stat_with_context(0.0),
            penalty_kill_goals_against=0,
            times_shorthanded=0,
            penalty_kill_pct=create_stat_with_context(0.0),
            short_handed_goals=0,
            short_handed_goals_against=0
        ),
        discipline=DisciplineStats(
            penalty_minutes=0,
            pim_per_game=create_stat_with_context(0.0),
            penalties_taken=0,
            major_penalties=0,
            game_misconducts=0
        ),
        home_stats=HomeAwayStats(
            record="0-0-0",
            goals_for=0,
            goals_against=0,
            points=0,
            goal_differential=0
        ),
        away_stats=HomeAwayStats(
            record="0-0-0",
            goals_for=0,
            goals_against=0,
            points=0,
            goal_differential=0
        ),
        recent_form=RecentForm(
            last_10=f"{team['wins']}-{team['losses']}-{team['ties']}",
            current_streak=current_streak,
            streak_count=streak_count,
            last_5_games=recent_form_games
        ),
        data_quality={
            "games_with_complete_data": team['games_played'],
            "overall_confidence": 0.95
        }
    )


@app.get("/api/v1/teams/{team_id}/schedule", response_model=List[GameInfo])
async def get_team_schedule(
    team_id: int = Path(..., description="Team ID"),
    db=Depends(get_db_connection)
):
    """
    Get team's schedule (past and future games)
    """
    cursor = db.cursor()

    games = cursor.execute("""
        SELECT
            g.game_api_id,
            g.season_id,
            g.division_api_id,
            d.division_name,
            '' as game_number,
            'Regular Season' as game_type,
            g.game_date,
            g.game_time,
            g.venue,
            g.status,
            g.home_team_api_id,
            g.home_team_name,
            g.visitor_team_api_id,
            g.visitor_team_name,
            g.home_score,
            g.visitor_score
        FROM games g
        LEFT JOIN divisions d ON g.division_api_id = d.division_api_id
        WHERE g.home_team_api_id = ? OR g.visitor_team_api_id = ?
        ORDER BY g.game_date, g.game_time
    """, (team_id, team_id)).fetchall()

    return [
        GameInfo(
            game_id=str(game['game_api_id']),
            season_id=game['season_id'],
            division_id=game['division_api_id'],
            division_name=game['division_name'] or "",
            game_number=game['game_number'],
            game_type=game['game_type'],
            date=game['game_date'],
            time=game['game_time'] or "",
            location=game['venue'] or "",
            status=game['status'],
            home_team=TeamBasic(
                team_id=game['home_team_api_id'],
                team_name=game['home_team_name']
            ),
            visitor_team=TeamBasic(
                team_id=game['visitor_team_api_id'],
                team_name=game['visitor_team_name']
            ),
            home_score=game['home_score'],
            visitor_score=game['visitor_score']
        )
        for game in games
    ]


@app.get("/api/v1/teams/{team_id}/roster", response_model=List[PlayerBasic])
async def get_team_roster(
    team_id: int = Path(..., description="Team ID"),
    db=Depends(get_db_connection)
):
    """
    Get team's current roster with player stats
    """
    cursor = db.cursor()

    # Get team info
    team = cursor.execute("""
        SELECT team_name FROM teams WHERE team_api_id = ?
    """, (team_id,)).fetchone()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    players = cursor.execute("""
        SELECT
            p.player_api_id,
            p.jersey_number,
            p.player_name,
            p.team_api_id,
            p.goals,
            p.assists,
            p.points,
            p.penalty_minutes,
            p.games_played
        FROM players p
        WHERE p.team_api_id = ?
        ORDER BY p.points DESC, p.goals DESC
    """, (team_id,)).fetchall()

    return [
        PlayerBasic(
            player_id=str(player['player_api_id']),
            player_number=player['jersey_number'],
            player_name=player['player_name'] or "",
            team_id=player['team_api_id'],
            team_name=team['team_name']
        )
        for player in players
    ]


@app.get("/api/v1/teams/{team_id}/leaders", response_model=Dict[str, List[LeaderEntry]])
async def get_team_leaders(
    team_id: int = Path(..., description="Team ID"),
    limit: int = Query(5, ge=1, le=20, description="Number of leaders per category"),
    db=Depends(get_db_connection)
):
    """
    Get team leaders in all statistical categories
    """
    cursor = db.cursor()

    # Get team info
    team = cursor.execute("""
        SELECT team_name, division_name FROM teams WHERE team_api_id = ?
    """, (team_id,)).fetchone()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Points leaders
    points_leaders = cursor.execute("""
        SELECT
            p.player_api_id,
            p.jersey_number,
            p.player_name,
            p.points,
            p.games_played,
            p.goals,
            p.assists
        FROM players p
        WHERE p.team_api_id = ?
        ORDER BY p.points DESC, p.goals DESC
        LIMIT ?
    """, (team_id, limit)).fetchall()

    # Goals leaders
    goals_leaders = cursor.execute("""
        SELECT
            p.player_api_id,
            p.jersey_number,
            p.player_name,
            p.goals,
            p.games_played
        FROM players p
        WHERE p.team_api_id = ?
        ORDER BY p.goals DESC, p.points DESC
        LIMIT ?
    """, (team_id, limit)).fetchall()

    # Assists leaders
    assists_leaders = cursor.execute("""
        SELECT
            p.player_api_id,
            p.jersey_number,
            p.player_name,
            p.assists,
            p.games_played
        FROM players p
        WHERE p.team_api_id = ?
        ORDER BY p.assists DESC, p.points DESC
        LIMIT ?
    """, (team_id, limit)).fetchall()

    # PIM leaders
    pim_leaders = cursor.execute("""
        SELECT
            p.player_api_id,
            p.jersey_number,
            p.player_name,
            p.penalty_minutes,
            p.games_played
        FROM players p
        WHERE p.team_api_id = ?
        ORDER BY p.penalty_minutes DESC
        LIMIT ?
    """, (team_id, limit)).fetchall()

    def create_leader_entry(rank: int, player: sqlite3.Row, value_key: str) -> LeaderEntry:
        return LeaderEntry(
            rank=rank,
            player=PlayerBasic(
                player_id=str(player['player_api_id']),
                player_number=player['jersey_number'],
                player_name=player['player_name'] or "",
                team_id=team_id,
                team_name=team['team_name']
            ),
            team=TeamBasic(
                team_id=team_id,
                team_name=team['team_name'],
                division_name=team['division_name']
            ),
            value=player[value_key],
            games_played=player['games_played']
        )

    return {
        "points": [create_leader_entry(i+1, p, 'points') for i, p in enumerate(points_leaders)],
        "goals": [create_leader_entry(i+1, p, 'goals') for i, p in enumerate(goals_leaders)],
        "assists": [create_leader_entry(i+1, p, 'assists') for i, p in enumerate(assists_leaders)],
        "penalty_minutes": [create_leader_entry(i+1, p, 'penalty_minutes') for i, p in enumerate(pim_leaders)]
    }


# ============================================================================
# PLAYER ENDPOINTS
# ============================================================================

@app.get("/api/v1/players/{player_id}", response_model=PlayerBasic)
async def get_player_info(
    player_id: str = Path(..., description="Player ID"),
    db=Depends(get_db_connection)
):
    """
    Get basic player information
    """
    cursor = db.cursor()

    player = cursor.execute("""
        SELECT
            p.player_api_id,
            p.jersey_number,
            p.player_name,
            p.team_api_id,
            t.team_name
        FROM players p
        LEFT JOIN teams t ON p.team_api_id = t.team_api_id
        WHERE p.player_api_id = ?
    """, (player_id,)).fetchone()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    return PlayerBasic(
        player_id=str(player['player_api_id']),
        player_number=player['jersey_number'],
        player_name=player['player_name'] or "",
        team_id=player['team_api_id'],
        team_name=player['team_name']
    )


@app.get("/api/v1/players/{player_id}/stats", response_model=PlayerStats)
async def get_player_stats(
    player_id: str = Path(..., description="Player ID"),
    db=Depends(get_db_connection)
):
    """
    Get complete player statistics
    """
    cursor = db.cursor()

    player = cursor.execute("""
        SELECT
            p.player_api_id,
            p.team_api_id,
            p.jersey_number,
            p.player_name,
            p.goals,
            p.assists,
            p.points,
            p.penalty_minutes,
            p.games_played
        FROM players p
        WHERE p.player_api_id = ?
    """, (player_id,)).fetchone()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    ppg = player['points'] / player['games_played'] if player['games_played'] > 0 else 0.0
    pimpg = player['penalty_minutes'] / player['games_played'] if player['games_played'] > 0 else 0.0

    # Get team rank
    team_rank = cursor.execute("""
        SELECT COUNT(*) + 1 as rank
        FROM players
        WHERE team_api_id = ?
        AND (points > ? OR (points = ? AND goals > ?))
    """, (player['team_api_id'], player['points'], player['points'], player['goals'])).fetchone()

    return PlayerStats(
        games_played=player['games_played'],
        goals=player['goals'],
        assists=player['assists'],
        points=player['points'],
        points_per_game=round(ppg, 2),
        power_play_goals=0,
        power_play_assists=0,
        power_play_points=0,
        short_handed_goals=0,
        short_handed_assists=0,
        game_winning_goals=0,
        empty_net_goals=0,
        penalties=0,
        penalty_minutes=player['penalty_minutes'],
        pim_per_game=round(pimpg, 2),
        major_penalties=0,
        team_rank_points=team_rank['rank'] if team_rank else None
    )


@app.get("/api/v1/players/search")
async def search_players(
    number: Optional[str] = Query(None, description="Jersey number"),
    team_id: Optional[int] = Query(None, description="Team ID"),
    name: Optional[str] = Query(None, description="Player name (partial match)"),
    db=Depends(get_db_connection)
):
    """
    Search for players by number, team, and/or name
    Returns confidence scores due to potential data accuracy issues
    """
    cursor = db.cursor()

    query = """
        SELECT
            p.player_api_id,
            p.jersey_number,
            p.player_name,
            p.team_api_id,
            t.team_name,
            t.division_name
        FROM players p
        LEFT JOIN teams t ON p.team_api_id = t.team_api_id
        WHERE 1=1
    """
    params = []

    if number:
        query += " AND p.jersey_number = ?"
        params.append(number)

    if team_id:
        query += " AND p.team_api_id = ?"
        params.append(team_id)

    if name:
        query += " AND p.player_name LIKE ?"
        params.append(f"%{name}%")

    query += " ORDER BY p.points DESC LIMIT 50"

    players = cursor.execute(query, params).fetchall()

    results = []
    for player in players:
        matches = []
        if number and player['jersey_number'] == number:
            matches.append("number")
        if name and name.lower() in (player['player_name'] or "").lower():
            matches.append("name")

        confidence = 0.9 if len(matches) >= 2 else 0.7

        results.append(
            PlayerSearchResult(
                player=PlayerBasic(
                    player_id=str(player['player_api_id']),
                    player_number=player['jersey_number'],
                    player_name=player['player_name'] or "",
                    team_id=player['team_api_id'],
                    team_name=player['team_name']
                ),
                team=TeamBasic(
                    team_id=player['team_api_id'],
                    team_name=player['team_name'],
                    division_name=player['division_name']
                ),
                confidence_score=confidence,
                matches=matches,
                data_quality_notes="Player numbers may vary between games due to data entry"
            )
        )

    return results


# ============================================================================
# GAME ENDPOINTS
# ============================================================================

@app.get("/api/v1/games/{game_id}", response_model=GameInfo)
async def get_game_info(
    game_id: str = Path(..., description="Game ID"),
    db=Depends(get_db_connection)
):
    """
    Get complete game information
    """
    cursor = db.cursor()

    game = cursor.execute("""
        SELECT
            g.game_api_id,
            g.season_id,
            g.division_api_id,
            d.division_name,
            g.game_date,
            g.game_time,
            g.venue,
            g.status,
            g.home_team_api_id,
            g.home_team_name,
            g.visitor_team_api_id,
            g.visitor_team_name,
            g.home_score,
            g.visitor_score
        FROM games g
        LEFT JOIN divisions d ON g.division_api_id = d.division_api_id
        WHERE g.game_api_id = ?
    """, (game_id,)).fetchone()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return GameInfo(
        game_id=str(game['game_api_id']),
        season_id=game['season_id'],
        division_id=game['division_api_id'],
        division_name=game['division_name'] or "",
        game_number="",
        game_type="Regular Season",
        date=game['game_date'],
        time=game['game_time'] or "",
        location=game['venue'] or "",
        status=game['status'],
        home_team=TeamBasic(
            team_id=game['home_team_api_id'],
            team_name=game['home_team_name']
        ),
        visitor_team=TeamBasic(
            team_id=game['visitor_team_api_id'],
            team_name=game['visitor_team_name']
        ),
        home_score=game['home_score'],
        visitor_score=game['visitor_score']
    )


@app.get("/api/v1/games/{game_id}/summary", response_model=GameSummary)
async def get_game_summary(
    game_id: str = Path(..., description="Game ID"),
    db=Depends(get_db_connection)
):
    """
    Get game summary statistics
    """
    # Get game info first
    game_info = await get_game_info(game_id, db)

    return GameSummary(
        game=game_info,
        total_goals=(game_info.home_score or 0) + (game_info.visitor_score or 0),
        total_penalties=0,
        total_pim=0,
        home_pp_goals=0,
        home_pp_opportunities=0,
        visitor_pp_goals=0,
        visitor_pp_opportunities=0
    )


# ============================================================================
# LEAGUE-WIDE ENDPOINTS
# ============================================================================

@app.get("/api/v1/seasons/{season_id}/leaders/points", response_model=LeaderBoard)
async def get_points_leaders(
    season_id: str = Path(..., description="Season ID"),
    division_id: Optional[int] = Query(None, description="Filter by division"),
    limit: int = Query(20, ge=1, le=100, description="Number of leaders"),
    min_games: int = Query(0, ge=0, description="Minimum games played"),
    db=Depends(get_db_connection)
):
    """
    Get league or division scoring leaders
    """
    cursor = db.cursor()

    query = """
        SELECT
            p.player_api_id,
            p.jersey_number,
            p.player_name,
            p.team_api_id,
            p.points,
            p.goals,
            p.assists,
            p.games_played,
            t.team_name,
            t.division_name
        FROM players p
        LEFT JOIN teams t ON p.team_api_id = t.team_api_id
        WHERE t.season_id = ?
        AND p.games_played >= ?
    """
    params = [season_id, min_games]

    if division_id:
        query += " AND t.division_api_id = ?"
        params.append(division_id)

    query += " ORDER BY p.points DESC, p.goals DESC LIMIT ?"
    params.append(limit)

    leaders = cursor.execute(query, params).fetchall()

    # Get total qualified players
    count_query = """
        SELECT COUNT(*) as count
        FROM players p
        LEFT JOIN teams t ON p.team_api_id = t.team_api_id
        WHERE t.season_id = ?
        AND p.games_played >= ?
    """
    count_params = [season_id, min_games]

    if division_id:
        count_query += " AND t.division_api_id = ?"
        count_params.append(division_id)

    total = cursor.execute(count_query, count_params).fetchone()

    return LeaderBoard(
        category="points",
        season_id=season_id,
        division_id=division_id,
        leaders=[
            LeaderEntry(
                rank=i+1,
                player=PlayerBasic(
                    player_id=str(leader['player_api_id']),
                    player_number=leader['jersey_number'],
                    player_name=leader['player_name'] or "",
                    team_id=leader['team_api_id'],
                    team_name=leader['team_name']
                ),
                team=TeamBasic(
                    team_id=leader['team_api_id'],
                    team_name=leader['team_name'],
                    division_name=leader['division_name']
                ),
                value=leader['points'],
                games_played=leader['games_played'],
                percentile=calculate_percentile(i+1, total['count']),
                interpretation=interpret_percentile(calculate_percentile(i+1, total['count']))
            )
            for i, leader in enumerate(leaders)
        ],
        minimum_games=min_games,
        total_qualified_players=total['count']
    )


@app.get("/api/v1/seasons/{season_id}/leaders/goals", response_model=LeaderBoard)
async def get_goals_leaders(
    season_id: str = Path(..., description="Season ID"),
    division_id: Optional[int] = Query(None, description="Filter by division"),
    limit: int = Query(20, ge=1, le=100, description="Number of leaders"),
    min_games: int = Query(0, ge=0, description="Minimum games played"),
    db=Depends(get_db_connection)
):
    """
    Get league or division goal scoring leaders
    """
    cursor = db.cursor()

    query = """
        SELECT
            p.player_api_id,
            p.jersey_number,
            p.player_name,
            p.team_api_id,
            p.goals,
            p.games_played,
            t.team_name,
            t.division_name
        FROM players p
        LEFT JOIN teams t ON p.team_api_id = t.team_api_id
        WHERE t.season_id = ?
        AND p.games_played >= ?
    """
    params = [season_id, min_games]

    if division_id:
        query += " AND t.division_api_id = ?"
        params.append(division_id)

    query += " ORDER BY p.goals DESC, p.points DESC LIMIT ?"
    params.append(limit)

    leaders = cursor.execute(query, params).fetchall()

    # Get total
    count_query = """
        SELECT COUNT(*) as count
        FROM players p
        LEFT JOIN teams t ON p.team_api_id = t.team_api_id
        WHERE t.season_id = ?
        AND p.games_played >= ?
    """
    count_params = [season_id, min_games]

    if division_id:
        count_query += " AND t.division_api_id = ?"
        count_params.append(division_id)

    total = cursor.execute(count_query, count_params).fetchone()

    return LeaderBoard(
        category="goals",
        season_id=season_id,
        division_id=division_id,
        leaders=[
            LeaderEntry(
                rank=i+1,
                player=PlayerBasic(
                    player_id=str(leader['player_api_id']),
                    player_number=leader['jersey_number'],
                    player_name=leader['player_name'] or "",
                    team_id=leader['team_api_id'],
                    team_name=leader['team_name']
                ),
                team=TeamBasic(
                    team_id=leader['team_api_id'],
                    team_name=leader['team_name'],
                    division_name=leader['division_name']
                ),
                value=leader['goals'],
                games_played=leader['games_played'],
                percentile=calculate_percentile(i+1, total['count']),
                interpretation=interpret_percentile(calculate_percentile(i+1, total['count']))
            )
            for i, leader in enumerate(leaders)
        ],
        minimum_games=min_games,
        total_qualified_players=total['count']
    )


@app.get("/api/v1/seasons/{season_id}/leaders/assists", response_model=LeaderBoard)
async def get_assists_leaders(
    season_id: str = Path(..., description="Season ID"),
    division_id: Optional[int] = Query(None, description="Filter by division"),
    limit: int = Query(20, ge=1, le=100, description="Number of leaders"),
    min_games: int = Query(0, ge=0, description="Minimum games played"),
    db=Depends(get_db_connection)
):
    """
    Get league or division assist leaders
    """
    cursor = db.cursor()

    query = """
        SELECT
            p.player_api_id,
            p.jersey_number,
            p.player_name,
            p.team_api_id,
            p.assists,
            p.games_played,
            t.team_name,
            t.division_name
        FROM players p
        LEFT JOIN teams t ON p.team_api_id = t.team_api_id
        WHERE t.season_id = ?
        AND p.games_played >= ?
    """
    params = [season_id, min_games]

    if division_id:
        query += " AND t.division_api_id = ?"
        params.append(division_id)

    query += " ORDER BY p.assists DESC, p.points DESC LIMIT ?"
    params.append(limit)

    leaders = cursor.execute(query, params).fetchall()

    count_query = """
        SELECT COUNT(*) as count
        FROM players p
        LEFT JOIN teams t ON p.team_api_id = t.team_api_id
        WHERE t.season_id = ?
        AND p.games_played >= ?
    """
    count_params = [season_id, min_games]

    if division_id:
        count_query += " AND t.division_api_id = ?"
        count_params.append(division_id)

    total = cursor.execute(count_query, count_params).fetchone()

    return LeaderBoard(
        category="assists",
        season_id=season_id,
        division_id=division_id,
        leaders=[
            LeaderEntry(
                rank=i+1,
                player=PlayerBasic(
                    player_id=str(leader['player_api_id']),
                    player_number=leader['jersey_number'],
                    player_name=leader['player_name'] or "",
                    team_id=leader['team_api_id'],
                    team_name=leader['team_name']
                ),
                team=TeamBasic(
                    team_id=leader['team_api_id'],
                    team_name=leader['team_name'],
                    division_name=leader['division_name']
                ),
                value=leader['assists'],
                games_played=leader['games_played'],
                percentile=calculate_percentile(i+1, total['count']),
                interpretation=interpret_percentile(calculate_percentile(i+1, total['count']))
            )
            for i, leader in enumerate(leaders)
        ],
        minimum_games=min_games,
        total_qualified_players=total['count']
    )


# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API root - health check and info"""
    return {
        "service": "Advanced Hockey Stats API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc",
        "base_path": "/api/v1"
    }


@app.get("/health")
async def health_check(db=Depends(get_db_connection)):
    """Health check endpoint"""
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )


# ============================================================================
# WHK HAWKS API ENDPOINTS
# ============================================================================

# --- Dashboard ---

@app.get("/api/v1/whk/dashboard", response_model=WHKDashboard, tags=["WHK"])
async def get_whk_dashboard(db=Depends(get_db_connection)):
    """
    Get WHK Hawks dashboard data including today's games, upcoming schedule,
    announcements, and teams.
    """
    cursor = db.cursor()

    # Get teams
    cursor.execute("SELECT * FROM whk_teams ORDER BY division, level")
    teams = [dict(row) for row in cursor.fetchall()]

    # Get active announcements
    cursor.execute("""
        SELECT * FROM announcements
        WHERE is_active = 1
        AND (publish_date IS NULL OR publish_date <= datetime('now'))
        AND (expire_date IS NULL OR expire_date >= datetime('now'))
        ORDER BY priority DESC, created_at DESC
        LIMIT 5
    """)
    announcements = [dict(row) for row in cursor.fetchall()]

    # Get data reliability notes
    cursor.execute("SELECT * FROM data_reliability_notes")
    reliability_notes = [dict(row) for row in cursor.fetchall()]

    return WHKDashboard(
        todays_games=[],  # TODO: Integrate with games table
        upcoming_games=[],
        recent_announcements=[Announcement(**a) for a in announcements],
        teams=[WHKTeam(**t) for t in teams],
        data_reliability_notes=[DataReliabilityNote(**r) for r in reliability_notes]
    )


# --- Players ---

@app.get("/api/v1/whk/players", tags=["WHK"])
async def list_whk_players(
    division: Optional[str] = Query(None, description="Filter by division"),
    age_group: Optional[str] = Query(None, description="Filter by age group"),
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db_connection)
):
    """List all WHK players with optional filters"""
    cursor = db.cursor()

    query = "SELECT * FROM whk_players WHERE 1=1"
    params = []

    if division:
        query += " AND division = ?"
        params.append(division)
    if age_group:
        query += " AND age_group = ?"
        params.append(age_group)
    if team_id:
        query += " AND team_id = ?"
        params.append(team_id)

    # Get total count
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    # Get paginated results
    query += " ORDER BY last_name, first_name LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    players = [WHKPlayerBasic(**dict(row)) for row in cursor.fetchall()]

    return {
        "players": players,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(players) < total
        }
    }


@app.get("/api/v1/whk/players/{player_id}", response_model=WHKPlayerWithEvaluations, tags=["WHK"])
async def get_whk_player(
    player_id: str = Path(..., description="Player ID"),
    db=Depends(get_db_connection)
):
    """Get WHK player profile with evaluations"""
    cursor = db.cursor()

    # Get player
    cursor.execute("SELECT * FROM whk_players WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Player not found")

    player = WHKPlayer(**dict(row))

    # Get evaluations
    cursor.execute("""
        SELECT * FROM player_evaluations
        WHERE player_id = ?
        ORDER BY created_at DESC
    """, (player_id,))
    evaluations = [PlayerEvaluation(**dict(r)) for r in cursor.fetchall()]

    return WHKPlayerWithEvaluations(
        player=player,
        evaluations=evaluations,
        game_stats=None  # TODO: Link to player_stats table
    )


@app.get("/api/v1/whk/players/{player_id}/evaluations", tags=["WHK"])
async def get_player_evaluations(
    player_id: str = Path(..., description="Player ID"),
    db=Depends(get_db_connection)
):
    """Get all evaluations for a player"""
    cursor = db.cursor()

    cursor.execute("""
        SELECT * FROM player_evaluations
        WHERE player_id = ?
        ORDER BY created_at DESC
    """, (player_id,))

    evaluations = [PlayerEvaluation(**dict(r)) for r in cursor.fetchall()]

    return {"evaluations": evaluations, "count": len(evaluations)}


# --- Teams ---

@app.get("/api/v1/whk/teams", tags=["WHK"])
async def list_whk_teams(
    division: Optional[str] = Query(None, description="Filter by division"),
    season: Optional[str] = Query(None, description="Filter by season"),
    db=Depends(get_db_connection)
):
    """List all WHK teams"""
    cursor = db.cursor()

    query = "SELECT * FROM whk_teams WHERE 1=1"
    params = []

    if division:
        query += " AND division = ?"
        params.append(division)
    if season:
        query += " AND season = ?"
        params.append(season)

    query += " ORDER BY division, level"

    cursor.execute(query, params)
    teams = [WHKTeam(**dict(row)) for row in cursor.fetchall()]

    return {"teams": teams, "count": len(teams)}


@app.get("/api/v1/whk/teams/{team_id}", response_model=WHKTeamWithRoster, tags=["WHK"])
async def get_whk_team(
    team_id: int = Path(..., description="Team ID"),
    db=Depends(get_db_connection)
):
    """Get WHK team with roster"""
    cursor = db.cursor()

    # Get team
    cursor.execute("SELECT * FROM whk_teams WHERE team_id = ?", (team_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Team not found")

    team = WHKTeam(**dict(row))

    # Get players on this team
    cursor.execute("""
        SELECT * FROM whk_players
        WHERE team_id = ?
        ORDER BY last_name, first_name
    """, (team_id,))
    players = [WHKPlayerBasic(**dict(r)) for r in cursor.fetchall()]

    # Get coaches for this team
    cursor.execute("""
        SELECT * FROM coaches
        WHERE team_ids LIKE ?
    """, (f'%{team_id}%',))
    coaches = [Coach(**dict(r)) for r in cursor.fetchall()]

    return WHKTeamWithRoster(
        team=team,
        players=players,
        coaches=coaches,
        record=None,  # TODO: Link to team_stats
        next_game=None  # TODO: Link to games table
    )


@app.get("/api/v1/whk/teams/{team_id}/roster", tags=["WHK"])
async def get_team_roster(
    team_id: int = Path(..., description="Team ID"),
    db=Depends(get_db_connection)
):
    """Get team roster with player details"""
    cursor = db.cursor()

    cursor.execute("""
        SELECT * FROM whk_players
        WHERE team_id = ?
        ORDER BY jersey_number, last_name
    """, (team_id,))

    players = [WHKPlayer(**dict(r)) for r in cursor.fetchall()]

    return {
        "team_id": team_id,
        "players": players,
        "count": len(players),
        "data_note": "Player jersey numbers from game statistics may be inaccurate."
    }


@app.get("/api/v1/whk/teams/{team_id}/schedule", tags=["WHK"])
async def get_team_schedule(
    team_id: int = Path(..., description="Team ID"),
    include_past: bool = Query(False, description="Include past games"),
    db=Depends(get_db_connection)
):
    """Get team schedule (games and practices)"""
    cursor = db.cursor()

    # Get calendar events for this team
    if include_past:
        cursor.execute("""
            SELECT * FROM calendar_events
            WHERE team_id = ?
            ORDER BY start_time
        """, (team_id,))
    else:
        cursor.execute("""
            SELECT * FROM calendar_events
            WHERE team_id = ? AND start_time >= datetime('now')
            ORDER BY start_time
        """, (team_id,))

    events = [CalendarEvent(**dict(r)) for r in cursor.fetchall()]

    # TODO: Also query games table for this team's games

    return {
        "team_id": team_id,
        "events": events,
        "count": len(events)
    }


# --- Board & Organization ---

@app.get("/api/v1/whk/board", tags=["WHK"])
async def get_board_members(db=Depends(get_db_connection)):
    """Get all board members"""
    cursor = db.cursor()

    cursor.execute("""
        SELECT * FROM board_members
        WHERE is_active = 1
        ORDER BY
            CASE
                WHEN position LIKE '%President%' THEN 1
                WHEN position LIKE '%Vice President%' THEN 2
                WHEN position LIKE '%Secretary%' THEN 3
                WHEN position LIKE '%Treasurer%' THEN 4
                ELSE 5
            END,
            name
    """)

    members = [BoardMember(**dict(r)) for r in cursor.fetchall()]

    return {"board_members": members, "count": len(members)}


@app.get("/api/v1/whk/venues", tags=["WHK"])
async def get_venues(db=Depends(get_db_connection)):
    """Get all venues/rinks"""
    cursor = db.cursor()

    cursor.execute("SELECT * FROM venues ORDER BY name")
    venues = [Venue(**dict(r)) for r in cursor.fetchall()]

    return {"venues": venues, "count": len(venues)}


@app.get("/api/v1/whk/announcements", tags=["WHK"])
async def get_announcements(
    limit: int = Query(10, ge=1, le=50),
    include_expired: bool = Query(False),
    db=Depends(get_db_connection)
):
    """Get active announcements"""
    cursor = db.cursor()

    if include_expired:
        cursor.execute("""
            SELECT * FROM announcements
            ORDER BY priority DESC, created_at DESC
            LIMIT ?
        """, (limit,))
    else:
        cursor.execute("""
            SELECT * FROM announcements
            WHERE is_active = 1
            AND (publish_date IS NULL OR publish_date <= datetime('now'))
            AND (expire_date IS NULL OR expire_date >= datetime('now'))
            ORDER BY priority DESC, created_at DESC
            LIMIT ?
        """, (limit,))

    announcements = [Announcement(**dict(r)) for r in cursor.fetchall()]

    return {"announcements": announcements, "count": len(announcements)}


# --- Schedule ---

@app.get("/api/v1/whk/schedule", tags=["WHK"])
async def get_whk_schedule(
    team_id: Optional[int] = Query(None, description="Filter by team"),
    days: int = Query(14, ge=1, le=90, description="Days ahead to include"),
    db=Depends(get_db_connection)
):
    """Get unified schedule (games and events)"""
    cursor = db.cursor()

    # Get calendar events
    if team_id:
        cursor.execute("""
            SELECT * FROM calendar_events
            WHERE team_id = ?
            AND start_time >= datetime('now')
            AND start_time <= datetime('now', '+' || ? || ' days')
            ORDER BY start_time
        """, (team_id, days))
    else:
        cursor.execute("""
            SELECT * FROM calendar_events
            WHERE start_time >= datetime('now')
            AND start_time <= datetime('now', '+' || ? || ' days')
            ORDER BY start_time
        """, (days,))

    events = [dict(r) for r in cursor.fetchall()]

    schedule_items = []
    for e in events:
        schedule_items.append(ScheduleItem(
            item_type="event",
            id=f"event_{e['id']}",
            title=e['title'],
            start_time=datetime.fromisoformat(e['start_time']) if e['start_time'] else datetime.now(),
            end_time=datetime.fromisoformat(e['end_time']) if e.get('end_time') else None,
            team_id=e.get('team_id'),
            status="scheduled"
        ))

    # TODO: Also include games from the games table

    return {"schedule": schedule_items, "count": len(schedule_items)}


@app.get("/api/v1/whk/schedule/today", tags=["WHK"])
async def get_todays_schedule(db=Depends(get_db_connection)):
    """Get today's games and events"""
    cursor = db.cursor()

    cursor.execute("""
        SELECT * FROM calendar_events
        WHERE date(start_time) = date('now')
        ORDER BY start_time
    """)

    events = [dict(r) for r in cursor.fetchall()]

    schedule_items = []
    for e in events:
        schedule_items.append(ScheduleItem(
            item_type="event",
            id=f"event_{e['id']}",
            title=e['title'],
            start_time=datetime.fromisoformat(e['start_time']) if e['start_time'] else datetime.now(),
            team_id=e.get('team_id'),
            status="scheduled"
        ))

    return {"schedule": schedule_items, "count": len(schedule_items), "date": date.today().isoformat()}


# --- Push Notifications ---

@app.post("/api/v1/whk/push/register", tags=["WHK"])
async def register_push_token(
    subscription: PushSubscriptionCreate,
    db=Depends(get_db_connection)
):
    """Register a device for push notifications"""
    cursor = db.cursor()

    import json

    cursor.execute("""
        INSERT OR REPLACE INTO push_subscriptions
        (expo_push_token, user_email, player_ids, team_ids,
         notify_game_start, notify_score_update, notify_schedule_change,
         notify_announcements, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        subscription.expo_push_token,
        subscription.user_email,
        json.dumps(subscription.player_ids) if subscription.player_ids else None,
        json.dumps(subscription.team_ids) if subscription.team_ids else None,
        subscription.notify_game_start,
        subscription.notify_score_update,
        subscription.notify_schedule_change,
        subscription.notify_announcements
    ))

    db.commit()

    return {"status": "registered", "token": subscription.expo_push_token}


@app.put("/api/v1/whk/push/preferences", tags=["WHK"])
async def update_push_preferences(
    token: str,
    notify_game_start: Optional[bool] = None,
    notify_score_update: Optional[bool] = None,
    notify_schedule_change: Optional[bool] = None,
    notify_announcements: Optional[bool] = None,
    db=Depends(get_db_connection)
):
    """Update push notification preferences"""
    cursor = db.cursor()

    updates = []
    params = []

    if notify_game_start is not None:
        updates.append("notify_game_start = ?")
        params.append(notify_game_start)
    if notify_score_update is not None:
        updates.append("notify_score_update = ?")
        params.append(notify_score_update)
    if notify_schedule_change is not None:
        updates.append("notify_schedule_change = ?")
        params.append(notify_schedule_change)
    if notify_announcements is not None:
        updates.append("notify_announcements = ?")
        params.append(notify_announcements)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(token)

        cursor.execute(f"""
            UPDATE push_subscriptions
            SET {', '.join(updates)}
            WHERE expo_push_token = ?
        """, params)

        db.commit()

    return {"status": "updated", "token": token}


# --- Data Sync Status ---

@app.get("/api/v1/whk/sync/status", tags=["WHK"])
async def get_sync_status(db=Depends(get_db_connection)):
    """Get data synchronization status"""
    cursor = db.cursor()

    stats = {}
    tables = ['whk_players', 'player_evaluations', 'whk_teams',
              'board_members', 'venues', 'announcements', 'calendar_events']

    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        except:
            stats[table] = 0

    # Get data reliability notes
    cursor.execute("SELECT * FROM data_reliability_notes")
    reliability = [dict(r) for r in cursor.fetchall()]

    return {
        "status": "ok",
        "table_counts": stats,
        "data_reliability": reliability,
        "timestamp": datetime.now().isoformat()
    }


# --- Evaluations (standalone) ---

@app.get("/api/v1/whk/evaluations", tags=["WHK"])
async def list_evaluations(
    tryout_color: Optional[str] = Query(None, description="Filter by tryout color"),
    min_score: Optional[int] = Query(None, description="Minimum total score"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db_connection)
):
    """List all evaluations with optional filters"""
    cursor = db.cursor()

    query = "SELECT * FROM player_evaluations WHERE 1=1"
    params = []

    if tryout_color:
        query += " AND tryout_color = ?"
        params.append(tryout_color)
    if min_score:
        query += " AND total_score >= ?"
        params.append(min_score)

    # Get total
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += " ORDER BY total_score DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    evals = [PlayerEvaluation(**dict(r)) for r in cursor.fetchall()]

    return {
        "evaluations": evals,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(evals) < total
        }
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found",
                "details": {"path": str(request.url)}
            },
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# LOGO API ENDPOINTS
# ============================================================================

# Initialize logo service (lazy-loaded with GameSheet data)
_logo_service: Optional[LogoService] = None

def _get_logo_service() -> LogoService:
    global _logo_service
    if _logo_service is None:
        logos_dir = FilePath(__file__).parent / "logos"
        _logo_service = LogoService(logos_dir)
        _logo_service.load_gamesheet_teams()
    return _logo_service


@app.get("/api/v1/logos/manifest", response_model=LogoManifest, tags=["Logos"])
async def get_logo_manifest(season_id: int = Query(default=10776, description="GameSheet season ID")):
    """Get cross-reference manifest of all teams and their logo sources."""
    svc = _get_logo_service()
    manifest = svc.build_manifest(season_id)
    return LogoManifest(
        season_id=manifest.season_id,
        season_name=manifest.season_name,
        generated_at=manifest.generated_at,
        total_teams=manifest.total_teams,
        matched_local=manifest.matched_local,
        matched_gamesheet=manifest.matched_gamesheet,
        unmatched=manifest.unmatched,
        teams=[
            LogoInfo(
                team_name=t.team_name,
                team_id=t.team_id,
                local_logo=t.local_file,
                gamesheet_url=t.gamesheet_url,
                source=t.source,
                match_confidence=t.match_confidence,
            )
            for t in manifest.teams
        ],
    )


@app.get("/api/v1/logos/team/{team_name}", response_model=LogoInfo, tags=["Logos"])
async def get_team_logo(team_name: str):
    """Look up logo info for a specific team (fuzzy matched)."""
    svc = _get_logo_service()
    result = svc.match(team_name)
    return LogoInfo(
        team_name=result.team_name,
        team_id=result.team_id,
        local_logo=result.local_file,
        gamesheet_url=result.gamesheet_url,
        source=result.source,
        match_confidence=result.match_confidence,
    )


@app.get("/api/v1/logos/file/{filename}", tags=["Logos"])
async def serve_logo_file(filename: str):
    """Serve a logo file directly from the logos/ directory."""
    svc = _get_logo_service()
    path = svc.logos_dir / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Logo file '{filename}' not found")
    # Prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    content_type = {
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(str(path), media_type=content_type)


@app.get("/api/v1/logos/gamesheet/{team_id}", tags=["Logos"])
async def get_gamesheet_logo(team_id: int, size: int = Query(default=256, description="Image size (128, 256, or 'public' for full)")):
    """Get the GameSheet CDN logo URL for a team. Returns a redirect or URL info."""
    svc = _get_logo_service()
    url = svc._gamesheet_cache.get(team_id)
    if not url:
        raise HTTPException(status_code=404, detail=f"No GameSheet logo found for team ID {team_id}")
    sized_url = f"{url}/{size}" if size in (128, 256) else f"{url}/public"
    return {"team_id": team_id, "url": sized_url, "size": size}


@app.get("/api/v1/logos/search", response_model=LogoSearchResult, tags=["Logos"])
async def search_logos(q: str = Query(..., description="Search query"), limit: int = Query(default=10, le=50)):
    """Fuzzy search across all known team names for logos."""
    svc = _get_logo_service()
    results = svc.search(q, limit=limit)
    return LogoSearchResult(
        query=q,
        results=[
            LogoInfo(
                team_name=r.team_name,
                team_id=r.team_id,
                local_logo=r.local_file,
                gamesheet_url=r.gamesheet_url,
                source=r.source,
                match_confidence=r.match_confidence,
            )
            for r in results
        ],
        total_results=len(results),
    )


@app.get("/api/v1/logos/list", tags=["Logos"])
async def list_local_logos():
    """List all available local logo files."""
    svc = _get_logo_service()
    files = svc.list_local_logos()
    return {"total": len(files), "files": files}


@app.post("/api/v1/logos/refresh", tags=["Logos"])
async def refresh_logo_cache(db=Depends(get_db_connection)):
    """
    Refresh the logo database cache from all sources:
    - Local SVG files in logos/ directory
    - GameSheet CDN URLs from teams table
    - Manual alias mappings

    This consolidates all logo data into the logos and logo_aliases tables.
    """
    svc = _get_logo_service()
    stats = svc.populate_logo_tables(DATABASE_PATH)
    logo_stats = svc.get_logo_stats(DATABASE_PATH)
    return {
        "status": "refreshed",
        "import_stats": stats,
        "coverage": logo_stats
    }


@app.get("/api/v1/logos/stats", tags=["Logos"])
async def get_logo_stats():
    """Get statistics about logo coverage from database."""
    svc = _get_logo_service()
    stats = svc.get_logo_stats(DATABASE_PATH)
    return stats


@app.get("/api/v1/logos/lookup", response_model=LogoInfo, tags=["Logos"])
async def lookup_logo_from_db(
    team_name: str = Query(..., description="Team name to look up"),
    team_id: int = Query(default=None, description="Optional GameSheet team ID for exact match")
):
    """
    Look up logo from database cache (faster than API calls).
    Uses exact match first, then canonical name match, then falls back to fuzzy matching.
    """
    svc = _get_logo_service()
    result = svc.match_from_db(team_name, team_id, DATABASE_PATH)
    return LogoInfo(
        team_name=result.team_name,
        team_id=result.team_id,
        local_logo=result.local_file,
        gamesheet_url=result.gamesheet_url,
        source=result.source,
        match_confidence=result.match_confidence
    )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

# ============================================================================
# CLUB ENDPOINTS (Multi-club SSC data)
# ============================================================================

@app.get("/api/v1/clubs", tags=["Clubs"])
async def list_clubs(db=Depends(get_db_connection)):
    """List all SSC member clubs."""
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM clubs ORDER BY club_name")
        clubs = [ClubBasic(**dict(r)) for r in cursor.fetchall()]
        return {"clubs": clubs, "count": len(clubs)}
    except Exception:
        return {"clubs": [], "count": 0, "note": "Club tables may not be populated yet"}


@app.get("/api/v1/clubs/search/{query}", tags=["Clubs"])
async def search_clubs(query: str, db=Depends(get_db_connection)):
    """Search for clubs by name, abbreviation, or town."""
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT * FROM clubs
            WHERE club_name LIKE ? OR abbreviation LIKE ? OR town LIKE ?
            ORDER BY club_name
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        clubs = [ClubBasic(**dict(r)) for r in cursor.fetchall()]
        return {"query": query, "clubs": clubs, "count": len(clubs)}
    except Exception:
        return {"query": query, "clubs": [], "count": 0}


@app.get("/api/v1/clubs/player-search", tags=["Clubs"])
async def search_club_players(
    name: str = Query(..., description="Player name to search"),
    club: Optional[str] = Query(None, description="Club name or abbreviation to filter"),
    db=Depends(get_db_connection)
):
    """Search for players across all clubs by name."""
    cursor = db.cursor()
    try:
        query = """
            SELECT p.*, c.club_name, c.abbreviation as club_abbreviation, ct.team_name
            FROM club_players p
            JOIN clubs c ON p.club_id = c.id
            LEFT JOIN club_teams ct ON p.club_team_id = ct.id
            WHERE (p.first_name || ' ' || p.last_name LIKE ?)
        """
        params: list = [f"%{name}%"]

        if club:
            query += " AND (c.club_name LIKE ? OR c.abbreviation LIKE ?)"
            params.extend([f"%{club}%", f"%{club}%"])

        query += " ORDER BY p.last_name, p.first_name"
        cursor.execute(query, params)

        results = []
        for r in cursor.fetchall():
            d = dict(r)
            results.append({
                "id": d["id"],
                "first_name": d["first_name"],
                "last_name": d["last_name"],
                "jersey_number": d.get("jersey_number"),
                "position": d.get("position"),
                "club_name": d.get("club_name"),
                "club_abbreviation": d.get("club_abbreviation"),
                "team_name": d.get("team_name"),
            })

        return {"query": name, "results": results, "count": len(results)}
    except Exception as e:
        return {"query": name, "results": [], "count": 0, "error": str(e)}


@app.get("/api/v1/clubs/{club_id}", response_model=ClubDetail, tags=["Clubs"])
async def get_club_detail(club_id: int, db=Depends(get_db_connection)):
    """Get detailed info for a single club including counts."""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM clubs WHERE id = ?", (club_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Club {club_id} not found")

    club = ClubBasic(**dict(row))

    counts = {}
    for table, col in [
        ('club_teams', 'team'), ('club_players', 'player'),
        ('club_coaches', 'coach'), ('club_board_members', 'board_member'),
        ('club_games', 'game'), ('club_contacts', 'contact'),
    ]:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE club_id = ?", (club_id,))
        counts[f"{col}_count"] = cursor.fetchone()[0]

    return ClubDetail(club=club, **counts)


@app.get("/api/v1/clubs/{club_id}/teams", tags=["Clubs"])
async def get_club_teams(club_id: int, db=Depends(get_db_connection)):
    """Get all teams for a club."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM club_teams
        WHERE club_id = ? AND is_active = 1
        ORDER BY age_group, division_level, team_name
    """, (club_id,))
    teams = [ClubTeamBasic(**dict(r)) for r in cursor.fetchall()]
    return {"teams": teams, "count": len(teams)}


@app.get("/api/v1/clubs/{club_id}/teams/{team_id}", response_model=ClubTeamWithRoster, tags=["Clubs"])
async def get_club_team_with_roster(club_id: int, team_id: int, db=Depends(get_db_connection)):
    """Get a specific club team with its full roster and coaches."""
    cursor = db.cursor()

    cursor.execute("SELECT * FROM club_teams WHERE id = ? AND club_id = ?", (team_id, club_id))
    team_row = cursor.fetchone()
    if not team_row:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found in club {club_id}")

    team = ClubTeamBasic(**dict(team_row))

    cursor.execute("""
        SELECT * FROM club_players
        WHERE club_team_id = ?
        ORDER BY CAST(jersey_number AS INTEGER), last_name, first_name
    """, (team_id,))
    players = [ClubPlayerBasic(**dict(r)) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM club_coaches WHERE club_team_id = ?", (team_id,))
    coaches = [ClubCoachInfo(**dict(r)) for r in cursor.fetchall()]

    return ClubTeamWithRoster(team=team, players=players, coaches=coaches)


@app.get("/api/v1/clubs/{club_id}/players", tags=["Clubs"])
async def get_club_players(
    club_id: int,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    search: Optional[str] = Query(None, description="Search by player name"),
    db=Depends(get_db_connection)
):
    """Get all players for a club, optionally filtered by team or name."""
    cursor = db.cursor()

    query = """
        SELECT p.*, ct.team_name, ct.team_page_url
        FROM club_players p
        LEFT JOIN club_teams ct ON p.club_team_id = ct.id
        WHERE p.club_id = ?
    """
    params: list = [club_id]

    if team_id:
        query += " AND p.club_team_id = ?"
        params.append(team_id)

    if search:
        query += " AND (p.first_name || ' ' || p.last_name LIKE ?)"
        params.append(f"%{search}%")

    query += " ORDER BY p.last_name, p.first_name"
    cursor.execute(query, params)
    players = [ClubPlayerBasic(**dict(r)) for r in cursor.fetchall()]
    return {"players": players, "count": len(players)}


@app.get("/api/v1/clubs/{club_id}/board", tags=["Clubs"])
async def get_club_board(club_id: int, db=Depends(get_db_connection)):
    """Get board members for a club."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM club_board_members
        WHERE club_id = ? AND is_active = 1
        ORDER BY
            CASE
                WHEN title LIKE '%President%' AND title NOT LIKE '%Vice%' THEN 1
                WHEN title LIKE '%Vice President%' THEN 2
                WHEN title LIKE '%Secretary%' THEN 3
                WHEN title LIKE '%Treasurer%' THEN 4
                WHEN title LIKE '%Director%' THEN 5
                WHEN title LIKE '%Coordinator%' THEN 6
                ELSE 7
            END,
            name
    """, (club_id,))
    members = [ClubBoardMemberInfo(**dict(r)) for r in cursor.fetchall()]
    return {"board_members": members, "count": len(members)}


@app.get("/api/v1/clubs/{club_id}/coaches", tags=["Clubs"])
async def get_club_coaches(club_id: int, db=Depends(get_db_connection)):
    """Get all coaches for a club."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT c.*, ct.team_name, ct.team_page_url
        FROM club_coaches c
        LEFT JOIN club_teams ct ON c.club_team_id = ct.id
        WHERE c.club_id = ?
        ORDER BY c.name
    """, (club_id,))
    coaches = [ClubCoachInfo(**dict(r)) for r in cursor.fetchall()]
    return {"coaches": coaches, "count": len(coaches)}


@app.get("/api/v1/clubs/{club_id}/contacts", tags=["Clubs"])
async def get_club_contacts(club_id: int, db=Depends(get_db_connection)):
    """Get contact information for a club."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM club_contacts
        WHERE club_id = ?
        ORDER BY contact_type, value
    """, (club_id,))
    contacts = [ClubContactInfo(**dict(r)) for r in cursor.fetchall()]
    return {"contacts": contacts, "count": len(contacts)}


@app.get("/api/v1/clubs/{club_id}/games", tags=["Clubs"])
async def get_club_games(
    club_id: int,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    status: Optional[str] = Query(None, description="Filter by status: scheduled, final, cancelled"),
    db=Depends(get_db_connection)
):
    """Get schedule/games for a club, optionally filtered by team or status."""
    cursor = db.cursor()

    query = "SELECT * FROM club_games WHERE club_id = ?"
    params: list = [club_id]

    if team_id:
        query += " AND club_team_id = ?"
        params.append(team_id)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY date, time"
    cursor.execute(query, params)
    games = [ClubGameInfo(**dict(r)) for r in cursor.fetchall()]
    return {"games": games, "count": len(games)}






# ============================================================================
# ERROR HANDLERS (keep at bottom)
# ============================================================================

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal server error occurred",
                "details": {"error": str(exc)}
            },
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
