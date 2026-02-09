from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import uvicorn
import os
from pathlib import Path

from database.db import init_db
from routes import products, dashboard, actions
from scheduler.jobs import job_scheduler
from utils.logger import logger

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 ML Automation System starting...")
    
    # Initialize database
    init_db()
    logger.info("✅ Database initialized")
    
    # Start scheduler
    job_scheduler.start()
    logger.info("✅ Job scheduler started")
    
    logger.info("✅ System ready!")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down ML Automation System...")
    job_scheduler.shutdown()

# Create app
app = FastAPI(
    title="ML Automation System",
    description="Sistema de automatización para Mercado Libre",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(products.router)
app.include_router(dashboard.router)
app.include_router(actions.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ML Automation System",
        "status": "running",
        "docs": "/docs",
        "dashboard": "/dashboard"
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
