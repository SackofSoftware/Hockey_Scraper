#!/usr/bin/env python3
"""
Fetch ALL GameSheet Data from all divisions

This script fetches data from ALL divisions automatically by first 
retrieving the list of divisions and then fetching data for each one.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
import requests
from datetime import datetime

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def fetch_all_divisions(season_id: str) -> List[Dict]:
    """Fetch all divisions for a season"""
    base_api = "https://gamesheetstats.com/api"
    url = f"{base_api}/useSeasonDivisions/getDivisions/{season_id}"
    
    try:
        print(f"Fetching all divisions for season {season_id}...")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            divisions = response.json()
            print(f"Found {len(divisions)} divisions")
            return divisions
        else:
            print(f"Error fetching divisions: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching divisions: {e}")
        return []

def extract_gamesheet_data_for_all_divisions(season_id: str, out_dir: Path) -> Dict[str, Any]:
    """
    Extract data from GameSheetStats API for ALL divisions.
    """
    print(f"Extracting GameSheet data for ALL divisions in season {season_id}")
    
    # First, get all divisions
    all_divisions = fetch_all_divisions(season_id)
    if not all_divisions:
        print("No divisions found, exiting")
        return {}
    
    # Extract division IDs
    division_ids = [str(div["id"]) for div in all_divisions]
    print(f"Division IDs: {', '.join(division_ids)}")
    
    # Base API URL
    base_api = "https://gamesheetstats.com/api"
    divisions_param = ",".join(division_ids)
    timezone_offset = -240  # EDT timezone
    
    # API endpoints
    endpoints = {
        "season": f"{base_api}/useSeasonDivisions/getSeason/{season_id}",
        "divisions": f"{base_api}/useSeasonDivisions/getDivisions/{season_id}",
        "division_standings": f"{base_api}/useStandings/getDivisionStandings/{season_id}?filter[divisions]={divisions_param}&filter[limit]=100&filter[offset]=0&filter[timeZoneOffset]={timezone_offset}",
    }
    
    results = {}
    
    # Fetch data from each endpoint
    for name, url in endpoints.items():
        try:
            print(f"  Fetching {name}...")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results[name] = data
                
                # Save raw API response
                raw_dir = out_dir / "raw" 
                ensure_dir(raw_dir)
                filename = raw_dir / f"gamesheet_{name}_{season_id}.json"
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"    Saved to {filename}")
            else:
                print(f"    Error {response.status_code}: {response.text[:200]}...")
                
        except Exception as e:
            print(f"    Failed to fetch {name}: {e}")
    
    # Fetch division schedule with pagination (like the scrolling behavior)
    print("  Fetching division schedule (paginated)...")
    division_schedule_data = {}
    offset = 0
    max_pages = 100  # Reasonable limit
    
    while offset < max_pages:
        try:
            schedule_url = f"{base_api}/useSchedule/getSeasonSchedule/{season_id}?filter[divisions]={divisions_param}&filter[gametype]=overall&filter[limit]=10&filter[offset]={offset}&filter[start]={datetime.now().strftime('%Y-%m-%d')}&filter[timeZoneOffset]={timezone_offset}"
            
            response = requests.get(schedule_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got any data
                has_data = False
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        has_data = True
                        division_schedule_data[f"{key}_{offset}"] = value
                
                if not has_data:
                    print(f"    No more data at offset {offset}, stopping pagination")
                    break
                    
                print(f"    Fetched page {offset//10 + 1} (offset {offset})")
                offset += 10
            else:
                print(f"    Error at offset {offset}: {response.status_code}")
                break
                
        except Exception as e:
            print(f"    Failed to fetch schedule page at offset {offset}: {e}")
            break
    
    if division_schedule_data:
        results["division_schedule"] = division_schedule_data
        # Save paginated schedule data
        raw_dir = out_dir / "raw" 
        filename = raw_dir / f"gamesheet_division_schedule_{season_id}_paginated.json"
        with open(filename, "w") as f:
            json.dump(division_schedule_data, f, indent=2)
        print(f"    Saved paginated schedule to {filename}")
    
    return results

def normalize_gamesheet_data_all_divisions(gamesheet_results: Dict[str, Any]) -> Dict[str, List]:
    """
    Convert GameSheet API responses to normalized Game/Player/Team objects.
    """
    normalized_games = []
    normalized_players = []
    normalized_teams = []
    
    # Process division schedule (nested format)
    div_schedule = gamesheet_results.get("division_schedule", {})
    
    teams_seen = set()
    for key, daily_games in div_schedule.items():
        if isinstance(daily_games, list):
            for day_data in daily_games:
                if isinstance(day_data, dict):
                    # Handle different possible structures
                    games_list = day_data.get("games", []) if "games" in day_data else [day_data]
                    game_date = day_data.get("date")
                    
                    for game in games_list:
                        try:
                            # Try different field names based on actual structure
                            home_team_name = None
                            visitor_team_name = None
                            
                            # Check homeTeam/visitorTeam structure
                            if isinstance(game.get("homeTeam"), dict):
                                home_team_name = game["homeTeam"].get("name") or game["homeTeam"].get("title")
                            if isinstance(game.get("visitorTeam"), dict):
                                visitor_team_name = game["visitorTeam"].get("name") or game["visitorTeam"].get("title")
                            
                            # Check home/visitor structure  
                            if not home_team_name and isinstance(game.get("home"), dict):
                                home_team_name = game["home"].get("title") or game["home"].get("name")
                            if not visitor_team_name and isinstance(game.get("visitor"), dict):
                                visitor_team_name = game["visitor"].get("title") or game["visitor"].get("name")
                            
                            if home_team_name or visitor_team_name:
                                # Add teams
                                if home_team_name and home_team_name not in teams_seen:
                                    normalized_teams.append({
                                        "name": home_team_name,
                                        "source_url": "GameSheetStats API division_schedule"
                                    })
                                    teams_seen.add(home_team_name)
                                    
                                if visitor_team_name and visitor_team_name not in teams_seen:
                                    normalized_teams.append({
                                        "name": visitor_team_name,
                                        "source_url": "GameSheetStats API division_schedule"
                                    })
                                    teams_seen.add(visitor_team_name)
                                
                                # Add game
                                game_time = game.get("time") or game.get("scheduleStartTime")
                                location = game.get("location")
                                
                                normalized_games.append({
                                    "date": game_date or game.get("date"),
                                    "time": game_time,
                                    "home_team": home_team_name,
                                    "away_team": visitor_team_name,
                                    "location": location,
                                    "source_url": "GameSheetStats API division_schedule"
                                })
                            
                        except (KeyError, TypeError) as e:
                            print(f"    Warning: Failed to normalize division game: {e}")
    
    # Process divisions data to get division names
    divisions_data = gamesheet_results.get("divisions", [])
    division_names = []
    for division in divisions_data:
        division_names.append({
            "id": division.get("id"),
            "name": division.get("title"),
            "source_url": "GameSheetStats API divisions"
        })
    
    print(f"  Normalized: {len(normalized_games)} games, {len(normalized_players)} players, {len(normalized_teams)} teams, {len(division_names)} divisions")
    
    return {
        "games": normalized_games,
        "players": normalized_players,
        "teams": normalized_teams,
        "divisions": division_names
    }

def main():
    parser = argparse.ArgumentParser(description="Fetch ALL GameSheet data from all divisions")
    parser.add_argument("--season-id", type=str, default="10776", help="GameSheet season ID")
    parser.add_argument("--out", default="gamesheet_all_data", help="Output directory for JSON files")
    
    args = parser.parse_args()
    out_dir = Path(args.out)
    ensure_dir(out_dir)
    
    print("Fetching ALL GameSheet data from all divisions")
    print(f"Season ID: {args.season_id}")
    print(f"Output directory: {out_dir}")
    
    # Extract data from GameSheet APIs for ALL divisions
    gamesheet_results = extract_gamesheet_data_for_all_divisions(
        season_id=args.season_id,
        out_dir=out_dir
    )
    
    if not gamesheet_results:
        print("No data fetched, exiting")
        return 1
    
    # Normalize the data
    normalized_data = normalize_gamesheet_data_all_divisions(gamesheet_results)
    
    # Save consolidated outputs
    schedules_path = out_dir / "schedules.json"
    rosters_path = out_dir / "rosters.json"
    teams_path = out_dir / "teams.json"
    divisions_path = out_dir / "divisions.json"
    
    with open(schedules_path, "w", encoding="utf-8") as f:
        json.dump(normalized_data["games"], f, ensure_ascii=False, indent=2)
    with open(rosters_path, "w", encoding="utf-8") as f:
        json.dump(normalized_data["players"], f, ensure_ascii=False, indent=2)
    with open(teams_path, "w", encoding="utf-8") as f:
        json.dump(normalized_data["teams"], f, ensure_ascii=False, indent=2)
    with open(divisions_path, "w", encoding="utf-8") as f:
        json.dump(normalized_data["divisions"], f, ensure_ascii=False, indent=2)
    
    print("\nGameSheet API Summary:")
    print(f"  Found {len(normalized_data['divisions'])} divisions -> {divisions_path}")
    print(f"  Found {len(normalized_data['teams'])} teams -> {teams_path}")
    print(f"  Found {len(normalized_data['games'])} games -> {schedules_path}")
    print(f"  Found {len(normalized_data['players'])} players -> {rosters_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())