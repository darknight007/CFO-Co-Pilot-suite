from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello from CFO Co-Pilot Suite"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

# Handler for AWS Lambda/Vercel
handler = Mangum(app)
