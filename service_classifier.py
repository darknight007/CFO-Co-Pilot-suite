from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re
from enum import Enum

class ServiceType(Enum):
    """Types of services that can be provided"""
    CONSULTING = "Consulting"
    SAAS = "SaaS"
    ROYALTY = "Royalty"
    GOODS = "Goods"
    PRINTING = "Printing"
    ADVERTISING = "Advertising"
    COMMISSION = "Commission"
    RENT = "Rent"
    PROFESSIONAL = "Professional Services"
    TECHNICAL = "Technical Services"
    MANPOWER = "Manpower Services"
    OTHER = "Other"

class TransactionType(Enum):
    """Types of transactions based on relationship"""
    INTRA_GROUP = "Intra-group"
    THIRD_PARTY = "Third-party"
    UNKNOWN = "Unknown"

class PaymentTerms(Enum):
    """Types of payment terms"""
    ADVANCE = "Advance"
    DEFERRED = "Deferred"
    MILESTONE = "Milestone"
    IMMEDIATE = "Immediate"
    UNKNOWN = "Unknown"

@dataclass
class Currency:
    """Currency information"""
    code: str
    symbol: str
    name: str

class CurrencyHelper:
    """Helper class for currency detection"""
    CURRENCIES = {
        'INR': Currency('INR', '₹', 'Indian Rupee'),
        'USD': Currency('USD', '$', 'US Dollar'),
        'EUR': Currency('EUR', '€', 'Euro'),
        'GBP': Currency('GBP', '£', 'British Pound'),
    }
    
    SYMBOLS_TO_CODE = {
        '₹': 'INR',
        'Rs': 'INR',
        'INR': 'INR',
        '$': 'USD',
        'USD': 'USD',
        '€': 'EUR',
        'EUR': 'EUR',
        '£': 'GBP',
        'GBP': 'GBP'
    }

@dataclass
class ServiceClassification:
    """Classification of service and transaction details"""
    service_type: ServiceType
    transaction_type: TransactionType
    transaction_value: float
    currency: Currency
    payment_terms: PaymentTerms
    confidence_score: float

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'service_type': self.service_type.value,
            'transaction_type': self.transaction_type.value,
            'transaction_value': self.transaction_value,
            'currency': {
                'code': self.currency.code,
                'symbol': self.currency.symbol,
                'name': self.currency.name
            },
            'payment_terms': self.payment_terms.value,
            'confidence_score': self.confidence_score
        }

class ServiceClassifier:
    """Classifier for service type and transaction details"""
    
    def __init__(self):
        # Keywords indicating service types
        self.service_keywords = {
            ServiceType.CONSULTING: [
                'consulting', 'advisory', 'consultation', 'strategy', 'advice'
            ],
            ServiceType.SAAS: [
                'software', 'subscription', 'platform', 'cloud', 'license', 'saas'
            ],
            ServiceType.ROYALTY: [
                'royalty', 'intellectual property', 'patent', 'trademark', 'copyright'
            ],
            ServiceType.GOODS: [
                'goods', 'product', 'material', 'supply', 'item', 'merchandise'
            ],
            ServiceType.PRINTING: [
                'print', 'brochure', 'booklet', 'leaflet', 'catalogue', 'stationery'
            ],
            ServiceType.ADVERTISING: [
                'advertising', 'marketing', 'promotion', 'campaign', 'media'
            ],
            ServiceType.COMMISSION: [
                'commission', 'brokerage', 'agency', 'referral'
            ],
            ServiceType.RENT: [
                'rent', 'lease', 'hiring', 'rental'
            ],
            ServiceType.PROFESSIONAL: [
                'professional', 'legal', 'accounting', 'audit'
            ],
            ServiceType.TECHNICAL: [
                'technical', 'engineering', 'development', 'maintenance'
            ],
            ServiceType.MANPOWER: [
                'manpower', 'staffing', 'personnel', 'recruitment'
            ]
        }
        
        # Keywords indicating intra-group transactions
        self.intra_group_keywords = [
            'group company', 'subsidiary', 'holding company', 'affiliate',
            'related party', 'parent company', 'sister concern'
        ]
        
        # Keywords indicating payment terms
        self.payment_terms_keywords = {
            PaymentTerms.ADVANCE: [
                'advance', 'prepaid', 'payment in advance', 'pay before'
            ],
            PaymentTerms.DEFERRED: [
                'net', 'days', 'credit period', 'payment after', 'due in'
            ],
            PaymentTerms.MILESTONE: [
                'milestone', 'phase', 'completion', 'stage', 'deliverable'
            ],
            PaymentTerms.IMMEDIATE: [
                'immediate', 'due on receipt', 'payable immediately', 'cash on delivery'
            ]
        }

    def classify(self, invoice_text: str, hsn_sac_code: Optional[str] = None) -> ServiceClassification:
        """Classify service type and transaction details from invoice text"""
        
        # Determine service type
        service_type = self._classify_service_type(invoice_text, hsn_sac_code)
        
        # Determine transaction type
        transaction_type = self._classify_transaction_type(invoice_text)
        
        # Extract currency and amount
        currency, amount = self._extract_currency_and_amount(invoice_text)
        
        # Determine payment terms
        payment_terms = self._classify_payment_terms(invoice_text)
        
        # Calculate confidence score based on keyword matches
        confidence_score = self._calculate_confidence_score(
            invoice_text, service_type, transaction_type, payment_terms
        )
        
        return ServiceClassification(
            service_type=service_type,
            transaction_type=transaction_type,
            transaction_value=amount,
            currency=currency,
            payment_terms=payment_terms,
            confidence_score=confidence_score
        )

    def _classify_service_type(self, text: str, hsn_sac_code: Optional[str] = None) -> ServiceType:
        """Classify the type of service based on text and HSN/SAC code"""
        text = text.lower()
        
        # First check HSN/SAC code if available
        if hsn_sac_code:
            # Example HSN/SAC mappings (extend as needed)
            if hsn_sac_code.startswith('49'):  # Chapter 49: Printed books, newspapers, etc.
                return ServiceType.PRINTING
            elif hsn_sac_code.startswith('99'):  # Services
                if hsn_sac_code in ['998311', '998312']:  # Consulting services
                    return ServiceType.CONSULTING
        
        # Check keywords in text
        max_matches = 0
        best_type = ServiceType.OTHER
        
        for service_type, keywords in self.service_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > max_matches:
                max_matches = matches
                best_type = service_type
        
        return best_type

    def _classify_transaction_type(self, text: str) -> TransactionType:
        """Classify the transaction as intra-group or third-party"""
        text = text.lower()
        
        for keyword in self.intra_group_keywords:
            if keyword in text:
                return TransactionType.INTRA_GROUP
        
        # If no intra-group keywords found, assume third-party
        return TransactionType.THIRD_PARTY

    def _extract_currency_and_amount(self, text: str) -> Tuple[Currency, float]:
        """Extract currency and total amount from text"""
        text = text.replace(',', '')  # Remove commas from numbers
        
        # Try to find currency symbol/code and amount
        currency_pattern = r'(?:Rs\.?|INR|\$|USD|€|EUR|£|GBP)?\s*(\d+(?:\.\d{2})?)'
        
        # First look for total amount
        total_patterns = [
            r'total\s+(?:amount|value)?\s*:?\s*(?:Rs\.?|INR|\$|USD|€|EUR|£|GBP)?\s*(\d+(?:\.\d{2})?)',
            r'(?:grand|net|final)\s+total\s*:?\s*(?:Rs\.?|INR|\$|USD|€|EUR|£|GBP)?\s*(\d+(?:\.\d{2})?)',
            r'amount\s+payable\s*:?\s*(?:Rs\.?|INR|\$|USD|€|EUR|£|GBP)?\s*(\d+(?:\.\d{2})?)',
            currency_pattern
        ]
        
        amount = 0.0
        currency = CurrencyHelper.CURRENCIES['INR']  # Default to INR
        
        # Try to find currency and amount
        for pattern in total_patterns:
            matches = re.finditer(pattern, text, re.I)
            for match in matches:
                # Look for currency symbol/code before the amount
                pre_amount = text[max(0, match.start() - 10):match.start()]
                for symbol, code in CurrencyHelper.SYMBOLS_TO_CODE.items():
                    if symbol in pre_amount:
                        currency = CurrencyHelper.CURRENCIES[code]
                        break
                
                try:
                    amount = float(match.group(1))
                    if amount > 0:  # Found a valid amount
                        return currency, amount
                except (ValueError, IndexError):
                    continue
        
        return currency, amount

    def _classify_payment_terms(self, text: str) -> PaymentTerms:
        """Classify payment terms from text"""
        text = text.lower()
        
        for terms, keywords in self.payment_terms_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return terms
        
        return PaymentTerms.UNKNOWN

    def _calculate_confidence_score(
        self, text: str, 
        service_type: ServiceType,
        transaction_type: TransactionType,
        payment_terms: PaymentTerms
    ) -> float:
        """Calculate confidence score for the classification"""
        score = 0.0
        total_factors = 3  # Number of classification aspects
        
        # Service type confidence
        if service_type != ServiceType.OTHER:
            keywords = self.service_keywords.get(service_type, [])
            matches = sum(1 for keyword in keywords if keyword in text.lower())
            score += min(matches / len(keywords), 1.0)
        
        # Transaction type confidence
        if transaction_type != TransactionType.UNKNOWN:
            score += 1.0
        
        # Payment terms confidence
        if payment_terms != PaymentTerms.UNKNOWN:
            score += 1.0
        
        return score / total_factors
