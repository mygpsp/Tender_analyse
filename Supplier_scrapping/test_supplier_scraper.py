"""
Test script for supplier scraper.

Tests parsing rules by scraping first few suppliers and printing results.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from supplier_scraper import SupplierScraper, SupplierScraperConfig, load_config


async def test_parsing() -> None:
    """Test supplier scraping and parsing."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    
    log = logging.getLogger("test")
    
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Load configuration
    config_path = script_dir / "config" / "supplier_selectors.yaml"
    config_data = load_config(config_path)
    
    # Build test config - scrape only 1 page, non-headless to see what's happening
    scraper_config = SupplierScraperConfig(
        base_url=config_data["base_url"],
        headless=False,  # Show browser for testing
        max_pages=1,  # Only scrape first page
        output_path=script_dir / "data" / "test_suppliers.jsonl",
        page_pause_ms=1500  # Slower for observation
    )
    
    log.info("=" * 60)
    log.info("SUPPLIER SCRAPER TEST")
    log.info("=" * 60)
    log.info(f"Config: {config_path}")
    log.info(f"Output: {scraper_config.output_path}")
    log.info(f"Max pages: {scraper_config.max_pages}")
    log.info(f"Headless: {scraper_config.headless}")
    log.info("=" * 60)
    
    # Run scraper
    async with SupplierScraper(scraper_config, config_data) as scraper:
        await scraper.run()
    
    # Read and display results
    log.info("=" * 60)
    log.info("RESULTS")
    log.info("=" * 60)
    
    if scraper_config.output_path.exists():
        import json
        
        with open(scraper_config.output_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        log.info(f"Total suppliers scraped: {len(lines)}")
        log.info("")
        
        for idx, line in enumerate(lines[:5], 1):  # Show first 5
            supplier_data = json.loads(line)
            supplier = supplier_data.get("supplier", {})
            contact_persons = supplier_data.get("contact_persons", [])
            
            log.info(f"Supplier {idx}:")
            log.info(f"  Name: {supplier.get('name', 'N/A')}")
            log.info(f"  ID: {supplier.get('identification_code', 'N/A')}")
            log.info(f"  Country: {supplier.get('country', 'N/A')}")
            log.info(f"  City: {supplier.get('city_or_region', 'N/A')}")
            log.info(f"  Address: {supplier.get('legal_address', 'N/A')}")
            log.info(f"  Phone: {supplier.get('telephone', 'N/A')}")
            log.info(f"  Email: {supplier.get('email', 'N/A')}")
            log.info(f"  Website: {supplier.get('website', 'N/A')}")
            
            if contact_persons:
                log.info(f"  Contact Persons: {len(contact_persons)}")
                for cp_idx, cp in enumerate(contact_persons[:2], 1):
                    log.info(f"    {cp_idx}. {cp.get('full_name', 'N/A')} - {cp.get('position', 'N/A')}")
                    log.info(f"       Tel: {cp.get('telephone', 'N/A')}, Email: {cp.get('email', 'N/A')}")
            
            log.info("")
        
        if len(lines) > 5:
            log.info(f"... and {len(lines) - 5} more suppliers")
    else:
        log.warning("No output file created!")
    
    log.info("=" * 60)
    log.info("TEST COMPLETE")
    log.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_parsing())
