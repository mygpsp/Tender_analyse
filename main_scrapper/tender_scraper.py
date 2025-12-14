import argparse
import asyncio
import json
import logging
import re
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from playwright.async_api import Browser, Page, async_playwright
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


DEFAULT_CONFIG_PATH = Path("main_scrapper/config/selectors.yaml")


@dataclass
class SelectorConfig:
    date_from: str
    date_to: str
    date_type: str
    search_button: str
    result_rows: str
    detail_link: str
    detail_panel: str
    close_detail: str
    next_button: str


@dataclass
class ScrapeConfig:
    base_url: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    headless: bool = True
    page_pause_ms: int = 500
    max_pages: int = 0
    output_path: Path = Path("data/tenders.jsonl")
    tender_type: Optional[str] = None  # e.g., 'CON', 'NAT', 'SPA'
    category_code: Optional[str] = None  # e.g., '60100000'
    count_only: bool = False  # If True, only extract count and exit


def load_config(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class JsonLinesWriter:
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: Dict[str, Any]) -> None:
        with self.output_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


class TenderScraper:
    def __init__(self, scrape_cfg: ScrapeConfig, selectors: SelectorConfig):
        self.cfg = scrape_cfg
        self.selectors = selectors
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.writer = JsonLinesWriter(scrape_cfg.output_path)
        self.log = logging.getLogger("tender_scraper")
        self._working_result_selector: Optional[str] = None
        self.existing_tenders: set[str] = set()
        self.tenders_scraped_count: int = 0  # Track number of tenders actually scraped
        self.expected_total_count: Optional[int] = None  # Expected total from website

    def set_existing_tenders(self, existing: set[str]) -> None:
        """Set list of existing tender numbers to skip."""
        self.existing_tenders = existing

    async def __aenter__(self) -> "TenderScraper":
        self.log.debug("Launching Chromium (headless=%s)", self.cfg.headless)
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.cfg.headless)
        context = await self.browser.new_context()
        self.page = await context.new_page()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.browser:
            await self.browser.close()

    async def run(self) -> None:
        assert self.page is not None
        
        # STEP 1: Navigate to base URL
        self.log.info("Navigating to %s", self.cfg.base_url)
        await self.page.goto(self.cfg.base_url, wait_until="networkidle")
        
        # STEP 2: Apply date filters (if provided)
        if self.cfg.date_from and self.cfg.date_to:
            self.log.info("Applying date filters...")
            await self.apply_date_filters()
        else:
            self.log.info("No date filters provided, using website default (Active Tenders).")
        
        # STEP 2.5: Apply tender type and category filters if specified
        if self.cfg.tender_type or self.cfg.category_code:
            self.log.info("Applying tender type and category filters...")
            await self.apply_tender_filters()
        
        # STEP 3: Wait for search button to be ready and visible
        self.log.info("Waiting for search button to be ready...")
        await self.page.wait_for_selector(self.selectors.search_button, state="visible", timeout=5_000)
        
        # Verify search button is enabled
        is_enabled = await self.page.evaluate(f"""() => {{
            const btn = document.querySelector('{self.selectors.search_button}');
            return btn && !btn.disabled && btn.offsetParent !== null;
        }}""")
        if not is_enabled:
            self.log.warning("Search button may not be enabled")
        
        # STEP 4: Perform search
        self.log.info(
            "🔍 Clicking search button for date window %s → %s",
            self.cfg.date_from,
            self.cfg.date_to,
        )
        await self.page.click(self.selectors.search_button)
        self.log.info("✅ Search button clicked, waiting for results...")
        
        # STEP 5: Wait for search to complete and results to appear
        self.log.info("Waiting for search results to appear...")
        await self._wait_for_search_results()
        
        # STEP 6: Verify results exist and find working selector
        # First check if "No records found" message exists
        is_no_records = await self.page.evaluate("""() => {
            const bodyText = document.body.innerText || document.body.textContent || '';
            // Check for specific Georgian "No records found" message
            return bodyText.includes('ჩანაწერები არ არის');
        }""")
        
        if is_no_records:
            self.log.info("✅ No tenders found for this date (Website returned 'No records found').")
            self.expected_total_count = 0
            self.tenders_scraped_count = 0
            
            # Count-only check
            if self.cfg.count_only:
                 self.log.info("="*60)
                 self.log.info("📊 TENDER COUNT: 0")
                 self.log.info("="*60)
                 self.log.info("Website Count: 0 tenders")
                 self.log.info("="*60)
            
            return # Exit gracefully
            
        used_selector = await self._find_result_selector()
        if not used_selector:
            # Final check before raising error - sometimes the table exists but is empty
            raise Exception("Could not find any result rows after search")
        
        # Store the selector that worked for future use
        self._working_result_selector = used_selector
        
        # STEP 6.5: Extract and log total tender count from website
        # Wait a bit to ensure pagination has fully updated with filtered results
        await self.page.wait_for_timeout(1000)
        
        total_count_info = await self._extract_total_count()
        if total_count_info:
            self.expected_total_count = total_count_info.get('total_tenders')
            self.log.info("📊 Website reports: %s total tenders across %s pages", 
                         total_count_info.get('total_tenders', 'unknown'),
                         total_count_info.get('total_pages', 'unknown'))
        
        # Safety: If count extraction failed (0 or None) but we found rows, use row count
        last_found = getattr(self, '_last_found_row_count', 0)
        if (not self.expected_total_count or self.expected_total_count == 0) and last_found > 0:
             self.log.info(f"⚠️ Extracted count was 0/None but found {last_found} rows. Using row count.")
             self.expected_total_count = last_found
        
        # COUNT-ONLY MODE: Exit here if we only need the count
        if self.cfg.count_only:
            self.log.info("✅ COUNT-ONLY MODE: Extracted count, exiting without scraping rows")
            self.log.info("="*60)
            self.log.info("📊 TENDER COUNT")
            self.log.info("="*60)
            self.log.info("Website Count: %s tenders", self.expected_total_count or "unknown")
            self.log.info("="*60)
            return  # Exit without scraping
        
        self.log.info("Search completed. Starting to scrape results...")
        
        # STEP 7: Now scrape results page by page
        page_index = 1
        while True:
            await self.scrape_current_page(page_index)
            page_index += 1
            if 0 < self.cfg.max_pages < page_index:
                self.log.info("Reached max_pages limit (%s), stopping", self.cfg.max_pages)
                break
            if not await self.go_to_next_page():
                self.log.info("No more pages, scraping complete")
                break
        
        # STEP 8: Log final summary with comparison
        self.log.info("="*60)
        self.log.info("📊 SCRAPING SUMMARY")
        self.log.info("="*60)
        
        # Show active filters
        self.log.info("Active Filters:")
        if self.cfg.date_from or self.cfg.date_to:
            self.log.info("  📅 Date Range: %s to %s", 
                         self.cfg.date_from or "any", 
                         self.cfg.date_to or "any")
        if self.cfg.tender_type:
            self.log.info("  📋 Tender Type: %s", self.cfg.tender_type)
        if self.cfg.category_code:
            self.log.info("  🏷️  Category Code: %s", self.cfg.category_code)
        
        self.log.info("")
        self.log.info("Results Comparison:")
        self.log.info("  Website Count: %s tenders", self.expected_total_count or "unknown")
        self.log.info("  Local Count:   %s tenders", self.tenders_scraped_count)
        
        if self.expected_total_count:
            if self.tenders_scraped_count == self.expected_total_count:
                self.log.info("  ✅ SUCCESS: All tenders scraped correctly!")
            else:
                difference = self.expected_total_count - self.tenders_scraped_count
                coverage = (self.tenders_scraped_count / self.expected_total_count * 100) if self.expected_total_count > 0 else 0
                if difference > 0:
                    self.log.warning("  ⚠️ MISMATCH: Missing %s tenders (%.1f%% coverage)", 
                                   difference, coverage)
                else:
                    self.log.info("  ℹ️  Scraped %s extra tenders (%.1f%% of expected)", 
                                abs(difference), coverage)
        self.log.info("="*60)
    
    async def _wait_for_search_results(self) -> None:
        """Wait for search to complete - results table AND pagination controls must be ready."""
        assert self.page is not None
        
        self.log.info("Waiting for search to complete...")
        
        # Step 1: Wait for "გთხოვთ დაელოდოთ" (Please wait) message to disappear
        self.log.info("Waiting for loading message to disappear...")
        try:
            await self.page.wait_for_function(
                """() => {
                    // Check if "გთხოვთ დაელოდოთ" text exists anywhere on the page
                    const bodyText = document.body.innerText || document.body.textContent || '';
                    const hasLoadingMessage = bodyText.includes('გთხოვთ დაელოდოთ');
                    return !hasLoadingMessage; // Wait until it's NOT present
                }""",
                timeout=15_000
            )
            self.log.info("✅ Loading message disappeared")
        except Exception as e:
            self.log.debug("Loading message wait timeout: %s", e)
            # Check if it's still there
            still_loading = await self.page.evaluate("""() => {
                const bodyText = document.body.innerText || document.body.textContent || '';
                return bodyText.includes('გთხოვთ დაელოდოთ');
            }""")
            if still_loading:
                self.log.warning("⚠️ Loading message still present, but continuing...")
        
        # Step 2: Wait for results table to appear
        self.log.info("Waiting for result rows to appear...")
        try:
            await self.page.wait_for_selector(
                f"{self.selectors.result_rows}, table tbody tr",
                timeout=10_000,
                state="attached"
            )
            self.log.debug("✅ Result rows appeared")
        except Exception as e:
            self.log.debug("Result rows wait timeout, trying network idle: %s", e)
            try:
                await self.page.wait_for_load_state("networkidle", timeout=5_000)
            except Exception:
                pass
        
        # Step 3: Wait for pagination controls to appear (next button or indication that there are no more pages)
        self.log.info("Waiting for pagination controls to be ready...")
        try:
            # Wait for next button to appear (even if disabled, it should exist)
            await self.page.wait_for_selector(
                self.selectors.next_button,
                timeout=5_000,
                state="attached"
            )
            self.log.debug("✅ Pagination button appeared")
        except Exception:
            # Next button might not exist if there's only one page - that's okay
            self.log.debug("Next button not found (might be single page)")
        
        # Step 4: Wait for page to fully load and stabilize
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=3_000)
        except Exception:
            pass
        
        # Step 5: Wait for any loading overlays to disappear
        try:
            await self.page.wait_for_function(
                """() => {
                    const overlay = document.querySelector('.blockUI.blockOverlay');
                    return !overlay || window.getComputedStyle(overlay).display === 'none';
                }""",
                timeout=3_000
            )
            self.log.debug("✅ Loading overlay cleared")
        except Exception:
            pass
        
        # Step 6: Final verification - check that results are actually visible and loading message is gone
        page_state = await self.page.evaluate("""() => {
            const bodyText = document.body.innerText || document.body.textContent || '';
            const hasLoadingMessage = bodyText.includes('გთხოვთ დაელოდოთ');
            const rows = document.querySelectorAll('table tbody tr, .noticeRow');
            return {
                hasLoadingMessage: hasLoadingMessage,
                resultCount: rows.length,
                hasNextButton: !!document.querySelector('#btn_next > span.ui-button-icon-primary.ui-icon.ui-icon-seek-next')
            };
        }""")
        
        if page_state.get("hasLoadingMessage"):
            self.log.warning("⚠️ Loading message still present! Waiting a bit more...")
            await asyncio.sleep(2)
            # Check again
            still_loading = await self.page.evaluate("""() => {
                const bodyText = document.body.innerText || document.body.textContent || '';
                return bodyText.includes('გთხოვთ დაელოდოთ');
            }""")
            if still_loading:
                self.log.warning("⚠️ Loading message persists, but proceeding anyway...")
        
        if page_state.get("resultCount", 0) > 0:
            self.log.info("✅ Search completed! Found %s result rows ready for scraping", page_state.get("resultCount"))
        else:
            self.log.warning("⚠️ Search completed but no result rows found")
    
    async def _find_result_selector(self) -> Optional[str]:
        """Find which selector works for result rows. Returns the working selector or None."""
        assert self.page is not None
        
        # Debug: Check what's actually on the page
        page_content = await self.page.evaluate("""() => {
            return {
                title: document.title,
                url: window.location.href,
                hasNoticeRow: !!document.querySelector('.noticeRow'),
                hasTable: !!document.querySelector('table'),
                hasTbody: !!document.querySelector('tbody'),
                allTableRows: document.querySelectorAll('table tbody tr').length,
                allRowsWithClass: document.querySelectorAll('.noticeRow').length,
            };
        }""")
        self.log.debug("Page after search: %s", page_content)
        
        # Try multiple possible selectors for result rows
        possible_selectors = [
            ".noticeRow",          # Most specific - used by tender rows
            "[class*='notice']",   # Alternative specific
            "tr[class*='Row']",    # Another specific pattern
            "table.ktable tbody tr[id]", # Specific table structure seen in logs
            "tr[id^='A']",         # Rows often have IDs like A123456
            self.selectors.result_rows, # Config fallback
        ]
        
        for selector in possible_selectors:
            try:
                rows = await self.page.query_selector_all(selector)
                if rows and len(rows) > 0:
                    self.log.info("Found %s result rows using selector: %s", len(rows), selector)
                    self._last_found_row_count = len(rows)  # Store count for fallback
                    
                    # DEBUG: Log the first row's text to see if dates match
                    try:
                         first_row_text = await rows[0].inner_text()
                         self.log.info(f"DEBUG - First Row Content: {first_row_text[:100]}...")
                    except:
                         pass
                         
                    return selector
            except Exception as e:
                self.log.debug("Selector %s failed: %s", selector, e)
                continue
        
        # If no results found, take screenshot for debugging
        if self.page:
            await self.page.screenshot(path="debug_search_failed.png")
            html_snippet = await self.page.evaluate("""() => {
                const tables = document.querySelectorAll('table');
                return Array.from(tables).map(t => t.outerHTML.substring(0, 1000)).join('\\n---\\n');
            }""")
            self.log.error("Screenshot saved to debug_search_failed.png")
            self.log.error("Table HTML snippets: %s", html_snippet)
        
        return None

    async def _extract_total_count(self) -> Optional[Dict[str, int]]:
        """Extract total tender count and page count from pagination text.
        
        Looks for text like: "2190 ჩანაწერი (გვერდი: 1/548)"
        Returns: {'total_tenders': 2190, 'total_pages': 548, 'current_page': 1}
        """
        assert self.page is not None
        
        try:
            # Wait a bit for pagination to load
            await self.page.wait_for_timeout(500)
            
            # Extract pagination text from the page
            pagination_info = await self.page.evaluate("""() => {
                // Look for pagination text in span with class ui-button-text
                const spans = document.querySelectorAll('span.ui-button-text');
                
                for (const span of spans) {
                    const text = span.textContent || span.innerText || '';
                    // Pattern: "X ჩანაწერი (გვერდი: Y/Z)" or "X მონაცემი ცხრილში (გვერდი: Y/Z)"
                    const match = text.match(/(\\d+)\\s*(?:ჩანაწერი|მონაცემი\\s*ცხრილში)\\s*\\(გვერდი:\\s*(\\d+)\\/(\\d+)\\)/);
                    
                    if (match) {
                        return {
                            total_tenders: parseInt(match[1]),
                            current_page: parseInt(match[2]),
                            total_pages: parseInt(match[3])
                        };
                    }
                }
                
                return null;
            }""")
            
            if pagination_info:
                self.log.debug("Extracted pagination info: %s", pagination_info)
                return pagination_info
            
            # Fallback: Use stored row count from search (most reliable)
            last_count = getattr(self, '_last_found_row_count', 0)
            self.log.info(f"DEBUG: Checking _last_found_row_count: {last_count}")
            if last_count > 0:
                self.log.info(f"Pagination text not found. Using previously found row count: {last_count}")
                return {
                    'total_tenders': last_count,
                    'total_pages': 1,
                    'current_page': 1
                }

            self.log.debug("Could not extract pagination info from page")
            return None
                
        except Exception as e:
            self.log.debug("Error extracting total count: %s", e)
            return None

    async def apply_date_filters(self) -> None:
        assert self.page is not None
        
        # Wait for page to be ready
        await self.page.wait_for_load_state("domcontentloaded")
        
        # NOTE: We don't change the date type dropdown - default is already Registration/Announcement Date
        # which is what we want for filtering by published_date
        
        start = date.fromisoformat(self.cfg.date_from)
        end = date.fromisoformat(self.cfg.date_to)
        
        # Set date from
        self.log.info("Setting date FROM: %s", start.isoformat())
        await self._set_date_via_picker(self.selectors.date_from, start)
        
        # Verify date from was set
        date_from_value = await self.page.evaluate(f"""() => {{
            const input = document.querySelector('{self.selectors.date_from}');
            return input ? input.value : '';
        }}""")
        self.log.info("Date FROM value after setting: '%s'", date_from_value)
        
        # Set date to
        self.log.info("Setting date TO: %s", end.isoformat())
        await self._set_date_via_picker(self.selectors.date_to, end)
        
        # Verify date to was set
        date_to_value = await self.page.evaluate(f"""() => {{
            const input = document.querySelector('{self.selectors.date_to}');
            return input ? input.value : '';
        }}""")
        self.log.info("Date TO value after setting: '%s'", date_to_value)
        
        # Final verification - both dates should be set
        if not date_from_value or not date_to_value:
            self.log.warning("⚠️ Date fields may not be set correctly!")
            self.log.warning("  Date FROM: '%s'", date_from_value)
            self.log.warning("  Date TO: '%s'", date_to_value)
        else:
            self.log.info("✅ Date filters applied successfully")
    
    async def apply_tender_filters(self) -> None:
        """Apply tender type and category code filters using select_option."""
        assert self.page is not None
        
        # Apply tender type filter (e.g., CON)
        if self.cfg.tender_type:
            self.log.info(f"Setting tender type filter to: {self.cfg.tender_type}")
            try:
                # Wait for the select element (actual ID is #app_type)
                tender_type_selector = '#app_type'
                await self.page.wait_for_selector(tender_type_selector, state="attached", timeout=5_000)
                
                # Map tender type codes to their select values
                # From HTML: value="4" for CON, value="9" for NAT, etc.
                tender_type_values = {
                    'CON': '4',
                    'NAT': '9',
                    'SPA': '2',
                    'CNT': '6',
                    'MEP': '11',
                    'DAP': '15',
                    'TEP': '16',
                    'GEO': '3',
                    'DEP': '5',
                    'GRA': '7'
                }
                
                value = tender_type_values.get(self.cfg.tender_type, self.cfg.tender_type)
                await self.page.select_option(tender_type_selector, value=value)
                
                self.log.info(f"✅ Tender type set to: {self.cfg.tender_type} (value={value})")
                await asyncio.sleep(0.3)
            except Exception as e:
                self.log.warning(f"Could not set tender type filter: {e}")
        
        # Apply category code filter (e.g., 60100000)
        if self.cfg.category_code:
            self.log.info(f"Setting category code filter to: {self.cfg.category_code}")
            try:
                # Wait for the select element (actual ID is #app_basecode)
                category_selector = '#app_basecode'
                await self.page.wait_for_selector(category_selector, state="attached", timeout=5_000)
                
                # Select by label since the value is an internal ID, not the category code
                # Label format: "60100000 - საავტომობილო ტრანსპორტის მომსახურებები"
                # We need to match the label that starts with the category code
                result = await self.page.evaluate(
                    """(args) => {
                        const select = document.querySelector(args.selector);
                        if (!select) return { success: false, error: 'select not found' };
                        
                        // Find option with label starting with category code
                        const options = select.querySelectorAll('option');
                        for (let option of options) {
                            if (option.textContent.trim().startsWith(args.categoryCode)) {
                                select.value = option.value;
                                // Trigger change event
                                select.dispatchEvent(new Event('change', { bubbles: true }));
                                return { success: true, value: option.value, label: option.textContent.trim() };
                            }
                        }
                        return { success: false, error: 'option not found' };
                    }""",
                    {'selector': category_selector, 'categoryCode': self.cfg.category_code}
                )
                
                if result.get('success'):
                    self.log.info(f"✅ Category code set to: {self.cfg.category_code} (value={result.get('value')})")
                else:
                    self.log.warning(f"Could not find category option: {result.get('error')}")
                
                await asyncio.sleep(0.3)
            except Exception as e:
                self.log.warning(f"Could not set category code filter: {e}")

    async def _set_date_via_picker(self, input_selector: str, target_date: date) -> None:
        assert self.page is not None
        self.log.debug("Setting %s to %s", input_selector, target_date.isoformat())
        
        # Wait for input to be available
        await self.page.wait_for_selector(input_selector, state="visible", timeout=5_000)
        
        # Format date as DD.MM.YYYY (Georgian format used by the site)
        date_str_georgian = target_date.strftime("%d.%m.%Y")
        
        # Try using jQuery UI datepicker API directly
        result = await self.page.evaluate(
            """(args) => {
                try {
                    const $input = $(args.selector);
                    if ($input.length && typeof $input.datepicker === 'function') {
                        // Create Date object
                        const dateObj = new Date(args.year, args.month - 1, args.day);
                        // Set date using datepicker API
                        $input.datepicker('setDate', dateObj);
                        // Also set value directly as backup
                        $input.val(args.dateStr);
                        // Trigger change event
                        $input.trigger('change');
                        // Verify it was set
                        const currentValue = $input.val();
                        return { 
                            success: currentValue && currentValue.length > 0, 
                            method: 'jquery_api',
                            value: currentValue
                        };
                    }
                } catch (e) {
                    return { success: false, error: e.message };
                }
                return { success: false, error: 'jquery not available' };
            }""",
            {
                "selector": input_selector,
                "year": target_date.year,
                "month": target_date.month,
                "day": target_date.day,
                "dateStr": date_str_georgian,
            },
        )
        
        # Check if jQuery method worked
        if result.get("success") and result.get("value"):
            self.log.debug("Date set via jQuery API: %s", result.get("value"))
            # Wait a moment for datepicker to update
            await asyncio.sleep(0.3)
        else:
            # Fallback: click input, navigate calendar manually
            self.log.debug("jQuery API failed, using manual navigation: %s", result.get("error"))
            await self.page.click(input_selector)
            await self.page.wait_for_selector(".ui-datepicker", timeout=5_000)
            await self._navigate_calendar_to_date(target_date)
            # Wait for datepicker to close
            try:
                await self.page.wait_for_selector(".ui-datepicker", state="hidden", timeout=2_000)
            except Exception:
                pass
        
        # Final verification - check if date was actually set
        current_value = await self.page.evaluate(
            """(sel) => {
                const input = document.querySelector(sel);
                return input ? input.value : '';
            }""",
            input_selector,
        )
        
        if not current_value or current_value == "":
            self.log.warning("⚠️ Date was not set! Trying manual navigation again...")
            # Try one more time with manual navigation
            await self.page.click(input_selector)
            await self.page.wait_for_selector(".ui-datepicker", timeout=5_000)
            await self._navigate_calendar_to_date(target_date)
            try:
                await self.page.wait_for_selector(".ui-datepicker", state="hidden", timeout=2_000)
            except Exception:
                pass
            # Check again
            current_value = await self.page.evaluate(
                """(sel) => document.querySelector(sel)?.value || ''""",
                input_selector,
            )
        
        if current_value:
            self.log.debug("✅ Date set successfully: %s", current_value)
        else:
            self.log.error("❌ Failed to set date for %s", input_selector)

    async def _navigate_calendar_to_date(self, target_date: date) -> None:
        """Navigate jQuery UI calendar to target date by clicking prev/next buttons."""
        assert self.page is not None
        
        # Get current displayed month/year from calendar
        current_info = await self.page.evaluate("""() => {
            const yearEl = document.querySelector('.ui-datepicker-year');
            const monthEl = document.querySelector('.ui-datepicker-month');
            // jQuery UI datepicker stores month as 0-indexed in data
            const monthSelect = document.querySelector('.ui-datepicker-month');
            let monthNum = null;
            if (monthSelect) {
                monthNum = parseInt(monthSelect.getAttribute('data-month')) + 1;
            }
            return {
                year: yearEl ? parseInt(yearEl.textContent) : null,
                month: monthNum
            };
        }""")
        
        self.log.debug("Current calendar shows: %s", current_info)
        
        # Calculate months difference
        target_month = target_date.month
        target_year = target_date.year
        
        if current_info.get("year") and current_info.get("month"):
            current_year = current_info["year"]
            current_month = current_info["month"]
            months_diff = (target_year - current_year) * 12 + (target_month - current_month)
            
            if months_diff != 0:
                # Click prev/next buttons to navigate
                button_selector = ".ui-datepicker-next" if months_diff > 0 else ".ui-datepicker-prev"
                for _ in range(abs(months_diff)):
                    await self.page.click(button_selector)
                    # Wait for calendar to update - check if we've reached target
                    try:
                        # Wait a brief moment for calendar to update
                        await asyncio.sleep(0.2)
                        # Check if we've reached target month
                        check = await self.page.evaluate("""() => {
                            const yearEl = document.querySelector('.ui-datepicker-year');
                            const monthEl = document.querySelector('.ui-datepicker-month');
                            if (!yearEl || !monthEl) return null;
                            return {
                                year: parseInt(yearEl.textContent),
                                month: parseInt(monthEl.getAttribute('data-month')) + 1
                            };
                        }""")
                        if check and check.get("year") == target_year and check.get("month") == target_month:
                            break  # Reached target month
                    except Exception:
                        # Continue to next iteration
                        pass
        
        # Now click the day
        day_links = await self.page.query_selector_all(
            ".ui-datepicker-calendar td a:not(.ui-state-disabled)"
        )
        for link in day_links:
            text = await link.inner_text()
            if text.strip() == str(target_date.day):
                await link.click()
                return
        
        self.log.warning("Could not find day %s in calendar", target_date.day)

    async def scrape_current_page(self, page_idx: int) -> None:
        assert self.page is not None
        # Use the working selector if we found one, otherwise fall back to config selector
        selector = self._working_result_selector or self.selectors.result_rows
        rows = await self.page.query_selector_all(selector)
        self.log.info("Page %s has %s rows (using selector: %s)", page_idx, len(rows), selector)
        
        # Skip first row if it's a header (check if it has th elements)
        start_idx = 0
        if rows:
            first_row_html = await rows[0].inner_html()
            if "<th" in first_row_html or "header" in first_row_html.lower():
                self.log.debug("Skipping header row")
                start_idx = 1
        
        for row_idx, row in enumerate(rows[start_idx:], start=start_idx + 1):
            self.log.debug("Scraping page %s row %s", page_idx, row_idx)
            await self.collect_row(row)
            # Minimal delay between rows - only if page_pause_ms is set
            if self.cfg.page_pause_ms > 0:
                await asyncio.sleep(min(self.cfg.page_pause_ms / 1000, 0.1))  # Max 100ms

    def _is_obviously_invalid(self, record: Dict[str, Any]) -> bool:
        """Only filter out obviously invalid rows (navigation buttons, headers, calendar dates). Save everything else for later parsing."""
        all_cells = record.get("all_cells", "").lower()
        raw_html = record.get("raw_html", "").lower()
        number = record.get("number", "").strip()
        status = record.get("status", "").strip()
        
        # Skip obvious navigation button rows
        nav_keywords = [
            "მომხმარებლები",  # Users
            "cmr", "con", "smp", "eplan", "mrs",  # Navigation buttons
        ]
        for keyword in nav_keywords:
            if keyword in all_cells or keyword in raw_html:
                # But only if it's clearly a button (has ui-button class)
                if "ui-button" in raw_html and "btn_" in raw_html:
                    return True
        
        # Skip if it's clearly a header row (has <th> elements)
        if "<th" in raw_html or "header" in raw_html.lower():
            return True
        
        # Skip calendar date rows - check for datepicker indicators
        if "data-handler=\"selectday\"" in raw_html or "ui-datepicker" in raw_html:
            return True
        
        # Skip if all_cells looks like calendar dates (pattern: "1 | 2 | 3 | 4 | 5 | 6 | 7")
        if re.match(r'^\d+\s*\|\s*\d+\s*\|\s*\d+', all_cells.strip()):
            return True
        
        # Skip if status is just a digit (calendar day) and no tender info
        if status.isdigit() and len(status) <= 2:
            if not any(keyword in all_cells for keyword in ["განცხადების", "ნომერი", "შემსყიდველი", "ტენდერი"]):
                return True
        
        # Skip if number is just digits (likely calendar days or page numbers) and no tender info
        if number.isdigit() and len(number) <= 2:
            # Check if there's any tender-related text
            if not any(keyword in all_cells for keyword in ["განცხადების", "ნომერი", "შემსყიდველი", "ტენდერი"]):
                return True
        
        # Skip if completely empty
        if not all_cells.strip() and not raw_html.strip():
            return True
        
        # Everything else - save it! We'll parse tender numbers from all_cells/raw_html later
        return False
    
    async def collect_row(self, row_handle) -> None:
        """Extract data directly from table row - no clicking into detail pages."""
        if self.page is None:
            return
        
        # Extract data directly from table row - no navigation needed
        record = await self.extract_from_row(row_handle)
        
        # Only skip obvious navigation/header rows - save everything else for later parsing
        if self._is_obviously_invalid(record):
            self.log.debug("Skipping obvious invalid row (navigation/header)")
            return
            
        # Check for duplicates if we have existing tenders
        if self.existing_tenders:
            # We need to extract the number to check
            # This duplicates some logic from extract_from_row but is necessary for filtering
            # Actually, extract_from_row already does a lot of parsing, let's check the record
            # But wait, extract_from_row returns a dict with 'number' key if it found it
            # The current implementation of extract_from_row parses 'number'
            
            tender_num = record.get("number", "").strip().upper()
            if tender_num and tender_num in self.existing_tenders:
                self.log.debug(f"Skipping duplicate tender: {tender_num}")
                return
        
        # Save all rows - we'll parse/extract tender numbers from all_cells/raw_html later
        self.log.debug("Captured row (will parse later)")
        self.writer.write(record)
        self.tenders_scraped_count += 1  # Increment counter

    # Removed extract_detail method - not used in simplified table-only extraction approach
    # Kept commented for potential future use if detail page extraction is needed
    # async def extract_detail(self, page: Page, detail_panel_selector: Optional[str] = None) -> Dict[str, Any]:
    #     """Extract data from detail panel - not currently used."""
    #     pass

    async def extract_from_row(self, row_handle) -> Dict[str, Any]:
        """Extract data directly from table row using element methods for immediate serialization."""
        assert self.page is not None
        import re
        
        # Get all cells using element methods (immediate serialization - no stale element issues)
        cells = await row_handle.query_selector_all('td')
        cell_texts = []
        for cell in cells:
            text = await cell.inner_text()
            cell_texts.append(text.strip())
        
        # Extract tender_id from row attributes (for building detail URLs)
        tender_id = None
        try:
            row_id_attr = await row_handle.get_attribute("id")
            if row_id_attr and row_id_attr.startswith("A"):
                # Extract ID from id="A657645"
                tender_id = row_id_attr[1:]  # Remove "A" prefix
            else:
                # Try to extract from onclick: ShowApp(657645,...)
                onclick_attr = await row_handle.get_attribute("onclick")
                if onclick_attr:
                    match = re.search(r'ShowApp\((\d+)', onclick_attr)
                    if match:
                        tender_id = match.group(1)
        except Exception:
            pass
        
        # Build detail URL if we have tender_id
        detail_url = None
        if tender_id:
            detail_url = f"https://tenders.procurement.gov.ge/public/?go={tender_id}&lang=ge"
        
        # Combine all cell text
        all_cells_text = " | ".join(cell_texts)
        
        # Parse structured data from text
        tender_number = ""
        buyer_name = ""
        status_text = ""
        participant_count = None  # Number of participants
        
        # Extract tender number from text (pattern: "განცხადების ნომერი: NAT250021657")
        tender_number_match = re.search(
            r'განცხადების\s+ნომერი[:\s]+([A-Z]{2,4}\d{9,})',
            all_cells_text,
            re.IGNORECASE
        )
        if tender_number_match:
            tender_number = tender_number_match.group(1)
        else:
            # Fallback: look for tender number pattern anywhere in text
            fallback_match = re.search(r'\b([A-Z]{2,4}\d{9,})\b', all_cells_text)
            if fallback_match:
                tender_number = fallback_match.group(1)
        
        # Extract buyer (pattern: "შემსყიდველი: ...")
        buyer_match = re.search(
            r'შემსყიდველი[:\s]+([^\n|]+)',
            all_cells_text
        )
        if buyer_match:
            buyer_name = buyer_match.group(1).strip()
            # Clean up buyer name (remove extra whitespace, newlines)
            buyer_name = re.sub(r'\s+', ' ', buyer_name).strip()
        
        # Extract supplier (pattern: "გამარჯვებული: ..." or "მიმწოდებელი: ...")
        supplier_name = ""
        supplier_match = re.search(
            r'გამარჯვებული[:\s]+([^\n|]+)',
            all_cells_text
        )
        if supplier_match:
            supplier_name = supplier_match.group(1).strip()
            # Clean up supplier name (remove extra whitespace, newlines)
            supplier_name = re.sub(r'\s+', ' ', supplier_name).strip()
        else:
            # Try alternative pattern: "მიმწოდებელი: ..." or "მომწოდებელი: ..."
            supplier_match = re.search(
                r'მ[იო]მწოდებელი[:\s]+([^\n|]+)',
                all_cells_text
            )
            if supplier_match:
                supplier_name = supplier_match.group(1).strip()
                supplier_name = re.sub(r'\s+', ' ', supplier_name).strip()
        
        # Extract status - look for all possible status types
        # Statuses from the system: გამოცხადებულია, წინადადებების მიღება დაწყებულია,
        # წინადადებების მიღება დასრულებულია, შერჩევა/შეფასება, გამარჯვებული გამოვლენილია,
        # დასრულებულია უარყოფითი შედეგით, არ შედგა, შეწყვეტილია,
        # მიმდინარეობს ხელშეკრულების მომზადება, ხელშეკრულება დადებულია
        status_patterns = [
            r'წინადადებების მიღება დაწყებულია',
            r'წინადადებების მიღება დასრულებულია',
            r'შერჩევა/შეფასება',
            r'გამარჯვებული გამოვლენილია',
            r'დასრულებულია უარყოფითი შედეგით',
            r'არ შედგა',
            r'შეწყვეტილია',
            r'მიმდინარეობს ხელშეკრულების მომზადება',
            r'ხელშეკრულება დადებულია',
            r'დასრულებულია',
            r'გამოცხადებულია',
            r'მიმდინარეობს',
        ]
        
        status_text = ""
        for pattern in status_patterns:
            status_match = re.search(pattern, all_cells_text, re.IGNORECASE)
            if status_match:
                status_text = status_match.group(0)
                break
        
        # Fallback: use first non-empty cell as status if no pattern matched
        if not status_text:
            status_text = cell_texts[0] if cell_texts and cell_texts[0].strip() else ""
        
        # Extract participant count (pattern: "მონაწილეთა რაოდენობა - 2")
        participant_match = re.search(
            r'მონაწილეთა\s+რაოდენობა[:\s-]+(\d+)',
            all_cells_text,
            re.IGNORECASE
        )
        if participant_match:
            try:
                participant_count = int(participant_match.group(1))
            except (ValueError, AttributeError):
                participant_count = None
        
        # Extract amount (pattern: "შესყიდვის სავარაუდო ღირებულება: 3`368.90 ლარი")
        amount = None
        amount_patterns = [
            r'შესყიდვის\s+სავარაუდო\s+ღირებულება[:\s]+(\d+(?:`\d+)*(?:\.\d+)?)\s*ლარი',
            r'ღირებულება[:\s]+(\d+(?:`\d+)*(?:\.\d+)?)\s*ლარი',
            r'(\d+(?:`\d+)*(?:\.\d+)?)\s*ლარი',
        ]
        for pattern in amount_patterns:
            amount_match = re.search(pattern, all_cells_text, re.IGNORECASE)
            if amount_match:
                amount_str = amount_match.group(1)
                cleaned = amount_str.replace('`', '').replace(',', '')
                try:
                    amount_value = float(cleaned)
                    # Validate: reasonable amount range (100 GEL to 1 billion GEL)
                    if 100 <= amount_value < 1_000_000_000:
                        amount = amount_value
                        break
                except ValueError:
                    pass
        
        # Extract published date (pattern: "შესყიდვის გამოცხადების თარიღი: 24.10.2025")
        published_date = None
        published_date_match = re.search(
            r'შესყიდვის\s+გამოცხადების\s+თარიღი[:\s]+(\d{2}\.\d{2}\.\d{4})',
            all_cells_text,
            re.IGNORECASE
        )
        if published_date_match:
            date_str = published_date_match.group(1)
            # Normalize DD.MM.YYYY to YYYY-MM-DD
            try:
                day, month, year = date_str.split('.')
                published_date = f"{year}-{month}-{day}"
            except ValueError:
                pass
        
        # Extract deadline date (pattern: "წინდადებების მიღების ვადა: 31.10.2025")
        # Fixed: actual text uses "წინდადებების" not "წინადადებების"
        deadline_date = None
        deadline_date_match = re.search(
            r'წინდადებების\s+მიღების\s+ვადა[:\s]+(\d{2}\.\d{2}\.\d{4})',
            all_cells_text,
            re.IGNORECASE
        )
        if deadline_date_match:
            date_str = deadline_date_match.group(1)
            # Normalize DD.MM.YYYY to YYYY-MM-DD
            try:
                day, month, year = date_str.split('.')
                deadline_date = f"{year}-{month}-{day}"
            except ValueError:
                pass
        
        # Extract category (pattern: "შესყიდვის კატეგორია: 45500000-სამშენებლო...")
        category = None
        category_code = None
        category_match = re.search(
            r'შესყიდვის\s+კატეგორია[:\s]+(\d{8})-([^\n|]+)',
            all_cells_text,
            re.IGNORECASE
        )
        if category_match:
            category_code = category_match.group(1)
            category_desc = category_match.group(2).strip()
            category = f"{category_code}-{category_desc}"
        
        # Extract tender type (pattern: "(GEO)", "(NAT)", "(CON)", etc.)
        tender_type = None
        tender_type_match = re.search(
            r'\(([A-Z]{2,4}|ePLAN)\)',
            all_cells_text
        )
        if tender_type_match:
            tender_type = tender_type_match.group(1)
        
        # Map to fields
        payload = {
            "number": tender_number,  # Extracted tender number
            "buyer": buyer_name,      # Extracted buyer name
            "supplier": supplier_name,  # Extracted supplier name (from "გამარჯვებული:" or "მიმწოდებელი:")
            "status": status_text,    # Extracted status
            "participants_count": participant_count,  # Number of participants (if available)
            "all_cells": all_cells_text,  # Keep all text for parsing
        }
        
        # Add new structured fields if extracted
        if amount is not None:
            payload["amount"] = amount
        if published_date:
            payload["published_date"] = published_date
        if deadline_date:
            payload["deadline_date"] = deadline_date
        if category:
            payload["category"] = category
        if category_code:
            payload["category_code"] = category_code
        if tender_type:
            payload["tender_type"] = tender_type
        
        # Add tender_id and detail_url if available
        if tender_id:
            payload["tender_id"] = tender_id
        if detail_url:
            payload["detail_url"] = detail_url
        
        # Add metadata
        payload["scraped_at"] = asyncio.get_event_loop().time()
        payload["date_window"] = {
            "from": self.cfg.date_from,
            "to": self.cfg.date_to,
        }
        payload["extraction_method"] = "row_direct"
        return payload

    async def go_to_next_page(self) -> bool:
        """Try to go to next page with retry logic. Returns True if successful, False if no more pages."""
        assert self.page is not None
        
        max_retries = 5
        retry_delay = 0.4
        
        for attempt in range(max_retries):
            try:
                # Re-query the button on each attempt (to avoid stale element)
                next_button = await self.page.query_selector(self.selectors.next_button)
                if not next_button:
                    if attempt == 0:
                        self.log.info("Next button not present, stopping pagination")
                    return False
                
                # Check if button is disabled
                disabled = await next_button.get_attribute("aria-disabled")
                if disabled in ("true", "True", "1"):
                    if attempt == 0:
                        self.log.info("Next button disabled, reached last page")
                    return False
                
                # Also check if button is actually clickable
                try:
                    is_enabled = await next_button.is_enabled()
                    if not is_enabled:
                        if attempt == 0:
                            self.log.info("Next button not enabled, reached last page")
                        return False
                except Exception:
                    pass
                
                # Button exists and is enabled - try to click it
                if attempt > 0:
                    self.log.debug("Retry attempt %s/%s to click next button...", attempt + 1, max_retries)
                
                self.log.info("Advancing to next page")
                await next_button.click(timeout=10_000)
                
                # Wait for "გთხოვთ დაელოდოთ" to disappear after clicking
                try:
                    await self.page.wait_for_function(
                        """() => {
                            const bodyText = document.body.innerText || document.body.textContent || '';
                            return !bodyText.includes('გთხოვთ დაელოდოთ');
                        }""",
                        timeout=10_000
                    )
                except Exception:
                    pass
                
                # Wait for results to appear using the working selector
                selector = self._working_result_selector or self.selectors.result_rows
                await self.page.wait_for_selector(selector, timeout=20_000)
                
                # Verify results are ready
                result_count = await self.page.evaluate("""() => {
                    const rows = document.querySelectorAll('table tbody tr, .noticeRow');
                    return rows.length;
                }""")
                
                if result_count > 0:
                    self.log.info("✅ Successfully advanced to next page (found %s rows)", result_count)
                    return True
                else:
                    self.log.warning("Next page loaded but no results found, retrying...")
                    await asyncio.sleep(retry_delay)
                    continue
                
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    self.log.debug("Attempt %s/%s failed: %s, retrying in %.1fs...", 
                                 attempt + 1, max_retries, error_msg[:80], retry_delay)
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    # Last attempt failed
                    if "not attached" in error_msg.lower() or "stale" in error_msg.lower():
                        self.log.info("Next button became detached (likely page changed), reached last page")
                    else:
                        self.log.warning("Could not click next button after %s attempts: %s", 
                                       max_retries, error_msg[:100])
                    return False
        
        return False


def build_configs(config_path: Path, args: argparse.Namespace) -> (ScrapeConfig, SelectorConfig):
    raw = load_config(config_path)
    selectors = raw["selectors"]
    scrape_block = raw.get("scrape", {})
    scrape_cfg = ScrapeConfig(
        base_url=raw.get("base_url"),
        date_from=args.date_from or scrape_block.get("date_from"),
        date_to=args.date_to or scrape_block.get("date_to"),
        headless=args.headless if args.headless is not None else scrape_block.get("headless", True),
        page_pause_ms=args.page_pause_ms or scrape_block.get("page_pause_ms", 500),
        max_pages=args.max_pages if args.max_pages is not None else scrape_block.get("max_pages", 0),
        output_path=Path(args.output or scrape_block.get("output_path", "data/tenders.jsonl")),
        tender_type=args.tender_type if hasattr(args, 'tender_type') else None,
        category_code=args.category_code if hasattr(args, 'category_code') else None,
        count_only=args.count_only if hasattr(args, 'count_only') else False,
    )

    selector_cfg = SelectorConfig(
        date_from=selectors["date_from"],
        date_to=selectors["date_to"],
        date_type=selectors["date_type"],
        search_button=selectors["search_button"],
        result_rows=selectors["result_rows"],
        detail_link=selectors["detail_link"],
        detail_panel=selectors["detail_panel"],
        close_detail=selectors["close_detail"],
        next_button=selectors["next_button"],
    )
    return scrape_cfg, selector_cfg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Georgian tender portal.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to selectors.yaml")
    parser.add_argument("--date-from", help="Override start date (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="Override end date (YYYY-MM-DD)")
    parser.add_argument("--headless", type=lambda v: v.lower() == "true", help="Set headless true/false")
    parser.add_argument("--page-pause-ms", type=int, help="Delay between row interactions")
    parser.add_argument("--max-pages", type=int, help="Limit number of result pages (0 = all)")
    parser.add_argument("--output", help="Override JSONL path")
    parser.add_argument("--tender-type", help="Filter by tender type (e.g., CON, NAT, SPA)")
    parser.add_argument("--category-code", help="Filter by category code (e.g., 60100000)")
    parser.add_argument("--count-only", action="store_true", help="Only extract tender count, don't scrape rows")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    return parser.parse_args()


async def async_main(args: argparse.Namespace) -> None:
    cfg_path = Path(args.config)
    scrape_cfg, selector_cfg = build_configs(cfg_path, args)
    async with TenderScraper(scrape_cfg, selector_cfg) as scraper:
        await scraper.run()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()

