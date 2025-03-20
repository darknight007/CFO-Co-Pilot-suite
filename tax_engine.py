from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum
from datetime import datetime

class TaxJurisdiction(Enum):
    """Major tax jurisdictions"""
    INDIA = "India"
    USA = "United States"
    UK = "United Kingdom"
    EU_DE = "Germany"  # Example EU country
    EU_FR = "France"
    SINGAPORE = "Singapore"

class ServiceCategory(Enum):
    """Service categories for tax determination"""
    CONSULTING = "Consulting"
    TECHNICAL = "Technical Services"
    PROFESSIONAL = "Professional Services"
    ROYALTY = "Royalty/License"
    SAAS = "Software as a Service"
    GOODS = "Goods"
    PRINTING = "Printing"
    ADVERTISING = "Advertising"
    COMMISSION = "Commission"
    RENT = "Rent"
    MANPOWER = "Manpower Services"
    CLOUD_SERVICES = "Cloud Services"
    DATA_PROCESSING = "Data Processing"
    RESEARCH = "Research and Development"
    LEGAL = "Legal Services"
    ACCOUNTING = "Accounting Services"
    DIGITAL_CONTENT = "Digital Content"
    TELECOM = "Telecommunication Services"
    FINANCIAL = "Financial Services"
    INSURANCE = "Insurance Services"
    ECOMMERCE = "E-commerce Services"

class TaxType(Enum):
    """Types of taxes"""
    WITHHOLDING = "Withholding Tax"
    TDS = "Tax Deducted at Source"
    VAT = "Value Added Tax"
    GST = "Goods and Services Tax"
    CGST = "Central Goods and Services Tax"
    SGST = "State Goods and Services Tax"
    RCM = "Reverse Charge Mechanism"
    CORPORATION = "Corporation Tax"
    PERMANENT_ESTABLISHMENT = "Permanent Establishment Tax"
    CIS = "Construction Industry Scheme"  # UK specific
    MWST = "Mehrwertsteuer"  # German VAT
    TVA = "Taxe sur la Valeur Ajoutée"  # French VAT

@dataclass
class TaxRate:
    """Tax rate with conditions"""
    rate: float
    currency_threshold: Optional[float] = None
    currency: str = "USD"
    notes: Optional[str] = None

@dataclass
class TaxForm:
    """Tax form details"""
    form_number: str
    name: str
    filing_deadline: str
    notes: Optional[str] = None

@dataclass
class DTAATreaty:
    """Double Tax Avoidance Agreement details"""
    country1: str
    country2: str
    effective_date: datetime
    withholding_rates: Dict[str, float]
    permanent_establishment_days: int
    special_provisions: List[str]

@dataclass
class TaxAdvice:
    """Tax advice for a specific scenario"""
    applicable_taxes: Dict[TaxType, TaxRate]
    filing_requirements: List[TaxForm]
    dtaa_treaty: Optional[DTAATreaty]
    permanent_establishment_risk: bool
    exemptions: List[str]
    compliance_notes: List[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "applicable_taxes": {
                tax_type.value: {
                    "rate": rate.rate,
                    "currency_threshold": rate.currency_threshold,
                    "currency": rate.currency,
                    "notes": rate.notes
                } for tax_type, rate in self.applicable_taxes.items()
            },
            "filing_requirements": [
                {
                    "form_number": form.form_number,
                    "name": form.name,
                    "filing_deadline": form.filing_deadline,
                    "notes": form.notes
                } for form in self.filing_requirements
            ],
            "dtaa_treaty": {
                "country1": self.dtaa_treaty.country1,
                "country2": self.dtaa_treaty.country2,
                "effective_date": self.dtaa_treaty.effective_date.isoformat(),
                "withholding_rates": self.dtaa_treaty.withholding_rates,
                "permanent_establishment_days": self.dtaa_treaty.permanent_establishment_days,
                "special_provisions": self.dtaa_treaty.special_provisions
            } if self.dtaa_treaty else None,
            "permanent_establishment_risk": self.permanent_establishment_risk,
            "exemptions": self.exemptions,
            "compliance_notes": self.compliance_notes
        }

class TaxEngine:
    """Engine for determining applicable taxes based on jurisdiction and service type"""
    
    def __init__(self):
        self._load_tax_treaties()
        self._load_tax_rates()
        self._load_compliance_requirements()

    def _load_tax_treaties(self):
        """Load DTAA treaties data"""
        self.tax_treaties = {
            # India-US DTAA
            ("India", "United States"): DTAATreaty(
                country1="India",
                country2="United States",
                effective_date=datetime(1991, 1, 1),
                withholding_rates={
                    "royalty": 15.0,
                    "technical_services": 15.0,
                    "interest": 15.0,
                    "dividend": 15.0
                },
                permanent_establishment_days=90,
                special_provisions=[
                    "Article 12 covers Royalties and Technical Services",
                    "Reduced rates available with Tax Residency Certificate"
                ]
            ),
            # India-UK DTAA
            ("India", "United Kingdom"): DTAATreaty(
                country1="India",
                country2="United Kingdom",
                effective_date=datetime(1994, 1, 1),
                withholding_rates={
                    "royalty": 15.0,
                    "technical_services": 15.0,
                    "interest": 15.0,
                    "dividend": 15.0
                },
                permanent_establishment_days=90,
                special_provisions=[
                    "Article 13 covers Royalties and Technical Services",
                    "Reduced rates available with Tax Residency Certificate"
                ]
            ),
            # Singapore-France DTAA
            ("Singapore", "France"): DTAATreaty(
                country1="Singapore",
                country2="France",
                effective_date=datetime(2016, 1, 1),
                withholding_rates={
                    "royalty": 5.0,
                    "technical_services": 0.0,  # No withholding on services
                    "interest": 10.0,
                    "dividend": 15.0
                },
                permanent_establishment_days=183,
                special_provisions=[
                    "No withholding tax on technical services",
                    "Digital services may be subject to DST"
                ]
            )
        }
        
        # Add EU member states for VAT handling
        self.eu_member_states = {
            "Germany", "France", "Italy", "Spain", "Netherlands",
            "Belgium", "Austria", "Ireland", "Greece", "Portugal",
            "Finland", "Sweden", "Denmark", "Poland", "Czech Republic",
            "Romania", "Hungary", "Slovakia", "Croatia", "Bulgaria",
            "Lithuania", "Slovenia", "Latvia", "Estonia", "Cyprus",
            "Luxembourg", "Malta"
            # Note: UK removed from EU member states post-Brexit
        }

    def _load_tax_rates(self):
        """Load tax rates for different jurisdictions"""
        self.tax_rates = {
            TaxJurisdiction.INDIA: {
                ServiceCategory.TECHNICAL: {
                    TaxType.TDS: TaxRate(10.0, notes="Section 194J applicable"),
                    TaxType.GST: TaxRate(18.0),
                    TaxType.RCM: TaxRate(18.0, notes="For foreign vendors")
                },
                ServiceCategory.CONSULTING: {
                    TaxType.TDS: TaxRate(10.0, notes="Section 194J applicable"),
                    TaxType.GST: TaxRate(18.0)
                },
                ServiceCategory.CLOUD_SERVICES: {
                    TaxType.TDS: TaxRate(2.0, notes="Section 194C applicable"),
                    TaxType.GST: TaxRate(18.0),
                    TaxType.RCM: TaxRate(18.0, notes="For foreign vendors")
                },
                ServiceCategory.DATA_PROCESSING: {
                    TaxType.TDS: TaxRate(2.0, notes="Section 194C applicable"),
                    TaxType.GST: TaxRate(18.0)
                },
                ServiceCategory.RESEARCH: {
                    TaxType.TDS: TaxRate(10.0, notes="Section 194J applicable"),
                    TaxType.GST: TaxRate(18.0)
                },
                ServiceCategory.LEGAL: {
                    TaxType.TDS: TaxRate(10.0, notes="Section 194J applicable"),
                    TaxType.GST: TaxRate(18.0)
                },
                ServiceCategory.ACCOUNTING: {
                    TaxType.TDS: TaxRate(10.0, notes="Section 194J applicable"),
                    TaxType.GST: TaxRate(18.0)
                },
                ServiceCategory.DIGITAL_CONTENT: {
                    TaxType.TDS: TaxRate(2.0, notes="Section 194C applicable"),
                    TaxType.GST: TaxRate(18.0),
                    TaxType.RCM: TaxRate(18.0, notes="For foreign vendors")
                },
                ServiceCategory.TELECOM: {
                    TaxType.TDS: TaxRate(2.0, notes="Section 194C applicable"),
                    TaxType.GST: TaxRate(18.0)
                },
                ServiceCategory.FINANCIAL: {
                    TaxType.TDS: TaxRate(10.0, notes="Section 194J applicable"),
                    TaxType.GST: TaxRate(18.0, notes="Certain services exempt")
                },
                ServiceCategory.INSURANCE: {
                    TaxType.TDS: TaxRate(5.0, notes="Section 194D applicable"),
                    TaxType.GST: TaxRate(18.0)
                },
                ServiceCategory.ECOMMERCE: {
                    TaxType.TDS: TaxRate(1.0, notes="Section 194-O applicable"),
                    TaxType.GST: TaxRate(18.0)
                }
            },
            TaxJurisdiction.EU_FR: {
                ServiceCategory.TECHNICAL: {
                    TaxType.TVA: TaxRate(20.0, notes="Standard French VAT rate"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="For non-EU residents")
                },
                ServiceCategory.CLOUD_SERVICES: {
                    TaxType.TVA: TaxRate(20.0, notes="Digital services VAT"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="For non-EU digital services")
                },
                ServiceCategory.DATA_PROCESSING: {
                    TaxType.TVA: TaxRate(20.0, notes="Standard French VAT rate")
                },
                ServiceCategory.RESEARCH: {
                    TaxType.TVA: TaxRate(20.0, notes="Standard French VAT rate"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="For non-EU R&D services")
                },
                ServiceCategory.DIGITAL_CONTENT: {
                    TaxType.TVA: TaxRate(20.0, notes="Digital services VAT"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="For non-EU digital content")
                },
                ServiceCategory.FINANCIAL: {
                    TaxType.TVA: TaxRate(0.0, notes="Financial services exempt from VAT")
                },
                ServiceCategory.INSURANCE: {
                    TaxType.TVA: TaxRate(0.0, notes="Insurance services exempt from VAT")
                },
                ServiceCategory.ECOMMERCE: {
                    TaxType.TVA: TaxRate(20.0, notes="Digital services VAT"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="For non-EU e-commerce")
                }
            },
            TaxJurisdiction.SINGAPORE: {
                ServiceCategory.TECHNICAL: {
                    TaxType.GST: TaxRate(8.0, notes="Standard Singapore GST rate"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="Technical service withholding")
                },
                ServiceCategory.CLOUD_SERVICES: {
                    TaxType.GST: TaxRate(8.0, notes="Standard Singapore GST rate"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="Digital service withholding")
                },
                ServiceCategory.DATA_PROCESSING: {
                    TaxType.GST: TaxRate(8.0, notes="Standard Singapore GST rate"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="Technical service withholding")
                },
                ServiceCategory.RESEARCH: {
                    TaxType.GST: TaxRate(8.0, notes="Standard Singapore GST rate"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="Technical service withholding")
                },
                ServiceCategory.DIGITAL_CONTENT: {
                    TaxType.GST: TaxRate(8.0, notes="Standard Singapore GST rate"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="Digital service withholding")
                },
                ServiceCategory.FINANCIAL: {
                    TaxType.GST: TaxRate(0.0, notes="Financial services exempt from GST")
                },
                ServiceCategory.INSURANCE: {
                    TaxType.GST: TaxRate(0.0, notes="Insurance services exempt from GST")
                },
                ServiceCategory.ECOMMERCE: {
                    TaxType.GST: TaxRate(8.0, notes="Standard Singapore GST rate"),
                    TaxType.WITHHOLDING: TaxRate(15.0, notes="Digital service withholding")
                }
            }
        }

    def _load_compliance_requirements(self):
        """Load compliance requirements for different jurisdictions"""
        self.compliance_forms = {
            TaxJurisdiction.INDIA: {
                TaxType.TDS: [
                    TaxForm(
                        form_number="26Q",
                        name="TDS Return for Non-salary Payments",
                        filing_deadline="Quarterly",
                        notes="Due within 30 days from end of quarter"
                    ),
                    TaxForm(
                        form_number="15CA",
                        name="Foreign Remittance Certificate",
                        filing_deadline="Before remittance",
                        notes="Required for all foreign remittances"
                    ),
                    TaxForm(
                        form_number="15CB",
                        name="CA Certificate for Foreign Remittance",
                        filing_deadline="Before remittance",
                        notes="Required if payment exceeds INR 5 lakhs"
                    )
                ]
            },
            TaxJurisdiction.USA: {
                TaxType.WITHHOLDING: [
                    TaxForm(
                        form_number="1042-S",
                        name="Foreign Person's U.S. Source Income",
                        filing_deadline="March 15",
                        notes="Annual filing required"
                    ),
                    TaxForm(
                        form_number="W-8BEN",
                        name="Certificate of Foreign Status",
                        filing_deadline="Before payment",
                        notes="Valid for 3 years"
                    )
                ]
            },
            TaxJurisdiction.UK: {
                TaxType.VAT: [
                    TaxForm(
                        form_number="VAT Return",
                        name="Value Added Tax Return",
                        filing_deadline="Quarterly",
                        notes="Due one month and seven days after quarter end"
                    )
                ],
                TaxType.CIS: [
                    TaxForm(
                        form_number="CIS300",
                        name="Contractor Monthly Return",
                        filing_deadline="Monthly",
                        notes="Due by 19th of each month"
                    )
                ],
                TaxType.WITHHOLDING: [
                    TaxForm(
                        form_number="CT61",
                        name="Return of Income Tax",
                        filing_deadline="Quarterly",
                        notes="For payments to non-residents"
                    )
                ]
            },
            TaxJurisdiction.EU_DE: {
                TaxType.MWST: [
                    TaxForm(
                        form_number="UStVA",
                        name="Umsatzsteuer-Voranmeldung",
                        filing_deadline="Monthly/Quarterly",
                        notes="VAT advance return"
                    ),
                    TaxForm(
                        form_number="ZM",
                        name="Zusammenfassende Meldung",
                        filing_deadline="Monthly",
                        notes="EU sales listing"
                    )
                ]
            },
            TaxJurisdiction.EU_FR: {
                TaxType.TVA: [
                    TaxForm(
                        form_number="CA3",
                        name="TVA Return",
                        filing_deadline="Monthly",
                        notes="Standard VAT return"
                    ),
                    TaxForm(
                        form_number="DES",
                        name="Declaration Européenne de Services",
                        filing_deadline="Monthly",
                        notes="EU services declaration"
                    )
                ]
            },
            TaxJurisdiction.SINGAPORE: {
                TaxType.GST: [
                    TaxForm(
                        form_number="F5",
                        name="GST Return",
                        filing_deadline="Quarterly",
                        notes="Due one month after quarter end"
                    )
                ],
                TaxType.WITHHOLDING: [
                    TaxForm(
                        form_number="S45",
                        name="Withholding Tax Return",
                        filing_deadline="Within 30 days",
                        notes="Due within 30 days of payment"
                    )
                ]
            }
        }

    def get_tax_advice(
        self,
        payer_country: str,
        vendor_country: str,
        service_type: str,
        transaction_value: float,
        currency: str = "USD",
        has_permanent_establishment: bool = False,
        tax_residency_certificate: bool = False
    ) -> TaxAdvice:
        """
        Determine applicable taxes and compliance requirements
        
        Args:
            payer_country: Country of the payer
            vendor_country: Country of the vendor
            service_type: Type of service being provided
            transaction_value: Value of the transaction
            currency: Currency of transaction
            has_permanent_establishment: Whether vendor has PE in payer country
            tax_residency_certificate: Whether vendor has valid TRC
        
        Returns:
            TaxAdvice object containing applicable taxes and compliance requirements
        """
        try:
            payer_jurisdiction = TaxJurisdiction(payer_country)
            service_category = ServiceCategory(service_type)
        except ValueError:
            raise ValueError("Invalid country or service type")

        # Get DTAA treaty if applicable
        dtaa_treaty = self.tax_treaties.get((payer_country, vendor_country))

        # Initialize collections
        applicable_taxes = {}
        filing_requirements = []
        exemptions = []
        compliance_notes = []

        # Check for permanent establishment implications
        pe_risk = self._assess_permanent_establishment_risk(
            payer_country, vendor_country, has_permanent_establishment, dtaa_treaty
        )

        # Special handling for intra-EU transactions
        is_intra_eu = (
            payer_country in self.eu_member_states and 
            vendor_country in self.eu_member_states
        )

        # Determine applicable taxes based on jurisdiction and service type
        jurisdiction_rates = self.tax_rates.get(payer_jurisdiction, {})
        service_rates = jurisdiction_rates.get(service_category, {})

        for tax_type, rate in service_rates.items():
            # Skip withholding tax for intra-EU transactions
            if is_intra_eu and tax_type == TaxType.WITHHOLDING:
                exemptions.append("Intra-EU supply - No withholding tax applicable")
                continue

            # Apply DTAA benefits if applicable
            if dtaa_treaty and tax_type in [TaxType.WITHHOLDING, TaxType.TDS]:
                treaty_rate = self._get_treaty_rate(dtaa_treaty, service_category)
                if treaty_rate is not None and treaty_rate < rate.rate:
                    rate = TaxRate(
                        treaty_rate,
                        rate.currency_threshold,
                        currency,
                        f"DTAA rate applied ({payer_country}-{vendor_country} treaty)"
                    )
                    compliance_notes.append(
                        f"DTAA benefit applied: Rate reduced to {treaty_rate}%"
                    )

            # Update currency in tax rate
            rate.currency = currency
            applicable_taxes[tax_type] = rate

        # Get filing requirements
        jurisdiction_forms = self.compliance_forms.get(payer_jurisdiction, {})
        for tax_type in applicable_taxes.keys():
            if tax_type in jurisdiction_forms:
                filing_requirements.extend(jurisdiction_forms[tax_type])

        # Add relevant compliance notes
        if tax_residency_certificate:
            compliance_notes.append(
                "Tax Residency Certificate available - DTAA benefits applicable"
            )
        if has_permanent_establishment:
            compliance_notes.append(
                "Permanent Establishment exists - Local tax laws applicable"
            )
        if is_intra_eu:
            compliance_notes.append(
                "Intra-EU transaction - Special VAT rules apply"
            )

        return TaxAdvice(
            applicable_taxes=applicable_taxes,
            filing_requirements=filing_requirements,
            dtaa_treaty=dtaa_treaty,
            permanent_establishment_risk=pe_risk,
            exemptions=exemptions,
            compliance_notes=compliance_notes
        )

    def _assess_permanent_establishment_risk(
        self,
        payer_country: str,
        vendor_country: str,
        has_pe: bool,
        dtaa_treaty: Optional[DTAATreaty]
    ) -> bool:
        """Assess permanent establishment risk"""
        if has_pe:
            return True
        if dtaa_treaty and dtaa_treaty.permanent_establishment_days > 0:
            return False
        return False

    def _get_treaty_rate(self, treaty: DTAATreaty, service_category: ServiceCategory) -> Optional[float]:
        """Get applicable rate from tax treaty"""
        if service_category == ServiceCategory.ROYALTY:
            return treaty.withholding_rates.get("royalty")
        elif service_category in [ServiceCategory.TECHNICAL, ServiceCategory.CONSULTING]:
            return treaty.withholding_rates.get("technical_services")
        return None

    def _determine_exemptions(
        self,
        jurisdiction: TaxJurisdiction,
        service_category: ServiceCategory,
        value: float,
        currency: str,
        has_pe: bool
    ) -> List[str]:
        """Determine applicable exemptions"""
        exemptions = []
        
        # India-specific exemptions
        if jurisdiction == TaxJurisdiction.INDIA:
            if service_category == ServiceCategory.TECHNICAL and value < 30000:
                exemptions.append("TDS exemption under Section 194J for amount below threshold")
            if not has_pe and service_category in [ServiceCategory.SAAS, ServiceCategory.ROYALTY]:
                exemptions.append("Eligible for reduced withholding under DTAA with valid TRC")

        # US-specific exemptions
        elif jurisdiction == TaxJurisdiction.USA:
            if service_category == ServiceCategory.TECHNICAL and not has_pe:
                exemptions.append("Eligible for tax treaty benefits with valid W8-BEN")

        return exemptions

    def analyze_transaction(self, source_country: str, destination_country: str, 
                          transaction_type: str, amount: float) -> dict:
        """Analyze a transaction and determine applicable taxes"""
        result = {
            "source_country": source_country,
            "destination_country": destination_country,
            "transaction_type": transaction_type,
            "amount": amount,
            "applicable_taxes": [],
            "total_tax_amount": 0.0,
            "compliance_requirements": []
        }

        # Determine applicable taxes based on countries and transaction type
        if source_country == "India" and destination_country == "Singapore":
            # Export of services
            if transaction_type in ["Digital Services", "Technical Services"]:
                # Zero-rated GST for exports
                tax = {
                    "type": "GST",
                    "rate": 0.0,
                    "amount": 0.0,
                    "notes": "Zero-rated for exports"
                }
                result["applicable_taxes"].append(tax)
                
                # Check if WHT applies
                wht_rate = 0.17
                if wht_rate > 0:
                    wht = {
                        "type": "WHT",
                        "rate": wht_rate,
                        "amount": amount * wht_rate,
                        "notes": "Singapore WHT on technical services"
                    }
                    result["applicable_taxes"].append(wht)
                    result["total_tax_amount"] += wht["amount"]

        elif source_country == "Singapore" and destination_country == "India":
            # Import of services to India
            if transaction_type in ["Digital Services", "Technical Services"]:
                # IGST applies on import of services
                igst_rate = 0.18
                igst = {
                    "type": "IGST",
                    "rate": igst_rate,
                    "amount": amount * igst_rate,
                    "notes": "IGST on import of services"
                }
                result["applicable_taxes"].append(igst)
                result["total_tax_amount"] += igst["amount"]

                # Indian WHT may apply
                wht_rate = 0.10
                if wht_rate > 0:
                    wht = {
                        "type": "WHT",
                        "rate": wht_rate,
                        "amount": amount * wht_rate,
                        "notes": "India WHT on technical services"
                    }
                    result["applicable_taxes"].append(wht)
                    result["total_tax_amount"] += wht["amount"]

        # Add compliance requirements
        result["compliance_requirements"] = self._get_compliance_requirements(
            source_country, destination_country, result["applicable_taxes"]
        )

        return result

    def _get_compliance_requirements(self, source_country: str, 
                                  destination_country: str,
                                  applicable_taxes: list) -> list:
        """Determine compliance requirements based on transaction details"""
        requirements = []
        
        for tax in applicable_taxes:
            if tax["type"] == "GST":
                requirements.append({
                    "type": "Registration",
                    "description": f"GST registration in {source_country}",
                    "deadline_days": 30
                })
                requirements.append({
                    "type": "Filing",
                    "description": f"GST return filing in {source_country}",
                    "deadline_days": 20
                })
            elif tax["type"] == "WHT":
                requirements.append({
                    "type": "Filing",
                    "description": f"WHT return filing in {destination_country}",
                    "deadline_days": 7
                })
                requirements.append({
                    "type": "Documentation",
                    "description": "Tax residency certificate",
                    "deadline_days": 90
                })

        return requirements
