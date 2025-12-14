#!/usr/bin/env python3
"""
Deduplicate detailed_tenders.jsonl file.
Keeps the best record for each tender number.
"""
import json
from pathlib import Path
from typing import Dict, Any

def is_valid_record(record: Dict[str, Any]) -> bool:
    """Check if record has valid data."""
    basic_info = record.get("basic_info", {})
    buyer = basic_info.get("buyer", "")
    
    # Valid buyer should not be a search hint
    if buyer and (buyer.startswith("(") or len(buyer) < 5):
        return False
    
    # Should have basic_info with at least buyer or category
    if not basic_info:
        return False
    
    return bool(basic_info.get("buyer") or basic_info.get("category"))

def choose_best_record(records: list) -> Dict[str, Any]:
    """Choose the best record from duplicates."""
    # Filter to valid records
    valid = [r for r in records if is_valid_record(r)]
    
    if not valid:
        # If none are valid, return the most recent
        return max(records, key=lambda r: r.get("scraped_at", 0))
    
    # Among valid records, prefer one with amount
    with_amount = [r for r in valid if r.get("basic_info", {}).get("amount")]
    if with_amount:
        return max(with_amount, key=lambda r: r.get("scraped_at", 0))
    
    # Otherwise, return most recent valid
    return max(valid, key=lambda r: r.get("scraped_at", 0))

def deduplicate_file(input_path: Path, output_path: Path):
    """Deduplicate detailed tenders file."""
    records_by_number: Dict[str, list] = {}
    
    # Load all records
    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                record = json.loads(line.strip())
                tender_number = record.get("tender_number")
                
                if not tender_number:
                    print(f"Line {line_num}: Skipping - no tender_number")
                    continue
                
                if tender_number not in records_by_number:
                    records_by_number[tender_number] = []
                
                records_by_number[tender_number].append(record)
                
            except Exception as e:
                print(f"Line {line_num}: Error - {e}")
                continue
    
    # Deduplicate
    unique_records = []
    for tender_number, records in records_by_number.items():
        if len(records) > 1:
            print(f"{tender_number}: {len(records)} duplicates, keeping best")
        best = choose_best_record(records)
        unique_records.append(best)
    
    # Write deduplicated records
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in unique_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Deduplicated: {len(unique_records)} unique records")
    print(f"✅ Saved to {output_path}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/detailed_tenders.jsonl')
    parser.add_argument('--output', default='data/detailed_tenders.jsonl')
    args = parser.parse_args()
    
    deduplicate_file(Path(args.input), Path(args.output))

