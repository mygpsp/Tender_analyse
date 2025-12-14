#!/usr/bin/env python3
"""
Incremental scraper for new tenders.

This script:
1. Analyzes existing data to find the latest dates
2. Suggests a start date for scraping new tenders
3. Can test if there are new tenders without scraping
4. Scrapes only new tenders, avoiding duplicates

Usage:
    # Check what date to start from
    python3 incremental_scraper.py --check
    
    # Test if there are new tenders (dry-run)
    python3 incremental_scraper.py --test --days 7
    
    # Scrape new tenders from suggested date
    python3 incremental_scraper.py --scrape
    
    # Scrape from specific date
    python3 incremental_scraper.py --scrape --date-from 2025-11-29
"""

import argparse
import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Set, Optional, Tuple

from tender_scraper import TenderScraper, build_configs, load_config, SelectorConfig, ScrapeConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("incremental_scraper")


def analyze_existing_data(data_path: Path) -> Dict[str, any]:
    """Analyze existing tender data to find latest dates and tender numbers."""
    if not data_path.exists():
        log.warning(f"Data file {data_path} does not exist")
        return {
            'latest_published_date': None,
            'latest_deadline_date': None,
            'latest_date_window_to': None,
            'latest_scraped_at': None,
            'tender_numbers': set(),
            'total_records': 0
        }
    
    published_dates = []
    deadline_dates = []
    date_windows = []
    scraped_at_times = []
    tender_numbers = set()
    total_records = 0
    
    log.info(f"Analyzing existing data from {data_path}...")
    with open(data_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                record = json.loads(line)
                total_records += 1
                
                # Collect dates
                if record.get('published_date'):
                    published_dates.append(record['published_date'])
                if record.get('deadline_date'):
                    deadline_dates.append(record['deadline_date'])
                if record.get('date_window'):
                    date_windows.append(record['date_window'])
                if record.get('scraped_at'):
                    scraped_at_times.append(record['scraped_at'])
                
                # Collect tender numbers for duplicate detection
                tender_num = record.get('number', '').strip()
                if tender_num:
                    tender_numbers.add(tender_num.upper())
                    
            except json.JSONDecodeError as e:
                log.warning(f"Skipping invalid JSON at line {line_num}: {e}")
                continue
    
    result = {
        'latest_published_date': max(published_dates) if published_dates else None,
        'latest_deadline_date': max(deadline_dates) if deadline_dates else None,
        'latest_date_window_to': max(d['to'] for d in date_windows) if date_windows else None,
        'latest_scraped_at': max(scraped_at_times) if scraped_at_times else None,
        'tender_numbers': tender_numbers,
        'total_records': total_records
    }
    
    return result


def suggest_start_date(analysis: Dict) -> Tuple[str, str]:
    """
    Suggest start and end dates for scraping new tenders.
    
    Returns:
        (start_date, end_date) as YYYY-MM-DD strings
    """
    today = date.today()
    
    # Use latest published_date as base, or today - 7 days if no data
    if analysis['latest_published_date']:
        try:
            latest = datetime.strptime(analysis['latest_published_date'], '%Y-%m-%d').date()
            # Start from day after latest published date
            start_date = latest + timedelta(days=1)
        except ValueError:
            start_date = today - timedelta(days=7)
    else:
        # No existing data, start from 7 days ago
        start_date = today - timedelta(days=7)
    
    # End date: today + 30 days (to catch future tenders)
    end_date = today + timedelta(days=30)
    
    # Ensure start_date is not in the future
    if start_date > today:
        start_date = today - timedelta(days=1)
    
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


def print_analysis(analysis: Dict, suggested_dates: Tuple[str, str]):
    """Print analysis results and suggestions."""
    print("\n" + "=" * 60)
    print("EXISTING DATA ANALYSIS")
    print("=" * 60)
    print(f"Total records: {analysis['total_records']:,}")
    print(f"Unique tender numbers: {len(analysis['tender_numbers']):,}")
    print()
    
    if analysis['latest_published_date']:
        print(f"Latest published_date: {analysis['latest_published_date']}")
    else:
        print("No published_date found in existing data")
    
    if analysis['latest_deadline_date']:
        print(f"Latest deadline_date: {analysis['latest_deadline_date']}")
    
    if analysis['latest_date_window_to']:
        print(f"Latest date_window.to: {analysis['latest_date_window_to']}")
    
    if analysis['latest_scraped_at']:
        scraped_dt = datetime.fromtimestamp(analysis['latest_scraped_at'])
        print(f"Latest scraped_at: {scraped_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "=" * 60)
    print("SUGGESTED SCRAPING DATES")
    print("=" * 60)
    start_date, end_date = suggested_dates
    print(f"Start date: {start_date}")
    print(f"End date: {end_date}")
    print()
    print("To scrape new tenders, run:")
    print(f"  python3 incremental_scraper.py --scrape --date-from {start_date} --date-to {end_date}")
    print("=" * 60 + "\n")


async def test_for_new_tenders(
    config_path: Path,
    start_date: str,
    end_date: str,
    existing_numbers: Set[str]
) -> Dict:
    """
    Test if there are new tenders without scraping them.
    Returns count of potential new tenders.
    """
    log.info(f"Testing for new tenders from {start_date} to {end_date}...")
    
    # Build config for test
    class TestArgs:
        date_from = start_date
        date_to = end_date
        headless = True
        page_pause_ms = 500
        max_pages = 1  # Only check first page
        output = None
    
    args = TestArgs()
    scrape_cfg, selector_cfg = build_configs(config_path, args)
    
    # Use temporary output file
    test_output = Path("data/tenders_test.jsonl")
    if test_output.exists():
        test_output.unlink()
    scrape_cfg.output_path = test_output
    
    new_tenders_found = 0
    duplicate_tenders = 0
    
    try:
        async with TenderScraper(scrape_cfg, selector_cfg) as scraper:
            # Navigate and apply filters
            await scraper.page.goto(scrape_cfg.base_url, wait_until="networkidle")
            await scraper.apply_date_filters()
            await scraper.page.wait_for_selector(selector_cfg.search_button, state="visible", timeout=5000)
            await scraper.page.click(selector_cfg.search_button)
            await scraper.page.wait_for_timeout(2000)
            
            # Get results from first page only
            rows = await scraper.page.query_selector_all(selector_cfg.result_rows)
            log.info(f"Found {len(rows)} results on first page")
            
            for row in rows:
                try:
                    # Extract tender number
                    cells = await row.query_selector_all("td")
                    if cells:
                        cell_texts = []
                        for cell in cells:
                            text = await cell.inner_text()
                            cell_texts.append(text.strip())
                        
                        if cell_texts:
                            tender_num = cell_texts[0].strip().upper()
                            if tender_num:
                                if tender_num in existing_numbers:
                                    duplicate_tenders += 1
                                else:
                                    new_tenders_found += 1
                                    log.debug(f"New tender found: {tender_num}")
                except Exception as e:
                    log.debug(f"Error processing row: {e}")
                    continue
    
    except Exception as e:
        log.error(f"Error during test: {e}")
        return {'new_tenders': 0, 'duplicates': 0, 'error': str(e)}
    finally:
        # Clean up test file
        if test_output.exists():
            test_output.unlink()
    
    return {
        'new_tenders': new_tenders_found,
        'duplicates': duplicate_tenders,
        'total_checked': new_tenders_found + duplicate_tenders
    }


async def scrape_incremental(
    config_path: Path,
    start_date: str,
    end_date: str,
    existing_numbers: Set[str],
    output_path: Path,
    tender_type: Optional[str] = None,
    category_code: Optional[str] = None
) -> Dict:
    """
    Scrape new tenders, then filter out duplicates.
    Uses temporary file, then merges only new records.
    """
    log.info(f"Starting incremental scrape from {start_date} to {end_date}...")
    
    # Use temporary output file
    temp_output = output_path.with_suffix('.tmp.jsonl')
    if temp_output.exists():
        temp_output.unlink()
    
    class ScrapeArgs:
        date_from = start_date
        date_to = end_date
        headless = True  # Always run headless in production
        page_pause_ms = None
        max_pages = 0
        output = str(temp_output)
        # Add filter args
        nonlocal tender_type, category_code
        # dynamically add attributes since we're using a dummy class
    
    args = ScrapeArgs()
    # Manually attach optional filters if they exist, or set to None
    args.tender_type = tender_type
    args.category_code = category_code
    scrape_cfg, selector_cfg = build_configs(config_path, args)
    
    try:
        # Run the scraper to temp file
        async with TenderScraper(scrape_cfg, selector_cfg) as scraper:
            # Pass existing numbers to scraper for early filtering
            scraper.set_existing_tenders(existing_numbers)
            await scraper.run()
        
        # Now filter duplicates and merge
        new_tenders = 0
        skipped_duplicates = 0
        
        # Read temp file and filter duplicates
        new_records = []
        if temp_output.exists():
            with open(temp_output, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        tender_num = record.get('number', '').strip().upper()
                        
                        if tender_num and tender_num in existing_numbers:
                            skipped_duplicates += 1
                            log.debug(f"Skipping duplicate: {tender_num}")
                        else:
                            new_records.append(record)
                            if tender_num:
                                existing_numbers.add(tender_num)
                            new_tenders += 1
                    except json.JSONDecodeError:
                        continue
            
            # Append new records to main file
            if new_records:
                with open(output_path, 'a', encoding='utf-8') as f:
                    for record in new_records:
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')
                log.info(f"Added {len(new_records)} new records to {output_path}")
            
            # Clean up temp file
            temp_output.unlink()
        
    except Exception as e:
        log.error(f"Error during scraping: {e}", exc_info=True)
        # Clean up temp file on error
        if temp_output.exists():
            temp_output.unlink()
        return {
            'new_tenders': new_tenders,
            'skipped_duplicates': skipped_duplicates,
            'error': str(e)
        }
    
    return {
        'new_tenders': new_tenders,
        'skipped_duplicates': skipped_duplicates
    }


def split_date_range(start_date: str, end_date: str, num_chunks: int) -> list[tuple[str, str]]:
    """Split a date range into equal chunks."""
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    total_days = (end - start).days + 1
    if total_days <= 0:
        return []
        
    if num_chunks <= 1 or total_days < num_chunks:
        return [(start_date, end_date)]
    
    chunk_size = total_days // num_chunks
    remainder = total_days % num_chunks
    
    ranges = []
    current_start = start
    
    for i in range(num_chunks):
        # Distribute remainder days across first few chunks
        days_in_chunk = chunk_size + (1 if i < remainder else 0)
        current_end = current_start + timedelta(days=days_in_chunk - 1)
        
        ranges.append((
            current_start.strftime("%Y-%m-%d"),
            current_end.strftime("%Y-%m-%d")
        ))
        
        current_start = current_end + timedelta(days=1)
        
    return ranges


async def scrape_parallel(
    config_path: Path,
    start_date: str,
    end_date: str,
    existing_numbers: Set[str],
    output_path: Path,
    concurrency: int,
    tender_type: Optional[str] = None,
    category_code: Optional[str] = None
) -> Dict:
    """
    Run multiple scrapers in parallel by splitting the date range.
    """
    log.info(f"Starting parallel scrape with {concurrency} workers...")
    
    # Split date range
    date_ranges = split_date_range(start_date, end_date, concurrency)
    log.info(f"Split date range into {len(date_ranges)} chunks: {date_ranges}")
    
    if len(date_ranges) == 1:
        # Fallback to sequential if only one chunk needed
        return await scrape_incremental(
            config_path, 
            start_date, 
            end_date, 
            existing_numbers, 
            output_path,
            tender_type,
            category_code
        )
    
    tasks = []
    temp_files = []
    
    # Create tasks for each chunk
    for i, (chunk_start, chunk_end) in enumerate(date_ranges):
        # Create unique temp file for this worker
        worker_output = output_path.with_suffix(f'.worker_{i}.jsonl')
        temp_files.append(worker_output)
        
        # We reuse scrape_incremental logic but with a specific chunk and output file
        # Note: scrape_incremental handles its own temp file logic too, but that's fine
        # We just need to make sure we merge everything at the end
        
        # Actually, scrape_incremental does a full run and then merges to output_path
        # If we pass worker_output as output_path, it will append to it (creating it if needed)
        # But scrape_incremental also filters duplicates based on existing_numbers
        # This is exactly what we want!
        
        tasks.append(scrape_incremental(
            config_path, 
            chunk_start, 
            chunk_end, 
            existing_numbers, # Pass shared set (read-only effectively)
            worker_output,
            tender_type,
            category_code
        ))
    
    # Run all tasks
    results = await asyncio.gather(*tasks)
    
    # Aggregate results
    total_new = 0
    total_skipped = 0
    errors = []
    
    for res in results:
        total_new += res.get('new_tenders', 0)
        total_skipped += res.get('skipped_duplicates', 0)
        if res.get('error'):
            errors.append(res['error'])
            
    # Merge all worker output files to main output
    log.info("Merging worker output files...")
    merged_count = 0
    
    try:
        with open(output_path, 'a', encoding='utf-8') as main_f:
            for temp_file in temp_files:
                if temp_file.exists():
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            main_f.write(line)
                            merged_count += 1
                    # Clean up
                    temp_file.unlink()
                    
        log.info(f"Merged {merged_count} records from workers")
        
    except Exception as e:
        log.error(f"Error merging files: {e}")
        errors.append(f"Merge error: {e}")
        
    return {
        'new_tenders': total_new,
        'skipped_duplicates': total_skipped,
        'error': "; ".join(errors) if errors else None
    }


def main():
    parser = argparse.ArgumentParser(
        description="Incremental scraper for new tenders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check what date to start from
  python3 incremental_scraper.py --check
  
  # Test if there are new tenders (dry-run, first page only)
  python3 incremental_scraper.py --test --days 7
  
  # Scrape new tenders using suggested dates
  python3 incremental_scraper.py --scrape
  
  # Scrape from specific date
  python3 incremental_scraper.py --scrape --date-from 2025-11-29 --date-to 2025-12-31
        """
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Analyze existing data and suggest start date (default action)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test if there are new tenders without scraping (checks first page only)'
    )
    parser.add_argument(
        '--scrape',
        action='store_true',
        help='Scrape new tenders (skips duplicates)'
    )
    parser.add_argument(
        '--date-from',
        type=str,
        help='Start date (YYYY-MM-DD). If not provided, will use suggested date.'
    )
    parser.add_argument(
        '--date-to',
        type=str,
        help='End date (YYYY-MM-DD). If not provided, will use today + 30 days.'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to look back for test (default: 7)'
    )
    parser.add_argument(
        '--data-file',
        type=Path,
        default=Path('main_scrapper/data/tenders.jsonl'),
        help='Path to existing tender data file (default: main_scrapper/data/tenders.jsonl)'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('main_scrapper/config/selectors.yaml'),
        help='Path to scraper config (default: main_scrapper/config/selectors.yaml)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file for scraped data (default: same as --data-file)'
    )
    
    parser.add_argument(
        '--concurrency',
        type=int,
        default=1,
        help='Number of parallel workers (default: 1)'
    )
    parser.add_argument("--tender-type", help="Filter by tender type (e.g., CON, NAT)")
    parser.add_argument("--category-code", help="Filter by category code (e.g., 60100000)")

    
    args = parser.parse_args()
    
    # Default action is --check if nothing specified
    if not (args.check or args.test or args.scrape):
        args.check = True
    
    # Analyze existing data
    analysis = analyze_existing_data(args.data_file)
    suggested_start, suggested_end = suggest_start_date(analysis)
    
    # Determine dates to use
    start_date = args.date_from or suggested_start
    if args.date_to:
        end_date = args.date_to
    elif args.test:
        # For test, use days parameter
        test_start = (datetime.strptime(start_date, '%Y-%m-%d').date() - timedelta(days=args.days)).strftime('%Y-%m-%d')
        end_date = (datetime.strptime(start_date, '%Y-%m-%d').date() + timedelta(days=args.days)).strftime('%Y-%m-%d')
        start_date = test_start
    else:
        end_date = suggested_end
    
    # Print analysis
    if args.check:
        print_analysis(analysis, (start_date, end_date))
        return 0
    
    # Test mode
    if args.test:
        print(f"\n🧪 Testing for new tenders from {start_date} to {end_date}...")
        print(f"   (Checking first page only)\n")
        
        result = asyncio.run(
            test_for_new_tenders(
                args.config,
                start_date,
                end_date,
                analysis['tender_numbers']
            )
        )
        
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"New tenders found: {result.get('new_tenders', 0)}")
        print(f"Duplicate tenders: {result.get('duplicates', 0)}")
        print(f"Total checked: {result.get('total_checked', 0)}")
        if result.get('error'):
            print(f"Error: {result['error']}")
        print("=" * 60 + "\n")
        
        if result.get('new_tenders', 0) > 0:
            print(f"✅ Found {result['new_tenders']} new tenders! Run with --scrape to collect them.")
        else:
            print("ℹ️  No new tenders found on first page.")
        
        return 0
    
    # Scrape mode
    if args.scrape:
        output_path = args.output or args.data_file
        
        print(f"\n🚀 Starting incremental scrape...")
        print(f"   Date range: {start_date} to {end_date}")
        print(f"   Output: {output_path}")
        print(f"   Existing tenders: {len(analysis['tender_numbers']):,}")
        if args.concurrency > 1:
            print(f"   Concurrency: {args.concurrency} workers")
        print()
        
        if args.concurrency > 1:
            result = asyncio.run(
                scrape_parallel(
                    args.config,
                    start_date,
                    end_date,
                    analysis['tender_numbers'].copy(),
                    output_path,
                    args.concurrency,
                    args.tender_type,
                    args.category_code
                )
            )
        else:
            result = asyncio.run(
                scrape_incremental(
                    args.config,
                    start_date,
                    end_date,
                    analysis['tender_numbers'].copy(),
                    output_path,
                    args.tender_type,
                    args.category_code
                )
            )
        
        print("\n" + "=" * 60)
        print("SCRAPING RESULTS")
        print("=" * 60)
        print(f"New tenders scraped: {result.get('new_tenders', 0)}")
        print(f"Duplicates skipped: {result.get('skipped_duplicates', 0)}")
        if result.get('error'):
            print(f"Error: {result['error']}")
        print("=" * 60 + "\n")
        
        if result.get('new_tenders', 0) > 0:
            print(f"✅ Successfully scraped {result['new_tenders']} new tenders!")
        else:
            print("ℹ️  No new tenders found.")
        
        return 0
    
    return 0


if __name__ == "__main__":
    exit(main())

