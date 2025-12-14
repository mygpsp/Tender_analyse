"""
Detailed tender scraper - extracts full information for specific tender numbers.

This module is separate from the main scraper to maintain modularity.
It navigates to individual tender detail pages and extracts comprehensive information.
"""
import argparse
import asyncio
import json
import logging
import re
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from playwright.async_api import Browser, Page, async_playwright
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

logger = logging.getLogger("detailed_scraper")


def parse_date(date_str: str) -> str:
    """
    Parse date string (absolute or relative) and return YYYY-MM-DD format.
    
    Supports:
    - Absolute dates: "2025-12-01", "2025-11-29"
    - Relative dates: "today", "1 day ago", "-1 day", "10 days ago", "-10 days"
    
    Args:
        date_str: Date string to parse
    
    Returns:
        Date in YYYY-MM-DD format
    """
    date_str = date_str.strip().lower()
    today = datetime.now().date()
    
    # Handle "today"
    if date_str == "today":
        return today.strftime("%Y-%m-%d")
    
    # Handle relative dates like "1 day ago", "-1 day", "10 days ago", "-10 days"
    relative_match = re.match(r'(-?\d+)\s*(day|days|week|weeks|month|months)\s*(ago)?', date_str)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        
        # If "ago" is present, make amount negative
        if relative_match.group(3) == "ago" and amount > 0:
            amount = -amount
        
        # Convert to days
        if unit in ("week", "weeks"):
            days = amount * 7
        elif unit in ("month", "months"):
            days = amount * 30  # Approximate
        else:
            days = amount
        
        result_date = today + timedelta(days=days)
        return result_date.strftime("%Y-%m-%d")
    
    # Try to parse as absolute date (YYYY-MM-DD)
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD, 'today', or 'N days ago'")


def filter_tenders_by_date(
    data_path: Path,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    days: Optional[int] = None,
    filter_by_deadline_date: bool = True,
    filter_by_published_date: bool = False
) -> List[Dict[str, Any]]:
    """
    Filter tenders from main data file by date range.
    
    Args:
        data_path: Path to tenders.jsonl file
        date_from: Start date (YYYY-MM-DD or relative like "today", "1 day ago")
        date_to: End date (YYYY-MM-DD or relative like "today")
        days: Number of days (alternative to date_to)
        filter_by_deadline_date: Filter by deadline_date (default: True)
        filter_by_published_date: Filter by published_date (default: False)
    
    Returns:
        List of tender data dicts with tender_number, tender_id, detail_url
    """
    # Parse dates
    today = datetime.now().date()
    
    if days is not None:
        # If days is provided, calculate date_from and date_to
        if date_from:
            # date_from is provided, date_to = date_from + days
            date_from_parsed = parse_date(date_from)
            date_from_dt = datetime.strptime(date_from_parsed, "%Y-%m-%d").date()
            date_to_dt = date_from_dt + timedelta(days=days)
            date_to_parsed = date_to_dt.strftime("%Y-%m-%d")
        else:
            # date_from not provided, use today - days to today
            date_to_parsed = today.strftime("%Y-%m-%d")
            date_from_dt = today - timedelta(days=days)
            date_from_parsed = date_from_dt.strftime("%Y-%m-%d")
    else:
        # Use provided dates or defaults
        if date_from:
            date_from_parsed = parse_date(date_from)
        else:
            date_from_parsed = today.strftime("%Y-%m-%d")
        
        if date_to:
            date_to_parsed = parse_date(date_to)
        else:
            date_to_parsed = today.strftime("%Y-%m-%d")
    
    logger.info(f"Filtering tenders by date range: {date_from_parsed} to {date_to_parsed}")
    logger.info(f"  - Filter by deadline_date: {filter_by_deadline_date}")
    logger.info(f"  - Filter by published_date: {filter_by_published_date}")
    
    # Load and filter tenders
    filtered_tenders = []
    total_tenders = 0
    
    with open(data_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                record = json.loads(line.strip())
                total_tenders += 1
                
                # Extract tender number
                tender_number = record.get("number") or record.get("tender_number")
                if not tender_number:
                    # Try to extract from all_cells
                    all_cells = record.get("all_cells", "")
                    tender_num_match = re.search(r'([A-Z]{2,4}\d{9,})', all_cells)
                    if tender_num_match:
                        tender_number = tender_num_match.group(1)
                    else:
                        continue
                
                # Check date filters
                matches = False
                
                # Check deadline_date
                if filter_by_deadline_date:
                    deadline_date = record.get("deadline_date")
                    if deadline_date:
                        try:
                            deadline_dt = datetime.strptime(deadline_date, "%Y-%m-%d").date()
                            date_from_dt = datetime.strptime(date_from_parsed, "%Y-%m-%d").date()
                            date_to_dt = datetime.strptime(date_to_parsed, "%Y-%m-%d").date()
                            
                            if date_from_dt <= deadline_dt <= date_to_dt:
                                matches = True
                        except (ValueError, TypeError):
                            pass
                
                # Check published_date
                if not matches and filter_by_published_date:
                    published_date = record.get("published_date")
                    if published_date:
                        try:
                            published_dt = datetime.strptime(published_date, "%Y-%m-%d").date()
                            date_from_dt = datetime.strptime(date_from_parsed, "%Y-%m-%d").date()
                            date_to_dt = datetime.strptime(date_to_parsed, "%Y-%m-%d").date()
                            
                            if date_from_dt <= published_dt <= date_to_dt:
                                matches = True
                        except (ValueError, TypeError):
                            pass
                
                # If no date filters enabled, include all
                if not filter_by_deadline_date and not filter_by_published_date:
                    matches = True
                
                if matches:
                    tender_id = record.get("tender_id")
                    detail_url = record.get("detail_url")
                    
                    # Build detail_url if we have tender_id but no detail_url
                    if tender_id and not detail_url:
                        detail_url = f"https://tenders.procurement.gov.ge/public/?go={tender_id}&lang=ge"
                    
                    filtered_tenders.append({
                        "tender_number": tender_number,
                        "tender_id": tender_id,
                        "detail_url": detail_url
                    })
            
            except json.JSONDecodeError as e:
                logger.debug(f"Error parsing line {line_num}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Error processing line {line_num}: {e}")
                continue
    
    logger.info(f"Filtered {len(filtered_tenders)} tenders from {total_tenders} total tenders")
    with_id = sum(1 for t in filtered_tenders if t.get("tender_id"))
    logger.info(f"  - {with_id} have tender_id (can use direct URL)")
    logger.info(f"  - {len(filtered_tenders) - with_id} need search method")
    
    return filtered_tenders


def load_tender_id_from_main_data(tender_number: str, data_path: Path = None) -> Optional[Dict[str, str]]:
    """
    Load tender_id and detail_url from main tenders.jsonl file.
    
    Args:
        tender_number: Tender number to look up (e.g., "GEO250000505")
        data_path: Path to tenders.jsonl (defaults to data/tenders.jsonl)
    
    Returns:
        Dictionary with 'tender_id' and 'detail_url' if found, None otherwise
    """
    if data_path is None:
        # Default to data/tenders.jsonl in project root
        project_root = Path(__file__).parent.parent
        data_path = project_root / "data" / "tenders.jsonl"
    
    if not data_path.exists():
        logger.debug(f"[TENDER_ID_LOOKUP] Main data file not found: {data_path}")
        return None
    
    tender_number_upper = tender_number.upper()
    logger.debug(f"[TENDER_ID_LOOKUP] Looking up tender_id for {tender_number_upper} in {data_path}")
    
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line.strip())
                    # Check both 'number' and 'tender_number' fields
                    record_number = (record.get("number") or record.get("tender_number", "")).upper()
                    
                    if record_number == tender_number_upper:
                        tender_id = record.get("tender_id")
                        detail_url = record.get("detail_url")
                        
                        # Build detail_url if we have tender_id but no detail_url
                        if tender_id and not detail_url:
                            detail_url = f"https://tenders.procurement.gov.ge/public/?go={tender_id}&lang=ge"
                        
                        if tender_id or detail_url:
                            logger.info(f"[TENDER_ID_LOOKUP] ✅ Found tender_id for {tender_number_upper}: {tender_id}, detail_url: {detail_url}")
                            return {
                                "tender_id": tender_id,
                                "detail_url": detail_url
                            }
                        else:
                            logger.debug(f"[TENDER_ID_LOOKUP] Found record but no tender_id or detail_url")
                except json.JSONDecodeError as e:
                    logger.debug(f"[TENDER_ID_LOOKUP] Error parsing line {line_num}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"[TENDER_ID_LOOKUP] Error processing line {line_num}: {e}")
                    continue
        
        logger.debug(f"[TENDER_ID_LOOKUP] ❌ Tender {tender_number_upper} not found in main data file")
        return None
    except Exception as e:
        logger.warning(f"[TENDER_ID_LOOKUP] Error reading main data file: {e}")
        return None


@dataclass
class DetailScraperConfig:
    """Configuration for detailed scraper."""
    base_url: str
    headless: bool
    page_pause_ms: int
    output_path: Path
    max_retries: int


@dataclass
class DetailSelectors:
    """CSS selectors for detail page elements."""
    tender_number_input: str
    search_button: str
    detail_panel: str
    detail_title: str
    detail_content: str
    close_button: str


class JsonLinesWriter:
    """Writer for JSONL format with automatic deduplication and file locking."""
    
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = asyncio.Lock()
    
    async def write_async(self, record: Dict[str, Any]) -> None:
        """
        Write a record to JSONL file, automatically removing duplicates.
        Thread-safe version using asyncio.Lock.
        """
        async with self.lock:
            self.write(record)

    def write(self, record: Dict[str, Any]) -> None:
        """
        Write a record to JSONL file, automatically removing duplicates.
        If a tender with the same number already exists, it will be replaced.
        
        This implementation uses file locking to prevent race conditions when
        multiple workers are writing concurrently.
        """
        import json
        import fcntl
        import tempfile
        import shutil
        
        # Support both 'number' and 'tender_number' for backward compatibility
        tender_num = record.get('number', record.get('tender_number', '')).upper()
        if not tender_num:
            # No tender number - just append with lock
            with self.output_path.open("a", encoding="utf-8") as fh:
                # Acquire exclusive lock
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                try:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                finally:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            return
        
        # Create a lock file for this operation
        lock_file_path = self.output_path.with_suffix('.lock')
        
        # Use a lock file to ensure only one process writes at a time
        with open(lock_file_path, 'w') as lock_file:
            # Acquire exclusive lock on the lock file
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            
            try:
                # Check if file exists and if duplicate exists
                duplicate_found = False
                
                if self.output_path.exists():
                    # First pass: check if duplicate exists
                    with self.output_path.open("r", encoding="utf-8") as fh:
                        for line in fh:
                            if line.strip():
                                try:
                                    existing_record = json.loads(line.strip())
                                    existing_num = existing_record.get('number', existing_record.get('tender_number', '')).upper()
                                    if existing_num == tender_num:
                                        duplicate_found = True
                                        break
                                except:
                                    pass
                
                if duplicate_found:
                    # Need to rewrite file to remove duplicate
                    logger = logging.getLogger("detailed_scraper")
                    logger.debug(f"Removing duplicate record for {tender_num}")
                    
                    # Read all records except the duplicate
                    records_to_keep = []
                    with self.output_path.open("r", encoding="utf-8") as fh:
                        for line in fh:
                            if line.strip():
                                try:
                                    existing_record = json.loads(line.strip())
                                    existing_num = existing_record.get('number', existing_record.get('tender_number', '')).upper()
                                    if existing_num != tender_num:
                                        records_to_keep.append(line.strip())
                                except:
                                    # Keep invalid lines
                                    records_to_keep.append(line.strip())
                    
                    # Write to temporary file first (atomic operation)
                    temp_fd, temp_path = tempfile.mkstemp(dir=self.output_path.parent, text=True)
                    try:
                        with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_fh:
                            # Write all kept records
                            for record_line in records_to_keep:
                                temp_fh.write(record_line + "\n")
                            # Append new record
                            temp_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                        
                        # Atomic replace
                        shutil.move(temp_path, self.output_path)
                    except:
                        # Clean up temp file on error
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                        raise
                else:
                    # No duplicate - just append
                    with self.output_path.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                        
            finally:
                # Release lock
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)




class DetailedTenderScraper:
    """Scraper for detailed tender information."""
    
    def __init__(self, config: DetailScraperConfig, selectors: DetailSelectors, browser: Optional[Browser] = None, page: Optional[Page] = None, writer: Optional[JsonLinesWriter] = None):
        self.config = config
        self.selectors = selectors
        self.browser: Optional[Browser] = browser
        self.page: Optional[Page] = page
        self.writer = writer if writer else JsonLinesWriter(config.output_path)
        self.log = logging.getLogger("detailed_scraper")
        self._own_browser = browser is None
        self._own_page = page is None

    def get_existing_tender_numbers(self) -> set[str]:
        """Get set of tender numbers that have already been scraped."""
        existing = set()
        if not self.config.output_path.exists():
            return existing
            
        try:
            with open(self.config.output_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # Check both 'number' and 'tender_number'
                        num = record.get("number") or record.get("tender_number")
                        if num:
                            existing.add(num)
                    except:
                        pass
        except Exception as e:
            self.log.warning(f"Error reading existing file: {e}")
            
        return existing
    
    async def __aenter__(self) -> "DetailedTenderScraper":
        """Async context manager entry."""
        if self._own_browser:
            self.log.debug("Launching Chromium (headless=%s)", self.config.headless)
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=self.config.headless)
        
        if self._own_page:
            assert self.browser is not None
            context = await self.browser.new_context()
            self.page = await context.new_page()
            
        return self
    
    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Async context manager exit."""
        if self._own_page and self.page:
            await self.page.close()
            
        if self._own_browser and self.browser:
            await self.browser.close()
    
    async def scrape_tender_detail(
        self, 
        tender_number: str, 
        tender_id: Optional[str] = None,
        detail_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed information for a specific tender number.
        
        Args:
            tender_number: Tender number (e.g., "GEO250000579")
            tender_id: Optional tender ID (e.g., "657645") - if provided, uses direct URL
            detail_url: Optional direct detail URL - fastest method if available
            
        Returns:
            Dictionary with detailed tender information, or None if failed
        """
        assert self.page is not None
        
        try:
            self.log.info(f"[WORKFLOW] ===== START Scraping tender: {tender_number} =====")
            
            # ====================================================================
            # STEP 0: LOOKUP TENDER_ID FROM MAIN DATA (PREFERRED METHOD)
            # ====================================================================
            # First, try to get tender_id from tenders.jsonl to use direct URL method
            # This is the fastest and most reliable method
            if not detail_url and not tender_id:
                self.log.debug(f"[WORKFLOW STEP 0] Looking up tender_id from main data file...")
                main_data_info = load_tender_id_from_main_data(tender_number)
                if main_data_info:
                    tender_id = main_data_info.get("tender_id")
                    detail_url = main_data_info.get("detail_url")
                    if tender_id or detail_url:
                        self.log.info(f"[WORKFLOW STEP 0] ✅ Found tender_id in main data, will use direct URL method")
                    else:
                        self.log.debug(f"[WORKFLOW STEP 0] No tender_id found in main data, will use search method")
                else:
                    self.log.debug(f"[WORKFLOW STEP 0] Tender not found in main data, will use search method")
            
            # ====================================================================
            # STEP 1: NAVIGATION - Choose the fastest method to reach tender page
            # ====================================================================
            # Method 1: Use direct URL if provided (fastest - no search needed)
            if detail_url:
                self.log.info(f"[WORKFLOW STEP 1] Using direct URL method (fastest - from main data or parameter)")
                self.log.debug(f"[WORKFLOW] URL: {detail_url}")
                await self.page.goto(detail_url, wait_until="networkidle")
                await asyncio.sleep(self.config.page_pause_ms / 1000)
                self.log.debug(f"[WORKFLOW] Navigation complete, current URL: {self.page.url}")
            # Method 2: Build URL from tender_id if provided (fast - direct navigation)
            elif tender_id:
                detail_url = f"https://tenders.procurement.gov.ge/public/?go={tender_id}&lang=ge"
                self.log.info(f"[WORKFLOW STEP 1] Using tender ID method (fast - from main data or parameter)")
                self.log.debug(f"[WORKFLOW] Built URL from tender_id: {detail_url}")
                await self.page.goto(detail_url, wait_until="networkidle")
                await asyncio.sleep(self.config.page_pause_ms / 1000)
                self.log.debug(f"[WORKFLOW] Navigation complete, current URL: {self.page.url}")
            # Method 3: Search by tender number (slowest - requires search + click, only if not in main data)
            else:
                self.log.info(f"[WORKFLOW STEP 1] Using search method (requires search + click)")
                self.log.debug(f"[WORKFLOW] Navigating to base URL: {self.config.base_url}")
                await self.page.goto(self.config.base_url, wait_until="networkidle")
                await asyncio.sleep(self.config.page_pause_ms / 1000)
                self.log.debug(f"[WORKFLOW] Base page loaded, current URL: {self.page.url}")
                
                # ====================================================================
                # STEP 2: SEARCH - Enter tender number and click search
                # ====================================================================
                self.log.info(f"[WORKFLOW STEP 2] Performing search for: {tender_number}")
                self.log.debug(f"[WORKFLOW] Filling search input: {self.selectors.tender_number_input}")
                await self.page.fill(self.selectors.tender_number_input, tender_number)
                await asyncio.sleep(0.5)
                
                self.log.debug(f"[WORKFLOW] Clicking search button: {self.selectors.search_button}")
                await self.page.click(self.selectors.search_button)
                
                # Wait for results table to appear
                self.log.debug(f"[WORKFLOW] Waiting for search results to appear...")
                try:
                    await self.page.wait_for_selector(
                        "tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow",
                        timeout=5000,
                        state='attached'
                    )
                    self.log.debug(f"[WORKFLOW] Search results appeared")
                except Exception:
                    self.log.warning("[WORKFLOW] Search results wait timeout, continuing anyway")
                
                # ====================================================================
                # STEP 3: FIND RESULT ROWS - Locate search result rows in the table
                # ====================================================================
                self.log.info(f"[WORKFLOW STEP 3] Finding search result rows")
                # Tender rows have id="A{number}" or onclick="ShowApp({number},...)"
                tender_row = None
                try:
                    # Try multiple selectors for result rows (in order of specificity)
                    possible_selectors = [
                        "tr[id^='A']",  # Rows with id starting with "A" (most specific)
                        "tr[onclick*='ShowApp']",  # Rows with ShowApp in onclick
                        ".noticeRow",  # Notice row class
                        "table tbody tr",  # Any table row (fallback)
                    ]
                    
                    rows = []
                    for selector in possible_selectors:
                        try:
                            self.log.debug(f"[WORKFLOW] Trying selector: {selector}")
                            found_rows = await self.page.query_selector_all(selector)
                            if found_rows and len(found_rows) > 0:
                                rows = found_rows
                                self.log.info(f"[WORKFLOW] Found {len(rows)} search results using selector: {selector}")
                                break
                        except Exception as e:
                            self.log.debug(f"[WORKFLOW] Selector {selector} failed: {e}")
                            continue
                    
                    if not rows:
                        raise Exception("No result rows found after search")
                    
                    # ====================================================================
                    # STEP 4: CLICK THROUGH RESULTS - Try each result until we find the correct tender
                    # ====================================================================
                    # Strategy: Click each row and verify AFTER clicking (more reliable than pre-matching)
                    # IMPORTANT: We use index-based approach to avoid stale element references
                    tender_row = None
                    max_rows_to_try = min(len(rows), 10)
                    self.log.info(f"[WORKFLOW STEP 4] Checking {max_rows_to_try} results to find correct tender...")
                    for idx in range(max_rows_to_try):
                        try:
                            self.log.info(f"[WORKFLOW] Trying result {idx + 1}/{max_rows_to_try}...")
                            
                            if idx >= len(rows):
                                self.log.debug(f"[WORKFLOW] Index {idx} out of range, breaking")
                                break
                            
                            # Get fresh row reference (avoid stale element issues)
                            try:
                                self.log.debug(f"[WORKFLOW] Getting fresh row reference for index {idx}")
                                fresh_rows = await self.page.query_selector_all("tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow")
                                if idx >= len(fresh_rows):
                                    self.log.debug(f"[WORKFLOW] Row count changed, updating rows list")
                                    rows = fresh_rows
                                    if idx >= len(rows):
                                        break
                                row = fresh_rows[idx] if fresh_rows else None
                                if not row:
                                    self.log.debug(f"[WORKFLOW] Row {idx} not found, skipping")
                                    continue
                            except Exception as e:
                                self.log.debug(f"[WORKFLOW] Error getting fresh rows: {e}")
                                continue
                            
                            # Record URL before click to detect navigation
                            url_before_click = self.page.url
                            self.log.debug(f"[WORKFLOW] URL before click: {url_before_click}")
                            
                            # ====================================================================
                            # STEP 4.1: WAIT FOR OVERLAY - Ensure no blocking overlay is present
                            # ====================================================================
                            self.log.debug(f"[WORKFLOW] Checking for blocking overlay before click...")
                            try:
                                overlay_exists = await self.page.evaluate("""() => {
                                    const overlay = document.querySelector('.blockUI.blockOverlay');
                                    return overlay && window.getComputedStyle(overlay).display !== 'none';
                                }""")
                                if overlay_exists:
                                    self.log.debug(f"[WORKFLOW] Overlay detected, waiting for it to disappear...")
                                    for wait_attempt in range(10):
                                        overlay_still_exists = await self.page.evaluate("""() => {
                                            const overlay = document.querySelector('.blockUI.blockOverlay');
                                            return overlay && window.getComputedStyle(overlay).display !== 'none';
                                        }""")
                                        if not overlay_still_exists:
                                            self.log.debug(f"[WORKFLOW] Overlay disappeared after {wait_attempt + 1} attempts")
                                            break
                                        await asyncio.sleep(0.5)
                                else:
                                    self.log.debug(f"[WORKFLOW] No overlay detected")
                            except Exception as e:
                                self.log.debug(f"[WORKFLOW] Error checking overlay: {e}")
                                pass
                            
                            await asyncio.sleep(0.2)  # Small delay before click
                            
                            # ====================================================================
                            # STEP 4.2: CLICK ROW - Click the result row with retry logic
                            # ====================================================================
                            self.log.debug(f"[WORKFLOW] Attempting to click row {idx + 1}...")
                            click_success = False
                            for click_attempt in range(3):  # Max 3 retry attempts
                                self.log.debug(f"[WORKFLOW] Click attempt {click_attempt + 1}/3")
                                try:
                                    overlay_blocking = await self.page.evaluate("""() => {
                                        const overlay = document.querySelector('.blockUI.blockOverlay');
                                        if (!overlay) return false;
                                        const style = window.getComputedStyle(overlay);
                                        return style.display !== 'none' && style.pointerEvents !== 'none';
                                    }""")
                                    
                                    if overlay_blocking:
                                        await asyncio.sleep(0.8)
                                        try:
                                            fresh_rows = await self.page.query_selector_all("tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow")
                                            if idx < len(fresh_rows):
                                                row = fresh_rows[idx]
                                        except:
                                            pass
                                        continue
                                    
                                    await row.click()
                                    click_success = True
                                    self.log.debug(f"[WORKFLOW] ✅ Successfully clicked row {idx + 1}")
                                    break
                                    
                                except Exception as click_error:
                                    error_str = str(click_error)
                                    if 'blockUI' in error_str or 'intercepts pointer' in error_str or 'not attached' in error_str:
                                        await asyncio.sleep(1)
                                        try:
                                            fresh_rows = await self.page.query_selector_all("tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow")
                                            if idx < len(fresh_rows):
                                                row = fresh_rows[idx]
                                            else:
                                                rows = fresh_rows
                                                max_rows_to_try = min(len(rows), 10)
                                                if idx >= len(rows):
                                                    break
                                        except:
                                            break
                                    else:
                                        raise
                            
                            if not click_success:
                                self.log.warning(f"[WORKFLOW] ❌ Could not click result {idx + 1} after 3 attempts, trying next...")
                                # Re-navigate to search page if click failed
                                try:
                                    self.log.debug(f"[WORKFLOW] Re-navigating to search page...")
                                    await self.page.goto(self.config.base_url, wait_until="domcontentloaded")
                                    await asyncio.sleep(1)
                                    await self.page.fill(self.selectors.tender_number_input, tender_number)
                                    await self.page.click(self.selectors.search_button)
                                    await asyncio.sleep(1)
                                    rows = await self.page.query_selector_all("tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow")
                                    max_rows_to_try = min(len(rows), 10)
                                    if not rows:
                                        self.log.warning(f"[WORKFLOW] No rows found after re-navigation, breaking")
                                        break
                                except Exception as e:
                                    self.log.debug(f"[WORKFLOW] Error during re-navigation: {e}")
                                    pass
                                continue
                            
                            # ====================================================================
                            # STEP 4.3: VERIFY NAVIGATION - Check if click caused navigation or panel open
                            # ====================================================================
                            self.log.debug(f"[WORKFLOW] Waiting for click to register...")
                            await asyncio.sleep(0.15)  # Small delay for click to register
                            
                            url_after_click = self.page.url
                            navigation_occurred = (url_after_click != url_before_click)
                            self.log.debug(f"[WORKFLOW] URL after click: {url_after_click}")
                            self.log.debug(f"[WORKFLOW] Navigation occurred: {navigation_occurred}")
                            
                            # Wait for page/panel to load based on navigation type
                            if navigation_occurred:
                                self.log.debug(f"[WORKFLOW] Full page navigation detected, waiting for load...")
                                try:
                                    await self.page.wait_for_load_state("domcontentloaded", timeout=2000)
                                    self.log.debug(f"[WORKFLOW] Page loaded")
                                except Exception as e:
                                    self.log.debug(f"[WORKFLOW] Load wait timeout: {e}")
                                    pass
                            else:
                                self.log.debug(f"[WORKFLOW] Panel/modal navigation detected, waiting for panel...")
                                try:
                                    # Wait for panel to appear
                                    await self.page.wait_for_selector(
                                        '#noticeContent, #app, .ui-tabs-panel',
                                        timeout=1500,
                                        state='attached'
                                    )
                                    self.log.debug(f"[WORKFLOW] Panel appeared")
                                    
                                    # CRITICAL: Wait for panel content to update (not just appear)
                                    # Sometimes panel appears but content is still from previous tender
                                    await asyncio.sleep(0.5)  # Give time for content to update
                                    
                                    # Verify panel content has updated by checking if it contains any text
                                    for wait_attempt in range(5):
                                        panel_text_check = await self.page.evaluate("""() => {
                                            const panel = document.querySelector('#noticeContent') || document.querySelector('#app');
                                            if (!panel) return {hasContent: false, length: 0};
                                            const text = (panel.innerText || panel.textContent || '').trim();
                                            return {hasContent: text.length > 100, length: text.length};
                                        }""")
                                        if panel_text_check.get('hasContent'):
                                            self.log.debug(f"[WORKFLOW] Panel content updated: {panel_text_check.get('length')} chars")
                                            break
                                        await asyncio.sleep(0.3)
                                        self.log.debug(f"[WORKFLOW] Waiting for panel content to update (attempt {wait_attempt + 1}/5)...")
                                    
                                except Exception as e:
                                    self.log.debug(f"[WORKFLOW] Panel wait timeout: {e}")
                                    pass
                                await asyncio.sleep(0.3)
                            
                            # ====================================================================
                            # STEP 4.4: VERIFY TENDER - Check if the opened page is the correct tender
                            # ====================================================================
                            self.log.debug(f"[WORKFLOW] Extracting page text to verify tender number...")
                            # Try multiple methods to extract and verify tender number
                            verification_result = await self.page.evaluate("""(tenderNum) => {
                                // Method 1: Check in detail panel
                                const panel = document.querySelector('#noticeContent') || document.querySelector('#app');
                                let panelText = '';
                                if (panel) {
                                    panelText = (panel.innerText || panel.textContent || '').toLowerCase();
                                }
                                
                                // Method 2: Check in page title/headings
                                const headings = document.querySelectorAll('h1, h2, h3, .noticeTitle, strong');
                                let headingText = '';
                                headings.forEach(h => {
                                    headingText += (h.innerText || h.textContent || '').toLowerCase() + ' ';
                                });
                                
                                // Method 3: Check in URL
                                const urlText = window.location.href.toLowerCase();
                                
                                // Method 4: Check in active tab content
                                const activeTab = document.querySelector('.ui-tabs-panel:not([style*="display: none"])');
                                let tabText = '';
                                if (activeTab) {
                                    tabText = (activeTab.innerText || activeTab.textContent || '').toLowerCase();
                                }
                                
                                // Combine all text sources
                                const allText = (panelText + ' ' + headingText + ' ' + urlText + ' ' + tabText).toLowerCase();
                                
                                // Check if tender number appears anywhere
                                const tenderLower = tenderNum.toLowerCase();
                                const foundInPanel = panelText.includes(tenderLower);
                                const foundInHeadings = headingText.includes(tenderLower);
                                const foundInUrl = urlText.includes(tenderLower);
                                const foundInTab = tabText.includes(tenderLower);
                                const foundInAll = allText.includes(tenderLower);
                                
                                // Also try to find in structured elements (like "განცხადების ნომერი: GEO250000505")
                                const numberElements = document.querySelectorAll('td, .tender-number, [id*="number"], [class*="number"]');
                                let foundInElements = false;
                                for (const el of numberElements) {
                                    const elText = (el.innerText || el.textContent || '').toLowerCase();
                                    if (elText.includes(tenderLower)) {
                                        foundInElements = true;
                                        break;
                                    }
                                }
                                
                                // CRITICAL: Check for exact match in tender number field
                                // Look for "განცხადების ნომერი" or "განცხადების ნომერი:" followed by the tender number
                                let foundInTenderNumberField = false;
                                const tenderNumberPatterns = [
                                    'განცხადების ნომერი',
                                    'განცხადების ნომერი:',
                                    'tender number',
                                    'number'
                                ];
                                
                                // Check in panel text for tender number field
                                for (const pattern of tenderNumberPatterns) {
                                    const patternIndex = panelText.indexOf(pattern.toLowerCase());
                                    if (patternIndex !== -1) {
                                        // Check if tender number appears after this pattern (within 50 chars)
                                        const afterPattern = panelText.substring(patternIndex, patternIndex + 50);
                                        if (afterPattern.includes(tenderLower)) {
                                            foundInTenderNumberField = true;
                                            break;
                                        }
                                    }
                                }
                                
                                // Also check in table cells that might contain tender number
                                const tableCells = document.querySelectorAll('table td');
                                for (const cell of tableCells) {
                                    const cellText = (cell.innerText || cell.textContent || '').toLowerCase();
                                    // Check if cell contains "განცხადების ნომერი" or similar
                                    if (cellText.includes('განცხადების') || cellText.includes('ნომერი')) {
                                        // Check if next cell or same cell contains tender number
                                        const nextCell = cell.nextElementSibling;
                                        if (nextCell) {
                                            const nextText = (nextCell.innerText || nextCell.textContent || '').toLowerCase();
                                            if (nextText.includes(tenderLower)) {
                                                foundInTenderNumberField = true;
                                                break;
                                            }
                                        }
                                        if (cellText.includes(tenderLower)) {
                                            foundInTenderNumberField = true;
                                            break;
                                        }
                                    }
                                }
                                
                                return {
                                    found: foundInTenderNumberField || (foundInPanel && foundInHeadings) || foundInUrl,
                                    foundInPanel,
                                    foundInHeadings,
                                    foundInUrl,
                                    foundInTab,
                                    foundInElements,
                                    foundInTenderNumberField,
                                    panelTextLength: panelText.length,
                                    allTextLength: allText.length
                                };
                            }""", tender_number)
                            
                            # Check if this is the correct tender
                            # Require either: tender number field match OR (panel + headings match) OR URL match
                            if verification_result.get('found'):
                                self.log.info(f"[WORKFLOW] ✅ Found correct tender {tender_number} (result {idx + 1})")
                                self.log.debug(f"[WORKFLOW] Verification details: "
                                             f"tenderNumberField={verification_result.get('foundInTenderNumberField')}, "
                                             f"panel={verification_result.get('foundInPanel')}, "
                                             f"headings={verification_result.get('foundInHeadings')}, "
                                             f"url={verification_result.get('foundInUrl')}, "
                                             f"tab={verification_result.get('foundInTab')}, "
                                             f"elements={verification_result.get('foundInElements')}")
                                tender_row = idx
                                break
                            else:
                                self.log.debug(f"[WORKFLOW] ❌ Tender number {tender_number} not found in any text source")
                                self.log.debug(f"[WORKFLOW] Panel text length: {verification_result.get('panelTextLength', 0)} chars")
                            
                            # ====================================================================
                            # STEP 4.5: GO BACK IF WRONG - Return to search if wrong tender opened
                            # ====================================================================
                            # If not the correct tender, go back to search results
                            # Try browser back first (faster), fallback to re-navigation
                            if idx < max_rows_to_try - 1:
                                self.log.debug(f"[WORKFLOW] Wrong tender opened, going back to search results...")
                                try:
                                    # Try browser back button first
                                    await self.page.go_back(wait_until="domcontentloaded", timeout=3000)
                                    await asyncio.sleep(0.3)
                                    # Verify we're back on search page
                                    current_url = self.page.url
                                    if self.config.base_url not in current_url:
                                        # Back didn't work, re-navigate
                                        raise Exception("Back navigation failed")
                                    # Check if search results are still there
                                    rows = await self.page.query_selector_all("tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow")
                                    if not rows or len(rows) == 0:
                                        # Need to re-search
                                        raise Exception("No search results after back")
                                    self.log.debug(f"Used browser back, found {len(rows)} results")
                                except Exception:
                                    # Fallback: re-navigate and search
                                    self.log.debug("Browser back failed, re-navigating to search")
                                    await self.page.goto(self.config.base_url, wait_until="domcontentloaded")
                                    await asyncio.sleep(0.3)  # Reduced from 0.5
                                    await self.page.fill(self.selectors.tender_number_input, tender_number)
                                    await self.page.click(self.selectors.search_button)
                                    try:
                                        await self.page.wait_for_selector(
                                            "tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow",
                                            timeout=5000,
                                            state='attached'
                                        )
                                    except Exception:
                                        pass
                                    await asyncio.sleep(0.3)  # Reduced from 0.5
                                    rows = await self.page.query_selector_all("tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow")
                                max_rows_to_try = min(len(rows), 10)
                                if not rows:
                                    break
                        
                        except Exception as e:
                            self.log.warning(f"Error trying result {idx + 1}: {e}")
                            # Check if navigation happened despite error
                            current_url = self.page.url
                            if "?go=" in current_url or "#" in current_url:
                                try:
                                    page_text = await self.page.evaluate("""() => {
                                        const panel = document.querySelector('#noticeContent') || document.querySelector('#app') || document.body;
                                        return (panel.innerText || panel.textContent || '').toLowerCase();
                                    }""")
                                    if tender_number.lower() in page_text:
                                        tender_match = re.search(rf'\b{re.escape(tender_number)}\b', page_text, re.IGNORECASE)
                                        if tender_match:
                                            self.log.info(f"✅ Found correct tender {tender_number} (result {idx + 1})")
                                            tender_row = idx
                                            break
                                except:
                                    pass
                            
                            # Try to go back to search if possible
                            # Use browser back first (faster)
                            try:
                                try:
                                    await self.page.go_back(wait_until="domcontentloaded", timeout=3000)
                                    await asyncio.sleep(0.3)
                                    current_url = self.page.url
                                    if self.config.base_url not in current_url:
                                        raise Exception("Back navigation failed")
                                    rows = await self.page.query_selector_all("tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow")
                                    if not rows or len(rows) == 0:
                                        raise Exception("No search results after back")
                                    self.log.debug(f"Used browser back after error, found {len(rows)} results")
                                except Exception:
                                    # Fallback: re-navigate
                                    self.log.debug("Browser back failed after error, re-navigating")
                                    await self.page.goto(self.config.base_url, wait_until="domcontentloaded")
                                    await asyncio.sleep(0.5)  # Reduced from 1
                                    await self.page.fill(self.selectors.tender_number_input, tender_number)
                                    await self.page.click(self.selectors.search_button)
                                    try:
                                        await self.page.wait_for_selector(
                                            "tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow",
                                            timeout=5000,
                                            state='attached'
                                        )
                                    except:
                                        pass
                                    await asyncio.sleep(0.5)  # Reduced from 1
                                    rows = await self.page.query_selector_all("tr[id^='A'], tr[onclick*='ShowApp'], .noticeRow")
                                max_rows_to_try = min(len(rows), 10)
                                if not rows:
                                    break
                            except Exception:
                                break
                            continue
                    
                    if tender_row is None:
                        raise Exception(f"Could not find tender {tender_number} after trying {max_rows_to_try} results")
                            
                except Exception as e:
                    self.log.error(f"Error finding tender row: {e}")
                    raise
                
                # We've already clicked and verified the correct tender, so continue with extraction
                # Ensure page is fully loaded
                try:
                    await self.page.wait_for_load_state("domcontentloaded", timeout=3000)
                except Exception:
                    pass
            
            # Wait for page to be fully loaded before extracting
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=3000)
            except Exception:
                pass
            
            # NOW extract tender link from the detail page (AFTER clicking)
            # Retry mechanism - wait and try multiple times if link not found
            extracted_link = None
            extracted_tender_id = None
            max_retries = 3
            retry_delay = 1.0  # seconds
            
            for attempt in range(max_retries):
                if attempt > 0:
                    self.log.debug(f"Retry attempt {attempt + 1}/{max_retries} to find tender link (waiting {retry_delay}s)...")
                    await asyncio.sleep(retry_delay)
                
                # Get page content - filter out search form elements (<option>, <select>, etc.)
                # These are from the search page, not actual tender data
                page_data = await self.page.evaluate("""() => {
                    // Get content from detail panel or main content area
                    let contentElement = document.querySelector('#noticeContent');
                    if (!contentElement) {
                        contentElement = document.querySelector('#app');
                    }
                    if (!contentElement) {
                        contentElement = document.body;
                    }
                    
                    // Clone to avoid modifying original
                    const contentClone = contentElement.cloneNode(true);
                    
                    // Remove ALL search form elements - these are huge and not actual data
                    // Remove: select, option, form, input, textarea (search forms)
                    const formsInContent = contentClone.querySelectorAll('select, option, form, input, textarea');
                    formsInContent.forEach(el => {
                        // Check if it's inside a form or is a search element
                        const parentForm = el.closest('form');
                        if (parentForm || el.tagName === 'SELECT' || el.tagName === 'OPTION' || el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                            el.remove();
                        }
                    });
                    
                    // Also remove any remaining option elements that might be orphaned
                    const remainingOptions = contentClone.querySelectorAll('option');
                    remainingOptions.forEach(el => el.remove());
                    
                    return {
                        html: contentClone.innerHTML || '',
                        text: contentClone.innerText || contentClone.textContent || '',
                        url: window.location.href
                    };
                }""")
                
                page_html = page_data.get('html', '')
                page_text = page_data.get('text', '')
                current_url = page_data.get('url', self.page.url)
                
                # Log content info (only on first attempt)
                if attempt == 0:
                    self.log.debug(f"Extracting link from page (text: {len(page_text)} chars, HTML: {len(page_html)} chars)")
                
                # Method 1: Look for link in page HTML (filtered, no form elements)
                patterns = [
                    r'შესყიდვის ბმული[:\s]*</?[^>]*>?\s*(https?://[^\s\n<"\'\)]+)',
                    r'შესყიდვის ბმული[:\s]+(https?://[^\s\n<"\'\)]+)',
                    r'ბმული[:\s]+(https?://tenders\.procurement\.gov\.ge[^\s\n<"\'\)]+)',
                    r'(http://tenders\.procurement\.gov\.ge/public/\?go=\d+&lang=ge)',
                    r'(https://tenders\.procurement\.gov\.ge/public/\?go=\d+&lang=ge)',
                ]
                
                for pattern in patterns:
                    link_match = re.search(pattern, page_html, re.IGNORECASE | re.DOTALL)
                    if link_match:
                        extracted_link = link_match.group(1)
                        self.log.debug(f"Found tender link: {extracted_link}")
                        break
                
                # If found, break out of retry loop
                if extracted_link:
                    break
                
                # Method 2: Look for link in page text
                if not extracted_link:
                    for pattern in [
                        r'შესყიდვის ბმული[:\s]+(https?://[^\s\n]+)',
                        r'ბმული[:\s]+(http://tenders\.procurement\.gov\.ge[^\s\n]+)',
                        r'(http://tenders\.procurement\.gov\.ge/public/\?go=\d+&lang=ge)',
                    ]:
                        link_match = re.search(pattern, page_text, re.IGNORECASE)
                        if link_match:
                            extracted_link = link_match.group(1)
                            self.log.debug(f"Found tender link in text: {extracted_link}")
                            break
                
                # If found, break out of retry loop
                if extracted_link:
                    break
                
                # Method 3: Check current URL
                if not extracted_link and "?go=" in current_url:
                    extracted_link = current_url
                    self.log.debug(f"Using current URL as tender link: {extracted_link}")
                    break
                
                # Method 4: Look for link elements in the detail content
                if not extracted_link:
                    link_elements = await self.page.query_selector_all('#noticeContent a[href*="?go="], #app a[href*="?go="], a[href*="?go="]')
                    for link_el in link_elements[:10]:  # Limit to first 10
                        try:
                            href = await link_el.get_attribute('href')
                            text = await link_el.inner_text()
                            # Skip if it's in a form or search element
                            is_in_form = await link_el.evaluate("""(el) => {
                                return el.closest('form, select') !== null;
                            }""")
                            if not is_in_form and href and ('?go=' in href or '&go=' in href):
                                if href.startswith('http'):
                                    extracted_link = href
                                else:
                                    extracted_link = f"https://tenders.procurement.gov.ge{href}" if href.startswith('/') else f"https://tenders.procurement.gov.ge/{href}"
                                self.log.debug(f"Found tender link in element: {extracted_link}")
                                break
                        except:
                            continue
                
                # If found, break out of retry loop
                if extracted_link:
                    break
            
            # Extract tender_id from the link (after all retries)
            if extracted_link:
                go_match = re.search(r'[?&]go=([^&]+)', extracted_link)
                if go_match:
                    extracted_tender_id = go_match.group(1)
                    self.log.debug(f"Extracted tender_id: {extracted_tender_id}")
                    detail_url = extracted_link
                    tender_id = extracted_tender_id
                else:
                    self.log.warning(f"Found link but no ?go= parameter: {extracted_link}")
            else:
                self.log.warning(f"Could not find tender link after {max_retries} attempts")
            
            # Check page state
            page_info = await self.page.evaluate("""() => {
                return {
                    hasNoticeContent: !!document.querySelector('#noticeContent'),
                    hasApp: !!document.querySelector('#app'),
                    hasApplicationTabs: !!document.querySelector('#application_tabs'),
                };
            }""")
            if page_info.get('hasApplicationTabs'):
                self.log.debug("Page has tabs, will extract from all tabs")
            
            # ====================================================================
            # STEP 5: EXTRACT DETAILED INFORMATION - Extract all data from the tender page
            # ====================================================================
            self.log.info(f"[WORKFLOW STEP 5] Extracting detailed information from tender page...")
            detail_data = await self.extract_detail_information(tender_number)
            
            if detail_data:
                # Get current URL after navigation/clicking
                current_url = self.page.url
                
                # Use the tender_id and detail_url we extracted from search results (if available)
                # These were set in the search method above when we found the row
                search_result_tender_id = tender_id  # This was set from search results if found
                search_result_detail_url = detail_url  # This was set from search results if found
                
                # Extract tender_id from URL if present (format: ?go=TENDER_ID)
                extracted_tender_id = None
                if "?go=" in current_url:
                    match = re.search(r'\?go=([^&]+)', current_url)
                    if match:
                        extracted_tender_id = match.group(1)
                        self.log.debug(f"Extracted tender_id from URL: {extracted_tender_id}")
                
                # If not in URL, try to extract from page content
                if not extracted_tender_id:
                    extracted_tender_id = await self.page.evaluate("""() => {
                        // Try to find tender ID in links
                        const links = document.querySelectorAll('a[href*="?go="], a[href*="&go="]');
                        for (const link of links) {
                            const href = link.getAttribute('href');
                            const match = href.match(/[?&]go=([^&]+)/);
                            if (match) return match[1];
                        }
                        
                        // Try to find in text content that might contain the link
                        const bodyText = document.body.innerText || '';
                        const linkMatch = bodyText.match(/tenders\.procurement\.gov\.ge[^\\s]*[?&]go=([^&\\s]+)/);
                        if (linkMatch) return linkMatch[1];
                        
                        return null;
                    }""")
                    
                    if extracted_tender_id:
                        self.log.debug(f"Extracted tender_id from page: {extracted_tender_id}")
                
                # Add metadata - ensure all required fields are set
                if "number" not in detail_data:
                    detail_data["number"] = detail_data.get("procurement_number", tender_number)
                if "procurement_number" not in detail_data:
                    detail_data["procurement_number"] = tender_number
                
                # Get the final tender_id (from search results, parameter, URL, or extracted)
                final_tender_id = search_result_tender_id or extracted_tender_id or detail_data.get("tender_id")
                if final_tender_id:
                    detail_data["tender_id"] = final_tender_id
                
                # Set detail_url - prefer the one extracted from search results
                if search_result_detail_url and "?go=" in search_result_detail_url:
                    detail_data["detail_url"] = search_result_detail_url
                elif "?go=" in current_url:
                    detail_data["detail_url"] = current_url
                elif final_tender_id:
                    constructed_url = f"https://tenders.procurement.gov.ge/public/?go={final_tender_id}&lang=ge"
                    detail_data["detail_url"] = constructed_url
                else:
                    self.log.warning(f"Could not determine tender link for {tender_number}")
                    detail_data["detail_url"] = current_url
                
                # Remove fields that are no longer needed
                detail_data.pop("tender_link", None)
                detail_data.pop("source_url", None)
                detail_data.pop("raw_html", None)
                detail_data.pop("html_content", None)
                detail_data.pop("full_text", None)  # Replaced by all_cells
                detail_data.pop("structured_sections", None)
                detail_data.pop("all_sections", None)
                
                detail_data["scraped_at"] = asyncio.get_event_loop().time()
                # Don't overwrite status - it should contain the actual tender status from parser
                # If status is missing, it means parsing failed, so set to error
                if not detail_data.get("status"):
                    detail_data["status"] = "error"
                    detail_data["error"] = "Could not extract tender status"
                # Add scraping status separately
                detail_data["scraping_status"] = "success"
                
                # Write to file
                await self.writer.write_async(detail_data)
                self.log.info(f"Successfully scraped details for {tender_number}")
                return detail_data
            else:
                self.log.warning(f"Could not extract details for {tender_number}")
                # Write error record
                error_record = {
                    "number": tender_number,
                    "scraped_at": asyncio.get_event_loop().time(),
                    "status": "error",
                    "error": "Could not extract detail information",
                    "extraction_method": "detailed"
                }

                await self.writer.write_async(error_record)
                return None
                
        except Exception as e:
            self.log.error(f"Error scraping {tender_number}: {e}", exc_info=True)
            # Write error record
            error_record = {
                "number": tender_number,
                "procurement_number": tender_number,
                "scraped_at": asyncio.get_event_loop().time(),
                "status": "error",
                "scraping_status": "error",
                "error": str(e),
                "extraction_method": "detailed"
            }

            await self.writer.write_async(error_record)
            return None
    
    async def extract_detail_information(self, tender_number: str) -> Optional[Dict[str, Any]]:
        """
        Extract detailed information from the detail panel/page.
        
        Extracts:
        - Tender link (შესყიდვის ბმული)
        - Full description
        - Documents/attachments
        - Timeline/status history
        - Contact information
        - All other available fields
        
        Also handles tabs if present - clicks through tabs to extract all data.
        """
        assert self.page is not None
        import sys
        from pathlib import Path
        
        # Add detailed_scraper directory to path for imports
        detailed_scraper_dir = Path(__file__).parent
        if str(detailed_scraper_dir) not in sys.path:
            sys.path.insert(0, str(detailed_scraper_dir))
        
        from detail_parser import TenderDetailParser
        
        try:
            # ====================================================================
            # STEP 5.1: EXTRACT FROM TABS - Get content from all tabs first
            # ====================================================================
            # This must happen BEFORE extracting the main content, so we can click through tabs
            # Tabs contain additional information: documents, bids, contracts, results
            self.log.debug(f"[WORKFLOW STEP 5.1] Detecting and extracting from all tabs...")
            tabs_data = await self._extract_from_all_tabs()
            self.log.debug(f"[WORKFLOW STEP 5.1] Tab extraction complete, found {len(tabs_data)} tabs")
            
            # ====================================================================
            # STEP 5.2: EXTRACT MAIN CONTENT - Get content from main detail panel
            # ====================================================================
            self.log.debug(f"[WORKFLOW STEP 5.2] Extracting main content from detail panel...")
            # Get page content (full HTML)
            content = await self.page.content()
            self.log.debug(f"[WORKFLOW] Page content size: {len(content)} chars")
            
            # Extract all text from detail panel (current active tab)
            # After clicking through tabs, get the final combined content
            self.log.debug(f"[WORKFLOW] Extracting text from detail panel...")
            detail_text = await self.page.evaluate("""() => {
                // Try multiple selectors for detail panel
                let panel = document.querySelector('#noticeContent');
                if (!panel) {
                    panel = document.querySelector('#app');
                }
                if (!panel) {
                    panel = document.querySelector('.ui-dialog-content');
                }
                if (!panel) {
                    // Look for any visible content div
                    const divs = document.querySelectorAll('div[style*="display: block"], div:not([style*="display: none"])');
                    for (const div of divs) {
                        if (div.innerText && div.innerText.length > 100) {
                            panel = div;
                            break;
                        }
                    }
                }
                
                // Also try to get content from active tab panel
                let activeTabPanel = null;
                // Try first selector
                activeTabPanel = document.querySelector('.ui-tabs-panel:not([style*="display: none"])');
                // If not found, try alternative
                if (!activeTabPanel) {
                    activeTabPanel = document.querySelector('.ui-tabs-panel[style*="display: block"]');
                }
                if (activeTabPanel && activeTabPanel.innerText && activeTabPanel.innerText.length > 50) {
                    // Combine panel and active tab content
                    const panelText = panel ? (panel.innerText || panel.textContent || '') : '';
                    const tabText = activeTabPanel.innerText || activeTabPanel.textContent || '';
                    return (panelText + String.fromCharCode(10) + String.fromCharCode(10) + tabText).trim();
                }
                
                if (panel) {
                    return panel.innerText || panel.textContent || '';
                }
                // Last resort: get body text but filter out form elements
                const body = document.body.cloneNode(true);
                // Remove form elements
                const forms = body.querySelectorAll('form, input, select, button');
                forms.forEach(el => el.remove());
                return body.innerText || body.textContent || '';
            }""")
            
            # Extract HTML from detail panel
            self.log.debug(f"[WORKFLOW] Extracting HTML from detail panel...")
            detail_html = await self.page.evaluate("""() => {
                // Try multiple selectors for detail panel
                let panel = document.querySelector('#noticeContent');
                if (!panel) {
                    panel = document.querySelector('#app');
                }
                if (!panel) {
                    panel = document.querySelector('.ui-dialog-content');
                }
                if (panel) {
                    return panel.innerHTML || '';
                }
                return '';
            }""")
            
            # ====================================================================
            # STEP 5.3: COMBINE TAB CONTENT - Merge content from all tabs
            # ====================================================================
            # Debug: log what we found
            self.log.debug(f"[WORKFLOW STEP 5.3] Main content extracted: text={len(detail_text)} chars, HTML={len(detail_html)} chars")
            if len(detail_text) < 100:
                self.log.warning("[WORKFLOW] Very short detail text extracted - panel might not be loaded")
            
            # Combine text from all tabs - this is critical for getting all content
            # Start with main panel text, then append each tab's content
            all_tabs_text = detail_text
            # Also extract documents from tabs_data HTML
            tabs_documents = []
            if tabs_data:
                self.log.info(f"[WORKFLOW STEP 5.3] Combining content from {len(tabs_data)} tabs")
                for tab_name, tab_content in tabs_data.items():
                    # Extract documents from each tab's HTML
                    if isinstance(tab_content, dict) and 'html' in tab_content:
                        from detail_parser import TenderDetailParser
                        parser = TenderDetailParser()
                        tab_docs = parser._extract_documents(tab_content['html'])
                        if tab_docs:
                            self.log.debug(f"Found {len(tab_docs)} documents in tab '{tab_name}'")
                            tabs_documents.extend(tab_docs)
                    tab_text = tab_content.get('text', '')
                    if tab_text and len(tab_text) > 50:  # Only add if substantial content
                        # Add tab content with clear separator
                        all_tabs_text += f"\n\n{'='*60}\nTAB: {tab_name}\n{'='*60}\n{tab_text}"
                        self.log.debug(f"Added {len(tab_text)} chars from tab '{tab_name}'")
            
            # Log final combined text length
            self.log.info(f"Final combined text length: {len(all_tabs_text)} chars")
            
            # Extract current page URL (this is the tender link)
            current_url = self.page.url
            
            # Extract tender link from page content (შესყიდვის ბმული)
            tender_link = None
            
            # First, try to extract from page content
            if "შესყიდვის ბმული" in detail_text or "შესყიდვის ბმული" in detail_html:
                # Look for URL after "შესყიდვის ბმული:"
                link_match = re.search(
                    r'შესყიდვის ბმული[:\s]+(https?://[^\s\n<]+)',
                    detail_text + detail_html
                )
                if link_match:
                    tender_link = link_match.group(1)
            
            # If not found in text, use current URL if it has ?go= parameter
            if not tender_link and "?go=" in current_url:
                tender_link = current_url
            elif not tender_link:
                # Try to extract tender_id from page and construct URL
                tender_id_from_page = await self.page.evaluate("""() => {
                    // Try to find tender ID in URL parameters
                    const urlParams = new URLSearchParams(window.location.search);
                    const goParam = urlParams.get('go');
                    if (goParam) return goParam;
                    
                    // Try to find in page content
                    const links = document.querySelectorAll('a[href*="?go="]');
                    for (const link of links) {
                        const href = link.getAttribute('href');
                        const match = href.match(/[?&]go=([^&]+)/);
                        if (match) return match[1];
                    }
                    return null;
                }""")
                
                if tender_id_from_page:
                    tender_link = f"https://tenders.procurement.gov.ge/public/?go={tender_id_from_page}&lang=ge"
            
            # Extract documents/attachments - comprehensive extraction from entire page and all tabs
            documents = await self.page.evaluate("""() => {
                // Search in entire document, not just panel, to catch documents in all tabs
                const panel = document.querySelector('#noticeContent') || document.querySelector('#app') || document.body;
                const docs = [];
                const seenUrls = new Set();
                
                // Method 1: Find all links in the entire document (including all tabs, even hidden ones)
                const links = document.querySelectorAll('a[href]');
                links.forEach(link => {
                    const href = link.getAttribute('href');
                    const text = (link.innerText || link.textContent || '').trim();
                    
                    if (!href) return;
                    
                    // Check for document file extensions
                    const docExtensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.txt'];
                    const isDocLink = docExtensions.some(ext => href.toLowerCase().includes(ext));
                    
                    // Check for download indicators
                    const hasDownload = href.toLowerCase().includes('download') || 
                                       href.toLowerCase().includes('file') ||
                                       href.toLowerCase().includes('attachment') ||
                                       link.getAttribute('download') !== null;
                    
                    // Check text for document indicators (Georgian and English)
                    const textIndicators = [
                        'დოკუმენტი', 'ფაილი', 'ცხრილი', 'დანართი', 
                        'document', 'file', 'attachment', 'download',
                        'ფასების', 'ხარჯთაღრიცხვა', 'excel', 'spreadsheet'
                    ];
                    const hasTextIndicator = textIndicators.some(ind => text.toLowerCase().includes(ind.toLowerCase()));
                    
                    // Also check parent elements for document context
                    const parentEl = link.parentElement;
                    const parentText = (parentEl && (parentEl.innerText || parentEl.textContent) || '').toLowerCase();
                    const hasParentIndicator = textIndicators.some(ind => parentText.includes(ind.toLowerCase()));
                    
                    if (isDocLink || hasDownload || hasTextIndicator || hasParentIndicator) {
                        // Make URL absolute
                        let absoluteUrl = href;
                        if (!href.startsWith('http')) {
                            if (href.startsWith('/')) {
                                absoluteUrl = window.location.origin + href;
                            } else if (href.startsWith('./') || href.startsWith('../')) {
                                absoluteUrl = new URL(href, window.location.href).href;
                            } else {
                                absoluteUrl = window.location.origin + '/' + href;
                            }
                        }
                        
                        // Fix missing /public in URL for procurement.gov.ge
                        if (absoluteUrl.includes('tenders.procurement.gov.ge') && 
                            absoluteUrl.includes('/library/') && 
                            !absoluteUrl.includes('/public/library/')) {
                            absoluteUrl = absoluteUrl.replace('/library/', '/public/library/');
                        }
                        
                        // Skip duplicates
                        if (seenUrls.has(absoluteUrl)) return;
                        seenUrls.add(absoluteUrl);
                        
                        // Determine file type
                        let fileType = 'unknown';
                        const hrefLower = href.toLowerCase();
                        if (hrefLower.includes('.pdf')) fileType = 'pdf';
                        else if (hrefLower.includes('.xls') || hrefLower.includes('.xlsx')) fileType = 'xls';
                        else if (hrefLower.includes('.doc') || hrefLower.includes('.docx')) fileType = 'doc';
                        else if (hrefLower.includes('.zip') || hrefLower.includes('.rar')) fileType = 'zip';
                        else if (text.toLowerCase().includes('xls') || text.toLowerCase().includes('excel')) fileType = 'xls';
                        else if (text.toLowerCase().includes('pdf')) fileType = 'pdf';
                        else if (text.toLowerCase().includes('doc')) fileType = 'doc';
                        else if (text.toLowerCase().includes('ცხრილი') || text.toLowerCase().includes('ხარჯთაღრიცხვა')) fileType = 'xls';
                        
                        // Get document name - try multiple sources
                        let docName = text;
                        if (!docName || docName.length < 2) {
                            // Try parent element text
                            const parentEl = link.parentElement;
                            const parentText = (parentEl && (parentEl.innerText || parentEl.textContent) || '');
                            if (parentText.trim().length > 2 && parentText.trim().length < 100) {
                                docName = parentText.trim();
                            } else {
                                const parts = href.split('/');
                                docName = parts[parts.length - 1] || 'Document';
                                // Remove query parameters
                                docName = docName.split('?')[0];
                            }
                        }
                        
                        // Clean up document name
                        docName = docName.trim();
                        if (docName.length > 100) {
                            docName = docName.substring(0, 100) + '...';
                        }
                        
                        docs.push({
                            name: docName,
                            url: absoluteUrl,
                            type: fileType
                        });
                    }
                });
                
                // Method 2: Find document references in text (e.g., "ფასების ცხრილი.xls", "დანართი N1.xlsx")
                const textContent = (panel.innerText || panel.textContent || '').toLowerCase();
                
                // Simplified pattern matching - look for file extensions
                const fileExtPattern = /\.(pdf|doc|docx|xls|xlsx|zip|rar|txt)/gi;
                const extMatches = Array.from(textContent.matchAll(fileExtPattern));
                
                for (const extMatch of extMatches) {
                    const extIndex = extMatch.index;
                    if (extIndex === undefined) continue;
                    
                    // Extract potential document name (up to 50 chars before extension)
                    const startIdx = Math.max(0, extIndex - 50);
                    const endIdx = extIndex + extMatch[0].length;
                    const potentialName = textContent.substring(startIdx, endIdx);
                    
                    // Try to find corresponding link
                    const matchingLink = Array.from(links).find(link => {
                        const linkText = (link.innerText || link.textContent || '').toLowerCase();
                        const linkHref = (link.getAttribute('href') || '').toLowerCase();
                        const ext = extMatch[1].toLowerCase();
                        return linkHref.includes('.' + ext) || linkText.includes(ext);
                    });
                    
                    if (matchingLink) {
                        const href = matchingLink.getAttribute('href');
                        if (href) {
                            let absoluteUrl = href;
                            if (!href.startsWith('http')) {
                                if (href.startsWith('/')) {
                                    absoluteUrl = window.location.origin + href;
                                } else {
                                    absoluteUrl = window.location.origin + '/' + href;
                                }
                            }
                            
                            // Fix missing /public in URL for procurement.gov.ge
                            if (absoluteUrl.includes('tenders.procurement.gov.ge') && 
                                absoluteUrl.includes('/library/') && 
                                !absoluteUrl.includes('/public/library/')) {
                                absoluteUrl = absoluteUrl.replace('/library/', '/public/library/');
                            }
                            
                            if (!seenUrls.has(absoluteUrl)) {
                                const ext = extMatch[1].toLowerCase();
                                let fileType = 'unknown';
                                if (ext === 'pdf') fileType = 'pdf';
                                else if (ext === 'xls' || ext === 'xlsx') fileType = 'xls';
                                else if (ext === 'doc' || ext === 'docx') fileType = 'doc';
                                else if (ext === 'zip' || ext === 'rar') fileType = 'zip';
                                
                                const docName = potentialName.trim() || 'Document.' + ext;
                                docs.push({
                                    name: docName,
                                    url: absoluteUrl,
                                    type: fileType
                                });
                                seenUrls.add(absoluteUrl);
                            }
                        }
                    }
                }
                
                return docs;
            }""")
            
            # Extract structured sections
            # Look for common Georgian labels and extract content after them
            structured_sections = {}
            section_labels = [
                "შესყიდვის ბმული",
                "აღწერა",
                "სპეციფიკაცია",
                "დოკუმენტები",
                "კონტაქტი",
                "ვადები",
                "პირობები",
            ]
            
            for label in section_labels:
                pattern = rf'{re.escape(label)}[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*(?:{re.escape("|".join(section_labels))}|$))'
                match = re.search(pattern, detail_text, re.MULTILINE | re.DOTALL)
                if match:
                    structured_sections[label.lower().replace(" ", "_")] = match.group(1).strip()
            
            # Prepare tabs_data for parser (only text, no HTML)
            tabs_data_for_parser = {}
            if tabs_data:
                for tab_name, tab_content in tabs_data.items():
                    if isinstance(tab_content, dict):
                        tabs_data_for_parser[tab_name] = {
                            "text": tab_content.get("text", ""),
                            # Don't pass HTML to parser
                        }
            
            # ====================================================================
            # STEP 5.4: PARSE STRUCTURED DATA - Use parser to extract fields
            # ====================================================================
            self.log.debug(f"[WORKFLOW STEP 5.4] Parsing structured data from content...")
            # Use new parser structure
            parser = TenderDetailParser()
            parsed_data = parser.parse(detail_html, all_tabs_text, tabs_data_for_parser)
            self.log.debug(f"[WORKFLOW STEP 5.4] Parsing complete, extracted {len(parsed_data)} top-level fields")
            
            # Combine documents from main extraction and tabs
            all_documents = list(documents) if documents else []
            all_documents.extend(tabs_documents)
            # Remove duplicates based on URL (case-insensitive)
            seen_doc_urls = set()
            unique_documents = []
            for doc in all_documents:
                doc_url = doc.get('url', '').lower()
                if doc_url and doc_url not in seen_doc_urls:
                    seen_doc_urls.add(doc_url)
                    unique_documents.append(doc)
            
            # Also deduplicate documents from parser
            parser_docs = parsed_data.get("documents", [])
            for doc in parser_docs:
                doc_url = doc.get('url', '').lower()
                if doc_url and doc_url not in seen_doc_urls:
                    seen_doc_urls.add(doc_url)
                    unique_documents.append(doc)
            
            # ====================================================================
            # STEP 5.5: STRUCTURE DATA - Use new parser structure directly
            # ====================================================================
            self.log.debug(f"[WORKFLOW STEP 5.5] Using new parser structure...")
            
            # The new parser returns data in the new structure format
            # Merge documents from page extraction with parser documents
            parser_docs = parsed_data.get("documents", [])
            all_documents = list(documents) if documents else []
            all_documents.extend(parser_docs)
            
            # Remove duplicates based on URL (case-insensitive)
            seen_doc_urls = set()
            unique_documents = []
            for doc in all_documents:
                doc_url = doc.get('url', '').lower()
                if doc_url and doc_url not in seen_doc_urls:
                    seen_doc_urls.add(doc_url)
                    unique_documents.append(doc)
            
            # Update parsed_data with merged documents
            parsed_data["documents"] = unique_documents
            
            # Ensure detail_url is set
            if not parsed_data.get("detail_url"):
                parsed_data["detail_url"] = tender_link or current_url
            
            # Ensure procurement_number is set
            if not parsed_data.get("procurement_number"):
                parsed_data["procurement_number"] = tender_number
            
            # Add all_cells for backward compatibility (combined tab text)
            parsed_data["all_cells"] = all_tabs_text
            
            # Add extraction_method
            parsed_data["extraction_method"] = "detailed"
            
            # Add number field for backward compatibility
            parsed_data["number"] = parsed_data.get("procurement_number", tender_number)
            
            self.log.debug(f"[WORKFLOW] Structured data ready with {len(parsed_data)} top-level fields")
            
            return parsed_data
            
        except Exception as e:
            self.log.error(f"Error extracting detail information: {e}", exc_info=True)
            return None
    
    async def _extract_from_all_tabs(self) -> Dict[str, Dict[str, Any]]:
        """
        Detect tabs in detail panel and extract data from each tab.
        
        Workflow:
        1. Detect tabs using multiple selector patterns
        2. Prioritize "დოკუმენტაცია" tab (process first)
        3. For each tab:
           - Check if already active (skip click if so)
           - Click tab if needed
           - Wait for content to load
           - Extract text and HTML
        
        Returns:
            Dictionary with tab names as keys and their content as values
        """
        assert self.page is not None
        tabs_data = {}
        
        try:
            # ====================================================================
            # TAB EXTRACTION STEP 1: DETECT TABS
            # ====================================================================
            # Detect tabs - look for common tab patterns, specifically looking for "დოკუმენტაცია"
            # Search in both #noticeContent and the whole page for #application_tabs
            self.log.debug(f"[TAB_EXTRACTION] Step 1: Detecting tabs...")
            tab_info = await self.page.evaluate("""() => {
                // First, try to find #application_tabs in the whole page (it might be outside noticeContent)
                // This is the most important selector based on user feedback
                let tabsContainer = document.querySelector('#application_tabs');
                let panel = document.querySelector('#noticeContent');
                
                // If #application_tabs not found, try to find it within noticeContent
                if (!tabsContainer && panel) {
                    tabsContainer = panel.querySelector('#application_tabs');
                }
                
                // If still not found, try to find any tab structure in the whole page
                if (!tabsContainer) {
                    tabsContainer = document.querySelector('ul.ui-tabs-nav, ul.tabs, #application_tabs');
                }
                
                // Look for tabs - common patterns
                const tabs = [];
                
                // Pattern 1: #application_tabs > ul > li (jQuery UI tabs) - PRIORITY
                // This is the structure the user mentioned: #application_tabs > ul > li.ui-state-default...
                if (tabsContainer) {
                    // Look for ul > li structure
                    const ul = tabsContainer.querySelector('ul');
                    if (ul) {
                        const ulTabs = ul.querySelectorAll('li');
                        Array.from(ulTabs).forEach((li, idx) => {
                            const text = li.innerText || li.textContent || '';
                            const tabId = li.id || '';
                            const className = li.className || '';
                            // Include all tabs, even if text is empty (might be icon-only)
                            // But prioritize tabs with text
                            if (text.trim() || tabId || className.includes('ui-state')) {
                                tabs.push({
                                    index: idx,
                                    name: text.trim() || tabId || 'Tab_' + (idx + 1),
                                    selector: '#application_tabs ul li:nth-child(' + (idx + 1) + ')',
                                    element: li,
                                    className: className
                                });
                            }
                        });
                    } else {
                        // No ul, try direct li children
                        const directTabs = tabsContainer.querySelectorAll('li');
                        Array.from(directTabs).forEach((li, idx) => {
                            const text = li.innerText || li.textContent || '';
                            const tabId = li.id || '';
                            const className = li.className || '';
                            if (text.trim() || tabId || className.includes('ui-state')) {
                                tabs.push({
                                    index: idx,
                                    name: text.trim() || tabId || 'Tab_' + (idx + 1),
                                    selector: '#application_tabs li:nth-child(' + (idx + 1) + ')',
                                    element: li,
                                    className: className
                                });
                            }
                        });
                    }
                }
                
                // Pattern 2: If no tabs found, try searching in panel
                if (tabs.length === 0 && panel) {
                    const ulTabs = panel.querySelectorAll('ul.tabs li, ul.ui-tabs-nav li, .tabs li');
                    if (ulTabs.length > 0) {
                        Array.from(ulTabs).forEach((li, idx) => {
                            const text = li.innerText || li.textContent || '';
                            const tabId = li.id || '';
                            if (text.trim() || tabId) {
                                tabs.push({
                                    index: idx,
                                    name: text.trim() || tabId,
                                    selector: `ul.tabs li:nth-child(${idx + 1}), ul.ui-tabs-nav li:nth-child(${idx + 1})`,
                                    element: li
                                });
                            }
                        });
                    }
                }
                
                // Pattern 3: Look for elements with onclick that contain "ShowTab" or similar
                // Only if panel exists
                if (panel) {
                    const onclickTabs = panel.querySelectorAll('a[onclick*="ShowTab"], a[onclick*="tab"], li[onclick*="tab"]');
                    if (onclickTabs.length > 0 && tabs.length === 0) {
                        Array.from(onclickTabs).forEach((el, idx) => {
                            const text = el.innerText || el.textContent || '';
                            if (text.trim()) {
                                tabs.push({
                                    index: idx,
                                    name: text.trim(),
                                    element: el
                                });
                            }
                        });
                    }
                    
                    // Pattern 4: div.tab-header or similar
                    const tabHeaders = panel.querySelectorAll('.tab-header, .tab-title, [data-tab]');
                    if (tabHeaders.length > 0 && tabs.length === 0) {
                        Array.from(tabHeaders).forEach((header, idx) => {
                            const text = header.innerText || header.textContent || '';
                            const tabId = header.getAttribute('data-tab') || header.id || '';
                            if (text.trim() || tabId) {
                                tabs.push({
                                    index: idx,
                                    name: text.trim() || tabId,
                                    selector: '.tab-header:nth-child(' + (idx + 1) + '), [data-tab="' + tabId + '"]',
                                    element: header
                                });
                            }
                        });
                    }
                    
                    // Pattern 5: Look for clickable elements that might be tabs
                    const clickables = panel.querySelectorAll('a[onclick*="tab"], button[onclick*="tab"], .tab-link');
                    if (clickables.length > 0 && tabs.length === 0) {
                        Array.from(clickables).forEach((el, idx) => {
                            const text = el.innerText || el.textContent || '';
                            if (text.trim()) {
                                tabs.push({
                                    index: idx,
                                    name: text.trim(),
                                    element: el
                                });
                            }
                        });
                    }
                }
                
                return {
                    hasTabs: tabs.length > 0,
                    tabs: tabs,
                    panelHTML: panel ? (panel.innerHTML || '').substring(0, 2000) : '',
                    panelExists: !!panel,
                    tabsContainerExists: !!tabsContainer
                };
            }""")
            
            if not tab_info:
                self.log.warning("[TAB_EXTRACTION] Tab detection returned null/undefined")
                return {}
            
            if not tab_info.get('hasTabs'):
                self.log.debug(f"[TAB_EXTRACTION] No tabs detected on page")
                return {}
            
            tab_names = [t.get('name', 'unnamed') for t in tab_info['tabs']]
            self.log.info(f"[TAB_EXTRACTION] Step 1 complete: Found {len(tab_info['tabs'])} tabs: {', '.join(tab_names)}")
            
            # ====================================================================
            # TAB EXTRACTION STEP 2: PRIORITIZE TABS
            # ====================================================================
            # Click through each tab and extract content
            # Prioritize "დოკუმენტაცია" tab if it exists (contains documents)
            self.log.debug(f"[TAB_EXTRACTION] Step 2: Prioritizing tabs...")
            tabs_to_process = tab_info['tabs']
            doc_tab = None
            for tab in tabs_to_process:
                if 'დოკუმენტაცია' in tab.get('name', ''):
                    doc_tab = tab
                    self.log.debug(f"[TAB_EXTRACTION] Found დოკუმენტაცია tab, will process first")
                    break
            
            # Process documentation tab first if found
            if doc_tab:
                tabs_to_process = [doc_tab] + [t for t in tabs_to_process if t != doc_tab]
                self.log.debug(f"[TAB_EXTRACTION] Reordered tabs: დოკუმენტაცია first")
            
            # ====================================================================
            # TAB EXTRACTION STEP 3: EXTRACT FROM EACH TAB
            # ====================================================================
            self.log.debug(f"[TAB_EXTRACTION] Step 3: Extracting content from {len(tabs_to_process)} tabs...")
            
            for tab_idx, tab in enumerate(tabs_to_process, 1):
                tab_name = tab.get('name', f"Tab_{tab['index']}")
                self.log.debug(f"[TAB_EXTRACTION] Processing tab {tab_idx}/{len(tabs_to_process)}: {tab_name}")
                
                try:
                    # ====================================================================
                    # TAB EXTRACTION STEP 3.1: CHECK IF TAB IS ALREADY ACTIVE
                    # ====================================================================
                    # Optimization: Skip clicking if tab is already active (saves time)
                    self.log.debug(f"[TAB_EXTRACTION] Checking if tab '{tab_name}' is already active...")
                    is_active = await self.page.evaluate("""(tabName) => {
                        // Check if this tab is already active
                        const tabs = document.querySelectorAll('#application_tabs ul li, ul.ui-tabs-nav li');
                        for (const tab of tabs) {
                            const text = (tab.innerText || tab.textContent || '').trim();
                            if (text === tabName) {
                                // Check if tab has active class
                                const hasActive = tab.classList.contains('ui-state-active') || 
                                                 tab.classList.contains('ui-tabs-active') ||
                                                 tab.classList.contains('active');
                                if (hasActive) {
                                    // Also check if corresponding panel is visible
                                    const tabId = tab.querySelector('a')?.getAttribute('aria-controls') || 
                                                  tab.querySelector('a')?.getAttribute('href')?.replace('#', '');
                                    if (tabId) {
                                        const panel = document.getElementById(tabId) || 
                                                     document.querySelector(`#${tabId}`);
                                        if (panel) {
                                            const style = window.getComputedStyle(panel);
                                            if (style.display !== 'none' && panel.offsetParent !== null) {
                                                return true;
                                            }
                                        }
                                    }
                                    return hasActive;
                                }
                            }
                        }
                        return false;
                    }""", tab_name)
                    
                    if is_active:
                        self.log.debug(f"[TAB_EXTRACTION] ✅ Tab '{tab_name}' is already active, skipping click (optimization)")
                        # Extract content without clicking (already visible)
                        tab_content = await self.page.evaluate("""() => {
                            let activeTab = document.querySelector('.ui-tabs-panel:not([style*="display: none"]), .ui-tabs-panel[style*="display: block"]');
                            if (!activeTab) {
                                const panels = document.querySelectorAll('.ui-tabs-panel');
                                for (const panel of panels) {
                                    const style = window.getComputedStyle(panel);
                                    if (style.display !== 'none' && panel.offsetParent !== null) {
                                        activeTab = panel;
                                        break;
                                    }
                                }
                            }
                            const contentElement = activeTab || document.querySelector('#noticeContent') || document.querySelector('#app') || document.body;
                            return {
                                text: contentElement.innerText || contentElement.textContent || '',
                                html: contentElement.innerHTML || ''
                            };
                        }""")
                        tabs_data[tab_name] = {
                            "text": tab_content.get("text", ""),
                            "html": tab_content.get("html", "")
                        }
                        self.log.debug(f"[TAB_EXTRACTION] ✅ Extracted {len(tab_content.get('text', ''))} chars from tab '{tab_name}' (already active, no click needed)")
                        continue
                    
                    # ====================================================================
                    # TAB EXTRACTION STEP 3.2: CLICK TAB (if not active)
                    # ====================================================================
                    self.log.debug(f"[TAB_EXTRACTION] Tab '{tab_name}' is not active, attempting to click...")
                    # Try to click the tab using multiple methods
                    clicked = False
                    
                    # Method 1: Direct element click
                    if 'element' in tab:
                        try:
                            # Scroll element into view first using element.evaluate() (not page.evaluate())
                            await tab['element'].evaluate("""(el) => {
                                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            }""")
                            await asyncio.sleep(0.2)  # Reduced from 0.3
                            
                            # Try regular click
                            await tab['element'].click()
                            clicked = True
                        except Exception:
                            try:
                                await tab['element'].evaluate("""(el) => {
                                    if (el) {
                                        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                        el.click();
                                    }
                                }""")
                                clicked = True
                            except Exception:
                                pass
                    
                    # Method 2: Click by selector
                    if not clicked:
                        selector = tab.get('selector', '')
                        if selector:
                            try:
                                # Try to find the element by selector
                                tab_element = await self.page.query_selector(selector)
                                if tab_element:
                                    await tab_element.click()
                                    clicked = True
                            except Exception:
                                try:
                                    await self.page.evaluate("""(sel) => {
                                        const el = document.querySelector(sel);
                                        if (el) {
                                            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                            el.click();
                                        }
                                    }""", selector)
                                    clicked = True
                                except:
                                    pass
                    
                    if not clicked:
                        self.log.warning(f"[TAB_EXTRACTION] ❌ Could not click tab '{tab_name}' after all methods, skipping")
                        continue
                    
                    # ====================================================================
                    # TAB EXTRACTION STEP 3.3: WAIT FOR TAB CONTENT TO LOAD
                    # ====================================================================
                    self.log.debug(f"[TAB_EXTRACTION] Tab '{tab_name}' clicked, waiting for content to load...")
                    # Wait for tab content to load - reduced wait since wait_for_selector handles timing
                    await asyncio.sleep(0.3)  # Small delay for tab click to register
                    
                    # Wait for tab panel to become visible
                    try:
                        await self.page.wait_for_selector(
                            '.ui-tabs-panel:not([style*="display: none"]), .ui-tabs-panel[style*="display: block"], div[id*="tabs"]:not([style*="display: none"])',
                            timeout=5000,
                            state='visible'
                        )
                        self.log.debug(f"[TAB_EXTRACTION] Tab panel for '{tab_name}' is now visible")
                    except Exception as e:
                        self.log.debug(f"[TAB_EXTRACTION] Tab panel visibility check timeout for '{tab_name}': {e}, continuing anyway")
                    
                    # ====================================================================
                    # TAB EXTRACTION STEP 3.4: EXTRACT CONTENT FROM TAB
                    # ====================================================================
                    self.log.debug(f"[TAB_EXTRACTION] Extracting content from tab '{tab_name}'...")
                    tab_content = await self.page.evaluate("""() => {
                        // Try to find active tab panel - jQuery UI tabs
                        let activeTab = document.querySelector('.ui-tabs-panel:not([style*="display: none"]), .ui-tabs-panel[style*="display: block"]');
                        
                        // If not found, try to find by checking all tab panels
                        if (!activeTab) {
                            const panels = document.querySelectorAll('.ui-tabs-panel, div[id*="tabs"], div[id*="tab"]');
                            for (const panel of panels) {
                                const style = window.getComputedStyle(panel);
                                const isVisible = style.display !== 'none' && panel.offsetParent !== null;
                                if (isVisible && panel.innerText && panel.innerText.length > 50) {
                                    activeTab = panel;
                                    break;
                                }
                            }
                        }
                        
                        // Fallback: get content from noticeContent or app
                        const panel = document.querySelector('#noticeContent') || document.querySelector('#app');
                        
                        // If we have an active tab, use it; otherwise use panel
                        const contentElement = activeTab || panel || document.body;
                        
                        // Get all text content
                        const text = contentElement.innerText || contentElement.textContent || '';
                        const html = contentElement.innerHTML || '';
                        
                        return {
                            text: text,
                            html: html,
                            elementId: contentElement.id || '',
                            className: contentElement.className || ''
                        };
                    }""")
                    
                    tabs_data[tab_name] = tab_content
                    text_len = len(tab_content.get('text', ''))
                    self.log.debug(f"Extracted {text_len} chars from tab '{tab_name}'")
                    
                except Exception as e:
                    self.log.error(f"❌ Error extracting tab {tab_name}: {e}", exc_info=True)
                    continue
            
            # Return to first tab if we clicked through multiple
            if len(tabs_data) > 1:
                try:
                    first_tab = tab_info['tabs'][0]
                    if 'element' in first_tab:
                        await first_tab['element'].click()
                    elif 'selector' in first_tab:
                        tab_element = await self.page.query_selector(first_tab['selector'])
                        if tab_element:
                            await tab_element.click()
                    await asyncio.sleep(0.3)
                except Exception:
                    pass
            
        except Exception as e:
            self.log.warning(f"Error detecting/extracting tabs: {e}")
        
        return tabs_data
    
    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_fixed(2)
    )
    async def scrape_multiple(
        self, 
        tender_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple tenders with retry logic.
        
        Args:
            tender_data: List of dicts with tender info:
                - tender_number (required): e.g., "GEO250000579"
                - tender_id (optional): e.g., "657645"
                - detail_url (optional): Full URL to detail page
                
        Returns:
            List of scraped detail records
        """
        # Filter out existing tenders
        existing_numbers = self.get_existing_tender_numbers()
        if existing_numbers:
            self.log.info(f"Found {len(existing_numbers)} existing records in output file")
            
        tenders_to_scrape = []
        for item in tender_data:
            num = item.get("tender_number") or item.get("number")
            if num and num not in existing_numbers:
                tenders_to_scrape.append(item)
            elif num:
                self.log.debug(f"Skipping {num} - already scraped")
                
        if not tenders_to_scrape:
            self.log.info("All tenders have already been scraped!")
            return []
            
        self.log.info(f"Scraping {len(tenders_to_scrape)} new tenders (skipped {len(tender_data) - len(tenders_to_scrape)})")
        
        results = []
        total = len(tenders_to_scrape)
        
        for idx, tender_info in enumerate(tenders_to_scrape, 1):
            tender_number = tender_info.get("tender_number") or tender_info.get("number")
            tender_id = tender_info.get("tender_id")
            detail_url = tender_info.get("detail_url")
            
            if not tender_number:
                self.log.warning(f"Skipping item {idx}: no tender_number")
                continue
            
            self.log.info(f"Scraping {idx}/{total}: {tender_number}")
            
            result = await self.scrape_tender_detail(
                tender_number=tender_number,
                tender_id=tender_id,
                detail_url=detail_url
            )
            if result:
                results.append(result)
            
            # Pause between requests
            await asyncio.sleep(self.config.page_pause_ms / 1000)
        
        return results

    async def scrape_worker(
        self, 
        queue: asyncio.Queue, 
        results: List[Dict[str, Any]],
        worker_id: int
    ) -> None:
        """Worker for parallel scraping."""
        self.log.debug(f"Worker {worker_id} started")
        
        while True:
            try:
                # Get item from queue
                item = await queue.get()
                
                # Check for stop signal
                if item is None:
                    queue.task_done()
                    break
                
                idx, tender_info = item
                tender_number = tender_info.get("tender_number") or tender_info.get("number")
                tender_id = tender_info.get("tender_id")
                detail_url = tender_info.get("detail_url")
                
                if not tender_number:
                    self.log.warning(f"Skipping item {idx}: no tender_number")
                    queue.task_done()
                    continue
                
                self.log.info(f"[Worker {worker_id}] Scraping {tender_number}")
                
                # Scrape
                result = await self.scrape_tender_detail(
                    tender_number=tender_number,
                    tender_id=tender_id,
                    detail_url=detail_url
                )
                
                if result:
                    results.append(result)
                
                queue.task_done()
                
                # Pause between requests
                await asyncio.sleep(self.config.page_pause_ms / 1000)
                
            except Exception as e:
                self.log.error(f"[Worker {worker_id}] Error: {e}")
                
                # Check if browser is disconnected
                if self.browser and not self.browser.is_connected():
                    self.log.error(f"[Worker {worker_id}] Browser disconnected, stopping worker")
                    queue.task_done()
                    break
                    
                # Don't break the loop on error, just mark task as done and continue
                queue.task_done()

    async def scrape_multiple_parallel(
        self, 
        tender_data: List[Dict[str, Any]],
        concurrency: int,
        force: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple tenders in parallel.
        """
        # Filter out existing tenders
        existing_numbers = set()
        if not force:
            existing_numbers = self.get_existing_tender_numbers()
            if existing_numbers:
                self.log.info(f"Found {len(existing_numbers)} existing records in output file")
            
        tenders_to_scrape = []
        for item in tender_data:
            num = item.get("tender_number") or item.get("number")
            if num and num not in existing_numbers:
                tenders_to_scrape.append(item)
            elif num:
                self.log.debug(f"Skipping {num} - already scraped")
                
        if not tenders_to_scrape:
            self.log.info("All tenders have already been scraped!")
            return []
            
        self.log.info(f"Scraping {len(tenders_to_scrape)} new tenders (skipped {len(tender_data) - len(tenders_to_scrape)})")
        
        results = []
        queue = asyncio.Queue()
        
        # Fill queue
        for idx, item in enumerate(tenders_to_scrape, 1):
            queue.put_nowait((idx, item))
            
        # Create workers
        workers = []
        
        # We need to create separate scraper instances for each worker
        # because each needs its own Page, but they can share the Browser and Writer
        
        assert self.browser is not None
        
        async def worker_wrapper(w_id):
            try:
                # Create new context and page for this worker
                context = await self.browser.new_context()
                page = await context.new_page()
                
                # Create scraper instance sharing browser and writer
                worker_scraper = DetailedTenderScraper(
                    self.config, 
                    self.selectors, 
                    browser=self.browser, 
                    page=page, 
                    writer=self.writer
                )
                
                try:
                    await worker_scraper.scrape_worker(queue, results, w_id)
                finally:
                    # Use a short timeout for cleanup to prevent hanging
                    try:
                        if page:
                            await asyncio.wait_for(page.close(), timeout=2.0)
                    except Exception as e:
                        self.log.debug(f"[Worker {w_id}] Error closing page: {e}")
                    
                    try:
                        if context:
                            await asyncio.wait_for(context.close(), timeout=2.0)
                    except Exception as e:
                        self.log.debug(f"[Worker {w_id}] Error closing context: {e}")
            except Exception as e:
                self.log.error(f"[Worker {w_id}] Critical error in worker wrapper: {e}")
                # Ensure we drain the queue if a worker dies completely
                # This prevents the main process from hanging waiting for queue.join() (if we used it)
                # But here we use queue.task_done() inside worker, so if worker dies, 
                # items might be left in queue? 
                # We are using gather on workers, so if one dies, it returns.
                # But we need to make sure we don't hang.
                pass
        
        # Start workers
        self.log.info(f"Starting {concurrency} workers for {len(tenders_to_scrape)} items")
        for i in range(concurrency):
            workers.append(asyncio.create_task(worker_wrapper(i+1)))
            
        # Add stop signals
        for _ in range(concurrency):
            queue.put_nowait(None)
            
        # Wait for all workers
        await asyncio.gather(*workers)
        
        return results


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_configs(config_path: Path, args: argparse.Namespace) -> tuple[DetailScraperConfig, DetailSelectors]:
    """Build configuration objects from YAML and command-line args."""
    raw = load_config(config_path)
    selectors_raw = raw["selectors"]
    scrape_raw = raw.get("scrape", {})
    
    config = DetailScraperConfig(
        base_url=raw.get("base_url"),
        headless=args.headless if args.headless else scrape_raw.get("headless", False),  # Default to visible for debugging
        page_pause_ms=args.page_pause_ms or scrape_raw.get("page_pause_ms", 1000),
        output_path=Path(args.output or scrape_raw.get("output_path", "data/detailed_tenders.jsonl")),
        max_retries=scrape_raw.get("max_retries", 3)
    )
    
    selectors = DetailSelectors(
        tender_number_input=selectors_raw["tender_number_input"],
        search_button=selectors_raw["search_button"],
        detail_panel=selectors_raw["detail_panel"],
        detail_title=selectors_raw.get("detail_title", ""),
        detail_content=selectors_raw.get("detail_content", ""),
        close_button=selectors_raw["close_button"]
    )
    
    return config, selectors


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Scrape detailed information for specific tenders.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape specific tender numbers
  python3 detailed_scraper/detail_scraper.py GEO250000505 GEO250000506
  
  # Scrape tenders from last 10 days (by deadline_date)
  python3 detailed_scraper/detail_scraper.py --days 10
  
  # Scrape tenders from 1 day ago to today
  python3 detailed_scraper/detail_scraper.py --date-from "1 day ago" --date-to today
  
  # Scrape tenders from specific date range
  python3 detailed_scraper/detail_scraper.py --date-from 2025-11-29 --date-to 2025-12-05
  
  # Scrape only by published_date (not deadline_date)
  python3 detailed_scraper/detail_scraper.py --days 7 --filter-by-deadline-date false --filter-by-published-date true
        """
    )
    parser.add_argument(
        "tender_numbers",
        nargs="*",
        help="Tender numbers to scrape (e.g., GEO250000579). Optional if using --days or --date-from."
    )
    parser.add_argument(
        "--config",
        default="detailed_scraper/config.yaml",
        help="Path to config.yaml"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: False, browser will be visible for debugging)"
    )
    parser.add_argument(
        "--page-pause-ms",
        type=int,
        help="Delay between operations in milliseconds"
    )
    parser.add_argument(
        "--output",
        help="Output JSONL file path"
    )
    parser.add_argument(
        "--from-main-data",
        help="Load tender numbers and IDs from main data file (data/tenders.jsonl)"
    )
    parser.add_argument(
        "--data-file",
        type=Path,
        default=Path("data/tenders.jsonl"),
        help="Path to main data file for date filtering (default: data/tenders.jsonl)"
    )
    parser.add_argument(
        "--date-from",
        type=str,
        help="Start date (YYYY-MM-DD, 'today', '1 day ago', etc.)"
    )
    parser.add_argument(
        "--date-to",
        type=str,
        help="End date (YYYY-MM-DD, 'today', etc.). Default: today"
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Number of days to scrape. If --date-from provided: date-to = date-from + days. Otherwise: date-from = today - days, date-to = today"
    )
    parser.add_argument(
        "--filter-by-deadline-date",
        action="store_true",
        default=True,
        help="Filter by deadline_date (default: True) ⭐ PRIMARY FILTER"
    )
    parser.add_argument(
        "--no-filter-by-deadline-date",
        action="store_false",
        dest="filter_by_deadline_date",
        help="Disable filtering by deadline_date"
    )
    parser.add_argument(
        "--filter-by-published-date",
        action="store_true",
        default=False,
        help="Also filter by published_date (default: False)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing detailed data file before scraping"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of parallel scrapers (default: 1)"
    )
    return parser.parse_args()


def load_tender_data_from_main_file(data_path: Path) -> List[Dict[str, Any]]:
    """Load tender numbers and IDs from main data file."""
    import json
    
    tender_data = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                # Extract tender number
                all_cells = record.get("all_cells", "")
                tender_num_match = re.search(r'([A-Z]{2,4}\d{9,})', all_cells)
                if not tender_num_match:
                    continue
                
                tender_number = tender_num_match.group(1)
                tender_id = record.get("tender_id")
                detail_url = record.get("detail_url")
                
                tender_data.append({
                    "tender_number": tender_number,
                    "tender_id": tender_id,
                    "detail_url": detail_url
                })
            except Exception as e:
                logger.warning(f"Failed to parse record: {e}")
                continue
    
    return tender_data


async def async_main(args: argparse.Namespace) -> None:
    """Main async function."""
    cfg_path = Path(args.config)
    config, selectors = build_configs(cfg_path, args)
    
    # Clear output file if requested
    if args.clear:
        if config.output_path.exists():
            # Create backup before clearing
            backup_path = config.output_path.with_suffix('.jsonl.bak')
            import shutil
            shutil.copy(config.output_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            
            # Clear the file
            config.output_path.write_text('', encoding='utf-8')
            logger.info(f"Cleared existing detailed data file: {config.output_path}")
        else:
            logger.info(f"Output file does not exist yet: {config.output_path}")
    
    # Prepare tender data
    tender_data = []
    
    # Priority 1: Date filtering (if date arguments provided)
    if args.date_from or args.date_to or args.days:
        if not args.data_file.exists():
            logger.error(f"Data file not found: {args.data_file}")
            logger.error("Cannot filter by date without main data file")
            return
        
        tender_data = filter_tenders_by_date(
            data_path=args.data_file,
            date_from=args.date_from,
            date_to=args.date_to,
            days=args.days,
            filter_by_deadline_date=args.filter_by_deadline_date,
            filter_by_published_date=args.filter_by_published_date
        )
        
        if not tender_data:
            logger.warning("No tenders found matching date criteria")
            return
        
        logger.info(f"Will scrape {len(tender_data)} tenders based on date filter")
    
    # Priority 2: Load from main data file (if --from-main-data provided)
    elif args.from_main_data:
        data_path = Path(args.from_main_data)
        tender_data = load_tender_data_from_main_file(data_path)
        logger.info(f"Loaded {len(tender_data)} tenders from main data file")
    
    # Priority 3: Load from file path (if tender_numbers starts with "file:")
    elif len(args.tender_numbers) == 1 and args.tender_numbers[0].startswith("file:"):
        file_path = args.tender_numbers[0].replace("file:", "")
        data_path = Path(file_path)
        tender_data = load_tender_data_from_main_file(data_path)
        logger.info(f"Loaded {len(tender_data)} tenders from {file_path}")
    
    # Priority 4: Use provided tender numbers
    elif args.tender_numbers:
        tender_data = [{"tender_number": num} for num in args.tender_numbers]
        logger.info(f"Will scrape {len(tender_data)} specified tender numbers")
    
    else:
        logger.error("No tenders specified. Provide tender numbers, use --days/--date-from, or --from-main-data")
        return
    
    if not tender_data:
        logger.warning("No tender data to scrape")
        return
    
    if args.concurrency > 1:
        logger.info(f"Running in parallel mode with {args.concurrency} workers")
        
        # For parallel execution, we need to manage the browser lifecycle at the top level
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=config.headless)
        
        try:
            # Create a shared writer
            writer = JsonLinesWriter(config.output_path)
            
            # Create a master scraper instance that holds the browser
            # We don't pass a page because workers will create their own
            scraper = DetailedTenderScraper(config, selectors, browser=browser, writer=writer)
            
            results = await scraper.scrape_multiple_parallel(tender_data, args.concurrency)
            logger.info(f"✅ Successfully scraped {len(results)} out of {len(tender_data)} tenders")
            
        finally:
            # Robust cleanup
            if browser:
                try:
                    logger.debug("Closing browser...")
                    await asyncio.wait_for(browser.close(), timeout=5.0)
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
            
            if playwright:
                try:
                    logger.debug("Stopping playwright...")
                    await asyncio.wait_for(playwright.stop(), timeout=5.0)
                except Exception as e:
                    logger.warning(f"Error stopping playwright: {e}")
            
    else:
        # Sequential execution (legacy mode)
        async with DetailedTenderScraper(config, selectors) as scraper:
            results = await scraper.scrape_multiple(tender_data)
            logger.info(f"✅ Successfully scraped {len(results)} out of {len(tender_data)} tenders")


def main() -> None:
    """Main entry point."""
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()

