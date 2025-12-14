#!/usr/bin/env python3
"""
Production runner for detailed scraper.
Filters tenders from main data and scrapes details in parallel.
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path to allow imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from detailed_scraper.filter_tenders import filter_tenders
from detailed_scraper.detail_scraper import (
    DetailedTenderScraper, 
    DetailScraperConfig, 
    DetailSelectors,
    JsonLinesWriter,
    build_configs
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("detailed_scraper.log")
    ]
)
logger = logging.getLogger("run_detailed_production")

async def main():
    parser = argparse.ArgumentParser(description="Run detailed scraper in production mode")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of parallel workers")
    parser.add_argument("--info", action="store_true", help="Show count of matching tenders without scraping")
    parser.add_argument("--tenders", nargs="+", help="Specific tender numbers to scrape (overrides date filter)")
    parser.add_argument("--test", action="store_true", help="Run on top 10 tenders only")
    parser.add_argument("--days", type=int, default=60, help="Filter tenders within N days (default: 60)")
    parser.add_argument("--date-from", help="Start date (YYYY-MM-DD) or 'today'")
    parser.add_argument("--date-to", help="End date (YYYY-MM-DD) or 'today'")
    parser.add_argument("--clear", action="store_true", help="Clear existing detailed data before starting")
    parser.add_argument("--force", action="store_true", help="Force re-scrape of existing tenders")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no browser UI)")
    parser.add_argument("--no-headless", action="store_true", help="Run with browser UI visible")
    parser.add_argument("--tender-type", type=str, help="Tender type for output file (CON, NAT, SPA, etc.). Determines output filename.")
    
    args = parser.parse_args()
    
    # Paths
    main_data_path = project_root / "main_scrapper" / "data" / "tenders.jsonl"
    
    # Determine output file based on tender type
    if args.tender_type:
        # Use type-specific file: con_detailed_tenders.jsonl, nat_detailed_tenders.jsonl, etc.
        output_filename = f"{args.tender_type.lower()}_detailed_tenders.jsonl"
    else:
        # Default to main detailed file
        output_filename = "detailed_tenders.jsonl"
    
    output_path = project_root / "main_scrapper" / "data" / output_filename
    config_path = project_root / "detailed_scraper" / "config.yaml"
    
    logger.info(f"🚀 Starting detailed scraper production run")
    logger.info(f"   Source: {main_data_path}")
    logger.info(f"   Output: {output_path}")
    logger.info(f"   Concurrency: {args.concurrency}")
    logger.info(f"   Headless: {args.headless}")
    
    # 1. Filter/Select Tenders
    tenders_to_scrape = []
    
    if args.tenders:
        logger.info(f"Step 1: Using {len(args.tenders)} specific tenders provided by user")
        # For specific tenders, we try to find them in main data to get IDs, but if not found, we scrape anyway
        # We need to load main data to look them up
        logger.info("Looking up details for specific tenders in main data...")
        from detailed_scraper.detail_scraper import load_tender_id_from_main_data
        
        for tender_num in args.tenders:
            tender_info = load_tender_id_from_main_data(tender_num, main_data_path)
            if tender_info:
                tenders_to_scrape.append({
                    "tender_number": tender_num,
                    "tender_id": tender_info.get("tender_id"),
                    "detail_url": tender_info.get("detail_url")
                })
            else:
                # Not found in main data, add with just number
                tenders_to_scrape.append({"tender_number": tender_num})
                
    else:
        logger.info("Step 1: Filtering tenders from main data...")
        tenders = filter_tenders(
            main_data_path, 
            days_threshold=args.days,
            date_from=args.date_from,
            date_to=args.date_to
        )
        
        if not tenders:
            logger.error("No tenders found matching criteria!")
            return
            
        logger.info(f"Found {len(tenders)} tenders matching criteria.")
        
        # Convert to format expected by scraper
        for t in tenders:
            tenders_to_scrape.append({
                "tender_number": t.get("number") or t.get("tender_number"),
                "tender_id": t.get("tender_id"),
                "detail_url": t.get("detail_url")
            })
            
        # Test Mode Handling (only if not using specific tenders)
        if args.test:
            logger.info("🧪 TEST MODE: Taking top 10 tenders only")
            tenders_to_scrape = tenders_to_scrape[:10]

    # 2. Info Mode
    if args.info:
        logger.info("=" * 60)
        logger.info("ℹ️  INFO MODE")
        logger.info("=" * 60)
        logger.info(f"Total tenders to scrape: {len(tenders_to_scrape)}")
        if len(tenders_to_scrape) > 0:
            logger.info("Sample tenders:")
            for t in tenders_to_scrape[:5]:
                logger.info(f"  - {t['tender_number']}")
        logger.info("=" * 60)
        return

    # 3. Clear Output if requested
    if args.clear and output_path.exists():
        logger.info(f"Clearing existing output file: {output_path}")
        backup_path = output_path.with_suffix('.bak')
        import shutil
        shutil.copy(output_path, backup_path)
        logger.info(f"Created backup at {backup_path}")
        output_path.write_text("", encoding="utf-8")
        
    # 4. Run Scraper
    logger.info(f"Step 2: Starting scrape for {len(tenders_to_scrape)} tenders...")
    
    # Create config manually or load from file
    # We'll use build_configs but override some values
    class MockArgs:
        config = str(config_path)
        headless = args.headless
        page_pause_ms = 1000
        output = str(output_path)
        
    scraper_config, selectors = build_configs(config_path, MockArgs())
    
    # Override output path to be sure
    scraper_config.output_path = output_path
    
    # Initialize parallel scraper
    from playwright.async_api import async_playwright
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=args.headless)
    
    try:
        writer = JsonLinesWriter(output_path)
        scraper = DetailedTenderScraper(scraper_config, selectors, browser=browser, writer=writer)
        
        # We need to access scrape_multiple_parallel. 
        # Pass force argument to control re-scraping behavior
        results = await scraper.scrape_multiple_parallel(tenders_to_scrape, args.concurrency, force=args.force)
        
        logger.info("=" * 60)
        logger.info(f"✅ Scraping Complete!")
        logger.info(f"   Total attempted: {len(tenders_to_scrape)}")
        logger.info(f"   Successfully scraped: {len(results)}")
        logger.info(f"   Output file: {output_path}")
        logger.info("=" * 60)
        
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())
