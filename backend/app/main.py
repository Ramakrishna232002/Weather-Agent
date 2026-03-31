from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.core.config import settings

# Create FastAPI instance
app = FastAPI(
    title="Weather Agent API",
    description="Weather data with AI analysis using Ollama",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "Weather Agent API is running",
        "status": "active",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "weather": "/api/v1/weather",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Weather Agent"}