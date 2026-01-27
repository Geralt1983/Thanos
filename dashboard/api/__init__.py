"""
Thanos Dashboard API Routes.

This package contains API route modules for the dashboard backend.
Each module defines FastAPI routers for different domains (tasks, energy, health).
"""

from fastapi import APIRouter

# API version prefix
API_V1_PREFIX = "/api"

__all__ = ["API_V1_PREFIX"]
