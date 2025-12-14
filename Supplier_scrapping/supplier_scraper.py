"""
Supplier Scraper

Scrapes supplier profile data from Georgian procurement website.
Navigates to Users -> Suppliers section and extracts supplier information.
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from playwright.async_api import Browser, Page, async_playwright

from supplier_parser import SupplierParser

# ---------------------------------------------------------------------------
# Helper class for round‑robin page assignment in parallel mode
# ---------------------------------------------------------------------------
class PageScheduler:
    """Compute the next page number for each worker.

    Each worker receives a distinct sequence of pages:
    worker 1 → 1, 1+N, 1+2N, ...
    worker 2 → 2, 2+N, 2+2N, ...
    where N is the total number of workers.
    """
    def __init__(self, max_pages: int, workers: int):
        self.max_pages = max_pages
        self.workers = workers
        # Initialise next page for each worker (1‑based indexing)
        self.next_page = {worker_id: worker_id for worker_id in range(1, workers + 1)}

    def get_next(self, worker_id: int) -> int | None:
        """Return the next page for *worker_id* or ``None`` if all pages are exhausted."""
        page = self.next_page[worker_id]
        if page > self.max_pages:
            return None
        # Prepare next page for this worker
        self.next_page[worker_id] = page + self.workers
        return page



@dataclass
class SupplierScraperConfig:
    """Configuration for supplier scraper."""
    base_url: str
    headless: bool
    max_pages: int
    output_path: Path
    page_pause_ms: int


class JsonLinesWriter:
    """Writes records to JSON Lines file with thread-safe locking."""
    
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = asyncio.Lock()
    
    async def write(self, record: Dict[str, Any]) -> None:
        """Write a single record to the file (thread-safe)."""
        async with self.lock:
            with self.output_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")


class SupplierScraper:
    """Main scraper class for supplier data."""
    
    def __init__(
        self, 
        config: SupplierScraperConfig, 
        selectors: Dict[str, Any],
        browser: Optional[Browser] = None,
        page: Optional[Page] = None,
        writer: Optional[JsonLinesWriter] = None
    ):
        """
        Initialize scraper.
        
        Args:
            config: Scraper configuration
            selectors: CSS/XPath selectors from YAML config
            browser: Optional shared browser instance (for parallel mode)
            page: Optional page instance (for workers)
            writer: Optional shared writer (for parallel mode)
        """
        self.cfg = config
        self.selectors = selectors
        self.browser = browser
        self.page = page
        self.playwright = None
        self.writer = writer or JsonLinesWriter(config.output_path)
        self.parser = SupplierParser(selectors)
        self.log = logging.getLogger("supplier_scraper")
        self.existing_suppliers: Set[str] = set()
    
    async def __aenter__(self) -> "SupplierScraper":
        """Async context manager entry."""
        if not self.browser:
            self.log.debug("Launching browser (headless=%s)", self.cfg.headless)
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.cfg.headless)
        
        if not self.page:
            context = await self.browser.new_context()
            self.page = await context.new_page()
        
        # Initialise page tracking
        self.current_page = 1
        return self
    
    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def load_existing_suppliers(self) -> Set[str]:
        """Load existing supplier IDs from output file to skip duplicates."""
        existing = set()
        if not self.cfg.output_path.exists():
            return existing
        
        try:
            with open(self.cfg.output_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        supplier = record.get("supplier", {})
                        supplier_id = supplier.get("identification_code")
                        if supplier_id:
                            existing.add(supplier_id)
                    except:
                        pass
            
            self.log.info(f"Loaded {len(existing)} existing suppliers")
        except Exception as e:
            self.log.warning(f"Error loading existing suppliers: {e}")
        
        return existing
    
    async def run(self) -> None:
        """Main scraping workflow."""
        assert self.page is not None
        
        # Load existing suppliers to skip
        self.existing_suppliers = self.load_existing_suppliers()
        
        # Step 1: Navigate to base URL
        self.log.info(f"Navigating to {self.cfg.base_url}")
        await self.page.goto(self.cfg.base_url, wait_until="networkidle")
        
        # Step 2: Click Users button
        self.log.info("Clicking Users button")
        users_button = self.selectors["navigation"]["users_button"]
        await self.page.wait_for_selector(users_button, state="visible")
        await self.page.click(users_button)
        await asyncio.sleep(self.cfg.page_pause_ms / 1000)
        
        # Step 3: Click Suppliers tab
        self.log.info("Clicking Suppliers tab")
        suppliers_tab = self.selectors["navigation"]["suppliers_tab"]
        await self.page.wait_for_selector(suppliers_tab, state="visible")
        await self.page.click(suppliers_tab)
        await asyncio.sleep(self.cfg.page_pause_ms / 1000)
        
        # Step 4: Wait for supplier table to load with retry
        self.log.info("Waiting for supplier table")
        table_rows_selector = self.selectors["supplier_list"]["table_rows"]
        
        # Try multiple times as the table loads dynamically
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Wait for at least one row to appear
                await self.page.wait_for_selector(table_rows_selector, state="visible", timeout=5000)
                self.log.debug("Supplier table loaded successfully")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    self.log.debug(f"Table not loaded yet (attempt {attempt + 1}/{max_retries}), retrying...")
                    await asyncio.sleep(2)
                else:
                    self.log.error(f"Failed to load supplier table after {max_retries} attempts")
                    raise

        
        # Step 5: Scrape suppliers page by page
        page_num = 1
        while page_num <= self.cfg.max_pages:
            self.log.info(f"Scraping page {page_num}")
            
            scraped_count = await self.scrape_current_page()
            self.log.info(f"Scraped {scraped_count} suppliers from page {page_num}")
            
            # Try to go to next page
            if not await self.go_to_next_page():
                self.log.info("No more pages available")
                break
            
            page_num += 1
            await asyncio.sleep(self.selectors["timing"]["between_pages_ms"] / 1000)
        
        self.log.info("Scraping completed")
    
    async def scrape_current_page(self) -> int:
        """
        Scrape all suppliers on current page.
        
        Returns:
            Number of suppliers scraped
        """
        assert self.page is not None
        
        # Get all supplier rows
        rows_selector = self.selectors["supplier_list"]["table_rows"]
        rows = await self.page.locator(rows_selector).all()
        
        self.log.debug(f"Found {len(rows)} rows on current page")
        scraped = 0
        
        for idx, row in enumerate(rows):
            try:
                # Extract data from table row cells
                cells = await row.locator("td").all()
                
                if len(cells) < 3:
                    continue
                
                # Extract supplier name from first cell
                name_cell_selector = self.selectors["supplier_list"]["supplier_name_cell"]
                name_element = row.locator(name_cell_selector)
                supplier_name = await name_element.text_content()
                
                if not supplier_name or not supplier_name.strip():
                    continue
                
                supplier_name = supplier_name.strip()
                
                # Extract registration date from second cell
                registration_date = await cells[1].text_content()
                registration_date = (registration_date or "").strip()
                
                # Extract supplier/buyer type from third cell
                supplier_type = await cells[2].text_content()
                supplier_type = (supplier_type or "").strip()
                
                self.log.debug(f"Processing supplier {idx + 1}: {supplier_name} (Registered: {registration_date}, Type: {supplier_type})")
                
                # Click on supplier name to open modal
                await name_element.click()
                await asyncio.sleep(self.selectors["timing"]["between_clicks_ms"] / 1000)
                
                # Parse profile from modal, passing metadata from table
                profile = await self.parser.parse_profile(
                    self.page, 
                    supplier_name=supplier_name,
                    registration_date=registration_date,
                    supplier_type=supplier_type
                )
                
                # Check if already scraped
                supplier_id = profile.get("supplier", {}).get("identification_code", "")
                if supplier_id in self.existing_suppliers:
                    self.log.debug(f"Skipping already scraped supplier: {supplier_id}")
                    await self.close_modal()
                    continue
                
                # Validate profile
                if not self.parser.validate_profile(profile):
                    self.log.warning(f"Invalid profile for {supplier_name}, skipping")
                    await self.close_modal()
                    continue
                
                # Add timestamp
                profile["scraped_at"] = datetime.now().isoformat()
                
                # Write to file
                await self.writer.write(profile)
                self.existing_suppliers.add(supplier_id)
                scraped += 1
                
                supplier_display_name = profile.get("supplier", {}).get("name", supplier_name)
                self.log.info(f"✓ Scraped supplier: {supplier_display_name} ({supplier_id})")
                
                # Close modal
                await self.close_modal()
                
            except Exception as e:
                self.log.error(f"Error scraping supplier {idx + 1}: {e}")
                # Try to close modal if it's open
                try:
                    await self.close_modal()
                except:
                    pass
                continue
        
        return scraped
    
    async def go_to_prev_page(self) -> bool:
        """
        Navigate to previous page of suppliers.
        
        Returns:
            True if successfully moved to prev page, False if no more pages
        """
        assert self.page is not None
        
        try:
            prev_button = self.selectors["pagination"]["prev_button"]
            
            # Check if prev button exists and is enabled
            prev_btn = self.page.locator(prev_button)
            if await prev_btn.count() == 0:
                return False
            
            # Check if button is disabled
            is_disabled = await prev_btn.get_attribute("disabled")
            if is_disabled:
                return False
            
            # Click prev button
            await prev_btn.click()
            await asyncio.sleep(self.selectors["timing"]["between_pages_ms"] / 1000)
            
            # Wait for table to reload
            table_container = self.selectors["supplier_list"]["table_container"]
            await self.page.wait_for_selector(table_container, state="visible")
            
            return True
            
        except Exception as e:
            self.log.debug(f"Could not go to prev page: {e}")
            return False

    async def go_to_last_page(self) -> bool:
        """
        Navigate to the last page of suppliers.
        
        Returns:
            True if successful
        """
        assert self.page is not None
        
        try:
            last_button = self.selectors["pagination"]["last_button"]
            
            # Check if last button exists
            last_btn = self.page.locator(last_button)
            if await last_btn.count() == 0:
                return False
            
            self.log.info("Clicking Last Page button")
            await last_btn.click()
            await asyncio.sleep(self.selectors["timing"]["between_pages_ms"] / 1000)
            
            # Wait for table to reload
            table_container = self.selectors["supplier_list"]["table_container"]
            await self.page.wait_for_selector(table_container, state="visible")
            
            return True
            
        except Exception as e:
            self.log.error(f"Could not go to last page: {e}")
            return False

    async def _go_to_page(self, target_page: int) -> bool:
        """Navigate from the current page to *target_page* using next clicks.

        Returns True if the target page was reached, False otherwise.
        """
        assert self.page is not None
        # Use the instance's current_page tracking
        while self.current_page < target_page:
            if not await self.go_to_next_page():
                self.log.warning(f"Failed to navigate to page {target_page} (stuck at {self.current_page})")
                return False
            self.current_page += 1
        return True

    async def scrape_worker(self, worker_id: int, scheduler: "PageScheduler", existing_suppliers: Set[str]) -> int:
        """Worker for parallel scraping using round‑robin PageScheduler.

        Args:
            worker_id: Identifier of the worker (1‑based).
            scheduler: Shared PageScheduler instance.
            existing_suppliers: Set of already scraped supplier IDs.
        """
        assert self.page is not None
        self.existing_suppliers = existing_suppliers
        
        # -------------------------------------------------------------------
        # RESTORED INITIALIZATION LOGIC
        # -------------------------------------------------------------------
        try:
            # Navigate to the suppliers page
            self.log.info(f"[{worker_id}] Navigating to supplier list")
            await self.page.goto(self.cfg.base_url, wait_until="networkidle")
            
            # Click Users button
            users_button = self.selectors["navigation"]["users_button"]
            await self.page.wait_for_selector(users_button, state="visible")
            await self.page.click(users_button)
            await asyncio.sleep(self.cfg.page_pause_ms / 1000)
            
            # Click Suppliers tab
            suppliers_tab = self.selectors["navigation"]["suppliers_tab"]
            await self.page.wait_for_selector(suppliers_tab, state="visible")
            await self.page.click(suppliers_tab)
            await asyncio.sleep(self.cfg.page_pause_ms / 1000)
            
            # Wait for table to load
            table_rows_selector = self.selectors["supplier_list"]["table_rows"]
            await self.page.wait_for_selector(table_rows_selector, state="visible", timeout=10000)
            
            # Reset current page tracker for this worker
            self.current_page = 1
            
        except Exception as e:
            self.log.error(f"[{worker_id}] Initialization failed: {e}")
            return 0
            
        total_scraped = 0
        while True:
            page_num = scheduler.get_next(worker_id)
            if page_num is None:
                break
            self.log.info(f"[{worker_id}] Scraping page {page_num}")
            
            # Navigate to target page
            if not await self._go_to_page(page_num):
                self.log.warning(f"[{worker_id}] Could not reach page {page_num}, stopping worker")
                break
                
            count = await self.scrape_current_page()
            total_scraped += count
            self.log.info(f"[{worker_id}] Scraped {count} from page {page_num}")
        return total_scraped


    
    async def close_modal(self) -> None:
        """Close supplier profile modal."""
        assert self.page is not None
        
        close_button = self.selectors["modal"]["close_button"]
        try:
            # Try to find and click close button
            await self.page.click(close_button, timeout=2000)
            await asyncio.sleep(0.5)
        except Exception as e:
            self.log.debug(f"Could not close modal with button: {e}")
            # Try pressing Escape key as fallback
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
    
    async def go_to_next_page(self) -> bool:
        """
        Navigate to next page of suppliers.
        
        Returns:
            True if successfully moved to next page, False if no more pages
        """
        assert self.page is not None
        
        try:
            next_button = self.selectors["pagination"]["next_button"]
            
            # Check if next button exists and is enabled
            next_btn = self.page.locator(next_button)
            if await next_btn.count() == 0:
                return False
            
            # Check if button is disabled
            is_disabled = await next_btn.get_attribute("disabled")
            if is_disabled:
                return False
            
            # Click next button
            await next_btn.click()
            await asyncio.sleep(self.selectors["timing"]["between_pages_ms"] / 1000)
            
            # Wait for table to reload
            table_container = self.selectors["supplier_list"]["table_container"]
            await self.page.wait_for_selector(table_container, state="visible")
            
            return True
            
        except Exception as e:
            self.log.debug(f"Could not go to next page: {e}")
            return False
    
    async def scrape_parallel(
        self,
        max_pages: int,
        concurrency: int
    ) -> int:
        """
        Scrape multiple pages in parallel using round-robin page assignment.
        
        Args:
            max_pages: Maximum number of pages to scrape
            concurrency: Number of parallel workers
        
        Returns:
            Total number of suppliers scraped
        """
        assert self.browser is not None
        
        # Load existing suppliers once
        existing_suppliers = self.load_existing_suppliers()
        
        self.log.info(f"Starting parallel scraping: {max_pages} pages with {concurrency} workers")
        
        # Initialise scheduler for round-robin distribution
        scheduler = PageScheduler(max_pages, concurrency)
        
        async def worker_wrapper(worker_id: int) -> int:
            """Wrapper for each worker identified by *worker_id* (1-based)."""
            try:
                # Create new context and page for this worker
                context = await self.browser.new_context()
                page = await context.new_page()
                
                # Create scraper instance for this worker (shares writer)
                worker_scraper = SupplierScraper(
                    self.cfg,
                    self.selectors,
                    browser=self.browser,
                    page=page,
                    writer=self.writer
                )
                
                try:
                    count = await worker_scraper.scrape_worker(worker_id, scheduler, existing_suppliers)
                    return count
                finally:
                    # Cleanup resources
                    try:
                        await asyncio.wait_for(page.close(), timeout=2.0)
                    except Exception:
                        pass
                    try:
                        await asyncio.wait_for(context.close(), timeout=2.0)
                    except Exception:
                        pass
            except Exception as e:
                self.log.error(f"Worker {worker_id} failed: {e}")
                return 0
        
        # Launch workers
        tasks = [worker_wrapper(i) for i in range(1, concurrency + 1)]
        results = await asyncio.gather(*tasks)
        
        total_scraped = sum(results)
        self.log.info(f"Parallel scraping complete: {total_scraped} total suppliers scraped")
        return total_scraped


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load YAML configuration file."""
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Scrape supplier data from procurement website")
    
    # Get script directory for relative paths
    script_dir = Path(__file__).parent
    
    parser.add_argument(
        "--config",
        type=Path,
        default=script_dir / "config" / "supplier_selectors.yaml",
        help="Path to selectors config file"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / "data" / "suppliers.jsonl",
        help="Output file path"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Maximum number of pages to scrape (default: 1)"
    )
    parser.add_argument(
        "--page-pause-ms",
        type=int,
        default=1000,
        help="Pause between page actions in milliseconds"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    return parser.parse_args()


async def async_main(args: argparse.Namespace) -> None:
    """Async main function."""
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    
    logger = logging.getLogger("main")
    
    # Load configuration
    config_data = load_config(args.config)
    
    # Build scraper config
    scraper_config = SupplierScraperConfig(
        base_url=config_data["base_url"],
        headless=args.headless,
        max_pages=args.max_pages,
        output_path=args.output,
        page_pause_ms=args.page_pause_ms
    )
    
    if args.concurrency > 1:
        logger.info(f"Running in parallel mode with {args.concurrency} workers")
        
        # For parallel execution, manage browser lifecycle at top level
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=scraper_config.headless)
        
        try:
            # Create shared writer
            writer = JsonLinesWriter(scraper_config.output_path)
            
            # Create master scraper instance
            scraper = SupplierScraper(scraper_config, config_data, browser=browser, writer=writer)
            
            # Run parallel scraping
            total = await scraper.scrape_parallel(args.max_pages, args.concurrency)
            logger.info(f"✅ Total suppliers scraped: {total}")
            
        finally:
            # Cleanup
            if browser:
                try:
                    await asyncio.wait_for(browser.close(), timeout=5.0)
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
            
            if playwright:
                try:
                    await asyncio.wait_for(playwright.stop(), timeout=5.0)
                except Exception as e:
                    logger.warning(f"Error stopping playwright: {e}")
    else:
        # Sequential execution
        async with SupplierScraper(scraper_config, config_data) as scraper:
            await scraper.run()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
