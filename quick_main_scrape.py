#!/usr/bin/env python3
"""
Quick Main Scraping - Get New Tenders Fast

This script runs ONLY main scraping (no detailed scraping) for all tender types.
Perfect for daily updates to get new tender listings quickly.

Usage:
    python3 quick_main_scrape.py                    # Scrape all types
    python3 quick_main_scrape.py --type CON         # Scrape only CON
    python3 quick_main_scrape.py --type NAT --type SPA  # Scrape NAT and SPA
"""

import argparse
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent

# Tender types
TENDER_TYPES = {
    'CON': {'category_code': '60100000'},
    'NAT': {'category_code': None},
    'SPA': {'category_code': None},
    'CNT': {'category_code': None},
    'MEP': {'category_code': None},
    'DAP': {'category_code': None},
    'TEP': {'category_code': None},
    'GEO': {'category_code': None},
    'DEP': {'category_code': None},
    'GRA': {'category_code': None}
}

def run_main_scraper(tender_type: str, start_date: str, end_date: str):
    """Run main scraper for a specific tender type."""
    logger.info(f"=" * 70)
    logger.info(f"📊 MAIN SCRAPING: {tender_type}")
    logger.info(f"=" * 70)
    
    config = TENDER_TYPES[tender_type]
    
    cmd = [
        'python3',
        'main_scrapper/tender_scraper.py',
        '--date-from', start_date,
        '--date-to', end_date,
        '--headless', 'true',
        '--tender-type', tender_type
    ]
    
    if config['category_code']:
        cmd.extend(['--category-code', config['category_code']])
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes
        )
        
        if result.returncode == 0:
            logger.info(f"✅ {tender_type} main scraping completed successfully")
            # Show last 20 lines of output
            output_lines = result.stdout.split('\n')
            for line in output_lines[-20:]:
                if line.strip():
                    logger.info(f"   {line}")
            return True
        else:
            logger.error(f"❌ {tender_type} main scraping failed")
            logger.error(f"Error: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {tender_type} scraping timed out")
        return False
    except Exception as e:
        logger.error(f"❌ {tender_type} scraping error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Quick Main Scraping - Get new tenders fast (no detailed scraping)'
    )
    parser.add_argument(
        '--type',
        action='append',
        choices=list(TENDER_TYPES.keys()),
        help='Tender type to scrape (can specify multiple). If not specified, scrapes all types.'
    )
    parser.add_argument(
        '--days-back',
        type=int,
        default=2,
        help='How many days back to start scraping (default: 2)'
    )
    parser.add_argument(
        '--days-forward',
        type=int,
        default=60,
        help='How many days forward to scrape (default: 60 = ~2 months)'
    )
    
    args = parser.parse_args()
    
    # Calculate date range
    now = datetime.now()
    start_date = (now - timedelta(days=args.days_back)).strftime('%Y-%m-%d')
    end_date = (now + timedelta(days=args.days_forward)).strftime('%Y-%m-%d')
    
    logger.info("=" * 70)
    logger.info("🚀 QUICK MAIN SCRAPING")
    logger.info("=" * 70)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Types to scrape: {args.type if args.type else 'ALL'}")
    logger.info("=" * 70)
    
    # Determine which types to scrape
    types_to_scrape = args.type if args.type else list(TENDER_TYPES.keys())
    
    # Run scraping for each type
    results = {}
    start_time = datetime.now()
    
    for tender_type in types_to_scrape:
        success = run_main_scraper(tender_type, start_date, end_date)
        results[tender_type] = success
    
    # Print summary
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("📊 SCRAPING SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    logger.info("")
    
    success_count = sum(1 for v in results.values() if v)
    failed_count = sum(1 for v in results.values() if not v)
    
    logger.info(f"Results: {success_count} succeeded, {failed_count} failed")
    logger.info("")
    
    for tender_type, success in results.items():
        status_icon = "✅" if success else "❌"
        logger.info(f"{status_icon} {tender_type}")
    
    logger.info("=" * 70)
    logger.info("")
    logger.info("💡 Next step: Run detailed scraping if needed:")
    logger.info("   python3 update_all_tenders.py --detailed")
    logger.info("")

if __name__ == "__main__":
    main()
