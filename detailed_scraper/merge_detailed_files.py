#!/usr/bin/env python3
"""
Merge Detailed Files
-------------------
Merges all type-specific detailed tender files (e.g., con_detailed_tenders.jsonl)
into the single aggregate file (detailed_tenders.jsonl) used by the backend.

This ensures that updates made by type-specific scrapers are visible to the application.
"""

import json
import logging
import sys
import shutil
import fcntl
from pathlib import Path
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('merge_files')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "main_scrapper" / "data"

AGGREGATE_FILE = DATA_DIR / "detailed_tenders.jsonl"

def get_tender_id(record: Dict[str, Any]) -> str:
    """Extract standard tender ID from record."""
    return (
        record.get("procurement_number") or 
        record.get("number") or 
        record.get("tender_number") or 
        ""
    ).upper()

def load_file_content(file_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load JSONL file content into a dictionary keyed by tender ID."""
    data = {}
    if not file_path.exists():
        return data
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    record = json.loads(line)
                    tid = get_tender_id(record)
                    if tid:
                        data[tid] = record
                except:
                    continue
    except Exception as e:
        logger.error(f"Error reading {file_path.name}: {e}")
        
    return data

def merge_files():
    """Main merge logic."""
    logger.info("=" * 60)
    logger.info("🔄 STARTING MERGE: Split Files -> detailed_tenders.jsonl")
    logger.info("=" * 60)
    
    # 1. Load existing aggregate data
    aggregate_data = load_file_content(AGGREGATE_FILE)
    logger.info(f"Loaded {len(aggregate_data)} records from {AGGREGATE_FILE.name}")
    
    # 2. Iterate through specific files and merge
    # We look for pattern *_detailed_tenders.jsonl, excluding the aggregate itself
    source_files = list(DATA_DIR.glob("*_detailed_tenders.jsonl"))
    
    updates_count = 0
    new_count = 0
    
    for src in source_files:
        if src.name == AGGREGATE_FILE.name:
            continue
            
        logger.info(f"Processing {src.name}...")
        src_data = load_file_content(src)
        
        for tid, record in src_data.items():
            if tid in aggregate_data:
                # Simple logic: Overwrite with data from specific files
                # Assuming specific files are the source of truth for updates
                # We could add timestamp check if 'scraped_at' is reliable
                aggregate_data[tid] = record
                updates_count += 1
            else:
                aggregate_data[tid] = record
                new_count += 1
                
    logger.info(f"Merge summary: {new_count} new records, {updates_count} updates/overwrites")
    
    # 3. Write back to aggregate file safely
    temp_file = AGGREGATE_FILE.with_suffix('.tmp')
    
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            # Lock file for writing
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                for record in aggregate_data.values():
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        # Atomic move
        shutil.move(temp_file, AGGREGATE_FILE)
        logger.info(f"✅ Successfully wrote {len(aggregate_data)} records to {AGGREGATE_FILE.name}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save merged file: {e}")
        if temp_file.exists():
            temp_file.unlink()
            
if __name__ == "__main__":
    merge_files()
