#!/usr/bin/env python3
import argparse
import sys
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set

# Add parent directory to path to import modules
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

# Tender type configurations
TENDER_TYPES = {
    'CON': {
        'file': 'con_detailed_tenders.jsonl',
        'detailed_file': 'con_detailed_tenders.jsonl',
        'name': 'CON (Construction/Automotive)',
        'category_code': '60100000'
    },
    'NAT': {
        'file': 'nat_detailed_tenders.jsonl',
        'detailed_file': 'nat_detailed_tenders.jsonl',
        'name': 'NAT (National)',
        'category_code': None
    },
    'SPA': {
        'file': 'spa_detailed_tenders.jsonl',
        'detailed_file': 'spa_detailed_tenders.jsonl',
        'name': 'SPA (Simplified)',
        'category_code': None
    },
    'CNT': {
        'file': 'cnt_detailed_tenders.jsonl',
        'detailed_file': 'cnt_detailed_tenders.jsonl',
        'name': 'CNT (Contract)',
        'category_code': None
    },
    'MEP': {
        'file': 'mep_detailed_tenders.jsonl',
        'detailed_file': 'mep_detailed_tenders.jsonl',
        'name': 'MEP (Mechanical/Electrical/Plumbing)',
        'category_code': None
    },
    'DAP': {
        'file': 'dap_detailed_tenders.jsonl',
        'detailed_file': 'dap_detailed_tenders.jsonl',
        'name': 'DAP (Direct Award)',
        'category_code': None
    },
    'TEP': {
        'file': 'tep_detailed_tenders.jsonl',
        'detailed_file': 'tep_detailed_tenders.jsonl',
        'name': 'TEP (Technical)',
        'category_code': None
    },
    'GEO': {
        'file': 'geo_detailed_tenders.jsonl',
        'detailed_file': 'geo_detailed_tenders.jsonl',
        'name': 'GEO (Georgian)',
        'category_code': None
    },
    'DEP': {
        'file': 'dep_detailed_tenders.jsonl',
        'detailed_file': 'dep_detailed_tenders.jsonl',
        'name': 'DEP (Department)',
        'category_code': None
    },
    'GRA': {
        'file': 'gra_detailed_tenders.jsonl',
        'detailed_file': 'gra_detailed_tenders.jsonl',
        'name': 'GRA (Grant)',
        'category_code': None
    }
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('detailed_updater')

DATA_DIR = PROJECT_ROOT / 'main_scrapper' / 'data'

class DetailedTenderUpdater:
    def __init__(self, dry_run=False, active_only=True, force_all_missing=False, debug=False):
        self.dry_run = dry_run
        self.active_only = active_only
        self.force_all_missing = force_all_missing
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)

    def scan_and_update(self, target_types: List[str] = None):
        """Scan local files and update active tenders missing details."""
        if target_types is None:
            config_items = TENDER_TYPES.items()
        else:
            config_items = [(k, v) for k, v in TENDER_TYPES.items() if k in target_types]

        logger.info(f"🚀 Starting Detailed Audit (Types: {len(config_items)})")
        logger.info(f"   Mode: {'Active Only (Deadline > Now)' if self.active_only else 'All Time'}")
        if self.force_all_missing:
            logger.info("   Force: Checking ALL missing details regardless of deadline")

        total_candidates = 0
        
        # Pre-load existing detailed IDs to avoid duplication check overhead
        for t_type, config in config_items:
            f_path = DATA_DIR / config['detailed_file']
            
            # 1. Existing Candidates (Status check)
            candidates = []
            existing_ids = set()
            
            if f_path.exists():
                candidates = self._find_candidates(f_path, t_type)
                try:
                    with open(f_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    t = json.loads(line)
                                    tid = t.get('number') or t.get('tender_id')
                                    if tid: existing_ids.add(tid)
                                except: pass
                except: pass
            else:
                 logger.warning(f"ℹ️  File not found for {t_type}: {f_path} (Will look in main list)")

            # 2. New Candidates (From main list)
            # Scan tenders.jsonl for tenders of this type that are NOT in existing_ids
            main_file = DATA_DIR / 'tenders.jsonl'
            new_candidates = self._find_new_candidates(main_file, t_type, existing_ids)
            
            if new_candidates:
                logger.info(f"   🆕 {t_type}: Found {len(new_candidates)} new tenders in main list.")
                candidates.extend(new_candidates)
            
            # Unique candidates
            candidates = list(set(candidates))
            count = len(candidates)
            total_candidates += count
            
            if count > 0:
                logger.info(f"   🎯 {t_type}: Found {count} tenders needing details (Update + New).")
                if not self.dry_run:
                    self._process_candidates(t_type, config, candidates)
            else:
                logger.info(f"   ✅ {t_type}: All active tenders have details.")

        logger.info("="*60)
        logger.info(f"🏁 Audit Complete. Total Updated: {total_candidates}")

    def _find_new_candidates(self, main_file: Path, t_type: str, existing_ids: Set[str]) -> List[str]:
        """Scan main file for new active tenders not in detailed file."""
        if not main_file.exists(): return []
        
        new_candidates = []
        now = datetime.now()
        
        # Map simple type to expected tender_type field value or prefix
        # Actually tenders.jsonl has 'category' or we infer type from number prefix?
        # Number prefix is safest: CON..., NAT..., etc.
        prefix = t_type.upper()
        
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        t = json.loads(line)
                        tid = t.get('number') or t.get('tender_number')
                        if not tid: continue
                        
                        # Type Check
                        if not tid.upper().startswith(prefix):
                            continue
                            
                        # Existence Check
                        if tid in existing_ids:
                            continue
                            
                        # Active Check
                        deadline_str = t.get('deadline_date') # main file uses deadline_date
                        if deadline_str:
                            try:
                                d_date = datetime.strptime(deadline_str, '%Y-%m-%d')
                                # Check if future or today
                                if d_date >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                                    new_candidates.append(tid)
                            except: pass
                    except: pass
        except Exception as e:
            logger.error(f"Error scanning main file: {e}")
            
        return new_candidates

    def _find_candidates(self, f_path: Path, t_type: str) -> List[str]:
        """Read file and find IDs needing update."""
        candidates = []
        now = datetime.now()
        
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        t = json.loads(line)
                        tid = t.get('number') or t.get('tender_id')
                        if not tid: continue
                        
                        # Check Deadline (if active_only)
                        is_active = False
                        deadline_str = t.get('deadline', '')
                        if deadline_str:
                            try:
                                # Parse deadline - format usually "YYYY-MM-DD HH:MM:SS" or similar
                                # Sometimes it's just date. Let's try basic parse.
                                # If scrape stores it as string, we need to be careful.
                                # Assuming simplified format or flexible parse.
                                # Standard format in this project seems to be YYYY-MM-DD usually?
                                # Let's try to parse liberally.
                                d_date = None
                                if len(deadline_str) >= 10:
                                    d_date = datetime.strptime(deadline_str[:10], '%Y-%m-%d')
                                
                                if d_date and d_date >= now: # Future or today
                                    is_active = True
                            except:
                                pass # parsing fail, assume not active?
                        
                        # Check Missing Details
                        missing_details = False
                        if 'cpv_codes' not in t or not t.get('cpv_codes'):
                            missing_details = True
                        elif 'suppliers' not in t: # suppliers list might be empty if no one applied, so check existence
                            missing_details = True
                            
                        # Logic Decision
                        should_update = False
                        
                        if self.force_all_missing:
                            if missing_details: should_update = True
                        elif self.active_only:
                            if is_active and missing_details: should_update = True
                        else:
                            # Not active only, checking all? Usually implies force_all_missing logic but let's say user passed --all-time
                            if missing_details: should_update = True
                            
                        if should_update:
                            candidates.append(tid)
                            
                    except Exception as e:
                        pass
        except Exception as e:
            logger.error(f"Error reading {f_path}: {e}")
            
        return candidates

    def _process_candidates(self, t_type: str, config: dict, candidates: List[str]):
        """Run scrape for candidates."""
        # We can use TenderDataUpdater's scrape_tenders_by_ids
        # Batch them to avoid huge command lines if using subprocess, but class method is better.
        
        from data_updater import TenderDataUpdater
        
        # Batch size
        BATCH_SIZE = 50
        total = len(candidates)
        
        f_path = DATA_DIR / config['detailed_file']
        updater = TenderDataUpdater(f_path, dry_run=self.dry_run, skip_detailed=False)
        
        for i in range(0, total, BATCH_SIZE):
            batch = candidates[i:i+BATCH_SIZE]
            logger.info(f"      Processing batch {i+1}-{min(i+BATCH_SIZE, total)} of {total}...")
            
            try:
                # Direct method call
                updater.scrape_tenders_by_ids(batch)
            except Exception as e:
                logger.error(f"      ❌ Batch failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Update Detailed Tenders (Audit & Fix)")
    parser.add_argument('--type', action='append', help='Filter by tender type (CON, NAT, etc)')
    parser.add_argument('--all-time', action='store_true', help='Check ALL history (ignore deadlines)')
    parser.add_argument('--force-missing', action='store_true', help='Force update for any missing details (implies --all-time)')
    parser.add_argument('--dry-run', action='store_true', help='Show candidates without scraping')
    parser.add_argument('--debug', action='store_true', help='Debug logging')
    
    args = parser.parse_args()
    
    active_only = True
    if args.all_time or args.force_missing:
        active_only = False
        
    updater = DetailedTenderUpdater(
        dry_run=args.dry_run,
        active_only=active_only,
        force_all_missing=args.force_missing,
        debug=args.debug
    )
    
    updater.scan_and_update(target_types=args.type)

if __name__ == "__main__":
    main()
