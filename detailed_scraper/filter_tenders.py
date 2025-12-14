import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("filter_tenders")

def parse_date(date_str: str) -> datetime.date:
    if not date_str:
        return datetime.now().date()
    
    date_str = date_str.lower().strip()
    today = datetime.now().date()
    
    if date_str == 'today':
        return today
    elif date_str == 'tomorrow':
        return today + timedelta(days=1)
    elif date_str == 'yesterday':
        return today - timedelta(days=1)
    
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        logger.warning(f"Could not parse date: {date_str}, using today")
        return today

def filter_tenders(
    data_path: Path,
    days_threshold: int = 60,
    date_from: str = None,
    date_to: str = None,
    excluded_statuses: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter tenders based on status and deadline date.
    
    Args:
        data_path: Path to the main tenders.jsonl file.
        days_threshold: Number of days from now to include tenders based on deadline (used if date_to not provided).
        date_from: Start date string (YYYY-MM-DD or 'today'). Defaults to today.
        date_to: End date string (YYYY-MM-DD or 'today'). Defaults to today + days_threshold.
        excluded_statuses: List of statuses to exclude.
        
    Returns:
        List of filtered tender dictionaries.
    """
    if excluded_statuses is None:
        excluded_statuses = ["არ შედგა", "დასრულებულია უარყოფითი შედეგით", "შეწყვეტილია"]

    if not data_path.exists():
        logger.error(f"Data file not found: {data_path}")
        return []

    filtered_tenders = []
    total_tenders = 0
    skipped_status = 0
    skipped_date = 0
    skipped_parse_error = 0

    # Determine date range
    start_date = parse_date(date_from) if date_from else datetime.now().date()
    
    if date_to:
        end_date = parse_date(date_to)
    else:
        end_date = start_date + timedelta(days=days_threshold)
    
    logger.info(f"Filtering tenders with deadline between {start_date} and {end_date}")
    logger.info(f"Excluding statuses: {excluded_statuses}")

    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            total_tenders += 1
            try:
                record = json.loads(line)
                
                # 1. Check Status
                status = record.get('status', '').strip()
                if status in excluded_statuses:
                    skipped_status += 1
                    continue
                
                # 2. Check Deadline Date
                deadline_str = record.get('deadline_date')
                if not deadline_str:
                    skipped_date += 1
                    continue
                
                try:
                    deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                except ValueError:
                    skipped_date += 1
                    continue
                
                # Check if deadline is within range
                if start_date <= deadline_date <= end_date:
                    filtered_tenders.append(record)
                else:
                    skipped_date += 1
                    
            except json.JSONDecodeError:
                skipped_parse_error += 1
                continue

    logger.info(f"Total processed: {total_tenders}")
    logger.info(f"Skipped by status: {skipped_status}")
    logger.info(f"Skipped by date/deadline: {skipped_date}")
    logger.info(f"Skipped parse errors: {skipped_parse_error}")
    logger.info(f"Total matching tenders: {len(filtered_tenders)}")

    return filtered_tenders

if __name__ == "__main__":
    # Example usage
    project_root = Path(__file__).parent.parent
    data_file = project_root / "main_scrapper" / "data" / "tenders.jsonl"
    
    tenders = filter_tenders(data_file)
    
    # Print first 5 for verification
    print(json.dumps(tenders[:5], indent=2, ensure_ascii=False))
