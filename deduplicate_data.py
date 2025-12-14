#!/usr/bin/env python3
"""
Script to deduplicate tender data in JSONL files.

This script removes duplicate tender records based on all fields (not just tender number).
When duplicates are found, it keeps the most recent or most complete record.
Metadata fields (scraped_at, date_window, extraction_method) are excluded from comparison.

Usage:
    python3 deduplicate_data.py [input_file] [output_file]

If output_file is not specified, creates a backup and overwrites input_file.
"""

import argparse
import json
import re
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def extract_tender_number(record: Dict[str, Any]) -> Optional[str]:
    """Extract tender number from record (e.g., GEO250000579)."""
    # Try number field first
    number = record.get("number", "").strip()
    if number:
        match = re.search(r'([A-Z]{2,4}\d{9,})', number)
        if match:
            return match.group(1)
    
    # Try all_cells field
    all_cells = record.get("all_cells", "")
    if all_cells:
        match = re.search(r'([A-Z]{2,4}\d{9,})', all_cells)
        if match:
            return match.group(1)
    
    return None


def normalize_value(value: Any) -> Any:
    """Normalize a value for consistent comparison."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        # Sort keys for consistent ordering
        return {k: normalize_value(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    return value


def get_record_signature(record: Dict[str, Any], exclude_metadata: bool = True) -> str:
    """
    Generate a deterministic hash/signature from all fields of a record.
    
    Args:
        record: The tender record dictionary
        exclude_metadata: If True, exclude scraped_at, date_window, extraction_method
        
    Returns:
        A hash string representing the record's content
    """
    # Create a copy of the record for normalization
    normalized = {}
    
    # Fields to exclude from comparison (metadata)
    exclude_fields = set()
    if exclude_metadata:
        exclude_fields = {"scraped_at", "date_window", "extraction_method"}
    
    # Normalize all fields except excluded ones
    for key, value in record.items():
        if key not in exclude_fields:
            normalized[key] = normalize_value(value)
    
    # Create a deterministic JSON string (sorted keys)
    json_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    
    # Generate hash
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def is_valid_record(record: Dict[str, Any]) -> bool:
    """Check if a record is valid (not a header or invalid row)."""
    number = record.get("number", "").strip()
    buyer = record.get("buyer", "").strip()
    
    # Skip if number contains navigation elements
    if "მომხმარებლები" in number or "CMR" in number or "CON" in number:
        return False
    
    # Skip if it's clearly a datepicker element (check in all_cells as fallback)
    if "ui-datepicker" in record.get("all_cells", ""):
        return False
    
    # Skip if number is just digits (likely a calendar day)
    if number.isdigit() and len(number) <= 2:
        return False
    
    # Skip empty records
    if not number and not buyer:
        return False
    
    return True


def deduplicate_file(input_path: Path, output_path: Path) -> tuple[int, int, int]:
    """
    Deduplicate tender records in a JSONL file based on all fields.
    
    Returns:
        (total_records, unique_records, duplicates_removed)
    """
    seen = {}  # record_signature -> best_record
    total_records = 0
    valid_records = 0
    
    print(f"Reading {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            total_records += 1
            try:
                record = json.loads(line)
                
                # Filter out invalid records
                if not is_valid_record(record):
                    continue
                
                valid_records += 1
                
                # Generate signature from all fields (excluding metadata)
                signature = get_record_signature(record, exclude_metadata=True)
                
                if signature not in seen:
                    # First time seeing this exact record
                    seen[signature] = record
                else:
                    # Duplicate found - decide which to keep
                    existing = seen[signature]
                    
                    # Prefer record with more recent scraped_at
                    existing_time = existing.get("scraped_at", 0)
                    new_time = record.get("scraped_at", 0)
                    
                    if new_time > existing_time:
                        seen[signature] = record
                    elif new_time == existing_time:
                        # If same time, prefer record with more complete data
                        existing_cells_len = len(existing.get("all_cells", ""))
                        new_cells_len = len(record.get("all_cells", ""))
                        if new_cells_len > existing_cells_len:
                            seen[signature] = record
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON at line {line_num}: {e}")
                continue
    
    # Write deduplicated records
    print(f"Writing {len(seen)} unique records to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        for record in seen.values():
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    duplicates_removed = valid_records - len(seen)
    return total_records, len(seen), duplicates_removed


def main():
    parser = argparse.ArgumentParser(
        description="Deduplicate tender data in JSONL files"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Input JSONL file path"
    )
    parser.add_argument(
        "output_file",
        type=Path,
        nargs="?",
        help="Output JSONL file path (default: overwrites input with backup)"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup of input file"
    )
    
    args = parser.parse_args()
    
    input_path = args.input_file
    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist")
        return 1
    
    # Determine output path
    if args.output_file:
        output_path = args.output_file
    else:
        # Create backup and overwrite input
        if not args.no_backup:
            backup_path = input_path.with_suffix(
                f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            )
            print(f"Creating backup: {backup_path}")
            shutil.copy2(input_path, backup_path)
        output_path = input_path
    
    # Deduplicate
    total, unique, duplicates = deduplicate_file(input_path, output_path)
    
    print(f"\nSummary:")
    print(f"  Total records read: {total}")
    print(f"  Valid records: {total - (total - unique - duplicates)}")
    print(f"  Unique records: {unique}")
    print(f"  Duplicates removed: {duplicates}")
    print(f"  Output file: {output_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())

