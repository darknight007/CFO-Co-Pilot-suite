from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import time
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Add middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    # Log request details
    logger.info(
        f"Path: {request.url.path} | Method: {request.method} | "
        f"Process Time: {process_time:.3f}s | Status: {response.status_code}"
    )
    return response

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error processing request: {request.url.path}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "path": request.url.path,
            "timestamp": datetime.now().isoformat()
        }
    )

# Monitoring endpoints
@app.get("/api/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/metrics")
async def metrics():
    """Return basic metrics about the API"""
    return {
        "uptime": time.time() - app.state.start_time,
        "total_requests": app.state.request_count,
        "error_count": app.state.error_count,
        "timestamp": datetime.now().isoformat()
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize state variables on startup"""
    app.state.start_time = time.time()
    app.state.request_count = 0
    app.state.error_count = 0
    logger.info("Application started successfully")

# Request counter middleware
@app.middleware("http")
async def count_requests(request: Request, call_next):
    app.state.request_count += 1
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            app.state.error_count += 1
        return response
    except Exception as e:
        app.state.error_count += 1
        raise e

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
