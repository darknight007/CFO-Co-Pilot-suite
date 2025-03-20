import PyPDF2
import spacy
import re
import pycountry
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
import json
from pathlib import Path
from datetime import datetime
import cv2
import numpy as np
import pytesseract
from PIL import Image
from service_classifier import ServiceClassifier, ServiceClassification

@dataclass
class InvoiceItem:
    description: str
    quantity: float
    rate: float
    hsn_sac: str
    amount: float
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0

@dataclass
class BankDetails:
    """Bank account details from invoice"""
    bank_name: str
    account_holder_name: str
    account_number: str
    ifsc_code: str
    branch: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {
            'bank_name': self.bank_name,
            'account_holder_name': self.account_holder_name,
            'account_number': self.account_number,
            'ifsc_code': self.ifsc_code,
            'branch': self.branch
        }

@dataclass
class InvoiceAnalysis:
    # Basic Invoice Details
    invoice_number: str
    invoice_date: str
    due_date: str
    terms: str
    
    # Payer Details
    payer_name: str
    payer_gstin: str
    payer_address: str
    
    # Payee Details
    payee_name: str
    payee_gstin: str
    payee_address: str
    
    # Location Details
    place_of_supply: str
    
    # Items and Tax
    items: List[InvoiceItem]
    total_amount: float
    total_cgst: float
    total_sgst: float
    total_igst: float
    
    # Payment Details
    bank_details: BankDetails
    
    # Verification
    has_signature: bool
    has_stamp: bool
    
    # Service Classification
    service_classification: Optional[ServiceClassification] = None

    def to_dict(self) -> Dict:
        """Convert analysis to dictionary"""
        result = {
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'due_date': self.due_date,
            'terms': self.terms,
            'payer_name': self.payer_name,
            'payer_gstin': self.payer_gstin,
            'payer_address': self.payer_address,
            'payee_name': self.payee_name,
            'payee_gstin': self.payee_gstin,
            'payee_address': self.payee_address,
            'place_of_supply': self.place_of_supply,
            'items': [item.__dict__ for item in self.items],
            'total_amount': self.total_amount,
            'total_cgst': self.total_cgst,
            'total_sgst': self.total_sgst,
            'total_igst': self.total_igst,
            'bank_details': self.bank_details.to_dict(),
            'has_signature': self.has_signature,
            'has_stamp': self.has_stamp,
        }
        
        if self.service_classification:
            result['service_classification'] = self.service_classification.to_dict()
        
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

class InvoiceAnalyzer:
    def __init__(self):
        """Initialize the invoice analyzer"""
        self.nlp = spacy.load("en_core_web_sm")
        self.company_indicators = [
            'ltd', 'limited', 'llp', 'corporation', 'inc', 'private', 'pvt',
            'company', 'enterprises', 'industries', 'solutions', 'services'
        ]
        self.address_indicators = [
            'street', 'road', 'lane', 'avenue', 'floor', 'block', 'sector',
            'phase', 'district', 'state', 'pin', 'zip'
        ]
        self.service_classifier = ServiceClassifier()

    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, List[np.ndarray]]:
        """Extract text and image content from PDF"""
        text = ""
        images = []
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                    # Extract images if available (simplified version)
                    if '/XObject' in page['/Resources']:
                        x_objects = page['/Resources']['/XObject'].get_object()
                        for obj in x_objects:
                            if x_objects[obj]['/Subtype'] == '/Image':
                                try:
                                    data = x_objects[obj].get_data()
                                    if data:
                                        # Convert raw image data to numpy array
                                        nparr = np.frombuffer(data, np.uint8)
                                        try:
                                            # Try to decode as a color image
                                            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                                            if img is not None:
                                                images.append(img)
                                        except Exception as e:
                                            print(f"Warning: Could not decode image: {str(e)}")
                                except Exception as e:
                                    print(f"Warning: Could not extract image data: {str(e)}")
        except Exception as e:
            raise Exception(f"Error reading PDF file: {str(e)}")
        return text, images

    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number using regex patterns"""
        patterns = [
            r'(?i)invoice\s*(?:#|number|num|no|no\.):?\s*([A-Z0-9\-/]+)',
            r'(?i)bill\s*(?:#|number|num|no|no\.):?\s*([A-Z0-9\-/]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return "Not found"

    def extract_dates(self, text: str) -> Tuple[str, str]:
        """Extract invoice and due dates"""
        invoice_date = "Not found"
        due_date = "Not found"
        
        # Date patterns
        date_patterns = [
            r'(?i)(?:invoice|bill)\s*date:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(?i)due\s*date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(?i)date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'  # Generic date pattern
        ]
        
        # Look for dates in the text
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                if 'due' in pattern.lower():
                    due_date = match.group(1)
                else:
                    invoice_date = match.group(1)
        
        # If due date not found in standard format, look for it in terms
        if due_date == "Not found":
            due_match = re.search(r'Due\s+Date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
            if due_match:
                due_date = due_match.group(1)
        
        return invoice_date, due_date

    def extract_entities(self, text: str) -> Tuple[str, str, str, str, str, str]:
        """Extract payer and payee details including name, GSTIN, and address"""
        payer_section = ""
        payee_section = ""
        
        # Split text into lines for processing
        lines = text.split('\n')
        
        # Find bill to and ship to sections
        bill_to_start = -1
        ship_to_start = -1
        for i, line in enumerate(lines):
            if 'bill to' in line.lower():
                bill_to_start = i
            elif 'ship to' in line.lower():
                ship_to_start = i
        
        # If we found bill to section, get the next few lines
        if bill_to_start != -1:
            end_idx = ship_to_start if ship_to_start != -1 else bill_to_start + 5
            payer_section = '\n'.join(lines[bill_to_start:end_idx])
        
        # Look for supplier/seller section at the start of invoice
        supplier_section = '\n'.join(lines[:min(10, len(lines))])
        payee_section = supplier_section
        
        # Extract payer details
        payer_name = self._extract_company_name(payer_section) if payer_section else "Not found"
        payer_gstin = self._extract_gstin(payer_section) if payer_section else "Not found"
        payer_address = self._extract_address(payer_section) if payer_section else "Not found"
        
        # Extract payee details
        payee_name = self._extract_company_name(payee_section) if payee_section else "Not found"
        payee_gstin = self._extract_gstin(payee_section) if payee_section else "Not found"
        payee_address = self._extract_address(payee_section) if payee_section else "Not found"
        
        # If payer GSTIN not found in bill to section, try looking in full text
        if payer_gstin == "Not found":
            # Look for any GSTIN after "Bill To" in the full text
            bill_to_idx = text.lower().find('bill to')
            if bill_to_idx != -1:
                remaining_text = text[bill_to_idx:]
                payer_gstin = self._extract_gstin(remaining_text)
        
        return payer_name, payer_gstin, payer_address, payee_name, payee_gstin, payee_address

    def _extract_gstin(self, text: str) -> str:
        """Extract GSTIN from text"""
        gstin_patterns = [
            r'GSTIN\s*:?\s*([0-9A-Z]{15})',  # Standard format
            r'(?:GST|GSTIN|TIN)\s*(?:Number|No\.?)?\s*:?\s*([0-9A-Z]{15})',  # Variations
            r'(?<!\w)([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})(?!\w)'  # Raw GSTIN
        ]
        
        for pattern in gstin_patterns:
            gstin_matches = re.finditer(pattern, text, re.I)
            for match in gstin_matches:
                gstin = match.group(1)
                if re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$', gstin):
                    return gstin
        
        # Try one more time with a more lenient pattern
        raw_pattern = r'(?<!\w)([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z0-9]{3})(?!\w)'
        raw_matches = re.finditer(raw_pattern, text)
        for match in raw_matches:
            gstin = match.group(1)
            if len(gstin) == 15:
                return gstin
        
        return "Not found"

    def _extract_company_name(self, text: str) -> str:
        """Extract company name from text"""
        lines = text.split('\n')
        company_name = "Not found"
        
        # First try to find a line with company indicators
        for line in lines:
            line = line.strip()
            if any(indicator in line.lower() for indicator in self.company_indicators):
                # Remove GSTIN if present
                company_name = re.sub(r'GSTIN\s*:?\s*\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}', '', line)
                # Remove common prefixes
                company_name = re.sub(r'^(?:M/s\.?|Messrs\.?|To:|Bill\s+To:?)\s*', '', company_name, flags=re.I)
                company_name = company_name.strip()
                return company_name
        
        # If no company indicators found, look for lines with common business words
        business_words = ['trading', 'industries', 'corporation', 'company', 'enterprises']
        for line in lines:
            line = line.strip()
            if any(word in line.lower() for word in business_words):
                company_name = line
                break
        
        # If still not found, try NER
        if company_name == "Not found":
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ['ORG']:
                    company_name = ent.text.strip()
                    break
        
        return company_name

    def _extract_address(self, text: str) -> str:
        """Extract address from text"""
        lines = text.split('\n')
        address_lines = []
        
        # Look for address indicators and collect lines
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Skip lines with GSTIN
            if 'GSTIN' in line or re.search(r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}', line):
                continue
                
            # If line contains address indicators or postal code pattern
            if (any(indicator in line.lower() for indicator in self.address_indicators) or
                re.search(r'\b\d{6}\b', line)):  # Postal code pattern
                address_lines.append(line)
                
                # Include the next line if it exists and looks like part of address
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not any(skip in next_line for skip in ['GSTIN', 'PAN', 'Phone', 'Email']):
                        address_lines.append(next_line)
        
        # If no address found with indicators, try looking for lines with commas and postal codes
        if not address_lines:
            for i, line in enumerate(lines):
                line = line.strip()
                if not line or any(skip in line for skip in ['GSTIN', 'PAN', 'Phone', 'Email']):
                    continue
                    
                if ',' in line or re.search(r'\b\d{6}\b', line):
                    address_lines.append(line)
                    # Include the next line if it exists and looks like part of address
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and not any(skip in next_line for skip in ['GSTIN', 'PAN', 'Phone', 'Email']):
                            address_lines.append(next_line)
        
        return ' '.join(address_lines) if address_lines else "Not found"

    def extract_bank_details(self, text: str) -> BankDetails:
        """Extract bank details from text"""
        bank_name = account_holder_name = account_number = ifsc_code = branch = "Not found"
        
        # Look for bank details section
        bank_section_start = -1
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            if 'bank detail' in line.lower():
                bank_section_start = i
                break
        
        if bank_section_start != -1:
            # Get next few lines after bank details
            bank_section = '\n'.join(lines[bank_section_start:bank_section_start + 5])
            bank_lines = bank_section.split('\n')
            
            # Extract account number
            acc_match = re.search(r'(?:A/?C|account|no|number)[^0-9]*(\d[\d\s-]*\d)', bank_section, re.I)
            if acc_match:
                account_number = re.sub(r'\s+', '', acc_match.group(1))
            
            # Extract IFSC code (including ISFC misspelling)
            ifsc_match = re.search(r'(?:IFSC|RTGS|NEFT|ISFC)\s*(?:CODE|NO\.?)?\s*[-:]*\s*([A-Z]{4}0[A-Z0-9]{6})', bank_section, re.I)
            if ifsc_match:
                ifsc_code = ifsc_match.group(1)
                # Determine bank name from IFSC code
                bank_code = ifsc_code[:4]
                bank_mapping = {
                    'FDRL': 'Federal Bank',
                    'SBIN': 'State Bank of India',
                    'HDFC': 'HDFC Bank',
                    'ICIC': 'ICICI Bank',
                    'UTIB': 'Axis Bank',
                    'KKBK': 'Kotak Mahindra Bank',
                    'YESB': 'Yes Bank',
                    'IDIB': 'IDBI Bank',
                    'PUNB': 'Punjab National Bank',
                    'CNRB': 'Canara Bank',
                    'UBIN': 'Union Bank of India',
                    'IOBA': 'Indian Overseas Bank',
                    'UCBA': 'UCO Bank',
                    'SYNB': 'Syndicate Bank',
                    'CORP': 'Corporation Bank',
                    'ANDB': 'Andhra Bank',
                    'ALLA': 'Allahabad Bank',
                    'BARB': 'Bank of Baroda',
                    'MAHB': 'Bank of Maharashtra',
                    'ORBC': 'Oriental Bank of Commerce',
                    'BKDN': 'Dena Bank',
                    'CBIN': 'Central Bank of India',
                    'VIJB': 'Vijaya Bank',
                    'UBOI': 'United Bank of India',
                    'SCBL': 'Standard Chartered Bank'
                }
                bank_name = bank_mapping.get(bank_code, "Unknown Bank")
            
            # Extract account holder name
            for line in bank_lines:
                # First try to find account holder name after "Bank:" or similar
                holder_match = re.search(r'(?:Bank|Account)\s*Details?\s*:(.+?)(?=\s*(?:A/?C|account|no|number|code|ifsc|rtgs|micr)|\s*$)', line, re.I)
                if holder_match:
                    account_holder_name = holder_match.group(1).strip()
                    break
            
            # Clean up account holder name
            if account_holder_name != "Not found":
                account_holder_name = re.sub(r'^(?:Name|Bank|Account)\s*:?\s*', '', account_holder_name, flags=re.I)
                account_holder_name = re.sub(r'\s*(?:Account|Number|Details).*$', '', account_holder_name, flags=re.I)
                account_holder_name = account_holder_name.strip()
        
        return BankDetails(bank_name, account_holder_name, account_number, ifsc_code, branch)

    def extract_gst_details(self, text: str) -> Tuple[float, float, float]:
        """Extract total GST amounts from text"""
        cgst = sgst = igst = 0.0
        
        # Look for total GST amounts in summary section
        gst_patterns = {
            'cgst': [
                r'CGST\s*(?:9|@)?\s*\((?:\d+(?:\.\d+)?)%\)\s*(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)',
                r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*CGST\s*(?:9|@)?\s*\((?:\d+(?:\.\d+)?)%\)',
                r'CGST\s*(?:9|@)?\s*(?:\d+(?:\.\d+)?)%\s*(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)',
                r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*CGST\s*(?:9|@)?\s*(?:\d+(?:\.\d+)?)%'
            ],
            'sgst': [
                r'SGST\s*(?:9|@)?\s*\((?:\d+(?:\.\d+)?)%\)\s*(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)',
                r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*SGST\s*(?:9|@)?\s*\((?:\d+(?:\.\d+)?)%\)',
                r'SGST\s*(?:9|@)?\s*(?:\d+(?:\.\d+)?)%\s*(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)',
                r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*SGST\s*(?:9|@)?\s*(?:\d+(?:\.\d+)?)%'
            ],
            'igst': [
                r'IGST\s*(?:9|@)?\s*\((?:\d+(?:\.\d+)?)%\)\s*(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)',
                r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*IGST\s*(?:9|@)?\s*\((?:\d+(?:\.\d+)?)%\)',
                r'IGST\s*(?:9|@)?\s*(?:\d+(?:\.\d+)?)%\s*(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)',
                r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*IGST\s*(?:9|@)?\s*(?:\d+(?:\.\d+)?)%'
            ]
        }
        
        # Try to find GST amounts in summary section first
        summary_start = -1
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in ['sub total', 'subtotal', 'summary', 'total amount']):
                summary_start = i
                break
        
        if summary_start != -1:
            summary_text = '\n'.join(lines[summary_start:])
            
            for gst_type, patterns in gst_patterns.items():
                for pattern in patterns:
                    gst_match = re.search(pattern, summary_text)
                    if gst_match:
                        try:
                            amount_str = gst_match.group(1).replace(',', '')
                            amount = float(amount_str)
                            if amount > 0:  # Only use non-zero amounts
                                if gst_type == 'cgst':
                                    cgst = amount
                                elif gst_type == 'sgst':
                                    sgst = amount
                                elif gst_type == 'igst':
                                    igst = amount
                                break
                        except (ValueError, AttributeError):
                            continue
        
        return cgst, sgst, igst

    def extract_items(self, text: str) -> List[InvoiceItem]:
        """Extract item details including HSN/SAC and GST"""
        items = []
        
        # Look for item section
        item_section = re.search(r'(?i)(?:Sr\.?\s*No\.?|Item|Description|Particulars).*?(?=Notes|Sub\s*Total|Total\s+Amount|Balance|$)', text, re.DOTALL)
        
        if item_section:
            section_text = item_section.group(0)
            
            # Split into lines and process each line
            lines = section_text.split('\n')
            current_item = None
            item_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip header lines
                if re.search(r'(?i)^(Sr\.?\s*No\.?|Item|Description|HSN|SAC|Qty|Rate|Amount|CGST|SGST|IGST)$', line):
                    continue
                
                # If line starts with a number, it's likely a new item
                if re.match(r'^\d+\s', line):
                    # Process previous item if exists
                    if item_lines:
                        self._process_item_lines(item_lines, items)
                    item_lines = [line]
                else:
                    # Append to current item description
                    if item_lines:
                        item_lines.append(line)
            
            # Process the last item
            if item_lines:
                self._process_item_lines(item_lines, items)
        
        return items
        
    def _process_item_lines(self, lines: List[str], items: List[InvoiceItem]):
        """Process a group of lines that belong to a single item"""
        combined_line = ' '.join(lines)
        
        # Look for HSN/SAC code
        hsn_match = re.search(r'(\d{8}|\d{6}|\d{4})', combined_line)
        if not hsn_match:
            return
            
        # Extract description (text before HSN code)
        desc_text = combined_line[:combined_line.find(hsn_match.group(0))].strip()
        desc_text = re.sub(r'^\d+\s+', '', desc_text)  # Remove leading item number
        
        # Look for quantity and unit price
        qty_match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:nos|pcs|units|pieces)', combined_line, re.I)
        
        # Try different rate patterns
        rate_patterns = [
            # Rate between quantity and GST/amount
            r'(?:pcs|pieces)\s+(?:@\s*)?(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*(?=\s*(?:\d|CGST|SGST|IGST))',
            # Rate after quantity
            r'(?:nos|pcs|units|pieces)\s+(?:@\s*)?(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)',
            # Rate as a standalone number
            r'(?:@\s*)?(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:/-|per\s+pc|\b)'
        ]
        
        rate = 0.0
        for pattern in rate_patterns:
            rate_match = re.search(pattern, combined_line)
            if rate_match:
                try:
                    rate = float(rate_match.group(1).replace(',', ''))
                    if rate > 0 and rate < 1000000:  # Only use reasonable rates
                        break
                except ValueError:
                    continue
        
        # Look for GST amounts and percentages
        gst_patterns = {
            'cgst': [
                r'(\d+(?:,\d+)?(?:\.\d+)?)\s*\(\s*\d+(?:\.\d+)?%\s*\)',  # Amount (rate%)
                r'\(\s*\d+(?:\.\d+)?%\s*\)\s*(\d+(?:,\d+)?(?:\.\d+)?)',  # (rate%) Amount
                r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*(?=\s*\(\s*\d+(?:\.\d+)?%\s*\))',  # Amount before (rate%)
                r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?=\s*\(\s*\d+(?:\.\d+)?%\s*\))'  # Amount before (rate%)
            ],
            'sgst': [
                r'(\d+(?:,\d+)?(?:\.\d+)?)\s*\(\s*\d+(?:\.\d+)?%\s*\)',  # Amount (rate%)
                r'\(\s*\d+(?:\.\d+)?%\s*\)\s*(\d+(?:,\d+)?(?:\.\d+)?)',  # (rate%) Amount
                r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*(?=\s*\(\s*\d+(?:\.\d+)?%\s*\))',  # Amount before (rate%)
                r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?=\s*\(\s*\d+(?:\.\d+)?%\s*\))'  # Amount before (rate%)
            ],
            'igst': [
                r'(\d+(?:,\d+)?(?:\.\d+)?)\s*\(\s*\d+(?:\.\d+)?%\s*\)',  # Amount (rate%)
                r'\(\s*\d+(?:\.\d+)?%\s*\)\s*(\d+(?:,\d+)?(?:\.\d+)?)',  # (rate%) Amount
                r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*(?=\s*\(\s*\d+(?:\.\d+)?%\s*\))',  # Amount before (rate%)
                r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?=\s*\(\s*\d+(?:\.\d+)?%\s*\))'  # Amount before (rate%)
            ]
        }
        
        gst_values = {'cgst': 0.0, 'sgst': 0.0, 'igst': 0.0}
        
        # First find all GST percentages and amounts
        gst_amounts = []
        gst_percent_pattern = r'(\d+(?:,\d+)?(?:\.\d+)?)\s*\(\s*(\d+(?:\.\d+)?)%\s*\)'
        for match in re.finditer(gst_percent_pattern, combined_line):
            try:
                amount = float(match.group(1).replace(',', ''))
                percent = float(match.group(2))
                gst_amounts.append((amount, percent))
            except (ValueError, AttributeError):
                continue
        
        # Then assign them to CGST/SGST/IGST based on order and context
        if len(gst_amounts) == 2 and abs(gst_amounts[0][1] - gst_amounts[1][1]) < 0.1:
            # If we have two equal percentages, it's likely CGST and SGST
            gst_values['cgst'] = gst_amounts[0][0]
            gst_values['sgst'] = gst_amounts[1][0]
        elif len(gst_amounts) == 1:
            # If we have one percentage, check if it's IGST
            if 'igst' in combined_line.lower():
                gst_values['igst'] = gst_amounts[0][0]
            else:
                # Try to determine based on percentage
                if abs(gst_amounts[0][1] - 18.0) < 0.1:
                    gst_values['igst'] = gst_amounts[0][0]
                elif abs(gst_amounts[0][1] - 9.0) < 0.1:
                    # Could be either CGST or SGST, try to determine from context
                    if 'cgst' in combined_line.lower():
                        gst_values['cgst'] = gst_amounts[0][0]
                    elif 'sgst' in combined_line.lower():
                        gst_values['sgst'] = gst_amounts[0][0]
        
        # Look for amount at the end of the line or before Notes/Total
        amount_patterns = [
            r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*(?=\s*(?:Notes|Sub Total|Total|$))',
            r'(?:Rs\.?|INR|\u20b9)?\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*$'
        ]
        
        amount = 0.0
        for pattern in amount_patterns:
            amount_match = re.search(pattern, combined_line)
            if amount_match:
                try:
                    amount = float(amount_match.group(1).replace(',', ''))
                    if amount > 0:  # Only use non-zero amounts
                        break
                except ValueError:
                    continue
        
        # Clean up amounts (remove commas)
        qty = float(qty_match.group(1).replace(',', '')) if qty_match else 1.0
        
        # If we have quantity and rate but no amount, calculate it
        if amount == 0.0 and qty > 0 and rate > 0:
            amount = qty * rate
        # If we have amount and quantity but no rate, calculate it
        elif rate == 0.0 and qty > 0 and amount > 0:
            rate = amount / qty
        
        items.append(InvoiceItem(
            description=desc_text,
            quantity=qty,
            rate=rate,
            hsn_sac=hsn_match.group(1),
            amount=amount,
            cgst=gst_values['cgst'],
            sgst=gst_values['sgst'],
            igst=gst_values['igst']
        ))

    def extract_place_of_supply(self, text: str) -> str:
        """Extract place of supply"""
        place = "Not found"
        
        # Look for place of supply with variations
        patterns = [
            r'(?i):\s*([^:\n(]+?)\s*\(\d+\)\s*(?:Place\s+[Oo]f\s+Supply)',  # Delhi (07) Place Of Supply
            r'(?i)(?:Place\s+[Oo]f\s+Supply|POS)\s*:?\s*([^:\n]+?)(?=\n|$)',  # Place of Supply: Delhi
            r'(?i):\s*([^:\n(]+?)\s*\(\d+\)'  # : Delhi (07)
        ]
        
        for pattern in patterns:
            pos_match = re.search(pattern, text)
            if pos_match:
                place = pos_match.group(1).strip()
                # Clean up the place name
                place = re.sub(r'\s*\(\d+\)', '', place).strip()
                if place:
                    break
        
        return place

    def has_signature(self, text: str) -> bool:
        """Check if invoice has signature"""
        signature_indicators = [
            'authorized signatory',
            'authorized signature',
            'signature',
            'signed by',
            'digitally signed'
        ]
        return any(indicator in text.lower() for indicator in signature_indicators)

    def has_stamp(self, text: str) -> bool:
        """Check if invoice has stamp"""
        stamp_keywords = [
            'stamp', 'seal', 'stamped', 'sealed',
            'company seal', 'office seal', 'business seal',
            'rubber stamp', 'common seal', 'official stamp',
            'authorized stamp', 'authorised stamp'
        ]
        
        # First check for explicit stamp mentions
        text_lower = text.lower()
        for keyword in stamp_keywords:
            if keyword in text_lower:
                return True
        
        # Then check for signature section with stamp-like indicators
        signature_section = ""
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'signature' in line.lower() or 'authorized' in line.lower():
                # Get a few lines around the signature
                start = max(0, i-3)
                end = min(len(lines), i+4)
                signature_section = '\n'.join(lines[start:end])
                break
        
        if signature_section:
            # Look for stamp-like patterns near signature
            stamp_patterns = [
                r'for\s+[A-Z\s&]+\s*$',  # "For COMPANY NAME"
                r'\(.*\)\s*$',  # Text in parentheses at end
                r'authorized\s+signatory',  # Authorized signatory
                r'proprietor',  # Proprietor
                r'director',  # Director
                r'partner'  # Partner
            ]
            
            for pattern in stamp_patterns:
                if re.search(pattern, signature_section, re.I):
                    return True
        
        return False

    def detect_signature_and_stamp(self, images: List[np.ndarray]) -> Tuple[bool, bool]:
        """Detect presence of signature and stamp in images"""
        # Simplified version without Tesseract dependency
        has_signature = False
        has_stamp = False
        
        if not images:  # If no images found
            return False, False
            
        for img in images:
            # Convert to grayscale
            try:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Basic image analysis
                mean_value = np.mean(gray)
                std_value = np.std(gray)
                
                # Assume signature/stamp exists if there's significant variation in the image
                if std_value > 40:  # Threshold for variation
                    has_signature = True
                if mean_value < 200 and std_value > 50:  # Different threshold for stamps
                    has_stamp = True
            except Exception as e:
                print(f"Warning: Error processing image: {str(e)}")
                continue
        
        return has_signature, has_stamp

    def analyze_invoice(self, pdf_path: str) -> InvoiceAnalysis:
        """
        Analyze PDF invoice and extract all required information
        
        Args:
            pdf_path: Path to the PDF invoice file
            
        Returns:
            InvoiceAnalysis object containing structured invoice information
        """
        # Extract text and images from PDF
        text, images = self.extract_text_from_pdf(pdf_path)
        
        # Extract invoice details
        invoice_number = self.extract_invoice_number(text)
        invoice_date, due_date = self.extract_dates(text)
        
        # Extract terms
        terms_match = re.search(r'(?i)terms.*?(?=\n\n|$)', text, re.DOTALL)
        terms = terms_match.group(0) if terms_match else "Not found"
        
        # Extract entity details
        payer_name, payer_gstin, payer_addr, payee_name, payee_gstin, payee_addr = self.extract_entities(text)
        
        # Extract place of supply
        place_of_supply = self.extract_place_of_supply(text)
        
        # Extract items and calculate totals
        items = self.extract_items(text)
        total_amount = sum(item.amount for item in items)
        total_cgst, total_sgst, total_igst = self.extract_gst_details(text)
        
        # Extract bank details
        bank_details = self.extract_bank_details(text)
        
        # Detect signature and stamp
        has_signature = self.has_signature(text)
        has_stamp = self.has_stamp(text)
        
        # Get service classification
        hsn_sac = items[0].hsn_sac if items else None
        service_classification = self.service_classifier.classify(text, hsn_sac)
        
        return InvoiceAnalysis(
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            due_date=due_date,
            terms=terms,
            payer_name=payer_name,
            payer_gstin=payer_gstin,
            payer_address=payer_addr,
            payee_name=payee_name,
            payee_gstin=payee_gstin,
            payee_address=payee_addr,
            place_of_supply=place_of_supply,
            items=items,
            total_amount=total_amount,
            total_cgst=total_cgst,
            total_sgst=total_sgst,
            total_igst=total_igst,
            bank_details=bank_details,
            has_signature=has_signature,
            has_stamp=has_stamp,
            service_classification=service_classification
        )

# Example usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python invoice_analyzer.py <path_to_invoice.pdf>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    analyzer = InvoiceAnalyzer()
    try:
        result = analyzer.analyze_invoice(pdf_path)
        print(result.to_json())
    except Exception as e:
        print(f"Error analyzing invoice: {str(e)}")
        sys.exit(1)
