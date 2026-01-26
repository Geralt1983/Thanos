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


# MCP call timeout configuration (seconds)
MCP_CALL_TIMEOUT_SECONDS = 5.0

# Global MCP client cache (per-process)
_oura_client_cache: Optional[MCPBridge] = None
_workos_client_cache: Optional[MCPBridge] = None


def _get_oura_client() -> MCPBridge:
    """
    Get or create MCP client for Oura operations.

    Returns:
        MCPBridge: Initialized MCP client for Oura server

    Raises:
        RuntimeError: If MCP client cannot be initialized with actionable error message

    Note:
        Creates a new client on first call, then reuses the cached instance.
        MCPBridge uses session-per-call pattern, so no persistent connection.
    """
    global _oura_client_cache

    if _oura_client_cache is not None:
        return _oura_client_cache

    # Find local Oura MCP server
    oura_server = PROJECT_ROOT / "mcp-servers" / "oura-mcp" / "src" / "index.ts"

    if not oura_server.exists():
        raise RuntimeError(
            f"❌ Oura MCP server not found at: {oura_server}\n\n"
            f"Troubleshooting:\n"
            f"  1. Check if the MCP server is installed:\n"
            f"     ls -la {oura_server.parent}\n"
            f"  2. Verify project structure is intact\n"
            f"  3. Reinstall dependencies if needed:\n"
            f"     cd {oura_server.parent} && bun install"
        )

    try:
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

    except FileNotFoundError as e:
        raise RuntimeError(
            f"❌ 'bun' command not found. The MCP server requires Bun to run.\n\n"
            f"Troubleshooting:\n"
            f"  1. Install Bun:\n"
            f"     curl -fsSL https://bun.sh/install | bash\n"
            f"  2. Restart your terminal after installation\n"
            f"  3. Verify installation: bun --version\n\n"
            f"Original error: {e}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"❌ Failed to initialize Oura MCP client.\n\n"
            f"Troubleshooting:\n"
            f"  1. Check if server file exists:\n"
            f"     ls -la {oura_server}\n"
            f"  2. Verify dependencies installed:\n"
            f"     cd {oura_server.parent} && bun install\n"
            f"  3. Test server manually:\n"
            f"     bun run {oura_server}\n"
            f"  4. Check if OURA_API_KEY is set:\n"
            f"     echo $OURA_API_KEY\n"
            f"  5. Check logs in: {PROJECT_ROOT}/logs/\n\n"
            f"Original error: {e}"
        ) from e


def _get_workos_client() -> MCPBridge:
    """
    Get or create MCP client for WorkOS operations.

    Returns:
        MCPBridge: Initialized MCP client for WorkOS server

    Raises:
        RuntimeError: If MCP client cannot be initialized with actionable error message

    Note:
        Creates a new client on first call, then reuses the cached instance.
        MCPBridge uses session-per-call pattern, so no persistent connection.
    """
    global _workos_client_cache

    if _workos_client_cache is not None:
        return _workos_client_cache

    # Find local WorkOS MCP server
    workos_server = PROJECT_ROOT / "mcp-servers" / "workos-mcp" / "src" / "index.ts"

    if not workos_server.exists():
        raise RuntimeError(
            f"❌ WorkOS MCP server not found at: {workos_server}\n\n"
            f"Troubleshooting:\n"
            f"  1. Check if the MCP server is installed:\n"
            f"     ls -la {workos_server.parent}\n"
            f"  2. Verify project structure is intact\n"
            f"  3. Reinstall dependencies if needed:\n"
            f"     cd {workos_server.parent} && bun install"
        )

    try:
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

    except FileNotFoundError as e:
        raise RuntimeError(
            f"❌ 'bun' command not found. The MCP server requires Bun to run.\n\n"
            f"Troubleshooting:\n"
            f"  1. Install Bun:\n"
            f"     curl -fsSL https://bun.sh/install | bash\n"
            f"  2. Restart your terminal after installation\n"
            f"  3. Verify installation: bun --version\n\n"
            f"Original error: {e}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"❌ Failed to initialize WorkOS MCP client.\n\n"
            f"Troubleshooting:\n"
            f"  1. Check if server file exists:\n"
            f"     ls -la {workos_server}\n"
            f"  2. Verify dependencies installed:\n"
            f"     cd {workos_server.parent} && bun install\n"
            f"  3. Test server manually:\n"
            f"     bun run {workos_server}\n"
            f"  4. Check logs in: {PROJECT_ROOT}/logs/\n\n"
            f"Original error: {e}"
        ) from e


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

    timeout_seconds = MCP_CALL_TIMEOUT_SECONDS

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
        logger.warning(
            f"⏱️ Oura readiness call timed out after {timeout_seconds}s. "
            f"The MCP server may be slow or unresponsive. Using fallback value."
        )
    except ConnectionRefusedError as e:
        logger.warning(
            f"❌ Cannot connect to Oura MCP server. "
            f"Check if the server is running: bun run {PROJECT_ROOT}/mcp-servers/oura-mcp/src/index.ts"
        )
    except Exception as e:
        logger.error(
            f"⚠️ Failed to get Oura readiness: {e}. "
            f"Using fallback value. Verify OURA_API_KEY is set and server is healthy."
        )

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
        logger.warning(
            f"⏱️ Oura sleep call timed out after {timeout_seconds}s. "
            f"The MCP server may be slow or unresponsive. Using fallback value."
        )
    except ConnectionRefusedError as e:
        logger.warning(
            f"❌ Cannot connect to Oura MCP server. "
            f"Check if the server is running: bun run {PROJECT_ROOT}/mcp-servers/oura-mcp/src/index.ts"
        )
    except Exception as e:
        logger.error(
            f"⚠️ Failed to get Oura sleep: {e}. "
            f"Using fallback value. Check server health and API key."
        )

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
        logger.warning(
            f"⏱️ Oura activity call timed out after {timeout_seconds}s. "
            f"The MCP server may be slow or unresponsive. Using fallback value."
        )
    except ConnectionRefusedError as e:
        logger.warning(
            f"❌ Cannot connect to Oura MCP server. "
            f"Check if the server is running: bun run {PROJECT_ROOT}/mcp-servers/oura-mcp/src/index.ts"
        )
    except Exception as e:
        logger.error(
            f"⚠️ Failed to get Oura activity: {e}. "
            f"Using fallback value. Check server health and API key."
        )

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


async def _get_energy_appropriate_tasks_async(
    client: MCPBridge,
    energy_level: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Async helper to fetch energy-appropriate tasks from WorkOS.

    Args:
        client: MCPBridge instance for WorkOS server
        energy_level: low|medium|high
        limit: Maximum tasks to return

    Returns:
        List of task dictionaries filtered by energy-appropriate drain types
    """
    # Map energy level to drain types
    # low → admin (low cognitive load)
    # medium → shallow (moderate cognitive load)
    # high → deep (high cognitive load)
    drain_type_map = {
        "low": "admin",
        "medium": "shallow",
        "high": "deep"
    }

    target_drain_type = drain_type_map.get(energy_level, "shallow")
    timeout_seconds = MCP_CALL_TIMEOUT_SECONDS

    try:
        # Get active tasks from WorkOS
        result: ToolResult = await asyncio.wait_for(
            client.call_tool("workos_get_tasks", {
                "status": "active",
                "limit": limit * 3  # Fetch extra to allow filtering
            }),
            timeout=timeout_seconds
        )

        if result and result.success and result.data:
            tasks = result.data if isinstance(result.data, list) else []

            # Filter tasks by appropriate drain type
            filtered_tasks = [
                task for task in tasks
                if task.get("drainType") == target_drain_type
            ]

            # Limit results
            filtered_tasks = filtered_tasks[:limit]

            logger.debug(f"Found {len(filtered_tasks)} {target_drain_type} tasks for {energy_level} energy")
            return filtered_tasks

    except asyncio.TimeoutError:
        logger.warning(
            f"⏱️ WorkOS get_tasks timed out after {timeout_seconds}s. "
            f"The MCP server may be slow or unresponsive. Using fallback suggestions."
        )
    except ConnectionRefusedError as e:
        logger.warning(
            f"❌ Cannot connect to WorkOS MCP server. "
            f"Check if the server is running: bun run {PROJECT_ROOT}/mcp-servers/workos-mcp/src/index.ts"
        )
    except Exception as e:
        logger.error(
            f"⚠️ Failed to get WorkOS tasks: {e}. "
            f"Using fallback suggestions. Check server health."
        )

    # Fallback to empty list
    return []


def get_energy_appropriate_tasks(energy_level: str, mcp_client=None) -> List[Dict[str, Any]]:
    """
    Fetch energy-appropriate tasks from WorkOS.

    Args:
        energy_level: low|medium|high
        mcp_client: MCP client (optional)

    Returns:
        List of task dictionaries
    """
    # Get or create WorkOS MCP client
    client = mcp_client if mcp_client else _get_workos_client()

    # Fetch tasks via MCP (async)
    try:
        tasks = asyncio.run(_get_energy_appropriate_tasks_async(client, energy_level, limit=5))

        if tasks:
            return tasks

        # If no tasks found for exact drain type, provide fallback suggestions
        logger.info(f"No {energy_level}-energy tasks found, using fallback suggestions")

    except Exception as e:
        logger.error(f"Failed to fetch energy-appropriate tasks: {e}")

    # Fallback suggestions if MCP call fails or no tasks match
    if energy_level == "low":
        return [
            {"title": "Review completed tasks", "points": 1, "valueTier": "checkbox", "drainType": "admin"},
            {"title": "Brain dump loose thoughts", "points": 1, "valueTier": "checkbox", "drainType": "admin"},
        ]
    elif energy_level == "medium":
        return [
            {"title": "Review client work", "points": 2, "valueTier": "progress", "drainType": "shallow"},
            {"title": "Plan deliverables", "points": 2, "valueTier": "progress", "drainType": "shallow"},
        ]
    else:
        return [
            {"title": "Design new architecture", "points": 7, "valueTier": "milestone", "drainType": "deep"},
            {"title": "Implement core feature", "points": 4, "valueTier": "deliverable", "drainType": "deep"},
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
