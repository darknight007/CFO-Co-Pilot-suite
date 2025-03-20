from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import io
from .models import InvoiceAnalysisResponse, ComplianceCheckResponse
from .utils import process_invoice_file, validate_invoice_format

app = FastAPI(title="CFO Co-Pilot Suite API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return JSONResponse({
        "message": "Welcome to CFO Co-Pilot Suite API",
        "endpoints": {
            "upload_invoice": "/api/upload-invoice",
            "health": "/api/health"
        }
    })

@app.get("/api/health")
async def health():
    return JSONResponse({"status": "healthy"})

@app.post("/api/upload-invoice", response_model=InvoiceAnalysisResponse)
async def upload_invoice(file: UploadFile = File(...)):
    """
    Upload and analyze an invoice PDF file.
    Returns detailed analysis including tax and compliance information.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")
        
        # Read file content
        content = await file.read()
        
        # Validate PDF format
        if not validate_invoice_format(io.BytesIO(content)):
            raise HTTPException(status_code=400, detail="Invalid PDF format")
        
        # Process invoice
        result = await process_invoice_file(content)
        
        return JSONResponse(result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
