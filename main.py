from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os

# Crear aplicación FastAPI
app = FastAPI(
    title="ML Automation System",
    description="Sistema de automatización para Mercado Libre",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar"""
    print("🚀 Starting ML Automation System...")
    print("✅ System ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al apagar"""
    print("👋 Shutting down ML Automation System...")

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "ML Automation System",
        "status": "running",
        "docs": "/docs"
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
