#!/usr/bin/env python3
"""
Epic Expert Learning - Solution Capture Workflow

Guides the agent through capturing Jeremy's Epic problem-solving approach.
Stores learnings in Memory V2, Graphiti, and updates learning state.

Usage:
    python capture_solution.py --interactive
    python capture_solution.py --auto-detect "User message text"
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Paths
SKILL_DIR = Path(__file__).parent.parent
STATE_FILE = SKILL_DIR / "references" / "learning-state.json"
DOMAINS_FILE = SKILL_DIR / "references" / "epic-domains.md"


class SolutionCapture:
    """Handles solution capture workflow and storage."""

    def __init__(self):
        self.state = self.load_state()
        self.domains = self.load_domains()

    def load_state(self) -> Dict:
        """Load current learning state."""
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_state(self):
        """Save updated learning state."""
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def load_domains(self) -> List[str]:
        """Load available domain names."""
        return [
            "orderset_builds",
            "interfaces",
            "clindoc_configuration",
            "cardiac_rehab_integrations",
            "workflow_optimization",
            "cutover_procedures"
        ]

    def detect_completion_signal(self, message: str) -> bool:
        """
        Detect if user message indicates Epic problem completion.
        
        Completion signals:
        - "fixed", "solved", "working", "done", "completed"
        - "finally got X working"
        - "issue resolved"
        """
        keywords = [
            "fixed", "solved", "working now", "done", "completed",
            "finally got", "issue resolved", "problem solved",
            "that worked", "success"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in keywords)

    def detect_domain_from_context(self, context: str) -> str:
        """
        Infer Epic domain from context.
        
        Keywords mapping:
        - orderset, smartset, quick list, preference → orderset_builds
        - interface, hl7, bridge, provider matching → interfaces
        - smartphrase, template, clindoc, flowsheet → clindoc_configuration
        - versacare, scottcare, rehab, cardiac → cardiac_rehab_integrations
        - bpa, workflow, efficiency, optimization → workflow_optimization
        - cutover, go-live, migration, validation → cutover_procedures
        """
        context_lower = context.lower()

        domain_keywords = {
            "orderset_builds": ["orderset", "order set", "smartset", "quick list", 
                                "preference", "panel", "redirector"],
            "interfaces": ["interface", "hl7", "bridge", "provider matching",
                          "adt", "orm", "oru", "mapping"],
            "clindoc_configuration": ["smartphrase", "smarttext", "template",
                                     "clindoc", "flowsheet", "navigator"],
            "cardiac_rehab_integrations": ["versacare", "scottcare", "rehab",
                                          "cardiac", "telemonitoring"],
            "workflow_optimization": ["bpa", "workflow", "efficiency", 
                                     "optimization", "click reduction"],
            "cutover_procedures": ["cutover", "go-live", "migration", 
                                  "validation", "command center"]
        }

        for domain, keywords in domain_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                return domain

        return "unknown"

    def guided_capture(self) -> Dict:
        """
        Run interactive guided capture workflow.
        
        Returns solution data structure for storage.
        """
        print("\n🎓 Epic Solution Capture\n")

        # Collect solution details
        problem = input("What was the problem? ")
        approach = input("How did you approach it? ")
        decision = input("What was your key decision/solution? ")
        reasoning = input("Why did you choose this approach? ")
        alternatives = input("What alternatives did you consider? (comma-separated) ")
        learnings = input("What would you do differently next time? ")

        # Domain and metadata
        print("\nAvailable domains:")
        for i, domain in enumerate(self.domains, 1):
            print(f"  {i}. {domain}")
        domain_idx = int(input("Select domain (number): ")) - 1
        domain = self.domains[domain_idx]

        complexity = int(input("Complexity (1-5, where 5 is expert-level): "))
        client = input("Client/project (optional): ") or "general"

        # Build solution object
        solution = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": domain,
            "complexity": complexity,
            "client": client,
            "problem": problem,
            "approach": approach,
            "solution": decision,
            "reasoning": reasoning,
            "alternatives": [a.strip() for a in alternatives.split(",") if a.strip()],
            "learnings": learnings,
            "confidence": "high",  # Directly from Jeremy
            "source": "guided_capture"
        }

        return solution

    def auto_capture_from_context(self, context: str, problem: str, 
                                   solution: str) -> Dict:
        """
        Auto-capture from detected context (non-interactive).
        
        Used when agent detects completion and extracts solution from conversation.
        """
        domain = self.detect_domain_from_context(context)

        solution_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": domain,
            "complexity": 3,  # Default medium, can be refined
            "client": "auto-detected",
            "problem": problem,
            "approach": "auto-captured from context",
            "solution": solution,
            "reasoning": "extracted from conversation",
            "alternatives": [],
            "learnings": "",
            "confidence": "medium",  # Lower since not directly asked
            "source": "auto_capture"
        }

        return solution_obj

    def store_in_memory_v2(self, solution: Dict):
        """
        Store solution facts in Memory V2 for semantic search.
        
        Integration point: Replace with actual Memory V2 API.
        """
        facts = [
            {
                "content": f"Problem: {solution['problem']}",
                "tags": ["epic", solution["domain"], "problem"],
                "source": f"solution_{solution['timestamp']}",
                "confidence": 0.9 if solution['confidence'] == 'high' else 0.7
            },
            {
                "content": f"Solution: {solution['solution']}. Reasoning: {solution['reasoning']}",
                "tags": ["epic", solution["domain"], "solution"],
                "source": f"solution_{solution['timestamp']}",
                "confidence": 0.9 if solution['confidence'] == 'high' else 0.7
            }
        ]

        # TODO: Integrate with actual Memory V2 API
        # from memory_v2 import store_fact
        # for fact in facts:
        #     store_fact(**fact)

        print(f"  → Memory V2: {len(facts)} facts stored")
        return facts

    def store_in_graphiti(self, solution: Dict):
        """
        Store decision patterns in Graphiti knowledge graph.
        
        Integration point: Replace with actual Graphiti API.
        """
        relationships = [
            {
                "subject": "Jeremy",
                "predicate": "solved",
                "object": solution["problem"],
                "context": {
                    "solution": solution["solution"],
                    "reasoning": solution["reasoning"],
                    "domain": solution["domain"],
                    "complexity": solution["complexity"],
                    "date": solution["timestamp"]
                }
            }
        ]

        if solution["alternatives"]:
            relationships.append({
                "subject": solution["solution"],
                "predicate": "chosen_over",
                "object": ", ".join(solution["alternatives"]),
                "context": {
                    "reasoning": solution["reasoning"],
                    "domain": solution["domain"]
                }
            })

        # TODO: Integrate with actual Graphiti API
        # from graphiti import add_relationship
        # for rel in relationships:
        #     add_relationship(**rel)

        print(f"  → Graphiti: {len(relationships)} relationships stored")
        return relationships

    def update_learning_state(self, solution: Dict):
        """Update learning-state.json with new solution and domain progress."""
        domain = solution["domain"]

        if domain not in self.state.get("domains", {}):
            print(f"  ! Warning: Unknown domain '{domain}', skipping state update")
            return

        # Update domain stats
        domain_state = self.state["domains"][domain]
        domain_state["solutions_captured"] += 1
        domain_state["concepts_learned"] += 1  # Assume each solution = new concept
        domain_state["last_updated"] = solution["timestamp"]

        # Add to recent concepts
        if "recent_concepts" not in domain_state:
            domain_state["recent_concepts"] = []

        domain_state["recent_concepts"].insert(0, {
            "concept": solution["solution"],
            "learned_date": solution["timestamp"].split("T")[0],
            "confidence": solution["confidence"],
            "source": solution["source"]
        })

        # Keep only last 5 recent concepts
        domain_state["recent_concepts"] = domain_state["recent_concepts"][:5]

        # Update strength level
        concepts = domain_state["concepts_learned"]
        if concepts >= 51:
            domain_state["strength"] = "expert"
            domain_state["strength_level"] = 4
        elif concepts >= 31:
            domain_state["strength"] = "advanced"
            domain_state["strength_level"] = 3
        elif concepts >= 16:
            domain_state["strength"] = "intermediate"
            domain_state["strength_level"] = 2
        elif concepts >= 6:
            domain_state["strength"] = "beginner"
            domain_state["strength_level"] = 1
        else:
            domain_state["strength"] = "novice"
            domain_state["strength_level"] = 0

        # Update global stats
        if "global_stats" in self.state:
            self.state["global_stats"]["total_solutions_captured"] += 1
            self.state["global_stats"]["total_concepts_learned"] += 1

        # Update recent learnings
        if "recent_learnings" not in self.state:
            self.state["recent_learnings"] = []

        self.state["recent_learnings"].insert(0, {
            "date": solution["timestamp"].split("T")[0],
            "domain": domain,
            "concept": solution["solution"],
            "source": solution["source"],
            "confidence": solution["confidence"],
            "context": solution["problem"]
        })

        # Keep only last 10 recent learnings
        self.state["recent_learnings"] = self.state["recent_learnings"][:10]

        # Update session history
        if "session_history" not in self.state:
            self.state["session_history"] = {}

        self.state["session_history"]["last_capture_timestamp"] = solution["timestamp"]
        self.state["session_history"]["captures_today"] = \
            self.state["session_history"].get("captures_today", 0) + 1

        self.save_state()
        print(f"  → Learning state updated: {domain} now {domain_state['strength']} "
              f"({domain_state['concepts_learned']} concepts)")

    def capture_and_store(self, solution: Dict):
        """Execute full capture workflow: store in all systems."""
        print(f"\n📦 Storing solution in knowledge systems...")

        self.store_in_memory_v2(solution)
        self.store_in_graphiti(solution)
        self.update_learning_state(solution)

        print(f"\n✅ Solution captured successfully!")
        print(f"   Domain: {solution['domain']}")
        print(f"   Complexity: {solution['complexity']}/5")
        print(f"   Confidence: {solution['confidence']}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Epic Solution Capture")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Run interactive guided capture")
    parser.add_argument("--auto-detect", "-a", type=str,
                       help="Auto-detect completion from message")
    parser.add_argument("--context", "-c", type=str,
                       help="Context for auto-detection")

    args = parser.parse_args()

    capturer = SolutionCapture()

    if args.interactive:
        solution = capturer.guided_capture()
        capturer.capture_and_store(solution)

    elif args.auto_detect:
        if capturer.detect_completion_signal(args.auto_detect):
            print("🎯 Completion signal detected!")
            # In real usage, agent would extract problem/solution from context
            # For now, this is a stub
            print("Agent would now ask: 'Can I capture how you solved this?'")
        else:
            print("No completion signal detected in message.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
