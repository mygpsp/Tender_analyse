"""API routes for supplier operations."""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pathlib import Path

from ..models.supplier import (
    SupplierListResponse,
    SupplierResponse
)
from ..services.supplier_loader import SupplierLoader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

# Initialize supplier loader - data path relative to project root
_data_path = Path(__file__).parent.parent.parent.parent / "Supplier_scrapping" / "data" / "suppliers.jsonl"
supplier_loader = SupplierLoader(_data_path)


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None, description="Search by name, ID, or email"),
    country: Optional[str] = Query(default=None, description="Filter by country"),
    city: Optional[str] = Query(default=None, description="Filter by city/region"),
    supplier_type: Optional[str] = Query(default=None, description="Filter by supplier or buyer type"),
    sort_by: str = Query(default="date", description="Sort by: date, name, id"),
    sort_order: str = Query(default="desc", description="Sort order: asc, desc")
):
    """
    List suppliers with pagination and filtering.
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - search: Search term for name, ID, or email
    - country: Filter by country
    - city: Filter by city/region
    - supplier_type: Filter by supplier or buyer type (e.g., "მიმწოდებელი")
    - sort_by: Sort field (date, name, id)
    - sort_order: Sort order (asc, desc)
    """
    try:
        # Load data
        all_suppliers = supplier_loader.load_data()
        
        # Apply filters
        filtered_suppliers = supplier_loader.filter_suppliers(
            all_suppliers,
            search=search,
            country=country,
            city=city,
            supplier_type=supplier_type,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Calculate pagination
        total = len(filtered_suppliers)
        pages = (total + page_size - 1) // page_size
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_suppliers = filtered_suppliers[start_idx:end_idx]
        
        # Format response
        items = [
            SupplierResponse(id=idx, supplier=supplier)
            for idx, supplier in enumerate(paginated_suppliers, start=start_idx + 1)
        ]
        
        return SupplierListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
    except Exception as e:
        logger.error(f"Error listing suppliers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: int):
    """
    Get a specific supplier by ID.
    
    Args:
        supplier_id: Supplier ID (1-indexed position in dataset)
    """
    try:
        all_suppliers = supplier_loader.load_data()
        
        if supplier_id < 1 or supplier_id > len(all_suppliers):
            raise HTTPException(
                status_code=404,
                detail=f"Supplier with ID {supplier_id} not found"
            )
        
        supplier = all_suppliers[supplier_id - 1]
        return SupplierResponse(id=supplier_id, supplier=supplier)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting supplier {supplier_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_supplier_stats():
    """
    Get summary statistics about suppliers.
    
    Returns:
        Dictionary with supplier statistics
    """
    try:
        all_suppliers = supplier_loader.load_data()
        
        # Calculate statistics
        total_suppliers = len(all_suppliers)
        
        # Count by country
        countries = {}
        cities = {}
        supplier_types = {}
        
        for supplier in all_suppliers:
            supplier_info = supplier.get('supplier', {})
            
            # Count countries
            country = supplier_info.get('country', 'Unknown')
            countries[country] = countries.get(country, 0) + 1
            
            # Count cities
            city = supplier_info.get('city_or_region', 'Unknown')
            cities[city] = cities.get(city, 0) + 1
            
            # Count supplier types
            s_type = supplier.get('supplier_or_buyer_type', 'Unknown')
            supplier_types[s_type] = supplier_types.get(s_type, 0) + 1
        
        return {
            "total_suppliers": total_suppliers,
            "by_country": dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_city": dict(sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_type": supplier_types
        }
    except Exception as e:
        logger.error(f"Error getting supplier stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
