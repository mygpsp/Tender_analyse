#!/usr/bin/env python3
"""
Split detailed_tenders.jsonl by tender type
Creates separate files for each tender type (CON, NAT, GEO, etc.)
"""
import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List

def extract_tender_type(procurement_number: str) -> str:
    """Extract tender type from procurement number (e.g., CON250000123 -> CON)."""
    if not procurement_number:
        return 'UNKNOWN'
    
    # Extract alphabetic prefix (usually 3 letters)
    tender_type = ''.join([c for c in procurement_number if c.isalpha()])
    
    # Take first 3 characters as type
    return tender_type[:3] if tender_type else 'UNKNOWN'

def split_detailed_tenders():
    """Split detailed tenders by type into separate files."""
    
    input_file = Path('main_scrapper/data/detailed_tenders.jsonl')
    output_dir = Path('main_scrapper/data')
    
    print("=" * 70)
    print("SPLITTING DETAILED TENDERS BY TYPE")
    print("=" * 70)
    print()
    
    # Step 1: Read and categorize all tenders
    print("📂 Step 1: Reading detailed tenders...")
    tenders_by_type: Dict[str, List[str]] = defaultdict(list)
    type_counts = Counter()
    total = 0
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                total += 1
                try:
                    data = json.loads(line)
                    proc_num = data.get('procurement_number', '')
                    tender_type = extract_tender_type(proc_num)
                    
                    tenders_by_type[tender_type].append(line)
                    type_counts[tender_type] += 1
                    
                except json.JSONDecodeError:
                    continue
    
    print(f"   Total tenders: {total}")
    print(f"   Tender types found: {len(type_counts)}")
    print()
    
    # Step 2: Show distribution
    print("📊 Step 2: Tender type distribution:")
    print("-" * 70)
    for tender_type, count in type_counts.most_common():
        pct = (count / total * 100) if total > 0 else 0
        print(f"   {tender_type:10s}: {count:5d} ({pct:5.1f}%)")
    print()
    
    # Step 3: Write separate files
    print("💾 Step 3: Writing separate files...")
    files_created = []
    
    for tender_type, lines in tenders_by_type.items():
        # Create filename: con_detailed_tenders.jsonl, nat_detailed_tenders.jsonl, etc.
        output_file = output_dir / f"{tender_type.lower()}_detailed_tenders.jsonl"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line)
        
        files_created.append((tender_type, output_file, len(lines)))
        print(f"   ✅ {output_file.name}: {len(lines)} tenders")
    
    print()
    
    # Step 4: Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tenders processed: {total}")
    print(f"Files created: {len(files_created)}")
    print()
    print("Created files:")
    for tender_type, file_path, count in sorted(files_created, key=lambda x: -x[2]):
        print(f"  - {file_path.name} ({count} tenders)")
    print("=" * 70)
    
    return files_created

if __name__ == "__main__":
    split_detailed_tenders()
