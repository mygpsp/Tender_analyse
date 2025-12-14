import asyncio
from playwright.async_api import async_playwright

async def inspect_pagination():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating...")
        await page.goto("http://tenders.procurement.gov.ge/public/?go", wait_until="networkidle")
        
        print("Clicking Users...")
        await page.click("button#btn_org")
        await asyncio.sleep(1)
        
        print("Clicking Suppliers...")
        await page.click("button#b3")
        await asyncio.sleep(2)
        
        print("Waiting for table...")
        await page.wait_for_selector("table#list_orgs", state="visible")
        
        # Try to jump to page 5 using jqGrid method
        print("Attempting to jump to page 5 using jqGrid trigger...")
        try:
            # Check if jQuery is available
            has_jquery = await page.evaluate("typeof jQuery !== 'undefined'")
            print(f"Has jQuery: {has_jquery}")
            
            if has_jquery:
                # Get current page
                curr_page = await page.evaluate("jQuery('#list_orgs').getGridParam('page')")
                print(f"Current page (from grid param): {curr_page}")
                
                # Trigger reload with page 5
                await page.evaluate("jQuery('#list_orgs').setGridParam({page: 5}).trigger('reloadGrid')")
                await asyncio.sleep(3)
                
                # Check new page
                new_page = await page.evaluate("jQuery('#list_orgs').getGridParam('page')")
                print(f"New page (from grid param): {new_page}")
                
                # Get first supplier name to verify content changed
                name = await page.locator("td:nth-child(1) span").first.text_content()
                print(f"First supplier on page {new_page}: {name}")
                
            else:
                print("jQuery not found!")
                
        except Exception as e:
            print(f"Error executing JS: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_pagination())
