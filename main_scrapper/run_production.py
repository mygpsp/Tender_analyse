#!/usr/bin/env python3
"""
Production script for running main scraper in headless mode with multiple workers.

Usage:
    # Run with 10 workers for 30 days
    python3 main_scrapper/run_production.py --concurrency 10 --days 30
    
    # Run in background
    nohup python3 main_scrapper/run_production.py --concurrency 10 --days 30 > scraper.log 2>&1 &
"""
import argparse
import asyncio
import logging
from pathlib import Path
from datetime import date, timedelta

# Import from main_scraper module
import sys
sys.path.insert(0, str(Path(__file__).parent))

from main_scraper import (
    analyze_existing_data,
    suggest_start_date,
    scrape_parallel,
    load_config,
    build_configs
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("production_scraper")


def main():
    parser = argparse.ArgumentParser(
        description="Production scraper for tenders (headless mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--concurrency',
        type=int,
        default=10,
        help='Number of parallel workers (default: 10)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to scrape (default: 30)'
    )
    parser.add_argument(
        '--date-from',
        type=str,
        help='Start date (YYYY-MM-DD). If not provided, will use suggested date.'
    )
    parser.add_argument(
        '--date-to',
        type=str,
        help='End date (YYYY-MM-DD). If not provided, will use today + 30 days.'
    )
    parser.add_argument(
        '--data-file',
        type=Path,
        default=Path('main_scrapper/data/tenders.jsonl'),
        help='Path to data file (default: main_scrapper/data/tenders.jsonl)'
    )
    parser.add_argument(
        '--config',
        default=Path('main_scrapper/config/selectors.yaml'),
        help='Path to config file (default: main_scrapper/config/selectors.yaml)'
    )
    parser.add_argument("--tender-type", help="Filter by tender type (e.g., CON, NAT)")
    parser.add_argument("--category-code", help="Filter by category code (e.g., 60100000)")

    
    args = parser.parse_args()
    
    # Analyze existing data
    logger.info("Analyzing existing data...")
    analysis = analyze_existing_data(args.data_file)
    suggested_start, suggested_end = suggest_start_date(analysis)
    
    # Determine dates
    if args.date_from:
        start_date = args.date_from
    else:
        start_date = suggested_start
    
    if args.date_to:
        end_date = args.date_to
    else:
        # Calculate end date based on days parameter
        start_dt = date.fromisoformat(start_date)
        end_dt = start_dt + timedelta(days=args.days)
        end_date = end_dt.strftime('%Y-%m-%d')
    
    logger.info(f"🚀 Starting production scrape")
    logger.info(f"   Date range: {start_date} to {end_date}")
    logger.info(f"   Workers: {args.concurrency}")
    logger.info(f"   Output: {args.data_file}")
    logger.info(f"   Existing tenders: {len(analysis['tender_numbers']):,}")
    logger.info(f"   Mode: HEADLESS (no browser windows)")
    
    # Run scraper
    result = asyncio.run(
        scrape_parallel(
            args.config,
            start_date,
            end_date,
            analysis['tender_numbers'].copy(),
            args.data_file,
            args.concurrency,
            args.tender_type,
            args.category_code
        )
    )
    
    logger.info("=" * 60)
    logger.info("SCRAPING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"New tenders scraped: {result.get('new_tenders', 0)}")
    logger.info(f"Duplicates skipped: {result.get('skipped_duplicates', 0)}")
    if result.get('error'):
        logger.error(f"Errors: {result['error']}")
    logger.info("=" * 60)
    
    if result.get('new_tenders', 0) > 0:
        logger.info(f"✅ Successfully scraped {result['new_tenders']} new tenders!")
    else:
        logger.info("ℹ️  No new tenders found.")


if __name__ == "__main__":
    main()
