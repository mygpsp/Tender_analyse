"""Analytics service for tender data analysis."""
import re
import logging
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normalize date string to YYYY-MM-DD format.
    Handles both DD.MM.YYYY and YYYY-MM-DD formats.
    """
    if not date_str:
        return None
    
    # Already in YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # Convert DD.MM.YYYY to YYYY-MM-DD
    match = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', date_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    
    return date_str


class AnalyticsService:
    """Service for analyzing tender data."""
    
    def __init__(self, data_loader):
        self.data_loader = data_loader
    
    def extract_amount(self, text: str) -> Optional[float]:
        """
        Extract amount from Georgian Lari format.
        Examples: "17`627.00 ლარი" -> 17627.00
        
        This function specifically looks for amounts near "ღირებულება" (value) or "ლარი" (lari)
        to avoid matching CPV codes, tender numbers, or dates.
        """
        if not text:
            return None
        
        # Strategy: Look for amounts in context of "ღირებულება" or "ლარი"
        # This avoids matching CPV codes (8-digit numbers) or other numeric fields
        
        # Pattern 1: Number with backticks followed by "ლარი" (most common format)
        # Example: "17`627.00 ლარი" or "1`195`156.91 ლარი"
        pattern1 = r'(\d+(?:`\d+)*(?:\.\d+)?)\s*ლარი'
        match = re.search(pattern1, text)
        if match:
            amount_str = match.group(1)
            cleaned = amount_str.replace('`', '').replace(',', '')
            try:
                amount = float(cleaned)
                # Validate: reasonable amount range (100 GEL to 1 billion GEL)
                if 100 <= amount < 1_000_000_000:
                    return amount
            except ValueError:
                pass
        
        # Pattern 2: "ღირებულება:" followed by number with backticks
        # Example: "ღირებულება: 17`627.00"
        pattern2 = r'ღირებულება[:\s]+(\d+(?:`\d+)*(?:\.\d+)?)'
        match = re.search(pattern2, text)
        if match:
            amount_str = match.group(1)
            cleaned = amount_str.replace('`', '').replace(',', '')
            try:
                amount = float(cleaned)
                if 100 <= amount < 1_000_000_000:
                    return amount
            except ValueError:
                pass
        
        # Pattern 3: Number with backticks within 30 characters before "ლარი"
        # This catches cases where there might be extra text
        pattern3 = r'(\d+(?:`\d+)*(?:\.\d+)?).{0,30}ლარი'
        match = re.search(pattern3, text)
        if match:
            amount_str = match.group(1)
            # Check if this is not a CPV code (CPV codes are usually 8 digits without backticks)
            if '`' in amount_str:  # Amounts have backticks, CPV codes usually don't
                cleaned = amount_str.replace('`', '').replace(',', '')
                try:
                    amount = float(cleaned)
                    if 100 <= amount < 1_000_000_000:
                        return amount
                except ValueError:
                    pass
        
        # Last resort: Look for any number with backticks and decimal point
        # (amounts typically have both, CPV codes don't)
        pattern4 = r'(\d+(?:`\d+)+\.\d+)'
        match = re.search(pattern4, text)
        if match:
            amount_str = match.group(1)
            cleaned = amount_str.replace('`', '').replace(',', '')
            try:
                amount = float(cleaned)
                if 100 <= amount < 1_000_000_000:
                    return amount
            except ValueError:
                pass
        
        return None
    
    def extract_tender_number(self, text: str) -> Optional[str]:
        """Extract tender number from text (e.g., GEO250000579)."""
        if not text:
            return None
        
        # Look for patterns like GEO250000579, CON250000518
        pattern = r'([A-Z]{2,4}\d{9,})'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None
    
    def extract_dates(self, text: str) -> Dict[str, Optional[str]]:
        """Extract dates from text in DD.MM.YYYY format."""
        dates = {}
        if not text:
            return dates
        
        # Look for date patterns DD.MM.YYYY
        pattern = r'(\d{2}\.\d{2}\.\d{4})'
        matches = re.findall(pattern, text)
        
        if matches:
            dates['published_at'] = matches[0] if len(matches) > 0 else None
            dates['deadline'] = matches[1] if len(matches) > 1 else None
        
        return dates
    
    def extract_category(self, text: str) -> Optional[str]:
        """Extract CPV category code from text."""
        if not text:
            return None
        
        # Look for CPV codes like 14200000-ქვიშა და თიხა
        pattern = r'(\d{8})-\s*([^\n]+)'
        match = re.search(pattern, text)
        if match:
            return match.group(1) + "-" + match.group(2).strip()
        return None
    
    def get_summary(self, tenders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics."""
        if not tenders:
            return {
                "total_tenders": 0,
                "total_amount": None,
                "avg_amount": None,
                "unique_buyers": 0,
                "date_range": None
            }
        
        total_amount = 0.0
        amount_count = 0
        buyers = set()
        date_ranges = []
        
        for tender in tenders:
            # Extract buyer
            buyer = (tender.get("buyer") or "").strip()
            if buyer:
                # Try to extract buyer name from text
                buyer_name = self._extract_buyer_name(buyer)
                if buyer_name:
                    buyers.add(buyer_name)
                else:
                    # Fallback to the buyer text itself (if it's already a clean name)
                    buyers.add(buyer)
            
            # Get amount - use structured field if available, otherwise extract from all_cells (backward compatibility)
            amount = tender.get("amount")
            if amount is None:
                # Fallback: extract from all_cells for old records
                all_cells = tender.get("all_cells", "")
                amount = self.extract_amount(all_cells)
            
            if amount:
                # Sanity check: log if amount seems suspiciously large
                if amount > 100_000_000:  # More than 100 million GEL
                    logger.warning(
                        f"Suspiciously large amount: {amount} GEL. "
                        f"Tender: {tender.get('number', 'N/A')}"
                    )
                # Cap at reasonable maximum (1 billion GEL) to prevent errors
                if amount > 1_000_000_000:
                    logger.error(
                        f"Amount exceeds maximum threshold: {amount} GEL. Skipping."
                    )
                    continue
                total_amount += amount
                amount_count += 1
            
            # Extract date range
            date_window = tender.get("date_window")
            if date_window:
                date_ranges.append(date_window)
        
        avg_amount = total_amount / amount_count if amount_count > 0 else None
        
        # Get overall date range
        date_range = None
        if date_ranges:
            all_from = [dw.get("from") for dw in date_ranges if dw.get("from")]
            all_to = [dw.get("to") for dw in date_ranges if dw.get("to")]
            if all_from and all_to:
                date_range = {
                    "from": min(all_from),
                    "to": max(all_to)
                }
        
        return {
            "total_tenders": len(tenders),
            "total_amount": total_amount if amount_count > 0 else None,
            "avg_amount": avg_amount,
            "unique_buyers": len(buyers),
            "date_range": date_range
        }
    
    def _extract_buyer_name(self, text: str) -> Optional[str]:
        """Extract buyer name from text."""
        if not text:
            return None
        
        # Look for pattern: შემსყიდველი: <name>
        pattern = r'შემსყიდველი\s*[:\t]\s*<strong>([^<]+)</strong>'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        
        # Alternative: look for text after "შემსყიდველი" (colon or tab or multi-space)
        # Use regex similar to detailed_scraper to avoid false positives
        pattern = r'შემსყიდველი(?:[:\t]|[ \t]{2,})\s*([^\n]+)'
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip()
            # Remove HTML tags if any
            name = re.sub(r'<[^>]+>', '', name)
            return name.strip()
        
        return None
    
    def get_buyer_analytics(self, tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get statistics grouped by buyer."""
        buyer_stats = defaultdict(lambda: {"count": 0, "amounts": []})
        
        for tender in tenders:
            buyer_text = tender.get("buyer", "").strip()
            buyer_name = self._extract_buyer_name(buyer_text)
            
            if not buyer_name:
                buyer_name = buyer_text[:50] if buyer_text else "Unknown"
            
            buyer_stats[buyer_name]["count"] += 1
            
            # Get amount - use structured field if available, otherwise extract from all_cells
            amount = tender.get("amount")
            if amount is None:
                all_cells = tender.get("all_cells", "")
                amount = self.extract_amount(all_cells)
            if amount:
                # Apply same validation as in get_summary
                if amount > 1_000_000_000:
                    logger.warning(
                        f"Amount exceeds maximum threshold in buyer analytics: {amount} GEL. Skipping."
                    )
                else:
                    buyer_stats[buyer_name]["amounts"].append(amount)
        
        # Convert to list and calculate totals
        result = []
        for buyer, stats in buyer_stats.items():
            total_amount = sum(stats["amounts"]) if stats["amounts"] else None
            result.append({
                "name": buyer,
                "tender_count": stats["count"],
                "total_amount": total_amount
            })
        
        # Sort by tender count descending
        result.sort(key=lambda x: x["tender_count"], reverse=True)
        return result
    
    def get_winner_analytics(self, tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get statistics grouped by winner/supplier."""
        winner_stats = defaultdict(lambda: {"count": 0, "amounts": []})
        
        for tender in tenders:
            # Get supplier from tender record (handle None values)
            supplier = (tender.get("supplier") or "").strip()
            
            # If supplier is empty, try to extract from all_cells
            if not supplier:
                all_cells = tender.get("all_cells", "")
                # Try to extract from "გამარჯვებული: ..." pattern
                supplier_match = re.search(
                    r'გამარჯვებული[:\s]+([^\n|]+)',
                    all_cells,
                    re.IGNORECASE
                )
                if supplier_match:
                    supplier = supplier_match.group(1).strip()
                    supplier = re.sub(r'\s+', ' ', supplier)
            
            if not supplier:
                continue  # Skip tenders without supplier/winner info
            
            winner_stats[supplier]["count"] += 1
            
            # Get amount - use structured field if available, otherwise extract from all_cells
            amount = tender.get("amount")
            if amount is None:
                all_cells = tender.get("all_cells", "")
                amount = self.extract_amount(all_cells)
            if amount:
                # Apply same validation as in other analytics
                if amount > 1_000_000_000:
                    logger.warning(
                        f"Amount exceeds maximum threshold in winner analytics: {amount} GEL. Skipping."
                    )
                else:
                    winner_stats[supplier]["amounts"].append(amount)
        
        # Convert to list and calculate totals
        result = []
        for winner, stats in winner_stats.items():
            total_amount = sum(stats["amounts"]) if stats["amounts"] else None
            avg_amount = total_amount / len(stats["amounts"]) if stats["amounts"] else None
            result.append({
                "name": winner,
                "tender_count": stats["count"],
                "total_amount": total_amount,
                "avg_amount": avg_amount
            })
        
        # Sort by tender count descending
        result.sort(key=lambda x: x["tender_count"], reverse=True)
        return result
    
    def get_category_analytics(self, tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get statistics grouped by category."""
        category_stats = defaultdict(lambda: {"count": 0, "amounts": []})
        
        for tender in tenders:
            # Use structured category if available, otherwise extract from all_cells
            category = tender.get("category")
            if not category:
                all_cells = tender.get("all_cells", "")
                category = self.extract_category(all_cells)
            
            if not category:
                category = "Unknown"
            
            category_stats[category]["count"] += 1
            
            # Get amount - use structured field if available, otherwise extract from all_cells
            amount = tender.get("amount")
            if amount is None:
                all_cells = tender.get("all_cells", "")
                amount = self.extract_amount(all_cells)
            if amount:
                # Apply same validation as in get_summary
                if amount > 1_000_000_000:
                    logger.warning(
                        f"Amount exceeds maximum threshold in category analytics: {amount} GEL. Skipping."
                    )
                else:
                    category_stats[category]["amounts"].append(amount)
        
        # Convert to list
        result = []
        for category, stats in category_stats.items():
            total_amount = sum(stats["amounts"]) if stats["amounts"] else None
            result.append({
                "category": category,
                "tender_count": stats["count"],
                "total_amount": total_amount
            })
        
        # Sort by tender count descending
        result.sort(key=lambda x: x["tender_count"], reverse=True)
        return result
    
    def get_timeline(self, tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get timeline data grouped by date."""
        timeline = defaultdict(lambda: {"count": 0, "amounts": []})
        
        for tender in tenders:
            # Use structured published_date if available, otherwise extract from all_cells
            date_key = tender.get("published_date")
            if not date_key:
                all_cells = tender.get("all_cells", "")
                dates = self.extract_dates(all_cells)
                date_key = dates.get("published_at")
                if not date_key:
                    # Fall back to date window
                    date_window = tender.get("date_window", {})
                    date_key = date_window.get("from")
            
            # Normalize date to YYYY-MM-DD format
            date_key = normalize_date(date_key)
            
            if date_key:
                timeline[date_key]["count"] += 1
                
                # Get amount - use structured field if available, otherwise extract from all_cells
                amount = tender.get("amount")
                if amount is None:
                    all_cells = tender.get("all_cells", "")
                    amount = self.extract_amount(all_cells)
                if amount:
                    # Apply same validation as in get_summary
                    if amount > 1_000_000_000:
                        logger.warning(
                            f"Amount exceeds maximum threshold in timeline: {amount} GEL. Skipping."
                        )
                    else:
                        timeline[date_key]["amounts"].append(amount)
        
        # Convert to list and sort by date
        result = []
        for date_key, stats in timeline.items():
            total_amount = sum(stats["amounts"]) if stats["amounts"] else None
            result.append({
                "date": date_key,
                "count": stats["count"],
                "total_amount": total_amount
            })
        
        # Sort by date
        result.sort(key=lambda x: x["date"])
        return result
    
    def search_tenders(self, tenders: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Full-text search across tenders."""
        if not query:
            return tenders
        
        query_lower = query.lower()
        results = []
        
        for tender in tenders:
            # Search in all text fields
            searchable_text = " ".join([
                tender.get("number") or "",
                tender.get("buyer") or "",
                tender.get("supplier") or "",
                tender.get("status") or "",
                tender.get("all_cells") or ""
            ]).lower()
            
            if query_lower in searchable_text:
                results.append(tender)
        
        return results
    
    def filter_tenders(
        self,
        tenders: List[Dict[str, Any]],
        buyer: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        filter_by_published_date: bool = True,
        filter_by_deadline_date: bool = True,
        search: Optional[str] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        tender_number: Optional[str] = None,
        has_detailed_data: Optional[bool] = None,
        tender_numbers_with_details: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        """Filter tenders based on criteria."""
        filtered = tenders
        
        # Tender number filtering (exact or partial match)
        if tender_number:
            tender_number_upper = tender_number.upper().strip()
            filtered = [
                t for t in filtered
                if self._matches_tender_number(t, tender_number_upper)
            ]
        
        if search:
            filtered = self.search_tenders(filtered, search)
        
        if buyer:
            buyer_lower = buyer.lower()
            filtered = [
                t for t in filtered
                if buyer_lower in t.get("buyer", "").lower()
            ]
        
        if status:
            status_lower = status.lower()
            filtered = [
                t for t in filtered
                if status_lower in t.get("status", "").lower()
            ]
        
        # Date filtering would require parsing dates from text
        # For now, we'll filter by date_window if available
        if date_from or date_to:
            filtered = [
                t for t in filtered
                if self._matches_date_range(
                    t, 
                    date_from, 
                    date_to,
                    filter_by_published_date=filter_by_published_date,
                    filter_by_deadline_date=filter_by_deadline_date
                )
            ]
        
        # Amount filtering
        if amount_min is not None or amount_max is not None:
            filtered = [
                t for t in filtered
                if self._matches_amount_range(t, amount_min, amount_max)
            ]
        
        # Filter by detailed data availability
        if has_detailed_data is not None and tender_numbers_with_details is not None:
            filtered = [
                t for t in filtered
                if self._has_detailed_data(t, tender_numbers_with_details) == has_detailed_data
            ]
        
        # Sort by deadline date (bidding date) - most recent deadlines first
        filtered = self._sort_by_deadline(filtered)
        
        return filtered
    
    def _sort_by_deadline(self, tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort tenders by deadline date (soonest deadlines first)."""
        def get_deadline_date(tender: Dict[str, Any]) -> str:
            """Extract deadline date for sorting."""
            # Use structured deadline_date if available
            deadline_date_str = tender.get("deadline_date")
            
            if not deadline_date_str:
                # Extract from all_cells
                all_cells = tender.get("all_cells", "")
                dates = self.extract_dates(all_cells)
                deadline_date_str = dates.get("deadline")
            
            # Normalize to YYYY-MM-DD format
            deadline_date = normalize_date(deadline_date_str)
            
            # Return normalized date or a far future date if no deadline
            # (so tenders without deadlines appear at the end)
            return deadline_date if deadline_date else "9999-12-31"
        
        # Sort by deadline date ascending (soonest deadlines first)
        return sorted(tenders, key=get_deadline_date, reverse=False)
    
    def _has_detailed_data(self, tender: Dict[str, Any], tender_numbers_with_details: set) -> bool:
        """Check if tender has detailed data available."""
        # Extract tender number from record
        extracted_number = self.extract_tender_number(
            tender.get("number", "") + " " + tender.get("all_cells", "")
        )
        
        if extracted_number:
            return extracted_number.upper() in tender_numbers_with_details
        
        return False
    
    def _matches_tender_number(
        self,
        tender: Dict[str, Any],
        tender_number: str
    ) -> bool:
        """Check if tender matches the tender number filter (case-insensitive, partial match)."""
        # Extract tender number from record
        extracted_number = self.extract_tender_number(
            tender.get("number", "") + " " + tender.get("all_cells", "")
        )
        
        if extracted_number:
            # Case-insensitive partial match
            return tender_number in extracted_number.upper()
        
        # Also check if the filter appears in the number field or all_cells
        number_field = tender.get("number", "").upper()
        all_cells = tender.get("all_cells", "").upper()
        
        return tender_number in number_field or tender_number in all_cells
    
    def _matches_amount_range(
        self,
        tender: Dict[str, Any],
        amount_min: Optional[float],
        amount_max: Optional[float]
    ) -> bool:
        """Check if tender amount matches the range."""
        # Use structured amount field if available, otherwise extract from all_cells
        amount = tender.get("amount")
        if amount is None:
            all_cells = tender.get("all_cells", "")
            amount = self.extract_amount(all_cells)
        
        if amount is None:
            return False  # Exclude tenders without amounts
        
        if amount_min is not None and amount < amount_min:
            return False
        
        if amount_max is not None and amount > amount_max:
            return False
        
        return True
    
    def _matches_date_range(
        self,
        tender: Dict[str, Any],
        date_from: Optional[str],
        date_to: Optional[str],
        filter_by_published_date: bool = True,
        filter_by_deadline_date: bool = True
    ) -> bool:
        """
        Check if tender matches date range.
        Uses published date (გამოცხადების თარიღი) and/or deadline date (წინდადებების მიღების ვადა)
        based on filter_by_published_date and filter_by_deadline_date flags.
        A tender matches if any enabled date falls within the filter range.
        """
        if not date_from and not date_to:
            return True  # No date filter, include all
        
        # Use structured date fields if available, otherwise extract from all_cells
        published_date_str = tender.get("published_date")
        deadline_date_str = tender.get("deadline_date")
        
        if not published_date_str or not deadline_date_str:
            all_cells = tender.get("all_cells", "")
            dates = self.extract_dates(all_cells)
            if not published_date_str:
                published_date_str = dates.get("published_at")
            if not deadline_date_str:
                deadline_date_str = dates.get("deadline")
        
        # If no published date, fall back to date_window
        if not published_date_str:
            date_window = tender.get("date_window", {})
            published_date_str = date_window.get("from")
        
        # Normalize dates to YYYY-MM-DD format for comparison
        published_date = normalize_date(published_date_str)
        deadline_date = normalize_date(deadline_date_str)
        
        # Check if published date falls within range (only if enabled)
        published_matches = False
        if filter_by_published_date and published_date:
            published_matches = True
            if date_from and published_date < date_from:
                published_matches = False
            if date_to and published_date > date_to:
                published_matches = False
        
        # Check if deadline date falls within range (only if enabled)
        deadline_matches = False
        if filter_by_deadline_date and deadline_date:
            deadline_matches = True
            if date_from and deadline_date < date_from:
                deadline_matches = False
            if date_to and deadline_date > date_to:
                deadline_matches = False
        
        # Include tender if any enabled date falls within range
        if published_matches or deadline_matches:
            return True
        
        # If both filters are disabled, include all (no date filtering)
        if not filter_by_published_date and not filter_by_deadline_date:
            return True
        
        # If we can't determine any dates for enabled filters, include it (to be safe)
        if filter_by_published_date and not published_date and filter_by_deadline_date and not deadline_date:
            return True
        
        return False

