from pydantic import BaseModel
from typing import Optional, List, Dict

class InvoiceAnalysisResponse(BaseModel):
    invoice_number: str
    total_amount: float
    tax_details: Dict[str, float]
    compliance_status: str
    compliance_issues: Optional[List[str]] = []
    recommendations: Optional[List[str]] = []

class ComplianceCheckResponse(BaseModel):
    status: str
    issues: List[str] = []
    tax_compliance: bool
    required_actions: List[str] = []
    due_dates: Dict[str, str] = {}
