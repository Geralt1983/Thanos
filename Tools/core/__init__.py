"""
Thanos Core Services

Provides focused, single-responsibility services extracted from ThanosOrchestrator.
This module follows the Hexagonal Architecture pattern with clear service boundaries.

Services:
    - AgentService: Agent loading and management
    - CommandService: Command registry and lookup
    - ContextService: Context aggregation and prompt building
    - IntentService: Natural language intent matching
    - CalendarService: Calendar and WorkOS integration
    - ThanosOrchestratorV2: Slim coordinator using services
"""

from .interfaces import (
    IAgentService,
    ICommandService,
    IContextService,
    IIntentService,
    ICalendarService,
)
from .agent_service import AgentService, Agent
from .command_service import CommandService, Command
from .context_service import ContextService
from .intent_service import IntentService
from .calendar_service import CalendarService
from .orchestrator_v2 import ThanosOrchestratorV2

__all__ = [
    # Interfaces
    "IAgentService",
    "ICommandService",
    "IContextService",
    "IIntentService",
    "ICalendarService",
    # Implementations
    "AgentService",
    "CommandService",
    "ContextService",
    "IntentService",
    "CalendarService",
    "ThanosOrchestratorV2",
    # Data classes
    "Agent",
    "Command",
]
