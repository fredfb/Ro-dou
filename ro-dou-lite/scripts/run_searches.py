#!/usr/bin/env python3
"""
Run DOU searches and send email notifications.

Usage:
    python run_searches.py [--config path/to/config.yaml]

Examples:
    # Run with default config
    python run_searches.py

    # Use custom config
    python run_searches.py --config /path/to/config.yaml

    # Dry run (no emails sent)
    python run_searches.py --dry-run
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
from src.searcher import Searcher
from src.notifier import EmailNotifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run DOU searches and send notifications')
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run searches but do not send emails'
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

        # Initialize searcher
        searcher = Searcher(db)

        # Get search configurations
        searches = config.get_searches()
        logger.info(f"Running {len(searches)} search configurations")

        all_results = {}
        total_matches = 0

        # Run each search
        for i, search_config in enumerate(searches, 1):
            logger.info(f"Running search {i}/{len(searches)}")

            terms = search_config.get('terms', [])
            sections = search_config.get('sections')
            departments = search_config.get('departments')

            logger.info(f"  Terms: {terms}")
            if sections:
                logger.info(f"  Sections: {sections}")
            if departments:
                logger.info(f"  Departments: {departments}")

            # Execute search
            results = searcher.search(
                terms=terms,
                sections=sections,
                departments=departments,
                days_back=1
            )

            if results:
                # Group by term
                for term in terms:
                    term_results = [
                        r for r in results
                        if term.lower() in r.get('matched_terms', [])
                    ]

                    if term_results:
                        if term not in all_results:
                            all_results[term] = []

                        # Filter out already-notified articles
                        new_results = []
                        for article in term_results:
                            if not db.was_notified(term, article['id']):
                                new_results.append(article)

                        all_results[term].extend(new_results)
                        total_matches += len(new_results)

                        logger.info(f"  Found {len(new_results)} new matches for '{term}'")

        # Send notifications if results found
        if all_results and any(all_results.values()):
            logger.info(f"Total new matches found: {total_matches}")

            # Check if email is configured
            if not config.is_email_enabled():
                logger.warning("Email notifications not configured, skipping")
            elif args.dry_run:
                logger.info("DRY RUN: Would send email with results")
                logger.info(f"Recipients would be: {config.get_email_config().get('to')}")
            else:
                # Send email
                logger.info("Sending email notifications")

                email_config = config.get_email_config()
                notifier = EmailNotifier.from_config(email_config)

                subject = f"Ro-DOU Alerts - {datetime.now().strftime('%d/%m/%Y')}"

                notifier.send(
                    to_emails=email_config['to'],
                    subject=subject,
                    results=all_results
                )

                logger.info(f"Sent notification to {len(email_config['to'])} recipients")

                # Log notifications to prevent duplicate alerts
                for term, articles in all_results.items():
                    for article in articles:
                        db.log_notification(term, article['id'])

                logger.info("Logged notifications to database")

        else:
            logger.info("No new matches found")

        # Print summary
        logger.info("=" * 60)
        logger.info(f"Search Summary")
        logger.info(f"  Searches run: {len(searches)}")
        logger.info(f"  New matches found: {total_matches}")
        logger.info(f"  Email sent: {'No (dry run)' if args.dry_run else 'Yes' if all_results else 'No (no results)'}")
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
