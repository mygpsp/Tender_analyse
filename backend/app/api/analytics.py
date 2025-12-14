"""API routes for analytics operations."""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pathlib import Path

from ..models.tender import (
    AnalyticsSummary,
    BuyerAnalyticsResponse,
    CategoryAnalyticsResponse,
    WinnerAnalyticsResponse,
    TimelineResponse
)
from ..services.data_loader import DataLoader
from ..services.analytics import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Initialize services - data path relative to project root
_data_path = Path(__file__).parent.parent.parent.parent / "main_scrapper" / "data"
data_loader = DataLoader(_data_path)
analytics_service = AnalyticsService(data_loader)


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    buyer: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    filter_by_published_date: bool = Query(default=True, description="Filter by published date"),
    filter_by_deadline_date: bool = Query(default=True, description="Filter by deadline date"),
    search: Optional[str] = Query(default=None),
    amount_min: Optional[float] = Query(default=None),
    amount_max: Optional[float] = Query(default=None),
):
    """Get overall summary statistics with optional filters."""
    try:
        tenders = data_loader.load_data()
        # Apply filters if provided
        if any([buyer, status, date_from, date_to, search, amount_min, amount_max]):
            tenders = analytics_service.filter_tenders(
                tenders,
                buyer=buyer,
                status=status,
                date_from=date_from,
                date_to=date_to,
                filter_by_published_date=filter_by_published_date,
                filter_by_deadline_date=filter_by_deadline_date,
                search=search,
                amount_min=amount_min,
                amount_max=amount_max
            )
        summary = analytics_service.get_summary(tenders)
        return AnalyticsSummary(**summary)
    except Exception as e:
        logger.error(f"Error getting summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-buyer", response_model=BuyerAnalyticsResponse)
async def get_buyer_analytics(
    buyer: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
):
    """Get statistics grouped by buyer with optional filters."""
    try:
        tenders = data_loader.load_data()
        # Apply filters if provided
        if any([buyer, status, date_from, date_to, search]):
            tenders = analytics_service.filter_tenders(
                tenders,
                buyer=buyer,
                status=status,
                date_from=date_from,
                date_to=date_to,
                search=search
            )
        buyer_stats = analytics_service.get_buyer_analytics(tenders)
        return BuyerAnalyticsResponse(
            buyers=buyer_stats,
            total=len(buyer_stats)
        )
    except Exception as e:
        logger.error(f"Error getting buyer analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-category", response_model=CategoryAnalyticsResponse)
async def get_category_analytics(
    buyer: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
):
    """Get statistics grouped by category with optional filters."""
    try:
        tenders = data_loader.load_data()
        # Apply filters if provided
        if any([buyer, status, date_from, date_to, search]):
            tenders = analytics_service.filter_tenders(
                tenders,
                buyer=buyer,
                status=status,
                date_from=date_from,
                date_to=date_to,
                search=search
            )
        category_stats = analytics_service.get_category_analytics(tenders)
        return CategoryAnalyticsResponse(
            categories=category_stats,
            total=len(category_stats)
        )
    except Exception as e:
        logger.error(f"Error getting category analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-winner", response_model=WinnerAnalyticsResponse)
async def get_winner_analytics(
    buyer: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
):
    """Get statistics grouped by winner/supplier with optional filters."""
    try:
        tenders = data_loader.load_data()
        # Apply filters if provided
        if any([buyer, status, date_from, date_to, search]):
            tenders = analytics_service.filter_tenders(
                tenders,
                buyer=buyer,
                status=status,
                date_from=date_from,
                date_to=date_to,
                search=search
            )
        winner_stats = analytics_service.get_winner_analytics(tenders)
        return WinnerAnalyticsResponse(
            winners=winner_stats,
            total=len(winner_stats)
        )
    except Exception as e:
        logger.error(f"Error getting winner analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    buyer: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
):
    """Get timeline analysis of tenders with optional filters."""
    try:
        tenders = data_loader.load_data()
        # Apply filters if provided
        if any([buyer, status, date_from, date_to, search]):
            tenders = analytics_service.filter_tenders(
                tenders,
                buyer=buyer,
                status=status,
                date_from=date_from,
                date_to=date_to,
                search=search
            )
        timeline = analytics_service.get_timeline(tenders)
        return TimelineResponse(timeline=timeline)
    except Exception as e:
        logger.error(f"Error getting timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-cache")
async def clear_cache():
    """Clear the data cache to force reload."""
    try:
        data_loader.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

