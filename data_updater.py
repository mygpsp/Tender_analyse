"""
Data Updater Script - Smart Tender Data Synchronization

This script performs a two-phase update:
1. Phase A: Re-check active tenders from the last 60 days for status changes
2. Phase B: Fetch new tenders incrementally from the last known date

Logs all operations to logs/update_history.json for monitoring.
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/data_updater.log')
    ]
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "main_scrapper" / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
STATUS_FILE = DATA_DIR / "tender_statuses.json"
UPDATE_LOG_FILE = LOGS_DIR / "update_history.json"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)


class TenderDataUpdater:
    """Manages tender data synchronization with smart update logic."""
    
    def __init__(self, data_file: Path, dry_run: bool = False, skip_detailed: bool = False, date_from: datetime = None, date_to: datetime = None):
        """Initialize the updater.
        
        Args:
            data_file: Path to the tender data file
            dry_run: If True, don't make actual changes
            skip_detailed: If True, skip detailed scraping (fast mode)
        """
        self.data_file = data_file
        self.temp_file = data_file.parent / f"{data_file.stem}.tmp{data_file.suffix}"
        self.run_id = str(uuid.uuid4())
        self.dry_run = dry_run
        self.skip_detailed = skip_detailed
        self.date_from = date_from
        self.date_to = date_to
        self.start_time = datetime.now()
        
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
        
        # Load status definitions
        self.load_status_definitions()
        
        # Metrics
        self.metrics = {
            'total_active_rechecked': 0,
            'status_changes_detected': 0,
            'new_tenders_added': 0,
            'total_tenders': 0,
            'errors': []
        }
        
    def set_custom_date_range(self, start_date: datetime, end_date: datetime):
        """Set custom date range for scraping."""
        self.custom_start_date = start_date
        self.custom_end_date = end_date
        logger.info(f"Set custom date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    def load_status_definitions(self):
        """Load tender status definitions from JSON file."""
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            # Extract status lists
            self.ACTIVE_STATUSES = status_data['filtering_recommendations']['active_tenders']
            self.FINAL_STATUSES = status_data['filtering_recommendations']['completed_tenders'] + \
                                  status_data['filtering_recommendations']['failed_tenders']
            self.ERROR_STATUSES = status_data['filtering_recommendations']['exclude_from_analysis']
            
            logger.info(f"Loaded {len(self.ACTIVE_STATUSES)} active statuses")
            logger.info(f"Loaded {len(self.FINAL_STATUSES)} final statuses")
            
        except Exception as e:
            logger.error(f"Failed to load status definitions: {e}")
            # Fallback to hardcoded values
            self.ACTIVE_STATUSES = [
                "გამოცხადებულია",
                "წინადადებების მიღება დაწყებულია",
                "წინადადებების მიღება დასრულებულია",
                "შერჩევა/შეფასება",
                "გამარჯვებული გამოვლენილია",
                "მიმდინარეობს ხელშეკრულების მომზადება"
            ]
            self.FINAL_STATUSES = [
                "ხელშეკრულება დადებულია",
                "არ შედგა",
                "დასრულებულია უარყოფითი შედეგით",
                "შეწყვეტილია"
            ]
            self.ERROR_STATUSES = ["error", "ჩანაწერები არ არის"]
    
    def load_existing_data(self) -> pd.DataFrame:
        """Load existing tender data from JSONL file."""
        if not self.data_file.exists():
            logger.info(f"Data file {self.data_file} does not exist. Starting fresh.")
            return pd.DataFrame()
        
        try:
            df = pd.read_json(self.data_file, lines=True)
            logger.info(f"Loaded {len(df)} existing tenders from {self.data_file}")
            return df
        except Exception as e:
            logger.error(f"Failed to load existing data: {e}")
            self.metrics['errors'].append(f"Load error: {str(e)}")
            return pd.DataFrame()
    
    def phase_a_recheck_active(self, df: pd.DataFrame) -> List[str]:
        """
        Phase A: Identify active tenders from last 60 days that need re-checking.
        
        Returns:
            List of tender IDs to re-scrape
        """
        logger.info("=" * 60)
        logger.info("PHASE A: Re-checking Active Tenders")
        logger.info("=" * 60)
        
        if df.empty:
            logger.info("No existing data to re-check")
            return []
        
        # Calculate cutoff date (60 days ago)
        cutoff_date = datetime.now() - timedelta(days=60)
        
        # Filter for active tenders
        active_mask = df['status'].isin(self.ACTIVE_STATUSES)
        
        # Filter by date if available
        if 'published_date' in df.columns:
            try:
                df['published_date_parsed'] = pd.to_datetime(df['published_date'], errors='coerce')
                date_mask = df['published_date_parsed'] >= cutoff_date
                final_mask = active_mask & date_mask
            except Exception as e:
                logger.warning(f"Date parsing failed: {e}. Using status filter only.")
                final_mask = active_mask
        else:
            final_mask = active_mask
        
        active_tenders = df[final_mask]
        
        logger.info(f"Found {len(active_tenders)} active tenders to re-check")
        
        if len(active_tenders) > 0:
            # Show status breakdown
            status_counts = active_tenders['status'].value_counts()
            logger.info("Status breakdown:")
            for status, count in status_counts.items():
                logger.info(f"  {status}: {count}")
        
        self.metrics['total_active_rechecked'] = len(active_tenders)
        
        # Return list of tender IDs
        if 'procurement_number' in active_tenders.columns:
            return active_tenders['procurement_number'].tolist()
        elif 'number' in active_tenders.columns:
            return active_tenders['number'].tolist()
        else:
            logger.warning("No procurement_number or number column found")
            return []
    
    def phase_b_fetch_new(self, df: pd.DataFrame) -> tuple:
        """
        Phase B: Determine date range for fetching new tenders.
        
        Uses a forward-looking approach:
        - Start: Today minus 2 days (safety buffer for recent updates)
        - End: Today plus 2 months (to catch tenders with future deadlines)
        
        This makes sense because tenders can be announced today with deadlines
        up to 2 months in the future.
        
        Returns:
            Tuple of (start_date, end_date) for scraping
        """
        logger.info("=" * 60)
        logger.info("PHASE B: Fetching New Tenders")
        logger.info("=" * 60)
        
        now = datetime.now()
        
        # Start: Today minus 2 days (safety buffer)
        start_date = now - timedelta(days=2)
        
        # End: Today plus 2 months (to catch future deadlines)
        end_date = now + timedelta(days=60)  # ~2 months
        
        logger.info(f"Using forward-looking date range:")
        logger.info(f"  Start: {start_date.strftime('%Y-%m-%d')} (today - 2 days)")
        logger.info(f"  End: {end_date.strftime('%Y-%m-%d')} (today + 2 months)")
        logger.info(f"  Rationale: Catches recent updates + tenders with future deadlines")
        
        logger.info(f"Rationale: Catches recent updates + tenders with future deadlines")
        
        if self.date_from and self.date_to:
            logger.info(f"📍 OVERRIDE: Using custom date range provided by user")
            logger.info(f"  Start: {self.date_from.strftime('%Y-%m-%d')}")
            logger.info(f"  End:   {self.date_to.strftime('%Y-%m-%d')}")
            return self.date_from, self.date_to
        
        return start_date, end_date
    
    def scrape_tenders_by_ids(self, tender_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape tenders by IDs using the detailed scraper.
        
        Calls the existing detailed_scraper/run_detailed_production.py script.
        """
        if not tender_ids:
            return []
        
        # Skip detailed scraping if in fast mode
        if self.skip_detailed:
            logger.info(f"⏭️  Skipping detailed scraping for {len(tender_ids)} tenders (fast mode)")
            return []
            
        logger.info(f"Scraping {len(tender_ids)} tenders by ID...")
        
        try:
            import subprocess
            
            # Determine tender type from filename
            tender_type = None
            if 'con_detailed' in str(self.data_file):
                tender_type = 'CON'
            elif 'nat_detailed' in str(self.data_file):
                tender_type = 'NAT'
            elif 'spa_detailed' in str(self.data_file):
                tender_type = 'SPA'
            
            # Build command
            cmd = [
                'python3',
                'detailed_scraper/run_detailed_production.py',
                '--tenders', *tender_ids,
                '--concurrency', '10',
                '--headless',
                '--force'  # Force re-scrape to get latest status
            ]
            
            if tender_type:
                cmd.extend(['--tender-type', tender_type])
            
            logger.info(f"Running: {' '.join(cmd)}")
            
            # Run scraper
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Scraper failed: {result.stderr}")
                self.metrics['errors'].append(f"Scraper error: {result.stderr[:200]}")
                return []
            
            logger.info("Scraping completed successfully")
            
            # Reload the data file to get the updated tenders
            if self.data_file.exists():
                updated_tenders = []
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            tender = json.loads(line)
                            if tender.get('procurement_number') in tender_ids or tender.get('number') in tender_ids:
                                updated_tenders.append(tender)
                
                logger.info(f"Retrieved {len(updated_tenders)} updated tenders")
                return updated_tenders
            
            return []
            
        except subprocess.TimeoutExpired:
            logger.error("Scraper timed out after 1 hour")
            self.metrics['errors'].append("Scraper timeout")
            return []
        except Exception as e:
            logger.error(f"Error running scraper: {e}")
            self.metrics['errors'].append(f"Scraper error: {str(e)}")
            return []
    
    def get_latest_announcement_date(self, df: pd.DataFrame) -> Optional[datetime]:
        """Find the most recent announcement date in local data."""
        if df is None or df.empty or 'published_date' not in df.columns:
            return None
        
        dates = pd.to_datetime(df['published_date'], errors='coerce')
        valid_dates = dates.dropna()
        
        if valid_dates.empty:
            return None
        
        latest = valid_dates.max()
        # Convert to datetime if it's a Timestamp
        if hasattr(latest, 'to_pydatetime'):
            return latest.to_pydatetime()
        return latest
    
    def count_tenders_for_date(self, df: pd.DataFrame, target_date: datetime) -> int:
        """Count tenders announced on a specific date."""
        if df is None or df.empty or 'published_date' not in df.columns:
            return 0
        
        dates = pd.to_datetime(df['published_date'], errors='coerce')
        target_date_only = target_date.date()
        date_mask = dates.dt.date == target_date_only
        
        return date_mask.sum()
    
    def get_website_count_for_date(self, target_date: datetime) -> Optional[int]:
        """Get tender count for a specific announcement date using count-only mode."""
        try:
            import subprocess
            
            date_str = target_date.strftime('%Y-%m-%d')
            
            count_cmd = [
                'python3',
                'main_scrapper/tender_scraper.py',
                '--date-from', date_str,
                '--date-to', date_str,
                '--count-only',
                '--headless', 'true'
            ]
            
            logger.info(f"🔍 Checking website count for {date_str}...")
            
            result = subprocess.run(
                count_cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.warning(f"Count check failed for {date_str}")
                logger.warning(f"Error: {result.stderr[:200]}")
                return None
            
            # Extract count from output (check both stdout and stderr since logging goes to stderr)
            output_to_check = result.stdout + '\n' + result.stderr
            
            for line in output_to_check.split('\n'):
                if 'Website Count:' in line:
                    try:
                        count = int(line.split('Website Count:')[1].split('tenders')[0].strip())
                        logger.info(f"✅ Website count for {date_str}: {count} tenders")
                        return count
                    except Exception as e:
                        logger.warning(f"Failed to parse count from line: {line}")
                        logger.warning(f"Parse error: {e}")
            
            # If we get here, count wasn't found in output
            logger.warning(f"Could not extract count from output for {date_str}")
            logger.warning(f"Stdout preview: {result.stdout[:300]}")
            logger.warning(f"Stderr preview: {result.stderr[:300]}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting website count for {target_date}: {e}")
            return None
    
    def scrape_tenders_by_date_range(self, start_date: datetime, end_date: datetime, df_existing: pd.DataFrame = None) -> List[Dict[str, Any]]:
        """
        Scrape tenders by date range.
        
        First scrapes main tenders, then intelligently decides which need detailed scraping:
        - New tenders: Always scrape details
        - Existing tenders with status change: Scrape details
        - Existing tenders with same status: Skip detailed scraping (optimization)
        """
        logger.info(f"Scraping tenders from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
        
        try:
            import subprocess
            
            # Determine tender type and category from filename
            tender_type = None
            category_code = None
            
            filename = str(self.data_file).lower()
            
            if 'con_detailed' in filename:
                tender_type = 'CON'
                category_code = '60100000'  # Automotive transport
            elif 'nat_detailed' in filename:
                tender_type = 'NAT'
            elif 'spa_detailed' in filename:
                tender_type = 'SPA'
            elif 'cnt_detailed' in filename:
                tender_type = 'CNT'
            elif 'mep_detailed' in filename:
                tender_type = 'MEP'
            elif 'dap_detailed' in filename:
                tender_type = 'DAP'
            elif 'tep_detailed' in filename:
                tender_type = 'TEP'
            elif 'geo_detailed' in filename:
                tender_type = 'GEO'
            elif 'dep_detailed' in filename:
                tender_type = 'DEP'
            elif 'gra_detailed' in filename:
                tender_type = 'GRA'
            
            if not tender_type:
                raise ValueError(f"Could not determine tender type from filename: {self.data_file}")
            
            # Determine optimal scraping date range (default to full range)
            scrape_from = start_date
            scrape_to = end_date
            skip_scraping = False

            # SMART PRE-CHECK: Check full date range
            # The single-date check was flaky ("unknown tenders"), so we check the full range
            # which we know works reliably.
            
            logger.info(f"📊 Checking website count for full range: {scrape_from.strftime('%Y-%m-%d')} to {scrape_to.strftime('%Y-%m-%d')}")
            
            try:
                # Count local tenders in this range
                local_count = 0
                if df_existing is not None and not df_existing.empty and 'published_date' in df_existing.columns:
                    # Filter local data to match the scrape range
                    # Note: Convert both to datetime for accurate comparison
                    pub_dates = pd.to_datetime(df_existing['published_date'], errors='coerce')
                    date_mask = (pub_dates >= pd.to_datetime(scrape_from)) & (pub_dates <= pd.to_datetime(scrape_to))
                    local_count = date_mask.sum()
                
                logger.info(f"   Local Database: {local_count} tenders in this range")

                # Get website count for the same range
                date_from_str = scrape_from.strftime('%Y-%m-%d')
                date_to_str = scrape_to.strftime('%Y-%m-%d')
                
                count_cmd = [
                    'python3',
                    'main_scrapper/tender_scraper.py',
                    '--date-from', date_from_str,
                    '--date-to', date_to_str,
                    '--count-only',
                    '--headless', 'true'
                ]
                
                if tender_type:
                    count_cmd.extend(['--tender-type', tender_type])
                if category_code:
                    count_cmd.extend(['--category-code', category_code])
                
                logger.info(f"   Running website check...")
                result = subprocess.run(
                    count_cmd,
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                website_count = None
                # Check both stdout and stderr
                output_to_check = result.stdout + '\n' + result.stderr
                for line in output_to_check.split('\n'):
                    if 'Website Count:' in line:
                        try:
                            website_count = int(line.split('Website Count:')[1].split('tenders')[0].strip())
                            break
                        except:
                            pass
                
                if website_count is not None:
                    logger.info(f"   Website Count:  {website_count} tenders")
                    
                    if website_count == local_count:
                        logger.info("✅ SMART SKIP: Counts match exactly! Data is up to date.")
                        skip_scraping = True
                    else:
                        diff = website_count - local_count
                        logger.info(f"⚠️  Mismatch: {diff} missing tenders (Website: {website_count}, Local: {local_count})")
                        
                        # GRANULAR BACKWARD CHECK as requested by user
                        # "count date by date starting from last dates in local database"
                        # We backtrack from latest_local_date to find the sync point
                        
                        logger.info("🔍 Starting granular backward check to find divergence point...")
                        
                        # Get latest local date
                        latest_local_date = self.get_latest_announcement_date(df_existing)
                        if latest_local_date:
                            # Start checking from latest date backwards
                            # Limit to 30 days back to avoid endless loop
                            backtrack_limit = 30
                            found_sync_point = False
                            
                            from datetime import timedelta
                            current_check_date = latest_local_date
                            
                            for i in range(backtrack_limit):
                                date_str = current_check_date.strftime('%Y-%m-%d')
                                
                                # Check local count for this specific date
                                local_date_count = self.count_tenders_for_date(df_existing, current_check_date)
                                
                                # Check website count for this specific date
                                logger.info(f"   Checking {date_str} (Backtrack step {i+1}/{backtrack_limit})...")
                                web_date_count = self.get_website_count_for_date(current_check_date)
                                
                                if web_date_count is not None:
                                    if web_date_count == local_date_count:
                                        logger.info(f"   ✅ Sync point found at {date_str} (Counts match: {web_date_count})")
                                        # Divergence starts AFTER this date
                                        scrape_from = current_check_date + timedelta(days=1)
                                        found_sync_point = True
                                        break
                                    else:
                                        logger.info(f"   ❌ Mismatch at {date_str} (Web: {web_date_count}, Local: {local_date_count})")
                                        # Continue checking previous day
                                        current_check_date = current_check_date - timedelta(days=1)
                                else:
                                    logger.warning(f"   Could not verify count for {date_str}, stopping backtrack.")
                                    break
                            
                            if found_sync_point:
                                logger.info(f"📊 Optimized Scraping Range: {scrape_from.strftime('%Y-%m-%d')} to {scrape_to.strftime('%Y-%m-%d')}")
                            else:
                                # Fallback if no sync point found
                                fallback_start = latest_local_date - timedelta(days=backtrack_limit)
                                logger.warning(f"⚠️  No sync point found in last {backtrack_limit} days.")
                                logger.info(f"   Falling back to scrape from {fallback_start.strftime('%Y-%m-%d')}")
                                scrape_from = fallback_start
                        else:
                             # Should not happen if full range check ran, but safety net
                             logger.warning("Could not determine latest local date for granular check.")
                        
                        logger.info(f"📊 Proceeding with scraping from {scrape_from.strftime('%Y-%m-%d')}")
                else:
                    logger.warning("   Could not retrieve website count (extraction failed). Proceeding with scraping.")
                    # Log output for debugging
                    logger.warning(f"   Debug Output: {output_to_check[:200]}...")

            except Exception as e:
                logger.error(f"Error during smart pre-check: {e}")
                logger.info("   Proceeding with scraping as fallback.")

            # Skip scraping if data is already complete
            if skip_scraping:
                logger.info("⏭️  Skipping scraping - data is already up to date")
                return []
            
            # Step 1: Scrape main tenders (NO FILTERS - get ALL tenders)
            logger.info("Step 1: Scraping main tender data (all types, no filters)...")
            main_output_file = PROJECT_ROOT / 'main_scrapper' / 'data' / 'tenders.jsonl'
            
            main_cmd = [
                'python3',
                'main_scrapper/tender_scraper.py',
                '--date-from', scrape_from.strftime('%Y-%m-%d'),
                '--date-to', scrape_to.strftime('%Y-%m-%d'),
                '--headless', 'false'
            ]
            
            # Apply filters to main scraping to be efficient and match the file type
            if tender_type:
                main_cmd.extend(['--tender-type', tender_type])
            if category_code:
                main_cmd.extend(['--category-code', category_code])
            
            # NOTE: We do NOT filter by tender_type or category_code during scraping
            # This ensures we get the correct total count and all tenders
            # Filtering happens later when saving to specific files
            
            logger.info(f"Running: {' '.join(main_cmd)}")
            result = subprocess.run(
                main_cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode != 0:
                logger.error(f"Main scraper failed: {result.stderr}")
                self.metrics['errors'].append(f"Main scraper error: {result.stderr[:200]}")
                return []
            
            logger.info("Main scraping completed")
            
            # Step 1.5: Load main scraped data and compare with existing
            logger.info("Step 1.5: Analyzing which tenders need detailed scraping...")
            
            tenders_needing_details = []
            tenders_skipped = 0
            
            if main_output_file.exists() and df_existing is not None and not df_existing.empty:
                # Read the newly scraped main data
                main_scraped = []
                with open(main_output_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                tender = json.loads(line)
                                # Filter by date range and tender type
                                pub_date_str = tender.get('published_date', '')
                                tender_num = tender.get('number', '')
                                tender_type_field = tender.get('tender_type', '')
                                
                                # IMPORTANT: Filter by tender_type to match this file
                                # Only include tenders that match the current tender_type
                                if tender_type_field != tender_type:
                                    continue  # Skip tenders of other types
                                
                                if pub_date_str and tender_num:
                                    try:
                                        pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
                                        if scrape_from <= pub_date <= scrape_to:
                                            main_scraped.append(tender)
                                    except:
                                        pass
                            except:
                                pass
                
                logger.info(f"Found {len(main_scraped)} tenders in main scrape for date range")
                
                # Compare with existing data
                id_col = 'procurement_number' if 'procurement_number' in df_existing.columns else 'number'
                existing_dict = {row[id_col]: row.get('status', '') for _, row in df_existing.iterrows()}
                
                for tender in main_scraped:
                    tender_num = tender.get('number', '')
                    new_status = tender.get('status', '')
                    
                    if tender_num in existing_dict:
                        old_status = existing_dict[tender_num]
                        
                        # Check if status changed
                        status_changed = (old_status != new_status)
                        
                        # Check if detailed info is missing (CPV codes or suppliers)
                        # This enables "filling in the gaps" for tenders scraped in fast mode
                        existing_tender = df_existing.loc[df_existing[id_col] == tender_num].iloc[0]
                        missing_details = False
                        
                        # Check specific fields that indicate detailed info is missing
                        if 'cpv_codes' not in existing_tender or not existing_tender['cpv_codes']:
                            missing_details = True
                        elif 'suppliers' not in existing_tender: # items/suppliers might be missing
                            missing_details = True
                            
                        if status_changed:
                            logger.debug(f"Status changed for {tender_num}: '{old_status}' -> '{new_status}'")
                            tenders_needing_details.append(tender_num)
                        elif missing_details:
                             logger.debug(f"Missing details for {tender_num} (Status: '{old_status}') - queuing for scrape")
                             tenders_needing_details.append(tender_num)
                        else:
                            # Status unchanged AND details present - skip
                            tenders_skipped += 1
                            logger.debug(f"Skipping {tender_num} - up to date")
                    else:
                        # New tender - needs detailed scraping
                        logger.debug(f"New tender: {tender_num}")
                        tenders_needing_details.append(tender_num)
                
                logger.info(f"📊 Smart Scraping Analysis:")
                logger.info(f"  - Tenders needing detailed scraping: {len(tenders_needing_details)}")
                logger.info(f"  - Tenders skipped (unchanged): {tenders_skipped}")
                logger.info(f"  - Time saved: ~{tenders_skipped * 2} seconds (estimated)")
            else:
                # No existing data or main output - scrape all details
                logger.info("No comparison possible - will scrape all details")
                tenders_needing_details = None  # Will use date range
            
            # Step 2: Scrape detailed info (only for tenders that need it)
            if tenders_needing_details is not None and len(tenders_needing_details) == 0:
                logger.info("✅ No tenders need detailed scraping - skipping Step 2")
                logger.info("All tenders are up-to-date!")
                return []
            
            # Step 2: Scrape detailed tender data (skip if in fast mode)
            if self.skip_detailed:
                logger.info("⏭️  Skipping Step 2: Detailed scraping disabled (fast mode)")
                logger.info("✅ Main scraping completed - use --detailed flag for full data")
                
                # Return the main scraped data
                result_data = []
                if main_output_file.exists():
                    with open(main_output_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    result_data.append(json.loads(line))
                                except:
                                    pass
                return result_data
            
            logger.info("Step 2: Scraping detailed tender data...")
            
            detail_cmd = [
                'python3',
                'detailed_scraper/run_detailed_production.py',
                '--concurrency', '10',
                '--headless',
                '--force'
            ]
            
            # Use specific tender list if we have it, otherwise use date range
            if tenders_needing_details is not None:
                detail_cmd.extend(['--tenders', *tenders_needing_details])
                logger.info(f"Scraping {len(tenders_needing_details)} specific tenders")
            else:
                detail_cmd.extend([
                    '--date-from', start_date.strftime('%Y-%m-%d'),
                    '--date-to', end_date.strftime('%Y-%m-%d')
                ])
                logger.info(f"Scraping all tenders in date range")
            
            if tender_type:
                detail_cmd.extend(['--tender-type', tender_type])
            
            logger.info(f"Running: {' '.join(detail_cmd)}")
            
            result = subprocess.run(
                detail_cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=7200  # 2 hours for detailed scraping
            )
            
            if result.returncode != 0:
                logger.error(f"Detail scraper failed: {result.stderr}")
                self.metrics['errors'].append(f"Detail scraper error: {result.stderr[:200]}")
                return []
            
            logger.info("Detailed scraping completed")
            
            # Reload and return new tenders
            if self.data_file.exists():
                new_tenders = []
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            tender = json.loads(line)
                            pub_date_str = tender.get('published_date', '')
                            if pub_date_str:
                                try:
                                    pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
                                    if start_date <= pub_date <= end_date:
                                        new_tenders.append(tender)
                                except:
                                    pass
                
                logger.info(f"Retrieved {len(new_tenders)} new tenders")
                return new_tenders
            
            return []
            
        except subprocess.TimeoutExpired:
            logger.error("Scraper timed out")
            self.metrics['errors'].append("Scraper timeout")
            return []
        except Exception as e:
            logger.error(f"Error running scraper: {e}")
            self.metrics['errors'].append(f"Scraper error: {str(e)}")
            return []
    
    def upsert_data(self, df_existing: pd.DataFrame, new_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Upsert new data into existing DataFrame.
        
        Updates existing records and adds new ones.
        """
        if not new_data:
            logger.info("No new data to upsert")
            return df_existing
        
        logger.info(f"Upserting {len(new_data)} records...")
        
        # Convert new data to DataFrame
        df_new = pd.DataFrame(new_data)
        
        # Determine ID column - check both dataframes
        # Main scraper uses 'number', detailed scraper uses 'procurement_number'
        if 'number' in df_new.columns:
            id_col = 'number'
        elif 'procurement_number' in df_new.columns:
            id_col = 'procurement_number'
        elif 'number' in df_existing.columns:
            id_col = 'number'
        elif 'procurement_number' in df_existing.columns:
            id_col = 'procurement_number'
        else:
            raise ValueError("No valid ID column found in data (expected 'number' or 'procurement_number')")
        
        logger.info(f"Using '{id_col}' as ID column for deduplication")
        
        if df_existing.empty:
            logger.info("No existing data - all records are new")
            self.metrics['new_tenders_added'] = len(df_new)
            return df_new
        
        # Ensure both dataframes have the ID column
        if id_col not in df_existing.columns:
            logger.error(f"ID column '{id_col}' not found in existing data")
            logger.error(f"Existing columns: {df_existing.columns.tolist()}")
            return df_existing
        
        if id_col not in df_new.columns:
            logger.error(f"ID column '{id_col}' not found in new data")
            logger.error(f"New columns: {df_new.columns.tolist()}")
            return df_existing
        
        # Track changes
        existing_ids = set(df_existing[id_col].tolist())
        new_ids = set(df_new[id_col].tolist())
        
        updates = existing_ids & new_ids
        additions = new_ids - existing_ids
        
        self.metrics['status_changes_detected'] = len(updates)
        self.metrics['new_tenders_added'] = len(additions)
        
        logger.info(f"Updates: {len(updates)}, Additions: {len(additions)}")
        
        # Combine and deduplicate (keep last)
        df_merged = pd.concat([df_existing, df_new], ignore_index=True)
        df_merged = df_merged.drop_duplicates(subset=[id_col], keep='last')
        
        return df_merged
    
    def save_data(self, df: pd.DataFrame):
        """Save data safely using temp file + rename pattern."""
        self.metrics['total_tenders'] = len(df)
        
        if self.dry_run:
            logger.info("=" * 60)
            logger.info("🔍 DRY RUN - Would save:")
            logger.info(f"   File: {self.data_file}")
            logger.info(f"   Records: {len(df)}")
            logger.info(f"   Size: ~{len(df) * 1000 / 1024 / 1024:.2f} MB (estimated)")
            logger.info("=" * 60)
            return
        
        try:
            # Write to temp file
            df.to_json(self.temp_file, orient='records', lines=True, force_ascii=False)
            logger.info(f"Wrote {len(df)} records to temp file")
            
            # Rename temp to actual (atomic operation)
            self.temp_file.rename(self.data_file)
            logger.info(f"Successfully saved to {self.data_file}")
            
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            self.metrics['errors'].append(f"Save error: {str(e)}")
            
            # Clean up temp file
            if self.temp_file.exists():
                self.temp_file.unlink()
    
    def log_run(self, status: str):
        """Log this run to update_history.json."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        log_entry = {
            'run_id': self.run_id,
            'timestamp': self.start_time.isoformat(),
            'status': status,
            'metrics': self.metrics,
            'duration_seconds': round(duration, 2),
            'data_file': str(self.data_file.name),
            'dry_run': self.dry_run
        }
        
        if self.dry_run:
            logger.info("=" * 60)
            logger.info("🔍 DRY RUN - Would log:")
            logger.info(json.dumps(log_entry, indent=2, ensure_ascii=False))
            logger.info("=" * 60)
            return
        
        # Load existing logs
        if UPDATE_LOG_FILE.exists():
            try:
                with open(UPDATE_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        else:
            logs = []
        
        # Append new log
        logs.append(log_entry)
        
        # Keep only last 100 logs
        logs = logs[-100:]
        
        # Save logs
        with open(UPDATE_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Logged run {self.run_id} with status {status}")
    
    def run(self):
        """Execute the full update process."""
        try:
            logger.info("=" * 60)
            logger.info(f"Starting Data Update - Run ID: {self.run_id}")
            logger.info("=" * 60)
            
            # Load existing data
            df_existing = self.load_existing_data()
            
            # Phase A: Re-check active tenders
            active_ids = self.phase_a_recheck_active(df_existing)
            updated_tenders = self.scrape_tenders_by_ids(active_ids) if active_ids else []
            
            # Phase B: Fetch new tenders (with smart scraping)
            start_date, end_date = self.phase_b_fetch_new(df_existing)
            new_tenders = self.scrape_tenders_by_date_range(start_date, end_date, df_existing)
            
            # Combine updates
            all_updates = updated_tenders + new_tenders
            
            # Upsert data
            df_final = self.upsert_data(df_existing, all_updates)
            
            # Save data
            self.save_data(df_final)
            
            # Log success
            self.log_run('SUCCESS')
            
            logger.info("=" * 60)
            logger.info("Update completed successfully!")
            logger.info(f"Total tenders: {self.metrics['total_tenders']}")
            logger.info(f"Active re-checked: {self.metrics['total_active_rechecked']}")
            logger.info(f"Status changes: {self.metrics['status_changes_detected']}")
            logger.info(f"New tenders: {self.metrics['new_tenders_added']}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Update failed: {e}", exc_info=True)
            self.metrics['errors'].append(str(e))
            self.log_run('FAILED')
            raise

    def update_with_data(self, new_tenders: List[Dict[str, Any]], verbose: bool = True):
        """Update with externally provided data (e.g. from global scraper)."""
        try:
            if verbose:
                logger.info("=" * 60)
                logger.info(f"Starting Injection Update - Run ID: {self.run_id}")
                logger.info(f"Injecting {len(new_tenders)} records")
                logger.info("=" * 60)
            
            # Load existing data
            df_existing = self.load_existing_data()
            
            # Upsert data
            df_final = self.upsert_data(df_existing, new_tenders)
            
            # Save data
            self.save_data(df_final)
            
            # Log success
            self.log_run('SUCCESS')
            
            if verbose:
                logger.info("=" * 60)
                logger.info("Injection update completed successfully!")
                logger.info(f"Total tenders: {self.metrics['total_tenders']}")
                logger.info(f"Status changes: {self.metrics['status_changes_detected']}")
                logger.info(f"New tenders: {self.metrics['new_tenders_added']}")
                logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Update failed: {e}", exc_info=True)
            self.metrics['errors'].append(str(e))
            self.log_run('FAILED')
            raise


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tender Data Updater - Smart Sync System')
    parser.add_argument('file', nargs='?', default='con_detailed_tenders.jsonl',
                        help='Data file to update (default: con_detailed_tenders.jsonl)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be updated without making changes')
    
    args = parser.parse_args()
    
    data_file = DATA_DIR / args.file
    
    logger.info(f"Target file: {data_file}")
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE ENABLED - No changes will be made")
    
    # Run updater
    updater = TenderDataUpdater(data_file, dry_run=args.dry_run)
    updater.run()


if __name__ == "__main__":
    main()
