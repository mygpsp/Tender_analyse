"""API routes for CON tender operations."""
import logging
import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from pathlib import Path
import io
import csv

from ..models.con_tender import (
    ConTenderListResponse,
    ConTenderItem,
    ConTenderStats
)
from ..services.con_tender_service import ConTenderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/con-tenders", tags=["con-tenders"])

# Initialize service
_data_path = Path(__file__).parent.parent.parent.parent / "main_scrapper" / "data"
con_service = ConTenderService(_data_path)


@router.get("", response_model=ConTenderListResponse)
async def list_con_tenders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
):
    """
    List CON tenders with pagination and filtering.
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - date_from: Filter from date (YYYY-MM-DD)
    - date_to: Filter to date (YYYY-MM-DD)
    - status: Filter by status
    - region: Filter by region
    - search: Search query
    """
    try:
        # Load and filter tenders
        tenders = con_service.load_con_tenders(
            date_from=date_from,
            date_to=date_to,
            status=status,
            region=region,
            search=search
        )
        
        # Enrich with detailed data
        tenders = con_service.enrich_with_detailed_data(tenders)
        
        # Calculate pagination
        total = len(tenders)
        pages = (total + page_size - 1) // page_size
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tenders = tenders[start_idx:end_idx]
        
        # Format response
        items = [
            ConTenderItem(
                number=t.get('number', ''),
                buyer=t.get('buyer', ''),
                status=t.get('status', ''),
                published_date=t.get('published_date', ''),
                deadline_date=t.get('deadline_date'),
                amount=t.get('amount'),
                final_price=t.get('final_price'),
                winner_name=t.get('winner_name'),
                region=t.get('region'),
                category=t.get('category'),
                detail_url=t.get('detail_url')
            )
            for t in paginated_tenders
        ]
        
        return ConTenderListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
    except Exception as e:
        logger.error(f"Error listing CON tenders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ConTenderStats)
async def get_con_tender_stats(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
):
    """
    Get statistics for CON tenders.
    
    Query Parameters:
    - date_from: Filter from date (YYYY-MM-DD)
    - date_to: Filter to date (YYYY-MM-DD)
    - status: Filter by status
    - region: Filter by region
    """
    try:
        # Load and filter tenders
        tenders = con_service.load_con_tenders(
            date_from=date_from,
            date_to=date_to,
            status=status,
            region=region
        )
        
        # Enrich with detailed data
        tenders = con_service.enrich_with_detailed_data(tenders)
        
        # Calculate statistics
        stats = con_service.get_statistics(tenders)
        
        return ConTenderStats(**stats)
    except Exception as e:
        logger.error(f"Error getting CON tender stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_con_tenders(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
):
    """
    Export CON tenders to CSV.
    
    Query Parameters:
    - date_from: Filter from date (YYYY-MM-DD)
    - date_to: Filter to date (YYYY-MM-DD)
    - status: Filter by status
    - region: Filter by region
    """
    try:
        # Load and filter tenders
        tenders = con_service.load_con_tenders(
            date_from=date_from,
            date_to=date_to,
            status=status,
            region=region
        )
        
        # Enrich with detailed data
        tenders = con_service.enrich_with_detailed_data(tenders)
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Tender Number',
            'Date Bidding',
            'Initial Price (GEL)',
            'Final Price (GEL)',
            'Winner',
            'Region',
            'Status',
            'Buyer',
            'Category'
        ])
        
        # Write data
        for t in tenders:
            writer.writerow([
                t.get('number', ''),
                t.get('published_date', ''),
                t.get('amount', ''),
                t.get('final_price', ''),
                t.get('winner_name', ''),
                t.get('region', ''),
                t.get('status', ''),
                t.get('buyer', ''),
                t.get('category', '')
            ])
        
        # Return as downloadable file
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=con_tenders_export.csv"
            }
        )
    except Exception as e:
        logger.error(f"Error exporting CON tenders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-detailed")
async def export_con_tenders_detailed(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
):
    """
    Export CON tenders with ALL detailed data to CSV.
    
    Query Parameters:
    - date_from: Filter from date (YYYY-MM-DD)
    - date_to: Filter to date (YYYY-MM-DD)
    - status: Filter by status
    - region: Filter by region
    """
    try:
        # Load and filter tenders
        tenders = con_service.load_con_tenders(
            date_from=date_from,
            date_to=date_to,
            status=status,
            region=region
        )
        
        # Enrich with detailed data
        tenders = con_service.enrich_with_detailed_data(tenders)
        
        # Load full detailed data
        detailed_data = {}
        detailed_file = con_service.detailed_file
        if detailed_file.exists():
            with open(detailed_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        detail = json.loads(line)
                        number = detail.get('procurement_number')
                        if number:
                            detailed_data[number] = detail
                    except json.JSONDecodeError:
                        continue
        
        # Create CSV with all fields
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write comprehensive header
        writer.writerow([
            'Tender Number',
            'Date Bidding',
            'Deadline Date',
            'Initial Price (GEL)',
            'Final Price (GEL)',
            'Winner',
            'Region',
            'Status',
            'Buyer',
            'Category',
            'Title',
            'Description',
            'Additional Information',
            'Estimated Value',
            'Winner Amount',
            'Winner Supplier',
            'Lowest Bidder Amount',
            'Lowest Bidder Supplier',
            'Buyer Contact Name',
            'Buyer Contact Email',
            'Buyer Contact Phone',
            'Documents Count',
            'Document Names',
            'Delivery Address',
            'Delivery Terms',
            'Payment Terms',
            'Tender ID',
            'Detail URL'
        ])
        
        # Write data
        for t in tenders:
            tender_number = t.get('number', '')
            detail = detailed_data.get(tender_number, {})
            
            # Extract all fields
            winner = detail.get('winner', {})
            lowest_bidder = detail.get('lowest_bidder', {})
            buyer_contacts = detail.get('buyer_contacts', {})
            delivery_terms = detail.get('delivery_terms', {})
            documents = detail.get('documents', [])
            doc_names = '; '.join([d.get('name', '') for d in documents[:10]])  # First 10 docs
            
            writer.writerow([
                tender_number,
                t.get('published_date', ''),
                t.get('deadline_date', ''),
                t.get('amount', ''),
                t.get('final_price', ''),
                t.get('winner_name', ''),
                t.get('region', ''),
                t.get('status', ''),
                t.get('buyer', ''),
                t.get('category', ''),
                detail.get('title', ''),
                detail.get('description', ''),
                detail.get('additional_information', ''),
                detail.get('estimated_value', ''),
                winner.get('amount', ''),
                winner.get('supplier', ''),
                lowest_bidder.get('amount', ''),
                lowest_bidder.get('supplier', ''),
                buyer_contacts.get('name', ''),
                buyer_contacts.get('email', ''),
                buyer_contacts.get('phone', ''),
                len(documents),
                doc_names,
                delivery_terms.get('delivery_address', ''),
                delivery_terms.get('delivery_terms', ''),
                detail.get('payment_terms', ''),
                t.get('tender_id', ''),
                t.get('detail_url', '')
            ])
        
        # Return as downloadable file
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=con_tenders_detailed_export.csv"
            }
        )
    except Exception as e:
        logger.error(f"Error exporting detailed CON tenders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
