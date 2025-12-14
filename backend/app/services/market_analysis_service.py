"""Market Analysis Service - Analyzes tender data with region correction and statistics."""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

logger = logging.getLogger(__name__)

# Georgian municipalities for region extraction
MUNICIPALITIES = {
    # Major cities
    'თბილის': 'თბილისი', 'ბათუმ': 'ბათუმი', 'ქუთაის': 'ქუთაისი', 'გორ': 'გორი',
    'ზუგდიდ': 'ზუგდიდი', 'ფოთ': 'ფოთი', 'თელავ': 'თელავი', 'რუსთავ': 'რუსთავი',
    
    # Adjara
    'ხულო': 'ხულო', 'შუახევ': 'შუახევი', 'ქედ': 'ქედა', 'ქობულეთ': 'ქობულეთი',
    'ხელვაჩაურ': 'ხელვაჩაური',
    
    # Guria
    'ლანჩხუთ': 'ლანჩხუთი', 'ოზურგეთ': 'ოზურგეთი', 'ჩოხატაურ': 'ჩოხატაური',
    
    # Samegrelo
    'მარტვილ': 'მარტვილი', 'სენაკ': 'სენაკი', 'ხობ': 'ხობი', 'წალენჯიხ': 'წალენჯიხა',
    'ჩხოროწყუ': 'ჩხოროწყუ', 'აბაშ': 'აბაშა',
    
    # Racha
    'ამბროლაურ': 'ამბროლაური', 'ონ': 'ონი', 'ცაგერ': 'ცაგერი', 'ლენტეხ': 'ლენტეხი',
    
    # Imereti
    'ჭიათურ': 'ჭიათურა', 'საჩხერ': 'საჩხერე', 'ზესტაფონ': 'ზესტაფონი',
    'ბაღდათ': 'ბაღდათი', 'ვან': 'ვანი', 'სამტრედი': 'სამტრედია', 'ხონ': 'ხონი',
    'ტყიბულ': 'ტყიბული', 'წყალტუბ': 'წყალტუბო', 'თერჯოლ': 'თერჯოლა',
    'ხარაგაულ': 'ხარაგაული',
    
    # Samtskhe-Javakheti
    'ბორჯომ': 'ბორჯომი', 'ახალციხ': 'ახალციხე', 'ადიგენ': 'ადიგენი',
    'ასპინძ': 'ასპინძა', 'ახალქალაქ': 'ახალქალაქი', 'ნინოწმინდ': 'ნინოწმინდა',
    
    # Shida Kartli
    'კასპ': 'კასპი', 'ქარელ': 'ქარელი', 'ხაშურ': 'ხაშური',
    
    # Mtskheta-Mtianeti
    'დუშეთ': 'დუშეთი', 'თიანეთ': 'თიანეთი', 'მცხეთ': 'მცხეთა', 'ყაზბეგ': 'ყაზბეგი',
    
    # Kvemo Kartli
    'თეთრიწყარ': 'თეთრიწყარო', 'ბოლნის': 'ბოლნისი', 'დმანის': 'დმანისი',
    'წალკ': 'წალკა', 'მარნეულ': 'მარნეული', 'გარდაბან': 'გარდაბანი',
    
    # Kakheti
    'საგარეჯ': 'საგარეჯო', 'გურჯაან': 'გურჯაანი', 'სიღნაღ': 'სიღნაღი',
    'დედოფლისწყარ': 'დედოფლისწყარო', 'ლაგოდეხ': 'ლაგოდეხი',
    'ყვარელ': 'ყვარელი', 'ახმეტ': 'ახმეტა',
    
    # Svaneti
    'მესტი': 'მესტია',
}


class MarketAnalysisService:
    """Service for market analysis calculations."""
    
    def __init__(self, data_path: Path):
        """Initialize the service."""
        self.data_path = data_path
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def extract_real_region(self, document_names: str, title: str, description: str) -> str:
        """
        Extract real region from document names, title, and description.
        
        Args:
            document_names: String containing document file names
            title: Tender title
            description: Additional information
            
        Returns:
            Municipality name or "Other"
        """
        # Combine all text sources
        search_text = f"{document_names} {title} {description}".lower()
        
        # Sort by length (longest first) to match longer names before shorter ones
        sorted_municipalities = sorted(MUNICIPALITIES.items(), key=lambda x: len(x[0]), reverse=True)
        
        for root, full_name in sorted_municipalities:
            # Special handling for 'ონ' (Oni) to avoid false matches
            if root == 'ონ':
                if 'ონი' in search_text:
                    # Exclude false positives
                    if 'ზესტაფონი' not in search_text and 'რეგიონი' not in search_text:
                        return full_name
            else:
                if root in search_text:
                    return full_name
        
        return "Other"
    
    def _load_all_detailed_tenders(self) -> List[Dict[str, Any]]:
        """Load all detailed tender files."""
        cache_key = "all_tenders"
        
        # Check cache
        if cache_key in self._cache:
            cache_age = datetime.now() - self._cache_time[cache_key]
            if cache_age < self._cache_ttl:
                logger.info(f"Using cached data (age: {cache_age.seconds}s)")
                return self._cache[cache_key]
        
        logger.info("Loading tender data from files...")
        tenders = []
        
        # Load all type-specific detailed files
        detailed_files = list(self.data_path.glob("*_detailed_tenders.jsonl"))
        
        for file_path in detailed_files:
            logger.info(f"Loading {file_path.name}...")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                tender = json.loads(line)
                                # Filter: Only include tenders with CPV code 60100000 (Automotive Transport Services)
                                if tender.get('category_code') == '60100000':
                                    tenders.append(tender)
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                continue
        
        logger.info(f"Loaded {len(tenders)} tenders total")
        
        # Cache the results
        self._cache[cache_key] = tenders
        self._cache_time[cache_key] = datetime.now()
        
        return tenders
    
    def _extract_year(self, date_str: Optional[str]) -> Optional[int]:
        """Extract year from date string."""
        if not date_str:
            return None
        try:
            # Try parsing YYYY-MM-DD format
            return int(date_str[:4])
        except (ValueError, IndexError):
            return None
    
    def _parse_price(self, price_value: Any) -> float:
        """Parse price value to float."""
        if price_value is None:
            return 0.0
        
        if isinstance(price_value, (int, float)):
            return float(price_value)
        
        if isinstance(price_value, str):
            # Remove commas and spaces
            cleaned = price_value.replace(',', '').replace(' ', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        
        return 0.0
    
    def calculate_price_trends(self) -> Dict[str, Any]:
        """Calculate price trends by region and year."""
        tenders = self._load_all_detailed_tenders()
        
        # Group by region and year
        region_year_prices = defaultdict(lambda: defaultdict(list))
        
        for tender in tenders:
            # Extract region
            doc_names = ' '.join([doc.get('name', '') for doc in tender.get('documents', [])])
            title = tender.get('title', '')
            desc = tender.get('additional_information', '')
            region = self.extract_real_region(doc_names, title, desc)
            
            # Extract year - use published_date (correct field name)
            pub_date = tender.get('published_date')
            year = self._extract_year(pub_date)
            
            # Extract price
            price = self._parse_price(tender.get('estimated_value') or tender.get('initial_price'))
            
            if year and price > 0:
                region_year_prices[region][year].append(price)
        
        # Calculate averages and inflation
        result = {
            "regions": [],
            "years": list(range(2020, 2026)),
            "data": {}
        }
        
        for region, years_data in region_year_prices.items():
            if len(years_data) < 2:  # Skip regions with insufficient data
                continue
            
            result["regions"].append(region)
            result["data"][region] = {}
            
            # Calculate average for each year (use median to handle per-unit pricing)
            for year in range(2020, 2026):
                if year in years_data and len(years_data[year]) > 0:
                    # Use median instead of mean to handle outliers (per-km, per-unit prices)
                    sorted_prices = sorted(years_data[year])
                    n = len(sorted_prices)
                    if n % 2 == 0:
                        median_price = (sorted_prices[n//2 - 1] + sorted_prices[n//2]) / 2
                    else:
                        median_price = sorted_prices[n//2]
                    result["data"][region][str(year)] = round(median_price, 2)
                else:
                    result["data"][region][str(year)] = None
            
            # Calculate 5-year inflation using median
            earliest_year = min(years_data.keys())
            latest_year = max(years_data.keys())
            
            if earliest_year != latest_year and len(years_data[earliest_year]) > 0 and len(years_data[latest_year]) > 0:
                # Calculate median for earliest year
                sorted_early = sorted(years_data[earliest_year])
                n_early = len(sorted_early)
                if n_early % 2 == 0:
                    earliest_median = (sorted_early[n_early//2 - 1] + sorted_early[n_early//2]) / 2
                else:
                    earliest_median = sorted_early[n_early//2]
                
                # Calculate median for latest year
                sorted_late = sorted(years_data[latest_year])
                n_late = len(sorted_late)
                if n_late % 2 == 0:
                    latest_median = (sorted_late[n_late//2 - 1] + sorted_late[n_late//2]) / 2
                else:
                    latest_median = sorted_late[n_late//2]
                
                if earliest_median > 0:
                    inflation = ((latest_median - earliest_median) / earliest_median) * 100
                    result["data"][region]["inflation_5y"] = round(inflation, 2)
                else:
                    result["data"][region]["inflation_5y"] = 0.0
            else:
                result["data"][region]["inflation_5y"] = 0.0
        
        # Sort regions by total activity
        result["regions"] = sorted(result["regions"], 
                                   key=lambda r: sum(1 for y in result["data"][r].values() if isinstance(y, (int, float)) and y),
                                   reverse=True)[:10]  # Top 10 regions
        
        return result
    
    def calculate_market_share(self) -> Dict[str, Any]:
        """Calculate market share by winners."""
        tenders = self._load_all_detailed_tenders()
        
        winner_stats = defaultdict(lambda: {
            'total_wins': 0,
            'total_value': 0.0,
            'regions': set()
        })
        
        for tender in tenders:
            # Get winner
            winner_data = tender.get('winner', {})
            if isinstance(winner_data, dict):
                winner_name = winner_data.get('supplier', '').strip()
            else:
                winner_name = str(winner_data).strip()
            
            if not winner_name or winner_name.lower() in ['', 'none', 'null']:
                continue
            
            # Get winning price
            winning_price = self._parse_price(
                winner_data.get('amount') if isinstance(winner_data, dict) else 
                tender.get('winning_price') or tender.get('final_price')
            )
            
            # Get region
            doc_names = ' '.join([doc.get('name', '') for doc in tender.get('documents', [])])
            title = tender.get('title', '')
            desc = tender.get('additional_information', '')
            region = self.extract_real_region(doc_names, title, desc)
            
            winner_stats[winner_name]['total_wins'] += 1
            winner_stats[winner_name]['total_value'] += winning_price
            winner_stats[winner_name]['regions'].add(region)
        
        # Convert to list and sort by total value
        top_winners = []
        for name, stats in winner_stats.items():
            top_winners.append({
                'name': name,
                'total_wins': stats['total_wins'],
                'total_value': round(stats['total_value'], 2),
                'regions': sorted(list(stats['regions']))
            })
        
        top_winners.sort(key=lambda x: x['total_value'], reverse=True)
        
        return {"top_winners": top_winners[:10]}
    
    def calculate_failure_rates(self) -> Dict[str, Any]:
        """Calculate failure rates by region."""
        tenders = self._load_all_detailed_tenders()
        
        region_stats = defaultdict(lambda: {'total': 0, 'failed': 0})
        
        # Failed status keywords
        failed_statuses = ['არ შედგა', 'უარყოფითი შედეგით', 'შეწყვეტილია']
        
        for tender in tenders:
            # Get region
            doc_names = ' '.join([doc.get('name', '') for doc in tender.get('documents', [])])
            title = tender.get('title', '')
            desc = tender.get('additional_information', '')
            region = self.extract_real_region(doc_names, title, desc)
            
            # Get status
            status = tender.get('status', '').strip()
            
            region_stats[region]['total'] += 1
            
            # Check if failed
            if any(failed_status in status for failed_status in failed_statuses):
                region_stats[region]['failed'] += 1
        
        # Calculate failure rates
        regions = []
        for region, stats in region_stats.items():
            if stats['total'] > 0:
                failure_rate = (stats['failed'] / stats['total']) * 100
                regions.append({
                    'name': region,
                    'total': stats['total'],
                    'failed': stats['failed'],
                    'failure_rate': round(failure_rate, 2)
                })
        
        # Sort by failure rate
        regions.sort(key=lambda x: x['failure_rate'], reverse=True)
        
        return {"regions": regions[:10]}
    
    def calculate_kpis(self) -> Dict[str, Any]:
        """Calculate overall KPIs."""
        tenders = self._load_all_detailed_tenders()
        
        total_tenders = len(tenders)
        total_market_volume = 0.0
        inflation_values = []
        
        # Calculate market volume
        for tender in tenders:
            price = self._parse_price(
                tender.get('estimated_value') or 
                tender.get('initial_price') or
                tender.get('winning_price')
            )
            total_market_volume += price
        
        # Get inflation from price trends
        price_trends = self.calculate_price_trends()
        for region_data in price_trends['data'].values():
            if 'inflation_5y' in region_data and region_data['inflation_5y']:
                inflation_values.append(region_data['inflation_5y'])
        
        avg_inflation = sum(inflation_values) / len(inflation_values) if inflation_values else 0.0
        
        return {
            'total_tenders': total_tenders,
            'avg_inflation': round(avg_inflation, 2),
            'total_market_volume': round(total_market_volume, 2)
        }
