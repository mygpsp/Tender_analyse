"""
API endpoints for detailed tender data.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pathlib import Path

from ..services.detail_loader import DetailLoader
from ..models.tender import TenderResponse

router = APIRouter(prefix="/api/detailed-tenders", tags=["detailed-tenders"])

# Initialize detail loader
# Initialize detail loader
DATA_DIR = Path(__file__).parent.parent.parent.parent / "main_scrapper" / "data"
DETAILED_DATA_PATH = DATA_DIR / "detailed_tenders.jsonl"
detail_loader = DetailLoader(DETAILED_DATA_PATH)


@router.get("/list")
async def list_detailed_tenders(
    tender_number: Optional[str] = Query(None, description="Filter by tender number"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> dict:
    """
    List detailed tender records.
    
    Args:
        tender_number: Optional filter by tender number
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        Dictionary with list of detailed tenders and pagination info
    """
    all_data = detail_loader.get_all()
    
    # Filter by tender number if provided
    if tender_number:
        tender_number_upper = tender_number.upper()
        all_data = [
            record for record in all_data
            if (
                record.get("tender_number", "").upper() == tender_number_upper or
                record.get("procurement_number", "").upper() == tender_number_upper or
                record.get("number", "").upper() == tender_number_upper
            )
        ]
    
    # Paginate
    total = len(all_data)
    paginated_data = all_data[offset:offset + limit]
    
    return {
        "items": paginated_data,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


@router.get("/browse")
async def browse_detailed_tenders(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(1, ge=1, le=10, description="Number of records to return"),
) -> dict:
    """
    Browse detailed tender records one by one.
    
    Args:
        offset: Offset for pagination (which tender to start from)
        limit: Number of records to return (typically 1 for browsing)
        
    Returns:
        Dictionary with tender data, total count, and pagination info
    """
    all_data = detail_loader.get_all()
    total = len(all_data)
    
    # Get the requested slice
    paginated_data = all_data[offset:offset + limit]
    
    return {
        "items": paginated_data,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_previous": offset > 0,
        "has_next": offset + limit < total,
    }


@router.get("/search")
async def search_detailed_tenders(
    query: str = Query(..., min_length=3, description="Text to search for"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results")
) -> dict:
    """
    Search for text across all fields in detailed tender data.
    Results are sorted by date (newest first).
    
    Args:
        query: Text to search for (case-insensitive)
        limit: Maximum number of results
        
    Returns:
        Dictionary with matching items and count
    """
    import json
    from datetime import datetime
    
    # Force reload to ensure we search latest data
    detail_loader.load_data(force_reload=True)
    all_data = detail_loader.get_all()
    
    query_lower = query.lower()
    matches = []
    
    for record in all_data:
        # Convert record to string for full-text search
        # This is a simple but effective way to search across all fields
        record_str = json.dumps(record, ensure_ascii=False).lower()
        
        if query_lower in record_str:
            matches.append(record)
    
    # Sort by date (newest first)
    def get_sort_date(record):
        """Extract date for sorting - try published_date, then deadline_date, then empty string"""
        date_str = record.get('published_date') or record.get('deadline_date') or ''
        if date_str:
            try:
                # Try to parse the date for proper sorting
                return datetime.strptime(date_str, '%Y-%m-%d')
            except:
                # If parsing fails, return the string (will sort alphabetically)
                return date_str
        return datetime.min  # Put records without dates at the end
    
    matches.sort(key=get_sort_date, reverse=True)
    
    # Apply limit after sorting
    matches = matches[:limit]
    
    return {
        "items": matches,
        "total": len(matches),
        "query": query
    }


@router.get("/tender-numbers")
async def get_tender_numbers_with_details() -> dict:
    """
    Get list of all tender numbers that have detailed data.
    
    Returns:
        Dictionary with list of tender numbers
    """
    # Force reload to get latest data
    detail_loader.load_data(force_reload=True)
    tender_numbers = detail_loader.get_tender_numbers_with_details()
    return {
        "tender_numbers": sorted(list(tender_numbers)),
        "count": len(tender_numbers),
    }


@router.get("/{tender_number}")
async def get_detailed_tender(tender_number: str) -> dict:
    """
    Get detailed data for a specific tender.
    
    Args:
        tender_number: Tender number (e.g., "GEO250000579")
        
    Returns:
        Detailed tender data
    """
    # Don't treat "tender-numbers" as a tender number
    if tender_number == "tender-numbers":
        raise HTTPException(status_code=404, detail="Invalid tender number")
    
    # Force reload to ensure we have latest data
    detail_loader.load_data(force_reload=True)
    detail_data = detail_loader.get_by_tender_number(tender_number)
    
    if not detail_data:
        raise HTTPException(
            status_code=404,
            detail=f"Detailed data not found for tender {tender_number}"
        )
    
    return detail_data


@router.delete("/{tender_number}")
async def delete_detailed_tender(tender_number: str) -> dict:
    """
    Delete detailed data for a specific tender number.
    This removes the record from the JSONL file.
    
    Args:
        tender_number: Tender number to delete (e.g., "GEO250000579")
        
    Returns:
        Status message
    """
    import json
    import shutil
    from pathlib import Path
    
    if not DETAILED_DATA_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Detailed tenders file not found"
        )
    
    # Read all records, filter out the one to delete
    records_to_keep = []
    deleted = False
    
    with open(DETAILED_DATA_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line.strip())
                if record.get("tender_number", "").upper() != tender_number.upper():
                    records_to_keep.append(line.strip())
                else:
                    deleted = True
            except json.JSONDecodeError:
                # Skip invalid JSON lines
                continue
    
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Detailed data not found for tender {tender_number}"
        )
    
    # Create backup
    backup_path = DETAILED_DATA_PATH.with_suffix('.jsonl.bak')
    shutil.copy(DETAILED_DATA_PATH, backup_path)
    
    # Write back all records except the deleted one
    with open(DETAILED_DATA_PATH, 'w', encoding='utf-8') as f:
        for record_line in records_to_keep:
            f.write(record_line + '\n')
    
    # Clear cache first, then reload to ensure fresh data
    detail_loader.clear_cache()
    detail_loader.load_data(force_reload=True)
    
    return {
        "status": "success",
        "message": f"Detailed data deleted for tender {tender_number}",
        "tender_number": tender_number,
    }


@router.post("/reload")
async def reload_detailed_data() -> dict:
    """
    Reload detailed tender data from file.
    
    Returns:
        Status message
    """
    detail_loader.load_data(force_reload=True)
    return {
        "status": "success",
        "message": "Detailed tender data reloaded",
        "count": len(detail_loader.get_all()),
    }

