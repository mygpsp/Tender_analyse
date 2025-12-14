"""Pydantic models for CON tender API."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ConTenderItem(BaseModel):
    """Single CON tender item."""
    number: str
    buyer: str
    status: str
    published_date: str
    deadline_date: Optional[str] = None
    amount: Optional[float] = None
    final_price: Optional[str] = None
    winner_name: Optional[str] = None
    region: Optional[str] = None
    category: Optional[str] = None
    detail_url: Optional[str] = None


class ConTenderListResponse(BaseModel):
    """Response for CON tender list."""
    items: List[ConTenderItem]
    total: int
    page: int
    page_size: int
    pages: int


class ConTenderStats(BaseModel):
    """Statistics for CON tenders."""
    total_count: int
    total_amount: float
    avg_amount: float
    status_distribution: Dict[str, int]
    region_distribution: Dict[str, int]
    date_range: Dict[str, str]
    regions_count: int
