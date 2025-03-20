from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CFO Co-Pilot Suite API",
        "documentation": "/docs",
        "health": "/api/health"
    }

def handler(request, response):
    if request.method == 'GET':
        response.status = 200
        response.body = json.dumps({"status": "ok"})
    return response

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "path": self.path
        }
        
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
