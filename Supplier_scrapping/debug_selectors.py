"""
Debug script to inspect the actual page structure after clicking Suppliers tab.
"""

import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright


async def debug_page_structure():
    """Debug the page structure to find correct selectors."""
    
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("debug")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Navigate
        log.info("Navigating to main page...")
        await page.goto("http://tenders.procurement.gov.ge/public/?go")
        await page.wait_for_load_state("networkidle")
        
        # Click Users
        log.info("Clicking Users button...")
        await page.click("button#btn_org")
        await asyncio.sleep(2)
        
        # Click Suppliers
        log.info("Clicking Suppliers tab...")
        await page.click("button#b3")
        await asyncio.sleep(5)  # Wait longer
        
        # Take screenshot
        screenshot_path = Path(__file__).parent / "debug_screenshot.png"
        await page.screenshot(path=str(screenshot_path))
        log.info(f"Screenshot saved to {screenshot_path}")
        
        # Get page content
        content = await page.content()
        html_path = Path(__file__).parent / "debug_page.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(content)
        log.info(f"HTML saved to {html_path}")
        
        # Try to find table elements
        log.info("\nLooking for table elements...")
        
        # Try different selectors
        selectors_to_try = [
            "div#org_list_div",
            "div#org_list_div table",
            "div#org_list_div table tbody",
            "div#org_list_div table tbody tr",
            "table",
            "tbody tr",
        ]
        
        for selector in selectors_to_try:
            try:
                count = await page.locator(selector).count()
                log.info(f"  {selector}: {count} elements found")
                
                if count > 0 and "tr" in selector:
                    # Get first row text
                    first = page.locator(selector).first
                    text = await first.text_content()
                    log.info(f"    First element text: {text[:100]}...")
            except Exception as e:
                log.info(f"  {selector}: ERROR - {e}")
        
        # Keep browser open for manual inspection
        log.info("\nBrowser will stay open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_page_structure())
