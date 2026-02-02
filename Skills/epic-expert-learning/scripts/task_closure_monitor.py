#!/usr/bin/env python3
"""
Epic Expert Learning - WorkOS Task Closure Monitor

Monitors WorkOS for task completions and automatically captures Epic learnings.
Can run as:
  1. Event handler (called by webhook)
  2. Polling monitor (checks periodically)
  3. Single task processor (one-off capture)

Usage:
    # Process single task (webhook/event handler)
    python task_closure_monitor.py --task-id <id>
    
    # Process task from JSON (webhook payload)
    python task_closure_monitor.py --task-json '{"id": "...", "title": "..."}'
    
    # Monitor mode (poll WorkOS API)
    python task_closure_monitor.py --monitor --interval 300
    
    # Check specific task interactively
    python task_closure_monitor.py --task-id <id> --interactive
"""

import json
import os
import sys
import time
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

# Paths
SKILL_DIR = Path(__file__).parent.parent
STATE_FILE = SKILL_DIR / "references" / "learning-state.json"
CAPTURE_SCRIPT = SKILL_DIR / "scripts" / "capture_solution.py"


class TaskClosureMonitor:
    """Monitors WorkOS tasks and captures Epic learnings automatically."""

    def __init__(self):
        self.state = self.load_state()
        self.epic_patterns = self.build_epic_patterns()
        self.solution_patterns = self.build_solution_patterns()
        
    def load_state(self) -> Dict:
        """Load learning state."""
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {}
    
    def save_state(self):
        """Save learning state."""
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def build_epic_patterns(self) -> Dict:
        """
        Build Epic detection patterns.
        
        Returns patterns for:
        - Client detection
        - Title keywords
        - Tag indicators
        - Domain classification
        """
        return {
            "client_indicators": [
                "epic", "ky", "kentucky", "versacare", "scottcare",
                "emr", "ehr"
            ],
            "title_keywords": [
                # Interfaces
                "interface", "hl7", "bridge", "provider matching", 
                "versacare", "scottcare", "adt", "orm", "oru",
                # Ordersets
                "orderset", "order set", "smartset", "quick list",
                "preference", "panel", "redirector", "occ",
                # ClinDoc
                "smartphrase", "smarttext", "template", "clindoc",
                "flowsheet", "navigator", "documentation",
                # Workflow
                "bpa", "workflow", "optimization", "best practice",
                # Cutover
                "cutover", "go-live", "migration", "validation",
                # General Epic
                "epic", "build", "configure"
            ],
            "tag_indicators": [
                "epic", "interface", "orderset", "clindoc", "hl7",
                "integration", "emr", "ehr"
            ],
            "domain_keywords": {
                "interfaces": [
                    "interface", "hl7", "bridge", "provider matching",
                    "adt", "orm", "oru", "mapping", "integration",
                    "versacare", "scottcare"
                ],
                "orderset_builds": [
                    "orderset", "order set", "smartset", "quick list",
                    "preference", "panel", "redirector", "occ"
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

    def build_solution_patterns(self) -> List[Dict]:
        """
        Build solution guess patterns based on task titles/descriptions.
        
        Each pattern has:
        - regex: Pattern to match
        - confidence: How confident we are (0-1)
        - solution: Educated guess
        - domain: Epic domain
        """
        return [
            # INTERFACES - High confidence
            {
                "regex": r"fix.*provider matching",
                "confidence": 0.90,
                "solution": "Fixed provider matching by using NPI instead of internal ID",
                "domain": "interfaces",
                "reasoning": "External systems typically lack Epic internal IDs"
            },
            {
                "regex": r"configure.*versacare.*interface",
                "confidence": 0.85,
                "solution": "Configured VersaCare telemonitoring data interface",
                "domain": "cardiac_rehab_integrations",
                "reasoning": "Standard VersaCare integration setup"
            },
            {
                "regex": r"configure.*scottcare.*interface",
                "confidence": 0.85,
                "solution": "Configured ScottCare exercise/monitoring data interface",
                "domain": "cardiac_rehab_integrations",
                "reasoning": "Standard ScottCare integration setup"
            },
            {
                "regex": r"fix.*hl7",
                "confidence": 0.75,
                "solution": "Fixed HL7 segment ordering or field mapping issue",
                "domain": "interfaces",
                "reasoning": "Common HL7 integration problems"
            },
            {
                "regex": r"configure.*bridge",
                "confidence": 0.75,
                "solution": "Configured Bridge interface with proper field mappings",
                "domain": "interfaces",
                "reasoning": "Standard Bridge configuration workflow"
            },
            {
                "regex": r"debug.*interface",
                "confidence": 0.65,
                "solution": "Debugged interface by checking message structure and routing",
                "domain": "interfaces",
                "reasoning": "Common interface troubleshooting approach"
            },
            
            # ORDERSET BUILDS - Medium-high confidence
            {
                "regex": r"build.*orderset",
                "confidence": 0.80,
                "solution": "Built orderset with SmartGroups and appropriate defaults",
                "domain": "orderset_builds",
                "reasoning": "Standard orderset build approach"
            },
            {
                "regex": r"fix.*phantom default",
                "confidence": 0.90,
                "solution": "Corrected phantom default configuration in OCC",
                "domain": "orderset_builds",
                "reasoning": "Specific known issue with phantom defaults"
            },
            {
                "regex": r"configure.*preference",
                "confidence": 0.80,
                "solution": "Set up preference list with proper cascading logic",
                "domain": "orderset_builds",
                "reasoning": "Standard preference list configuration"
            },
            {
                "regex": r"(create|build).*smartset",
                "confidence": 0.80,
                "solution": "Created SmartSet with organized sections and order groups",
                "domain": "orderset_builds",
                "reasoning": "Standard SmartSet build process"
            },
            
            # CLINDOC - Medium confidence
            {
                "regex": r"create.*template",
                "confidence": 0.80,
                "solution": "Created documentation template with appropriate SmartTools",
                "domain": "clindoc_configuration",
                "reasoning": "Standard template creation workflow"
            },
            {
                "regex": r"fix.*smartphrase",
                "confidence": 0.80,
                "solution": "Fixed SmartPhrase syntax or context configuration",
                "domain": "clindoc_configuration",
                "reasoning": "Common SmartPhrase issues"
            },
            {
                "regex": r"configure.*flowsheet",
                "confidence": 0.75,
                "solution": "Configured flowsheet rows and columns for discrete data entry",
                "domain": "clindoc_configuration",
                "reasoning": "Standard flowsheet setup"
            },
            
            # WORKFLOW - Medium confidence
            {
                "regex": r"optimize.*workflow",
                "confidence": 0.70,
                "solution": "Optimized workflow by reducing clicks and improving defaults",
                "domain": "workflow_optimization",
                "reasoning": "Common workflow optimization approach"
            },
            {
                "regex": r"configure.*bpa",
                "confidence": 0.75,
                "solution": "Configured BPA with appropriate firing logic and suppression rules",
                "domain": "workflow_optimization",
                "reasoning": "Standard BPA configuration"
            },
            
            # CUTOVER - Medium confidence
            {
                "regex": r"cutover",
                "confidence": 0.70,
                "solution": "Executed cutover procedures with validation checklist",
                "domain": "cutover_procedures",
                "reasoning": "Standard cutover workflow"
            },
            
            # GENERIC - Low confidence (ask instead)
            {
                "regex": r"fix.*issue",
                "confidence": 0.50,
                "solution": None,  # Too generic - ask directly
                "domain": None,
                "reasoning": "Generic fix - need more details"
            },
            {
                "regex": r"resolve.*problem",
                "confidence": 0.50,
                "solution": None,
                "domain": None,
                "reasoning": "Generic resolution - need more details"
            }
        ]

    def is_epic_task(self, task: Dict) -> Tuple[bool, float]:
        """
        Determine if task is Epic-related.
        
        Returns:
            (is_epic: bool, confidence: float)
        """
        title = task.get("title", "").lower()
        description = task.get("description", "").lower()
        tags = [tag.lower() for tag in task.get("tags", [])]
        client = task.get("client", "").lower()
        
        combined = f"{title} {description} {client} {' '.join(tags)}"
        
        confidence = 0.0
        
        # Check client indicators (high weight)
        for indicator in self.epic_patterns["client_indicators"]:
            if indicator in combined:
                confidence = max(confidence, 0.9)
        
        # Check title keywords (medium-high weight)
        for keyword in self.epic_patterns["title_keywords"]:
            if keyword in title:
                confidence = max(confidence, 0.85)
            elif keyword in combined:
                confidence = max(confidence, 0.65)
        
        # Check tag indicators (medium weight)
        for indicator in self.epic_patterns["tag_indicators"]:
            if indicator in tags:
                confidence = max(confidence, 0.75)
        
        is_epic = confidence > 0.6
        
        return is_epic, confidence

    def classify_domain(self, task: Dict) -> Tuple[Optional[str], float]:
        """
        Classify task into Epic domain.
        
        Returns:
            (domain: str|None, confidence: float)
        """
        title = task.get("title", "").lower()
        description = task.get("description", "").lower()
        combined = f"{title} {description}"
        
        domain_scores = {}
        
        for domain, keywords in self.epic_patterns["domain_keywords"].items():
            score = 0
            for keyword in keywords:
                if keyword in title:
                    score += 3  # Title = strong signal
                elif keyword in description:
                    score += 2  # Description = medium signal
                elif keyword in combined:
                    score += 1  # Other = weak signal
            
            if score > 0:
                domain_scores[domain] = score
        
        if not domain_scores:
            return None, 0.0
        
        best_domain = max(domain_scores.items(), key=lambda x: x[1])
        domain = best_domain[0]
        
        # Convert score to confidence
        max_possible_score = len(self.epic_patterns["domain_keywords"][domain]) * 3
        confidence = min(1.0, best_domain[1] / max_possible_score)
        
        return domain, confidence

    def guess_solution(self, task: Dict) -> Tuple[Optional[str], float, Optional[str]]:
        """
        Make educated guess about solution based on task title/description.
        
        Returns:
            (solution: str|None, confidence: float, domain: str|None)
        """
        title = task.get("title", "").lower()
        description = task.get("description", "").lower()
        combined = f"{title} {description}"
        
        # Check solution patterns
        for pattern in self.solution_patterns:
            if re.search(pattern["regex"], combined):
                return (
                    pattern["solution"],
                    pattern["confidence"],
                    pattern["domain"]
                )
        
        # No pattern match
        return None, 0.0, None

    def format_capture_prompt(self, task: Dict, solution_guess: Optional[str], 
                              confidence: float) -> str:
        """
        Format prompt for Jeremy based on confidence level.
        
        High confidence: "You did X, right?"
        Low confidence: "How'd you solve this?"
        """
        title = task.get("title", "")
        
        if confidence > 0.7 and solution_guess:
            return (
                f"📋 Task closed: \"{title}\"\n\n"
                f"Let me capture this for learning.\n\n"
                f"{solution_guess}, right?\n\n"
                f"(Or tell me what you actually did)"
            )
        else:
            return (
                f"📋 Task closed: \"{title}\"\n\n"
                f"How'd you solve this one?"
            )

    def capture_via_script(self, task: Dict, solution: str, 
                          domain: str, confidence: str) -> bool:
        """
        Capture solution by calling capture_solution.py.
        
        Args:
            task: Task data
            solution: Solution text
            domain: Epic domain
            confidence: "high" or "medium"
        
        Returns:
            bool: Success status
        """
        # Build capture data
        capture_data = {
            "problem": task.get("title", ""),
            "approach": f"From task closure: {task.get('description', '')[:100]}",
            "solution": solution,
            "reasoning": "Captured from WorkOS task completion",
            "alternatives": [],
            "learnings": "",
            "domain": domain,
            "complexity": self._infer_complexity(task),
            "client": task.get("client", "unknown"),
            "confidence": confidence,
            "source": "task_closure_monitor",
            "task_id": task.get("id", "unknown")
        }
        
        # Store via capture_solution integration
        return self._store_solution(capture_data)

    def _infer_complexity(self, task: Dict) -> int:
        """Infer task complexity (1-5) from task data."""
        description = task.get("description", "")
        title = task.get("title", "")
        
        complexity = 3  # Default medium
        
        # Length indicator
        if len(description) > 500:
            complexity += 1
        elif len(description) < 100:
            complexity -= 1
        
        # Technical terms
        technical_terms = [
            "bridge", "hl7", "interface", "segment", "mapping",
            "cascading", "inheritance", "firing logic"
        ]
        combined = f"{title} {description}".lower()
        tech_count = sum(1 for term in technical_terms if term in combined)
        
        if tech_count >= 3:
            complexity += 1
        elif tech_count == 0:
            complexity -= 1
        
        return max(1, min(5, complexity))

    def _store_solution(self, solution_data: Dict) -> bool:
        """
        Store solution in learning state.
        
        This mimics what capture_solution.py does.
        """
        try:
            domain = solution_data["domain"]
            
            if domain not in self.state.get("domains", {}):
                print(f"  ! Unknown domain: {domain}")
                return False
            
            # Update domain stats
            domain_state = self.state["domains"][domain]
            domain_state["solutions_captured"] = domain_state.get("solutions_captured", 0) + 1
            domain_state["concepts_learned"] = domain_state.get("concepts_learned", 0) + 1
            domain_state["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Add to recent concepts
            if "recent_concepts" not in domain_state:
                domain_state["recent_concepts"] = []
            
            domain_state["recent_concepts"].insert(0, {
                "concept": solution_data["solution"],
                "learned_date": datetime.now(timezone.utc).date().isoformat(),
                "confidence": solution_data["confidence"],
                "source": "task_closure"
            })
            
            domain_state["recent_concepts"] = domain_state["recent_concepts"][:5]
            
            # Update strength
            concepts = domain_state["concepts_learned"]
            if concepts >= 51:
                domain_state["strength"] = "expert"
            elif concepts >= 31:
                domain_state["strength"] = "advanced"
            elif concepts >= 16:
                domain_state["strength"] = "intermediate"
            elif concepts >= 6:
                domain_state["strength"] = "beginner"
            else:
                domain_state["strength"] = "novice"
            
            # Update global stats
            if "global_stats" in self.state:
                self.state["global_stats"]["total_solutions_captured"] = \
                    self.state["global_stats"].get("total_solutions_captured", 0) + 1
                self.state["global_stats"]["total_concepts_learned"] = \
                    self.state["global_stats"].get("total_concepts_learned", 0) + 1
            
            # Update session history
            if "session_history" not in self.state:
                self.state["session_history"] = {}
            
            self.state["session_history"]["task_closures_captured"] = \
                self.state["session_history"].get("task_closures_captured", 0) + 1
            self.state["session_history"]["last_task_closure_timestamp"] = \
                datetime.now(timezone.utc).isoformat()
            
            self.save_state()
            
            print(f"  ✅ Captured: {domain} ({domain_state['strength']}, {concepts} concepts)")
            return True
            
        except Exception as e:
            print(f"  ❌ Error storing solution: {e}")
            return False

    def process_task(self, task: Dict, interactive: bool = False) -> Dict:
        """
        Process a single task completion.
        
        Args:
            task: Task data
            interactive: If True, wait for user input
        
        Returns:
            Processing result dict
        """
        result = {
            "task_id": task.get("id"),
            "task_title": task.get("title"),
            "is_epic": False,
            "captured": False,
            "confidence": 0.0,
            "solution": None,
            "domain": None
        }
        
        # Check if Epic task
        is_epic, epic_confidence = self.is_epic_task(task)
        result["is_epic"] = is_epic
        result["epic_confidence"] = epic_confidence
        
        if not is_epic:
            print(f"❌ Not Epic-related: \"{task.get('title', 'Unknown')}\"")
            return result
        
        print(f"✅ Epic task detected: \"{task.get('title', 'Unknown')}\"")
        print(f"   Epic confidence: {epic_confidence:.0%}")
        
        # Classify domain
        domain, domain_confidence = self.classify_domain(task)
        result["domain"] = domain
        result["domain_confidence"] = domain_confidence
        
        if domain:
            print(f"   Domain: {domain} (confidence: {domain_confidence:.0%})")
        
        # Guess solution
        solution_guess, solution_confidence, solution_domain = self.guess_solution(task)
        result["confidence"] = solution_confidence
        result["solution_guess"] = solution_guess
        
        # Use solution domain if available, otherwise use classified domain
        capture_domain = solution_domain or domain or "workflow_optimization"
        
        if solution_confidence > 0.7 and solution_guess:
            print(f"   Solution confidence: {solution_confidence:.0%} (HIGH)")
            print(f"   Educated guess: {solution_guess}")
        else:
            print(f"   Solution confidence: {solution_confidence:.0%} (LOW)")
            print(f"   Will ask directly")
        
        # Format prompt
        prompt = self.format_capture_prompt(task, solution_guess, solution_confidence)
        result["prompt"] = prompt
        
        print(f"\n{prompt}\n")
        
        if interactive:
            # Get user input
            user_input = input("→ Your solution: ").strip()
            
            if not user_input:
                print("⚠️  No solution provided, skipping capture")
                return result
            
            # Check if validating guess or providing new solution
            if solution_guess and user_input.lower() in ["yes", "y", "yeah", "correct", "right", "yep"]:
                final_solution = solution_guess
                confidence = "high"
                print("✅ Guess validated!")
            else:
                final_solution = user_input
                confidence = "medium"
            
            # Capture solution
            success = self.capture_via_script(
                task=task,
                solution=final_solution,
                domain=capture_domain,
                confidence=confidence
            )
            
            result["captured"] = success
            result["solution"] = final_solution
            
        else:
            # Non-interactive: auto-capture high confidence only
            if solution_confidence > 0.7 and solution_guess:
                print("🤖 Auto-capturing (high confidence)...")
                success = self.capture_via_script(
                    task=task,
                    solution=solution_guess,
                    domain=capture_domain,
                    confidence="high"
                )
                result["captured"] = success
                result["solution"] = solution_guess
            else:
                print("⚠️  Low confidence - requires user input (use --interactive)")
        
        return result

    def fetch_completed_tasks(self, since: Optional[datetime] = None) -> List[Dict]:
        """
        Fetch completed tasks from WorkOS API.
        
        Args:
            since: Only fetch tasks completed after this time
        
        Returns:
            List of task dicts
        """
        # TODO: Implement actual WorkOS API integration
        # For now, return empty list (placeholder)
        print("⚠️  WorkOS API integration not implemented yet")
        print("   Use --task-id or --task-json for manual processing")
        return []

    def monitor_loop(self, interval: int = 300):
        """
        Continuous monitoring loop.
        
        Args:
            interval: Check interval in seconds (default: 5 minutes)
        """
        print(f"🔍 Starting monitor loop (checking every {interval}s)")
        print("   Press Ctrl+C to stop\n")
        
        last_check = datetime.now(timezone.utc) - timedelta(seconds=interval)
        
        try:
            while True:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking for completed tasks...")
                
                # Fetch tasks completed since last check
                tasks = self.fetch_completed_tasks(since=last_check)
                
                if tasks:
                    print(f"   Found {len(tasks)} completed task(s)")
                    
                    for task in tasks:
                        print(f"\n{'='*60}")
                        self.process_task(task, interactive=False)
                else:
                    print("   No new completed tasks")
                
                last_check = datetime.now(timezone.utc)
                
                # Wait for next check
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Monitor stopped")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="WorkOS Task Closure Monitor for Epic Learning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single task interactively
  python task_closure_monitor.py --task-id task_abc123 --interactive
  
  # Process task from webhook JSON
  python task_closure_monitor.py --task-json '{"id": "task_123", "title": "Fix interface"}'
  
  # Monitor mode (poll every 5 minutes)
  python task_closure_monitor.py --monitor --interval 300
  
  # Process task automatically (high confidence only)
  python task_closure_monitor.py --task-id task_abc123
        """
    )
    
    parser.add_argument("--task-id", type=str, help="Process specific task by ID")
    parser.add_argument("--task-json", type=str, help="Process task from JSON string")
    parser.add_argument("--monitor", action="store_true", help="Run in monitoring mode")
    parser.add_argument("--interval", type=int, default=300, 
                       help="Monitor check interval in seconds (default: 300)")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Interactive mode (ask for user input)")
    
    args = parser.parse_args()
    
    monitor = TaskClosureMonitor()
    
    if args.monitor:
        # Monitoring mode
        monitor.monitor_loop(interval=args.interval)
        
    elif args.task_json:
        # Process from JSON
        try:
            task = json.loads(args.task_json)
            monitor.process_task(task, interactive=args.interactive)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            sys.exit(1)
            
    elif args.task_id:
        # Process single task (mock data for testing)
        print(f"📝 Fetching task: {args.task_id}")
        print("   (Using mock data for testing - implement WorkOS API fetch)\n")
        
        # Mock task data
        task = {
            "id": args.task_id,
            "title": "Fix VersaCare provider matching issue",
            "description": "Provider matching failing due to missing NPI in external system",
            "status": "done",
            "client": "KY",
            "tags": ["epic", "interface", "versacare"],
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        
        monitor.process_task(task, interactive=args.interactive)
        
    else:
        parser.print_help()
        print("\n❌ Error: Must specify --task-id, --task-json, or --monitor")
        sys.exit(1)


if __name__ == "__main__":
    main()
