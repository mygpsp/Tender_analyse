#!/usr/bin/env python3
"""
Compare CON tenders in con_filter.jsonl with detailed_tenders.jsonl
Shows which tenders have been scraped and which are missing.
"""
import json
from pathlib import Path
from typing import Set, Dict, Any

def extract_number_suffix(tender_num: str) -> str:
    """Extract the numeric suffix from tender number (e.g., CON220000044 -> 220000044)."""
    import re
    match = re.search(r'(\d{9,})', tender_num)
    return match.group(1) if match else tender_num

def load_tender_numbers(file_path: Path, number_field: str) -> Set[str]:
    """Load tender numbers from a JSONL file."""
    numbers = set()
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path}")
        return numbers
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    num = data.get(number_field, '').strip()
                    if num:
                        # Store the numeric suffix for comparison
                        numbers.add(extract_number_suffix(num))
                except json.JSONDecodeError:
                    continue
    
    return numbers

def main():
    # File paths
    con_filter_file = Path('main_scrapper/data/con_filter.jsonl')
    detailed_file = Path('main_scrapper/data/con_detailed_tenders.jsonl')
    
    print("=" * 70)
    print("CON TENDERS DETAILED SCRAPING STATUS")
    print("=" * 70)
    print()
    
    # Load CON tender numbers
    print("📂 Loading CON tenders from con_filter.jsonl...")
    con_tenders = load_tender_numbers(con_filter_file, 'number')
    print(f"   Found {len(con_tenders)} CON tenders")
    print()
    
    # Load detailed tender numbers
    print("📂 Loading detailed tenders from detailed_tenders.jsonl...")
    detailed_tenders = load_tender_numbers(detailed_file, 'procurement_number')
    print(f"   Found {len(detailed_tenders)} detailed tenders (all types)")
    print()
    
    # Calculate overlap
    scraped_con = con_tenders & detailed_tenders
    missing_con = con_tenders - detailed_tenders
    
    # Display results
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"✅ CON tenders with detailed data:  {len(scraped_con):4d} / {len(con_tenders)} ({len(scraped_con)/len(con_tenders)*100:.1f}%)")
    print(f"⏳ CON tenders missing details:     {len(missing_con):4d} / {len(con_tenders)} ({len(missing_con)/len(con_tenders)*100:.1f}%)")
    print("=" * 70)
    print()
    
    # Show missing tenders
    if missing_con:
        print(f"Missing CON tenders ({len(missing_con)} total):")
        print("-" * 70)
        missing_list = sorted(list(missing_con))
        
        # Show first 20
        for i, tender_num in enumerate(missing_list[:20], 1):
            print(f"  {i:3d}. {tender_num}")
        
        if len(missing_con) > 20:
            print(f"  ... and {len(missing_con) - 20} more")
        
        print()
        
        # Save missing to file
        missing_file = Path('missing_con_tenders.txt')
        with open(missing_file, 'w') as f:
            for tender_num in missing_list:
                f.write(f"{tender_num}\n")
        print(f"💾 Full list saved to: {missing_file}")
        print()
    else:
        print("🎉 All CON tenders have detailed data!")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total CON tenders:           {len(con_tenders):5d}")
    print(f"Already scraped (detailed):  {len(scraped_con):5d}")
    print(f"Still need scraping:         {len(missing_con):5d}")
    print("=" * 70)

if __name__ == "__main__":
    main()
