#!/usr/bin/env python3
"""
Find New Year Products Tenders in Khelvachauri
Searches for tenders containing "საახალწლო" (New Year) products in "ხელვაჩაური" (Khelvachauri)
"""

import json
from pathlib import Path

# Search terms
NEW_YEAR_TERM = "საახალწლო"  # New Year
KHELVACHAURI_TERM = "ხელვაჩაური"  # Khelvachauri

# Data directory
DATA_DIR = Path("main_scrapper/data")

# Results
results = {
    "new_year_products": [],
    "khelvachauri_tenders": [],
    "both_criteria": []
}

# Search all JSONL files
for jsonl_file in DATA_DIR.glob("*_detailed_tenders.jsonl"):
    print(f"Searching {jsonl_file.name}...")
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                tender = json.loads(line)
                tender_text = json.dumps(tender, ensure_ascii=False).lower()
                
                has_new_year = NEW_YEAR_TERM.lower() in tender_text
                has_khelvachauri = KHELVACHAURI_TERM.lower() in tender_text
                
                if has_new_year and has_khelvachauri:
                    results["both_criteria"].append(tender)
                    print(f"  ✅ MATCH (both): {tender.get('number', 'N/A')}")
                elif has_new_year:
                    results["new_year_products"].append(tender)
                    print(f"  🎄 New Year: {tender.get('number', 'N/A')}")
                elif has_khelvachauri:
                    results["khelvachauri_tenders"].append(tender)
                    print(f"  📍 Khelvachauri: {tender.get('number', 'N/A')}")
                    
            except json.JSONDecodeError:
                continue

# Print summary
print("\n" + "="*60)
print("SEARCH RESULTS SUMMARY")
print("="*60)
print(f"New Year products tenders: {len(results['new_year_products'])}")
print(f"Khelvachauri tenders: {len(results['khelvachauri_tenders'])}")
print(f"Tenders matching BOTH criteria: {len(results['both_criteria'])}")
print("="*60)

# Save results
output_file = Path("temp_new_year_khelvachauri_tenders.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n✅ Results saved to: {output_file}")

# Sort all results by published_date (descending - newest first)
def sort_by_date_desc(tenders):
    return sorted(tenders, key=lambda x: x.get('published_date', ''), reverse=True)

results["both_criteria"] = sort_by_date_desc(results["both_criteria"])
results["new_year_products"] = sort_by_date_desc(results["new_year_products"])
results["khelvachauri_tenders"] = sort_by_date_desc(results["khelvachauri_tenders"])

# Print detailed results for tenders matching both criteria
if results["both_criteria"]:
    print("\n" + "="*60)
    print("TENDERS MATCHING BOTH CRITERIA (New Year + Khelvachauri)")
    print("Sorted by: Published Date (Newest First)")
    print("="*60)
    for tender in results["both_criteria"]:
        print(f"\n📅 Published: {tender.get('published_date', 'N/A')} | Deadline: {tender.get('deadline_date', 'N/A')}")
        print(f"📋 Tender: {tender.get('number', 'N/A')}")
        print(f"🏢 Buyer: {tender.get('buyer', 'N/A')}")
        print(f"📊 Status: {tender.get('status', 'N/A')}")
        print(f"💰 Amount: {tender.get('amount', 'N/A')} GEL")
        if 'additional_info' in tender:
            print(f"ℹ️  Info: {tender['additional_info'][:200]}...")
        print("-" * 60)

# Print New Year products tenders
if results["new_year_products"]:
    print("\n" + "="*60)
    print("NEW YEAR PRODUCTS TENDERS (საახალწლო)")
    print("Sorted by: Published Date (Newest First)")
    print("="*60)
    for tender in results["new_year_products"][:20]:  # Show first 20
        print(f"\n📅 {tender.get('published_date', 'N/A')} → ⏰ Deadline: {tender.get('deadline_date', 'N/A')}")
        print(f"📋 {tender.get('number', 'N/A')} | 💰 {tender.get('amount', 'N/A')} GEL")
        print(f"🏢 {tender.get('buyer', 'N/A')}")
        print(f"📊 {tender.get('status', 'N/A')}")
        if 'additional_info' in tender:
            info = tender['additional_info'][:150].replace('\n', ' ')
            print(f"ℹ️  {info}...")

# Print Khelvachauri tenders
if results["khelvachauri_tenders"]:
    print("\n" + "="*60)
    print("KHELVACHAURI MUNICIPALITY TENDERS (ხელვაჩაური)")
    print("Sorted by: Published Date (Newest First)")
    print("="*60)
    for tender in results["khelvachauri_tenders"][:20]:  # Show first 20
        print(f"\n📅 {tender.get('published_date', 'N/A')} → ⏰ Deadline: {tender.get('deadline_date', 'N/A')}")
        print(f"📋 {tender.get('number', 'N/A')} | 💰 {tender.get('amount', 'N/A')} GEL")
        print(f"🏢 {tender.get('buyer', 'N/A')}")
        print(f"📊 {tender.get('status', 'N/A')}")
        if 'additional_info' in tender:
            info = tender['additional_info'][:150].replace('\n', ' ')
            print(f"ℹ️  {info}...")

print("\n✅ Search complete!")
