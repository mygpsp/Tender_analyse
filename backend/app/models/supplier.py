"""Supplier data models."""
from pydantic import BaseModel
from typing import Optional, List


class ContactPerson(BaseModel):
    """Contact person information."""
    full_name: Optional[str] = None
    position: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None


class SupplierInfo(BaseModel):
    """Supplier basic information."""
    name: Optional[str] = None
    identification_code: Optional[str] = None
    country: Optional[str] = None
    city_or_region: Optional[str] = None
    legal_address: Optional[str] = None
    telephone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class Supplier(BaseModel):
    """Complete supplier data model."""
    supplier: SupplierInfo
    contact_persons: List[ContactPerson] = []
    cpv_codes: List[dict] = []
    registration_date: Optional[str] = None
    supplier_or_buyer_type: Optional[str] = None
    scraped_at: Optional[str] = None
    scraping_status: str = "success"


class SupplierResponse(BaseModel):
    """Response model for a single supplier."""
    id: int
    supplier: dict


class SupplierListResponse(BaseModel):
    """Response model for paginated supplier list."""
    items: List[SupplierResponse]
    total: int
    page: int
    page_size: int
    pages: int
