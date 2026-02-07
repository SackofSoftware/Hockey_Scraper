#!/usr/bin/env python3
"""
Unified Data Import - Import ALL leagues into a single database
BSHL (Season 10776) + EHF (Season 10477)

Writes to /tmp first to avoid Dropbox sync corruption, then copies
the finished database to the project directory.
"""
import sys, os, shutil, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
from advanced_stats_database import create_database
from data_importer import DataImporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

LEAGUES = [
    {"name": "Bay State Hockey League", "season_id": "10776"},
    {"name": "Eastern Hockey Federation", "season_id": "10477"},
]

# Final destination in project directory
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL_DB_PATH = os.path.join(PROJECT_DIR, "hockey_stats.db")


def main():
    # Build in /tmp to avoid Dropbox sync corruption
    tmp_db = os.path.join(tempfile.gettempdir(), "hockey_stats_build.db")

    if os.path.exists(tmp_db):
        os.remove(tmp_db)
        logger.info(f"Removed existing temp database: {tmp_db}")

    logger.info(f"Building database in: {tmp_db}")
    logger.info("Creating database schema...")
    db = create_database(tmp_db)

    try:
        for league in LEAGUES:
            logger.info(f"\n{'='*60}")
            logger.info(f"Importing {league['name']} (Season {league['season_id']})...")
            logger.info(f"{'='*60}")

            importer = DataImporter(db, league['season_id'])
            importer.import_all()

            logger.info(f"{league['name']} import complete!")

    finally:
        db.close()

    # Copy finished database to project directory
    logger.info(f"\nCopying database to: {FINAL_DB_PATH}")
    if os.path.exists(FINAL_DB_PATH):
        os.remove(FINAL_DB_PATH)
    shutil.copy2(tmp_db, FINAL_DB_PATH)
    os.remove(tmp_db)

    logger.info(f"All leagues imported into: {FINAL_DB_PATH}")
    logger.info(f"Database size: {os.path.getsize(FINAL_DB_PATH) / 1024 / 1024:.1f} MB")


if __name__ == '__main__':
    main()
