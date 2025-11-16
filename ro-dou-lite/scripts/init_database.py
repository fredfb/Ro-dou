#!/usr/bin/env python3
"""
Initialize Ro-DOU Lite database.

Usage:
    python init_database.py [--config path/to/config.yaml]
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.database import Database

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Initialize Ro-DOU Lite database')
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file'
    )

    args = parser.parse_args()

    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = Config.from_file(args.config)

        db_path = config.get_database_path()
        logger.info(f"Database path: {db_path}")

        # Initialize database
        logger.info("Initializing database schema")
        db = Database(str(db_path))
        db.initialize()

        # Print stats
        logger.info("=" * 60)
        logger.info("Database initialized successfully")
        logger.info(f"  Location: {db_path}")
        logger.info(f"  Size: {db_path.stat().st_size if db_path.exists() else 0} bytes")
        logger.info(f"  Articles: {db.get_article_count()}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
