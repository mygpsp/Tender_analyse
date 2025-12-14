"""Service layer for CON tender business logic."""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter


# Georgian municipalities with root forms for matching
# Format: 'root': 'full_name'
MUNICIPALITY_ROOTS = {
    'ბათუმ': 'ბათუმი',
    'ქობულეთ': 'ქობულეთი',
    'ხელვაჩაურ': 'ხელვაჩაური',
    'ქედ': 'ქედა',
    'შუახევ': 'შუახევი',
    'ხულო': 'ხულო',
    'ქუთაის': 'ქუთაისი',
    'წყალტუბ': 'წყალტუბო',
    'ჭიათურ': 'ჭიათურა',
    'საჩხერ': 'საჩხერე',
    'ტყიბულ': 'ტყიბული',
    'ბაღდათ': 'ბაღდათი',
    'ვან': 'ვანი',
    'სამტრედი': 'სამტრედია',
    'ხონ': 'ხონი',
    'ზესტაფონ': 'ზესტაფონი',
    'თერჯოლ': 'თერჯოლა',
    'ხარაგაულ': 'ხარაგაული',
    'ამბროლაურ': 'ამბროლაური',
    'ცაგერ': 'ცაგერი',
    'ონ': 'ონი',
    'ლენტეხ': 'ლენტეხი',
    'ოზურგეთ': 'ოზურგეთი',
    'ლანჩხუთ': 'ლანჩხუთი',
    'ჩოხატაურ': 'ჩოხატაური',
    'ზუგდიდ': 'ზუგდიდი',
    'ფოთ': 'ფოთი',
    'სენაკ': 'სენაკი',
    'ხობ': 'ხობი',
    'მარტვილ': 'მარტვილი',
    'აბაშ': 'აბაშა',
    'წალენჯიხ': 'წალენჯიხა',
    'ჩხოროწყუ': 'ჩხოროწყუ',
    'მესტი': 'მესტია',
    'თელავ': 'თელავი',
    'ახმეტ': 'ახმეტა',
    'ყვარელ': 'ყვარელი',
    'ლაგოდეხ': 'ლაგოდეხი',
    'გურჯაან': 'გურჯაანი',
    'სიღნაღ': 'სიღნაღი',
    'დედოფლისწყარ': 'დედოფლისწყარო',
    'საგარეჯ': 'საგარეჯო',
    'რუსთავ': 'რუსთავი',
    'გარდაბან': 'გარდაბანი',
    'მარნეულ': 'მარნეული',
    'ბოლნის': 'ბოლნისი',
    'დმანის': 'დმანისი',
    'წალკ': 'წალკა',
    'თეთრიწყარ': 'თეთრიწყარო',
    'მცხეთ': 'მცხეთა',
    'დუშეთ': 'დუშეთი',
    'თიანეთ': 'თიანეთი',
    'ყაზბეგ': 'ყაზბეგი',
    'გორ': 'გორი',
    'კასპ': 'კასპი',
    'ქარელ': 'ქარელი',
    'ხაშურ': 'ხაშური',
    'ბორჯომ': 'ბორჯომი',
    'ახალციხ': 'ახალციხე',
    'ადიგენ': 'ადიგენი',
    'ასპინძ': 'ასპინძა',
    'ახალქალაქ': 'ახალქალაქი',
    'ნინოწმინდ': 'ნინოწმინდა',
    'თბილის': 'თბილისი'
}


def extract_region_from_text(text: str, additional_text: str = '') -> Optional[str]:
    """
    Extract region/municipality name from text using known municipality roots.
    
    Args:
        text: Primary text to search (e.g., document names)
        additional_text: Additional text to search (e.g., description)
        
    Returns:
        Full municipality name, or None if not found
    """
    if not text and not additional_text:
        return None
    
    # Combine texts for searching
    search_text = f"{text} {additional_text}"
    
    # Sort by length (longest first) to match longer names before shorter ones
    sorted_roots = sorted(MUNICIPALITY_ROOTS.items(), key=lambda x: len(x[0]), reverse=True)
    
    for root, full_name in sorted_roots:
        # Special handling for 'ონ' (Oni) to avoid false matches
        if root == 'ონ':
            # Only match if we find 'ონი' and NOT inside other words
            if 'ონი' in search_text:
                # Exclude false positives
                if 'ზესტაფონი' not in search_text and 'რეგიონი' not in search_text:
                    return full_name
        else:
            # For other municipalities, check if root appears in text
            if root in search_text:
                return full_name
    
    return None


class ConTenderService:
    """Service for CON tender operations."""
    
    def __init__(self, data_path: Path):
        """
        Initialize the service.
        
        Args:
            data_path: Path to main_scrapper/data directory
        """
        self.data_path = data_path
        # Use CON-specific filtered file for faster loading
        self.tenders_file = data_path / "con_filter.jsonl"
        # Use CON-specific detailed file
        self.detailed_file = data_path / "con_detailed_tenders.jsonl"
    
    def load_con_tenders(
        self,
        category_code: str = "60100000",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[str] = None,
        region: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load and filter CON tenders.
        
        Args:
            category_code: Category code to filter
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            status: Status filter
            region: Region filter
            search: Search query
            
        Returns:
            List of filtered CON tenders
        """
        # Load detailed data first for region extraction from documents
        detailed_data = {}
        if self.detailed_file.exists():
            with open(self.detailed_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        detail = json.loads(line)
                        number = detail.get('procurement_number')
                        if number:
                            detailed_data[number] = detail
                    except json.JSONDecodeError:
                        continue
        
        tenders = []
        
        with open(self.tenders_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    tender = json.loads(line)
                    
                    # Filter by tender_type and category_code
                    if (tender.get('tender_type') != 'CON' or 
                        tender.get('category_code') != category_code):
                        continue
                    
                    # Apply date filters
                    if date_from and tender.get('published_date', '') < date_from:
                        continue
                    if date_to and tender.get('published_date', '') > date_to:
                        continue
                    
                    # Apply status filter
                    if status and tender.get('status') != status:
                        continue
                    
                    # Apply search filter
                    if search:
                        search_text = (
                            tender.get('number', '') + ' ' +
                            tender.get('buyer', '') + ' ' +
                            tender.get('all_cells', '')
                        ).lower()
                        if search.lower() not in search_text:
                            continue
                    
                    # Extract region from document names and additional information
                    tender_number = tender.get('number')
                    tender_region = None
                    
                    if tender_number in detailed_data:
                        detail = detailed_data[tender_number]
                        
                        # Get document names
                        documents = detail.get('documents') or []
                        doc_names = ' '.join([doc.get('name', '') for doc in documents])
                        
                        # Get additional information
                        additional_info = detail.get('additional_information', '') + ' ' + detail.get('description', '')
                        
                        # Extract region
                        tender_region = extract_region_from_text(doc_names, additional_info)
                    
                    # Fallback: try to extract from main data
                    if not tender_region:
                        description = tender.get('all_cells', '') + ' ' + tender.get('category', '')
                        tender_region = extract_region_from_text(description)
                    
                    tender['region'] = tender_region or ''
                    
                    # Use estimated_value from detailed data if available
                    if tender_number in detailed_data:
                        detail = detailed_data[tender_number]
                        estimated_value = detail.get('estimated_value')
                        if estimated_value:
                            try:
                                tender['amount'] = float(estimated_value)
                            except (ValueError, TypeError):
                                pass
                    
                    # Apply region filter
                    if region and tender['region'] != region:
                        continue
                    
                    tenders.append(tender)
                    
                except json.JSONDecodeError:
                    continue
        
        return tenders
    
    def enrich_with_detailed_data(self, tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich tenders with detailed data (final price, winner).
        
        Args:
            tenders: List of CON tenders
            
        Returns:
            Enriched tenders with detailed data
        """
        # Load detailed tenders into a dict for quick lookup
        detailed_data = {}
        
        if self.detailed_file.exists():
            with open(self.detailed_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        detail = json.loads(line)
                        number = detail.get('procurement_number')
                        if number:
                            detailed_data[number] = detail
                    except json.JSONDecodeError:
                        continue
        
        # Enrich tenders
        enriched = []
        for tender in tenders:
            tender_number = tender.get('number')
            detail = detailed_data.get(tender_number, {})
            
            # Add final price (from winner or lowest bidder)
            winner = detail.get('winner', {})
            lowest_bidder = detail.get('lowest_bidder', {})
            
            tender['final_price'] = winner.get('amount') or lowest_bidder.get('amount') or ''
            tender['winner_name'] = winner.get('supplier') or lowest_bidder.get('supplier') or tender.get('supplier', '')
            
            enriched.append(tender)
        
        return enriched
    
    def get_statistics(self, tenders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics for CON tenders.
        
        Args:
            tenders: List of CON tenders
            
        Returns:
            Statistics dictionary
        """
        if not tenders:
            return {
                'total_count': 0,
                'total_amount': 0,
                'avg_amount': 0,
                'status_distribution': {},
                'region_distribution': {},
                'date_range': {'from': '', 'to': ''},
                'regions_count': 0
            }
        
        # Calculate statistics
        amounts = [t.get('amount', 0) for t in tenders if t.get('amount')]
        dates = [t.get('published_date') for t in tenders if t.get('published_date')]
        statuses = Counter(t.get('status', 'Unknown') for t in tenders)
        regions = Counter(t.get('region', 'Unknown') for t in tenders if t.get('region'))
        
        return {
            'total_count': len(tenders),
            'total_amount': sum(amounts),
            'avg_amount': sum(amounts) / len(amounts) if amounts else 0,
            'status_distribution': dict(statuses),
            'region_distribution': dict(regions),
            'date_range': {
                'from': min(dates) if dates else '',
                'to': max(dates) if dates else ''
            },
            'regions_count': len(regions)
        }
