#!/usr/bin/env python3
"""
Domain-Specific Agent Router

Routes messages to specialized domain agents based on keywords and context.
Main agent becomes a coordinator that delegates to specialists.
"""

import re
from typing import Dict, List, Optional
from pathlib import Path

class DomainRouter:
    def __init__(self):
        self.domains = {
            'finance': {
                'keywords': ['money', 'budget', 'monarch', 'spending', 'balance', 
                            'transaction', 'payment', 'expense', 'income', 'cash', 
                            'runway', 'forecast', 'debt', 'savings'],
                'agent': 'finance',
                'description': 'Budget tracking, spending analysis, financial planning'
            },
            'productivity': {
                'keywords': ['task', 'todo', 'priority', 'adhd', 'stuck', 
                            'procrastinating', 'focus', 'energy', 'activation',
                            'vigilance', 'tracking', 'habit', 'pattern'],
                'agent': 'productivity',
                'description': 'Task management, ADHD support, activation strategies'
            },
            'work': {
                'keywords': ['epic', 'clindoc', 'orders', 'client', 'certification',
                            'linkedin', 'consulting', 'implementation', 'module',
                            'beaker', 'willow', 'cadence'],
                'agent': 'work',
                'description': 'Epic consulting, certification, client management'
            },
            'health': {
                'keywords': ['vyvanse', 'energy', 'tired', 'crash', 'oura',
                            'readiness', 'sleep', 'medication', 'supplement',
                            'health', 'fitness'],
                'agent': 'health',
                'description': 'Medication management, energy optimization, health tracking'
            },
            'family': {
                'keywords': ['ashley', 'sullivan', 'family', 'household',
                            'relationship', 'parenting', 'home', 'kids'],
                'agent': 'family',
                'description': 'Family management, household coordination, relationships'
            },
            'code': {
                'keywords': ['architecture', 'bug', 'design', 'refactor',
                            'implement', 'code', 'git', 'deployment', 'testing',
                            'debug', 'error', 'function', 'class'],
                'agent': 'code',
                'description': 'Software architecture, debugging, technical design'
            }
        }
    
    def route_message(self, message: str) -> Optional[str]:
        """
        Route message to appropriate domain agent
        
        Args:
            message: User message to route
            
        Returns:
            Agent name to route to, or None for main agent
        """
        msg_lower = message.lower()
        
        # Count keyword matches per domain
        matches = {}
        for domain, config in self.domains.items():
            count = sum(1 for kw in config['keywords'] if kw in msg_lower)
            if count > 0:
                matches[domain] = count
        
        # If no matches, return None (main agent handles)
        if not matches:
            return None
        
        # Return domain with most matches
        best_domain = max(matches, key=matches.get)
        return self.domains[best_domain]['agent']
    
    def get_agent_info(self, agent_name: str) -> Optional[Dict]:
        """Get information about a specific agent"""
        for domain, config in self.domains.items():
            if config['agent'] == agent_name:
                return config
        return None
    
    def list_agents(self) -> List[Dict]:
        """List all available domain agents"""
        return [
            {
                'name': config['agent'],
                'domain': domain,
                'description': config['description']
            }
            for domain, config in self.domains.items()
        ]

def main():
    """CLI interface for testing router"""
    import sys
    
    router = DomainRouter()
    
    if len(sys.argv) < 2:
        print("Usage: domain_router.py <message>")
        print("\nAvailable agents:")
        for agent in router.list_agents():
            print(f"  {agent['name']}: {agent['description']}")
        sys.exit(1)
    
    message = ' '.join(sys.argv[1:])
    agent = router.route_message(message)
    
    if agent:
        print(f"Route to: {agent}")
    else:
        print("Route to: main (no specialist match)")

if __name__ == '__main__':
    main()
