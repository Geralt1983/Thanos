"""
Correlations API endpoints.

Provides REST API endpoints for analyzing correlations between productivity
metrics (tasks, points) and health/energy data (Oura readiness, energy logs).
"""

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

from dashboard.mcp_client import get_client

logger = logging.getLogger(__name__)

# Create correlations router
router = APIRouter(prefix="/correlations", tags=["correlations"])


@router.get("")
async def get_correlations(
    days: Optional[int] = Query(
        default=7,
        description="Number of days to analyze for correlations",
        ge=1,
        le=90
    )
) -> Dict[str, Any]:
    """
    Get productivity-health correlations.

    Analyzes correlations between task completion/points earned and energy levels/
    readiness scores over the specified time period. Useful for identifying patterns
    between physical state and productivity output.

    The endpoint combines data from:
    - WorkOS tasks (completion dates, points earned)
    - WorkOS energy logs (high/medium/low energy levels)
    - Oura readiness scores (0-100 physical readiness)

    Returns daily aggregated data and basic correlation statistics.

    Args:
        days: Number of days to analyze (1-90, default 7)

    Returns:
        Dictionary containing:
        - daily_data: List of daily aggregates with tasks, energy, and readiness
        - stats: Basic correlation statistics
        - days_analyzed: Number of days requested

    Raises:
        HTTPException: 500 if MCP communication fails
        HTTPException: 400 if parameters are invalid
    """
    try:
        # Get MCP client
        client = get_client()

        # Call MCP client to get correlation data
        logger.info(f"Fetching correlation data for {days} days")
        correlation_data = await client.get_correlations(days=days)

        # Handle MCP client errors
        if correlation_data is None:
            logger.error("MCP client returned None (connection failure)")
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch correlation data from MCP servers"
            )

        # Return response with metadata
        return {
            "success": True,
            "data": correlation_data
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching correlations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
