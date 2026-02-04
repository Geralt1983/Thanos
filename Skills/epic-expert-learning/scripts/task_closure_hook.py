#!/usr/bin/env python3
"""
Epic Expert Learning - Task Closure Learning Hook

Automatically captures learnings when Jeremy closes Epic-related WorkOS tasks.
Integrates with WorkOS task state change events (status → "done" or "complete").

Usage:
    # Manual test
    python task_closure_hook.py --task-id <id> --interactive
    
    # Automatic (called by WorkOS webhook)
    python task_closure_hook.py --task-data <json_file>
    
    # Agent integration
    python task_closure_hook.py --task-id <id> --auto-capture
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Paths
SKILL_DIR = Path(__file__).parent.parent
STATE_FILE = SKILL_DIR / "references" / "learning-state.json"

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from openai_rag_crossref import OpenAIRagCrossRef


class TaskClosureHook:
    """Handles automatic learning capture from WorkOS task closures."""

    def __init__(self):
        self.state = self.load_state()
        self.epic_indicators = self.load_epic_indicators()
        self.crossref = OpenAIRagCrossRef()

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

    def load_epic_indicators(self) -> Dict:
        """
        Load Epic context indicators for detection.
        
        Returns dict with:
        - client_tags: Known Epic client tags
        - title_keywords: Epic-specific keywords
        - domain_keywords: Keywords mapped to domains
        """
        return {
            "client_tags": [
                "epic", "ky", "kentucky", "versacare", "scottcare",
                "emr", "ehr", "orderset", "interface", "clindoc"
            ],
            "title_keywords": [
                "epic", "orderset", "order set", "smartset", "quick list",
                "interface", "hl7", "bridge", "provider matching",
                "versacare", "scottcare", "rehab", "cardiac",
                "smartphrase", "template", "clindoc", "flowsheet",
                "bpa", "cutover", "go-live", "migration"
            ],
            "domain_keywords": {
                "orderset_builds": [
                    "orderset", "order set", "smartset", "quick list",
                    "preference", "panel", "redirector", "occ"
                ],
                "interfaces": [
                    "interface", "hl7", "bridge", "provider matching",
                    "adt", "orm", "oru", "mapping", "integration"
                ],
                "clindoc_configuration": [
                    "smartphrase", "smarttext", "template", "clindoc",
                    "flowsheet", "navigator", "documentation"
                ],
                "cardiac_rehab_integrations": [
                    "versacare", "scottcare", "rehab", "cardiac",
                    "telemonitoring", "device"
                ],
                "workflow_optimization": [
                    "bpa", "workflow", "efficiency", "optimization",
                    "click reduction", "best practice"
                ],
                "cutover_procedures": [
                    "cutover", "go-live", "migration", "validation",
                    "command center", "deploy"
                ]
            }
        }

    def detect_epic_context(self, task: Dict) -> Tuple[bool, Optional[str], float]:
        """
        Detect if task is Epic-related and identify domain.
        
        Returns:
            (is_epic: bool, domain: str|None, confidence: float)
        """
        title = task.get("title", "").lower()
        description = task.get("description", "").lower()
        tags = [tag.lower() for tag in task.get("tags", [])]
        client = task.get("client", "").lower()

        # Combine all text for analysis
        combined_text = f"{title} {description} {client} {' '.join(tags)}"

        # Check for Epic indicators
        is_epic = False
        confidence = 0.0

        # Client tags (high confidence)
        for tag in self.epic_indicators["client_tags"]:
            if tag in combined_text:
                is_epic = True
                confidence = max(confidence, 0.9)

        # Title keywords (medium-high confidence)
        for keyword in self.epic_indicators["title_keywords"]:
            if keyword in title:
                is_epic = True
                confidence = max(confidence, 0.8)
            elif keyword in combined_text:
                is_epic = True
                confidence = max(confidence, 0.6)

        if not is_epic:
            return False, None, 0.0

        # Identify domain
        domain_scores = {}
        for domain, keywords in self.epic_indicators["domain_keywords"].items():
            score = 0
            for keyword in keywords:
                if keyword in title:
                    score += 3  # Title match = strong signal
                elif keyword in description:
                    score += 2  # Description match = medium signal
                elif keyword in combined_text:
                    score += 1  # Tag/client match = weak signal

            if score > 0:
                domain_scores[domain] = score

        # Select highest-scoring domain
        if domain_scores:
            domain = max(domain_scores.items(), key=lambda x: x[1])[0]
            # Boost confidence if domain is clear
            if domain_scores[domain] >= 3:
                confidence = min(1.0, confidence + 0.1)
        else:
            domain = "workflow_optimization"  # Default generic domain

        return True, domain, confidence

    def assess_solution_confidence(self, task: Dict, domain: str) -> Tuple[float, Optional[str]]:
        """
        Assess confidence in making an educated guess about the solution.
        
        Returns:
            (confidence: float, educated_guess: str|None)
        
        High confidence (>0.7) means we can make a good guess.
        Low confidence (<0.7) means we should ask directly.
        """
        title = task.get("title", "").lower()
        description = task.get("description", "").lower()

        # Pattern-based guessing
        patterns = {
            # Orderset builds
            r"build.*orderset": (0.8, "Built the orderset with SmartGroups and appropriate defaults"),
            r"fix.*phantom default": (0.9, "Corrected phantom default configuration in OCC"),
            r"configure.*preference": (0.8, "Set up preference list with proper cascading"),
            
            # Interfaces
            r"fix.*provider matching": (0.9, "Fixed provider matching by using NPI instead of internal ID"),
            r"configure.*bridge": (0.7, "Configured Bridge interface with proper field mappings"),
            r"debug.*interface": (0.6, "Debugged interface by checking HL7 message structure"),
            r"fix.*hl7": (0.7, "Fixed HL7 segment ordering or field mapping issue"),
            
            # ClinDoc
            r"create.*template": (0.8, "Created documentation template with appropriate SmartTools"),
            r"fix.*smartphrase": (0.8, "Fixed SmartPhrase syntax or context issues"),
            
            # Cardiac rehab
            r"versacare.*interface": (0.8, "Configured VersaCare telemonitoring data interface"),
            r"scottcare.*interface": (0.8, "Configured ScottCare exercise/monitoring data interface"),
            
            # Workflow
            r"optimize.*workflow": (0.7, "Optimized workflow by reducing clicks and improving defaults"),
            r"configure.*bpa": (0.7, "Configured BPA with appropriate firing logic"),
            
            # Generic fixes
            r"fix.*issue": (0.5, "Troubleshot and resolved the issue"),
            r"resolve.*problem": (0.5, "Identified root cause and implemented fix"),
        }

        combined = f"{title} {description}"
        
        for pattern, (conf, guess) in patterns.items():
            if re.search(pattern, combined):
                return conf, guess

        # Check for domain-specific high-confidence indicators
        domain_patterns = {
            "interfaces": [
                (r"provider.*match", 0.85, "Fixed provider matching configuration"),
                (r"bridge", 0.75, "Configured Bridge interface"),
            ],
            "orderset_builds": [
                (r"orderset", 0.8, "Built/modified orderset configuration"),
                (r"smartset", 0.8, "Configured SmartSet with proper structure"),
            ],
            "cardiac_rehab_integrations": [
                (r"versacare|scottcare", 0.85, "Configured cardiac rehab system interface"),
            ]
        }

        if domain in domain_patterns:
            for pattern, conf, guess in domain_patterns[domain]:
                if re.search(pattern, combined):
                    return conf, guess

        # Low confidence default
        return 0.4, None

    def generate_capture_prompt(
        self,
        task: Dict,
        domain: str,
        confidence: float,
        educated_guess: Optional[str],
        notebook_summary: Optional[str] = None,
    ) -> str:
        """
        Generate appropriate capture prompt based on confidence level.
        
        High confidence: "You solved this by doing X, right?"
        Low confidence: "How'd you solve this one?"
        """
        title = task.get("title", "Unknown task")
        summary_block = f"{notebook_summary}\n\n" if notebook_summary else ""

        if confidence > 0.7 and educated_guess:
            # High confidence - validate guess
            return (
                f"📋 Task closed: \"{title}\"\n\n"
                f"Let me capture this for learning.\n\n"
                f"{summary_block}"
                f"{educated_guess}, right?\n\n"
                f"(Or tell me what you actually did)"
            )
        else:
            # Low confidence - ask directly
            return (
                f"📋 Task closed: \"{title}\"\n\n"
                f"{summary_block}"
                f"How'd you solve this one?"
            )

    def extract_problem_statement(self, task: Dict) -> str:
        """Extract or infer problem statement from task."""
        title = task.get("title", "")
        description = task.get("description", "")

        # If description exists, use it
        if description and len(description) > 20:
            return description

        # Otherwise, infer from title
        problem_patterns = [
            (r"fix (.*)", r"Fixed: \1"),
            (r"resolve (.*)", r"Resolved: \1"),
            (r"debug (.*)", r"Debugged: \1"),
            (r"configure (.*)", r"Configured: \1"),
            (r"build (.*)", r"Built: \1"),
            (r"create (.*)", r"Created: \1"),
        ]

        title_lower = title.lower()
        for pattern, replacement in problem_patterns:
            match = re.search(pattern, title_lower)
            if match:
                return re.sub(pattern, replacement, title_lower).capitalize()

        # Default: use title as-is
        return title

    def build_solution_object(self, task: Dict, domain: str, 
                              solution_approach: str, 
                              validated_guess: bool = False) -> Dict:
        """
        Build solution object for storage.
        
        Args:
            task: WorkOS task data
            domain: Detected Epic domain
            solution_approach: User's explanation or validated guess
            validated_guess: True if this was an educated guess that was confirmed
        """
        problem = self.extract_problem_statement(task)

        solution = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": domain,
            "complexity": self.infer_complexity(task),
            "client": task.get("client", "unknown"),
            "problem": problem,
            "approach": "extracted from task closure",
            "solution": solution_approach,
            "reasoning": "captured from task context",
            "alternatives": [],
            "learnings": "",
            "confidence": "high" if validated_guess else "medium",
            "source": "task_closure_hook",
            "task_id": task.get("id", "unknown"),
            "task_title": task.get("title", ""),
            "validated_guess": validated_guess
        }

        return solution

    def infer_complexity(self, task: Dict) -> int:
        """
        Infer task complexity (1-5) from task data.
        
        Heuristics:
        - Length of description
        - Presence of technical terms
        - Time spent (if available)
        - Priority/urgency
        """
        description = task.get("description", "")
        title = task.get("title", "")

        complexity = 3  # Default medium

        # Length indicator
        if len(description) > 500:
            complexity += 1
        elif len(description) < 100:
            complexity -= 1

        # Technical depth indicators
        technical_terms = [
            "bridge", "hl7", "interface", "segment", "mapping",
            "cascading", "inheritance", "firing logic", "data structure"
        ]
        combined = f"{title} {description}".lower()
        tech_count = sum(1 for term in technical_terms if term in combined)

        if tech_count >= 3:
            complexity += 1
        elif tech_count == 0:
            complexity -= 1

        # Clamp to 1-5
        return max(1, min(5, complexity))

    def store_solution(self, solution: Dict):
        """
        Store solution in all knowledge systems.
        
        Integration points:
        - Memory V2 (searchable facts)
        - Graphiti (decision patterns)
        - Learning state (progress tracking)
        """
        print(f"\n📦 Storing solution from task closure...")

        # Memory V2 integration
        self.store_in_memory_v2(solution)

        # Graphiti integration
        self.store_in_graphiti(solution)

        # Update learning state
        self.update_learning_state(solution)

        print(f"✅ Solution captured from task: {solution['task_title']}")

    def store_in_memory_v2(self, solution: Dict):
        """Store in Memory V2 for semantic search."""
        facts = [
            {
                "content": f"Task: {solution['task_title']}. Problem: {solution['problem']}",
                "tags": ["epic", solution["domain"], "task", solution["client"]],
                "source": f"task_{solution['task_id']}",
                "confidence": 0.85 if solution['confidence'] == 'high' else 0.7
            },
            {
                "content": f"Solution: {solution['solution']}",
                "tags": ["epic", solution["domain"], "solution"],
                "source": f"task_{solution['task_id']}",
                "confidence": 0.85 if solution['confidence'] == 'high' else 0.7
            }
        ]

        # TODO: Integrate with actual Memory V2 API
        # from memory_v2 import store_fact
        # for fact in facts:
        #     store_fact(**fact)

        print(f"  → Memory V2: {len(facts)} facts stored")

    def store_in_graphiti(self, solution: Dict):
        """Store decision patterns in Graphiti."""
        relationships = [
            {
                "subject": "Jeremy",
                "predicate": "completed_task",
                "object": solution["task_title"],
                "context": {
                    "problem": solution["problem"],
                    "solution": solution["solution"],
                    "domain": solution["domain"],
                    "client": solution["client"],
                    "complexity": solution["complexity"],
                    "date": solution["timestamp"]
                }
            }
        ]

        # TODO: Integrate with actual Graphiti API
        # from graphiti import add_relationship
        # for rel in relationships:
        #     add_relationship(**rel)

        print(f"  → Graphiti: {len(relationships)} relationships stored")

    def update_learning_state(self, solution: Dict):
        """Update learning state with task-based capture."""
        domain = solution["domain"]

        if domain not in self.state.get("domains", {}):
            print(f"  ! Warning: Unknown domain '{domain}'")
            return

        # Update domain stats
        domain_state = self.state["domains"][domain]
        domain_state["solutions_captured"] += 1
        domain_state["concepts_learned"] += 1
        domain_state["last_updated"] = solution["timestamp"]

        # Add to recent concepts
        if "recent_concepts" not in domain_state:
            domain_state["recent_concepts"] = []

        domain_state["recent_concepts"].insert(0, {
            "concept": solution["solution"],
            "learned_date": solution["timestamp"].split("T")[0],
            "confidence": solution["confidence"],
            "source": "task_closure"
        })

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

        # Track task closure captures
        if "session_history" not in self.state:
            self.state["session_history"] = {}

        self.state["session_history"]["task_closures_captured"] = \
            self.state["session_history"].get("task_closures_captured", 0) + 1

        self.save_state()
        print(f"  → Learning state updated: {domain} ({domain_state['strength']})")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Epic Task Closure Learning Hook")
    parser.add_argument("--task-id", type=str, help="Task ID to process")
    parser.add_argument("--task-data", type=str, help="Path to JSON file with task data")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Run interactive capture")
    parser.add_argument("--auto-capture", "-a", action="store_true",
                       help="Auto-capture with educated guess")

    args = parser.parse_args()

    hook = TaskClosureHook()

    # Load task data
    task = None
    if args.task_data:
        with open(args.task_data, "r") as f:
            task = json.load(f)
    elif args.task_id:
        # In production, fetch from WorkOS API
        # For now, use mock data
        task = {
            "id": args.task_id,
            "title": "Fix VersaCare provider matching issue",
            "description": "Provider matching failing due to missing NPI in external system",
            "status": "done",
            "client": "KY",
            "tags": ["epic", "interface", "versacare"]
        }
        print(f"📝 Using mock task data for testing")

    if not task:
        print("❌ No task data provided. Use --task-id or --task-data")
        parser.print_help()
        return

    # Detect Epic context
    is_epic, domain, context_confidence = hook.detect_epic_context(task)

    if not is_epic:
        print(f"❌ Task doesn't appear to be Epic-related (confidence: {context_confidence:.0%})")
        return

    print(f"✅ Epic task detected!")
    print(f"   Domain: {domain}")
    print(f"   Confidence: {context_confidence:.0%}")

    # Assess solution confidence
    solution_confidence, educated_guess = hook.assess_solution_confidence(task, domain)

    print(f"\n🤔 Solution confidence: {solution_confidence:.0%}")
    if educated_guess:
        print(f"   Educated guess: {educated_guess}")

    # NotebookLM cross-reference before prompting
    notebook_summary = None
    if args.interactive or solution_confidence <= 0.7:
        notebook_summary = hook.crossref.summarize_for_task(
            task=task,
            domain=domain,
            timeout=120,
        )

    # Generate prompt
    prompt = hook.generate_capture_prompt(
        task,
        domain,
        solution_confidence,
        educated_guess,
        notebook_summary=notebook_summary,
    )
    print(f"\n{prompt}")

    if args.interactive:
        # Interactive mode - get user input
        user_input = input("\n→ Your solution: ")

        # Determine if guess was validated
        validated_guess = False
        if educated_guess and user_input.lower() in ["yes", "y", "yeah", "correct", "right"]:
            solution_approach = educated_guess
            validated_guess = True
        else:
            solution_approach = user_input

        # Build and store solution
        solution = hook.build_solution_object(task, domain, solution_approach, validated_guess)
        hook.store_solution(solution)

    elif args.auto_capture:
        # Auto-capture mode
        if solution_confidence > 0.7 and educated_guess:
            print("\n✅ High confidence - using educated guess")
            solution = hook.build_solution_object(task, domain, educated_guess, validated_guess=True)
            hook.store_solution(solution)
        else:
            print("\n⚠️  Low confidence - should ask user for solution")
            print("   (Use --interactive to provide solution)")


if __name__ == "__main__":
    main()
