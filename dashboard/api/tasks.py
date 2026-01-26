"""
Tasks API endpoints.

Provides REST API endpoints for fetching tasks from WorkOS MCP server.
Supports filtering by status, client, and pagination.
"""

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

from dashboard.mcp_client import get_client

logger = logging.getLogger(__name__)

# Create tasks router
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
async def get_tasks(
    status: Optional[str] = Query(
        default="active",
        description="Filter by status: active, queued, backlog, done"
    ),
    client_id: Optional[int] = Query(
        default=None,
        alias="clientId",
        description="Filter by client ID"
    ),
    client_name: Optional[str] = Query(
        default=None,
        alias="clientName",
        description="Filter by client name (case-insensitive)"
    ),
    limit: Optional[int] = Query(
        default=50,
        description="Maximum number of tasks to return",
        ge=1,
        le=500
    )
) -> Dict[str, Any]:
    """
    Get tasks from WorkOS.

    Fetches tasks from the WorkOS MCP server with optional filtering by status,
    client ID, or client name. Supports pagination via limit parameter.

    Args:
        status: Task status filter ('active', 'queued', 'backlog', 'done')
        client_id: Optional client ID filter
        client_name: Optional client name filter (case-insensitive)
        limit: Maximum number of tasks to return (1-500, default 50)

    Returns:
        Dictionary containing tasks array and metadata

    Raises:
        HTTPException: 500 if WorkOS MCP communication fails
        HTTPException: 400 if parameters are invalid
    """
    # Validate status parameter
    valid_statuses = ["active", "queued", "backlog", "done"]
    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    try:
        # Get MCP client
        client = get_client()

        # Build MCP tool arguments
        mcp_args = {"status": status, "limit": limit}

        # Add client filters if provided
        if client_id is not None:
            mcp_args["clientId"] = client_id
        if client_name is not None:
            mcp_args["clientName"] = client_name

        # Call WorkOS MCP via bridge
        logger.info(f"Fetching tasks with args: {mcp_args}")
        tasks = await client.get_tasks(status=status)

        # Handle MCP client errors
        if tasks is None:
            logger.error("WorkOS MCP returned None (connection failure)")
            raise HTTPException(
                status_code=500,
                detail="Failed to connect to WorkOS MCP server"
            )

        # Apply client filters if needed (MCP client currently only supports status)
        # TODO: When MCP client supports clientId/clientName filters, remove this
        filtered_tasks = tasks
        if client_id is not None:
            filtered_tasks = [t for t in filtered_tasks if t.get("clientId") == client_id]
        if client_name is not None:
            filtered_tasks = [
                t for t in filtered_tasks
                if t.get("clientName", "").lower() == client_name.lower()
            ]

        # Apply limit
        filtered_tasks = filtered_tasks[:limit]

        # Return response with metadata
        return {
            "success": True,
            "data": {
                "tasks": filtered_tasks,
                "count": len(filtered_tasks),
                "filters": {
                    "status": status,
                    "clientId": client_id,
                    "clientName": client_name,
                    "limit": limit
                }
            }
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/metrics")
async def get_today_metrics() -> Dict[str, Any]:
    """
    Get today's productivity metrics.

    Fetches today's work progress including points earned, target, pace status,
    streak information, and clients touched.

    Returns:
        Dictionary containing today's metrics

    Raises:
        HTTPException: 500 if WorkOS MCP communication fails
    """
    try:
        # Get MCP client
        client = get_client()

        # Call WorkOS MCP
        logger.info("Fetching today's metrics")
        metrics = await client.get_today_metrics()

        # Handle MCP client errors
        if metrics is None:
            logger.error("WorkOS MCP returned None (connection failure)")
            raise HTTPException(
                status_code=500,
                detail="Failed to connect to WorkOS MCP server"
            )

        return {
            "success": True,
            "data": metrics
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching today metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
