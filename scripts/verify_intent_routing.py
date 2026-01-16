#!/usr/bin/env python3
"""
Verify Thanos Intent Routing
Runs a comprehensive set of natural language queries to test the accuracy of the intent router.
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Tools.thanos_orchestrator import ThanosOrchestrator

@dataclass
class TestCase:
    message: str
    expected_agent: str
    category: str

TEST_CASES = [
    # --- OPS AGENT (Tactical, Planning, Calendar, Tasks) ---
    TestCase("What should I do today?", "ops", "planning"),
    TestCase("Help me plan my day", "ops", "planning"),
    TestCase("I have so much to do", "ops", "planning"),
    TestCase("What is on my calendar?", "ops", "calendar"),
    TestCase("Do I have any meetings?", "ops", "calendar"),
    TestCase("Show my schedule", "ops", "calendar"),
    TestCase("Add a task to buy milk", "ops", "tasks"),
    TestCase("Remind me to call John", "ops", "tasks"),
    TestCase("What are my deadlines?", "ops", "tasks"),
    TestCase("I'm overwhelmed with work", "ops", "emotional_tactical"),
    TestCase("Too many emails", "ops", "tasks"),
    TestCase("Clear my inbox", "ops", "tasks"),
    TestCase("What is my next action?", "ops", "planning"),
    TestCase("Prioritize my list", "ops", "planning"),
    TestCase("When am I free?", "ops", "calendar"),
    
    # --- COACH AGENT (Motivation, Habits, Accountability, Patterns) ---
    TestCase("I don't feel like working", "coach", "motivation"),
    TestCase("Why do I keep procrastinating?", "coach", "patterns"),
    TestCase("I'm stuck on this problem", "coach", "blockers"),
    TestCase("I need some motivation", "coach", "motivation"),
    TestCase("Help me stick to my habits", "coach", "habits"),
    TestCase("I failed to workout again", "coach", "habits"),
    TestCase("Why can't I focus?", "coach", "patterns"),
    TestCase("I keep getting distracted", "coach", "patterns"),
    TestCase("Hold me accountable", "coach", "accountability"),
    TestCase("I'm making excuses", "coach", "accountability"),
    TestCase("Analyze my behavior", "coach", "patterns"),
    TestCase("I'm self-sabotaging", "coach", "patterns"),
    TestCase("I need a pep talk", "coach", "motivation"),
    
    # --- STRATEGY AGENT (Long-term, Business, Big Picture) ---
    TestCase("What are my quarterly goals?", "strategy", "goals"),
    TestCase("Review my long-term strategy", "strategy", "strategy"),
    TestCase("Should I pivot my business?", "strategy", "decision"),
    TestCase("Is this project worth it?", "strategy", "decision"),
    TestCase("Where do I want to be in 5 years?", "strategy", "vision"),
    TestCase("Analyze the tradeoffs", "strategy", "decision"),
    TestCase("What is the big picture?", "strategy", "vision"),
    TestCase("Planning for next year", "strategy", "planning"),
    TestCase("Revenue growth ideas", "strategy", "business"),
    TestCase("Should I hire someone?", "strategy", "decision"),
    TestCase("Evaluate this opportunity", "strategy", "decision"),
    TestCase("Am I on the right track?", "strategy", "vision"),
    
    # --- HEALTH AGENT (Energy, Sleep, Meds, Focus) ---
    TestCase("I'm so tired", "health", "energy"),
    TestCase("I didn't sleep well", "health", "sleep"),
    TestCase("My energy is low", "health", "energy"),
    TestCase("Should I take my meds?", "health", "meds"),
    TestCase("I crashed this afternoon", "health", "energy"),
    TestCase("I can't concentrate", "health", "focus"),
    TestCase("Brain fog is bad today", "health", "focus"),
    TestCase("I need a break", "health", "energy"),
    TestCase("Did I workout?", "health", "exercise"),
    TestCase("I'm feeling burnt out", "health", "energy"),
    TestCase("My vyvanse isn't working", "health", "meds"),
    TestCase("I'm exhausted", "health", "energy"),
]

def run_tests():
    print(f"Initializing Thanos Orchestrator...")
    thanos = ThanosOrchestrator(base_dir=str(project_root))
    
    print(f"Running {len(TEST_CASES)} test cases...\n")
    
    passed = 0
    failed = 0
    failures = []
    
    # Group output by agent for better readability
    results_by_agent = {"ops": [], "coach": [], "strategy": [], "health": []}
    
    for case in TEST_CASES:
        agent = thanos.find_agent(case.message)
        result_name = agent.name.lower() if agent else "none"
        
        is_pass = result_name == case.expected_agent
        if is_pass:
            passed += 1
            results_by_agent[case.expected_agent].append(f"  ✓ {case.message}")
        else:
            failed += 1
            fail_msg = f"  ✗ {case.message} -> Got: {result_name} (Expected: {case.expected_agent})"
            results_by_agent[case.expected_agent].append(fail_msg)
            failures.append((case, result_name))

    # Print results
    for agent_name in ["ops", "coach", "strategy", "health"]:
        print(f"\n--- {agent_name.upper()} ---")
        for line in results_by_agent.get(agent_name, []):
            print(line)
            
    print("\n" + "="*40)
    print(f"SUMMARY: {passed} Passed, {failed} Failed")
    print("="*40)
    
    if failures:
        print("\nFAILURES LIST:")
        for case, result in failures:
            print(f"- \"{case.message}\" routed to [{result}] instead of [{case.expected_agent}]")
            
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
