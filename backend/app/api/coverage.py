"""API endpoints for data coverage analysis."""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.services.data_loader import DataLoader
from app.services.detail_loader import DetailLoader
from app.services.analytics import AnalyticsService, normalize_date

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coverage", tags=["coverage"])

# Initialize services - data path relative to project root
_data_path = Path(__file__).parent.parent.parent.parent / "main_scrapper" / "data"
data_loader = DataLoader(_data_path)
_detailed_data_path = _data_path / "detailed_tenders.jsonl"
detail_loader = DetailLoader(_detailed_data_path)


@router.get("/stats")
async def get_coverage_stats(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    filter_by_published_date: bool = Query(default=True),
    filter_by_deadline_date: bool = Query(default=True),
):
    """
    Get coverage statistics showing scraped vs non-scraped tenders.
    
    Returns:
    - Total tenders
    - Scraped count
    - Non-scraped count
    - Coverage percentage
    - Breakdown by date
    - Breakdown by category
    - Breakdown by buyer
    """
    try:
        # Load all tenders
        all_tenders = data_loader.load_data()
        
        # Get tender numbers with detailed data
        tender_numbers_with_details = detail_loader.get_tender_numbers_with_details()
        
        # Initialize analytics service
        analytics_service = AnalyticsService(data_loader)
        
        # Apply date filtering if provided
        if date_from or date_to:
            all_tenders = analytics_service.filter_tenders(
                all_tenders,
                date_from=date_from,
                date_to=date_to,
                filter_by_published_date=filter_by_published_date,
                filter_by_deadline_date=filter_by_deadline_date
            )
        
        # Calculate coverage
        total_count = len(all_tenders)
        scraped_count = 0
        non_scraped_count = 0
        
        # Breakdowns
        by_date: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "scraped": 0})
        by_category: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "scraped": 0})
        by_buyer: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "scraped": 0})
        
        for tender in all_tenders:
            # Extract tender number
            tender_number = analytics_service.extract_tender_number(
                tender.get("number", "") + " " + tender.get("all_cells", "")
            )
            
            # Check if scraped
            is_scraped = tender_number and tender_number.upper() in tender_numbers_with_details
            
            if is_scraped:
                scraped_count += 1
            else:
                non_scraped_count += 1
            
            # Extract date for breakdown
            deadline_date_str = tender.get("deadline_date")
            if not deadline_date_str:
                all_cells = tender.get("all_cells", "")
                dates = analytics_service.extract_dates(all_cells)
                deadline_date_str = dates.get("deadline")
            
            deadline_date = normalize_date(deadline_date_str)
            if deadline_date:
                by_date[deadline_date]["total"] += 1
                if is_scraped:
                    by_date[deadline_date]["scraped"] += 1
            
            # Extract category for breakdown
            category = tender.get("category")
            if not category:
                all_cells = tender.get("all_cells", "")
                category = analytics_service.extract_category(all_cells)
            
            if not category:
                category = "Unknown"
            
            by_category[category]["total"] += 1
            if is_scraped:
                by_category[category]["scraped"] += 1
            
            # Extract buyer for breakdown
            buyer = tender.get("buyer", "")
            if buyer:
                buyer_name = analytics_service._extract_buyer_name(buyer)
                if not buyer_name:
                    buyer_name = buyer[:50] if buyer else "Unknown"
            else:
                buyer_name = "Unknown"
            
            by_buyer[buyer_name]["total"] += 1
            if is_scraped:
                by_buyer[buyer_name]["scraped"] += 1
        
        # Calculate coverage percentage
        coverage_percentage = (scraped_count / total_count * 100) if total_count > 0 else 0
        
        # Convert breakdowns to lists and sort
        date_breakdown = [
            {
                "date": date,
                "total": stats["total"],
                "scraped": stats["scraped"],
                "coverage": (stats["scraped"] / stats["total"] * 100) if stats["total"] > 0 else 0
            }
            for date, stats in by_date.items()
        ]
        date_breakdown.sort(key=lambda x: x["date"], reverse=True)
        
        category_breakdown = [
            {
                "category": category,
                "total": stats["total"],
                "scraped": stats["scraped"],
                "coverage": (stats["scraped"] / stats["total"] * 100) if stats["total"] > 0 else 0
            }
            for category, stats in by_category.items()
        ]
        category_breakdown.sort(key=lambda x: x["total"], reverse=True)
        
        buyer_breakdown = [
            {
                "buyer": buyer,
                "total": stats["total"],
                "scraped": stats["scraped"],
                "coverage": (stats["scraped"] / stats["total"] * 100) if stats["total"] > 0 else 0
            }
            for buyer, stats in by_buyer.items()
        ]
        buyer_breakdown.sort(key=lambda x: x["total"], reverse=True)
        
        return {
            "summary": {
                "total": total_count,
                "scraped": scraped_count,
                "non_scraped": non_scraped_count,
                "coverage_percentage": round(coverage_percentage, 2)
            },
            "by_date": date_breakdown[:30],  # Last 30 days
            "by_category": category_breakdown[:20],  # Top 20 categories
            "by_buyer": buyer_breakdown[:20]  # Top 20 buyers
        }
        
    except Exception as e:
        logger.error(f"Error getting coverage stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
