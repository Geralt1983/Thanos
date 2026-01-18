"""
Intent Service - Natural language intent matching

Extracted from ThanosOrchestrator for single-responsibility.
Handles intent matching using keyword patterns or trie-based matching.
"""

from typing import Dict, List, Optional, Union, Any

from .agent_service import Agent


# Default agent keywords for intent matching
# Keywords are organized by agent and priority tier
# Total: 92 keywords across 4 agents (ops=26, coach=24, strategy=20, health=22)
DEFAULT_AGENT_KEYWORDS = {
    "ops": {
        "high": [
            "what should i do",
            "whats on my plate",
            "help me plan",
            "overwhelmed",
            "what did i commit",
            "process inbox",
            "clear my inbox",
            "prioritize",
            "show my calendar",
            "when am i free",
            "schedule this task",
            "what should i focus on",
            "next action",
            "next step",
        ],
        "medium": [
            "task",
            "tasks",
            "todo",
            "to-do",
            "schedule",
            "plan",
            "organize",
            "today",
            "tomorrow",
            "this week",
            "deadline",
            "due",
            "calendar",
            "meeting",
            "meetings",
            "appointment",
            "appointments",
            "event",
            "events",
            "free time",
            "availability",
            "book",
            "block time",
            "email",
            "inbox",
        ],
        "low": ["busy", "work", "productive", "efficiency"],
    },
    "coach": {
        "high": [
            "i keep doing this",
            "why can't i",
            "im struggling",
            "i'm struggling",
            "why cant i",
            "pattern",
            "be honest",
            "accountability",
            "avoiding",
            "procrastinating",
            "stick to my goals",
            "hold me accountable",
            "analyze my behavior",
            "self-sabotaging",
            "pep talk",
        ],
        "medium": [
            "habit",
            "habits",
            "stuck",
            "motivation",
            "discipline",
            "consistent",
            "consistency",
            "excuse",
            "excuses",
            "failing",
            "trying",
            "again",
            "distracted",
            "distraction",
            "focus",
            "analyze",
        ],
        "low": ["feel", "feeling", "hard", "difficult", "trying"],
    },
    "strategy": {
        "high": [
            "quarterly",
            "long-term",
            "strategy",
            "goals",
            "where am i headed",
            "big picture",
            "priorities",
            "direction",
            "is it worth",
            "best approach",
            "right track",
            "vision",
            "mission",
            "tradeoff",
            "tradeoffs",
        ],
        "medium": [
            "should i take this client",
            "revenue",
            "growth",
            "future",
            "planning",
            "decision",
            "invest",
            "worth it",
            "years",
            "year plan",
        ],
        "low": ["career", "business", "opportunity", "risk"],
    },
    "health": {
        "high": [
            "im tired",
            "i'm tired",
            "should i take my vyvanse",
            "i cant focus",
            "i'm not sleeping well",
            "i can't focus",
            "supplements",
            "i crashed",
            "energy",
            "sleep",
            "medication",
            "crashed",
            "drained",
            "focus",
            "maintain focus",
            "brain fog",
            "burnt out",
            "burnout",
            "meds",
            "vyvanse",
        ],
        "medium": [
            "exhausted",
            "exhaustion",
            "fatigue",
            "fatigued",
            "concentration",
            "adhd",
            "stimulant",
            "caffeine",
            "workout",
            "workouts",
            "exercise",
            "exercising",
            "tired",
            "concentrate",
        ],
        "low": ["rest", "break", "recovery"],
    },
}


class IntentService:
    """Service for natural language intent matching.

    Usage:
        service = IntentService()
        service.initialize(agent_triggers={"ops": ["task", "todo"]})
        agent_name = service.find_best_agent("What should I do today?")
    """

    def __init__(
        self,
        agent_keywords: Optional[Dict[str, Dict[str, List[str]]]] = None,
        matcher_strategy: str = "regex",
    ):
        """Initialize intent service.

        Args:
            agent_keywords: Custom keyword configuration (uses defaults if None)
            matcher_strategy: 'regex' or 'trie' for matching strategy
        """
        self.agent_keywords = agent_keywords or DEFAULT_AGENT_KEYWORDS
        self.matcher_strategy = matcher_strategy
        self._matcher: Optional[Any] = None
        self._agent_triggers: Dict[str, List[str]] = {}
        self._agents: Dict[str, Agent] = {}

    def initialize(
        self,
        agent_triggers: Optional[Dict[str, List[str]]] = None,
        agents: Optional[Dict[str, Agent]] = None,
    ) -> None:
        """Initialize the intent matcher with triggers and agents.

        Args:
            agent_triggers: Dictionary mapping agent names to trigger lists
            agents: Dictionary of Agent objects for fallback routing
        """
        self._agent_triggers = agent_triggers or {}
        self._agents = agents or {}
        self._matcher = None  # Reset matcher to force reinitialization

    def _get_matcher(self) -> Any:
        """Get or create the cached intent matcher.

        Returns:
            KeywordMatcher or TrieKeywordMatcher instance
        """
        if self._matcher is None:
            # Import here to avoid circular imports
            from Tools.intent_matcher import KeywordMatcher, TrieKeywordMatcher

            if self.matcher_strategy == "trie":
                self._matcher = TrieKeywordMatcher(
                    self.agent_keywords, self._agent_triggers
                )
            else:
                self._matcher = KeywordMatcher(
                    self.agent_keywords, self._agent_triggers
                )

        return self._matcher

    def match_intent(self, message: str) -> Dict[str, float]:
        """Match message to agent scores.

        Args:
            message: User message to analyze

        Returns:
            Dictionary mapping agent names to confidence scores
        """
        matcher = self._get_matcher()
        return matcher.match(message)

    def find_best_agent(self, message: str, confidence_threshold: float = 5.0) -> Optional[str]:
        """Find the best matching agent for a message.

        Args:
            message: User message to analyze
            confidence_threshold: Minimum score for high-confidence match

        Returns:
            Agent name or None if no confident match
        """
        scores = self.match_intent(message)

        if not scores:
            return None

        best_agent, best_score = max(scores.items(), key=lambda x: x[1])

        if best_score >= confidence_threshold:
            return best_agent

        # Below threshold - return best if any score
        if best_score > 0:
            return best_agent

        return None

    def find_agent(
        self,
        message: str,
        api_client: Optional[Any] = None,
        confidence_threshold: float = 5.0,
    ) -> Optional[Agent]:
        """Find appropriate agent for a message using hybrid routing.

        1. Fast Keyword Matcher (Zero latency, deterministic)
        2. Semantic LLM Fallback (Higher accuracy for complex queries)
        3. Heuristic Fallback (legacy logic)

        Args:
            message: User message
            api_client: Optional API client for LLM fallback
            confidence_threshold: Score threshold for high-confidence match

        Returns:
            Agent instance or None
        """
        # 1. Fast Path: Keyword matching
        best_agent_name = self.find_best_agent(message, confidence_threshold)

        if best_agent_name and best_agent_name in self._agents:
            return self._agents.get(best_agent_name)

        # 2. Semantic Fallback: Use LLM routing for ambiguous queries
        if api_client and hasattr(api_client, "route"):
            candidates = ["ops", "coach", "strategy", "health"]
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
                routed_agent_name = api_client.route(
                    query=message,
                    candidates=candidates,
                    classification_prompt=system_prompt,
                )
                if routed_agent_name and routed_agent_name in self._agents:
                    return self._agents.get(routed_agent_name)
            except Exception as e:
                print(f"Routing error: {e}")

        # 3. Heuristic Fallback
        message_lower = message.lower()
        if any(
            word in message_lower
            for word in ["what should", "help me", "need to", "have to"]
        ):
            return self._agents.get("ops")
        if any(
            word in message_lower
            for word in ["should i", "is it worth", "best approach"]
        ):
            return self._agents.get("strategy")

        # Default fallback
        return self._agents.get("ops")
