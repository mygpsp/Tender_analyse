#!/usr/bin/env python3
"""
Debug script to inspect modal content and selectors.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from supplier_scraper import SupplierScraper, SupplierScraperConfig, load_config


async def debug_modal():
    """Debug modal content."""
    
    config_path = Path(__file__).parent / "config" / "supplier_selectors.yaml"
    config_data = load_config(config_path)
    
    scraper_config = SupplierScraperConfig(
        base_url=config_data["base_url"],
        headless=False,
        max_pages=1,
        output_path=Path(__file__).parent / "data" / "test_contact.jsonl",
        page_pause_ms=1500
    )
    
    test_supplier_id = "206178447"
    
    async with SupplierScraper(scraper_config, config_data) as scraper:
        page = scraper.page
        selectors = scraper.selectors
        
        # Navigate
        print(f"Navigating to {scraper_config.base_url}")
        await page.goto(scraper_config.base_url, wait_until="networkidle")
        
        await page.click(selectors["navigation"]["users_button"])
        await asyncio.sleep(1)
        
        await page.click(selectors["navigation"]["suppliers_tab"])
        await asyncio.sleep(1)
        
        await page.wait_for_selector(selectors["supplier_list"]["table_rows"], state="visible")
        
        # Search
        print(f"Searching for {test_supplier_id}")
        await page.fill("#search_org > input[type=text]:nth-child(4)", test_supplier_id)
        await asyncio.sleep(0.5)
        await page.click("#search_org_btn > span.ui-button-text")
        await asyncio.sleep(2)
        
        # Click
        print("Clicking on result")
        await page.locator("table#list_orgs tbody tr").first.click()
        await asyncio.sleep(2)
        
        # Debug modal
        print("\n" + "="*80)
        print("MODAL DEBUG")
        print("="*80)
        
        # Check modal title
        title_selector = selectors["modal"]["title"]
        print(f"\nTitle selector: {title_selector}")
        title_elements = await page.locator(title_selector).all()
        print(f"Found {len(title_elements)} title elements")
        for i, elem in enumerate(title_elements):
            text = await elem.text_content()
            print(f"  Title {i}: {text}")
        
        # Check for contact persons tab
        print("\nLooking for contact persons tab...")
        contact_tab = page.locator("a:has-text('საკონტაქტო პირები')")
        count = await contact_tab.count()
        print(f"Found {count} contact person tabs")
        
        # Check the specific location user mentioned
        print("\nChecking #profile_dialog > div:nth-child(2) > table...")
        contact_table = page.locator("#profile_dialog > div:nth-child(2) > table")
        table_count = await contact_table.count()
        print(f"Found {table_count} tables at that location")
        
        if table_count > 0:
            print("\nContact persons table found! Extracting data...")
            
            # Get header
            header = await contact_table.locator("thead tr td").all()
            print(f"Header cells: {len(header)}")
            for i, cell in enumerate(header):
                text = await cell.text_content()
                print(f"  Header {i}: {text}")
            
            # Get rows
            rows = await contact_table.locator("tbody tr").all()
            print(f"\nFound {len(rows)} contact person rows")
            
            for i, row in enumerate(rows):
                cells = await row.locator("td").all()
                print(f"\n  Row {i}: {len(cells)} cells")
                for j, cell in enumerate(cells):
                    text = await cell.text_content()
                    print(f"    Cell {j}: {text}")
        
        if count > 0:
            print("Clicking contact persons tab...")
            await contact_tab.first.click()
            await asyncio.sleep(1)
            
            # Check table
            rows = await page.locator("table tbody tr").all()
            print(f"Found {len(rows)} rows in contact persons table")
            
            for i, row in enumerate(rows):
                cells = await row.locator("td").all()
                print(f"\n  Row {i}: {len(cells)} cells")
                for j, cell in enumerate(cells):
                    text = await cell.text_content()
                    print(f"    Cell {j}: {text}")
        else:
            print("No contact persons tab found")
        
        # Get all tab names
        print("\nAll tabs:")
        tabs = await page.locator("a[role='tab'], .ui-tabs-nav a").all()
        for i, tab in enumerate(tabs):
            text = await tab.text_content()
            print(f"  Tab {i}: {text}")
        
        print("\nKeeping browser open for 30 seconds...")
        await page.wait_for_timeout(30000)


if __name__ == "__main__":
    asyncio.run(debug_modal())
