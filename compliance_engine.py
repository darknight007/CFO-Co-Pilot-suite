from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any
import json
import calendar

class ComplianceStatus(Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    ESCALATED = "Escalated"
    OVERDUE = "Overdue"

@dataclass
class ComplianceDocument:
    name: str
    type: str
    required: bool
    description: str
    retention_period: int  # in months

@dataclass
class ComplianceAction:
    form_number: str
    jurisdiction: str
    due_date: datetime
    required_documents: List[ComplianceDocument]
    status: ComplianceStatus
    risk_level: str
    assignee: str
    notes: str

class ComplianceEngine:
    def __init__(self):
        self.required_documents = {
            "INDIA": {
                "15CA": [
                    ComplianceDocument(
                        name="Invoice",
                        type="Transaction",
                        required=True,
                        description="Original invoice from vendor",
                        retention_period=96
                    ),
                    ComplianceDocument(
                        name="Tax Residency Certificate",
                        type="Tax",
                        required=True,
                        description="Valid for current financial year",
                        retention_period=96
                    ),
                    ComplianceDocument(
                        name="Service Agreement",
                        type="Contract",
                        required=True,
                        description="Master service agreement or SOW",
                        retention_period=96
                    )
                ]
            },
            "USA": {
                "1042-S": [
                    ComplianceDocument(
                        name="W-8BEN/W-8BEN-E",
                        type="Tax",
                        required=True,
                        description="Valid for 3 years from signing",
                        retention_period=84
                    ),
                    ComplianceDocument(
                        name="Invoice",
                        type="Transaction",
                        required=True,
                        description="Original invoice with tax breakdown",
                        retention_period=84
                    )
                ]
            },
            "EU": {
                "VAT": [
                    ComplianceDocument(
                        name="VAT Invoice",
                        type="Transaction",
                        required=True,
                        description="Invoice with VAT registration numbers",
                        retention_period=120
                    ),
                    ComplianceDocument(
                        name="Proof of Service",
                        type="Transaction",
                        required=True,
                        description="Evidence of B2B service provision",
                        retention_period=120
                    )
                ]
            }
        }
        self.filing_deadlines = {
            "GST": {
                "India": {
                    "monthly": 20,  # Due by 20th of next month
                    "quarterly": {"month": 4, "day": 30}  # For quarterly returns
                },
                "Singapore": {
                    "quarterly": {"month": 1, "day": 31}  # Due by Jan 31 for Q4
                }
            },
            "WHT": {
                "India": {
                    "monthly": 7  # Due by 7th of next month
                },
                "Singapore": {
                    "monthly": 15  # Due by 15th of next month
                }
            }
        }

    def generate_compliance_checklist(self, tax_advice: dict, transaction_date: datetime) -> List[ComplianceAction]:
        """Generate compliance checklist based on tax advice"""
        actions = []
        jurisdiction = tax_advice.get("jurisdiction")
        
        if not jurisdiction:
            return actions

        # Calculate due dates based on transaction date
        quarter_end = self._get_quarter_end(transaction_date)
        month_end = self._get_month_end(transaction_date)

        # Add jurisdiction-specific compliance actions
        if jurisdiction == "INDIA":
            if tax_advice.get("foreign_remittance"):
                actions.append(ComplianceAction(
                    form_number="15CA",
                    jurisdiction="INDIA",
                    due_date=transaction_date + timedelta(days=7),
                    required_documents=self.required_documents["INDIA"]["15CA"],
                    status=ComplianceStatus.PENDING,
                    risk_level="Medium",
                    assignee="Tax Team",
                    notes="Required before foreign remittance"
                ))

            if tax_advice.get("tds_applicable"):
                actions.append(ComplianceAction(
                    form_number="26Q",
                    jurisdiction="INDIA",
                    due_date=quarter_end,
                    required_documents=[],
                    status=ComplianceStatus.PENDING,
                    risk_level="High",
                    assignee="Tax Team",
                    notes="Quarterly TDS return"
                ))

        elif jurisdiction == "USA":
            if tax_advice.get("withholding_applicable"):
                actions.append(ComplianceAction(
                    form_number="1042-S",
                    jurisdiction="USA",
                    due_date=datetime(transaction_date.year + 1, 3, 15),
                    required_documents=self.required_documents["USA"]["1042-S"],
                    status=ComplianceStatus.PENDING,
                    risk_level="High",
                    assignee="Tax Team",
                    notes="Annual withholding tax return"
                ))

        elif jurisdiction in ["EU_FR", "EU_DE"]:
            actions.append(ComplianceAction(
                form_number="VAT Return",
                jurisdiction="EU",
                due_date=month_end + timedelta(days=20),
                required_documents=self.required_documents["EU"]["VAT"],
                status=ComplianceStatus.PENDING,
                risk_level="Medium",
                assignee="Tax Team",
                notes="Monthly VAT return"
            ))

        return actions

    def generate_checklist(self, tax_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate compliance checklist based on tax data"""
        checklist = []
        country = tax_data["country"]
        amount = tax_data["amount"]
        date = tax_data.get("date", datetime.now())

        # Add registration requirements
        if country == "India" and amount > 20000:  # 20,000 USD threshold
            checklist.append({
                "type": "Registration",
                "description": "GST Registration Required",
                "deadline": self._calculate_deadline(date, days=30),
                "priority": "High",
                "requirements": [
                    "Business PAN",
                    "Proof of business address",
                    "Bank account details"
                ]
            })

        # Add filing requirements
        if country == "India":
            # GST filing
            checklist.append({
                "type": "Filing",
                "description": "Monthly GST Return (GSTR-1)",
                "deadline": self._calculate_deadline(date, days=self.filing_deadlines["GST"]["India"]["monthly"]),
                "priority": "High",
                "requirements": [
                    "Invoice details",
                    "Tax payment challan",
                    "E-way bills if applicable"
                ]
            })
            
            # WHT filing
            checklist.append({
                "type": "Filing",
                "description": "TDS Return",
                "deadline": self._calculate_deadline(date, days=self.filing_deadlines["WHT"]["India"]["monthly"]),
                "priority": "Medium",
                "requirements": [
                    "Form 26Q",
                    "TDS certificates",
                    "Vendor PAN details"
                ]
            })

        elif country == "Singapore":
            # GST filing
            checklist.append({
                "type": "Filing",
                "description": "GST F5 Return",
                "deadline": self._get_quarter_end(date),
                "priority": "High",
                "requirements": [
                    "Sales listing",
                    "Purchase listing",
                    "Input tax claims"
                ]
            })

        # Add documentation requirements
        checklist.append({
            "type": "Documentation",
            "description": "Supporting Documents",
            "deadline": self._calculate_deadline(date, days=7),
            "priority": "Medium",
            "requirements": [
                "Original invoices",
                "Payment proof",
                "Contracts or agreements"
            ]
        })

        return checklist

    def calculate_due_date(self, filing_type: str, transaction_date: datetime) -> datetime:
        deadline = self.filing_deadlines.get(filing_type, timedelta(days=30))
        return transaction_date + deadline

    def validate_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        missing = []
        if not requirements.get("tax_registration"):
            missing.append("tax_registration")
        if not requirements.get("valid_tax_id"):
            missing.append("valid_tax_id")
        if not requirements.get("filing_history"):
            missing.append("filing_history")

        return {
            "is_compliant": len(missing) == 0,
            "missing_requirements": missing
        }

    def _get_quarter_end(self, date: datetime) -> datetime:
        """Get quarter end date"""
        quarter = (date.month - 1) // 3 + 1
        return datetime(date.year, quarter * 3, 1) + timedelta(days=30)

    def _get_month_end(self, date: datetime) -> datetime:
        """Get month end date"""
        if date.month == 12:
            return datetime(date.year, 12, 31)
        return datetime(date.year, date.month + 1, 1) - timedelta(days=1)

    def _get_next_filing_date(self, filing_type: str) -> datetime:
        today = datetime.now()
        if filing_type == "GST":
            # GST is filed quarterly
            quarter_end = datetime(today.year, ((today.month - 1) // 3 + 1) * 3, 1)
            return quarter_end + self.filing_deadlines[filing_type]
        return today + self.filing_deadlines.get(filing_type, timedelta(days=30))

    def _calculate_deadline(self, base_date: datetime, days: int) -> str:
        """Calculate deadline based on base date and days"""
        deadline = base_date + timedelta(days=days)
        return deadline.strftime("%Y-%m-%d")

    def _get_quarter_end(self, date: datetime) -> str:
        """Get quarter end date"""
        quarter = (date.month - 1) // 3
        last_month = (quarter + 1) * 3
        last_day = calendar.monthrange(date.year, last_month)[1]
        return datetime(date.year, last_month, last_day).strftime("%Y-%m-%d")

class FormGenerator:
    def generate_form_15ca(self, tax_data: dict) -> dict:
        """Generate Form 15CA draft for India"""
        return {
            "form_type": "15CA",
            "part": "A" if tax_data.get("amount_in_inr", 0) <= 500000 else "B",
            "remitter_details": {
                "name": tax_data.get("payer_name"),
                "pan": tax_data.get("payer_pan"),
                "tan": tax_data.get("payer_tan"),
                "address": tax_data.get("payer_address")
            },
            "remittance_details": {
                "amount": tax_data.get("amount"),
                "currency": tax_data.get("currency"),
                "purpose_code": self._get_purpose_code(tax_data.get("service_type")),
                "nature_of_remittance": tax_data.get("service_type")
            },
            "beneficiary_details": {
                "name": tax_data.get("vendor_name"),
                "address": tax_data.get("vendor_address"),
                "country": tax_data.get("vendor_country")
            },
            "certificate_details": {
                "ca_name": "",
                "ca_registration": "",
                "certificate_date": ""
            } if tax_data.get("amount_in_inr", 0) > 500000 else None
        }

    def generate_1042s(self, tax_data: dict) -> dict:
        """Generate Form 1042-S draft for USA"""
        return {
            "form_type": "1042-S",
            "tax_year": datetime.now().year,
            "withholding_agent": {
                "name": tax_data.get("payer_name"),
                "ein": tax_data.get("payer_ein"),
                "address": tax_data.get("payer_address")
            },
            "recipient": {
                "name": tax_data.get("vendor_name"),
                "address": tax_data.get("vendor_address"),
                "country": tax_data.get("vendor_country"),
                "tax_id": tax_data.get("vendor_tax_id")
            },
            "payment_details": {
                "income_type": self._get_income_code(tax_data.get("service_type")),
                "gross_amount": tax_data.get("amount"),
                "withholding_rate": tax_data.get("withholding_rate", 30),
                "tax_withheld": tax_data.get("tax_withheld")
            }
        }

    def generate_vat_invoice(self, tax_data: dict) -> dict:
        """Generate VAT invoice for EU/UK"""
        return {
            "document_type": "VAT Invoice",
            "invoice_number": tax_data.get("invoice_number"),
            "date": tax_data.get("invoice_date"),
            "supplier": {
                "name": tax_data.get("vendor_name"),
                "vat_number": tax_data.get("vendor_vat"),
                "address": tax_data.get("vendor_address")
            },
            "customer": {
                "name": tax_data.get("payer_name"),
                "vat_number": tax_data.get("payer_vat"),
                "address": tax_data.get("payer_address")
            },
            "service_details": {
                "description": tax_data.get("service_type"),
                "amount_excl_vat": tax_data.get("amount"),
                "vat_rate": tax_data.get("vat_rate"),
                "vat_amount": tax_data.get("vat_amount"),
                "total_amount": tax_data.get("total_amount")
            },
            "notes": [
                "Reverse Charge Applies" if tax_data.get("reverse_charge") else None,
                "Intra-EU Supply" if tax_data.get("intra_eu") else None
            ]
        }

    def _get_purpose_code(self, service_type: str) -> str:
        """Map service type to RBI purpose code"""
        purpose_codes = {
            "Technical Services": "S0304",
            "Professional Services": "S0304",
            "Royalty": "S0306",
            "Software": "S0302"
        }
        return purpose_codes.get(service_type, "S0304")

    def _get_income_code(self, service_type: str) -> str:
        """Map service type to 1042-S income code"""
        income_codes = {
            "Technical Services": "50",
            "Professional Services": "50",
            "Royalty": "12",
            "Software": "12"
        }
        return income_codes.get(service_type, "50")
