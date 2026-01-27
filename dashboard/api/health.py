"""
Health API endpoints.

Provides REST API endpoints for fetching health metrics from Oura MCP server.
Supports readiness scores, sleep data, and activity metrics.
"""

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

from dashboard.mcp_client import get_client

logger = logging.getLogger(__name__)

# Create health router
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/readiness")
async def get_readiness(
    days: Optional[int] = Query(
        default=7,
        description="Number of days to retrieve readiness data",
        ge=1,
        le=90
    )
) -> Dict[str, Any]:
    """
    Get readiness scores from Oura.

    Fetches readiness data from the Oura MCP server for the specified number of days.
    Readiness scores (0-100) indicate physical and mental recovery. Contributors include:
    sleep quality, HRV balance, body temperature, resting heart rate, activity balance,
    and recovery index.

    Higher scores (85+) indicate excellent readiness. Lower scores (<70) suggest the
    body needs rest.

    Args:
        days: Number of days to retrieve (1-90, default 7)

    Returns:
        Dictionary containing readiness data array and metadata

    Raises:
        HTTPException: 500 if Oura MCP communication fails
        HTTPException: 400 if parameters are invalid
    """
    try:
        # Get MCP client
        client = get_client()

        # Call Oura MCP to get readiness data
        logger.info(f"Fetching readiness data for {days} days")
        readiness_data = await client.get_readiness(days=days)

        # Handle MCP client errors
        if readiness_data is None:
            logger.error("Oura MCP returned None (connection failure)")
            raise HTTPException(
                status_code=500,
                detail="Failed to connect to Oura MCP server"
            )

        # Return response with metadata
        return {
            "success": True,
            "data": {
                "readiness": readiness_data,
                "count": len(readiness_data),
                "filters": {
                    "days": days
                }
            }
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching readiness data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
