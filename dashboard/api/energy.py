"""
Energy API endpoints.

Provides REST API endpoints for fetching energy logs from WorkOS MCP server.
Supports filtering by days/time range and includes Oura readiness integration.
"""

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

from dashboard.mcp_client import get_client

logger = logging.getLogger(__name__)

# Create energy router
router = APIRouter(prefix="/energy", tags=["energy"])


@router.get("")
async def get_energy(
    days: Optional[int] = Query(
        default=7,
        description="Number of days to retrieve energy logs",
        ge=1,
        le=90
    )
) -> Dict[str, Any]:
    """
    Get energy logs from WorkOS.

    Fetches energy logs from the WorkOS MCP server for the specified number of days.
    Energy logs include level (high/medium/low), optional notes, and Oura metrics
    (readiness score, HRV, sleep score) when available.

    Args:
        days: Number of days to retrieve (1-90, default 7)

    Returns:
        Dictionary containing energy logs array and metadata

    Raises:
        HTTPException: 500 if WorkOS MCP communication fails
        HTTPException: 400 if parameters are invalid
    """
    try:
        # Get MCP client
        client = get_client()

        # Call WorkOS MCP to get energy logs
        logger.info(f"Fetching energy logs for {days} days")
        energy_logs = await client.get_energy_logs(days=days)

        # Handle MCP client errors
        if energy_logs is None:
            logger.error("WorkOS MCP returned None (connection failure)")
            raise HTTPException(
                status_code=500,
                detail="Failed to connect to WorkOS MCP server"
            )

        # Return response with metadata
        return {
            "success": True,
            "data": {
                "energy_logs": energy_logs,
                "count": len(energy_logs),
                "filters": {
                    "days": days
                }
            }
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching energy logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
