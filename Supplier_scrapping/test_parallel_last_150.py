#!/usr/bin/env python3
"""
Test scraping the last 150 suppliers with parallel connections.
"""

import asyncio
import logging
from pathlib import Path

from supplier_scraper import SupplierScraper, SupplierScraperConfig, load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)

log = logging.getLogger("test_parallel")


async def main():
    """Test parallel scraping of last 150 suppliers."""
    
    # Load configuration
    config_path = Path(__file__).parent / "config" / "supplier_selectors.yaml"
    config_data = load_config(config_path)
    
    # Output path
    output_path = Path(__file__).parent / "data" / "suppliers.jsonl"
    
    # Build config
    # Assuming ~20 suppliers per page, 150 suppliers = ~8 pages
    scraper_config = SupplierScraperConfig(
        base_url=config_data["base_url"],
        headless=False,  # Run in background
        max_pages=8,    # ~150 suppliers
        output_path=output_path,
        page_pause_ms=500  # Faster for testing
    )
    
    log.info("="*80)
    log.info("PARALLEL SCRAPING TEST - Last ~150 Suppliers")
    log.info("="*80)
    log.info(f"Config: {config_path}")
    log.info(f"Output: {output_path}")
    log.info(f"Workers: 10")
    log.info(f"Max pages: {scraper_config.max_pages}")
    log.info(f"Headless: {scraper_config.headless}")
    log.info("="*80)
    
    # Create scraper and run parallel scraping
    async with SupplierScraper(scraper_config, config_data) as scraper:
        total_scraped = await scraper.scrape_parallel(
            max_pages=scraper_config.max_pages,
            concurrency=10
        )
    
    log.info("="*80)
    log.info("SCRAPING COMPLETED")
    log.info(f"Total suppliers scraped: {total_scraped}")
    log.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())

