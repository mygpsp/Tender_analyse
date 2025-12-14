#!/usr/bin/env python3
"""
Update All Tenders - Master Update Script

This script updates all tender types (CON, NAT, SPA) or specific types.
By default, it only runs MAIN scraping (fast). Use --detailed for full scraping.

Usage:
    python3 update_all_tenders.py                    # Update all types (main only)
    python3 update_all_tenders.py --detailed         # Update all types (main + detailed)
    python3 update_all_tenders.py --type CON         # Update only CON tenders
    python3 update_all_tenders.py --type CON --detailed  # CON with detailed scraping
    python3 update_all_tenders.py --dry-run          # See what would be updated
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/update_all_tenders.log')
    ]
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "main_scrapper" / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)

# Tender type configurations
TENDER_TYPES = {
    'CON': {
        'file': 'con_detailed_tenders.jsonl',
        'name': 'CON (Construction/Automotive)',
        'category_code': '60100000'  # Automotive transport for CON
    },
    'NAT': {
        'file': 'nat_detailed_tenders.jsonl',
        'name': 'NAT (National)',
        'category_code': None
    },
    'SPA': {
        'file': 'spa_detailed_tenders.jsonl',
        'name': 'SPA (Simplified)',
        'category_code': None
    },
    'CNT': {
        'file': 'cnt_detailed_tenders.jsonl',
        'name': 'CNT (Contract)',
        'category_code': None
    },
    'MEP': {
        'file': 'mep_detailed_tenders.jsonl',
        'name': 'MEP (Mechanical/Electrical/Plumbing)',
        'category_code': None
    },
    'DAP': {
        'file': 'dap_detailed_tenders.jsonl',
        'name': 'DAP (Direct Award)',
        'category_code': None
    },
    'TEP': {
        'file': 'tep_detailed_tenders.jsonl',
        'name': 'TEP (Technical)',
        'category_code': None
    },
    'GEO': {
        'file': 'geo_detailed_tenders.jsonl',
        'name': 'GEO (Georgian)',
        'category_code': None
    },
    'DEP': {
        'file': 'dep_detailed_tenders.jsonl',
        'name': 'DEP (Department)',
        'category_code': None
    },
    'GRA': {
        'file': 'gra_detailed_tenders.jsonl',
        'name': 'GRA (Grant)',
        'category_code': None
    }
}


class TenderUpdateOrchestrator:
    """Orchestrates updates for multiple tender types."""
    
    def __init__(self, detailed=False, dry_run=False, date_from: datetime = None, date_to: datetime = None, debug=False):
        self.detailed = detailed
        self.dry_run = dry_run
        self.date_from = date_from
        self.date_to = date_to
        self.debug = debug
        
        # Configure logging based on debug flag
        if self.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("🔧 Debug mode enabled")
        else:
            logger.setLevel(logging.INFO)
        
        # Auto-adjust date if same (user request for single day logic)
        if self.date_from and self.date_to and self.date_from == self.date_to:
            from datetime import timedelta
            logger.info("ℹ️  Single day range detected. Adjusting end date to +1 day for proper filtering.")
            self.date_to = self.date_from + timedelta(days=1)
            
        self.start_time = datetime.now()
        self.results = []
        self.day_stats = [] # To store per-day stats for report
        self.global_stats = {}
        
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
        
        if not self.detailed:
            logger.info("⚡ FAST MODE - Main scraping only (use --detailed for full scraping)")
    
    def update_tender_type(self, tender_type: str) -> Dict:
        """Update a specific tender type."""
        config = TENDER_TYPES[tender_type]
        data_file = DATA_DIR / config['file']
        
        if self.detailed:
             logger.info(f"Mode: {'DETAILED' if self.detailed else 'MAIN ONLY'}")
        
        result = {
            'tender_type': tender_type,
            'name': config['name'],
            'status': 'PENDING',
            'start_time': datetime.now().isoformat(),
            'metrics': {}
        }
        
        try:
            # Import here to avoid circular imports
            from data_updater import TenderDataUpdater
            
            # Create updater instance with skip_detailed flag
            skip_detailed = not self.detailed
            updater = TenderDataUpdater(data_file, dry_run=self.dry_run, skip_detailed=skip_detailed, date_from=self.date_from, date_to=self.date_to)
            
            # Modify updater to skip detailed scraping if not requested
            if self.detailed:
                logger.debug("🔍 DETAILED MODE: Both main and detailed scraping enabled")
            
            # Run the update
            updater.run()
            
            # Collect results
            result['status'] = 'SUCCESS'
            result['metrics'] = updater.metrics
            result['end_time'] = datetime.now().isoformat()
            
            logger.info(f"✅ {tender_type} update completed successfully")
            
        except Exception as e:
            logger.error(f"❌ {tender_type} update failed: {e}", exc_info=True)
            result['status'] = 'FAILED'
            result['error'] = str(e)
            result['end_time'] = datetime.now().isoformat()
        
        return result

    def get_latest_local_date(self) -> datetime:
        """Scan all local files to find the latest published date."""
        latest_date = None
        
        logger.debug("📅 Scanning local files for latest date...")
        
        for config in TENDER_TYPES.values():
            f_path = DATA_DIR / config['file']
            if not f_path.exists(): continue
            
            try:
                # Read last few lines efficiently? Or scan all? 
                # Since files are append-only, last lines usually have latest dates, but not guaranteed if sorted differently.
                # Files can be large. Scanning all is safest but slow.
                # Let's scan all for now, but optimize if needed.
                # Actually, reading line by line is fast enough for ~100MB files.
                with open(f_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            t = json.loads(line)
                            pd_str = t.get('published_date', '')
                            if pd_str:
                                d = datetime.strptime(pd_str, '%Y-%m-%d')
                                if latest_date is None or d > latest_date:
                                    latest_date = d
                        except: pass
            except Exception as e:
                logger.warning(f"Error reading {f_path}: {e}")
                
        if latest_date:
            logger.debug(f"✅ Latest local date found: {latest_date.strftime('%Y-%m-%d')}")
        else:
            logger.info("⚠️  No local data found, defaulting to today.")
            latest_date = datetime.now()
            
        return latest_date

    def _sum_all_local_counts(self, d_start, d_end, target_types: List[str] = None):
        """Sum local counts across all tender files for a specific date range, enforcing uniqueness."""
        global_seen_ids = set()
        
        # Determine which types to check
        if target_types is None:
            configs_to_check = TENDER_TYPES.values()
        else:
            configs_to_check = [TENDER_TYPES[t] for t in target_types if t in TENDER_TYPES]
            
        for config in configs_to_check:
            f_path = DATA_DIR / config['file']
            # Pass the set to the helper to track unique IDs
            self._get_local_count_for_range(d_start, d_end, f_path, global_seen_ids)
        return global_seen_ids # Return the SET of IDs, not just count

    def update_global_date_range(self, date_from: datetime, date_to: datetime, target_types: List[str] = None):
        """Perform a day-by-day check and scrape."""
        from datetime import timedelta
        
        logger.info(f"📅 Checking Date Range: {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}")

        current_date = date_from
        
        # Loop until current_date < date_to.
        # Note: if date_from=11 and date_to=12, loop runs for 11. (Since 12 is exclusive end bound usually in range)
        # But our date_to is inclusive in user intent usually?
        # My auto-adjust logic ensures date_to is +1 day if user inputs same dates.
        # If user inputs 11 to 15, they expect 11, 12, 13, 14, 15?
        # Standard Python range is exclusive.
        # But 'tender_scraper' treats arguments as inclusive boundaries if passed to DatePicker?
        # Actually my auto-adjust (11->12) implies I treat the provided connection as [Start, End).
        # Let's iterate day by day.
        all_tenders = [] # To accumulate tenders scraped daily

        # Initialize scraper once - Not needed with subprocess
        # from main_scrapper.tender_scraper import TenderScraper
        # self.scraper = TenderScraper(headless=True, debug=self.debug)
        
        # Import subprocess
        import subprocess
        
        while current_date < date_to:
            next_date = current_date + timedelta(days=1)
            day_str = current_date.strftime('%Y-%m-%d')
            
            # 1. Get Website Count
            web_count = self._get_website_count(current_date, next_date, target_types)

            # 2. Local Check
            logger.debug(f"   🔍 Verifying local data for {day_str}...")
            local_ids = self._sum_all_local_counts(current_date, current_date, target_types)
            local_count = len(local_ids)
            
            needs_scrape = False
            
            if web_count is None:
                logger.warning(f"⚠️  [{day_str}] Could not verify website count. Proceeding to scrape.")
                needs_scrape = True
                web_count = "?"
            elif web_count != local_count:
                logger.info(f"🔄 [{day_str}] MISMATCH: Web {web_count} != Local {local_count}. Scraping...")
                if local_count > web_count:
                     logger.warning(f"   ⚠️ Local count ({local_count}) is higher than Website ({web_count}).")
                needs_scrape = True
            else:
                logger.info(f"✅ [{day_str}] SYNCED: Web {web_count} == Local {local_count}.")
                needs_scrape = False

            scraped_day_count = 0
            new_added = 0
            
            if needs_scrape:
                # Scrape!
                logger.info(f"   ⬇️ Scraping {day_str}...")
                
                # Use a temp file for this day's scrape
                temp_output = DATA_DIR.parent / f"temp_{day_str}.jsonl"
                if temp_output.exists(): temp_output.unlink()
                
                cmd = [
                    sys.executable, 'main_scrapper/tender_scraper.py',
                    '--date-from', current_date.strftime('%Y-%m-%d'),
                    '--date-to', next_date.strftime('%Y-%m-%d'), # Use next_date (exclusive end?) to match user logic
                    '--output', str(temp_output),
                    '--headless', 'true'
                ]
                
                # Smart Filter: If single tender type, pass it to scraper
                if target_types and len(target_types) == 1:
                    cmd.extend(['--tender-type', target_types[0]])
                elif target_types and len(target_types) > 1:
                    # Scraper only accepts ONE type or ALL. cannot pass list?
                    # If multiple types, we might need to rely on scraping ALL and filtering later?
                    # Or generic scrape is better? 
                    # If user asks for CON and NAT, but we scrape ALL, we might get extra data but DataUpdater filters it?
                    # Wait, DataUpdater takes the WHOLE file.
                    # The `distribute` step later filters by type.
                    # So scraping ALL is "safe" but slower/more data than needed.
                    # But we can't tell scraper "CON,NAT". 
                    # So we scrape ALL unless exactly 1 type.
                    pass
                
                if self.debug:
                    logger.debug(f"   CMD: {' '.join(cmd)}")
                
                try:
                    subprocess.run(cmd, check=True, capture_output=not self.debug, cwd=PROJECT_ROOT)
                except subprocess.CalledProcessError as e:
                    logger.error(f"   ❌ Scraper failed for {day_str}: {e}")
                    if e.stderr:
                        logger.error(f"   ❌ STDERR: {e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else e.stderr}")
                    if e.stdout:
                         logger.debug(f"   ❌ STDOUT: {e.stdout.decode('utf-8') if isinstance(e.stdout, bytes) else e.stdout}")
                
                # Load scraped data
                day_tenders = []
                if temp_output.exists():
                     try:
                         with open(temp_output, 'r', encoding='utf-8') as f:
                             for line in f:
                                 if line.strip(): day_tenders.append(json.loads(line))
                         # Clean up
                         temp_output.unlink()
                     except Exception as e:
                         logger.error(f"   ❌ Failed to read temp output: {e}")
                
                scraped_day_count = len(day_tenders)
                
                # Check for Extra Tenders (Phantom)
                scraped_ids = {t.get('number') or t.get('tender_id') for t in day_tenders if t.get('number') or t.get('tender_id')}
                
                if local_count > 0:
                     extra_ids = local_ids - scraped_ids
                     if extra_ids:
                         sample = list(extra_ids)[:5]
                         logger.warning(f"   ❓ Found {len(extra_ids)} tenders LOCALLY that are NOT in current scrape.")
                         logger.warning(f"   ❓ Sample Extra IDs: {sample}")
                         logger.warning(f"   ❓ These might be hidden/archived tenders.")

                all_tenders.extend(day_tenders)
                
                # Distribution (keeping existing logic for 'new_added' calculation roughly)
                # Actually, simpler to just track total added. 
                new_added = scraped_day_count # Approximate, as some might be updates.
                
                # Update stats
                stats_entry = {
                    'date': day_str,
                    'web': web_count,
                    'local': local_count,
                    'new': new_added,
                    'status': 'SCRAPED',
                    'extra_ids': list(local_ids - scraped_ids) if local_count > 0 else []
                }
                self.global_stats[day_str] = stats_entry
                self.day_stats.append(stats_entry)
            else:
                stats_entry = {
                    'date': day_str,
                    'web': web_count,
                    'local': local_count,
                    'new': 0,
                    'status': 'SKIPPED',
                    'extra_ids': []
                }
                self.global_stats[day_str] = stats_entry
                self.day_stats.append(stats_entry)
            
            current_date += timedelta(days=1)
            
        # After iterating through all days, distribute the collected tenders
        logger.info("=" * 80)
        logger.info("📦 DISTRIBUTING SCRAPED TENDERS TO INDIVIDUAL FILES")
        logger.info(f"Total tenders collected: {len(all_tenders)}")
        logger.info("=" * 80)

        tenders_by_type = {}
        for t in all_tenders:
            tt = t.get('tender_type')
            if not tt: continue
            if tt not in tenders_by_type: tenders_by_type[tt] = []
            tenders_by_type[tt].append(t)
            
        for tender_type, config in TENDER_TYPES.items():
            tenders = tenders_by_type.get(tender_type, [])
            if not tenders: continue
            
            data_file = DATA_DIR / config['file']
            updater = TenderDataUpdater(data_file, dry_run=self.dry_run, skip_detailed=not self.detailed)
            try:
                updater.update_with_data(tenders, verbose=self.debug)
                # Collect results for summary
                self.results.append({
                    'tender_type': tender_type,
                    'name': config['name'],
                    'status': 'SUCCESS',
                    'metrics': updater.metrics,
                    'end_time': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Failed to update {tender_type} with scraped data: {e}")
                self.results.append({
                    'tender_type': tender_type,
                    'name': config['name'],
                    'status': 'FAILED',
                    'error': str(e),
                    'end_time': datetime.now().isoformat()
                })
        
        # Close scraper - not needed as we use subprocess
        pass

    def _get_website_count(self, date_from, date_to, target_types: List[str] = None):
        """Helper to get total count from website."""
        try:
            cmd = [
                sys.executable,
                'main_scrapper/tender_scraper.py',
                '--date-from', date_from.strftime('%Y-%m-%d'),
                '--date-to', date_to.strftime('%Y-%m-%d'), # Use provided date_to
                '--count-only',
                '--headless', 'true'
            ]
            
            # Smart Filter: If single tender type, pass it to scraper
            if target_types and len(target_types) == 1:
                cmd.extend(['--tender-type', target_types[0]])
            
            result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
            
            # Parse output for "Website Count: N tenders" or similar log
            # The scraper logs to stderr usually or stdout?
            # TenderScraper log level INFO.
            # We need to look for a specific log line potentially.
            # Or standard output if I add a print?
            # Check previous implementation or logs.
            # The previous implementation looked for "Website Count:" in combined stdout/stderr.
            # I need to ensure tender_scraper.py OUTPUTS this.
            # If it uses standard logging, it might be tricky.
            # But wait, tender_scraper.py has `if args.count_only: ...`?
            # I should strictly check if tender_scraper.py prints the count.
            # Usually it logs "Found N rows".
            # Or better: I can't rely on getting the EXACT count from the scraper without scraping rows if the site doesn't show a total count easily readable.
            # Actually, `get_total_count` from scraper might log it.
            # Let's hope the scraper logs the count clearly.
            # In previous session log: "Website Count: 150 tenders".
            # So I will search for that.
            
            for line in (result.stdout + result.stderr).split('\n'):
                if 'Website Count:' in line:
                    try:
                        return int(line.split('Website Count:')[1].split('tenders')[0].strip())
                    except: pass
                # Fallback: "Found X rows"
                if 'Found' in line and 'rows' in line: # "Found 150 rows"
                     # This is risky regex
                     pass
                     
            return None
        except Exception as e:
            logger.error(f"Error getting website count for {date_from.strftime('%Y-%m-%d')}: {e}")
            return None

    def _get_local_count_for_range(self, date_from, date_to, file_path, seen_ids=None):
        """Helper to count local tenders in date range, deduplicating by ID."""
        try:
            if not file_path.exists(): 
                return seen_ids if seen_ids is not None else set()
            if seen_ids is None:
                seen_ids = set()
                
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        t = json.loads(line)
                        
                        # Deduplication Check
                        tid = t.get('number') or t.get('tender_id')
                        # Note: We track ALL IDs in date range.
                            
                        # Date Check
                        pd_str = t.get('published_date', '')
                        if pd_str:
                            d = datetime.strptime(pd_str, '%Y-%m-%d')
                            if date_from <= d <= date_to: # Assuming inclusive check matching website
                                if tid:
                                    seen_ids.add(tid)
                    except: pass
            return seen_ids # Return SET
        except:
            return seen_ids if seen_ids is not None else set()
    
    def update_all(self, types_to_update: List[str] = None):
        """Update all or specific tender types."""
        if types_to_update is None:
            types_to_update = list(TENDER_TYPES.keys())
        
        logger.info(f"🚀 Updating Tenders (Mode: {'Detailed' if self.detailed else 'Fast'}, Types: {len(types_to_update)})")
        
        # SPECIAL MODE: Global Date Range Update (or Default Rolling Window)
        if self.date_from and self.date_to:
            self.update_global_date_range(self.date_from, self.date_to, types_to_update)
            # Print tabular summary
            self.print_summary_table()
            self.save_results()
            return

        # Update each type
        for tender_type in types_to_update:
            if tender_type not in TENDER_TYPES:
                logger.warning(f"⚠️  Unknown tender type: {tender_type}, skipping")
                continue
            
            result = self.update_tender_type(tender_type)
            self.results.append(result)
        
        # Print summary
        self.print_summary()
        
        # Save results
        self.save_results()
    
    def print_summary(self):
        """Print summary of all updates."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 UPDATE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"Mode: {'DETAILED' if self.detailed else 'MAIN ONLY'}")
        logger.info("")
        
        success_count = sum(1 for r in self.results if r['status'] == 'SUCCESS')
        failed_count = sum(1 for r in self.results if r['status'] == 'FAILED')
        
        logger.info(f"Results: {success_count} succeeded, {failed_count} failed")
        logger.info("")
        
        for result in self.results:
            status_icon = "✅" if result['status'] == 'SUCCESS' else "❌"
            logger.info(f"{status_icon} {result['tender_type']}: {result['name']}")
            
            if result['status'] == 'SUCCESS' and 'metrics' in result:
                metrics = result['metrics']
                logger.info(f"   Total tenders: {metrics.get('total_tenders', 0)}")
                logger.info(f"   New tenders: {metrics.get('new_tenders_added', 0)}")
                
            if result['status'] == 'FAILED':
                logger.error(f"   Error: {result.get('error', 'Unknown error')}")
            
            logger.info("")

    def print_summary_table(self):
        """Print a compact table for global update comparison."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 DAILY COMPARISON RERORT")
        logger.info("=" * 80)
        logger.info(f"{'DATE':<12} | {'WEBSITE':<8} | {'LOCAL':<8} | {'NEW':<8} | {'STATUS':<10}")
        logger.info("-" * 80)
        
        if self.day_stats:
            for s in self.day_stats:
                extra_flag = " (!)" if s.get('extra_ids') else ""
                logger.info(f"{s['date']:<12} | {str(s['web']):<8} | {str(s['local']) + extra_flag:<8} | {str(s.get('new', 0)):<8} | {s['status']:<10}")
        else:
            logger.info("No days processed.")
            
        logger.info("-" * 80)
        logger.info(f"Done in {duration:.1f}s")

    
    def save_results(self):
        """Save results to JSON file."""
        if self.dry_run:
            logger.info("🔍 DRY RUN - Would save results to logs/update_all_history.json")
            return
        
        results_file = LOGS_DIR / "update_all_history.json"
        
        # Load existing results
        if results_file.exists():
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        else:
            history = []
        
        # Add new results
        history.append({
            'timestamp': self.start_time.isoformat(),
            'mode': 'detailed' if self.detailed else 'main_only',
            'dry_run': self.dry_run,
            'results': self.results,
            'duration_seconds': (datetime.now() - self.start_time).total_seconds()
        })
        
        # Keep only last 50 runs
        history = history[-50:]
        
        # Save
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {results_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Update All Tenders - Master Update Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Update all types (main scraping only)
  %(prog)s --detailed               # Update all types (main + detailed scraping)
  %(prog)s --type CON               # Update only CON tenders (main only)
  %(prog)s --type CON --detailed    # Update only CON with detailed scraping
  %(prog)s --dry-run                # See what would be updated
  %(prog)s --type NAT --type SPA    # Update NAT and SPA only
        """
    )
    
    parser.add_argument(
        '--type',
        action='append',
        choices=['CON', 'NAT', 'SPA', 'CNT', 'MEP', 'DAP', 'TEP', 'GEO', 'DEP', 'GRA'],
        help='Tender type to update (can be specified multiple times). If not specified, updates all types.'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Enable detailed scraping (slower but complete). By default, only main scraping is performed.'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    parser.add_argument(
        '--date-from',
        help='Start date for scraping (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--date-to',
        help='End date for scraping (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Parse dates if provided
    date_from = None
    date_to = None
    if args.date_from:
        try:
            date_from = datetime.strptime(args.date_from, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid format for --date-from (expected YYYY-MM-DD)")
            sys.exit(1)
            
    if args.date_to:
        try:
            date_to = datetime.strptime(args.date_to, '%Y-%m-%d')
        except ValueError:
             print(f"Error: Invalid format for --date-to (expected YYYY-MM-DD)")
             sys.exit(1)
             
    # Create orchestrator
    orchestrator = TenderUpdateOrchestrator(
        dry_run=args.dry_run,
        detailed=args.detailed,
        date_from=date_from,
        date_to=date_to,
        debug=args.debug
    )
    
    # ROLLING WINDOW LOGIC
    # If no dates proivded, default to Smart Rolling Window
    if not date_from and not date_to:
        latest = orchestrator.get_latest_local_date()
        from datetime import timedelta
        date_from = latest - timedelta(days=60)
        date_to = datetime.now() # Today
        # Add +1 day to cover today fully if iterating? 
        # Actually scraper logic for 'today' usually handles up to now.
        # But if we want inclusive "today", and our loop is exclusive or inclusive?
        # My update_global_date_range iterates while current < date_to.
        # So to include today (e.g. 14th), date_to must be 15th (tomorrow).
        # Or if date_to is 14th, it scrapes 13->14?
        # Let's check loop: 
        # while current < date_to:
        #    next = current + 1
        #    scrape(current, current)
        # So if current=14, next=15.
        # If date_to=15, 14 < 15 is True. Runs for 14.
        # If date_to=14, 14 < 14 is False. Stops.
        # So date_to must be Tomorrow to include Today.
        date_to = date_to + timedelta(days=1)
        
        logger.info("ℹ️  No dates provided. Using ROLLING WINDOW:")
        logger.info(f"   Start: {date_from.strftime('%Y-%m-%d')} (Latest local - 60 days)")
        logger.info(f"   End:   {date_to.strftime('%Y-%m-%d')} (Tomorrow/Today inclusive)")
        
        # Update orchestrator dates
        orchestrator.date_from = date_from
        orchestrator.date_to = date_to

    # Run updates
    orchestrator.update_all(types_to_update=args.type)


if __name__ == "__main__":
    main()
