#!/usr/bin/env python3
"""
Inspect the tender search page to find correct selectors for dropdowns.
"""
import asyncio
from playwright.async_api import async_playwright


async def inspect_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("Navigating to tender portal...")
        await page.goto("https://tenders.procurement.gov.ge/public/?lang=ge")
        await page.wait_for_load_state("networkidle")
        
        print("\nLooking for tender type dropdown...")
        # Try different selectors
        selectors_to_try = [
            'select[name="search[tender_type]"]',
            '#search_tender_type',
            'button[data-id="search_tender_type"]',
            '.bootstrap-select button[title*="ტიპი"]',
            'select#search_tender_type',
        ]
        
        for selector in selectors_to_try:
            try:
                element = await page.query_selector(selector)
                if element:
                    print(f"  ✅ Found with selector: {selector}")
                    html = await element.evaluate('el => el.outerHTML')
                    print(f"     HTML: {html[:200]}")
            except:
                pass
        
        print("\nLooking for category dropdown...")
        category_selectors = [
            'select[name="search[category]"]',
            '#search_category',
            'button[data-id="search_category"]',
            '.bootstrap-select button[title*="კატეგორია"]',
            'select#search_category',
        ]
        
        for selector in category_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    print(f"  ✅ Found with selector: {selector}")
                    html = await element.evaluate('el => el.outerHTML')
                    print(f"     HTML: {html[:200]}")
            except:
                pass
        
        print("\nPress Enter to close browser...")
        input()
        await browser.close()


if __name__ == '__main__':
    asyncio.run(inspect_page())
