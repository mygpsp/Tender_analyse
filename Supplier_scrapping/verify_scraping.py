#!/usr/bin/env python3
"""
Scraping Verification Tool

Analyzes the scraped suppliers.jsonl file to:
1. Count suppliers by registration date
2. Identify potential gaps or issues
3. Provide statistics for verification

Future enhancement: Compare with website counts
"""

import json
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_suppliers(file_path: Path) -> List[dict]:
    """Load suppliers from JSONL file."""
    suppliers = []
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return suppliers
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                supplier = json.loads(line)
                suppliers.append(supplier)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON on line {line_num}: {e}")
    
    logger.info(f"Loaded {len(suppliers)} suppliers from file")
    return suppliers


def analyze_by_date(suppliers: List[dict]) -> Dict[str, int]:
    """Count suppliers by registration date."""
    date_counts = defaultdict(int)
    no_date_count = 0
    
    for supplier in suppliers:
        reg_date = supplier.get('registration_date')
        if reg_date:
            date_counts[reg_date] += 1
        else:
            no_date_count += 1
    
    if no_date_count > 0:
        logger.warning(f"Found {no_date_count} suppliers without registration date")
    
    return dict(sorted(date_counts.items()))


def analyze_by_year(date_counts: Dict[str, int]) -> Dict[str, int]:
    """Group counts by year."""
    year_counts = defaultdict(int)
    
    for date_str, count in date_counts.items():
        try:
            # Parse DD.MM.YYYY format
            parts = date_str.split('.')
            if len(parts) == 3:
                year = parts[2]
                year_counts[year] += count
        except Exception as e:
            logger.warning(f"Could not parse date {date_str}: {e}")
    
    return dict(sorted(year_counts.items()))


def print_statistics(suppliers: List[dict], date_counts: Dict[str, int], year_counts: Dict[str, int]):
    """Print comprehensive statistics."""
    print("\n" + "="*80)
    print("SCRAPING VERIFICATION REPORT")
    print("="*80)
    
    print(f"\nTotal Suppliers: {len(suppliers)}")
    print(f"Unique Registration Dates: {len(date_counts)}")
    
    print("\n--- Suppliers by Year ---")
    for year, count in year_counts.items():
        print(f"{year}: {count:,} suppliers")
    
    print("\n--- Top 10 Dates by Count ---")
    sorted_dates = sorted(date_counts.items(), key=lambda x: x[1], reverse=True)
    for date, count in sorted_dates[:10]:
        print(f"{date}: {count} suppliers")
    
    print("\n--- Dates with Only 1 Supplier (Potential Issues) ---")
    single_supplier_dates = [(date, count) for date, count in date_counts.items() if count == 1]
    if single_supplier_dates:
        print(f"Found {len(single_supplier_dates)} dates with only 1 supplier")
        for date, count in single_supplier_dates[:20]:  # Show first 20
            print(f"  {date}")
        if len(single_supplier_dates) > 20:
            print(f"  ... and {len(single_supplier_dates) - 20} more")
    else:
        print("None found")
    
    print("\n--- Date Range ---")
    if date_counts:
        dates = list(date_counts.keys())
        print(f"Earliest: {dates[0]}")
        print(f"Latest: {dates[-1]}")
    
    print("\n" + "="*80)


def export_to_csv(date_counts: Dict[str, int], output_path: Path):
    """Export date counts to CSV for analysis."""
    import csv
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Registration Date', 'Count'])
        for date, count in date_counts.items():
            writer.writerow([date, count])
    
    logger.info(f"Exported date counts to {output_path}")


def main():
    # Path to suppliers file
    data_path = Path(__file__).parent / "data" / "suppliers.jsonl"
    
    # Load and analyze
    suppliers = load_suppliers(data_path)
    
    if not suppliers:
        logger.error("No suppliers loaded. Exiting.")
        return
    
    date_counts = analyze_by_date(suppliers)
    year_counts = analyze_by_year(date_counts)
    
    # Print statistics
    print_statistics(suppliers, date_counts, year_counts)
    
    # Export to CSV
    csv_path = Path(__file__).parent / "data" / "supplier_counts_by_date.csv"
    export_to_csv(date_counts, csv_path)
    
    print(f"\nDetailed counts exported to: {csv_path}")
    print("\nNext Steps:")
    print("1. Review the date counts for anomalies")
    print("2. Check the website for total expected suppliers")
    print("3. Compare year totals with website statistics")
    print("4. Identify date ranges that need re-scraping")


if __name__ == "__main__":
    main()
