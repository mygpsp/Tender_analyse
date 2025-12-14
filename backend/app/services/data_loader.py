"""Service for loading and managing tender data from JSONL files."""
import json
import logging
import re
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataLoader:
    """Loads and caches tender data from JSONL files."""
    
    def __init__(self, data_dir: Path = Path("main_scrapper/data"), data_file: Optional[str] = None):
        self.data_dir = Path(data_dir)
        # Allow specifying a specific file to load (e.g., con_tenders_2020_60100000.jsonl)
        # If not specified, loads all .jsonl files in directory
        self.data_file = data_file
        self._cache: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: Optional[float] = None
    
    def load_data(self, force_reload: bool = False) -> List[Dict[str, Any]]:
        """
        Load tender data from JSONL files.
        
        Args:
            force_reload: If True, reload data even if cached
            
        Returns:
            List of tender records
        """
        if self._cache is not None and not force_reload:
            return self._cache
        
        tenders = []
        
        # If specific file is configured, load only that file
        if self.data_file:
            jsonl_files = [self.data_dir / self.data_file]
            if not jsonl_files[0].exists():
                logger.error(f"Configured data file not found: {jsonl_files[0]}")
                return tenders
        else:
            # Get all JSONL files but exclude backup files
            all_jsonl_files = list(self.data_dir.glob("*.jsonl"))
            jsonl_files = [
                f for f in all_jsonl_files 
                if not f.name.startswith("tenders.backup.") 
                and f.name != "detailed_tenders.jsonl"  # Exclude detailed tenders file
            ]
        
        if not jsonl_files:
            logger.warning(f"No JSONL files found in {self.data_dir}")
            return tenders
        
        for jsonl_file in jsonl_files:
            logger.info(f"Loading data from {jsonl_file}")
            try:
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            # Filter out invalid records (header rows, etc.)
                            if self._is_valid_record(record):
                                tenders.append(record)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON at line {line_num} in {jsonl_file}: {e}")
                            continue
            except Exception as e:
                logger.error(f"Error reading {jsonl_file}: {e}")
                continue
        
        # Deduplicate tenders by all fields (excluding metadata)
        deduplicated = self._deduplicate_tenders(tenders)
        duplicates_removed = len(tenders) - len(deduplicated)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate tender records")
        
        self._cache = deduplicated
        self._cache_timestamp = datetime.now().timestamp()
        logger.info(f"Loaded {len(deduplicated)} unique tender records")
        return deduplicated
    
    def _is_valid_record(self, record: Dict[str, Any]) -> bool:
        """Check if a record is valid (not a header or invalid row)."""
        # Filter out records that look like header rows or navigation elements
        number = record.get("number", "").strip()
        buyer = record.get("buyer", "").strip()
        
        # Skip if number contains navigation elements (but NOT if it's a valid tender number)
        # Valid tender numbers are like CON250000525, CMR250000123, etc.
        # Navigation buttons are just "CON", "CMR", "SMP" without numbers
        if number:
            # Check if it's just a navigation button (no numbers, just text)
            if number in ["CMR", "CON", "SMP", "ePLAN", "MRS", "მომხმარებლები"]:
                return False
            # Check if it contains navigation text but is NOT a valid tender number pattern
            if "მომხმარებლები" in number:
                # If it's just the navigation text without a tender number, skip it
                if not re.search(r'[A-Z]{2,4}\d{9,}', number):
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
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached data."""
        return {
            "cached": self._cache is not None,
            "count": len(self._cache) if self._cache else 0,
            "timestamp": self._cache_timestamp
        }
    
    def _normalize_value(self, value: Any) -> Any:
        """Normalize a value for consistent comparison."""
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            # Sort keys for consistent ordering
            return {k: self._normalize_value(v) for k, v in sorted(value.items())}
        if isinstance(value, list):
            return [self._normalize_value(item) for item in value]
        return value

    def _get_record_signature(self, record: Dict[str, Any], exclude_metadata: bool = True) -> str:
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
                normalized[key] = self._normalize_value(value)
        
        # Create a deterministic JSON string (sorted keys)
        json_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        
        # Generate hash
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

    def _extract_tender_number(self, record: Dict[str, Any]) -> Optional[str]:
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
    
    def _deduplicate_tenders(self, tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate tenders based on all fields (excluding metadata).
        When duplicates are found, keeps the record with:
        1. Most recent scraped_at timestamp, or
        2. Most complete data (longer all_cells), or
        3. First occurrence
        """
        seen = {}  # record_signature -> best_record
        
        for record in tenders:
            # Generate signature from all fields (excluding metadata)
            signature = self._get_record_signature(record, exclude_metadata=True)
            
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
        
        return list(seen.values())
    
    def clear_cache(self):
        """Clear the data cache."""
        self._cache = None
        self._cache_timestamp = None
        logger.info("Cache cleared")

