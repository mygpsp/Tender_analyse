#!/usr/bin/env python3
"""
Helper script to prepare tender data for detailed scraping.

Extracts tender numbers and IDs from main data file and creates
a list ready for detailed scraping.
"""
import argparse
import json
import re
from pathlib import Path
from typing import List, Dict, Any


def extract_tender_number(text: str) -> str | None:
    """Extract tender number from text."""
    if not text:
        return None
    match = re.search(r'([A-Z]{2,4}\d{9,})', text)
    return match.group(1) if match else None


def load_tenders_from_main_data(data_path: Path) -> List[Dict[str, Any]]:
    """Load tenders with tender_id and detail_url from main data."""
    tenders = []
    
    with open(data_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
                
                # Extract tender number
                all_cells = record.get("all_cells", "")
                tender_number = extract_tender_number(all_cells)
                
                if not tender_number:
                    continue
                
                # Get tender_id and detail_url if available
                tender_id = record.get("tender_id")
                detail_url = record.get("detail_url")
                
                # If not in record, try to extract from raw_html
                if not tender_id:
                    raw_html = record.get("raw_html", "")
                    # Try id="A657645"
                    id_match = re.search(r'id="A(\d+)"', raw_html)
                    if id_match:
                        tender_id = id_match.group(1)
                    else:
                        # Try onclick ShowApp(657645,...)
                        onclick_match = re.search(r'ShowApp\((\d+)', raw_html)
                        if onclick_match:
                            tender_id = onclick_match.group(1)
                
                # Build detail_url if we have tender_id
                if tender_id and not detail_url:
                    detail_url = f"https://tenders.procurement.gov.ge/public/?go={tender_id}&lang=ge"
                
                tenders.append({
                    "tender_number": tender_number,
                    "tender_id": tender_id,
                    "detail_url": detail_url,
                    "buyer": record.get("buyer", ""),
                    "status": record.get("status", ""),
                })
                
            except Exception as e:
                print(f"Warning: Failed to parse line {line_num}: {e}")
                continue
    
    return tenders


def filter_tenders(
    tenders: List[Dict[str, Any]],
    tender_numbers: List[str] | None = None
) -> List[Dict[str, Any]]:
    """Filter tenders by tender numbers if provided."""
    if not tender_numbers:
        return tenders
    
    filtered = []
    for tender in tenders:
        if tender["tender_number"] in tender_numbers:
            filtered.append(tender)
    
    return filtered


def main():
    parser = argparse.ArgumentParser(
        description="Prepare tender data for detailed scraping"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Main data file (data/tenders.jsonl)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file with tender data (default: print to stdout)"
    )
    parser.add_argument(
        "--tender-numbers",
        nargs="+",
        help="Filter by specific tender numbers"
    )
    parser.add_argument(
        "--format",
        choices=["json", "list", "command"],
        default="json",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    # Load tenders
    print(f"Loading tenders from {args.input_file}...")
    tenders = load_tenders_from_main_data(args.input_file)
    print(f"Found {len(tenders)} tenders with tender numbers")
    
    # Filter if requested
    if args.tender_numbers:
        tenders = filter_tenders(tenders, args.tender_numbers)
        print(f"Filtered to {len(tenders)} tenders")
    
    # Count with tender_id
    with_id = sum(1 for t in tenders if t.get("tender_id"))
    print(f"  - {with_id} have tender_id (can use direct URL)")
    print(f"  - {len(tenders) - with_id} need search method")
    
    # Output
    if args.format == "json":
        output = json.dumps(tenders, indent=2, ensure_ascii=False)
    elif args.format == "list":
        output = "\n".join([t["tender_number"] for t in tenders])
    elif args.format == "command":
        # Generate command for detailed scraper
        numbers = [t["tender_number"] for t in tenders]
        output = f"python3 detailed_scraper/detail_scraper.py {' '.join(numbers)}"
    
    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"\nOutput written to {args.output}")
    else:
        print("\n" + output)
    
    return 0


if __name__ == "__main__":
    exit(main())

