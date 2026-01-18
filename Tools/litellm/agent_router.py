#!/usr/bin/env python3
"""
Agent-based model routing for Thanos personas.

Routes requests to optimal models based on agent characteristics
rather than just prompt complexity. This enables using the best model
for each agent's personality and use case:

- Ops: Fast, tool-focused (OpenAI)
- Coach: Empathetic, nuanced (Claude)
- Strategy: Complex reasoning (OpenAI premium)
- Health: Warm, sensitive (Claude)

Usage:
    from Tools.litellm.agent_router import AgentRouter
    
    router = AgentRouter(config)
    model = router.get_model("coach")  # Returns "claude-3-5-haiku-20241022"
    chain = router.get_agent_chain("coach")  # ["claude-3-5-haiku-20241022", "gpt-4.1-mini"]
"""

from typing import Dict, List, Optional


class AgentRouter:
    """Route model selection based on active Thanos agent."""
    
    # Default agent configurations if not in config file
    DEFAULT_AGENTS = {
        "ops": {
            "model": "gpt-4.1-nano",
            "fallback": "gpt-4.1-mini",
            "description": "Fast operations, tool calls, scheduling"
        },
        "coach": {
            "model": "claude-3-5-haiku-20241022",
            "fallback": "gpt-4.1-mini",
            "description": "Empathetic coaching, accountability"
        },
        "strategy": {
            "model": "gpt-4o",
            "fallback": "claude-3-5-sonnet-20241022",
            "description": "Complex reasoning, big-picture planning"
        },
        "health": {
            "model": "claude-3-5-haiku-20241022",
            "fallback": "gpt-4.1-mini",
            "description": "Sensitive health topics, ADHD support"
        }
    }
    
    def __init__(self, config: Dict):
        """Initialize agent router with configuration.
        
        Args:
            config: Full API config dict (expects 'agent_routing' key)
        """
        self.config = config.get("agent_routing", {})
        self.enabled = self.config.get("enabled", False)
        self.agents = self.config.get("agents", self.DEFAULT_AGENTS)
        self.default_model = self.config.get("default_agent_model", "gpt-4.1-nano")
    
    def is_enabled(self) -> bool:
        """Check if agent-based routing is enabled."""
        return self.enabled
    
    def get_model(self, agent_name: str) -> Optional[str]:
        """Get recommended model for an agent.
        
        Args:
            agent_name: Name of the agent (ops, coach, strategy, health)
            
        Returns:
            Model name string or None if agent routing disabled
        """
        if not self.enabled:
            return None
        
        agent_config = self.agents.get(agent_name.lower(), {})
        return agent_config.get("model", self.default_model)
    
    def get_fallback(self, agent_name: str) -> Optional[str]:
        """Get fallback model for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Fallback model name or None
        """
        agent_config = self.agents.get(agent_name.lower(), {})
        return agent_config.get("fallback")
    
    def get_agent_chain(self, agent_name: str) -> List[str]:
        """Get ordered model chain for an agent (primary + fallback).
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of models to try in order
        """
        models = []
        primary = self.get_model(agent_name)
        fallback = self.get_fallback(agent_name)
        
        if primary:
            models.append(primary)
        if fallback and fallback != primary:
            models.append(fallback)
        
        return models
    
    def get_all_agents(self) -> Dict[str, Dict]:
        """Get all configured agents and their settings."""
        return self.agents.copy()
    
    def is_claude_model(self, model: str) -> bool:
        """Check if a model is a Claude model."""
        return model.startswith("claude")
    
    def is_openai_model(self, model: str) -> bool:
        """Check if a model is an OpenAI model."""
        return model.startswith("gpt")
