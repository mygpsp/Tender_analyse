"""API routes for tender operations."""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pathlib import Path

from ..models.tender import (
    TenderListResponse,
    TenderResponse,
    TenderFilters
)
from ..services.data_loader import DataLoader
from ..services.analytics import AnalyticsService
from ..services.detail_loader import DetailLoader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tenders", tags=["tenders"])

# Initialize services - data path relative to project root
_data_path = Path(__file__).parent.parent.parent.parent / "main_scrapper" / "data"

# Load all tenders (not filtered)
data_loader = DataLoader(_data_path)
analytics_service = AnalyticsService(data_loader)

# Initialize detail loader for checking detailed data availability
_detailed_data_path = _data_path / "detailed_tenders.jsonl"
detail_loader = DetailLoader(_detailed_data_path)


@router.get("", response_model=TenderListResponse)
async def list_tenders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=10000),
    buyer: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    filter_by_published_date: bool = Query(default=True, description="Filter by published date"),
    filter_by_deadline_date: bool = Query(default=True, description="Filter by deadline date"),
    search: Optional[str] = Query(default=None),
    amount_min: Optional[float] = Query(default=None),
    amount_max: Optional[float] = Query(default=None),
    tender_number: Optional[str] = Query(default=None, description="Filter by tender number (e.g., GEO250000579)"),
    has_detailed_data: Optional[bool] = Query(default=None, description="Filter by detailed data availability (true = only with details, false = only without details)"),
    sort_by: str = Query(default="deadline_date", description="Field to sort by (published_date, deadline_date, amount)"),
    sort_order: str = Query(default="asc", description="Sort order (asc, desc)")
):
    """
    List tenders with pagination and filtering.
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 10000)
    - buyer: Filter by buyer name
    - status: Filter by status
    - date_from: Filter from date (YYYY-MM-DD)
    - date_to: Filter to date (YYYY-MM-DD)
    - search: Full-text search query
    - has_detailed_data: Filter by detailed data availability
    - sort_by: Field to sort by (default: deadline_date)
    - sort_order: Sort order (default: asc)
    """
    try:
        # Load data
        all_tenders = data_loader.load_data()
        
        # Get tender numbers with detailed data if filtering by detailed data
        tender_numbers_with_details = None
        if has_detailed_data is not None:
            tender_numbers_with_details = detail_loader.get_tender_numbers_with_details()
        
        # Apply filters
        filtered_tenders = analytics_service.filter_tenders(
            all_tenders,
            buyer=buyer,
            status=status,
            date_from=date_from,
            date_to=date_to,
            filter_by_published_date=filter_by_published_date,
            filter_by_deadline_date=filter_by_deadline_date,
            search=search,
            amount_min=amount_min,
            amount_max=amount_max,
            tender_number=tender_number,
            has_detailed_data=has_detailed_data,
            tender_numbers_with_details=tender_numbers_with_details
        )
        
        # Calculate pagination
        total = len(filtered_tenders)
        pages = (total + page_size - 1) // page_size
        
        # Sort logic
        def get_sort_value(tender):
            val = tender.get(sort_by)
            # Handle None/Empty values for correct sorting
            if val is None or val == "":
                # Push empty values to end regardless of sort order usually, 
                # or treat as high/low? 
                # For dates: '0000-00-00' or '9999-99-99'? 
                # Let's use '9999-99-99' for ASC so they go to end, '0000-00-00' for DESC so they go to end?
                # Actually, standard string comparison '0' is small.
                return '0000-00-00' if sort_by in ['published_date', 'deadline_date'] else 0
            return val
        
        reverse = (sort_order.lower() == 'desc')
        filtered_tenders.sort(key=get_sort_value, reverse=reverse)
        
        # Apply pagination AFTER sorting
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tenders = filtered_tenders[start_idx:end_idx]
        
        # Normalize tender data before creating response (convert None to empty string for required fields)
        def normalize_tender(tender: dict) -> dict:
            """Normalize tender data to ensure required string fields are not None."""
            normalized = tender.copy()
            # Ensure required string fields are not None
            for field in ['number', 'buyer', 'supplier', 'status', 'all_cells']:
                if normalized.get(field) is None:
                    normalized[field] = ""
            
            # Helper to safely convert to string
            def safe_str(val):
                if val is None: return None
                if isinstance(val, float):
                    return str(int(val)) # Remove .0
                return str(val)

            # Convert ID and Category Code
            if 'tender_id' in normalized:
                normalized['tender_id'] = safe_str(normalized.get('tender_id'))
            
            if 'category_code' in normalized:
                normalized['category_code'] = safe_str(normalized.get('category_code'))
                
            return normalized
        
        # Format response
        items = [
            TenderResponse(id=idx, tender=normalize_tender(tender))
            for idx, tender in enumerate(paginated_tenders, start=start_idx + 1)
        ]
        
        return TenderListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
    except Exception as e:
        logger.error(f"Error listing tenders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender(tender_id: int):
    """
    Get a specific tender by ID.
    
    Args:
        tender_id: Tender ID (1-indexed position in dataset)
    """
    try:
        all_tenders = data_loader.load_data()
        
        if tender_id < 1 or tender_id > len(all_tenders):
            raise HTTPException(
                status_code=404,
                detail=f"Tender with ID {tender_id} not found"
            )
        
        # Normalize tender data before creating response (convert None to empty string for required fields)
        def normalize_tender(tender: dict) -> dict:
            """Normalize tender data to ensure required string fields are not None."""
            normalized = tender.copy()
            # Ensure required string fields are not None
            for field in ['number', 'buyer', 'supplier', 'status', 'all_cells']:
                if normalized.get(field) is None:
                    normalized[field] = ""
            
            # Helper to safely convert to string
            def safe_str(val):
                if val is None: return None
                if isinstance(val, float):
                    return str(int(val)) # Remove .0
                return str(val)

            # Convert ID and Category Code
            if 'tender_id' in normalized:
                normalized['tender_id'] = safe_str(normalized.get('tender_id'))
            
            if 'category_code' in normalized:
                normalized['category_code'] = safe_str(normalized.get('category_code'))
                
            return normalized
        
        tender = all_tenders[tender_id - 1]
        return TenderResponse(id=tender_id, tender=normalize_tender(tender))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tender {tender_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tender_id}/similar", response_model=TenderListResponse)
async def get_similar_tenders(
    tender_id: int,
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of similar tenders to return")
):
    """
    Find similar tenders based on same buyer AND same category.
    
    Args:
        tender_id: Source tender ID
        limit: Maximum number of results (default: 50, max: 100)
        
    Returns:
        List of tenders with matching buyer and category, sorted by published date (newest first)
    """
    try:
        all_tenders = data_loader.load_data()
        
        # Get source tender
        if tender_id < 1 or tender_id > len(all_tenders):
            raise HTTPException(
                status_code=404,
                detail=f"Tender with ID {tender_id} not found"
            )
        
        source_tender = all_tenders[tender_id - 1]
        source_buyer = source_tender.get('buyer', '').strip()
        source_category = source_tender.get('category', '').strip()
        
        # Validate that source tender has buyer and category
        if not source_buyer or not source_category:
            return TenderListResponse(
                items=[],
                total=0,
                page=1,
                page_size=limit,
                pages=0
            )
        
        # Find similar tenders
        similar_tenders = []
        for idx, tender in enumerate(all_tenders, start=1):
            # Skip the source tender itself
            if idx == tender_id:
                continue
            
            tender_buyer = tender.get('buyer', '').strip()
            tender_category = tender.get('category', '').strip()
            
            # Match both buyer AND category (case-insensitive)
            if (tender_buyer.lower() == source_buyer.lower() and 
                tender_category.lower() == source_category.lower()):
                similar_tenders.append((idx, tender))
        
        # Sort by published_date descending (newest first)
        def get_published_date(item):
            tender = item[1]
            pub_date = tender.get('published_date')
            if pub_date:
                return pub_date
            return '0000-00-00'  # Put tenders without date at the end
        
        similar_tenders.sort(key=get_published_date, reverse=True)
        
        # Apply limit
        similar_tenders = similar_tenders[:limit]
        
        # Normalize tender data
        def normalize_tender(tender: dict) -> dict:
            """Normalize tender data to ensure required string fields are not None."""
            normalized = tender.copy()
            for field in ['number', 'buyer', 'supplier', 'status', 'all_cells']:
                if normalized.get(field) is None:
                    normalized[field] = ""
            return normalized
        
        # Format response
        items = [
            TenderResponse(id=idx, tender=normalize_tender(tender))
            for idx, tender in similar_tenders
        ]
        
        total = len(similar_tenders)
        
        return TenderListResponse(
            items=items,
            total=total,
            page=1,
            page_size=limit,
            pages=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar tenders for {tender_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

