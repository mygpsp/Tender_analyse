#!/usr/bin/env python3
"""
Generate report of CON tenders without regions.

This script analyzes all CON tenders and creates a report showing
which tenders are missing region information, along with their
descriptions and document names to help identify the region manually.
"""
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from con_analysis.extract_region import extract_region_from_text


def generate_missing_regions_report():
    """Generate report of tenders without regions."""
    
    # Load main tender data
    main_data = {}
    with open('main_scrapper/data/tenders.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            try:
                tender = json.loads(line)
                if tender.get('tender_type') == 'CON' and tender.get('category_code') == '60100000':
                    main_data[tender.get('number')] = tender
            except json.JSONDecodeError:
                continue
    
    # Load detailed tender data
    detailed_data = {}
    with open('data/detailed_tenders.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            try:
                detail = json.loads(line)
                number = detail.get('procurement_number')
                if number and number.startswith('CON'):
                    detailed_data[number] = detail
            except json.JSONDecodeError:
                continue
    
    # Analyze each tender
    tenders_with_region = []
    tenders_without_region = []
    
    for number, tender in main_data.items():
        # Try to extract region from description
        description = tender.get('all_cells', '') + ' ' + tender.get('category', '')
        region = extract_region_from_text(description)
        
        # Try document names if no region found
        if not region and number in detailed_data:
            detail = detailed_data[number]
            documents = detail.get('documents', [])
            for doc in documents:
                doc_name = doc.get('name', '')
                doc_region = extract_region_from_text(doc_name)
                if doc_region:
                    region = doc_region
                    break
        
        tender_info = {
            'number': number,
            'region': region,
            'title': detailed_data.get(number, {}).get('title', ''),
            'description': detailed_data.get(number, {}).get('description', ''),
            'all_cells': tender.get('all_cells', '')[:200],
            'documents': [doc.get('name', '') for doc in detailed_data.get(number, {}).get('documents', [])][:5],
            'status': tender.get('status', ''),
            'published_date': tender.get('published_date', '')
        }
        
        if region:
            tenders_with_region.append(tender_info)
        else:
            tenders_without_region.append(tender_info)
    
    # Generate report
    print("=" * 80)
    print("CON TENDERS REGION ANALYSIS REPORT")
    print("=" * 80)
    print(f"\nTotal CON tenders: {len(main_data)}")
    print(f"Tenders WITH region: {len(tenders_with_region)} ({len(tenders_with_region)/len(main_data)*100:.1f}%)")
    print(f"Tenders WITHOUT region: {len(tenders_without_region)} ({len(tenders_without_region)/len(main_data)*100:.1f}%)")
    
    # Show tenders without regions
    print("\n" + "=" * 80)
    print("TENDERS WITHOUT REGIONS (need manual review)")
    print("=" * 80)
    
    for i, tender in enumerate(tenders_without_region, 1):
        print(f"\n{i}. {tender['number']} - {tender['published_date']} - {tender['status']}")
        print(f"   Title: {tender['title'][:100] if tender['title'] else 'N/A'}")
        print(f"   Description: {tender['description'][:150] if tender['description'] else 'N/A'}")
        print(f"   All cells: {tender['all_cells']}")
        if tender['documents']:
            print(f"   Documents:")
            for doc in tender['documents']:
                print(f"     - {doc}")
        else:
            print(f"   Documents: None")
        print()
    
    # Save to file
    output_file = Path('con_analysis/data/tenders_without_regions.txt')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("TENDERS WITHOUT REGIONS\n")
        f.write("=" * 80 + "\n\n")
        for tender in tenders_without_region:
            f.write(f"{tender['number']}\n")
            f.write(f"  Title: {tender['title']}\n")
            f.write(f"  Description: {tender['description'][:200]}\n")
            f.write(f"  Documents: {', '.join(tender['documents'])}\n")
            f.write(f"  All cells: {tender['all_cells']}\n")
            f.write("\n")
    
    print(f"\nReport saved to: {output_file}")
    
    # Show regions found
    print("\n" + "=" * 80)
    print("REGIONS FOUND")
    print("=" * 80)
    regions_count = {}
    for tender in tenders_with_region:
        region = tender['region']
        regions_count[region] = regions_count.get(region, 0) + 1
    
    for region, count in sorted(regions_count.items(), key=lambda x: -x[1]):
        print(f"  {region}: {count} tenders")


if __name__ == '__main__':
    generate_missing_regions_report()
