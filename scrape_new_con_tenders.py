#!/usr/bin/env python3
"""
Incremental Main Scraper - Check and scrape new CON tenders
Checks existing data, scrapes new tenders, and provides a detailed report.
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Set, Dict, Any

def load_existing_tender_numbers(file_path: Path) -> Set[str]:
    """Load existing tender numbers from JSONL file."""
    numbers = set()
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path}")
        return numbers
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    num = data.get('number', '').strip()
                    if num:
                        numbers.add(num)
                except json.JSONDecodeError:
                    continue
    
    return numbers

def get_date_range(days_back: int = 30) -> tuple:
    """Get date range for scraping (from X days ago to today + 30 days)."""
    today = datetime.now()
    start_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
    end_date = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    return start_date, end_date

def run_scraper(start_date: str, end_date: str, output_file: Path, concurrency: int = 10) -> Dict[str, Any]:
    """Run the production scraper and return results."""
    print(f"\n🚀 Starting scraper...")
    print(f"   Date range: {start_date} to {end_date}")
    print(f"   Concurrency: {concurrency} workers")
    print(f"   Output: {output_file}")
    print(f"   Filters: CON type, CPV 60100000")
    print()
    
    cmd = [
        'python3',
        'main_scrapper/run_production.py',
        '--date-from', start_date,
        '--date-to', end_date,
        '--tender-type', 'CON',
        '--category-code', '60100000',
        '--concurrency', str(concurrency),
        '--data-file', str(output_file)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse output for statistics
        output = result.stdout + result.stderr
        
        # Extract statistics from output
        new_tenders = 0
        duplicates = 0
        
        for line in output.split('\n'):
            if 'New tenders scraped:' in line:
                try:
                    new_tenders = int(line.split(':')[1].strip())
                except:
                    pass
            elif 'Duplicates skipped:' in line:
                try:
                    duplicates = int(line.split(':')[1].strip())
                except:
                    pass
        
        return {
            'success': True,
            'new_tenders': new_tenders,
            'duplicates': duplicates,
            'output': output
        }
    
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'error': str(e),
            'output': e.stdout + e.stderr
        }

def print_report(before_count: int, after_count: int, result: Dict[str, Any]):
    """Print detailed report of scraping results."""
    print("\n" + "=" * 70)
    print("SCRAPING REPORT")
    print("=" * 70)
    
    if result['success']:
        new_added = after_count - before_count
        
        print(f"✅ Scraping completed successfully!")
        print()
        print(f"📊 Statistics:")
        print(f"   Tenders before:        {before_count:5d}")
        print(f"   Tenders after:         {after_count:5d}")
        print(f"   New tenders added:     {new_added:5d}")
        print(f"   Duplicates skipped:    {result.get('duplicates', 0):5d}")
        print()
        
        if new_added > 0:
            print(f"🎉 Successfully added {new_added} new CON tenders!")
        else:
            print(f"ℹ️  No new tenders found.")
    else:
        print(f"❌ Scraping failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    print("=" * 70)

def main():
    print("=" * 70)
    print("CON TENDERS INCREMENTAL SCRAPER")
    print("=" * 70)
    print()
    
    # Configuration
    output_file = Path('main_scrapper/data/con_filter.jsonl')
    days_back = 30  # How many days back to check
    concurrency = 10  # Number of parallel workers
    
    # Step 1: Check existing data
    print("📂 Step 1: Checking existing data...")
    before_count = len(load_existing_tender_numbers(output_file))
    print(f"   Found {before_count} existing CON tenders")
    print()
    
    # Step 2: Determine date range
    print("📅 Step 2: Determining date range...")
    start_date, end_date = get_date_range(days_back)
    print(f"   Scraping from {start_date} to {end_date}")
    print(f"   (Last {days_back} days + next 30 days)")
    print()
    
    # Step 3: Run scraper
    print("🔍 Step 3: Scraping new tenders...")
    result = run_scraper(start_date, end_date, output_file, concurrency)
    
    # Step 4: Check results
    print("\n📊 Step 4: Analyzing results...")
    after_count = len(load_existing_tender_numbers(output_file))
    print(f"   Now have {after_count} total CON tenders")
    print()
    
    # Step 5: Print report
    print_report(before_count, after_count, result)
    
    # Save log
    log_file = Path('scraping_report.log')
    with open(log_file, 'a') as f:
        f.write(f"\n{'=' * 70}\n")
        f.write(f"Scraping Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'=' * 70}\n")
        f.write(f"Date range: {start_date} to {end_date}\n")
        f.write(f"Before: {before_count} tenders\n")
        f.write(f"After: {after_count} tenders\n")
        f.write(f"New: {after_count - before_count} tenders\n")
        f.write(f"Success: {result['success']}\n")
    
    print(f"\n💾 Full log saved to: {log_file}")
    
    return 0 if result['success'] else 1

if __name__ == "__main__":
    sys.exit(main())
