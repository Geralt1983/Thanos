#!/usr/bin/env python3
"""
TaskRouter Skill - Workflow Implementation

Handles task operations with energy-aware gating and priority tracking.
"""

import os
import sys
import re
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path
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
_mcp_client_cache: Optional[MCPBridge] = None
_oura_client_cache: Optional[MCPBridge] = None


def _get_mcp_client() -> MCPBridge:
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
    global _mcp_client_cache

    if _mcp_client_cache is not None:
        return _mcp_client_cache

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

        _mcp_client_cache = MCPBridge(config)
        logger.debug(f"MCPBridge initialized for WorkOS (local: {workos_server})")

        return _mcp_client_cache

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


class TaskIntent:
    """Parsed task intent."""

    def __init__(
        self,
        action: str,
        title: Optional[str] = None,
        task_id: Optional[int] = None,
        client_name: Optional[str] = None,
        value_tier: Optional[str] = None,
        cognitive_load: Optional[str] = None,
        drain_type: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
    ):
        self.action = action  # create|complete|promote|update|delete|query
        self.title = title
        self.task_id = task_id
        self.client_name = client_name
        self.value_tier = value_tier or "checkbox"
        self.cognitive_load = cognitive_load or "medium"
        self.drain_type = drain_type or "shallow"
        self.description = description
        self.status = status or "active"


def parse_intent(user_message: str) -> TaskIntent:
    """
    Parse user message to determine task intent and extract parameters.

    Args:
        user_message: Raw user input

    Returns:
        TaskIntent object with parsed parameters
    """
    lower_msg = user_message.lower()

    # Determine action
    action = "query"  # default

    if any(word in lower_msg for word in ["add", "create", "make", "new"]):
        action = "create"
    elif any(word in lower_msg for word in ["complete", "finish", "done", "mark as complete"]):
        action = "complete"
    elif any(word in lower_msg for word in ["promote", "elevate", "activate"]):
        action = "promote"
    elif any(word in lower_msg for word in ["update", "modify", "change", "edit"]):
        action = "update"
    elif any(word in lower_msg for word in ["delete", "remove"]):
        action = "delete"
    elif any(word in lower_msg for word in ["show", "list", "get", "view", "what"]):
        action = "query"

    # Extract title (for create action)
    title = None
    if action == "create":
        # Try to extract task title
        # Pattern: "add a task to X" or "create task: X"
        patterns = [
            r"task\s+to\s+(.+?)(?:\s*$|\.)",
            r"task:\s+(.+?)(?:\s*$|\.)",
            r"(?:add|create)\s+(?:a\s+)?(.+?)\s+task",
            r"(?:add|create)\s+task\s+(.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, lower_msg)
            if match:
                title = match.group(1).strip()
                break

        # Fallback: use message after "task"
        if not title:
            task_idx = lower_msg.find("task")
            if task_idx != -1:
                title = user_message[task_idx + 4 :].strip()

    # Detect complexity from keywords
    cognitive_load = "medium"
    high_complexity_keywords = [
        "design",
        "architect",
        "refactor",
        "implement",
        "build",
        "create",
        "develop",
        "research",
        "analyze",
        "plan",
    ]

    low_complexity_keywords = [
        "review",
        "check",
        "read",
        "respond",
        "reply",
        "schedule",
        "organize",
    ]

    if any(keyword in lower_msg for keyword in high_complexity_keywords):
        cognitive_load = "high"
    elif any(keyword in lower_msg for keyword in low_complexity_keywords):
        cognitive_load = "low"

    # Detect value tier
    value_tier = "checkbox"
    if any(word in lower_msg for word in ["milestone", "major", "critical"]):
        value_tier = "milestone"
    elif any(word in lower_msg for word in ["deliverable", "ship", "launch"]):
        value_tier = "deliverable"
    elif any(word in lower_msg for word in ["progress", "ongoing"]):
        value_tier = "progress"

    return TaskIntent(
        action=action,
        title=title,
        cognitive_load=cognitive_load,
        value_tier=value_tier,
    )


async def _get_energy_level_async() -> tuple[int, str]:
    """
    Async implementation of energy level retrieval.

    Tries Oura readiness first, falls back to WorkOS energy log.

    Returns:
        tuple: (readiness_score, energy_level)
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # Try Oura readiness first
    try:
        oura_client = _get_oura_client()

        # Call with 5s timeout
        result: ToolResult = await asyncio.wait_for(
            oura_client.call_tool(
                "oura__get_daily_readiness",
                {"startDate": today, "endDate": today}
            ),
            timeout=MCP_CALL_TIMEOUT_SECONDS
        )

        if result.success and result.data and len(result.data) > 0:
            score = result.data[0].get("score", 75)
            energy = map_readiness_to_energy(score)
            logger.debug(f"Got Oura readiness: {score} -> {energy}")
            return (score, energy)
    except asyncio.TimeoutError:
        logger.warning(
            f"⏱️ Oura MCP call timed out after {MCP_CALL_TIMEOUT_SECONDS}s. "
            f"The MCP server may be slow or unresponsive. Using fallback value."
        )
    except ConnectionRefusedError as e:
        logger.warning(
            f"❌ Cannot connect to Oura MCP server. "
            f"Check if the server is running: bun run {PROJECT_ROOT}/mcp-servers/oura-mcp/src/index.ts"
        )
    except Exception as e:
        logger.warning(
            f"⚠️ Failed to get Oura readiness: {e}. "
            f"Using fallback value. Check server health."
        )

    # Fallback to WorkOS energy log
    try:
        workos_client = _get_mcp_client()

        # Call with 5s timeout
        result: ToolResult = await asyncio.wait_for(
            workos_client.call_tool(
                "workos_get_energy",
                {"limit": 1}
            ),
            timeout=MCP_CALL_TIMEOUT_SECONDS
        )

        if result.success and result.data and len(result.data) > 0:
            # Map WorkOS energy level to readiness score
            level = result.data[0].get("level", "medium")
            score = _map_energy_level_to_score(level)
            energy = map_readiness_to_energy(score)
            logger.debug(f"Got WorkOS energy: {level} -> {score} -> {energy}")
            return (score, energy)
    except asyncio.TimeoutError:
        logger.warning(
            f"⏱️ WorkOS MCP call timed out after {MCP_CALL_TIMEOUT_SECONDS}s. "
            f"The MCP server may be slow or unresponsive. Using fallback value."
        )
    except ConnectionRefusedError as e:
        logger.warning(
            f"❌ Cannot connect to WorkOS MCP server. "
            f"Check if the server is running: bun run {PROJECT_ROOT}/mcp-servers/workos-mcp/src/index.ts"
        )
    except Exception as e:
        logger.warning(
            f"⚠️ Failed to get WorkOS energy: {e}. "
            f"Using fallback value. Check server health."
        )

    # Final fallback - assume medium energy
    logger.info("Using fallback energy level: medium (75)")
    return (75, "medium")


def _map_energy_level_to_score(level: str) -> int:
    """Map WorkOS energy level string to readiness score."""
    mapping = {
        "high": 85,
        "medium": 75,
        "low": 60,
        "exhausted": 50
    }
    return mapping.get(level.lower(), 75)


def get_energy_level() -> tuple[int, str]:
    """
    Get current energy level from Oura or WorkOS.

    Returns:
        tuple: (readiness_score, energy_level)
               energy_level: 'low'|'medium'|'high'

    Note:
        This is a synchronous wrapper around async MCP calls.
        Tries Oura readiness first, falls back to WorkOS energy.
        Always returns a value (defaults to medium if all sources fail).
    """
    return asyncio.run(_get_energy_level_async())


def map_readiness_to_energy(score: int) -> str:
    """Map readiness score to energy level."""
    if score >= 85:
        return "high"
    elif score >= 70:
        return "medium"
    else:
        return "low"


def should_gate_task(intent: TaskIntent, energy_level: str) -> bool:
    """
    Determine if task should be gated based on energy and complexity.

    Args:
        intent: Parsed task intent
        energy_level: Current energy level

    Returns:
        bool: True if task should be gated
    """
    if intent.action != "create":
        return False  # Only gate creation

    if energy_level == "low" and intent.cognitive_load == "high":
        return True

    return False


def get_suggested_alternatives(energy_level: str) -> List[str]:
    """
    Get suggested low-complexity alternatives for current energy level.

    Args:
        energy_level: Current energy level

    Returns:
        List of suggested task types
    """
    if energy_level == "low":
        return [
            "Review completed tasks",
            "Brain dump loose thoughts",
            "Check off a simple checkbox task",
            "Respond to low-priority emails",
            "Organize files or notes",
        ]
    elif energy_level == "medium":
        return [
            "Make progress on ongoing tasks",
            "Plan next steps for projects",
            "Review and update documentation",
            "Coordinate with team members",
        ]
    else:
        return []


def detect_priority_shift(user_message: str) -> bool:
    """
    Detect if message indicates a priority shift.

    Args:
        user_message: Raw user input

    Returns:
        bool: True if priority shift detected
    """
    indicators = [
        r"top priority",
        r"highest priority",
        r"more important than",
        r"focus on.*instead",
        r"switch to",
        r"most urgent",
        r"critical.*this week",
    ]

    lower_msg = user_message.lower()

    for pattern in indicators:
        if re.search(pattern, lower_msg):
            return True

    return False


def extract_new_priorities(user_message: str) -> List[str]:
    """
    Extract new priorities from user message.

    Args:
        user_message: Raw user input

    Returns:
        List of priority items
    """
    # Simple extraction - in production, use more sophisticated NLP
    priorities = []

    # Look for explicit priority statements
    patterns = [
        r"priority(?:\s+\d+)?[:\s]+(.+?)(?:\.|$)",
        r"focus on\s+(.+?)(?:\.|$)",
        r"top priority:\s+(.+?)(?:\.|$)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, user_message, re.IGNORECASE)
        priorities.extend([m.strip() for m in matches])

    return priorities[:3]  # Top 3


def update_current_focus(new_priorities: List[str]) -> None:
    """
    Update State/CurrentFocus.md with new priorities.

    Args:
        new_priorities: List of priority items
    """
    focus_file = PROJECT_ROOT / "State" / "CurrentFocus.md"

    if not focus_file.exists():
        return

    content = focus_file.read_text()

    # Find priorities section
    priorities_section_match = re.search(
        r"(## Priorities\n)(.*?)(?=\n##|\Z)", content, re.DOTALL
    )

    if priorities_section_match:
        # Build new priorities list
        new_section = "## Priorities\n"
        for i, priority in enumerate(new_priorities, 1):
            new_section += f"- {priority}\n"

        # Replace section
        updated_content = (
            content[: priorities_section_match.start()]
            + new_section
            + content[priorities_section_match.end() :]
        )

        focus_file.write_text(updated_content)


def format_thanos_response(
    intent: TaskIntent, result: Dict[str, Any], energy_score: int = 0
) -> str:
    """
    Format response in Thanos voice.

    Args:
        intent: Task intent
        result: Execution result
        energy_score: Readiness score (optional)

    Returns:
        Formatted response string
    """
    action = intent.action

    if action == "create":
        if result.get("gated"):
            alternatives = "\n".join(f"  - {alt}" for alt in result["alternatives"])
            return f"""### DESTINY // LOW POWER STATE

Readiness: {energy_score}. The stones require charging.

This task demands high cognitive load. Your current state suggests:
{alternatives}

The universe demands patience. Proceed anyway?"""

        points = _estimate_points(intent.value_tier)
        return f"""The task has been added to your sacrifices.
{intent.title}
+{points} toward the balance."""

    elif action == "complete":
        points = result.get("points", 0)
        progress = result.get("progress", "")
        target = result.get("target", "")

        return f"""A small price to pay for salvation.
{intent.title} has been snapped from existence.
+{points} toward the balance.
{progress}/{target} complete."""

    elif action == "promote":
        return f"""{intent.title} elevated to active status.
The work does not wait."""

    elif action == "query":
        tasks = result.get("tasks", [])
        if not tasks:
            return "The list is empty. A moment of balance."

        task_list = "\n".join(
            f"  [{task.get('valueTier', '')[0].upper()}] {task.get('title', '')}"
            for task in tasks
        )

        return f"""Your current sacrifices:
{task_list}

Dread it. Run from it. The work arrives all the same."""

    else:
        return "Task operation acknowledged."


def _estimate_points(value_tier: str) -> int:
    """Estimate points for value tier."""
    point_map = {"checkbox": 1, "progress": 2, "deliverable": 4, "milestone": 7}
    return point_map.get(value_tier, 1)


async def _execute_task_operation_async(
    intent: TaskIntent, mcp_client: MCPBridge
) -> Dict[str, Any]:
    """
    Execute task operation via MCP (async implementation).

    Args:
        intent: Parsed task intent
        mcp_client: MCP client instance

    Returns:
        Execution result dict
    """
    try:
        if intent.action == "create":
            # Build arguments for create_task
            args = {"title": intent.title}

            if intent.value_tier:
                args["valueTier"] = intent.value_tier
            if intent.drain_type:
                args["drainType"] = intent.drain_type
            if intent.status:
                args["status"] = intent.status
            if intent.description:
                args["description"] = intent.description
            # Note: client_id lookup could be added here if needed

            # Call with 5s timeout
            result: ToolResult = await asyncio.wait_for(
                mcp_client.call_tool("workos_create_task", args),
                timeout=MCP_CALL_TIMEOUT_SECONDS
            )

            if result.success:
                task = result.data
                return {
                    "success": True,
                    "task": task,
                    "points": _estimate_points(intent.value_tier)
                }
            else:
                logger.error(f"Failed to create task: {result.error}")
                return {"success": False, "error": result.error}

        elif intent.action == "complete":
            if not intent.task_id:
                return {"success": False, "error": "Task ID required for complete action"}

            # Call with 5s timeout
            result: ToolResult = await asyncio.wait_for(
                mcp_client.call_tool("workos_complete_task", {"taskId": intent.task_id}),
                timeout=MCP_CALL_TIMEOUT_SECONDS
            )

            if result.success:
                # Get today's metrics to show progress
                try:
                    metrics_result: ToolResult = await asyncio.wait_for(
                        mcp_client.call_tool("workos_get_today_metrics"),
                        timeout=MCP_CALL_TIMEOUT_SECONDS
                    )
                    metrics = metrics_result.data if metrics_result.success else {}
                except asyncio.TimeoutError:
                    logger.warning("Metrics fetch timed out, using defaults")
                    metrics = {}

                return {
                    "success": True,
                    "points": _estimate_points(intent.value_tier),
                    "progress": metrics.get("pointsToday", 0),
                    "target": metrics.get("dailyGoal", 18)
                }
            else:
                logger.error(f"Failed to complete task: {result.error}")
                return {"success": False, "error": result.error}

        elif intent.action == "promote":
            if not intent.task_id:
                return {"success": False, "error": "Task ID required for promote action"}

            # Call with 5s timeout
            result: ToolResult = await asyncio.wait_for(
                mcp_client.call_tool("workos_promote_task", {"taskId": intent.task_id}),
                timeout=MCP_CALL_TIMEOUT_SECONDS
            )

            if result.success:
                return {"success": True}
            else:
                logger.error(f"Failed to promote task: {result.error}")
                return {"success": False, "error": result.error}

        elif intent.action == "update":
            if not intent.task_id:
                return {"success": False, "error": "Task ID required for update action"}

            # Build arguments for update_task
            args = {"taskId": intent.task_id}

            if intent.title:
                args["title"] = intent.title
            if intent.description:
                args["description"] = intent.description
            if intent.status:
                args["status"] = intent.status
            if intent.value_tier:
                args["valueTier"] = intent.value_tier
            if intent.drain_type:
                args["drainType"] = intent.drain_type

            # Call with 5s timeout
            result: ToolResult = await asyncio.wait_for(
                mcp_client.call_tool("workos_update_task", args),
                timeout=MCP_CALL_TIMEOUT_SECONDS
            )

            if result.success:
                return {"success": True}
            else:
                logger.error(f"Failed to update task: {result.error}")
                return {"success": False, "error": result.error}

        elif intent.action == "delete":
            if not intent.task_id:
                return {"success": False, "error": "Task ID required for delete action"}

            # Call with 5s timeout
            result: ToolResult = await asyncio.wait_for(
                mcp_client.call_tool("workos_delete_task", {"taskId": intent.task_id}),
                timeout=MCP_CALL_TIMEOUT_SECONDS
            )

            if result.success:
                return {"success": True}
            else:
                logger.error(f"Failed to delete task: {result.error}")
                return {"success": False, "error": result.error}

        elif intent.action == "query":
            # Build arguments for get_tasks
            args = {}

            if intent.status:
                args["status"] = intent.status
            # Could add client_id filter here if needed

            # Call with 5s timeout
            result: ToolResult = await asyncio.wait_for(
                mcp_client.call_tool("workos_get_tasks", args),
                timeout=MCP_CALL_TIMEOUT_SECONDS
            )

            if result.success:
                return {"success": True, "tasks": result.data}
            else:
                logger.error(f"Failed to query tasks: {result.error}")
                return {"success": False, "error": result.error}

        else:
            return {"success": False, "error": f"Unknown action: {intent.action}"}

    except asyncio.TimeoutError:
        logger.error(
            f"⏱️ MCP call timed out after {MCP_CALL_TIMEOUT_SECONDS}s for action: {intent.action}"
        )
        return {
            "success": False,
            "error": (
                f"Operation timed out after {MCP_CALL_TIMEOUT_SECONDS}s. "
                f"The MCP server may be overloaded or unresponsive.\n"
                f"Try again or check server health."
            )
        }
    except ConnectionRefusedError as e:
        logger.error(f"❌ Cannot connect to WorkOS MCP server: {e}")
        return {
            "success": False,
            "error": (
                f"Cannot connect to WorkOS MCP server.\n"
                f"Check if server is running: bun run {PROJECT_ROOT}/mcp-servers/workos-mcp/src/index.ts"
            )
        }
    except Exception as e:
        logger.error(f"⚠️ Unexpected error executing task operation: {e}")
        error_msg = str(e)
        if "tool not found" in error_msg.lower():
            return {
                "success": False,
                "error": (
                    f"Tool not found: {error_msg}\n"
                    f"The MCP server may not support this operation. "
                    f"Check server implementation or API version."
                )
            }
        elif "invalid" in error_msg.lower() or "missing" in error_msg.lower():
            return {
                "success": False,
                "error": (
                    f"Invalid parameters: {error_msg}\n"
                    f"Check the data format and required fields."
                )
            }
        else:
            return {
                "success": False,
                "error": f"Unexpected error: {error_msg}\nCheck server logs for details."
            }


def execute_task_operation(
    user_input: str, mcp_client=None
) -> Dict[str, Any]:
    """
    Main workflow execution.

    Args:
        user_input: Raw user input
        mcp_client: MCP client instance (optional, for testing)

    Returns:
        {
            'success': bool,
            'action': str,
            'response': str,
            'priority_shift': bool,
            'updated_focus': list
        }
    """
    # 1. Parse intent
    intent = parse_intent(user_input)

    # 2. Get energy level
    energy_score, energy_level = get_energy_level()

    # 3. Check if should gate
    if should_gate_task(intent, energy_level):
        alternatives = get_suggested_alternatives(energy_level)

        result = {
            "gated": True,
            "alternatives": alternatives,
        }

        response = format_thanos_response(intent, result, energy_score)

        return {
            "success": False,
            "action": intent.action,
            "response": response,
            "priority_shift": False,
            "updated_focus": [],
        }

    # 4. Execute via MCP
    # Use provided client for testing, or create one for production
    client = mcp_client if mcp_client is not None else _get_mcp_client()

    # Execute task operation asynchronously
    execution_result = asyncio.run(_execute_task_operation_async(intent, client))

    # 5. Handle execution errors
    if not execution_result.get("success"):
        error_msg = execution_result.get("error", "Unknown error")
        return {
            "success": False,
            "action": intent.action,
            "response": f"Failed to {intent.action} task: {error_msg}",
            "priority_shift": False,
            "updated_focus": [],
        }

    # 6. Check for priority shift
    priority_shift = detect_priority_shift(user_input)
    updated_focus = []

    if priority_shift:
        new_priorities = extract_new_priorities(user_input)
        if new_priorities:
            update_current_focus(new_priorities)
            updated_focus = new_priorities

    # 7. Format response
    response = format_thanos_response(intent, execution_result, energy_score)

    return {
        "success": True,
        "action": intent.action,
        "response": response,
        "priority_shift": priority_shift,
        "updated_focus": updated_focus,
    }


def main():
    """CLI entry point for testing."""
    if len(sys.argv) < 2:
        print("Usage: python3 workflow.py \"user message\"", file=sys.stderr)
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    result = execute_task_operation(message)

    print(result["response"])

    if result["priority_shift"]:
        print(f"\nPriority shift detected: {result['updated_focus']}")


if __name__ == "__main__":
    main()
