#!/usr/bin/env python3
"""
Incremental import - only fetch specific game IDs
Fast sync for updating database with new games
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
from pathlib import Path
from data_importer import GameSheetImporter

def main():
    parser = argparse.ArgumentParser(description="Import specific games incrementally")
    parser.add_argument('--season-id', required=True, help="Season ID")
    parser.add_argument('--game-ids', required=True, help="Comma-separated game IDs")
    parser.add_argument('--db', required=True, help="Database path")

    args = parser.parse_args()

    game_ids = args.game_ids.split(',')

    print(f"Importing {len(game_ids)} games...")

    # Use existing importer but with specific game IDs
    importer = GameSheetImporter(args.db)

    for i, game_id in enumerate(game_ids, 1):
        print(f"  [{i}/{len(game_ids)}] Importing game {game_id}...")
        try:
            importer.import_single_box_score(args.season_id, game_id)
        except Exception as e:
            print(f"    ❌ Failed: {e}")
            continue

    print(f"✅ Imported {len(game_ids)} games")
    return 0

if __name__ == "__main__":
    sys.exit(main())
