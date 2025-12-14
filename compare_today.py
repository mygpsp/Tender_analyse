#!/usr/bin/env python3
import json
import logging
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('compare_today')

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "main_scrapper" / "data"

# Tender type configurations (Inline to avoid import issues)
TENDER_TYPES = {
    'CON': {'file': 'con_detailed_tenders.jsonl'},
    'NAT': {'file': 'nat_detailed_tenders.jsonl'},
    'SPA': {'file': 'spa_detailed_tenders.jsonl'},
    'CNT': {'file': 'cnt_detailed_tenders.jsonl'},
    'MEP': {'file': 'mep_detailed_tenders.jsonl'},
    'DAP': {'file': 'dap_detailed_tenders.jsonl'},
    'TEP': {'file': 'tep_detailed_tenders.jsonl'},
    'GEO': {'file': 'geo_detailed_tenders.jsonl'},
    'DEP': {'file': 'dep_detailed_tenders.jsonl'},
    'GRA': {'file': 'gra_detailed_tenders.jsonl'}
}

def get_website_count_today():
    """Get the total tender count from the website for today."""
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    # Use same day for from/to (inclusive in scraper logic usually requires next day as bound if using date pickers,
    # but let's stick to update_all_tenders logic: day -> day+1)
    date_from = today_str
    date_to = today_str # Same day usually means that day only if scraper handles it right. 
    # update_all_tenders uses day -> day (inclusive check). 
    
    cmd = [
        sys.executable,
        'main_scrapper/tender_scraper.py',
        '--date-from', date_from,
        '--date-to', date_to,
        '--count-only',
        '--headless', 'true'
    ]
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
        for line in (result.stdout + result.stderr).split('\n'):
            if 'Website Count:' in line:
                try:
                    return int(line.split('Website Count:')[1].split('tenders')[0].strip())
                except: pass
            if 'Found' in line and 'rows' in line: # Fallback
                 # extract number? risky.
                 pass
    except Exception as e:
        logger.error(f"Error getting website count: {e}")
    return None

def get_local_count_today():
    """Count local tenders with published_date == today."""
    today_str = datetime.now().strftime('%Y-%m-%d')
    total_local = 0
    
    for t_type, config in TENDER_TYPES.items():
        f_path = DATA_DIR / config['file']
        if not f_path.exists(): continue
        
        type_count = 0
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        t = json.loads(line)
                        if t.get('published_date') == today_str:
                            type_count += 1
                    except: pass
        except: pass
        total_local += type_count
        
    return total_local

def get_local_active_count():
    """Count local tenders with deadline >= today (Active)."""
    now = datetime.now()
    total_active = 0
    
    for t_type, config in TENDER_TYPES.items():
        f_path = DATA_DIR / config['file']
        if not f_path.exists(): continue
        
        type_count = 0
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        t = json.loads(line)
                        d_str = t.get('deadline', '')
                        if d_str:
                            try:
                                d_date = datetime.strptime(d_str[:10], '%Y-%m-%d')
                                if d_date >= now:
                                    type_count += 1
                            except: pass
                    except: pass
        except: pass
        total_active += type_count
    return total_active

def get_website_active_count():
    """Get the active tender count from the website using the default view (no date filters)."""
    # The website default view shows "Active" tenders (Upcoming deadlines).
    # We call the scraper without date arguments to get this count.
    
    cmd = [
        sys.executable,
        'main_scrapper/tender_scraper.py',
        '--count-only',
        '--headless', 'true'
    ]
    
    try:
        # Without date filters, scraper might be slower to load initially if default list is huge,
        # but we only need the count from pagination.
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=90)
        for line in (result.stdout + result.stderr).split('\n'):
            if 'Website Count:' in line:
                try:
                    return int(line.split('Website Count:')[1].split('tenders')[0].strip())
                except: pass
    except Exception as e:
        logger.error(f"Error getting website active count: {e}")
    return None

def main():
    print("=" * 60)
    print(f"📊 TENDER REPORT FOR {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    # 1. Published Today
    print("1️⃣  PUBLISHED TODAY (New tenders appearing today)")
    print("   ⏳ Checking Website (Today)...")
    web_today = get_website_count_today()
    print("   ⏳ Checking Local Files (Published Today)...")
    local_today = get_local_count_today()
    
    print("-" * 40)
    print(f"   WEBSITE : {web_today if web_today is not None else 'Error'}")
    print(f"   LOCAL   : {local_today}")
    print("-" * 40)
    
    if web_today is not None:
        if web_today == local_today:
            print("   ✅ SYNCED (Published today)")
        else:
            diff = abs(web_today - local_today)
            print(f"   ❌ MISMATCH (Diff: {diff})")
    
    print("\n")
    
    # 2. Active Tenders
    print("2️⃣  ACTIVE TENDERS (Deadline is in the future)")
    print("   ⏳ Checking Website (Default View / Active)...")
    web_active = get_website_active_count()
    
    print("   ⏳ Checking Local Files (Deadline >= Now)...")
    local_active = get_local_active_count()
    
    print("-" * 40)
    print(f"   WEBSITE : {web_active if web_active is not None else 'Error'}")
    print(f"   LOCAL   : {local_active}")
    print("-" * 40)
    
    if web_active is not None:
        if web_active == local_active:
             print("   ✅ SYNCED (Active count matches)")
        else:
            diff = abs(web_active - local_active)
            print(f"   ⚠️  MISMATCH (Diff: {diff})")
            print("       (Note: Website count is based on default view; Local is deadline >= now.)")

    print("=" * 60)

if __name__ == "__main__":
    main()
