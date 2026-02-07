#!/usr/bin/env python3
"""
Eastern Hockey Federation Import - Season 10477
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
from advanced_stats_database import create_database
from data_importer import DataImporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Configuration
    db_path = "advanced_hockey_stats_ehf_10477.db"
    season_id = "10477"  # Eastern Hockey Federation

    # Remove existing database for fresh start
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"Removed existing database: {db_path}")

    # Create database
    logger.info("Creating database schema...")
    db = create_database(db_path)

    try:
        # Create importer
        importer = DataImporter(db, season_id)

        # Import ALL divisions
        logger.info("Starting FULL import for Eastern Hockey Federation...")
        importer.import_all()

        logger.info("\nEHF import complete!")
        logger.info(f"Database: {db_path}")

    finally:
        db.close()

if __name__ == '__main__':
    main()
