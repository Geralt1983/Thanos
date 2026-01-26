"""
Thanos Dashboard API Server.

FastAPI backend server providing REST API endpoints for the Thanos visualization
dashboard. Integrates with WorkOS MCP and Oura MCP servers to fetch tasks, energy,
health, and correlation data.

Usage:
    uvicorn dashboard.main:app --host 0.0.0.0 --port 8001 --reload

The server provides endpoints for:
- Tasks overview and status
- Energy and readiness trends
- Health metrics from Oura
- Productivity correlation analysis
"""

import logging
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dashboard.api import API_V1_PREFIX
from dashboard.api.tasks import router as tasks_router
from dashboard.api.energy import router as energy_router
from dashboard.api.health import router as health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Thanos Dashboard API",
    description="REST API for Thanos visualization dashboard",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS to allow frontend access
# Allow all origins in development - tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(tasks_router, prefix=API_V1_PREFIX)
app.include_router(energy_router, prefix=API_V1_PREFIX)
app.include_router(health_router, prefix=API_V1_PREFIX)


@app.get("/")
async def root() -> Dict[str, Any]:
    """
    Root endpoint - API information.

    Returns:
        Dictionary containing API metadata and status
    """
    return {
        "name": "Thanos Dashboard API",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        Dictionary containing health status
    """
    return {
        "status": "healthy",
        "service": "thanos-dashboard-api"
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Thanos Dashboard API server...")
    uvicorn.run(
        "dashboard.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
