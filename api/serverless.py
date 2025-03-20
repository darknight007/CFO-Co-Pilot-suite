from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": str(datetime.now())}

@app.get("/")
async def root():
    return {"message": "CFO Co-Pilot Suite API"}
