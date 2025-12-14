#!/usr/bin/env python3
"""
Filter CON tenders with category code 60100000 from main data.

This script reads the main tenders.jsonl file, filters for CON tenders
with the specified category code, and saves the results to a new file.
"""
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter


def filter_con_tenders(
    input_file: Path,
    category_code: str = "60100000",
    output_file: Path = None
) -> List[Dict[str, Any]]:
    """
    Filter CON tenders with specified category code.
    
    Args:
        input_file: Path to tenders.jsonl file
        category_code: Category code to filter (default: 60100000)
        output_file: Path to save filtered tenders (optional)
        
    Returns:
        List of filtered tender dictionaries
    """
    filtered_tenders = []
    
    print(f"Reading tenders from: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                tender = json.loads(line)
                
                # Filter by tender_type == "CON" AND category_code == specified code
                if (tender.get('tender_type') == 'CON' and 
                    tender.get('category_code') == category_code):
                    filtered_tenders.append(tender)
                    
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line {line_num}: {e}")
                continue
    
    print(f"Found {len(filtered_tenders)} CON tenders with category {category_code}")
    
    # Save to output file if specified
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for tender in filtered_tenders:
                f.write(json.dumps(tender, ensure_ascii=False) + '\n')
        print(f"Saved filtered tenders to: {output_file}")
    
    return filtered_tenders


def print_statistics(tenders: List[Dict[str, Any]]):
    """Print statistics about filtered tenders."""
    if not tenders:
        print("No tenders to analyze")
        return
    
    print("\n" + "=" * 60)
    print("CON TENDER STATISTICS")
    print("=" * 60)
    
    # Total count
    print(f"Total CON tenders: {len(tenders)}")
    
    # Date range
    dates = [t.get('published_date') for t in tenders if t.get('published_date')]
    if dates:
        print(f"Date range: {min(dates)} to {max(dates)}")
    
    # Status distribution
    statuses = Counter(t.get('status', 'Unknown') for t in tenders)
    print(f"\nStatus distribution:")
    for status, count in statuses.most_common():
        print(f"  {status}: {count}")
    
    # Amount statistics
    amounts = [t.get('amount') for t in tenders if t.get('amount')]
    if amounts:
        print(f"\nAmount statistics:")
        print(f"  Total: {sum(amounts):,.2f} GEL")
        print(f"  Average: {sum(amounts)/len(amounts):,.2f} GEL")
        print(f"  Min: {min(amounts):,.2f} GEL")
        print(f"  Max: {max(amounts):,.2f} GEL")
    
    # Buyer distribution (top 10)
    buyers = Counter(t.get('buyer', 'Unknown') for t in tenders)
    print(f"\nTop 10 buyers:")
    for buyer, count in buyers.most_common(10):
        print(f"  {buyer[:50]}: {count}")
    
    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Filter CON tenders with category code 60100000'
    )
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('main_scrapper/data/tenders.jsonl'),
        help='Input tenders.jsonl file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('con_analysis/data/con_tenders_60100000.jsonl'),
        help='Output file for filtered tenders'
    )
    parser.add_argument(
        '--category',
        type=str,
        default='60100000',
        help='Category code to filter (default: 60100000)'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Print statistics only, do not save output'
    )
    
    args = parser.parse_args()
    
    # Filter tenders
    output_file = None if args.check else args.output
    tenders = filter_con_tenders(args.input, args.category, output_file)
    
    # Print statistics
    print_statistics(tenders)


if __name__ == '__main__':
    main()
