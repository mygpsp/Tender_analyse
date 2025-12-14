"""
Service for loading detailed tender data from JSONL files.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("detail_loader")


class DetailLoader:
    """Loads detailed tender data from JSONL files."""
    
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_loaded = False
    
    def load_data(self, force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Load detailed tender data from JSONL file.
        
        Args:
            force_reload: If True, reload from file even if cache exists
            
        Returns:
            Dictionary mapping tender_number to detailed data
        """
        if self._cache_loaded and not force_reload:
            return self._cache
        
        self._cache = {}
        
        if not self.data_path.exists():
            logger.warning(f"Detailed tenders file not found: {self.data_path}")
            return self._cache
        
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    
                    try:
                        record = json.loads(line.strip())
                        # Try multiple field names for tender number (new structure uses procurement_number)
                        tender_number = (
                            record.get("tender_number") or 
                            record.get("procurement_number") or 
                            record.get("number")
                        )
                        
                        if not tender_number:
                            logger.warning(f"Record {line_num} missing tender number (checked: tender_number, procurement_number, number), skipping")
                            continue
                        
                        # Normalize tender number to uppercase for consistent lookup
                        tender_number_upper = tender_number.upper()
                        
                        # Store by tender number (uppercase)
                        # If duplicate, keep the one with more complete data
                        if tender_number_upper in self._cache:
                            existing = self._cache[tender_number]
                            existing_has_basic = bool(existing.get("basic_info"))
                            new_has_basic = bool(record.get("basic_info"))
                            
                            # Prefer record with basic_info
                            if new_has_basic and not existing_has_basic:
                                self._cache[tender_number_upper] = record
                            elif existing_has_basic and not new_has_basic:
                                # Keep existing if it has basic_info and new doesn't
                                pass
                            elif new_has_basic and existing_has_basic:
                                # Both have basic_info - prefer one with valid buyer (not search hint)
                                new_buyer = record.get("basic_info", {}).get("buyer", "")
                                existing_buyer = existing.get("basic_info", {}).get("buyer", "")
                                
                                # Check if buyer is valid (not a search hint)
                                is_valid_buyer = lambda b: b and not b.startswith("(") and len(b) > 5
                                
                                if is_valid_buyer(new_buyer) and not is_valid_buyer(existing_buyer):
                                    self._cache[tender_number_upper] = record
                                elif is_valid_buyer(existing_buyer) and not is_valid_buyer(new_buyer):
                                    # Keep existing
                                    pass
                                else:
                                    # Both valid or both invalid - prefer more recent
                                    if record.get("scraped_at", 0) > existing.get("scraped_at", 0):
                                        self._cache[tender_number_upper] = record
                            else:
                                # Neither has basic_info - prefer more recent
                                if record.get("scraped_at", 0) > existing.get("scraped_at", 0):
                                    self._cache[tender_number_upper] = record
                        else:
                            self._cache[tender_number_upper] = record
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON on line {line_num}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing line {line_num}: {e}")
                        continue
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._cache)} detailed tender records")
            
        except Exception as e:
            logger.error(f"Error loading detailed tenders: {e}")
        
        return self._cache
    
    def get_by_tender_number(self, tender_number: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed data for a specific tender number.
        
        Args:
            tender_number: Tender number (e.g., "GEO250000579")
            
        Returns:
            Detailed tender data or None if not found
        """
        if not self._cache_loaded:
            self.load_data()
        
        # Normalize to uppercase for case-insensitive lookup
        tender_number_upper = tender_number.upper()
        
        # Try exact match first
        if tender_number_upper in self._cache:
            return self._cache[tender_number_upper]
        
        # Try case-insensitive lookup in cache keys
        for key, value in self._cache.items():
            if key.upper() == tender_number_upper:
                return value
        
        # Try searching in record fields (procurement_number, number, tender_number)
        for record in self._cache.values():
            record_num = (
                record.get("procurement_number") or 
                record.get("number") or 
                record.get("tender_number")
            )
            if record_num and record_num.upper() == tender_number_upper:
                return record
        
        return None
    
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all detailed tender records.
        
        Returns:
            List of all detailed tender records
        """
        if not self._cache_loaded:
            self.load_data()
        
        return list(self._cache.values())
    
    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache = {}
        self._cache_loaded = False
        logger.info("Detail loader cache cleared")
    
    def get_tender_numbers_with_details(self) -> set:
        """
        Get a set of all tender numbers that have detailed data.
        
        Returns:
            Set of tender numbers (strings) - normalized to uppercase
        """
        if not self._cache_loaded:
            self.load_data()
        
        # Return uppercase keys (which is how they're stored)
        return set(self._cache.keys())

