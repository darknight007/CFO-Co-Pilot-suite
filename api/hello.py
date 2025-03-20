from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/api/hello")
async def hello():
    return JSONResponse({"hello": "world"})

@app.get("/")
async def root():
    return JSONResponse({"message": "Welcome to CFO Co-Pilot Suite API"})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
