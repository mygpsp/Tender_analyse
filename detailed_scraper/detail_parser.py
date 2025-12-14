"""
Parser for extracting structured data from tender detail pages.

This parser extracts data according to the new standardized structure.
All fields are always filled (empty strings/objects/arrays if blank).
"""
import re
from typing import Dict, List, Any, Optional
from html.parser import HTMLParser
from html import unescape
from datetime import datetime


class TenderDetailParser:
    """Parser for tender detail page HTML - New Structure."""
    
    def __init__(self):
        pass
    
    def parse(self, html_content: str, text_content: str, tabs_data: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Parse HTML and text content to extract structured data according to new schema.
        
        Args:
            html_content: HTML content from detail panel
            text_content: Plain text content from detail panel
            tabs_data: Dictionary with tab names as keys and their text/html content
            
        Returns:
            Dictionary with structured tender data matching the new schema
        """
        # Initialize result with all required fields (always filled)
        result = self._create_empty_structure()
        
        # Extract basic information
        basic_info = self._extract_basic_info(text_content, html_content)
        
        # Core identification
        result["tender_id"] = basic_info.get("tender_id", "")
        result["procurement_number"] = basic_info.get("tender_number", "")
        result["detail_url"] = basic_info.get("tender_link", "")
        # Tender type: prefer code (NAT, SPA, CON, etc.) over full description
        result["tender_type"] = basic_info.get("tender_type_code", "") or basic_info.get("tender_type", "")
        result["status"] = basic_info.get("status", "")
        
        # Title and description
        result["title"] = self._extract_title(text_content)
        result["description"] = self._extract_section(text_content, ["აღწერა", "განცხადების აღწერა", "შესყიდვის აღწერა"])
        result["additional_information"] = basic_info.get("additional_information", "")
        
        # Category
        result["category"] = basic_info.get("category", "")
        result["category_code"] = basic_info.get("category_code", "")
        result["classifier_codes"] = basic_info.get("classifier_codes", [])
        
        # Buyer
        result["buyer"] = basic_info.get("buyer", "")
        result["buyer_contacts"] = self._extract_buyer_contacts(text_content, html_content)
        
        # Dates
        result["published_date"] = basic_info.get("published_date", "")
        result["deadline_date"] = basic_info.get("deadline_date", "") or basic_info.get("proposal_acceptance_ends", "")
        result["entry_date"] = basic_info.get("entry_date", "")
        result["last_modification"] = basic_info.get("last_modification", "")
        
        # Financial
        result["estimated_value"] = str(basic_info.get("amount", "")) if basic_info.get("amount") else ""
        result["currency"] = "GEL"
        result["vat_included"] = self._extract_vat_included(text_content)
        result["proposal_submission_requirement"] = basic_info.get("proposal_submission_requirement", "")
        result["quantity_or_volume"] = basic_info.get("quantity_or_volume", "")
        
        # Delivery terms
        result["delivery_terms"] = self._extract_delivery_terms(text_content)
        
        # Price reduction and guarantee
        result["price_reduction_step"] = str(basic_info.get("price_reduction_step", "")) if basic_info.get("price_reduction_step") else ""
        result["guarantee"] = self._extract_guarantee(text_content)
        
        # Payment terms
        result["payment_terms"] = self._extract_payment_terms(text_content)
        
        # Documents
        result["documents"] = self._extract_documents(html_content)
        
        # Tabs data (with raw HTML)
        if tabs_data:
            result["tabs_data"] = self._extract_tabs_data(tabs_data, html_content)
            result["raw_html_tables"] = self._extract_raw_html_tables(tabs_data, html_content)
        else:
            result["tabs_data"] = {
                "documentation": {"text": "", "documents_count": 0, "raw_html": ""},
                "offers": {"text": "", "documents_count": 0, "raw_html": ""},
                "results": {"text": "", "documents_count": 0, "raw_html": ""}
            }
            result["raw_html_tables"] = {
                "documentation_tab": "",
                "offers_tab": "",
                "results_tab": ""
            }
        
        # Technical specifications
        result["technical_specifications"] = self._extract_technical_specifications(text_content)
        
        # Additional requirements
        result["additional_requirements"] = self._extract_additional_requirements(text_content)
        
        # Bids (from tabs_data)
        if tabs_data:
            result["bids"] = self._extract_bids_new(tabs_data)
            result["bidders_count"] = len(set(b.get("supplier", "") for b in result["bids"] if b.get("supplier")))
            
            # Winner and lowest bidder
            winner_info = self._extract_winner(result["bids"], basic_info.get("status", ""))
            result["winner"] = winner_info["winner"]
            result["lowest_bidder"] = winner_info["lowest_bidder"]
        else:
            result["bids"] = []
            result["bidders_count"] = 0
            result["winner"] = {"supplier": "", "amount": "", "award_date": ""}
            result["lowest_bidder"] = {"supplier": "", "amount": ""}
        
        # Contracts
        if tabs_data:
            result["contracts"] = self._extract_contracts_new(tabs_data)
        else:
            result["contracts"] = []
        
        # Timeline, deadlines, contacts
        result["timeline"] = self._extract_timeline(text_content, html_content)
        result["deadlines"] = self._extract_deadlines(text_content)
        result["contacts"] = self._extract_contacts(text_content, html_content)
        
        return result
    
    def _create_empty_structure(self) -> Dict[str, Any]:
        """Create empty structure matching the new schema."""
        return {
            "tender_id": "",
            "procurement_number": "",
            "detail_url": "",
            "tender_type": "",
            "status": "",
            "title": "",
            "description": "",
            "additional_information": "",
            "category": "",
            "category_code": "",
            "classifier_codes": [],
            "buyer": "",
            "buyer_contacts": {
                "name": "",
                "phone": "",
                "email": ""
            },
            "published_date": "",
            "deadline_date": "",
            "entry_date": "",
            "last_modification": "",
            "estimated_value": "",
            "currency": "GEL",
            "vat_included": True,
            "proposal_submission_requirement": "",
            "quantity_or_volume": "",
            "delivery_terms": {
                "delivery_deadline": "",
                "delivery_start_date": "",
                "delivery_end_date": "",
                "delivery_type": "",
                "delivery_address": ""
            },
            "price_reduction_step": "",
            "guarantee": {
                "required": False,
                "amount": "",
                "validity_days": ""
            },
            "payment_terms": {
                "prepayment_allowed": False,
                "prepayment_conditions": "",
                "final_payment_terms": "",
                "final_payment_deadline_days": ""
            },
            "documents": [],
            "tabs_data": {},
            "technical_specifications": {
                "raw_text": "",
                "items": []
            },
            "additional_requirements": {
                "sample_required": False,
                "sample_deadline": "",
                "sample_address": "",
                "pricing_adequacy_required": False,
                "pricing_adequacy_terms": "",
                "warranty_required": False,
                "warranty_details": "",
                "no_alternative_offer": False
            },
            "bids": [],
            "winner": {
                "supplier": "",
                "amount": "",
                "award_date": ""
            },
            "contracts": [],
            "timeline": [],
            "deadlines": {},
            "contacts": {},
            "raw_html_tables": {
                "documentation_tab": "",
                "offers_tab": "",
                "results_tab": ""
            },
            "lowest_bidder": {
                "supplier": "",
                "amount": ""
            },
            "bidders_count": 0
        }
    
    def _extract_basic_info(self, text: str, html: str) -> Dict[str, Any]:
        """Extract basic tender information."""
        info = {}
        
        # Tender number
        tender_num_match = re.search(r'განცხადების ნომერი[:\s]+([A-Z]{2,4}\d{9,})', text)
        if tender_num_match:
            info["tender_number"] = tender_num_match.group(1)
        
        # Tender ID from URL
        id_match = re.search(r'[?&]go=(\d+)', html + text)
        if id_match:
            info["tender_id"] = id_match.group(1)
        
        
        # Buyer - Try HTML extraction first (more reliable)
        buyer = None
        
        # Method 1: HTML table parsing - look for "შემსყიდველი" label
        if html:
            # Try to find buyer in table structure: <td>შემსყიდველი</td> followed by <td><a>buyer name</a></td>
            # Pattern 1: With link tag
            buyer_html_match = re.search(
                r'<td[^>]*>\s*შემსყიდველი\s*</td>\s*<td[^>]*>\s*<a[^>]*>([^<]+)</a>',
                html,
                re.IGNORECASE | re.DOTALL
            )
            if buyer_html_match:
                buyer = buyer_html_match.group(1).strip()
            else:
                # Pattern 2: Without link tag (direct text)
                buyer_html_match = re.search(
                    r'<td[^>]*>\s*შემსყიდველი\s*</td>\s*<td[^>]*>([^<]+)</td>',
                    html,
                    re.IGNORECASE | re.DOTALL
                )
                if buyer_html_match:
                    buyer = buyer_html_match.group(1).strip()
            
            # Clean up if found
            if buyer:
                buyer = re.sub(r'\s+', ' ', buyer)  # Normalize whitespace
                buyer = unescape(buyer)  # Decode HTML entities
        
        # Method 2: Text-based extraction (fallback)
        if not buyer or len(buyer) < 3:
            buyer_match = re.search(r'შემსყიდველი\s*[:\t]\s*([^\n(]+)', text)
            if buyer_match:
                buyer = buyer_match.group(1).strip()
        
        # Store buyer if valid
        if buyer and len(buyer) > 3:
            info["buyer"] = buyer
        
        # Tender type - Extract from tender number or text
        # All possible tender types: NAT, SPA, CON, CNT, MEP, DAP, TEP, GEO, DEP, GRA, PPP, B2B
        tender_type_code = None
        if "tender_number" in info:
            # Extract code from tender number (first 2-4 uppercase letters)
            type_code_match = re.match(r'([A-Z]{2,4})', info["tender_number"])
            if type_code_match:
                tender_type_code = type_code_match.group(1)
                info["tender_type_code"] = tender_type_code
        
        # Also try to extract from text
        tender_type_match = re.search(r'შესყიდვის ტიპი[:\s]+([^\n]+)', text)
        if tender_type_match:
            tender_type_full = tender_type_match.group(1).strip()
            info["tender_type"] = tender_type_full
            
            # Map Georgian descriptions to codes
            tender_type_mapping = {
                "ელექტრონული ტენდერი აუქციონის გარეშე": "NAT",
                "გამარტივებული ელექტრონული ტენდერი აუქციონის გარეშე": "NAT",
                "ელექტრონული ტენდერი რევერსული აუქციონით": "SPA",
                "გამარტივებული ელექტრონული ტენდერი რევერსული აუქციონით": "SPA",
                "კონსოლიდირებული ტენდერი": "CON",
                "კონკურსი": "CNT",
                "ორეტაპიანი ელექტრონული ტენდერი": "MEP",
                "ორეტაპიანი გამარტივებული ელექტრონული ტენდერი": "MEP",
                "ელექტრონული ტენდერი განსხვავებული წესით": "DAP",
                "გამარტივებული ელექტრონული ტენდერი განსხვავებული წესით": "DAP",
                "ელექტრონული ტენდერი პრეკვალიფიკაციით": "TEP",
                "შესყიდვის ელექტრონული პროცედურა": "GEO",
                "შესყიდვის ელ. პროცედურა დონორის სახსრებით": "DEP",
                "საგრანტო კონკურსი": "GRA",
                "საჯარო-კერძო თანამშრომლობა/კონცესია": "PPP",
                "კერძო შესყიდვა": "B2B",
            }
            
            # Try to match the full description
            for georgian_text, code in tender_type_mapping.items():
                if georgian_text in tender_type_full:
                    info["tender_type_code"] = code
                    tender_type_code = code
                    break
        
        # If we still don't have a code, use the one from tender number
        if not tender_type_code and "tender_type_code" not in info and "tender_number" in info:
            type_code_match = re.match(r'([A-Z]{2,4})', info["tender_number"])
            if type_code_match:
                info["tender_type_code"] = type_code_match.group(1)
        
        # Status - Extract tender status (შესყიდვის სტატუსი)
        status_match = re.search(r'შესყიდვის სტატუსი[:\s]+([^\n]+)', text)
        if status_match:
            status_text = status_match.group(1).strip()
            # Clean up status text (remove extra whitespace)
            status_text = re.sub(r'\s+', ' ', status_text)
            info["status"] = status_text
        
        # Amount
        amount_patterns = [
            r'შესყიდვის სავარაუდო ღირებულება[:\s]+([\d`\s,]+\.?\d*)\s*GEL',
            r'პრეისკურანტის სავარაუდო ღირებულება[:\s]+([\d`\s,]+\.?\d*)\s*GEL',
            r'შესყიდვის ობიექტის სახელშეკრულებო ღირებულება[:\s]+([\d`\s,]+\.?\d*)\s*GEL'
        ]
        for pattern in amount_patterns:
            amount_match = re.search(pattern, text)
            if amount_match:
                amount_str = amount_match.group(1).replace('`', '').replace(',', '').replace(' ', '')
                try:
                    info["amount"] = float(amount_str)
                    break
                except ValueError:
                    pass
        
        # Dates
        published_match = re.search(r'შესყიდვის გამოცხადების თარიღი[:\s]+(\d{2}\.\d{2}\.\d{4})', text)
        if published_match:
            info["published_date"] = self._normalize_date(published_match.group(1))
        
        deadline_match = re.search(r'წინადადებების მიღება მთავრდება[:\s]+(\d{2}\.\d{2}\.\d{4})', text)
        if deadline_match:
            info["deadline_date"] = self._normalize_date(deadline_match.group(1))
            info["proposal_acceptance_ends"] = info["deadline_date"]
        
        # Category
        category_match = re.search(r'შესყიდვის კატეგორია[:\s]+([^\n]+)', text)
        if category_match:
            category_full = category_match.group(1).strip()
            info["category"] = category_full
            # Extract code
            code_match = re.search(r'(\d{8})', category_full)
            if code_match:
                info["category_code"] = code_match.group(1)
        
        # Classifier codes
        classifier_match = re.search(r'კლასიფიკატორის კოდები[:\s]*\n((?:\s*\d{8}\s*-\s*[^\n]+\n?)+)', text)
        if classifier_match:
            codes_text = classifier_match.group(1).strip()
            codes = []
            for line in codes_text.split('\n'):
                line = line.strip()
                if line:
                    codes.append(line)
            if codes:
                info["classifier_codes"] = codes
        
        # Additional fields
        info["additional_information"] = self._extract_section(text, ["დამატებითი ინფორმაცია"])
        info["quantity_or_volume"] = self._extract_section(text, ["შესყიდვის რაოდენობა ან მოცულობა"])
        info["proposal_submission_requirement"] = self._extract_section(text, ["წინადადება წარმოდგენილი უნდა იყოს"])
        
        price_step_match = re.search(r'შეთავაზების ფასის კლების ბიჯი[:\s]+([\d`\s,]+\.?\d*)\s*GEL', text)
        if price_step_match:
            step_str = price_step_match.group(1).replace('`', '').replace(',', '').replace(' ', '')
            try:
                info["price_reduction_step"] = float(step_str)
            except ValueError:
                pass
        
        entry_match = re.search(r'განცხადების ჩაწერა[:\s]+([^\n]+)', text)
        if entry_match:
            info["entry_date"] = entry_match.group(1).strip()
        
        modification_match = re.search(r'ბოლო შესწორება[:\s]+([^\n]+)', text)
        if modification_match:
            info["last_modification"] = modification_match.group(1).strip()
        
        # Tender link
        link_match = re.search(r'შესყიდვის ბმული[:\s]+(https?://[^\s]+)', text)
        if link_match:
            info["tender_link"] = link_match.group(1)
        else:
            id_match = re.search(r'[?&]go=(\d+)', html + text)
            if id_match:
                info["tender_link"] = f"https://tenders.procurement.gov.ge/public/?go={id_match.group(1)}&lang=ge"
        
        return info
    
    def _extract_bids_new(self, tabs_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract bids in new structure format.
        Detects all bidders from tables, rounds and SPA events.
        """
        bids = []
        if "შეთავაზებები" not in tabs_data:
            return bids
        
        text = tabs_data["შეთავაზებები"].get("text", "")
        
        # Extract bidders from main table (new format)
        # Pattern: პრეტენდენტი | ბოლო შეთავაზება | პირველი შეთავაზება
        # Improved pattern to avoid table headers
        table_bid_pattern = r'([ა-ჰ]+(?:\s+[ა-ჰ]+)*)\s+([\d`\s,]+\.?\d*)\s+(\d{2}\.\d{2}\.\d{4}(?:\s+\d{2}:\d{2})?)\s+([\d`\s,]+\.?\d*)\s+(\d{2}\.\d{2}\.\d{4}(?:\s+\d{2}:\d{2})?)'
        
        bidders_dict = {}  # supplier -> bid data
        
        # Skip table header row
        header_pattern = r'პრეტენდენტი\s+ბოლო\s+შეთავაზება'
        header_match = re.search(header_pattern, text)
        start_pos = header_match.end() if header_match else 0
        
        for match in re.finditer(table_bid_pattern, text[start_pos:], re.MULTILINE):
            supplier = match.group(1).strip()
            
            # Clean supplier name - remove table headers, tabs, newlines, and unwanted text
            supplier = re.sub(r'[\t\n]+', ' ', supplier)  # Replace tabs/newlines with space
            supplier = re.sub(r'^(დრო|შეთავაზებები|ნახვა|ბოლო|პირველი)\s+', '', supplier, flags=re.IGNORECASE)
            supplier = re.sub(r'\s+(დრო|შეთავაზებები|ნახვა)$', '', supplier, flags=re.IGNORECASE)
            supplier = re.sub(r'\s+', ' ', supplier)  # Normalize whitespace
            supplier = supplier.strip()
            
            # Filter out table headers and invalid matches
            if supplier in ["პრეტენდენტი", "ბოლო", "პირველი", "შეთავაზებები", "დრო", "ნახვა"] or len(supplier) < 3:
                continue
            
            # Skip if supplier name looks like a number or date
            if re.match(r'^\d+', supplier) or re.match(r'^\d{2}\.\d{2}', supplier):
                continue
            
            last_amount_str = match.group(2).replace('`', '').replace(',', '').replace(' ', '')
            last_date_str = match.group(3).strip()
            first_amount_str = match.group(4).replace('`', '').replace(',', '').replace(' ', '')
            first_date_str = match.group(5).strip()
            
            try:
                last_amount = float(last_amount_str)
                first_amount = float(first_amount_str)
                
                # Store bidder data
                if supplier not in bidders_dict:
                    bidders_dict[supplier] = {
                        "supplier": supplier,
                        "first_offer_amount": "",
                        "last_offer_amount": "",
                        "first_offer_time": "",
                        "last_offer_time": "",
                        "rounds": []
                    }
                
                # Update with earliest first and latest last
                if not bidders_dict[supplier]["first_offer_amount"] or first_amount < float(bidders_dict[supplier]["first_offer_amount"] or "0"):
                    bidders_dict[supplier]["first_offer_amount"] = str(first_amount)
                    bidders_dict[supplier]["first_offer_time"] = self._normalize_datetime(first_date_str)
                
                if not bidders_dict[supplier]["last_offer_amount"] or last_amount < float(bidders_dict[supplier]["last_offer_amount"] or "999999999"):
                    bidders_dict[supplier]["last_offer_amount"] = str(last_amount)
                    bidders_dict[supplier]["last_offer_time"] = self._normalize_datetime(last_date_str)
                
            except (ValueError, TypeError):
                continue
        
        # Extract rounds (SPA events)
        # Optimized regex to avoid catastrophic backtracking
        # We match the header, then capture everything until the next header or end of string
        round_pattern = r'ვაჭრობის (\d+).*?რაუნდი.*?დაწყება\s+დამთავრება\s+პრეტენდენტი\s+თანხა\s*\n(.*?)(?=ვაჭრობის \d+.*?რაუნდი|$)'
        for round_match in re.finditer(round_pattern, text, re.DOTALL):
            round_num = round_match.group(1)
            round_text = round_match.group(2)
            
            # Extract from round: start_time end_time supplier amount
            round_line_pattern = r'(\d{2}/\d{2})\s+(\d{2}:\d{2})\s+(\d{2}/\d{2})\s+(\d{2}:\d{2})\s+([ა-ჰ]+(?:\s+[ა-ჰ]+)*)\s+([\d`\s,]+\.?\d*)'
            for line_match in re.finditer(round_line_pattern, round_text):
                supplier = line_match.group(5).strip()
                if len(supplier) < 3:
                    continue
                
                if supplier not in bidders_dict:
                    bidders_dict[supplier] = {
                        "supplier": supplier,
                        "first_offer_amount": "",
                        "last_offer_amount": "",
                        "first_offer_time": "",
                        "last_offer_time": "",
                        "rounds": []
                    }
                
                amount_str = line_match.group(6).replace('`', '').replace(',', '').replace(' ', '')
                try:
                    amount = float(amount_str)
                    start_time = f"{line_match.group(1)} {line_match.group(2)}"
                    end_time = f"{line_match.group(3)} {line_match.group(4)}"
                    
                    bidders_dict[supplier]["rounds"].append({
                        "round_number": round_num,
                        "time_start": start_time,
                        "time_end": end_time,
                        "amount": str(amount)
                    })
                except ValueError:
                    continue
        
        # Convert to list and clean supplier names
        bids = []
        for bid in bidders_dict.values():
            # Clean supplier name
            supplier = bid.get("supplier", "").strip()
            supplier = re.sub(r'[\t\n]+', ' ', supplier)  # Replace tabs/newlines with space
            supplier = re.sub(r'^(დრო|შეთავაზებები|ნახვა|ბოლო|პირველი)\s+', '', supplier, flags=re.IGNORECASE)
            supplier = re.sub(r'\s+(დრო|შეთავაზებები|ნახვა)$', '', supplier, flags=re.IGNORECASE)
            supplier = re.sub(r'\s+', ' ', supplier)  # Normalize whitespace
            supplier = supplier.strip()
            
            # Only add if supplier name is valid
            if supplier and len(supplier) > 3 and supplier not in ["პრეტენდენტი", "ბოლო", "პირველი", "შეთავაზებები", "დრო", "ნახვა"]:
                bid["supplier"] = supplier
                bids.append(bid)
        
        return bids
    
    def _extract_winner(self, bids: List[Dict[str, Any]], status: str) -> Dict[str, Any]:
        """Extract winner and lowest bidder information."""
        winner = {"supplier": "", "amount": "", "award_date": ""}
        lowest_bidder = {"supplier": "", "amount": ""}
        
        if not bids:
            return {"winner": winner, "lowest_bidder": lowest_bidder}
        
        # Find lowest bidder (smallest last_offer_amount)
        lowest = None
        lowest_amount = float('inf')
        
        for bid in bids:
            last_amount_str = bid.get("last_offer_amount", "")
            if last_amount_str:
                try:
                    amount = float(last_amount_str)
                    if amount < lowest_amount:
                        lowest_amount = amount
                        lowest = bid
                except ValueError:
                    pass
        
        if lowest:
            # Clean supplier name
            supplier_name = lowest.get("supplier", "").strip()
            supplier_name = re.sub(r'[\t\n]+', ' ', supplier_name)  # Replace tabs/newlines with space
            supplier_name = re.sub(r'^(დრო|შეთავაზებები|ნახვა|ბოლო|პირველი)\s+', '', supplier_name, flags=re.IGNORECASE)
            supplier_name = re.sub(r'\s+(დრო|შეთავაზებები|ნახვა)$', '', supplier_name, flags=re.IGNORECASE)
            supplier_name = re.sub(r'\s+', ' ', supplier_name)  # Normalize whitespace
            supplier_name = supplier_name.strip()
            
            lowest_bidder["supplier"] = supplier_name
            lowest_bidder["amount"] = lowest.get("last_offer_amount", "")
            
            # If status indicates winner or selection/evaluation, set winner
            # Statuses that indicate a winner: contract signed, completed, or in selection/evaluation
            if any(keyword in status for keyword in ["ხელშეკრულება", "დადებულია", "შედგა", "შერჩევა", "შეფასება"]):
                winner["supplier"] = supplier_name
                winner["amount"] = lowest.get("last_offer_amount", "")
                winner["award_date"] = lowest.get("last_offer_time", "")
        
        return {"winner": winner, "lowest_bidder": lowest_bidder}
    
    def _extract_contracts_new(self, tabs_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract contracts in new structure format."""
        contracts = []
        if "ხელშეკრულება" not in tabs_data:
            return contracts
        
        text = tabs_data["ხელშეკრულება"].get("text", "")
        
        # Extract contract information
        contract_match = re.search(
            r'ნომერი/თანხა[:\s]+([^\s/]+(?:\s*/\s*[^\s/]+)*)\s*/\s*([\d`\s,]+\.?\d*)\s*ლარი',
            text,
            re.MULTILINE
        )
        
        if contract_match:
            contract_number = contract_match.group(1).strip()
            amount_str = contract_match.group(2).replace('`', '').replace(',', '').replace(' ', '')
            
            # Extract supplier
            supplier_match = re.search(
                r'(შპს\s+[ა-ჰ]+(?:\s+[ა-ჰ]+)*)\s*\n\s*ნომერი/თანხა',
                text,
                re.MULTILINE
            )
            supplier = supplier_match.group(1).strip() if supplier_match else ""
            
            # Extract dates
            signing_date_match = re.search(r'ხელშეკრულების თარიღი[:\s]+(\d{2}\.\d{2}\.\d{4})', text)
            signing_date = self._normalize_date(signing_date_match.group(1)) if signing_date_match else ""
            
            # Extract contract URL
            contract_url_match = re.search(r'ნახვა/გადმოწერა[:\s]+(https?://[^\s]+)', text)
            contract_url = contract_url_match.group(1) if contract_url_match else ""
            
            contracts.append({
                "contract_id": contract_number,
                "supplier": supplier,
                "amount": amount_str,
                "signing_date": signing_date,
                "contract_url": contract_url
            })
        
        return contracts
    
    def _extract_tabs_data(self, tabs_data: Dict[str, Dict[str, Any]], html_content: str) -> Dict[str, Dict[str, Any]]:
        """Extract tabs data with raw HTML."""
        result = {
            "documentation": {"text": "", "documents_count": 0, "raw_html": ""},
            "offers": {"text": "", "documents_count": 0, "raw_html": ""},
            "results": {"text": "", "documents_count": 0, "raw_html": ""}
        }
        
        # Map Georgian tab names to English keys
        tab_mapping = {
            "დოკუმენტაცია": "documentation",
            "შეთავაზებები": "offers",
            "შედეგები": "results"
        }
        
        for georgian_name, english_key in tab_mapping.items():
            if georgian_name in tabs_data:
                tab_content = tabs_data[georgian_name]
                result[english_key]["text"] = tab_content.get("text", "")
                result[english_key]["raw_html"] = tab_content.get("html", "")
                # Count documents in this tab
                result[english_key]["documents_count"] = len([d for d in self._extract_documents(html_content) if georgian_name in str(d)])
        
        return result
    
    def _extract_raw_html_tables(self, tabs_data: Dict[str, Dict[str, Any]], html_content: str) -> Dict[str, str]:
        """Extract raw HTML tables from tabs."""
        result = {
            "documentation_tab": "",
            "offers_tab": "",
            "results_tab": ""
        }
        
        tab_mapping = {
            "დოკუმენტაცია": "documentation_tab",
            "შეთავაზებები": "offers_tab",
            "შედეგები": "results_tab"
        }
        
        for georgian_name, english_key in tab_mapping.items():
            if georgian_name in tabs_data:
                tab_content = tabs_data[georgian_name]
                # Extract table HTML
                html_text = tab_content.get("html", "")
                if html_text:
                    # Find table elements
                    table_match = re.search(r'<table[^>]*>.*?</table>', html_text, re.DOTALL | re.IGNORECASE)
                    if table_match:
                        result[english_key] = table_match.group(0)
        
        return result
    
    # Helper methods (simplified versions)
    def _extract_title(self, text: str) -> str:
        """Extract tender title."""
        title_match = re.search(r'შესყიდვის ობიექტი[:\s]+([^\n]+)', text)
        return title_match.group(1).strip() if title_match else ""
    
    def _extract_section(self, text: str, labels: List[str]) -> str:
        """Extract section by label."""
        for label in labels:
            pattern = rf'{re.escape(label)}[:\s]*\n?(.+?)(?=\n\s*(?:[ა-ჰ]{{3,}}[:\s]|$))'
            match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
            if match:
                content = match.group(1).strip()
                if len(content) > 10:
                    return content
        return ""
    
    def _extract_buyer_contacts(self, text: str, html: str) -> Dict[str, str]:
        """Extract buyer contact information."""
        return {
            "name": "",
            "phone": "",
            "email": ""
        }
    
    def _extract_vat_included(self, text: str) -> bool:
        """Extract VAT inclusion status."""
        return "დღგ-ს გათვალისწინებით" in text
    
    def _extract_delivery_terms(self, text: str) -> Dict[str, str]:
        """Extract delivery terms."""
        return {
            "delivery_deadline": "",
            "delivery_start_date": "",
            "delivery_end_date": "",
            "delivery_type": "",
            "delivery_address": ""
        }
    
    def _extract_guarantee(self, text: str) -> Dict[str, Any]:
        """Extract guarantee information."""
        guarantee = {
            "required": False,
            "amount": "",
            "validity_days": ""
        }
        
        guarantee_match = re.search(r'გარანტიის ოდენობა[:\s]+([\d`\s,]+\.?\d*)\s*GEL', text)
        if guarantee_match:
            guarantee["required"] = True
            guarantee["amount"] = guarantee_match.group(1).replace('`', '').replace(',', '').replace(' ', '')
        
        validity_match = re.search(r'გარანტიის მოქმედების ვადა[:\s]+(\d+)\s*დღე', text)
        if validity_match:
            guarantee["validity_days"] = validity_match.group(1)
        
        return guarantee
    
    def _extract_payment_terms(self, text: str) -> Dict[str, Any]:
        """Extract payment terms."""
        return {
            "prepayment_allowed": False,
            "prepayment_conditions": "",
            "final_payment_terms": "",
            "final_payment_deadline_days": ""
        }
    
    def _extract_documents(self, html: str) -> List[Dict[str, str]]:
        """Extract document links."""
        documents = []
        seen_urls = set()
        
        link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>'
        for match in re.finditer(link_pattern, html, re.IGNORECASE):
            href = unescape(match.group(1)).strip()
            text = unescape(match.group(2)).strip()
            
            if href in seen_urls:
                continue
            
            if 'library/files.php' in href or href.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                file_type = href.split('.')[-1].lower() if '.' in href else "unknown"
                documents.append({
                    "name": text,
                    "url": href,
                    "type": file_type
                })
                seen_urls.add(href)
        
        return documents
    
    def _extract_technical_specifications(self, text: str) -> Dict[str, Any]:
        """Extract technical specifications."""
        return {
            "raw_text": self._extract_section(text, ["სპეციფიკაცია", "ტექნიკური სპეციფიკაცია"]),
            "items": []
        }
    
    def _extract_additional_requirements(self, text: str) -> Dict[str, Any]:
        """Extract additional requirements."""
        return {
            "sample_required": False,
            "sample_deadline": "",
            "sample_address": "",
            "pricing_adequacy_required": False,
            "pricing_adequacy_terms": "",
            "warranty_required": False,
            "warranty_details": "",
            "no_alternative_offer": False
        }
    
    def _extract_timeline(self, text: str, html: str) -> List[Dict[str, str]]:
        """Extract timeline events."""
        return []
    
    def _extract_deadlines(self, text: str) -> Dict[str, str]:
        """Extract deadline information."""
        return {}
    
    def _extract_contacts(self, text: str, html: str) -> Dict[str, str]:
        """Extract contact information."""
        return {}
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date to YYYY-MM-DD format."""
        if not date_str:
            return ""
        
        # Try DD.MM.YYYY format
        date_match = re.match(r'(\d{2})\.(\d{2})\.(\d{4})', date_str)
        if date_match:
            day, month, year = date_match.groups()
            return f"{year}-{month}-{day}"
        
        # Already in YYYY-MM-DD format
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            return date_str
        
        return date_str
    
    def _normalize_datetime(self, datetime_str: str) -> str:
        """Normalize datetime string."""
        if not datetime_str:
            return ""
        
        # Try DD.MM.YYYY HH:MM format
        dt_match = re.match(r'(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}:\d{2})', datetime_str)
        if dt_match:
            day, month, year, time = dt_match.groups()
            return f"{year}-{month}-{day} {time}"
        
        return datetime_str

