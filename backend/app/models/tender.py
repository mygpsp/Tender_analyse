"""Pydantic models for tender data."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DateWindow(BaseModel):
    """Date window for scraping."""
    from_date: str = Field(..., alias="from")
    to: str

    class Config:
        populate_by_name = True


class Tender(BaseModel):
    """Tender data model."""
    number: str = ""
    buyer: str = ""
    supplier: str = ""
    status: str = ""
    participants_count: Optional[int] = None  # Number of participants (მონაწილეთა რაოდენობა)
    amount: Optional[float] = None  # Tender amount in GEL
    published_date: Optional[str] = None  # Publication date (YYYY-MM-DD)
    deadline_date: Optional[str] = None  # Proposal deadline (YYYY-MM-DD)
    category: Optional[str] = None  # Full category description (CODE-DESCRIPTION)
    category_code: Optional[str] = None  # CPV category code (8 digits)
    tender_type: Optional[str] = None  # Tender type (GEO, NAT, CON, etc.)
    all_cells: str = ""
    scraped_at: Optional[float] = None
    date_window: Optional[DateWindow] = None
    extraction_method: Optional[str] = None
    tender_id: Optional[str] = None
    detail_url: Optional[str] = None

    class Config:
        populate_by_name = True


class TenderResponse(BaseModel):
    """Tender response with ID."""
    id: int
    tender: Tender


class TenderListResponse(BaseModel):
    """Paginated tender list response."""
    items: list[TenderResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TenderFilters(BaseModel):
    """Filters for tender queries."""
    buyer: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AnalyticsSummary(BaseModel):
    """Summary statistics."""
    total_tenders: int
    total_amount: Optional[float] = None
    avg_amount: Optional[float] = None
    unique_buyers: int
    date_range: Optional[Dict[str, str]] = None


class BuyerStats(BaseModel):
    """Statistics for a buyer."""
    name: str
    tender_count: int
    total_amount: Optional[float] = None


class BuyerAnalyticsResponse(BaseModel):
    """Buyer analytics response."""
    buyers: list[BuyerStats]
    total: int


class CategoryStats(BaseModel):
    """Statistics for a category."""
    category: str
    tender_count: int
    total_amount: Optional[float] = None


class CategoryAnalyticsResponse(BaseModel):
    """Category analytics response."""
    categories: list[CategoryStats]
    total: int


class WinnerStats(BaseModel):
    """Statistics for a winner/supplier."""
    name: str
    tender_count: int
    total_amount: Optional[float] = None
    avg_amount: Optional[float] = None


class WinnerAnalyticsResponse(BaseModel):
    """Winner/supplier analytics response."""
    winners: list[WinnerStats]
    total: int


class TimelinePoint(BaseModel):
    """Timeline data point."""
    date: str
    count: int
    total_amount: Optional[float] = None


class TimelineResponse(BaseModel):
    """Timeline analytics response."""
    timeline: list[TimelinePoint]

