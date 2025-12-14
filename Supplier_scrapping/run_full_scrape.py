import asyncio
import logging
import argparse
import sys
import os
from datetime import datetime

from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supplier_scraper import SupplierScraper, SupplierScraperConfig, load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("full_scrape.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("full_scrape")

async def main():
    parser = argparse.ArgumentParser(description="Run full supplier scraping")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--max-pages", type=int, default=4200, help="Maximum pages to scrape (default covers all)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    parser.add_argument("--visible", action="store_false", dest="headless", help="Run in visible mode")
    parser.add_argument("--output", type=str, default="data/suppliers.jsonl", help="Output file path")
    
    args = parser.parse_args()
    
    # Load config
    config_path = Path(os.path.join(os.path.dirname(__file__), "config/supplier_selectors.yaml"))
    config_data = load_config(config_path)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Build scraper config
    scraper_config = SupplierScraperConfig(
        base_url=config_data["base_url"],
        headless=args.headless,
        max_pages=args.max_pages,
        output_path=Path(args.output),
        page_pause_ms=1000  # Slightly slower for stability during long run
    )
    
    log.info("="*80)
    log.info("FULL SCALE SUPPLIER SCRAPING")
    log.info("="*80)
    log.info(f"Output: {args.output}")
    log.info(f"Workers: {args.concurrency}")
    log.info(f"Max pages: {args.max_pages}")
    log.info(f"Headless: {args.headless}")
    log.info("="*80)
    
    scraper = SupplierScraper(scraper_config, config_data)
    
    start_time = datetime.now()
    
    async with scraper:
        total_scraped = await scraper.scrape_parallel(
            max_pages=scraper_config.max_pages,
            concurrency=args.concurrency
        )
        
    end_time = datetime.now()
    duration = end_time - start_time
    
    log.info("="*80)
    log.info("SCRAPING COMPLETED")
    log.info(f"Total suppliers scraped: {total_scraped}")
    log.info(f"Duration: {duration}")
    log.info("="*80)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Scraping interrupted by user")
    except Exception as e:
        log.exception(f"Fatal error: {e}")
