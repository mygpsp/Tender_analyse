#!/usr/bin/env python3
"""
Utility module to extract region/municipality names from tender descriptions.

This module provides functions to identify Georgian municipalities from tender
text using regex patterns. It supports 50+ municipalities and handles various
grammatical cases.
"""
import re
from typing import Optional


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
        Region name in Georgian (nominative case), or None if not found
        
    Examples:
        >>> extract_region_from_text("ზუგდიდის მუნიციპალიტეტის სკოლების")
        'ზუგდიდი'
        >>> extract_region_from_text("თბილისის მუნიციპალიტეტის")
        'თბილისი'
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


def get_all_regions() -> list[str]:
    """
    Get list of all supported Georgian regions.
    
    Returns:
        List of region names in nominative case
    """
    return [region + "ი" for region in GEORGIAN_REGIONS]


if __name__ == "__main__":
    # Simple test
    test_texts = [
        "ზუგდიდის მუნიციპალიტეტის სკოლების მოსწავლეების სატრანსპორტო მომსახურება",
        "თბილისის მუნიციპალიტეტის სკოლების",
        "ბათუმის მუნიციპალიტეტის",
    ]
    
    print("Testing region extraction:")
    for text in test_texts:
        region = extract_region_from_text(text)
        print(f"  {text[:50]}... -> {region}")
