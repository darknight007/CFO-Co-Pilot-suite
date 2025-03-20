from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
import json

class RiskLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

@dataclass
class ValidationIssue:
    code: str
    description: str
    risk_level: RiskLevel
    recommendation: str
    requires_escalation: bool

@dataclass
class ValidationResult:
    valid: bool
    issues: List[ValidationIssue]
    timestamp: datetime
    validator_version: str = "1.0.0"

class ComplianceValidator:
    def __init__(self):
        self.current_forex_rates = {}  # Should be updated via external forex API
        self.pe_thresholds = {
            "INDIA": {
                "days": 90,
                "amount": 500000  # in local currency
            },
            "EU": {
                "days": 183,
                "amount": 100000  # in EUR
            }
        }
        self.tax_id_formats = {
            "India": {
                "GST": r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$",  # GST format
                "PAN": r"^[A-Z]{5}\d{4}[A-Z]{1}$"  # PAN format
            },
            "Singapore": {
                "UEN": r"^\d{9}[A-Z]$",  # UEN format
                "GST": r"^[MF]\d{8}[A-Z]$"  # GST format
            }
        }

    def validate_filing(self, tax_data: dict, compliance_data: dict) -> ValidationResult:
        """Validate tax filing data against compliance rules"""
        issues = []
        
        # Validate PE conditions
        pe_issues = self._validate_pe_conditions(tax_data)
        issues.extend(pe_issues)
        
        # Validate DTAA benefits
        dtaa_issues = self._validate_dtaa_benefits(tax_data)
        issues.extend(dtaa_issues)
        
        # Validate tax rates
        rate_issues = self._validate_tax_rates(tax_data)
        issues.extend(rate_issues)
        
        # Validate currency conversion
        currency_issues = self._validate_currency_conversion(tax_data)
        issues.extend(currency_issues)
        
        return ValidationResult(
            valid=len(issues) == 0,
            issues=issues,
            timestamp=datetime.now()
        )

    def _validate_pe_conditions(self, tax_data: dict) -> List[ValidationIssue]:
        """Validate Permanent Establishment conditions"""
        issues = []
        jurisdiction = tax_data.get("jurisdiction")
        
        if not jurisdiction:
            return issues
            
        pe_threshold = self.pe_thresholds.get(jurisdiction)
        if not pe_threshold:
            return issues
            
        # Check days threshold
        if tax_data.get("service_days", 0) > pe_threshold["days"]:
            issues.append(ValidationIssue(
                code="PE001",
                description=f"Service duration ({tax_data['service_days']} days) exceeds PE threshold ({pe_threshold['days']} days)",
                risk_level=RiskLevel.HIGH,
                recommendation="Review PE implications and consider local entity registration",
                requires_escalation=True
            ))
            
        # Check revenue threshold
        if tax_data.get("annual_revenue", 0) > pe_threshold["amount"]:
            issues.append(ValidationIssue(
                code="PE002",
                description=f"Annual revenue exceeds PE threshold",
                risk_level=RiskLevel.HIGH,
                recommendation="Review PE implications and consider local entity registration",
                requires_escalation=True
            ))
            
        return issues

    def _validate_dtaa_benefits(self, tax_data: dict) -> List[ValidationIssue]:
        """Validate DTAA benefit application"""
        issues = []
        
        if tax_data.get("dtaa_applied"):
            # Check if TRC is available and valid
            if not tax_data.get("trc_available"):
                issues.append(ValidationIssue(
                    code="DTAA001",
                    description="DTAA benefits applied without valid Tax Residency Certificate",
                    risk_level=RiskLevel.HIGH,
                    recommendation="Obtain valid TRC before applying DTAA benefits",
                    requires_escalation=True
                ))
            
            # Validate if service type qualifies for DTAA
            if not self._is_service_dtaa_eligible(tax_data.get("service_type")):
                issues.append(ValidationIssue(
                    code="DTAA002",
                    description="Service type may not qualify for DTAA benefits",
                    risk_level=RiskLevel.MEDIUM,
                    recommendation="Review service classification and DTAA article applicability",
                    requires_escalation=True
                ))
                
        return issues

    def _validate_tax_rates(self, tax_data: dict) -> List[ValidationIssue]:
        """Validate applied tax rates"""
        issues = []
        jurisdiction = tax_data.get("jurisdiction")
        
        if not jurisdiction:
            return issues
            
        # Check if applied rate matches statutory rate
        if tax_data.get("applied_rate") < tax_data.get("statutory_rate", 0):
            issues.append(ValidationIssue(
                code="RATE001",
                description="Applied rate is lower than statutory rate",
                risk_level=RiskLevel.MEDIUM,
                recommendation="Verify rate reduction justification and documentation",
                requires_escalation=False
            ))
            
        # Check for special rate applicability
        if tax_data.get("special_rate_applied"):
            if not tax_data.get("special_rate_documentation"):
                issues.append(ValidationIssue(
                    code="RATE002",
                    description="Special rate applied without supporting documentation",
                    risk_level=RiskLevel.HIGH,
                    recommendation="Obtain and maintain documentation for special rate",
                    requires_escalation=True
                ))
                
        return issues

    def _validate_currency_conversion(self, tax_data: dict) -> List[ValidationIssue]:
        """Validate currency conversion rates and methods"""
        issues = []
        
        if tax_data.get("currency") != tax_data.get("local_currency"):
            # Check if using official exchange rates
            if not tax_data.get("official_rate_used"):
                issues.append(ValidationIssue(
                    code="CURR001",
                    description="Non-official exchange rate used for conversion",
                    risk_level=RiskLevel.MEDIUM,
                    recommendation="Use official exchange rates as per regulatory requirements",
                    requires_escalation=False
                ))
            
            # Verify rate date
            if not self._is_valid_rate_date(tax_data.get("rate_date")):
                issues.append(ValidationIssue(
                    code="CURR002",
                    description="Exchange rate date does not comply with regulations",
                    risk_level=RiskLevel.MEDIUM,
                    recommendation="Use exchange rate as per prescribed date",
                    requires_escalation=False
                ))
                
        return issues

    def _is_service_dtaa_eligible(self, service_type: str) -> bool:
        """Check if service type is eligible for DTAA benefits"""
        eligible_services = {
            "Technical Services",
            "Professional Services",
            "Royalty",
            "Interest",
            "Dividend"
        }
        return service_type in eligible_services

    def _is_valid_rate_date(self, rate_date: datetime) -> bool:
        """Validate if exchange rate date complies with regulations"""
        if not rate_date:
            return False
            
        # Most jurisdictions require month-end or transaction date rates
        today = datetime.now()
        return (rate_date.year == today.year and 
                rate_date.month == today.month and 
                rate_date.day in [1, rate_date.day])

    def validate_requirements(self, data: dict) -> dict:
        """Validate compliance requirements for a given set of data"""
        result = {
            "valid": True,
            "checks": [],
            "issues": []
        }

        # Check tax registration
        if "tax_registration" in data:
            check = {
                "type": "Tax Registration",
                "status": "PASS" if data["tax_registration"] else "FAIL",
                "message": "Tax registration verified" if data["tax_registration"] else "Missing tax registration"
            }
            result["checks"].append(check)
            if not data["tax_registration"]:
                result["valid"] = False
                result["issues"].append("Tax registration not found")

        # Validate tax ID format
        if "valid_tax_id" in data:
            tax_id = data["valid_tax_id"]
            # For India GST number
            if len(tax_id) == 15:  # India GST number length
                import re
                is_valid = bool(re.match(self.tax_id_formats["India"]["GST"], tax_id))
                check = {
                    "type": "Tax ID Format",
                    "status": "PASS" if is_valid else "FAIL",
                    "message": f"Tax ID {tax_id} format is valid" if is_valid else f"Invalid tax ID format: {tax_id}"
                }
                result["checks"].append(check)
                if not is_valid:
                    result["valid"] = False
                    result["issues"].append(f"Invalid tax ID format: {tax_id}")

        # Check filing history
        if "filing_history" in data:
            history = data["filing_history"]
            check = {
                "type": "Filing History",
                "status": "PASS" if history else "FAIL",
                "message": f"Found {len(history)} previous filings" if history else "No filing history found"
            }
            result["checks"].append(check)
            if not history:
                result["valid"] = False
                result["issues"].append("No filing history found")

        return result
