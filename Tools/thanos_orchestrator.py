#!/usr/bin/env python3
"""
Thanos Orchestrator - Routes requests to appropriate agents and commands.
Replaces Claude Code's built-in skill system with direct API integration.

Usage:
    from Tools.thanos_orchestrator import thanos

    # Run a command
    response = thanos.run_command("pa:daily")

    # Chat with an agent
    response = thanos.chat("I'm overwhelmed", agent="ops")

    # Auto-route based on content
    response = thanos.route("What should I do today?")
"""

import os
import re
import json
import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Any, TYPE_CHECKING, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Ensure Thanos project is in path for imports BEFORE importing from Tools
_THANOS_DIR = Path(__file__).parent.parent
if str(_THANOS_DIR) not in sys.path:
    sys.path.insert(0, str(_THANOS_DIR))

from Tools.error_logger import log_error
from Tools.intent_matcher import KeywordMatcher, TrieKeywordMatcher
from Tools.spinner import command_spinner, chat_spinner, routing_spinner
from Tools.state_reader import StateReader
from Tools.state_store import SQLiteStateStore
from Tools.state_store.summary_builder import SummaryBuilder
from Tools.router_executor import Router, Executor, get_tool_catalog_text
from Tools.model_escalator_v2 import model_escalation_hook_v2 as model_escalation_hook, EscalationResult

# Lazy import for API client - only needed for chat/run, not hooks
if TYPE_CHECKING:
    from Tools.litellm_client import LiteLLMClient

_api_client_module = None

def _get_api_client_module():
    """Lazy load the LiteLLM client module (with fallback to direct Anthropic)."""
    global _api_client_module
    if _api_client_module is None:
        try:
            from Tools import litellm_client
            _api_client_module = litellm_client
        except ImportError:
            # Fallback to direct Anthropic client if LiteLLM unavailable
            from Tools import claude_api_client
            _api_client_module = claude_api_client
    return _api_client_module


@dataclass
class Agent:
    """Represents a Thanos agent with personality and triggers."""
    name: str
    role: str
    voice: str
    triggers: List[str]
    content: str
    file_path: str

    @classmethod
    def from_markdown(cls, file_path: Path) -> 'Agent':
        """Parse an agent definition from markdown file."""
        content = file_path.read_text(encoding='utf-8')

        # Extract frontmatter
        frontmatter = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        # Parse list values
                        if value.startswith('['):
                            value = json.loads(value.replace("'", '"'))
                        frontmatter[key] = value
                content = parts[2]

        return cls(
            name=frontmatter.get('name', file_path.stem),
            role=frontmatter.get('role', 'Assistant'),
            voice=frontmatter.get('voice', 'helpful'),
            triggers=frontmatter.get('triggers', []),
            content=content.strip(),
            file_path=str(file_path)
        )


@dataclass
class Command:
    """Represents a Thanos command/skill."""
    name: str
    description: str
    parameters: List[str]
    workflow: str
    content: str
    file_path: str

    @classmethod
    def from_markdown(cls, file_path: Path) -> 'Command':
        """Parse a command definition from markdown file."""
        content = file_path.read_text(encoding='utf-8')

        # Extract command name from first heading
        name_match = re.search(r'^#\s+(/\w+:\w+)', content, re.MULTILINE)
        name = name_match.group(1) if name_match else file_path.stem

        # Extract description (first paragraph after heading)
        desc_match = re.search(r'^#[^\n]+\n+([^\n#]+)', content, re.MULTILINE)
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract parameters section
        params = []
        params_match = re.search(r'## Parameters\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if params_match:
            for line in params_match.group(1).split('\n'):
                if line.strip().startswith('-'):
                    params.append(line.strip()[1:].strip())

        # Extract workflow section
        workflow_match = re.search(r'## Workflow\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        workflow = workflow_match.group(1).strip() if workflow_match else ""

        return cls(
            name=name,
            description=description,
            parameters=params,
            workflow=workflow,
            content=content,
            file_path=str(file_path)
        )


class ThanosOrchestrator:
    """Main orchestrator for Thanos personal assistant."""

    def __init__(self, base_dir: str = None, api_client: "LiteLLMClient" = None,
                 matcher_strategy: str = 'regex'):
        """Initialize the Thanos orchestrator.

        Args:
            base_dir: Base directory for Thanos files (defaults to project root)
            api_client: Optional LiteLLM client instance
            matcher_strategy: Strategy for keyword matching ('regex' or 'trie').
                            - 'regex': Uses regex-based KeywordMatcher (default, no dependencies)
                            - 'trie': Uses Aho-Corasick TrieKeywordMatcher (requires pyahocorasick,
                                     falls back to regex if not available)
        """
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.api_client = api_client
        self.matcher_strategy = matcher_strategy
        
        # Initialize StateReader
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

        # Load components
        self.agents: Dict[str, Agent] = {}
        self.commands: Dict[str, Command] = {}
        self.context: Dict[str, str] = {}

        self._load_agents()
        self._load_commands()
        self._load_context()

        # Initialize intent matcher with pre-compiled patterns (lazy initialization)
        self._intent_matcher: Optional[Union[KeywordMatcher, TrieKeywordMatcher]] = None

        # Lazy initialization for calendar adapter
        self._calendar_adapter = None
        self._calendar_context_cache: Optional[Dict[str, Any]] = None
        self._calendar_cache_time: Optional[datetime] = None

        # Lazy initialization for WorkOS gateway (MCP-first)
        self._workos_gateway = None
        self._workos_context_cache: Optional[Dict[str, Any]] = None
        self._workos_cache_time: Optional[datetime] = None

    def _load_agents(self):
        """Load all agent definitions."""
        agents_dir = self.base_dir / "Agents"
        if agents_dir.exists():
            for file in agents_dir.glob("*.md"):
                if file.name != "AgentFactory.md":
                    try:
                        agent = Agent.from_markdown(file)
                        self.agents[agent.name.lower()] = agent
                    except Exception as e:
                        print(f"Warning: Failed to load agent {file}: {e}")

    def _load_commands(self):
        """Load all command definitions."""
        commands_dir = self.base_dir / "commands"
        if commands_dir.exists():
            for subdir in commands_dir.iterdir():
                if subdir.is_dir():
                    for file in subdir.glob("*.md"):
                        if file.name != "README.md":
                            try:
                                cmd = Command.from_markdown(file)
                                # Store by multiple keys
                                self.commands[cmd.name] = cmd
                                self.commands[file.stem] = cmd
                                # Also store as prefix:name
                                prefix = subdir.name
                                self.commands[f"{prefix}:{file.stem}"] = cmd
                            except Exception as e:
                                print(f"Warning: Failed to load command {file}: {e}")

    def _load_context(self):
        """Load context files."""
        context_dir = self.base_dir / "Context"
        if context_dir.exists():
            for file in context_dir.glob("*.md"):
                try:
                    self.context[file.stem] = file.read_text(encoding='utf-8')
                except Exception as e:
                    print(f"Warning: Failed to load context {file}: {e}")

    def _collect_state(self) -> Dict[str, Any]:
        today = {
            "focus": self.state_reader.get_current_focus(),
            "energy": self.state_reader.get_energy_state(),
            "blockers": self.state_reader.get_blockers(),
            "top3": self.state_reader.get_todays_top3(),
        }
        daily_plan = self.state_store.get_state("daily_plan", [])
        scoreboard = self.state_store.get_state("scoreboard", {"wins": 0, "misses": 0, "streak": 0})
        reminders = self.state_store.get_state("reminders", [])
        tool_summaries = self.state_store.get_recent_summaries(limit=5)
        return {
            "today": today,
            "daily_plan": daily_plan,
            "scoreboard": scoreboard,
            "reminders": reminders,
            "tool_summaries": tool_summaries,
        }

    def _build_state_summary(self) -> str:
        state = self._collect_state()
        summary = self.summary_builder.build_state_summary(state)
        return summary.text

    def _update_plan_and_scoreboard(self, user_message: str) -> None:
        daily_plan = self.state_store.get_state("daily_plan", [])
        scoreboard = self.state_store.get_state("scoreboard", {"wins": 0, "misses": 0, "streak": 0})
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
        input_tokens = int(usage_entry.get("input_tokens", 0)) if usage_entry else 0
        output_tokens = int(usage_entry.get("output_tokens", 0)) if usage_entry else 0
        cost_usd = float(usage_entry.get("cost_usd", 0.0)) if usage_entry else 0.0
        state_size = self.state_store.get_state_size()
        self.state_store.record_turn_log(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            tool_call_count=tool_call_count,
            state_size=state_size,
            prompt_bytes=prompt_bytes,
            response_bytes=response_bytes,
        )

    def _get_workos_gateway(self):
        """Lazy load the WorkOS gateway."""
        if self._workos_gateway is None:
            try:
                from Tools.core.workos_gateway import WorkOSGateway
                self._workos_gateway = WorkOSGateway()
            except Exception as e:
                log_error("thanos_orchestrator", e, "Failed to initialize WorkOS gateway")
                return None
        return self._workos_gateway

    async def _fetch_workos_context_async(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch WorkOS context asynchronously with caching."""
        if not force_refresh and self._workos_context_cache is not None:
            if self._workos_cache_time and (datetime.now() - self._workos_cache_time).seconds < 300:
                return self._workos_context_cache

        gateway = self._get_workos_gateway()
        if gateway is None:
            return None

        try:
            context = await gateway.get_daily_summary(force_refresh=force_refresh)
            if context is None:
                return None
            self._workos_context_cache = context
            self._workos_cache_time = datetime.now()
            return context
        except Exception as e:
            log_error("thanos_orchestrator", e, "Failed to fetch WorkOS context")
            return None

    def _get_workos_context(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for fetching WorkOS context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return self._workos_context_cache
            else:
                return asyncio.run(self._fetch_workos_context_async(force_refresh))
        except RuntimeError:
            return asyncio.run(self._fetch_workos_context_async(force_refresh))
        except Exception as e:
            log_error("thanos_orchestrator", e, "Failed to get WorkOS context")
            return None

    def _get_calendar_adapter(self):
        """Lazy load the calendar adapter."""
        if self._calendar_adapter is None:
            try:
                from Tools.adapters import GoogleCalendarAdapter, GOOGLE_CALENDAR_AVAILABLE

                if not GOOGLE_CALENDAR_AVAILABLE:
                    return None

                self._calendar_adapter = GoogleCalendarAdapter()

                # Check if authenticated
                if not self._calendar_adapter.is_authenticated():
                    return None

            except Exception as e:
                log_error("thanos_orchestrator", e, "Failed to initialize calendar adapter")
                return None

        return self._calendar_adapter

    async def _fetch_calendar_context_async(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch calendar context asynchronously with caching.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary with calendar context including:
            - events: List of today's events
            - summary: Human-readable calendar summary
            - next_event: Details of next upcoming event
            - free_until: Next busy period
        """
        # Check cache (5 minute TTL)
        if not force_refresh and self._calendar_context_cache is not None:
            if self._calendar_cache_time and (datetime.now() - self._calendar_cache_time).seconds < 300:
                return self._calendar_context_cache

        adapter = self._get_calendar_adapter()
        if adapter is None:
            return None

        try:
            # Fetch today's events
            result = await adapter.call_tool("get_today_events", {})

            if not result.success:
                return None

            events = result.data.get("events", [])

            # Generate summary
            summary_result = await adapter.call_tool("generate_calendar_summary", {
                "date": datetime.now().strftime("%Y-%m-%d")
            })

            summary = summary_result.data.get("summary", "") if summary_result.success else ""

            # Find next event
            now = datetime.now()
            next_event = None
            for event in events:
                event_start_str = event.get("start", {}).get("dateTime")
                if event_start_str:
                    try:
                        event_start = datetime.fromisoformat(event_start_str.replace("Z", "+00:00"))
                        # Convert to naive datetime for comparison if it's aware
                        if event_start.tzinfo is not None:
                            event_start = event_start.replace(tzinfo=None)
                        if event_start > now:
                            next_event = event
                            break
                    except (ValueError, AttributeError):
                        continue

            # Calculate free until
            free_until = None
            if next_event:
                event_start_str = next_event.get("start", {}).get("dateTime")
                if event_start_str:
                    try:
                        free_until = datetime.fromisoformat(event_start_str.replace("Z", "+00:00"))
                        if free_until.tzinfo is not None:
                            free_until = free_until.replace(tzinfo=None)
                    except (ValueError, AttributeError):
                        pass

            context = {
                "events": events,
                "summary": summary,
                "next_event": next_event,
                "free_until": free_until,
                "event_count": len(events)
            }

            # Cache result
            self._calendar_context_cache = context
            self._calendar_cache_time = datetime.now()

            return context

        except Exception as e:
            log_error("thanos_orchestrator", e, "Failed to fetch calendar context")
            return None

    def _get_calendar_context(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for fetching calendar context.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary with calendar context or None if unavailable
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we can't use asyncio.run()
                # Return cached data or None
                return self._calendar_context_cache
            else:
                return asyncio.run(self._fetch_calendar_context_async(force_refresh))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._fetch_calendar_context_async(force_refresh))
        except Exception as e:
            log_error("thanos_orchestrator", e, "Failed to get calendar context")
            return None

    async def _check_time_conflict_async(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Check if a time slot conflicts with calendar events.

        Args:
            start_time: Proposed start time
            end_time: Proposed end time

        Returns:
            Dictionary with:
            - has_conflict: Boolean
            - conflicts: List of conflicting events
            - message: Human-readable conflict description
        """
        adapter = self._get_calendar_adapter()
        if adapter is None:
            return {
                "has_conflict": False,
                "conflicts": [],
                "message": "Calendar not available"
            }

        try:
            result = await adapter.call_tool("check_conflicts", {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            })

            if not result.success:
                return {
                    "has_conflict": False,
                    "conflicts": [],
                    "message": "Unable to check conflicts"
                }

            return result.data

        except Exception as e:
            log_error("thanos_orchestrator", e, "Failed to check time conflict")
            return {
                "has_conflict": False,
                "conflicts": [],
                "message": f"Error checking conflicts: {str(e)}"
            }

    def check_time_conflict(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Synchronous wrapper for checking time conflicts.

        Args:
            start_time: Proposed start time
            end_time: Proposed end time

        Returns:
            Dictionary with conflict information
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Return a simple check based on cached context
                context = self._calendar_context_cache
                if context is None:
                    return {
                        "has_conflict": False,
                        "conflicts": [],
                        "message": "Calendar not available"
                    }

                conflicts = []
                for event in context.get("events", []):
                    event_start_str = event.get("start", {}).get("dateTime")
                    event_end_str = event.get("end", {}).get("dateTime")
                    if event_start_str and event_end_str:
                        try:
                            event_start = datetime.fromisoformat(event_start_str.replace("Z", "+00:00"))
                            event_end = datetime.fromisoformat(event_end_str.replace("Z", "+00:00"))
                            # Convert to naive if aware
                            if event_start.tzinfo is not None:
                                event_start = event_start.replace(tzinfo=None)
                            if event_end.tzinfo is not None:
                                event_end = event_end.replace(tzinfo=None)

                            # Check overlap
                            if start_time < event_end and end_time > event_start:
                                conflicts.append(event)
                        except (ValueError, AttributeError):
                            continue

                return {
                    "has_conflict": len(conflicts) > 0,
                    "conflicts": conflicts,
                    "message": f"Found {len(conflicts)} conflict(s)" if conflicts else "No conflicts"
                }
            else:
                return asyncio.run(self._check_time_conflict_async(start_time, end_time))
        except RuntimeError:
            return asyncio.run(self._check_time_conflict_async(start_time, end_time))
        except Exception as e:
            log_error("thanos_orchestrator", e, "Failed to check time conflict")
            return {
                "has_conflict": False,
                "conflicts": [],
                "message": f"Error: {str(e)}"
            }

    def _get_intent_matcher(self) -> Union[KeywordMatcher, TrieKeywordMatcher]:
        """Get or create the cached intent matcher with pre-compiled patterns.

        For complete documentation of the keyword structure, scoring weights,
        and all 92 keywords organized by agent and priority, see:
        📚 docs/agent-routing.md

        PERFORMANCE OPTIMIZATION:
        ------------------------
        The original implementation used nested loops in find_agent():
            for agent_type in ['ops', 'coach', 'strategy', 'health']:
                for priority in ['high', 'medium', 'low']:
                    for keyword in keywords[agent_type][priority]:
                        if keyword in message.lower():
                            score += weight

        This resulted in:
        - O(n*m) complexity: n=92 keywords, m=message length
        - 92+ substring searches per message
        - Inefficient for every routing decision
        - ~120μs average per message

        OPTIMIZATION STRATEGY:
        ---------------------
        1. Pre-compile all keywords into optimized patterns (one-time cost)
        2. Cache the compiled matcher for the orchestrator's lifetime
        3. Use lazy initialization (only compile when first needed)
        4. Achieve O(m) complexity per message (single pass)
        5. Measured performance: ~12μs average (10x speedup)

        LAZY INITIALIZATION BENEFITS:
        ----------------------------
        - No compilation cost if orchestrator used only for commands
        - Compilation happens once on first routing decision
        - Cached for all subsequent calls
        - Amortized cost: negligible after first use

        MATCHER STRATEGY:
        ----------------
        The matcher strategy is determined by the matcher_strategy parameter:
        - 'regex': Uses KeywordMatcher with pre-compiled regex patterns (default)
          * Best for current scale (~92 keywords)
          * No external dependencies
          * ~12μs average performance

        - 'trie': Uses TrieKeywordMatcher with Aho-Corasick automaton
          * Optimal for 500+ keywords
          * Falls back to regex if pyahocorasick not available
          * ~1.2-2x faster at current scale
          * Better scalability for future growth

        Returns:
            KeywordMatcher or TrieKeywordMatcher instance with compiled patterns
        """
        if self._intent_matcher is None:
            # KEYWORD STRUCTURE:
            # ----------------
            # Keywords are organized by agent and priority tier.
            # Total: 92 keywords across 4 agents (ops=26, coach=24, strategy=20, health=22)
            #
            # Priority tiers determine scoring weights:
            # - high: weight=5 (strong signals for agent selection)
            # - medium: weight=2 (moderate signals)
            # - low: weight=1 (weak signals)
            #
            # Triggers (from agent definitions): weight=10 (immediate routing)
            #
            # DESIGN NOTES:
            # - Keywords can be multi-word phrases (e.g., "what should i do")
            # - Case-insensitive matching (all normalized to lowercase)
            # - Substring matching (e.g., "task" matches in "tasks" or "multitask")
            # - Keywords sorted by length (longer phrases matched first)
            agent_keywords = {
                'ops': {
                    'high': ['what should i do', 'whats on my plate', 'help me plan', 'overwhelmed',
                             'what did i commit', 'process inbox', 'clear my inbox', 'prioritize',
                             'show my calendar', 'when am i free', 'schedule this task', 'what should i focus on',
                             'next action', 'next step'],
                    'medium': ['task', 'tasks', 'todo', 'to-do', 'schedule', 'plan', 'organize',
                               'today', 'tomorrow', 'this week', 'deadline', 'due',
                               'calendar', 'meeting', 'meetings', 'appointment', 'appointments',
                               'event', 'events', 'free time', 'availability', 'book', 'block time',
                               'email', 'inbox'],
                    'low': ['busy', 'work', 'productive', 'efficiency']
                },
                'coach': {
                    'high': ['i keep doing this', "why can't i", "im struggling", "i'm struggling", "why cant i", 'pattern',
                             'be honest', 'accountability', 'avoiding', 'procrastinating', "stick to my goals",
                             'hold me accountable', 'analyze my behavior', 'self-sabotaging', 'pep talk'],
                    'medium': ['habit', 'habits', 'stuck', 'motivation', 'discipline', 'consistent',
                               'consistency', 'excuse', 'excuses', 'failing', 'trying', 'again',
                               'distracted', 'distraction', 'focus', 'analyze'],
                    'low': ['feel', 'feeling', 'hard', 'difficult', 'trying']
                },
                'strategy': {
                    'high': ['quarterly', 'long-term', 'strategy', 'goals', 'where am i headed',
                             'big picture', 'priorities', 'direction', 'is it worth', 'best approach',
                             'right track', 'vision', 'mission', 'tradeoff', 'tradeoffs'],
                    'medium': ['should i take this client', 'revenue', 'growth', 'future',
                               'planning', 'decision', 'invest', 'worth it',
                               'years', 'year plan'],
                    'low': ['career', 'business', 'opportunity', 'risk']
                },
                'health': {
                    'high': ["im tired", "i'm tired", 'should i take my vyvanse', "i cant focus", "i'm not sleeping well", "i can't focus", 'supplements',
                             'i crashed', 'energy', 'sleep', 'medication', 'crashed', 'drained', 'focus', 'maintain focus',
                             'brain fog', 'burnt out', 'burnout', 'meds', 'vyvanse'],
                    'medium': ['exhausted', 'exhaustion', 'fatigue', 'fatigued', 'concentration', 'adhd',
                               'stimulant', 'caffeine', 'workout', 'workouts', 'exercise', 'exercising', 'tired',
                               'concentrate'],
                    'low': ['rest', 'break', 'recovery']
                }
            }

            # Build triggers from agent definitions
            # Triggers are stored in agent markdown files and have highest weight (10)
            agent_triggers = {}
            for agent in self.agents.values():
                if agent.triggers:
                    agent_triggers[agent.name.lower()] = agent.triggers

            # MATCHER CREATION:
            # ----------------
            # Create and cache the matcher based on strategy.
            # This is the one-time O(n) compilation cost that enables O(m) matching.
            if self.matcher_strategy == 'trie':
                # Use Aho-Corasick trie-based matcher (optimal for 500+ keywords)
                # Falls back to regex if pyahocorasick not available
                self._intent_matcher = TrieKeywordMatcher(agent_keywords, agent_triggers)
            else:
                # Default to regex matcher (optimal for current scale, no dependencies)
                # This is the recommended strategy for ~92 keywords
                self._intent_matcher = KeywordMatcher(agent_keywords, agent_triggers)

        return self._intent_matcher

    def _build_time_context(self) -> str:
        """Build temporal context string."""
        now = datetime.now()
        parts = [f"## Temporal Context\nCurrent time: {now.strftime('%Y-%m-%d %H:%M')}"]
        
        # Get elapsed time since last interaction
        elapsed = self.state_reader.calculate_elapsed_time()
        readable_elapsed = self.state_reader.format_elapsed_time(elapsed)
        
        parts.append(f"Last interaction: {readable_elapsed}")
        
        return "\n".join(parts)

    def _build_system_prompt(self, agent: Optional[Agent] = None,
                             command: Optional[Command] = None,
                             include_context: bool = True) -> str:
        """Build system prompt for API call."""
        parts = []

        # Base identity
        parts.append("""You are The Operator.
You are stoic and direct.
You enforce accountability.
You turn vague goals into next actions.
You maintain a compact daily plan and a scoreboard.
""")

        # Add temporal context
        if include_context:
            parts.append(self._build_time_context())

        # Add core context
        if include_context and "CORE" in self.context:
            parts.append("\n## About Jeremy\n" + self.context["CORE"])

        # Add agent personality
        if agent:
            parts.append(f"\n## Current Role: {agent.role}")
            parts.append(f"Voice: {agent.voice}")
            parts.append(f"\n{agent.content}")

        # Add command context
        if command:
            parts.append(f"\n## Current Command: {command.name}")
            parts.append(f"{command.description}")
            parts.append(f"\n### Workflow\n{command.workflow}")

        # Add current state
        state_file = self.base_dir / "State" / "Today.md"
        if state_file.exists():
            try:
                today_state = state_file.read_text()
                parts.append(f"\n## Today's State\n{today_state[:2000]}")  # Limit size
            except (OSError, IOError) as e:
                # File read errors are not critical for system prompt
                log_error("thanos_orchestrator", e, "Failed to read Today.md for system prompt")
            except Exception as e:
                # Unexpected errors should be logged
                log_error("thanos_orchestrator", e, "Unexpected error reading Today.md")

        # Add stored summaries
        if include_context:
            workos_summary = self.state_store.get_state("workos_summary")
            if workos_summary:
                parts.append("\n## WorkOS Summary")
                parts.append(workos_summary)

            calendar_summary = self.state_store.get_state("calendar_summary")
            if calendar_summary:
                parts.append("\n## Calendar Summary")
                parts.append(calendar_summary)

            recent_tool_summaries = self.state_store.get_recent_summaries(limit=3)
            if recent_tool_summaries:
                parts.append("\n## Recent Tool Summaries")
                for entry in recent_tool_summaries:
                    parts.append(f"{entry.get('tool_name')} id {entry.get('summary_id')} {entry.get('summary_text')}")

            # Inject hot memories from Memory V2 (semantic context)
            memory_context = self._get_memory_context_for_prompt()
            if memory_context:
                parts.append("\n## Memory Context (Top of Mind)")
                parts.append(memory_context)

        prompt = "\n\n".join(parts)
        if len(prompt) > 6000:
            prompt = prompt[:6000]
        return prompt

    def _get_memory_context_for_prompt(self, limit: int = 3) -> Optional[str]:
        """Fetch hot memories for automatic context injection.

        This replaces the deprecated ThanosInteractive's _get_memory_context
        by providing passive retrieval during prompt building.

        Args:
            limit: Maximum memories to include (default 3 to save tokens)

        Returns:
            Formatted string of hot memories or None if unavailable
        """
        try:
            from Tools.memory_v2.service import get_memory_service

            ms = get_memory_service()
            hot_memories = ms.whats_hot(limit=limit)

            if not hot_memories:
                return None

            lines = []
            for mem in hot_memories:
                content = mem.get("memory", mem.get("content", ""))[:100]
                heat = mem.get("heat", 0)
                heat_icon = "🔥" if heat > 0.6 else "•"
                lines.append(f"{heat_icon} {content}...")

            return "\n".join(lines) if lines else None

        except Exception:
            # Memory service unavailable - fail silently
            return None

    def _ensure_client(self):
        """Ensure API client is initialized."""
        if self.api_client is None:
            api_module = _get_api_client_module()
            self.api_client = api_module.init_client(str(self.base_dir / "config" / "api.json"))

    def find_agent(self, message: str) -> Optional[Agent]:
        """
        Find appropriate agent for a message using hybrid routing:
        1. Fast Keyword Matcher (Zero latency, deterministic)
        2. Semantic LLM Fallback (Higher accuracy for complex queries)
        """
        matcher = self._get_intent_matcher()
        agent_scores = matcher.match(message)

        best_agent = max(agent_scores.items(), key=lambda x: x[1]) if agent_scores else (None, 0)

        # Thresholds
        HIGH_CONFIDENCE_THRESHOLD = 5

        # 1. Fast Path: High confidence keyword match
        if best_agent[1] >= HIGH_CONFIDENCE_THRESHOLD:
            return self.agents.get(best_agent[0])

        # 2. Semantic Fallback: Use LLM routing for ambiguous queries
        self._ensure_client()
        if self.api_client and hasattr(self.api_client, 'route'):
            candidates = ['ops', 'coach', 'strategy', 'health']
            
            system_prompt = (
                "You are the central router for the Thanos Personal Assistant. "
                "Route the user's query to the most appropriate agent:\n"
                "- ops: Tactical execution, calendar, todos, inbox, immediate planning.\n"
                "- coach: Motivation, habits, accountability, behavioral patterns, focus.\n"
                "- strategy: Long-term vision, business decisions, quarterly goals, trade-offs, big picture.\n"
                "- health: Energy, sleep, medication, supplements, physiology, burnout, physical state.\n\n"
                "Return ONLY the agent name (ops, coach, strategy, health)."
            )
            
            try:
                routed_agent_name = self.api_client.route(
                    query=message,
                    candidates=candidates,
                    classification_prompt=system_prompt
                )
                if routed_agent_name and routed_agent_name in self.agents:
                    return self.agents.get(routed_agent_name)
            except Exception as e:
                # Log error but fall back to heuristic
                print(f"Routing error: {e}")

        # 3. Last Resort: Heuristic Fallback (legacy logic)
        if best_agent[1] > 0:
            return self.agents.get(best_agent[0])

        message_lower = message.lower()
        if any(word in message_lower for word in ['what should', 'help me', 'need to', 'have to']):
            return self.agents.get('ops')
        if any(word in message_lower for word in ['should i', 'is it worth', 'best approach']):
            return self.agents.get('strategy')

        return self.agents.get('ops') # Default fallback

        if best_agent[1] > 0:
            # Found a keyword match - return the agent
            return self.agents.get(best_agent[0])

        # FALLBACK: No keyword matches found
        # Use question type heuristics for common patterns
        message_lower = message.lower()

        # Tactical/operational questions → Ops agent
        if any(word in message_lower for word in ['what should', 'help me', 'need to', 'have to']):
            return self.agents.get('ops')

        # Strategic/decision questions → Strategy agent
        if any(word in message_lower for word in ['should i', 'is it worth', 'best approach']):
            return self.agents.get('strategy')

        # Final fallback: Ops is the default tactical agent
        # This handles general queries that don't match any specific pattern
        return self.agents.get('ops')

    def find_command(self, query: str) -> Optional[Command]:
        """Find a command by name or pattern."""
        # Direct lookup
        if query in self.commands:
            return self.commands[query]

        # Try with common prefixes
        for prefix in ['pa', 'sc']:
            key = f"{prefix}:{query}"
            if key in self.commands:
                return self.commands[key]

        # Fuzzy match
        query_lower = query.lower()
        for name, cmd in self.commands.items():
            if query_lower in name.lower():
                return cmd

        return None

    def run_command(self, command_name: str, args: str = "",
                    stream: bool = False) -> str:
        """Execute a command and return the response."""
        self._ensure_client()

        # Special handling for pa:daily - run the script directly for compact output
        if command_name == "pa:daily":
            return self._run_daily_brief_direct(args, stream)

        command = self.find_command(command_name)
        if not command:
            return f"Command not found: {command_name}"

        system_prompt = self._build_system_prompt(command=command)

        user_prompt = f"Execute the {command.name} command."
        if args:
            user_prompt += f"\nArguments: {args}"
        user_prompt += "\n\nFollow the workflow exactly and provide the output in the specified format."

        if stream:
            result = ""
            usage = None
            spinner = command_spinner(command_name)
            spinner.start()
            
            try:
                first_chunk = True
                for chunk in self.api_client.chat_stream(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    operation=f"command:{command_name}"
                ):
                    if first_chunk:
                        spinner.stop()
                        first_chunk = False
                        
                        
                    if isinstance(chunk, dict) and chunk.get("type") == "usage":
                        usage = chunk.get("usage")
                        continue
                        
                    print(chunk, end="", flush=True)
                    result += chunk
                print()
                return {"content": result, "usage": usage}
            except Exception:
                spinner.fail()
                raise
        else:
            with command_spinner(command_name):
                # Non-streaming doesn't return usage in the same way yet, or we assume it's tracked internally
                # For consistency with the plan, we should try to return it if possible, but the plan focused on streaming
                # Check plan: "Update `chat` method (streaming path)"
                # But LiteLLMClient.chat (non-stream) returns just string.
                # However, LiteLLMClient tracks usage internally so we can get it from today's stats if we really wanted
                # But interactive mode specificially uses streaming.
                return {"content": self.api_client.chat(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    operation=f"command:{command_name}"
                ), "usage": None}

    def _run_daily_brief_direct(self, args: str = "", stream: bool = False) -> Dict:
        """Run daily-brief.ts directly for compact output."""
        import subprocess
        from pathlib import Path

        script_path = Path(self.base_dir) / "Tools" / "daily-brief.ts"

        if not script_path.exists():
            return {"content": "daily-brief.ts not found", "usage": None}

        try:
            cmd = ["bun", str(script_path)]
            if "--save" in args or "-s" in args:
                cmd.append("--save")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.base_dir
            )

            output = result.stdout

            # Inject fresh Oura health data from MCP
            oura_section = self._get_oura_health_section()
            if oura_section:
                # Insert after the date header line
                lines = output.split('\n')
                insert_idx = 4  # After the header box
                for i, line in enumerate(lines):
                    if line.startswith('═══') and i > 2:
                        insert_idx = i + 1
                        break
                lines.insert(insert_idx, oura_section)
                output = '\n'.join(lines)

            if result.stderr and "error" in result.stderr.lower():
                output += f"\n[Warning: {result.stderr.strip()}]"

            if stream:
                print(output)
                return {"content": output, "usage": None}
            else:
                return {"content": output, "usage": None}

        except subprocess.TimeoutExpired:
            return {"content": "Daily brief timed out", "usage": None}
        except FileNotFoundError:
            # Bun not installed, fall back to LLM
            return self._run_command_via_llm("pa:daily", args, stream)
        except Exception as e:
            return {"content": f"Error running daily brief: {e}", "usage": None}

    def _get_oura_health_section(self) -> str:
        """Fetch Oura health data from cache for daily brief."""
        import json
        from datetime import datetime, timedelta

        try:
            # Check cache file first (same as command_router)
            cache_file = self.base_dir / "State" / "OuraCache.json"
            today = datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            data = None
            data_date = None
            if cache_file.exists():
                try:
                    cache = json.loads(cache_file.read_text())
                    # Try today first, then yesterday as fallback
                    data = cache.get(today)
                    data_date = today
                    if not data:
                        data = cache.get(yesterday)
                        data_date = yesterday
                except (json.JSONDecodeError, IOError):
                    pass

            if not data:
                return ""

            # Extract metrics
            summary = data.get("summary", {})
            readiness = data.get("readiness", {})
            sleep = data.get("sleep", {})

            r_score = readiness.get("score", "?") if readiness else "?"
            s_score = sleep.get("score", "?") if sleep else "?"
            overall = summary.get("overall_status", "unknown")

            # Determine energy emoji
            if isinstance(r_score, int):
                if r_score >= 85:
                    energy_emoji, energy = "🟢", "HIGH"
                elif r_score >= 70:
                    energy_emoji, energy = "🟡", "MEDIUM"
                else:
                    energy_emoji, energy = "🔴", "LOW"
            else:
                energy_emoji, energy = "⚪", "UNKNOWN"

            # Get recommendation
            recs = summary.get("recommendations", [])
            rec = recs[0] if recs else "Check /oura for health data"

            # Add date note if using yesterday's data
            date_note = "" if data_date == today else f" (from {data_date})"

            section = f"""
💪 HEALTH STATUS{date_note}:
   {energy_emoji} Energy: {energy}
   😴 Sleep: {s_score}/100  |  🎯 Readiness: {r_score}/100
   📝 {rec}
"""
            return section

        except Exception:
            # Silently fail - Oura is optional
            return ""

    def _run_command_via_llm(self, command_name: str, args: str = "", stream: bool = False) -> Dict:
        """Fallback: run command via LLM."""
        command = self.find_command(command_name)
        if not command:
            return {"content": f"Command not found: {command_name}", "usage": None}

        system_prompt = self._build_system_prompt(command=command)
        user_prompt = f"Execute the {command.name} command."
        if args:
            user_prompt += f"\nArguments: {args}"
        user_prompt += "\n\nFollow the workflow exactly and provide the output in the specified format."

        if stream:
            result = ""
            for chunk in self.api_client.chat_stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
                operation=f"command:{command_name}"
            ):
                if isinstance(chunk, dict) and chunk.get("type") == "usage":
                    continue
                print(chunk, end="", flush=True)
                result += chunk
            print()
            return {"content": result, "usage": None}
        else:
            return {"content": self.api_client.chat(
                prompt=user_prompt,
                system_prompt=system_prompt,
                operation=f"command:{command_name}"
            ), "usage": None}

    def chat(self, message: str, agent: Optional[str] = None,
             stream: bool = False, model: Optional[str] = None,
             history: Optional[List[Dict]] = None,
             tools: Optional[List[Dict]] = None) -> Union[str, Dict]:
        """Chat with a specific agent or auto-detect.

        Args:
            message: User message to send
            agent: Optional agent name to use (auto-detects if None)
            stream: Whether to stream the response
            model: Optional model name to use (uses default from config if None)
            history: Optional list of previous messages for context
            tools: Optional list of tool definitions for MCP tool calling
        """
        if agent is None and model is None and not stream:
            return self.route(message, stream=False)
        
        # Model Escalation: Check if we should switch models based on complexity
        if model is None:
            try:
                escalation_result = model_escalation_hook(
                    conversation_id=f"thanos-chat-{datetime.now().strftime('%Y%m%d')}",
                    conversation_context={
                        'current_message': message,
                        'messages': history or [],
                        'token_count': len(message.split()) * 2
                    }
                )
                if escalation_result.escalated:
                    model = escalation_result.model
                    print(f"[ModelEscalator] Escalated to {model} (complexity: {escalation_result.complexity_score:.2f})")
            except Exception as e:
                log_error("model_escalator", e, "Model escalation check failed in chat")
        
        self._ensure_client()

        # Get agent
        if agent:
            agent_obj = self.agents.get(agent.lower())
        else:
            agent_obj = self.find_agent(message)

        system_prompt = self._build_system_prompt(agent=agent_obj)
        agent_name = agent_obj.name if agent_obj else 'default'

        try:
            if stream:
                result = ""
                usage = None
                spinner = chat_spinner(agent_name)
                spinner.start()
                
                try:
                    first_chunk = True
                    for chunk in self.api_client.chat_stream(
                        prompt=message,
                        model=model,
                        system_prompt=system_prompt,
                        history=history,
                        operation=f"chat:{agent_name}",
                        tools=tools
                    ):
                        if first_chunk:
                            spinner.stop()
                            first_chunk = False
                            
                        
                        if isinstance(chunk, dict) and chunk.get("type") == "usage":
                            usage = chunk.get("usage")
                            continue

                        print(chunk, end="", flush=True)
                        result += chunk
                    print()
                    return {"content": result, "usage": usage}
                except Exception:
                    spinner.fail()
                    raise
            else:
                with chat_spinner(agent_name):
                    return {"content": self.api_client.chat(
                        prompt=message,
                        model=model,
                        system_prompt=system_prompt,
                        history=history,
                        operation=f"chat:{agent_name}",
                        tools=tools
                    ), "usage": None}
        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            # Check for common issues
            if "api key" in str(e).lower():
                error_msg += "\n\nHint: Check that ANTHROPIC_API_KEY is set in your .env file"
            elif "rate limit" in str(e).lower():
                error_msg += "\n\nHint: Rate limit exceeded, try again in a moment"
            print(f"\n{error_msg}\n")
            log_error(e, {"operation": "chat", "agent": agent_obj.name if agent_obj else 'default'})
            return {"content": "", "usage": None}

    def route(self, message: str, stream: bool = False, model: Optional[str] = None) -> Union[str, Dict]:
        """Route a message through the Operator router and executor.
        
        Uses simple keyword-based routing first, then falls back to chat() for 
        conversational responses.
        """
        
        # Model Escalation: Check if we should switch models based on complexity
        if model is None:  # Only auto-escalate if no model override specified
            try:
                escalation_result = model_escalation_hook(
                    conversation_id=f"thanos-main-{datetime.now().strftime('%Y%m%d')}",
                    conversation_context={
                        'current_message': message,
                        'messages': [],  # Could be populated from history if available
                        'token_count': len(message.split()) * 2  # Rough estimate
                    }
                )
                if escalation_result.escalated:
                    model = escalation_result.model
                    print(f"[ModelEscalator] Escalated to {model} (complexity: {escalation_result.complexity_score:.2f})")
            except Exception as e:
                log_error("model_escalator", e, "Model escalation check failed")
        
        self._update_plan_and_scoreboard(message)

        # Check for command pattern (e.g., /pa:daily or pa:daily)
        cmd_match = re.match(r'^/?(\w+:\w+)\s*(.*)?$', message)
        if cmd_match:
            cmd_name = cmd_match.group(1)
            cmd_args = cmd_match.group(2) or ""
            result = self.run_command(cmd_name, cmd_args)
            return {"content": result, "usage": None}

        # Try keyword-based routing
        router_result = self.router.route(message)
        
        # If keyword router found a good match with tool, execute it
        if router_result.tool_name and router_result.confidence >= 0.7:
            exec_result = self.executor.execute(
                router_result.tool_name,
                router_result.parameters
            )
            content = exec_result.output
            if isinstance(content, str):
                content = self._maybe_append_epic_learning(message, content)
            return {"content": content, "usage": None}
        
        # If router has a fallback response (low confidence), use chat instead
        # for a more natural conversational response
        # Pass agent="default" to prevent chat() from recursing back to route()
        chat_result = self.chat(message, agent="default", model=model)
        if isinstance(chat_result, dict):
            chat_result["content"] = self._maybe_append_epic_learning(
                message, chat_result.get("content", "")
            )
            return chat_result
        return {
            "content": self._maybe_append_epic_learning(message, str(chat_result)),
            "usage": None,
        }

    def _maybe_append_epic_learning(self, message: str, reply: str) -> str:
        """Optionally append Epic learning prompt when Epic context detected."""
        if not message or not reply:
            return reply
        try:
            epic_scripts = self.base_dir / "Skills" / "epic-expert-learning" / "scripts"
            if not epic_scripts.exists():
                return reply
            if str(epic_scripts) not in sys.path:
                sys.path.insert(0, str(epic_scripts))

            from ask_question import QuestionAsker  # type: ignore
        except Exception:
            return reply

        try:
            asker = QuestionAsker()
            domain = asker.detect_work_context(message)
            if not domain:
                return reply

            should_ask, _reason = asker.should_ask_question()
            if not should_ask:
                return reply

            question_obj = asker.select_question(domain)
            if not question_obj:
                return reply

            notebook_summary = asker.crossref.summarize_for_question(
                domain=domain,
                question=question_obj["question"],
                timeout=120,
            )
            prompt = asker.generate_question_prompt(
                question_obj, notebook_summary=notebook_summary
            )
            asker.record_question_asked(domain, question_obj)

            return f"{reply}\n\n---\nEpic Learning Check:\n{prompt}"
        except Exception:
            return reply

    def list_commands(self) -> List[str]:
        """List all available commands."""
        seen = set()
        result = []
        for name, cmd in self.commands.items():
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(f"{cmd.name} - {cmd.description[:50]}...")
        return sorted(result)

    def list_agents(self) -> List[str]:
        """List all available agents."""
        return [f"{a.name} ({a.role})" for a in self.agents.values()]

    def get_usage(self, days: int = 30) -> Dict:
        """Get API usage summary."""
        self._ensure_client()
    def refresh_daily_state(self) -> None:
        """Force refresh of daily state (Calendar, WorkOS) into state_store.

        This ensures that commands like pa:daily have fresh context even if
        they don't execute tools themselves.
        """
        # 1. Refresh WorkOS Summary
        try:
            gateway = self._get_workos_gateway()
            if gateway:
                # Run async call synchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    payload = loop.run_until_complete(gateway.get_daily_summary(force_refresh=True))
                    if payload:
                        # Generate summary if needed, for now just store the text representation
                        summary_text = json.dumps(payload, indent=2)

                        # Store in state_store
                        self.state_store.set_state("workos_summary", summary_text)

                        # Also record as a tool output for history
                        self.state_store.add_tool_output_with_summary(
                            "workos.daily_summary", payload, "Refreshed via startup sync", "workos"
                        )
                finally:
                    loop.close()
        except Exception as e:
            log_error("thanos_orchestrator", e, "Failed to refresh WorkOS state")

        # 2. Refresh Calendar Summary
        try:
            adapter = self._get_calendar_adapter()
            if adapter and adapter.is_authenticated():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Get today's events
                    result = loop.run_until_complete(adapter.call_tool("get_today_events", {}))
                    if result.success:
                        events = result.data
                        
                        # Generate human readable summary using the adapter's tool if available
                        # or just formatting the events
                        summary_result = loop.run_until_complete(adapter.call_tool("generate_calendar_summary", {
                            "date": datetime.now().strftime("%Y-%m-%d")
                        }))
                        
                        summary_text = ""
                        if summary_result.success and isinstance(summary_result.data, dict):
                            summary_text = summary_result.data.get("summary", "")
                        else:
                            # Fallback to raw events dump if summary gen failed or return type unexpected
                            summary_text = json.dumps(events, indent=2)

                        self.state_store.set_state("calendar_summary", summary_text)
                finally:
                    loop.close()
        except Exception as e:
            log_error("thanos_orchestrator", e, "Failed to refresh Calendar state")



# Singleton instance
_thanos_instance = None

def get_thanos(base_dir: str = None) -> ThanosOrchestrator:
    """Get or create the singleton orchestrator instance."""
    global _thanos_instance
    if _thanos_instance is None:
        _thanos_instance = ThanosOrchestrator(base_dir)
    return _thanos_instance

# Convenience alias
thanos = None  # Will be initialized on first use


def init_thanos(base_dir: str = None) -> ThanosOrchestrator:
    """Initialize the global thanos instance."""
    global thanos
    thanos = ThanosOrchestrator(base_dir)
    return thanos


def _log_hook_error(error: str):
    """Log hook errors to file without disrupting hook execution.

    HOOK ERROR LOGGING STRATEGY:
    - Errors are logged to ~/.claude/logs/hooks.log for debugging
    - Logging failures NEVER disrupt hook execution (multi-level fallback)
    - All errors eventually exit 0 to maintain Claude Code lifecycle integrity

    This is part of a three-layer error handling system:
      Layer 1: Hook logic (try/except around specific operations)
      Layer 2: Hook function (try/except around entire hook)
      Layer 3: Log function (THIS function - try/except with stderr fallback)

    For comprehensive hook error documentation, see:
    docs/TROUBLESHOOTING.md - Hook Error Management section
    """
    try:
        log_dir = Path.home() / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "hooks.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] [thanos-orchestrator] {error}\n")
    except (OSError, IOError) as e:
        # Layer 3 fallback: Can't write to log file - note to stderr but don't break hooks
        # This handles permissions issues, disk full, or directory creation failures
        import sys
        print(f"[hooks] Cannot write to log file: {e}", file=sys.stderr)
    except Exception as e:
        # Layer 3 fallback: Truly unexpected errors - still don't break hooks
        # Even if logging completely fails, we continue execution
        import sys
        print(f"[CRITICAL] Error logging hook error: {e}", file=sys.stderr)


def _output_hook_response(context: str):
    """Output JSON in Claude hook format."""
    print(json.dumps({
        "hookSpecificOutput": {
            "additionalContext": context
        }
    }))


def handle_hook(event: str, args: List[str], base_dir: Path):
    """Handle hook events from Claude Code lifecycle.

    This function is designed to be fast and reliable:
    - No API calls
    - Only local file reads
    - Graceful error handling (always exit 0)
    - Outputs JSON in Claude hook format

    FAIL-SAFE ERROR HANDLING DESIGN:
    Hooks are critical to Claude Code's lifecycle and MUST NEVER fail. This function
    implements a multi-layer error handling strategy:

    Layer 1: Specific operation errors (state read, file write) are caught with
             nested try/except blocks and handled gracefully with fallback behavior

    Layer 2: Top-level try/except catches any unexpected errors in the hook logic,
             logs them via _log_hook_error(), and continues (see line 1082)

    Layer 3: _log_hook_error() itself has multi-level error handling with stderr
             fallback if log file writing fails

    Result: Hooks ALWAYS exit 0, even if every operation fails. Errors are logged
            to ~/.claude/logs/hooks.log for debugging but never disrupt Claude Code.

    For comprehensive hook error documentation and troubleshooting, see:
    docs/TROUBLESHOOTING.md - Hook Error Management section

    Args:
        event: Hook event name (morning-brief, session-end)
        args: Additional arguments
        base_dir: Thanos base directory
    """
    # Layer 2: Top-level error handler - catches all errors in hook logic
    try:
        if event == "morning-brief":
            # Fast path: read state files, no API calls
            from Tools.state_reader import StateReader
            reader = StateReader(base_dir / "State")
            ctx = reader.get_quick_context()

            parts = []
            if ctx["focus"]:
                parts.append(f"FOCUS: {ctx['focus']}")
            if ctx["top3"]:
                # Abbreviate to first 2 items
                items = ctx["top3"][:2]
                if len(items) == 1:
                    parts.append(f"TOP: {items[0]}")
                else:
                    parts.append(f"TOP: {items[0]} / {items[1]}...")
            if ctx["pending_commitments"] > 0:
                parts.append(f"PENDING: {ctx['pending_commitments']} commitments")
            if ctx["blockers"]:
                parts.append(f"BLOCKED: {ctx['blockers'][0]}")

            if parts:
                context = "[THANOS] " + " | ".join(parts)
                if ctx["is_morning"]:
                    context += "\n[ACTION] Consider running /pa:daily for full morning briefing"
                _output_hook_response(context)

        elif event == "session-end":
            # Log session to History/Sessions
            history_dir = base_dir / "History" / "Sessions"
            history_dir.mkdir(parents=True, exist_ok=True)

            now = datetime.now()
            filename = now.strftime("%Y-%m-%d-%H%M.md")
            log_path = history_dir / filename

            # Don't overwrite existing logs (multiple sessions same minute)
            if log_path.exists():
                # Append a suffix
                for i in range(2, 10):
                    alt_path = history_dir / now.strftime(f"%Y-%m-%d-%H%M-{i}.md")
                    if not alt_path.exists():
                        log_path = alt_path
                        break

            session_log = f"""# Session: {now.strftime("%Y-%m-%d %H:%M")}

## Summary
- Duration: ~unknown (hook-logged)
- Topics: [to be populated]

## Context at End
"""
            # Add quick context snapshot
            # Layer 1: Nested error handling for state file operations
            try:
                from Tools.state_reader import StateReader
                reader = StateReader(base_dir / "State")
                ctx = reader.get_quick_context()
                if ctx["focus"]:
                    session_log += f"- Focus: {ctx['focus']}\n"
                if ctx["pending_commitments"] > 0:
                    session_log += f"- Pending commitments: {ctx['pending_commitments']}\n"
            except (OSError, IOError) as e:
                # Layer 1 fallback: State file read errors - note in log but continue
                # Graceful degradation: Show [Context unavailable] instead of failing the hook
                log_error("thanos_orchestrator", e, "Failed to read state for session log")
                session_log += "- [Context unavailable]\n"
            except Exception as e:
                # Layer 1 fallback: Unexpected errors in state reading
                # Graceful degradation: Still create session log without context
                log_error("thanos_orchestrator", e, "Unexpected error reading context for session log")
                session_log += "- [Context unavailable]\n"

            session_log += f"""
## State Changes
- Check git diff for file changes

---
*Auto-logged by Thanos Orchestrator*
"""

            log_path.write_text(session_log)
            # Output confirmation (not as hook context, just for logging)
            print(f"Session logged: {log_path.name}", file=__import__('sys').stderr)

        else:
            # Unknown hook event - log but don't fail
            _log_hook_error(f"Unknown hook event: {event}")

    except Exception as e:
        # Layer 2 fallback: Top-level catch-all for any unexpected errors
        # This catches errors not handled by Layer 1 nested handlers
        # Examples: import errors, unexpected exceptions in hook logic
        _log_hook_error(f"{event} error: {e}")
        # CRITICAL: Always exit cleanly for hooks - NEVER raise or sys.exit(1)
        # Claude Code depends on hooks exiting with code 0 for lifecycle integrity
        # Errors are logged to ~/.claude/logs/hooks.log for debugging
        # See docs/TROUBLESHOOTING.md - Hook Error Management for troubleshooting
        pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Thanos Orchestrator")
        print("==================")
        print("Usage:")
        print("  python thanos_orchestrator.py list-commands")
        print("  python thanos_orchestrator.py list-agents")
        print("  python thanos_orchestrator.py run <command> [args]")
        print("  python thanos_orchestrator.py chat <message>")
        print("  python thanos_orchestrator.py usage")
        print("  python thanos_orchestrator.py hook <event> [args]")
        print()
        print("Hook events:")
        print("  morning-brief   - Generate quick morning context (no API)")
        print("  session-end     - Log session to History/Sessions/")
        sys.exit(0)

    # Hook subcommand - handle before ThanosOrchestrator init for speed
    if sys.argv[1] == "hook":
        if len(sys.argv) < 3:
            print("Usage: thanos_orchestrator.py hook <event> [args]", file=sys.stderr)
            sys.exit(0)  # Exit 0 even on error for hooks

        event = sys.argv[2]
        hook_args = sys.argv[3:] if len(sys.argv) > 3 else []
        base_dir = Path(__file__).parent.parent
        handle_hook(event, hook_args, base_dir)
        sys.exit(0)

    t = ThanosOrchestrator()

    if sys.argv[1] == "list-commands":
        print("Available Commands:")
        for cmd in t.list_commands():
            print(f"  {cmd}")

    elif sys.argv[1] == "list-agents":
        print("Available Agents:")
        for agent in t.list_agents():
            print(f"  {agent}")

    elif sys.argv[1] == "run" and len(sys.argv) >= 3:
        cmd_name = sys.argv[2]
        args = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        print(f"Running {cmd_name}...")
        print("-" * 40)
        t.run_command(cmd_name, args, stream=True)

    elif sys.argv[1] == "chat" and len(sys.argv) >= 3:
        message = " ".join(sys.argv[2:])
        t.chat(message, stream=True)

    elif sys.argv[1] == "usage":
        try:
            usage = t.get_usage()
            print("API Usage (Last 30 Days)")
            print(f"   Tokens: {usage['total_tokens']:,}")
            print(f"   Cost: ${usage['total_cost_usd']:.2f}")
            print(f"   Monthly Projection: ${usage['projected_monthly_cost']:.2f}")
        except Exception as e:
            print(f"Error getting usage: {e}")

    else:
        print(f"Unknown command: {sys.argv[1]}")
