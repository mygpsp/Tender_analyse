"""Supplier data loader service."""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SupplierLoader:
    """Service for loading supplier data from JSONL files."""
    
    def __init__(self, data_path: Path):
        """
        Initialize supplier loader.
        
        Args:
            data_path: Path to suppliers.jsonl file
        """
        self.data_path = data_path
        self._cache: Optional[List[Dict[str, Any]]] = None
        self._cache_mtime: Optional[float] = None
    
    def load_data(self) -> List[Dict[str, Any]]:
        """
        Load supplier data from JSONL file with caching.
        
        Returns:
            List of supplier dictionaries
        """
        # Check if file exists
        if not self.data_path.exists():
            logger.warning(f"Supplier data file not found: {self.data_path}")
            return []
        
        # Check if cache is valid
        current_mtime = self.data_path.stat().st_mtime
        if self._cache is not None and self._cache_mtime == current_mtime:
            logger.debug("Using cached supplier data")
            return self._cache
        
        # Load data from file
        logger.info(f"Loading supplier data from {self.data_path}")
        suppliers = []
        
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        supplier = json.loads(line)
                        suppliers.append(supplier)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON on line {line_num}: {e}")
                        continue
            
            # Update cache
            self._cache = suppliers
            self._cache_mtime = current_mtime
            
            logger.info(f"Loaded {len(suppliers)} suppliers")
            return suppliers
            
        except Exception as e:
            logger.error(f"Error loading supplier data: {e}", exc_info=True)
            return []
    
    def filter_suppliers(
        self,
        suppliers: List[Dict[str, Any]],
        search: Optional[str] = None,
        country: Optional[str] = None,
        city: Optional[str] = None,
        supplier_type: Optional[str] = None,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Filter and sort suppliers based on criteria.
        
        Args:
            suppliers: List of supplier dictionaries
            search: Search term for name, ID, email
            country: Filter by country
            city: Filter by city/region
            supplier_type: Filter by supplier or buyer type
            sort_by: Field to sort by (date, name, id)
            sort_order: Sort order (asc, desc)
            
        Returns:
            Filtered and sorted list of suppliers
        """
        # Create a shallow copy to avoid modifying the cache in-place
        filtered = list(suppliers)
        
        # Search filter
        if search:
            search_lower = search.lower()
            filtered = [
                s for s in filtered
                if (
                    search_lower in (s.get('supplier', {}).get('name') or '').lower() or
                    search_lower in (s.get('supplier', {}).get('identification_code') or '').lower() or
                    search_lower in (s.get('supplier', {}).get('email') or '').lower()
                )
            ]
        
        # Country filter
        if country:
            filtered = [
                s for s in filtered
                if s.get('supplier', {}).get('country', '').lower() == country.lower()
            ]
        
        # City filter
        if city:
            city_lower = city.lower()
            filtered = [
                s for s in filtered
                if city_lower in s.get('supplier', {}).get('city_or_region', '').lower()
            ]
        
        # Supplier type filter
        if supplier_type:
            filtered = [
                s for s in filtered
                if s.get('supplier_or_buyer_type', '').lower() == supplier_type.lower()
            ]
            
        # Sorting
        reverse = sort_order.lower() == "desc"
        
        if sort_by == "name":
            filtered.sort(
                key=lambda x: x.get('supplier', {}).get('name', '').lower(),
                reverse=reverse
            )
        elif sort_by == "id":
            filtered.sort(
                key=lambda x: x.get('supplier', {}).get('identification_code', ''),
                reverse=reverse
            )
        else:  # Default to date
            # Parse date string "DD.MM.YYYY" to comparable format
            def parse_date(d):
                try:
                    parts = d.split('.')
                    if len(parts) == 3:
                        return f"{parts[2]}-{parts[1]}-{parts[0]}"
                except:
                    pass
                return ""
                
            filtered.sort(
                key=lambda x: parse_date(x.get('registration_date', '')),
                reverse=reverse
            )
        
        return filtered
