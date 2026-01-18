"""
Router and Executor for Thanos orchestrator.
Handles semantic routing and tool execution with state management.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from Tools.state_store import SQLiteStateStore
    from Tools.state_store.summary_builder import SummaryBuilder
    from Tools.state_reader import StateReader


def get_tool_catalog_text() -> str:
    """Get a text description of available tools for routing prompts.
    
    Returns:
        Formatted string describing available tools.
    """
    return """Available Tools:
- daily_plan: Manage daily planning and priorities
- scoreboard: Track wins, misses, and streaks
- reminders: Set and manage reminders
- calendar: Check schedule and availability
- focus: Set current focus item
- energy: Track energy levels
- blockers: Log and manage blockers
"""


@dataclass
class RoutingResult:
    """Result of a routing decision."""
    tool_name: Optional[str] = None
    confidence: float = 0.0
    parameters: Dict[str, Any] = None
    fallback_response: Optional[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass 
class ExecutionResult:
    """Result of tool execution."""
    success: bool
    output: str
    tool_name: str
    summary: str = ""
    error: Optional[str] = None


class Router:
    """Routes user intents to appropriate tools or responses."""
    
    def __init__(
        self,
        max_output_tokens: int = 256,
        prompt_max_chars: int = 4000
    ):
        """Initialize the router.
        
        Args:
            max_output_tokens: Maximum tokens for routing response.
            prompt_max_chars: Maximum characters for routing prompt.
        """
        self.max_output_tokens = max_output_tokens
        self.prompt_max_chars = prompt_max_chars
    
    def route(
        self,
        user_message: str,
        context: Optional[str] = None
    ) -> RoutingResult:
        """Route a user message to appropriate tool or response.
        
        Args:
            user_message: The user's message to route.
            context: Optional context for routing decisions.
            
        Returns:
            RoutingResult with tool selection or fallback response.
        """
        message_lower = user_message.lower()
        
        # Simple keyword-based routing
        if any(kw in message_lower for kw in ["plan", "today", "schedule", "priority"]):
            return RoutingResult(
                tool_name="daily_plan",
                confidence=0.8,
                parameters={"action": "get"}
            )
        
        if any(kw in message_lower for kw in ["score", "wins", "streak", "progress"]):
            return RoutingResult(
                tool_name="scoreboard",
                confidence=0.8,
                parameters={"action": "get"}
            )
        
        if any(kw in message_lower for kw in ["remind", "reminder", "don't forget"]):
            return RoutingResult(
                tool_name="reminders",
                confidence=0.8,
                parameters={"action": "list"}
            )
        
        if any(kw in message_lower for kw in ["calendar", "meeting", "free", "busy"]):
            return RoutingResult(
                tool_name="calendar",
                confidence=0.8,
                parameters={"action": "today"}
            )
        
        if any(kw in message_lower for kw in ["focus", "working on", "concentrating"]):
            return RoutingResult(
                tool_name="focus",
                confidence=0.7,
                parameters={"action": "get"}
            )
        
        if any(kw in message_lower for kw in ["energy", "tired", "exhausted"]):
            return RoutingResult(
                tool_name="energy",
                confidence=0.7,
                parameters={"action": "get"}
            )
        
        if any(kw in message_lower for kw in ["blocked", "stuck", "can't"]):
            return RoutingResult(
                tool_name="blockers",
                confidence=0.7,
                parameters={"action": "list"}
            )
        
        # No clear routing - return fallback
        return RoutingResult(
            confidence=0.3,
            fallback_response="I'm not sure how to help with that. Could you be more specific?"
        )


class Executor:
    """Executes tools and manages state updates."""
    
    def __init__(
        self,
        state_store: "SQLiteStateStore",
        summary_builder: "SummaryBuilder",
        state_reader: "StateReader",
        max_output_tokens: int = 600,
        max_prompt_chars: int = 6000
    ):
        """Initialize the executor.
        
        Args:
            state_store: State storage backend.
            summary_builder: Summary builder for formatting.
            state_reader: State reader for file-based state.
            max_output_tokens: Maximum tokens for execution response.
            max_prompt_chars: Maximum characters for execution prompt.
        """
        self.state_store = state_store
        self.summary_builder = summary_builder
        self.state_reader = state_reader
        self.max_output_tokens = max_output_tokens
        self.max_prompt_chars = max_prompt_chars
    
    def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[str] = None
    ) -> ExecutionResult:
        """Execute a tool with given parameters.
        
        Args:
            tool_name: Name of the tool to execute.
            parameters: Tool parameters.
            context: Optional execution context.
            
        Returns:
            ExecutionResult with output and summary.
        """
        action = parameters.get("action", "get")
        
        try:
            if tool_name == "daily_plan":
                return self._execute_daily_plan(action, parameters)
            elif tool_name == "scoreboard":
                return self._execute_scoreboard(action, parameters)
            elif tool_name == "reminders":
                return self._execute_reminders(action, parameters)
            elif tool_name == "focus":
                return self._execute_focus(action, parameters)
            elif tool_name == "energy":
                return self._execute_energy(action, parameters)
            elif tool_name == "blockers":
                return self._execute_blockers(action, parameters)
            elif tool_name == "calendar":
                return self._execute_calendar(action, parameters)
            else:
                return ExecutionResult(
                    success=False,
                    output=f"Unknown tool: {tool_name}",
                    tool_name=tool_name,
                    error=f"Tool '{tool_name}' not found"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output=str(e),
                tool_name=tool_name,
                error=str(e)
            )
    
    def _execute_daily_plan(
        self,
        action: str,
        parameters: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute daily plan operations."""
        plan = self.state_store.get_state("daily_plan", [])
        
        if action == "get":
            if plan:
                output = "Today's plan:\n" + "\n".join(f"- {item}" for item in plan)
            else:
                output = "No items in today's plan yet."
            summary = f"Retrieved {len(plan)} plan items"
        elif action == "add":
            item = parameters.get("item", "")
            if item:
                plan.append(item)
                self.state_store.set_state("daily_plan", plan)
                output = f"Added to plan: {item}"
                summary = f"Added '{item}' to daily plan"
            else:
                output = "No item provided to add."
                summary = "Failed to add: no item provided"
        elif action == "clear":
            self.state_store.set_state("daily_plan", [])
            output = "Daily plan cleared."
            summary = "Cleared daily plan"
        else:
            output = f"Unknown action: {action}"
            summary = f"Unknown action: {action}"
        
        return ExecutionResult(
            success=True,
            output=output,
            tool_name="daily_plan",
            summary=summary
        )
    
    def _execute_scoreboard(
        self,
        action: str,
        parameters: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute scoreboard operations."""
        scoreboard = self.state_store.get_state(
            "scoreboard",
            {"wins": 0, "misses": 0, "streak": 0}
        )
        
        if action == "get":
            output = (
                f"Scoreboard:\n"
                f"- Wins: {scoreboard.get('wins', 0)}\n"
                f"- Misses: {scoreboard.get('misses', 0)}\n"
                f"- Streak: {scoreboard.get('streak', 0)} days"
            )
            summary = "Retrieved scoreboard"
        elif action == "win":
            scoreboard["wins"] = scoreboard.get("wins", 0) + 1
            scoreboard["streak"] = scoreboard.get("streak", 0) + 1
            self.state_store.set_state("scoreboard", scoreboard)
            output = f"🎉 Win recorded! Streak: {scoreboard['streak']}"
            summary = f"Recorded win, streak now {scoreboard['streak']}"
        elif action == "miss":
            scoreboard["misses"] = scoreboard.get("misses", 0) + 1
            scoreboard["streak"] = 0
            self.state_store.set_state("scoreboard", scoreboard)
            output = "Miss recorded. Streak reset."
            summary = "Recorded miss, streak reset"
        else:
            output = f"Unknown action: {action}"
            summary = f"Unknown action: {action}"
        
        return ExecutionResult(
            success=True,
            output=output,
            tool_name="scoreboard",
            summary=summary
        )
    
    def _execute_reminders(
        self,
        action: str,
        parameters: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute reminder operations."""
        reminders = self.state_store.get_state("reminders", [])
        
        if action == "list":
            if reminders:
                output = "Reminders:\n" + "\n".join(f"- {r}" for r in reminders)
            else:
                output = "No active reminders."
            summary = f"Listed {len(reminders)} reminders"
        elif action == "add":
            reminder = parameters.get("reminder", "")
            if reminder:
                reminders.append(reminder)
                self.state_store.set_state("reminders", reminders)
                output = f"Reminder added: {reminder}"
                summary = f"Added reminder: {reminder}"
            else:
                output = "No reminder text provided."
                summary = "Failed to add: no text"
        elif action == "clear":
            self.state_store.set_state("reminders", [])
            output = "All reminders cleared."
            summary = "Cleared all reminders"
        else:
            output = f"Unknown action: {action}"
            summary = f"Unknown action: {action}"
        
        return ExecutionResult(
            success=True,
            output=output,
            tool_name="reminders",
            summary=summary
        )
    
    def _execute_focus(
        self,
        action: str,
        parameters: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute focus operations."""
        focus = self.state_reader.get_current_focus()
        
        if action == "get":
            if focus:
                output = f"Current focus: {focus}"
            else:
                output = "No focus set."
            summary = "Retrieved current focus"
        else:
            output = f"Unknown action: {action}"
            summary = f"Unknown action: {action}"
        
        return ExecutionResult(
            success=True,
            output=output,
            tool_name="focus",
            summary=summary
        )
    
    def _execute_energy(
        self,
        action: str,
        parameters: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute energy operations."""
        energy = self.state_reader.get_energy_state()
        
        if action == "get":
            if energy:
                output = f"Energy level: {energy}"
            else:
                output = "Energy level not tracked."
            summary = "Retrieved energy level"
        else:
            output = f"Unknown action: {action}"
            summary = f"Unknown action: {action}"
        
        return ExecutionResult(
            success=True,
            output=output,
            tool_name="energy",
            summary=summary
        )
    
    def _execute_blockers(
        self,
        action: str,
        parameters: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute blocker operations."""
        blockers = self.state_reader.get_blockers()
        
        if action == "list":
            if blockers:
                if isinstance(blockers, list):
                    output = "Current blockers:\n" + "\n".join(f"- {b}" for b in blockers)
                else:
                    output = f"Current blockers: {blockers}"
            else:
                output = "No blockers reported."
            summary = "Retrieved blockers"
        else:
            output = f"Unknown action: {action}"
            summary = f"Unknown action: {action}"
        
        return ExecutionResult(
            success=True,
            output=output,
            tool_name="blockers",
            summary=summary
        )
    
    def _execute_calendar(
        self,
        action: str,
        parameters: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute calendar operations."""
        # Calendar integration would go here
        # For now, return a placeholder
        if action == "today":
            output = "Calendar integration not connected."
            summary = "Calendar not available"
        else:
            output = f"Unknown action: {action}"
            summary = f"Unknown action: {action}"
        
        return ExecutionResult(
            success=True,
            output=output,
            tool_name="calendar",
            summary=summary
        )
