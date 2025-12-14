#!/usr/bin/env python3
"""
Check which CON tenders are missing detailed data.

This script compares the filtered CON tenders against the detailed_tenders.jsonl
file to identify which tenders need to be scraped for detailed information.
"""
import json
import argparse
from pathlib import Path
from typing import Set, List


def load_tender_numbers(file_path: Path, number_field: str = 'number') -> Set[str]:
    """
    Load tender numbers from a JSONL file.
    
    Args:
        file_path: Path to JSONL file
        number_field: Field name containing tender number
        
    Returns:
        Set of tender numbers
    """
    numbers = set()
    
    if not file_path.exists():
        print(f"Warning: File not found: {file_path}")
        return numbers
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                number = data.get(number_field) or data.get('procurement_number')
                if number:
                    numbers.add(number)
            except json.JSONDecodeError:
                continue
    
    return numbers


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Check which CON tenders are missing detailed data'
    )
    parser.add_argument(
        '--con-tenders',
        type=Path,
        default=Path('con_analysis/data/con_tenders_60100000.jsonl'),
        help='Filtered CON tenders file'
    )
    parser.add_argument(
        '--detailed-tenders',
        type=Path,
        default=Path('data/detailed_tenders.jsonl'),
        help='Detailed tenders file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('con_analysis/data/missing_detailed_tenders.txt'),
        help='Output file for missing tender numbers'
    )
    
    args = parser.parse_args()
    
    # Load tender numbers
    print(f"Loading CON tender numbers from: {args.con_tenders}")
    con_numbers = load_tender_numbers(args.con_tenders, 'number')
    print(f"Found {len(con_numbers)} CON tenders")
    
    print(f"\nLoading detailed tender numbers from: {args.detailed_tenders}")
    detailed_numbers = load_tender_numbers(args.detailed_tenders, 'procurement_number')
    print(f"Found {len(detailed_numbers)} detailed tenders")
    
    # Find missing
    missing = con_numbers - detailed_numbers
    print(f"\nMissing detailed data for {len(missing)} CON tenders")
    
    if missing:
        # Save to output file
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            for number in sorted(missing):
                f.write(number + '\n')
        print(f"Saved missing tender numbers to: {args.output}")
        
        # Print first 10
        print(f"\nFirst 10 missing tenders:")
        for number in sorted(missing)[:10]:
            print(f"  {number}")
    else:
        print("All CON tenders have detailed data!")
    
    # Coverage statistics
    coverage = (len(con_numbers) - len(missing)) / len(con_numbers) * 100 if con_numbers else 0
    print(f"\nCoverage: {coverage:.1f}% ({len(con_numbers) - len(missing)}/{len(con_numbers)})")


if __name__ == '__main__':
    main()
