"""API routes for market analysis operations."""
import logging
from fastapi import APIRouter, HTTPException
from pathlib import Path

from ..services.market_analysis_service import MarketAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["market-analysis"])

# Initialize service
_data_path = Path(__file__).parent.parent.parent.parent / "main_scrapper" / "data"
market_analysis_service = MarketAnalysisService(_data_path)


@router.get("/kpis")
async def get_kpis():
    """
    Get overall market KPIs.
    
    Returns:
        - total_tenders: Total number of tenders
        - avg_inflation: Average price inflation across regions (%)
        - total_market_volume: Total market volume in GEL
    """
    try:
        kpis = market_analysis_service.calculate_kpis()
        return kpis
    except Exception as e:
        logger.error(f"Error calculating KPIs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-trends")
async def get_price_trends():
    """
    Get price trends by region and year.
    
    Returns:
        - regions: List of top regions
        - years: List of years (2020-2025)
        - data: Dictionary with region data including average prices and inflation
    """
    try:
        trends = market_analysis_service.calculate_price_trends()
        return trends
    except Exception as e:
        logger.error(f"Error calculating price trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-share")
async def get_market_share():
    """
    Get market share by top winners.
    
    Returns:
        - top_winners: List of top 10 winners with:
            - name: Company name
            - total_wins: Number of tenders won
            - total_value: Total contract value in GEL
            - regions: List of regions where they won
    """
    try:
        market_share = market_analysis_service.calculate_market_share()
        return market_share
    except Exception as e:
        logger.error(f"Error calculating market share: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failures")
async def get_failures():
    """
    Get failure rates by region.
    
    Returns:
        - regions: List of top 10 regions by failure rate with:
            - name: Region name
            - total: Total tenders
            - failed: Number of failed tenders
            - failure_rate: Failure percentage
    """
    try:
        failures = market_analysis_service.calculate_failure_rates()
        return failures
    except Exception as e:
        logger.error(f"Error calculating failure rates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-opportunities")
async def get_hot_opportunities():
    """
    Get hot opportunities (regions with recent failures).
    
    Returns list of regions with failed tenders that might be re-tendered.
    """
    try:
        # Get failure data
        failures = market_analysis_service.calculate_failure_rates()
        
        # Filter for regions with significant failures (>20%)
        hot_opportunities = [
            region for region in failures['regions']
            if region['failure_rate'] > 20 and region['failed'] >= 3
        ]
        
        return {"opportunities": hot_opportunities[:10]}
    except Exception as e:
        logger.error(f"Error calculating hot opportunities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
