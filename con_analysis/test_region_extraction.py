#!/usr/bin/env python3
"""
Test script to extract region information from tender descriptions.

Region is typically found in patterns like:
- "ზუგდიდის მუნიციპალიტეტის" -> Zugdidi
- "თბილისის მუნიციპალიტეტის" -> Tbilisi
- "ბათუმის მუნიციპალიტეტის" -> Batumi
"""
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any


# Common Georgian municipalities/regions
GEORGIAN_REGIONS = [
    "თბილის", "ბათუმ", "ქუთაის", "რუსთავ", "გორ", "ზუგდიდ", "ფოთ",
    "ხაშურ", "სამტრედი", "ზესტაფონ", "მარნეულ", "თელავ", "ახალციხ",
    "ქობულეთ", "ოზურგეთ", "კასპ", "ჭიათურ", "წყალტუბ", "საჩხერ",
    "ბოლნის", "გარდაბან", "დუშეთ", "მცხეთ", "ახმეტ", "გურჯაან",
    "სიღნაღ", "დედოფლისწყარ", "ლაგოდეხ", "საგარეჯ", "ონ", "ამბროლაურ",
    "ლენტეხ", "ცაგერ", "ახალგორ", "კარელ", "ხაშურ", "ბორჯომ",
    "ნინოწმინდ", "ადიგენ", "ასპინძ", "აბაშ", "სენაკ", "მარტვილ",
    "ჩხოროწყუ", "წალენჯიხ", "ხობ", "ლანჩხუთ", "ჩოხატაურ", "ბაღდათ",
    "ვან", "ხარაგაულ", "ტყიბულ", "წალკ", "ახალქალაქ", "ნინოწმინდ",
    "ბორჯომ", "ხულო", "შუახევ", "ქედ", "ხელვაჩაურ"
]


def extract_region_from_text(text: str) -> Optional[str]:
    """
    Extract region/municipality name from tender description text.
    
    Args:
        text: Tender description or title text
        
    Returns:
        Region name in Georgian, or None if not found
    """
    if not text:
        return None
    
    # Pattern 1: "X-ის მუნიციპალიტეტის" -> X municipality
    municipality_pattern = r'([ა-ჰ]+)ის\s+მუნიციპალიტეტ'
    match = re.search(municipality_pattern, text)
    if match:
        region = match.group(1)
        # Verify it's a known region
        for known_region in GEORGIAN_REGIONS:
            if region.startswith(known_region) or known_region.startswith(region):
                return region + "ი"  # Return in nominative case
    
    # Pattern 2: Direct municipality name mention
    for region in GEORGIAN_REGIONS:
        # Look for region name followed by municipality-related words
        pattern = rf'\b{region}[ა-ჰ]*\s+მუნიციპალიტეტ'
        if re.search(pattern, text):
            return region + "ი"
    
    # Pattern 3: Just the region name in genitive case
    for region in GEORGIAN_REGIONS:
        genitive_pattern = rf'\b{region}ის\b'
        if re.search(genitive_pattern, text):
            return region + "ი"
    
    return None


def test_region_extraction():
    """Test region extraction with sample data."""
    
    test_cases = [
        {
            "text": "ზუგდიდის მუნიციპალიტეტის სკოლების მოსწავლეების სატრანსპორტო მომსახურება",
            "expected": "ზუგდიდი"
        },
        {
            "text": "თბილისის მუნიციპალიტეტის სკოლების",
            "expected": "თბილისი"
        },
        {
            "text": "ბათუმის მუნიციპალიტეტის",
            "expected": "ბათუმი"
        },
        {
            "text": "ონის მუნიციპალიტეტის მერია",
            "expected": "ონი"
        },
        {
            "text": "ხულოს მუნიციპალიტეტი",
            "expected": "ხულოი"
        }
    ]
    
    print("Testing region extraction:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        result = extract_region_from_text(test["text"])
        expected = test["expected"]
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} Test {i}:")
        print(f"  Text: {test['text'][:60]}...")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    return failed == 0


def test_with_real_data():
    """Test with real tender data from detailed_tenders.jsonl."""
    
    data_file = Path(__file__).parent.parent / "data" / "detailed_tenders.jsonl"
    
    if not data_file.exists():
        print(f"Data file not found: {data_file}")
        return
    
    print("\nTesting with real tender data:")
    print("=" * 60)
    
    count = 0
    found_regions = 0
    
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            if count >= 10:  # Test first 10 tenders
                break
            
            try:
                data = json.loads(line)
                tender_num = data.get("procurement_number", "Unknown")
                
                # Try to extract region from description or title
                text = data.get("description", "") + " " + data.get("title", "")
                region = extract_region_from_text(text)
                
                if region:
                    found_regions += 1
                    print(f"✓ {tender_num}: {region}")
                    print(f"  Text: {text[:80]}...")
                else:
                    print(f"✗ {tender_num}: No region found")
                    print(f"  Text: {text[:80]}...")
                
                print()
                count += 1
                
            except json.JSONDecodeError:
                continue
    
    print("=" * 60)
    print(f"Found regions in {found_regions}/{count} tenders")


if __name__ == "__main__":
    # Run tests
    test_passed = test_region_extraction()
    
    # Test with real data
    test_with_real_data()
    
    if test_passed:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed - region extraction logic needs improvement")
