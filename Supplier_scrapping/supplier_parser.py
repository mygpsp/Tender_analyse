"""
Supplier Parser Module

Extracts structured data from supplier profile modals.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from playwright.async_api import Page


class SupplierParser:
    """Parser for supplier profile data."""
    
    def __init__(self, selectors: Dict[str, Any]):
        """
        Initialize parser with selectors configuration.
        
        Args:
            selectors: Dictionary containing XPath/CSS selectors for profile fields
        """
        self.selectors = selectors
        self.log = logging.getLogger("supplier_parser")
    
    async def parse_profile(
        self, 
        page: Page, 
        supplier_name: str = "",
        registration_date: str = "",
        supplier_type: str = ""
    ) -> Dict[str, Any]:
        """
        Parse supplier profile from modal.
        
        Args:
            page: Playwright page object with modal open
            supplier_name: Supplier name extracted from table row
            registration_date: Registration date from table row
            supplier_type: Supplier/buyer type from table row
            
        Returns:
            Dictionary containing supplier profile data in new schema format
        """
        # Wait for modal content to load
        await page.wait_for_selector(
            self.selectors["modal"]["content"],
            state="visible",
            timeout=self.selectors["timing"]["modal_load_timeout"]
        )
        
        # Use provided supplier name or try to extract from modal
        if not supplier_name:
            supplier_name = await self._extract_supplier_name(page)
        
        # Extract basic supplier information
        supplier_info = await self._extract_supplier_info(page)
        supplier_info["name"] = supplier_name or None
        
        # Extract contact persons from tabs
        contact_persons = await self._extract_contact_persons(page)
        
        # Extract CPV codes if available
        cpv_codes = await self._extract_cpv_codes(page)
        
        # Build final profile structure
        profile = {
            "supplier": supplier_info,
            "contact_persons": contact_persons,
            "cpv_codes": cpv_codes,
            # Add metadata from table row
            "registration_date": registration_date or None,
            "supplier_or_buyer_type": supplier_type or None,
            "scraped_at": "",  # Will be set by scraper
            "scraping_status": "success"
        }
        
        return profile
    
    async def _extract_supplier_name(self, page: Page) -> str:
        """Extract supplier name from modal title."""
        try:
            title_element = page.locator(self.selectors["modal"]["title"])
            title_text = await title_element.text_content()
            # Remove "პროფილი" and clean up
            name = (title_text or "").replace("პროფილი", "").strip()
            return name if name else ""
        except Exception as e:
            self.log.warning(f"Could not extract supplier name: {e}")
            return ""
    
    async def _extract_supplier_info(self, page: Page) -> Dict[str, str]:
        """Extract basic supplier information fields."""
        profile_fields = self.selectors["profile_fields"]
        
        # Extract all fields
        identification_code = await self._extract_field(page, profile_fields["identification_code"])
        country = await self._extract_field(page, profile_fields["country"])
        city = await self._extract_field(page, profile_fields["city"])
        address = await self._extract_field(page, profile_fields["address"])
        
        # Phone extraction - try multiple approaches
        phone = await self._extract_phone(page)
        
        fax = await self._extract_field(page, profile_fields["fax"])
        email = await self._extract_field(page, profile_fields["email"])
        website = await self._extract_field(page, profile_fields["website"])
        
        # Clean up website (remove double http://)
        website = self._clean_website(website)
        
        return {
            "name": "",  # Will be set later
            "identification_code": identification_code or None,
            "country": country or None,
            "city_or_region": city or None,
            "legal_address": address or None,
            "telephone": phone or None,
            "fax": fax or None,
            "email": email or None,
            "website": website or None
        }
    
    async def _extract_phone(self, page: Page) -> Optional[str]:
        """Extract phone number with multiple fallback strategies."""
        profile_fields = self.selectors["profile_fields"]
        
        # Strategy 1: Try the standard phone field
        phone = await self._extract_field(page, profile_fields["phone"])
        if phone and phone.strip():
            return phone.strip()
        
        # Strategy 2: Look in the "ტელეფონი" tab if it exists
        try:
            # Check if there's a phone tab
            phone_tab_selector = "a:has-text('ტელეფონი')"
            phone_tab = page.locator(phone_tab_selector)
            
            if await phone_tab.count() > 0:
                # Click the phone tab
                await phone_tab.first.click()
                await page.wait_for_timeout(500)
                
                # Try to extract phone from table
                phone_table = page.locator("table")
                if await phone_table.count() > 0:
                    table_text = await phone_table.first.text_content()
                    # Extract phone numbers from text
                    phones = re.findall(r'\+995[\s\d]+', table_text or "")
                    if phones:
                        return phones[0].strip()
        except Exception as e:
            self.log.debug(f"Could not extract phone from tab: {e}")
        
        return None
    
    async def _extract_contact_persons(self, page: Page) -> List[Dict[str, str]]:
        """Extract contact persons from the contact persons tab or table."""
        contact_persons = []
        
        try:
            # First, try to find contact persons in a tab (older format)
            contact_tab_selector = "a:has-text('საკონტაქტო პირები')"
            contact_tab = page.locator(contact_tab_selector)
            
            if await contact_tab.count() > 0:
                # Tab-based approach
                self.log.debug("Found contact persons tab, clicking...")
                await contact_tab.first.click()
                await page.wait_for_timeout(500)
                
                # Extract from table after clicking tab
                rows_selector = "table tbody tr"
                rows = await page.locator(rows_selector).all()
            else:
                # Direct table approach (newer format)
                # Contact persons are directly in the modal at #profile_dialog > div:nth-child(2) > table
                self.log.debug("No tab found, checking direct table location...")
                contact_table_selector = "#profile_dialog > div:nth-child(2) > table"
                contact_table = page.locator(contact_table_selector)
                
                if await contact_table.count() == 0:
                    self.log.debug("No contact persons table found")
                    return []
                
                # Get rows from this specific table
                rows = await contact_table.locator("tbody tr").all()
            
            # Process rows (same for both approaches)
            # Table structure: სახელი გვარი თანამდებობა | ტელეფონი | ელ-ფოსტა
            # (name and position are combined in first column)
            
            for row in rows:
                try:
                    cells = await row.locator("td").all()
                    if len(cells) >= 3:
                        # First column contains both name and position
                        name_position = await cells[0].text_content()
                        telephone = await cells[1].text_content()
                        email = await cells[2].text_content()
                        
                        # Try to parse name and position from combined text
                        # Common patterns: "Name Surname Position" or just "Name Surname"
                        full_name = None
                        position = None
                        
                        if name_position:
                            name_position = name_position.strip()
                            # Split by whitespace and try to identify position keywords
                            parts = name_position.split()
                            if len(parts) >= 2:
                                # Common position keywords in Georgian
                                position_keywords = ['დირექტორი', 'მენეჯერი', 'უფროსი', 'თავმჯდომარე', 
                                                    'ხელმძღვანელი', 'წარმომადგენელი', 'აღმასრულებელი']
                                
                                # Check if last word is a position
                                if parts[-1] in position_keywords:
                                    position = parts[-1]
                                    full_name = ' '.join(parts[:-1])
                                else:
                                    # Assume entire text is the name
                                    full_name = name_position
                        
                        contact_persons.append({
                            "full_name": full_name or None,
                            "position": position or None,
                            "telephone": (telephone or "").strip() or None,
                            "email": (email or "").strip() or None
                        })
                except Exception as e:
                    self.log.debug(f"Error extracting contact person row: {e}")
                    continue
                    
        except Exception as e:
            self.log.debug(f"Could not extract contact persons: {e}")
        
        return contact_persons
    
    async def _extract_cpv_codes(self, page: Page) -> List[Dict[str, str]]:
        """Extract CPV codes using the specific highlight container."""
        cpv_codes = []
        
        try:
            # Selector provided by user: #profile_dialog > div.ui-state-highlight.ui-corner-all > ul
            cpv_list_selector = "#profile_dialog > div.ui-state-highlight.ui-corner-all > ul > li"
            cpv_items = await page.locator(cpv_list_selector).all()
            
            for item in cpv_items:
                text = await item.text_content()
                if text:
                    # Format usually: "CODE - Description"
                    # Example: "45000000 - სამშენებლო სამუშაოები"
                    parts = text.split('-', 1)
                    code = parts[0].strip()
                    description = parts[1].strip() if len(parts) > 1 else ""
                    
                    cpv_codes.append({
                        "code": code,
                        "description": description
                    })
            
        except Exception as e:
            self.log.debug(f"Could not extract CPV codes: {e}")
        
        return cpv_codes
    
    async def _extract_field(self, page: Page, xpath: str) -> Optional[str]:
        """
        Extract text content from element using XPath.
        
        Args:
            page: Playwright page object
            xpath: XPath selector for the field
            
        Returns:
            Extracted text content, None if not found
        """
        try:
            element = page.locator(f"xpath={xpath}")
            # Use .first to handle multiple matches (avoid strict mode violation)
            text = await element.first.text_content(timeout=1000)
            cleaned = (text or "").strip()
            return cleaned if cleaned else None
        except Exception as e:
            self.log.debug(f"Could not extract field with XPath '{xpath}': {e}")
            return None
    
    def _clean_website(self, website: Optional[str]) -> Optional[str]:
        """Clean up website URL (remove double http://)."""
        if not website:
            return None
        
        # Remove double http:// or https://
        cleaned = re.sub(r'https?://(https?://)+', r'http://', website)
        
        # If it's just "http://" with nothing after, return None
        if cleaned.strip() in ["http://", "https://"]:
            return None
        
        return cleaned.strip()
    
    def validate_profile(self, profile: Dict[str, Any]) -> bool:
        """
        Validate that profile has minimum required fields.
        
        Args:
            profile: Supplier profile dictionary
            
        Returns:
            True if profile is valid, False otherwise
        """
        # At minimum, we need identification code
        supplier = profile.get("supplier", {})
        if not supplier.get("identification_code"):
            self.log.warning("Profile missing identification code")
            return False
        
        return True
