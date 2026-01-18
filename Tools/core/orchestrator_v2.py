#!/usr/bin/env python3
"""
Thanos Orchestrator V2 - Slim coordinator using extracted services.

This is the refactored version of ThanosOrchestrator that delegates to
focused, single-responsibility services. The original orchestrator is
preserved for backward compatibility.

Usage:
    from Tools.core.orchestrator_v2 import ThanosOrchestratorV2

    orchestrator = ThanosOrchestratorV2()
    response = orchestrator.route("What should I do today?")
"""

import os
import re
import json
import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Any, TYPE_CHECKING
from datetime import datetime

# Ensure Thanos project is in path
_THANOS_DIR = Path(__file__).parent.parent.parent
if str(_THANOS_DIR) not in sys.path:
    sys.path.insert(0, str(_THANOS_DIR))

from Tools.error_logger import log_error
from Tools.spinner import command_spinner, chat_spinner, routing_spinner
from Tools.state_reader import StateReader
from Tools.state_store import SQLiteStateStore
from Tools.state_store.summary_builder import SummaryBuilder
from Tools.router_executor import Router, Executor, get_tool_catalog_text

# Import extracted services
from Tools.core.agent_service import AgentService, Agent
from Tools.core.command_service import CommandService, Command
from Tools.core.context_service import ContextService
from Tools.core.intent_service import IntentService
from Tools.core.calendar_service import CalendarService

if TYPE_CHECKING:
    from Tools.litellm_client import LiteLLMClient

_api_client_module = None


def _get_api_client_module():
    """Lazy load the LiteLLM client module."""
    global _api_client_module
    if _api_client_module is None:
        try:
            from Tools import litellm_client
            _api_client_module = litellm_client
        except ImportError:
            from Tools import claude_api_client
            _api_client_module = claude_api_client
    return _api_client_module


class ThanosOrchestratorV2:
    """
    Slim orchestrator that delegates to focused services.
    
    This is the refactored version of ThanosOrchestrator (~300 lines vs 1400+).
    It coordinates between services but doesn't implement their logic directly.
    
    Services:
        - AgentService: Agent loading and lookup
        - CommandService: Command loading and lookup  
        - ContextService: Context aggregation and prompt building
        - IntentService: Natural language intent matching
        - CalendarService: Calendar and WorkOS integration
    """

    def __init__(
        self,
        base_dir: str = None,
        api_client: "LiteLLMClient" = None,
        matcher_strategy: str = "regex",
    ):
        """Initialize the orchestrator with services.

        Args:
            base_dir: Base directory for Thanos files
            api_client: Optional pre-configured API client
            matcher_strategy: 'regex' or 'trie' for intent matching
        """
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent.parent
        self.api_client = api_client

        # Initialize infrastructure
        self.state_reader = StateReader(self.base_dir / "State")
        self.state_store = SQLiteStateStore(self.base_dir / "State" / "operator_state.db")
        self.summary_builder = SummaryBuilder(max_chars=2000)
        self.router = Router(max_output_tokens=256, prompt_max_chars=4000)
        self.executor = Executor(
            state_store=self.state_store,
            summary_builder=self.summary_builder,
            state_reader=self.state_reader,
            max_output_tokens=600,
            max_prompt_chars=6000,
        )

        # Initialize services
        self.agent_service = AgentService()
        self.command_service = CommandService()
        self.context_service = ContextService(
            base_dir=self.base_dir,
            state_reader=self.state_reader,
            state_store=self.state_store,
        )
        self.intent_service = IntentService(matcher_strategy=matcher_strategy)
        self.calendar_service = CalendarService()

        # Load data into services
        self._load_services()

    def _load_services(self) -> None:
        """Load data into all services."""
        # Load agents
        self.agent_service.load_agents(self.base_dir / "Agents")
        
        # Load commands
        self.command_service.load_commands(self.base_dir / "commands")
        
        # Load context
        self.context_service.load_context(self.base_dir / "Context")
        
        # Initialize intent service with agent triggers
        self.intent_service.initialize(
            agent_triggers=self.agent_service.get_agent_triggers(),
            agents=self.agent_service.get_all_agents(),
        )

    # =========================================================================
    # Public API (Backward Compatible)
    # =========================================================================

    @property
    def agents(self) -> Dict[str, Agent]:
        """Get all loaded agents (backward compatibility)."""
        return self.agent_service.get_all_agents()

    @property
    def commands(self) -> Dict[str, Command]:
        """Get all loaded commands (backward compatibility)."""
        return self.command_service.get_all_commands()

    @property
    def context(self) -> Dict[str, str]:
        """Get all loaded context (backward compatibility)."""
        return self.context_service.get_all_context()

    def find_agent(self, message: str) -> Optional[Agent]:
        """Find appropriate agent for a message."""
        self._ensure_client()
        return self.intent_service.find_agent(
            message=message,
            api_client=self.api_client,
        )

    def find_command(self, query: str) -> Optional[Command]:
        """Find a command by name or pattern."""
        return self.command_service.find_command(query)

    def list_agents(self) -> List[str]:
        """List all available agents."""
        return self.agent_service.list_agents()

    def list_commands(self) -> List[str]:
        """List all available commands."""
        return self.command_service.list_commands()

    def check_time_conflict(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Check if a time slot conflicts with calendar events."""
        return self.calendar_service.check_time_conflict_sync(start_time, end_time)

    # =========================================================================
    # Core Operations
    # =========================================================================

    def _ensure_client(self) -> None:
        """Ensure API client is initialized."""
        if self.api_client is None:
            api_module = _get_api_client_module()
            self.api_client = api_module.init_client(
                str(self.base_dir / "config" / "api.json")
            )

    def _build_state_summary(self) -> str:
        """Build state summary for prompts."""
        state = self._collect_state()
        summary = self.summary_builder.build_state_summary(state)
        return summary.text

    def _collect_state(self) -> Dict[str, Any]:
        """Collect current state."""
        today = {
            "focus": self.state_reader.get_current_focus(),
            "energy": self.state_reader.get_energy_state(),
            "blockers": self.state_reader.get_blockers(),
            "top3": self.state_reader.get_todays_top3(),
        }
        return {
            "today": today,
            "daily_plan": self.state_store.get_state("daily_plan", []),
            "scoreboard": self.state_store.get_state(
                "scoreboard", {"wins": 0, "misses": 0, "streak": 0}
            ),
            "reminders": self.state_store.get_state("reminders", []),
            "tool_summaries": self.state_store.get_recent_summaries(limit=5),
        }

    def _update_plan_and_scoreboard(self, user_message: str) -> None:
        """Update plan and scoreboard based on message."""
        daily_plan = self.state_store.get_state("daily_plan", [])
        scoreboard = self.state_store.get_state(
            "scoreboard", {"wins": 0, "misses": 0, "streak": 0}
        )
        msg = user_message.lower().strip()

        if msg.startswith("plan ") or "next action" in msg:
            item = user_message.split(" ", 1)[1] if " " in user_message else user_message
            daily_plan.append(item.strip())
            daily_plan = daily_plan[-10:]

        if "done" in msg or "completed" in msg:
            scoreboard["wins"] = int(scoreboard.get("wins", 0)) + 1
            scoreboard["streak"] = int(scoreboard.get("streak", 0)) + 1

        if "missed" in msg or "did not" in msg:
            scoreboard["misses"] = int(scoreboard.get("misses", 0)) + 1
            scoreboard["streak"] = 0

        self.state_store.set_state("daily_plan", daily_plan)
        self.state_store.set_state("scoreboard", scoreboard)

    def _record_turn_log(
        self,
        model: str,
        usage_entry: Optional[Dict[str, Any]],
        latency_ms: float,
        tool_call_count: int,
        prompt_bytes: int,
        response_bytes: int,
    ) -> None:
        """Record turn metrics."""
        input_tokens = int(usage_entry.get("input_tokens", 0)) if usage_entry else 0
        output_tokens = int(usage_entry.get("output_tokens", 0)) if usage_entry else 0
        cost_usd = float(usage_entry.get("cost_usd", 0.0)) if usage_entry else 0.0

        self.state_store.record_turn_log(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            tool_call_count=tool_call_count,
            state_size=self.state_store.get_state_size(),
            prompt_bytes=prompt_bytes,
            response_bytes=response_bytes,
        )

    # =========================================================================
    # Command and Chat Operations
    # =========================================================================

    def run_command(
        self, command_name: str, args: str = "", stream: bool = False
    ) -> str:
        """Execute a command and return the response."""
        self._ensure_client()

        command = self.find_command(command_name)
        if not command:
            return f"Command not found: {command_name}"

        system_prompt = self.context_service.build_system_prompt(command=command)
        user_prompt = f"Execute the {command.name} command."
        if args:
            user_prompt += f"\nArguments: {args}"
        user_prompt += "\n\nFollow the workflow exactly and provide the output in the specified format."

        if stream:
            return self._stream_response(
                user_prompt, system_prompt, f"command:{command_name}"
            )
        else:
            with command_spinner(command_name):
                return self.api_client.chat(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    operation=f"command:{command_name}",
                    agent="ops",  # Commands function as Ops operations (fast/cheap)
                )

    def chat(
        self,
        message: str,
        agent: Optional[str] = None,
        stream: bool = False,
        model: Optional[str] = None,
    ) -> str:
        """Chat with a specific agent or auto-detect."""
        if agent is None and model is None and not stream:
            return self.route(message, stream=False)

        self._ensure_client()

        agent_obj = None
        if agent:
            agent_obj = self.agent_service.get_agent(agent.lower())
        else:
            agent_obj = self.find_agent(message)

        system_prompt = self.context_service.build_system_prompt(agent=agent_obj)
        agent_name = agent_obj.name if agent_obj else "default"

        try:
            if stream:
                return self._stream_response(
                    message, system_prompt, f"chat:{agent_name}", model, agent=agent_name
                )
            else:
                with chat_spinner(agent_name):
                    return self.api_client.chat(
                        prompt=message,
                        model=model,
                        system_prompt=system_prompt,
                        operation=f"chat:{agent_name}",
                        agent=agent_name,
                    )
        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            if "api key" in str(e).lower():
                error_msg += "\n\nHint: Check that ANTHROPIC_API_KEY is set in your .env file"
            print(f"\n{error_msg}\n")
            return ""

    def route(
        self, message: str, stream: bool = False, model: Optional[str] = None
    ) -> str:
        """Route a message through the Operator router and executor."""
        self._update_plan_and_scoreboard(message)
        state_summary = self._build_state_summary()
        tool_catalog = get_tool_catalog_text()

        # Check for explicit command pattern
        cmd_match = re.match(r"^/?(\w+:\w+)\s*(.*)?$", message)
        if cmd_match:
            action = self.router._parse_action(
                json.dumps({
                    "respond": "",
                    "tool_calls": [{
                        "name": "command.run",
                        "arguments": {
                            "command": cmd_match.group(1),
                            "args": cmd_match.group(2) or "",
                        },
                    }],
                    "escalate": False,
                    "escalate_reason": "",
                    "escalate_task": "",
                })
            )
            exec_result = self.executor.execute(
                message, action, state_summary, model_override=model
            )
            self._record_turn_log(
                model=exec_result.model,
                usage_entry=exec_result.usage_entry,
                latency_ms=exec_result.latency_ms,
                tool_call_count=exec_result.tool_call_count,
                prompt_bytes=exec_result.prompt_bytes,
                response_bytes=exec_result.response_bytes,
            )
            return exec_result.text

        # Route through LLM
        router_result = self.router.route(message, state_summary, tool_catalog)
        self._record_turn_log(
            model=router_result.model,
            usage_entry=router_result.usage_entry,
            latency_ms=router_result.latency_ms,
            tool_call_count=len(router_result.action.tool_calls),
            prompt_bytes=router_result.prompt_bytes,
            response_bytes=router_result.response_bytes,
        )

        if (
            router_result.action.respond
            and not router_result.action.tool_calls
            and not router_result.action.escalate
        ):
            return router_result.action.respond

        exec_result = self.executor.execute(
            message, router_result.action, state_summary, model_override=model
        )
        self._record_turn_log(
            model=exec_result.model,
            usage_entry=exec_result.usage_entry,
            latency_ms=exec_result.latency_ms,
            tool_call_count=exec_result.tool_call_count,
            prompt_bytes=exec_result.prompt_bytes,
            response_bytes=exec_result.response_bytes,
        )
        return exec_result.text

    def _stream_response(
        self,
        prompt: str,
        system_prompt: str,
        operation: str,
        model: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> str:
        """Stream a response with spinner."""
        result = ""
        spinner = chat_spinner(operation.split(":")[1] if ":" in operation else operation)
        spinner.start()

        try:
            first_chunk = True
            for chunk in self.api_client.chat_stream(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                operation=operation,
                agent=agent,
            ):
                if first_chunk:
                    spinner.stop()
                    first_chunk = False
                print(chunk, end="", flush=True)
                result += chunk
            print()
            return result
        except Exception:
            spinner.fail()
            raise

    def refresh_daily_state(self) -> None:
        """Force refresh of daily state (Calendar, WorkOS) into state_store."""
        # Refresh WorkOS
        try:
            context = self.calendar_service.get_workos_context_sync(force_refresh=True)
            if context:
                self.state_store.set_state("workos_summary", json.dumps(context, indent=2))
        except Exception as e:
            log_error("orchestrator_v2", e, "Failed to refresh WorkOS state")

        # Refresh Calendar
        try:
            context = self.calendar_service.get_calendar_context_sync(force_refresh=True)
            if context and context.get("summary"):
                self.state_store.set_state("calendar_summary", context["summary"])
        except Exception as e:
            log_error("orchestrator_v2", e, "Failed to refresh Calendar state")

    def get_usage(self, days: int = 30) -> Dict[str, Any]:
        """Get API usage summary."""
        self._ensure_client()
        if hasattr(self.api_client, "get_usage_summary"):
            return self.api_client.get_usage_summary(days)
        return {
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "total_calls": 0,
            "projected_monthly_cost": 0.0
        }
