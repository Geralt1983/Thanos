#!/usr/bin/env python3
"""
HealthInsight Skill - Health data interpretation with energy-aware suggestions
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# MCP client imports
from Tools.adapters.mcp_bridge import MCPBridge
from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig
from Tools.adapters.base import ToolResult

logger = logging.getLogger(__name__)


# Global MCP client cache (per-process)
_oura_client_cache: Optional[MCPBridge] = None
_workos_client_cache: Optional[MCPBridge] = None


def _get_oura_client() -> MCPBridge:
    """
    Get or create MCP client for Oura operations.

    Returns:
        MCPBridge: Initialized MCP client for Oura server

    Note:
        Creates a new client on first call, then reuses the cached instance.
        MCPBridge uses session-per-call pattern, so no persistent connection.
    """
    global _oura_client_cache

    if _oura_client_cache is not None:
        return _oura_client_cache

    # Find local Oura MCP server
    oura_server = PROJECT_ROOT / "mcp-servers" / "oura-mcp" / "src" / "index.ts"

    # Create Oura MCP configuration using bun (has built-in TypeScript support)
    config = MCPServerConfig(
        name="oura",
        transport=StdioConfig(
            command="bun",
            args=["run", str(oura_server)],
            env={}
        ),
        description="Oura health tracking MCP server"
    )

    _oura_client_cache = MCPBridge(config)
    logger.debug(f"MCPBridge initialized for Oura (local: {oura_server})")

    return _oura_client_cache


def _get_workos_client() -> MCPBridge:
    """
    Get or create MCP client for WorkOS operations.

    Returns:
        MCPBridge: Initialized MCP client for WorkOS server

    Note:
        Creates a new client on first call, then reuses the cached instance.
        MCPBridge uses session-per-call pattern, so no persistent connection.
    """
    global _workos_client_cache

    if _workos_client_cache is not None:
        return _workos_client_cache

    # Find local WorkOS MCP server
    workos_server = PROJECT_ROOT / "mcp-servers" / "workos-mcp" / "src" / "index.ts"

    # Create WorkOS MCP configuration using bun (has built-in TypeScript support)
    config = MCPServerConfig(
        name="workos",
        transport=StdioConfig(
            command="bun",
            args=["run", str(workos_server)],
            env={}
        ),
        description="WorkOS personal assistant MCP server"
    )

    _workos_client_cache = MCPBridge(config)
    logger.debug(f"MCPBridge initialized for WorkOS (local: {workos_server})")

    return _workos_client_cache


async def _get_health_snapshot_async(client: MCPBridge, today: str) -> Dict[str, Any]:
    """
    Async helper to fetch Oura data with timeout handling.

    Args:
        client: MCPBridge instance for Oura server
        today: Date string in YYYY-MM-DD format

    Returns:
        Dict with readiness, sleep_score, activity, stress data
        Falls back to placeholder values on error
    """
    # Default fallback values
    readiness_score = 75
    sleep_score = 82
    activity_data = {"steps": 8500, "active_calories": 450}
    stress_data = {"stress_high": 2}

    timeout_seconds = 5.0

    # Try to get readiness score
    try:
        result: ToolResult = await asyncio.wait_for(
            client.call_tool("oura__get_daily_readiness", {
                "startDate": today,
                "endDate": today
            }),
            timeout=timeout_seconds
        )
        if result and result.success and result.data:
            # Extract readiness score from Oura data
            data = result.data
            if isinstance(data, list) and len(data) > 0:
                readiness_score = data[0].get("score", readiness_score)
            elif isinstance(data, dict):
                readiness_score = data.get("score", readiness_score)
            logger.debug(f"Oura readiness score: {readiness_score}")
    except asyncio.TimeoutError:
        logger.warning(f"Oura readiness call timed out after {timeout_seconds}s, using fallback")
    except Exception as e:
        logger.error(f"Failed to get Oura readiness: {e}")

    # Try to get sleep score
    try:
        result: ToolResult = await asyncio.wait_for(
            client.call_tool("oura__get_daily_sleep", {
                "startDate": today,
                "endDate": today
            }),
            timeout=timeout_seconds
        )
        if result and result.success and result.data:
            # Extract sleep score from Oura data
            data = result.data
            if isinstance(data, list) and len(data) > 0:
                sleep_score = data[0].get("score", sleep_score)
            elif isinstance(data, dict):
                sleep_score = data.get("score", sleep_score)
            logger.debug(f"Oura sleep score: {sleep_score}")
    except asyncio.TimeoutError:
        logger.warning(f"Oura sleep call timed out after {timeout_seconds}s, using fallback")
    except Exception as e:
        logger.error(f"Failed to get Oura sleep: {e}")

    # Try to get activity data
    try:
        result: ToolResult = await asyncio.wait_for(
            client.call_tool("oura__get_daily_activity", {
                "startDate": today,
                "endDate": today
            }),
            timeout=timeout_seconds
        )
        if result and result.success and result.data:
            # Extract activity metrics from Oura data
            data = result.data
            if isinstance(data, list) and len(data) > 0:
                activity_item = data[0]
                activity_data = {
                    "steps": activity_item.get("steps", activity_data["steps"]),
                    "active_calories": activity_item.get("active_calories", activity_data["active_calories"])
                }
            elif isinstance(data, dict):
                activity_data = {
                    "steps": data.get("steps", activity_data["steps"]),
                    "active_calories": data.get("active_calories", activity_data["active_calories"])
                }
            logger.debug(f"Oura activity: {activity_data}")
    except asyncio.TimeoutError:
        logger.warning(f"Oura activity call timed out after {timeout_seconds}s, using fallback")
    except Exception as e:
        logger.error(f"Failed to get Oura activity: {e}")

    return {
        "readiness": readiness_score,
        "sleep_score": sleep_score,
        "activity": activity_data,
        "stress": stress_data  # Stress data would come from a separate Oura endpoint if available
    }


def get_health_snapshot(mcp_client=None) -> Dict[str, Any]:
    """
    Fetch Oura data and calculate health snapshot.

    Returns:
        {
            'readiness': int,      # 0-100
            'sleep_score': int,    # 0-100
            'activity': dict,
            'stress': dict,
            'energy_level': str,   # low|medium|high
            'energy_message': str,
            'suggested_tasks': list
        }
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # Get or create MCP client
    client = mcp_client if mcp_client else _get_oura_client()

    # Fetch health data with MCP calls (async)
    try:
        health_data = asyncio.run(_get_health_snapshot_async(client, today))
        readiness_score = health_data["readiness"]
        sleep_score = health_data["sleep_score"]
        activity_data = health_data["activity"]
        stress_data = health_data["stress"]
        logger.info(f"Health snapshot retrieved: readiness={readiness_score}, sleep={sleep_score}")
    except Exception as e:
        logger.error(f"Failed to fetch health snapshot: {e}")
        # Fallback to placeholder data
        readiness_score = 75
        sleep_score = 82
        activity_data = {"steps": 8500, "active_calories": 450}
        stress_data = {"stress_high": 2}
        logger.warning("Using fallback health data")

    # Map to energy level
    energy_level = map_readiness_to_energy(readiness_score)
    energy_message = get_energy_message(energy_level, readiness_score)

    # Get energy-appropriate tasks
    suggested_tasks = get_energy_appropriate_tasks(energy_level, mcp_client)

    # Determine visual state
    visual_state = determine_visual_state(energy_level, readiness_score)

    return {
        "readiness": readiness_score,
        "sleep_score": sleep_score,
        "activity": activity_data,
        "stress": stress_data,
        "energy_level": energy_level,
        "energy_message": energy_message,
        "suggested_tasks": suggested_tasks,
        "visual_state": visual_state,
    }


def map_readiness_to_energy(score: int) -> str:
    """Map readiness score to energy level."""
    if score >= 85:
        return "high"
    elif score >= 70:
        return "medium"
    else:
        return "low"


def get_energy_message(energy_level: str, score: int) -> str:
    """Get appropriate energy message in Thanos voice."""
    if energy_level == "high":
        return "All stones are charged. Full power available."
    elif energy_level == "medium":
        return "The universe grants moderate power."
    else:
        return "The stones require charging. Rest is strategic."


def get_energy_appropriate_tasks(energy_level: str, mcp_client=None) -> List[Dict[str, Any]]:
    """
    Fetch energy-appropriate tasks from WorkOS.

    Args:
        energy_level: low|medium|high
        mcp_client: MCP client (optional)

    Returns:
        List of task dictionaries
    """
    # TODO: Call workos_get_energy_aware_tasks when MCP is integrated
    # tasks = mcp_client.call('workos_get_energy_aware_tasks', {
    #     'energy_level': energy_level,
    #     'limit': 5
    # })

    # Placeholder
    if energy_level == "low":
        return [
            {"title": "Review completed tasks", "points": 1, "valueTier": "checkbox"},
            {"title": "Brain dump loose thoughts", "points": 1, "valueTier": "checkbox"},
        ]
    elif energy_level == "medium":
        return [
            {"title": "Review Memphis client work", "points": 2, "valueTier": "progress"},
            {"title": "Plan Raleigh deliverables", "points": 2, "valueTier": "progress"},
        ]
    else:
        return [
            {"title": "Design new architecture", "points": 7, "valueTier": "milestone"},
            {"title": "Implement core feature", "points": 4, "valueTier": "deliverable"},
        ]


def determine_visual_state(energy_level: str, readiness: int) -> str:
    """Determine appropriate visual state."""
    hour = datetime.now().hour

    # Morning with low energy → CHAOS
    if 5 <= hour < 12 and energy_level == "low":
        return "CHAOS"

    # High energy and focused work → FOCUS
    if energy_level == "high":
        return "FOCUS"

    # Evening or balanced state → BALANCE
    if hour >= 18 or (energy_level == "medium" and readiness > 80):
        return "BALANCE"

    return "FOCUS"  # default


def format_health_brief(snapshot: Dict[str, Any]) -> str:
    """Format health snapshot in Thanos voice."""
    now = datetime.now()
    time_str = now.strftime("%I:%M %p").lstrip("0")

    # Build task list
    task_lines = []
    for task in snapshot["suggested_tasks"]:
        tier_symbol = {"checkbox": "☐", "progress": "▸", "deliverable": "⬤", "milestone": "★"}.get(
            task["valueTier"], "·"
        )
        task_lines.append(f"  {tier_symbol} {task['title']} ({task['points']} points)")

    task_section = "\n".join(task_lines) if task_lines else "  No tasks suggested"

    return f"""### DESTINY // {time_str}

Readiness: {snapshot['readiness']} | Sleep: {snapshot['sleep_score']} | Steps: {snapshot['activity'].get('steps', 0)}
Energy: {snapshot['energy_level'].title()}. {snapshot['energy_message']}

Suggested sacrifices:
{task_section}

Visual State: {snapshot['visual_state']}"""


def execute_health_insight(user_input: str, mcp_client=None) -> Dict[str, Any]:
    """
    Main workflow execution.

    Args:
        user_input: Raw user input
        mcp_client: MCP client (optional)

    Returns:
        {
            'success': bool,
            'response': str,
            'snapshot': dict
        }
    """
    snapshot = get_health_snapshot(mcp_client)
    response = format_health_brief(snapshot)

    return {
        "success": True,
        "response": response,
        "snapshot": snapshot,
    }


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 workflow.py \"user message\"", file=sys.stderr)
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    result = execute_health_insight(message)

    print(result["response"])


if __name__ == "__main__":
    main()
