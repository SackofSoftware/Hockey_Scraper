#!/usr/bin/env python3
"""
Validation script for game details parsing.

This script validates that game detail data has been properly scraped and parsed.
It checks for data consistency and completeness.

Usage:
    python3 validate_game_details.py data/test_details/schedules.json
"""

import json
import sys
from pathlib import Path


def validate_game_details(json_file: Path):
    """Validate game details from scraped JSON."""
    print(f"[*] Validating game details from: {json_file}")

    with open(json_file, 'r') as f:
        games = json.load(f)

    print(f"[*] Loaded {len(games)} games")

    stats = {
        'total_games': len(games),
        'games_with_scores': 0,
        'games_with_period_scores': 0,
        'games_with_scoring_summary': 0,
        'games_with_penalties': 0,
        'games_with_shots': 0,
        'unplayed_games': 0,
        'validation_errors': []
    }

    for i, game in enumerate(games, 1):
        game_id = game.get('game_id', 'unknown')
        visitor_team = game.get('visitor_team', 'Unknown')
        home_team = game.get('home_team', 'Unknown')

        # Check if game has been played
        has_scores = game.get('visitor_score') is not None and game.get('home_score') is not None

        if has_scores:
            stats['games_with_scores'] += 1

            visitor_score = int(game['visitor_score'])
            home_score = int(game['home_score'])

            # Check for period scores
            if game.get('period_scores'):
                stats['games_with_period_scores'] += 1

                # Validate period scores sum to final scores
                try:
                    visitor_total = sum(p['visitor'] for p in game['period_scores'].values())
                    home_total = sum(p['home'] for p in game['period_scores'].values())

                    if visitor_total != visitor_score:
                        stats['validation_errors'].append(
                            f"Game {game_id}: Visitor period scores ({visitor_total}) don't match final score ({visitor_score})"
                        )

                    if home_total != home_score:
                        stats['validation_errors'].append(
                            f"Game {game_id}: Home period scores ({home_total}) don't match final score ({home_score})"
                        )
                except (KeyError, TypeError, ValueError) as e:
                    stats['validation_errors'].append(
                        f"Game {game_id}: Error validating period scores - {e}"
                    )

            # Check for scoring summary
            if game.get('scoring_summary'):
                stats['games_with_scoring_summary'] += 1
                goals = game['scoring_summary']

                # Validate total goals
                if len(goals) != (visitor_score + home_score):
                    stats['validation_errors'].append(
                        f"Game {game_id}: Scoring summary has {len(goals)} goals but final score is {visitor_score}-{home_score}"
                    )

                # Validate goal structure
                for goal in goals:
                    required_fields = ['period', 'time', 'player']
                    for field in required_fields:
                        if not goal.get(field):
                            stats['validation_errors'].append(
                                f"Game {game_id}: Goal missing required field '{field}'"
                            )

            # Check for penalties
            if game.get('penalties'):
                stats['games_with_penalties'] += 1

                # Validate penalty structure
                for penalty in game['penalties']:
                    required_fields = ['period', 'time', 'player', 'penalty']
                    for field in required_fields:
                        if not penalty.get(field):
                            stats['validation_errors'].append(
                                f"Game {game_id}: Penalty missing required field '{field}'"
                            )

            # Check for shots on goal
            if game.get('shots_on_goal'):
                stats['games_with_shots'] += 1

        else:
            stats['unplayed_games'] += 1

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total games:                    {stats['total_games']}")
    print(f"Games with scores:              {stats['games_with_scores']}")
    print(f"Unplayed games:                 {stats['unplayed_games']}")
    print()
    print(f"Games with period scores:       {stats['games_with_period_scores']} ({_pct(stats['games_with_period_scores'], stats['games_with_scores'])})")
    print(f"Games with scoring summary:     {stats['games_with_scoring_summary']} ({_pct(stats['games_with_scoring_summary'], stats['games_with_scores'])})")
    print(f"Games with penalties:           {stats['games_with_penalties']} ({_pct(stats['games_with_penalties'], stats['games_with_scores'])})")
    print(f"Games with shots on goal:       {stats['games_with_shots']} ({_pct(stats['games_with_shots'], stats['games_with_scores'])})")
    print()

    if stats['validation_errors']:
        print(f"VALIDATION ERRORS: {len(stats['validation_errors'])}")
        print("=" * 60)
        for error in stats['validation_errors']:
            print(f"  [!] {error}")
        print()
        return False
    else:
        print("[OK] No validation errors found!")
        print()
        return True


def _pct(numerator: int, denominator: int) -> str:
    """Calculate percentage string."""
    if denominator == 0:
        return "N/A"
    pct = (numerator / denominator) * 100
    return f"{pct:.1f}%"


def show_example_game(json_file: Path):
    """Show an example game with details."""
    with open(json_file, 'r') as f:
        games = json.load(f)

    # Find a game with full details
    detailed_game = None
    for game in games:
        if (game.get('period_scores') and
            game.get('scoring_summary') and
            game.get('penalties') and
            game.get('shots_on_goal')):
            detailed_game = game
            break

    if not detailed_game:
        # Find any game with period scores
        for game in games:
            if game.get('period_scores'):
                detailed_game = game
                break

    if detailed_game:
        print("=" * 60)
        print("EXAMPLE GAME WITH DETAILS")
        print("=" * 60)
        print(f"Game ID:     {detailed_game['game_id']}")
        print(f"Date:        {detailed_game['date']}")
        print(f"Matchup:     {detailed_game['visitor_team']} @ {detailed_game['home_team']}")
        print(f"Final Score: {detailed_game['visitor_score']} - {detailed_game['home_score']}")
        print()

        if detailed_game.get('period_scores'):
            print("Period Scores:")
            for period, scores in detailed_game['period_scores'].items():
                print(f"  {period:3s}: {scores['visitor']} - {scores['home']}")
            print()

        if detailed_game.get('scoring_summary'):
            print(f"Scoring Summary ({len(detailed_game['scoring_summary'])} goals):")
            for goal in detailed_game['scoring_summary']:
                assists_str = ", ".join(goal['assists']) if goal['assists'] else "Unassisted"
                print(f"  {goal['period']:3s} {goal['time']:5s} - {goal['player']} ({assists_str})")
            print()

        if detailed_game.get('penalties'):
            print(f"Penalties ({len(detailed_game['penalties'])} penalties):")
            for penalty in detailed_game['penalties']:
                mins = f"{penalty['minutes']} min" if penalty.get('minutes') else ""
                print(f"  {penalty['period']:3s} {penalty['time']:5s} - {penalty['player']} - {penalty['penalty']} {mins}")
            print()

        if detailed_game.get('shots_on_goal'):
            print("Shots on Goal:")
            for period, shots in detailed_game['shots_on_goal'].items():
                if isinstance(shots, dict):
                    print(f"  {period:3s}: {shots.get('visitor', 'N/A')} - {shots.get('home', 'N/A')}")
                else:
                    print(f"  {period:5s}: {shots}")
            print()


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 validate_game_details.py <schedules.json>")
        print("\nExample:")
        print("  python3 validate_game_details.py data/test_details/schedules.json")
        sys.exit(1)

    json_file = Path(sys.argv[1])

    if not json_file.exists():
        print(f"[!] Error: File not found: {json_file}")
        sys.exit(1)

    # Validate
    success = validate_game_details(json_file)

    # Show example
    show_example_game(json_file)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
