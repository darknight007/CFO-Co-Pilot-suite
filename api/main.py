from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our components
from tax_engine import TaxEngine
from compliance_engine import ComplianceEngine
from compliance_validator import ComplianceValidator
from cfo_automation import CFOAutomationOrchestrator
from integration.erp_connector import ERPConnector
from integration.payment_gateway import PaymentGatewayConnector
from integration.document_manager import DocumentManager
from integration.gov_portal import GovPortalSubmitter, FilingOrchestrator

app = FastAPI(
    title="Invoice Compliance Analyzer API",
    description="API for analyzing and managing invoice compliance across multiple jurisdictions",
    version="1.0.0"
)

# Configure CORS with specific origins for Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://invoice-compliance-analyzer.vercel.app",  # Production
        "http://localhost:3000",  # Local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class TransactionRequest(BaseModel):
    source_country: str
    destination_country: str
    transaction_type: str
    amount: float

class ComplianceRequest(BaseModel):
    country: str
    amount: float
    date: Optional[datetime] = None

class ValidationRequest(BaseModel):
    tax_registration: bool
    valid_tax_id: str
    filing_history: List[str]

class FilingRequest(BaseModel):
    form_type: str
    period: str
    amount: float
    invoice_id: str

# Initialize components (lazy loading for serverless)
def get_tax_engine():
    return TaxEngine()

def get_compliance_engine():
    return ComplianceEngine()

def get_compliance_validator():
    return ComplianceValidator()

def get_cfo_orchestrator():
    return CFOAutomationOrchestrator()

@app.get("/")
async def root():
    return {
        "message": "Invoice Compliance Analyzer API is running",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.post("/api/analyze/tax")
async def analyze_tax(request: TransactionRequest):
    try:
        tax_engine = get_tax_engine()
        result = tax_engine.analyze_transaction(
            source_country=request.source_country,
            destination_country=request.destination_country,
            transaction_type=request.transaction_type,
            amount=request.amount
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compliance/checklist")
async def generate_checklist(request: ComplianceRequest):
    try:
        compliance_engine = get_compliance_engine()
        result = compliance_engine.generate_checklist({
            "country": request.country,
            "amount": request.amount,
            "date": request.date or datetime.now()
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compliance/validate")
async def validate_compliance(request: ValidationRequest):
    try:
        compliance_validator = get_compliance_validator()
        result = compliance_validator.validate_requirements({
            "tax_registration": request.tax_registration,
            "valid_tax_id": request.valid_tax_id,
            "filing_history": request.filing_history
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process/transaction/{invoice_id}")
async def process_transaction(invoice_id: str):
    try:
        cfo_orchestrator = get_cfo_orchestrator()
        result = await cfo_orchestrator.process_transaction(invoice_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/submit/filing")
async def submit_filing(request: FilingRequest):
    try:
        gov_portal = GovPortalSubmitter()
        result = gov_portal.submit_filing({
            "form_type": request.form_type,
            "period": request.period,
            "amount": request.amount,
            "invoice_id": request.invoice_id
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint for Vercel
@app.get("/api/healthz")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
