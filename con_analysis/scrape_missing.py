#!/usr/bin/env python3
"""
Scrape missing detailed tender data for CON tenders.

This script uses the existing detailed scraper to fetch detailed information
for CON tenders that don't have detailed data yet.
"""
import asyncio
import argparse
from pathlib import Path
import sys
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from detailed_scraper.detail_scraper import (
    DetailedTenderScraper,
    DetailScraperConfig,
    DetailSelectors,
    JsonLinesWriter
)


async def scrape_missing_con_tenders(
    missing_file: Path,
    output_file: Path,
    concurrency: int = 5,
    max_tenders: int = None
):
    """
    Scrape missing CON tenders.
    
    Args:
        missing_file: Path to file with missing tender numbers
        output_file: Path to output detailed tenders file
        concurrency: Number of concurrent scraping tasks
        max_tenders: Maximum number of tenders to scrape (None = all)
    """
    # Read missing tender numbers
    if not missing_file.exists():
        print(f"Error: Missing file not found: {missing_file}")
        return
    
    with open(missing_file, 'r', encoding='utf-8') as f:
        tender_numbers = [line.strip() for line in f if line.strip()]
    
    if max_tenders:
        tender_numbers = tender_numbers[:max_tenders]
    
    print(f"Found {len(tender_numbers)} CON tenders to scrape")
    
    # Create config
    config = DetailScraperConfig(
        base_url="https://tenders.procurement.gov.ge/public/",
        headless=True,
        page_pause_ms=1000,
        output_path=output_file,
        max_retries=3
    )
    
    # Create selectors
    selectors = DetailSelectors(
        tender_number_input='input[name="search[number]"]',
        search_button='button[type="submit"]',
        detail_panel='div.modal-content',
        detail_title='h4.modal-title',
        detail_content='div.modal-body',
        close_button='button.close'
    )
    
    # Create writer
    writer = JsonLinesWriter(output_file)
    
    # Initialize scraper
    scraper = DetailedTenderScraper(
        config=config,
        selectors=selectors,
        writer=writer
    )
    
    # Prepare tender data (with tender IDs from main data)
    tender_data = []
    main_data_path = Path('main_scrapper/data/tenders.jsonl')
    
    print("Loading tender IDs from main data...")
    tender_id_map = {}
    with open(main_data_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                tender = json.loads(line)
                number = tender.get('number')
                if number in tender_numbers:
                    tender_id_map[number] = {
                        'tender_id': tender.get('tender_id'),
                        'detail_url': tender.get('detail_url')
                    }
            except json.JSONDecodeError:
                continue
    
    for number in tender_numbers:
        info = tender_id_map.get(number, {})
        tender_data.append({
            'number': number,
            'tender_id': info.get('tender_id'),
            'detail_url': info.get('detail_url')
        })
    
    print(f"Starting scraper with concurrency={concurrency}")
    print(f"Output file: {output_file}")
    
    # Scrape tenders
    async with scraper:
        await scraper.scrape_multiple_parallel(
            tender_data=tender_data,
            concurrency=concurrency,
            force=False  # Don't overwrite existing data
        )
    
    print(f"\nScraping complete!")
    print(f"Results saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scrape missing detailed data for CON tenders'
    )
    parser.add_argument(
        '--missing-file',
        type=Path,
        default=Path('con_analysis/data/missing_detailed_tenders.txt'),
        help='File with missing tender numbers'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('data/detailed_tenders.jsonl'),
        help='Output file for detailed tenders'
    )
    parser.add_argument(
        '--concurrency',
        type=int,
        default=5,
        help='Number of concurrent scraping tasks (default: 5)'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=None,
        help='Maximum number of tenders to scrape (default: all)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: scrape only first 5 tenders'
    )
    
    args = parser.parse_args()
    
    # Test mode
    if args.test:
        args.max = 5
        print("TEST MODE: Scraping only first 5 tenders\n")
    
    # Run scraper
    asyncio.run(scrape_missing_con_tenders(
        args.missing_file,
        args.output,
        args.concurrency,
        args.max
    ))


if __name__ == '__main__':
    main()
