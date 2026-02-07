"""
Test script for Hockey Stats API
Run after starting the server with: uvicorn api_server:app --reload

Usage: python3 test_api.py
"""
import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000/api/v1"


def print_section(title: str):
    """Print section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print('=' * 80)


def print_json(data: Dict[Any, Any], indent: int = 2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent))


def test_health():
    """Test health check endpoint"""
    print_section("HEALTH CHECK")
    response = requests.get("http://localhost:8000/health")
    print(f"Status Code: {response.status_code}")
    print_json(response.json())
    return response.status_code == 200


def test_season_info(season_id: str = "10776"):
    """Test season info endpoint"""
    print_section(f"SEASON INFO - {season_id}")
    response = requests.get(f"{BASE_URL}/seasons/{season_id}")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nSeason: {data['title']}")
        print(f"Sport: {data['sport']}")
        print(f"Divisions: {data['divisions_count']}")
        print(f"Teams: {data['teams_count']}")
        print(f"Games: {data['games_count']}")
        return True
    else:
        print_json(response.json())
        return False


def test_divisions(season_id: str = "10776"):
    """Test divisions endpoint"""
    print_section(f"DIVISIONS - {season_id}")
    response = requests.get(f"{BASE_URL}/seasons/{season_id}/divisions")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nFound {len(data['divisions'])} divisions:")
        for div in data['divisions'][:5]:  # Show first 5
            print(f"  - {div['division_name']} (ID: {div['division_id']}) - {div['teams_count']} teams")
        return data['divisions']
    else:
        print_json(response.json())
        return []


def test_standings(division_id: int):
    """Test division standings endpoint"""
    print_section(f"STANDINGS - Division {division_id}")
    response = requests.get(f"{BASE_URL}/divisions/{division_id}/standings")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nDivision: {data['division']['division_name']}")
        print(f"\nStandings:")
        for team in data['standings'][:5]:  # Top 5
            record = team['record']
            scoring = team['scoring']
            print(f"  {team['rank']}. {team['team']['team_name']}")
            print(f"     Record: {record['record_string']} - {record['points']} pts ({record['points_pct']:.3f})")
            print(f"     Goals: {scoring['goals_for']} for, {scoring['goals_against']} against ({scoring['goal_differential']:+d})")
        return data['standings']
    else:
        print_json(response.json())
        return []


def test_team_stats(team_id: int):
    """Test team stats endpoint"""
    print_section(f"TEAM STATS - Team {team_id}")
    response = requests.get(f"{BASE_URL}/teams/{team_id}/stats")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        team = data['team']
        record = data['record']
        scoring = data['scoring']
        recent = data['recent_form']

        print(f"\n{team['team_name']} ({team['division_name']})")
        print(f"\nRecord: {record['record_string']}")
        print(f"  Points: {record['points']} ({record['points_pct']:.3f})")
        print(f"  Division Rank: {record['division_rank']}")

        print(f"\nScoring:")
        print(f"  Goals For: {scoring['goals_for']['value']} ({scoring['goals_per_game']['value']:.2f}/game)")
        print(f"  Goals Against: {scoring['goals_against']['value']} ({scoring['goals_against_per_game']['value']:.2f}/game)")
        print(f"  Goal Differential: {scoring['goal_differential']['value']:+d}")

        print(f"\nRecent Form:")
        print(f"  Current Streak: {recent['current_streak']}")
        print(f"  Last 5 Games:")
        for game in recent['last_5_games']:
            home_away = "vs" if game['is_home'] else "@"
            print(f"    {game['date']}: {game['result']} {home_away} {game['opponent']} ({game['score']})")

        return True
    else:
        print_json(response.json())
        return False


def test_team_schedule(team_id: int):
    """Test team schedule endpoint"""
    print_section(f"TEAM SCHEDULE - Team {team_id}")
    response = requests.get(f"{BASE_URL}/teams/{team_id}/schedule")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nFound {len(data)} games")
        print("\nRecent/Upcoming Games:")
        for game in data[:5]:
            score = f"{game['home_score']}-{game['visitor_score']}" if game['home_score'] is not None else "TBD"
            print(f"  {game['date']} - {game['home_team']['team_name']} vs {game['visitor_team']['team_name']}")
            print(f"    Status: {game['status']} | Score: {score} | Venue: {game['location']}")
        return len(data) > 0
    else:
        print_json(response.json())
        return False


def test_team_roster(team_id: int):
    """Test team roster endpoint"""
    print_section(f"TEAM ROSTER - Team {team_id}")
    response = requests.get(f"{BASE_URL}/teams/{team_id}/roster")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nRoster ({len(data)} players):")
        for player in data[:10]:  # Show first 10
            name = player['player_name'] if player['player_name'] else "(No name)"
            print(f"  #{player['player_number']} - {name}")
        return data
    else:
        print_json(response.json())
        return []


def test_team_leaders(team_id: int):
    """Test team leaders endpoint"""
    print_section(f"TEAM LEADERS - Team {team_id}")
    response = requests.get(f"{BASE_URL}/teams/{team_id}/leaders?limit=5")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()

        print("\nPoints Leaders:")
        for leader in data['points']:
            print(f"  {leader['rank']}. #{leader['player']['player_number']} - {leader['value']} pts ({leader['games_played']} GP)")

        print("\nGoals Leaders:")
        for leader in data['goals']:
            print(f"  {leader['rank']}. #{leader['player']['player_number']} - {leader['value']} G ({leader['games_played']} GP)")

        return True
    else:
        print_json(response.json())
        return False


def test_player_search(number: str, team_id: int):
    """Test player search endpoint"""
    print_section(f"PLAYER SEARCH - #{number} on Team {team_id}")
    response = requests.get(f"{BASE_URL}/players/search?number={number}&team_id={team_id}")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nFound {len(data)} player(s):")
        for result in data:
            player = result['player']
            team = result['team']
            print(f"  #{player['player_number']} on {team['team_name']}")
            print(f"    Player ID: {player['player_id']}")
            print(f"    Confidence: {result['confidence_score']}")
            print(f"    Matches: {', '.join(result['matches'])}")
        return data
    else:
        print_json(response.json())
        return []


def test_player_stats(player_id: str):
    """Test player stats endpoint"""
    print_section(f"PLAYER STATS - Player {player_id}")
    response = requests.get(f"{BASE_URL}/players/{player_id}/stats")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nGames Played: {data['games_played']}")
        print(f"Goals: {data['goals']}")
        print(f"Assists: {data['assists']}")
        print(f"Points: {data['points']} ({data['points_per_game']:.2f} PPG)")
        print(f"Penalty Minutes: {data['penalty_minutes']} ({data['pim_per_game']:.2f} PIM/G)")
        print(f"Team Rank (Points): {data['team_rank_points']}")
        return True
    else:
        print_json(response.json())
        return False


def test_league_leaders(season_id: str = "10776", category: str = "points"):
    """Test league leaders endpoint"""
    print_section(f"LEAGUE LEADERS - {category.upper()}")
    response = requests.get(f"{BASE_URL}/seasons/{season_id}/leaders/{category}?limit=10&min_games=5")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nTop 10 {category.title()} Leaders (min 5 games):")
        print(f"Total Qualified Players: {data['total_qualified_players']}\n")

        for leader in data['leaders']:
            player = leader['player']
            team = leader['team']
            print(f"  {leader['rank']}. #{player['player_number']} ({team['team_name']})")
            print(f"      {category.title()}: {leader['value']} in {leader['games_played']} GP")
            print(f"      Percentile: {leader['percentile']:.1f}% - {leader['interpretation']}")
        return True
    else:
        print_json(response.json())
        return False


def run_all_tests():
    """Run all API tests"""
    print_section("STARTING API TESTS")
    print("Base URL:", BASE_URL)

    results = []

    # Test health check
    results.append(("Health Check", test_health()))

    # Test season info
    results.append(("Season Info", test_season_info()))

    # Test divisions
    divisions = test_divisions()
    results.append(("Divisions", len(divisions) > 0))

    # Test standings (use first division)
    if divisions:
        division_id = divisions[0]['division_id']
        standings = test_standings(division_id)
        results.append(("Standings", len(standings) > 0))

        # Test team endpoints (use first team)
        if standings:
            team_id = standings[0]['team']['team_id']

            results.append(("Team Stats", test_team_stats(team_id)))
            results.append(("Team Schedule", test_team_schedule(team_id)))

            roster = test_team_roster(team_id)
            results.append(("Team Roster", len(roster) > 0))

            results.append(("Team Leaders", test_team_leaders(team_id)))

            # Test player endpoints
            if roster:
                player_number = roster[0]['player_number']
                player_results = test_player_search(player_number, team_id)
                results.append(("Player Search", len(player_results) > 0))

                if player_results:
                    player_id = player_results[0]['player']['player_id']
                    results.append(("Player Stats", test_player_stats(player_id)))

    # Test league leaders
    results.append(("Points Leaders", test_league_leaders("10776", "points")))
    results.append(("Goals Leaders", test_league_leaders("10776", "goals")))
    results.append(("Assists Leaders", test_league_leaders("10776", "assists")))

    # Print summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    return passed == total


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API server")
        print("Make sure the server is running:")
        print("  uvicorn api_server:app --reload --port 8000")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
