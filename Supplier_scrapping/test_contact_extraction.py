#!/usr/bin/env python3
"""
Test contact person extraction for a specific supplier.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from supplier_scraper import SupplierScraper, SupplierScraperConfig, load_config


async def test_contact_extraction():
    """Test contact person extraction by scraping one supplier."""
    
    # Load configuration
    config_path = Path(__file__).parent / "config" / "supplier_selectors.yaml"
    config_data = load_config(config_path)
    
    # Build config
    scraper_config = SupplierScraperConfig(
        base_url=config_data["base_url"],
        headless=False,  # Show browser
        max_pages=1,
        output_path=Path(__file__).parent / "data" / "test_contact.jsonl",
        page_pause_ms=1500
    )
    
    # Supplier ID to test
    test_supplier_id = "222725807"
    
    # Initialize scraper
    async with SupplierScraper(scraper_config, config_data) as scraper:
        page = scraper.page
        selectors = scraper.selectors
        
        # Navigate to base URL
        print(f"Navigating to {scraper_config.base_url}")
        await page.goto(scraper_config.base_url, wait_until="networkidle")
        
        # Click Users button
        print("Clicking Users button")
        users_button = selectors["navigation"]["users_button"]
        await page.wait_for_selector(users_button, state="visible")
        await page.click(users_button)
        await asyncio.sleep(1)
        
        # Click Suppliers tab
        print("Clicking Suppliers tab")
        suppliers_tab = selectors["navigation"]["suppliers_tab"]
        await page.wait_for_selector(suppliers_tab, state="visible")
        await page.click(suppliers_tab)
        await asyncio.sleep(1)
        
        # Wait for table
        print("Waiting for supplier table")
        table_rows_selector = selectors["supplier_list"]["table_rows"]
        await page.wait_for_selector(table_rows_selector, state="visible", timeout=5000)
        
        # Search for specific supplier
        print(f"Searching for supplier ID: {test_supplier_id}")
        search_input = "#search_org > input[type=text]:nth-child(4)"
        search_button = "#search_org_btn > span.ui-button-text"
        
        await page.wait_for_selector(search_input, state="visible")
        await page.fill(search_input, test_supplier_id)
        await asyncio.sleep(0.5)
        
        await page.click(search_button)
        await asyncio.sleep(2)
        
        # Click on the first (should be only) result
        print("Extracting data from table row...")
        first_row = page.locator("table#list_orgs tbody tr").first
        
        # Extract metadata from table row before clicking
        cells = await first_row.locator("td").all()
        supplier_name = ""
        registration_date = ""
        supplier_type = ""
        
        if len(cells) >= 3:
            # First cell contains the name
            name_element = cells[0].locator("span")
            supplier_name = await name_element.text_content() or ""
            supplier_name = supplier_name.strip()
            
            # Second cell is registration date
            registration_date = await cells[1].text_content() or ""
            registration_date = registration_date.strip()
            
            # Third cell is supplier/buyer type
            supplier_type = await cells[2].text_content() or ""
            supplier_type = supplier_type.strip()
            
            print(f"  Name: {supplier_name}")
            print(f"  Registration Date: {registration_date}")
            print(f"  Type: {supplier_type}")
        
        # Now click to open modal
        print("Clicking on search result...")
        await first_row.click()
        await asyncio.sleep(2)
        
        # Wait for modal to appear
        print("Waiting for modal to open...")
        modal_selector = selectors["modal"]["dialog"]
        try:
            await page.wait_for_selector(modal_selector, state="visible", timeout=5000)
            print("Modal opened successfully")
        except Exception as e:
            print(f"Warning: Could not detect modal: {e}")
        
        # Take a screenshot for debugging
        await page.screenshot(path="debug_modal.png")
        print("Screenshot saved to debug_modal.png")
        
        # Parse supplier data (correct method name is parse_profile)
        print("Parsing supplier data...")
        supplier_data = await scraper.parser.parse_profile(
            page,
            supplier_name=supplier_name,
            registration_date=registration_date,
            supplier_type=supplier_type
        )
        
        # Print raw data for debugging
        import json
        print("\nRaw supplier data:")
        print(json.dumps(supplier_data, indent=2, ensure_ascii=False))
        
        # Print results
        print("\n" + "="*80)
        print("SUPPLIER DATA")
        print("="*80)
        print(f"Name: {supplier_data.get('supplier', {}).get('name')}")
        print(f"ID: {supplier_data.get('supplier', {}).get('identification_code')}")
        
        contact_persons = supplier_data.get('contact_persons', [])
        print(f"\nContact Persons: {len(contact_persons)}")
        
        if contact_persons:
            for i, person in enumerate(contact_persons, 1):
                print(f"\n  Person {i}:")
                print(f"    Name: {person.get('full_name')}")
                print(f"    Position: {person.get('position')}")
                print(f"    Phone: {person.get('telephone')}")
                print(f"    Email: {person.get('email')}")
        else:
            print("  No contact persons found")
        
        print("\n" + "="*80)
        
        # Keep browser open for inspection
        print("\nBrowser will stay open for 10 seconds for inspection...")
        await page.wait_for_timeout(10000)


if __name__ == "__main__":
    asyncio.run(test_contact_extraction())
