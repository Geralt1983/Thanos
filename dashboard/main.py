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


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Thanos Dashboard API server...")
    uvicorn.run(
        "dashboard.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
