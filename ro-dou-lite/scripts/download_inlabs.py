#!/usr/bin/env python3
"""
Download INLABS DOU data and load into SQLite database.

Usage:
    python download_inlabs.py [--date YYYY-MM-DD] [--config path/to/config.yaml]

Examples:
    # Download today's data
    python download_inlabs.py

    # Download specific date
    python download_inlabs.py --date 2025-01-15

    # Use custom config
    python download_inlabs.py --config /path/to/config.yaml
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.database import Database
from src.inlabs_client import INLABSClient
from src.xml_parser import XMLParser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Download INLABS DOU data')
    parser.add_argument(
        '--date',
        type=str,
        default=datetime.now().strftime('%Y-%m-%d'),
        help='Date to download (YYYY-MM-DD), default: today'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--keep-downloads',
        action='store_true',
        help='Keep downloaded files (default: cleanup after loading)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = Config.from_file(args.config)

        # Initialize database
        logger.info("Initializing database")
        db = Database(str(config.get_database_path()))
        db.initialize()

        # Get INLABS credentials
        username, password = config.get_inlabs_credentials()
        download_path = config.get_inlabs_download_path()

        # Initialize INLABS client
        logger.info("Connecting to INLABS portal")
        client = INLABSClient(username, password)

        # Download files
        logger.info(f"Downloading files for {args.date}")
        downloaded_files = client.download_date(
            target_date=args.date,
            dest_dir=str(download_path),
            cleanup_zip=True
        )

        if not downloaded_files:
            logger.warning(f"No files found for {args.date}")
            return 0

        # Parse XML files
        logger.info(f"Parsing {len(downloaded_files)} XML files")
        parser = XMLParser()

        # Parse all files in the date directory
        date_dir = download_path / args.date
        articles = parser.parse_directory(str(date_dir))

        if not articles:
            logger.warning("No articles extracted from XML files")
            return 0

        # Load into database
        logger.info(f"Loading {len(articles)} articles into database")
        inserted = db.insert_articles_batch(articles)

        logger.info(f"Successfully inserted {inserted} articles")

        # Cleanup old data
        retention_days = config.get_retention_days()
        logger.info(f"Cleaning up data older than {retention_days} days")
        deleted = db.cleanup_old_articles(retention_days)
        logger.info(f"Deleted {deleted} old articles")

        # Cleanup downloaded files unless keep flag is set
        if not args.keep_downloads:
            import shutil
            shutil.rmtree(date_dir, ignore_errors=True)
            logger.info("Cleaned up downloaded files")

        # Print summary
        logger.info("=" * 60)
        logger.info(f"Download Summary for {args.date}")
        logger.info(f"  XML files processed: {len(downloaded_files)}")
        logger.info(f"  Articles parsed: {len(articles)}")
        logger.info(f"  Articles inserted: {inserted}")
        logger.info(f"  Old articles deleted: {deleted}")
        logger.info(f"  Total articles in database: {db.get_article_count()}")
        logger.info("=" * 60)

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
