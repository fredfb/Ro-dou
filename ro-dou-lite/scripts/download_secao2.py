#!/usr/bin/env python3
"""
Download and load INLABS DOU Section 2 data to SQLite.

This script specifically downloads and processes only Section 2 (DO2) files
from INLABS portal.

Usage:
    python download_secao2.py [--date YYYY-MM-DD] [--config path/to/config.yaml]

Examples:
    # Download today's Section 2 data
    python download_secao2.py

    # Download specific date
    python download_secao2.py --date 2025-01-15
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
    parser = argparse.ArgumentParser(
        description='Download INLABS DOU Section 2 data'
    )
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
        client.authenticate()

        # Find all files for the date
        logger.info(f"Finding files for {args.date}")
        all_file_urls = client.find_files(args.date)

        if not all_file_urls:
            logger.warning(f"No files found for {args.date}")
            return 0

        # Filter Section 2 files only
        section2_urls = [url for url in all_file_urls
                         if 'DO2' in url.upper()]

        if not section2_urls:
            logger.warning(f"No Section 2 files found for {args.date}")
            return 0

        logger.info(f"Found {len(section2_urls)} Section 2 files (out of {len(all_file_urls)} total)")

        # Download Section 2 files
        downloaded_files = []
        date_dir = download_path / args.date
        date_dir.mkdir(parents=True, exist_ok=True)

        for file_url in section2_urls:
            try:
                logger.info(f"Downloading {file_url}")
                zip_path = client.download_file(file_url, download_path)

                # Extract
                extracted = client.extract_zip(zip_path, date_dir)
                downloaded_files.extend(extracted)

                # Cleanup ZIP
                zip_path.unlink()

            except Exception as e:
                logger.error(f"Failed to download {file_url}: {e}")
                continue

        if not downloaded_files:
            logger.warning("No files were successfully downloaded")
            return 0

        # Filter only XML files
        xml_files = [f for f in downloaded_files if f.suffix == '.xml']
        logger.info(f"Extracted {len(xml_files)} XML files")

        # Parse XML files
        logger.info("Parsing XML files")
        parser_obj = XMLParser()
        articles = []

        for xml_file in xml_files:
            try:
                file_articles = parser_obj.parse_file(str(xml_file))
                # Filter to ensure only Section 2 articles
                section2_articles = [
                    art for art in file_articles
                    if art.get('pubname', '').startswith('DO2')
                ]
                articles.extend(section2_articles)
            except Exception as e:
                logger.error(f"Failed to parse {xml_file.name}: {e}")
                continue

        if not articles:
            logger.warning("No Section 2 articles extracted from XML files")
            return 0

        # Load into database
        logger.info(f"Loading {len(articles)} Section 2 articles into database")
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
        logger.info(f"Section 2 Download Summary for {args.date}")
        logger.info(f"  Files found: {len(section2_urls)}")
        logger.info(f"  XML files processed: {len(xml_files)}")
        logger.info(f"  Section 2 articles parsed: {len(articles)}")
        logger.info(f"  Articles inserted: {inserted}")
        logger.info(f"  Old articles deleted: {deleted}")
        logger.info(f"  Total articles in database: {db.get_article_count()}")
        logger.info(f"  Section 2 articles: {db.count_articles(sections=['DO2', 'DO2E'])}")
        logger.info("=" * 60)

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        return 1
    finally:
        if 'client' in locals():
            client.close()


if __name__ == '__main__':
    sys.exit(main())
