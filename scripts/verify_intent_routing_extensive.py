#!/usr/bin/env python3
"""
Extensive Verification of Thanos Intent Routing
Runs 100+ varied natural language queries to stress test the intent router.
"""

import sys
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env")

from Tools.thanos_orchestrator import ThanosOrchestrator

@dataclass
class TestCase:
    message: str
    expected_agent: str
    category: str

# 120+ Test Cases including slang, variations, and potential ambiguities
TEST_CASES = [
    # --- OPS AGENT (Tactical, Calendar, Inbox) ---
    TestCase("What is on the docket today?", "ops", "calendar"),
    TestCase("Do I have anything coming up?", "ops", "calendar"),
    TestCase("Am I free at 2pm?", "ops", "calendar"),
    TestCase("Check my availability", "ops", "calendar"),
    TestCase("What is my schedule looking like?", "ops", "calendar"),
    TestCase("Any meetings today?", "ops", "calendar"),
    TestCase("List my appointments", "ops", "calendar"),
    TestCase("Whats next?", "ops", "planning"),
    TestCase("What needs to be done?", "ops", "planning"),
    TestCase("Gimme a plan", "ops", "planning"),
    TestCase("Organize my life", "ops", "planning"),
    TestCase("I need to sort out my tasks", "ops", "planning"),
    TestCase("Triage my inbox", "ops", "inbox"),
    TestCase("Process my email", "ops", "inbox"),
    TestCase("Clean up my todos", "ops", "planning"),
    TestCase("Add buy milk to the list", "ops", "tasks"),
    TestCase("Remind me to call mom", "ops", "tasks"),
    TestCase("I forgot what I have to do", "ops", "planning"),
    TestCase("Help me figure out my day", "ops", "planning"),
    TestCase("Where should I start?", "ops", "planning"),
    TestCase("I have too many tabs open", "ops", "tactical"),
    TestCase("I feel disorganized", "ops", "tactical"),
    TestCase("Structure my afternoon", "ops", "planning"),
    TestCase("What are my deadlines?", "ops", "tasks"),
    TestCase("What is due soon?", "ops", "tasks"),
    TestCase("Show me the calendar", "ops", "calendar"),
    TestCase("When is my next break?", "ops", "calendar"),
    TestCase("Do I have time for lunch?", "ops", "calendar"),
    TestCase("What commitments did I make?", "ops", "tasks"),
    TestCase("Review my open loops", "ops", "tasks"),

    # --- COACH AGENT (Motivation, Patterns, Accountability) ---
    TestCase("I keep procrastinating", "coach", "patterns"),
    TestCase("Why am I avoiding this?", "coach", "patterns"),
    TestCase("I am wasting time", "coach", "patterns"),
    TestCase("Kick my butt", "coach", "accountability"),
    TestCase("I need a push", "coach", "motivation"),
    TestCase("I'm feeling lazy", "coach", "motivation"),
    TestCase("I can't get started", "coach", "blockers"),
    TestCase("Why do I always do this?", "coach", "patterns"),
    TestCase("Analyze my habits", "coach", "patterns"),
    TestCase("Am I being consistent?", "coach", "habits"),
    TestCase("I broke my streak", "coach", "habits"),
    TestCase("I am stuck in a rut", "coach", "patterns"),
    TestCase("Help me focus", "coach", "distraction"), # Could be Health OR Coach
    TestCase("I keep getting distracted by youtube", "coach", "distraction"),
    TestCase("Hold me to this", "coach", "accountability"),
    TestCase("Call me out if I fail", "coach", "accountability"),
    TestCase("I'm self-sabotaging again", "coach", "patterns"),
    TestCase("Why is discipline so hard?", "coach", "discipline"),
    TestCase("I need to be more disciplined", "coach", "discipline"),
    TestCase("Motivate me", "coach", "motivation"),
    TestCase("Give me a pep talk", "coach", "motivation"),
    TestCase("I feel like giving up", "coach", "motivation"),
    TestCase("I'm making excuses", "coach", "accountability"),
    TestCase("This is a bad habit", "coach", "habits"),
    TestCase("I want to build better habits", "coach", "habits"),
    TestCase("Why am I failing at this?", "coach", "patterns"),
    TestCase("Review my behavior", "coach", "patterns"),
    TestCase("Am I lying to myself?", "coach", "accountability"),
    
    # --- STRATEGY AGENT (Big Picture, Business, Long-term) ---
    TestCase("What is the 5 year plan?", "strategy", "vision"),
    TestCase("Where is this all going?", "strategy", "vision"),
    TestCase("Should I quit my job?", "strategy", "decision"),
    TestCase("Is this business viable?", "strategy", "business"),
    TestCase("How do I grow revenue?", "strategy", "business"),
    TestCase("What is the ROI?", "strategy", "business"),
    TestCase("Analyze the market", "strategy", "business"),
    TestCase("What are my quarterly objectives?", "strategy", "goals"),
    TestCase("Am I focusing on the right things long term?", "strategy", "vision"),
    TestCase("Should I take this opportunity?", "strategy", "decision"),
    TestCase("Weigh the pros and cons", "strategy", "decision"),
    TestCase("What is the tradeoff?", "strategy", "decision"),
    TestCase("Is it worth the effort?", "strategy", "decision"),
    TestCase("Help me make a big decision", "strategy", "decision"),
    TestCase("Review my annual goals", "strategy", "goals"),
    TestCase("Strategic planning session", "strategy", "strategy"),
    TestCase("Roadmap for Q4", "strategy", "planning"),
    TestCase("Vision board", "strategy", "vision"),
    TestCase("Mission statement", "strategy", "vision"),
    TestCase("Am I on the right track?", "strategy", "vision"),
    TestCase("Should I hire a developer?", "strategy", "decision"),
    TestCase("Cost benefit analysis", "strategy", "decision"),
    TestCase("What is my north star?", "strategy", "vision"),
    TestCase("How do I scale?", "strategy", "business"),
    TestCase("Think big picture", "strategy", "big_picture"),
    
    # --- HEALTH AGENT (Energy, Sleep, Meds, Physiology) ---
    TestCase("I am exhausted", "health", "energy"),
    TestCase("I feel drained", "health", "energy"),
    TestCase("My brain is frying", "health", "energy"),
    TestCase("Brain fog", "health", "focus"),
    TestCase("I have a headache", "health", "physical"),
    TestCase("Did I take my pills?", "health", "meds"),
    TestCase("Should I take vyvanse?", "health", "meds"),
    TestCase("I slept terrible", "health", "sleep"),
    TestCase("I'm not sleeping", "health", "sleep"),
    TestCase("Insomnia again", "health", "sleep"),
    TestCase("I need to workout", "health", "exercise"),
    TestCase("Did I exercise today?", "health", "exercise"),
    TestCase("I'm burnt out", "health", "burnout"),
    TestCase("Burnout warning", "health", "burnout"),
    TestCase("My energy crashed", "health", "energy"),
    TestCase("I can't think straight", "health", "focus"),
    TestCase("I need caffeine", "health", "energy"),
    TestCase("Should I drink coffee?", "health", "energy"),
    TestCase("My focus is shot", "health", "focus"),
    TestCase("Maintain focus", "health", "focus"),
    TestCase("I am hungry", "health", "physical"),
    TestCase("Time for a break", "health", "recovery"),
    TestCase("I need to rest", "health", "recovery"),
    TestCase("My meds aren't working", "health", "meds"),
    TestCase("Supplements review", "health", "meds"),
    TestCase("Physiological state", "health", "physical"),
    TestCase("I feel weak", "health", "physical"),
]

def run_stress_test():
    print(f"Initializing Thanos Orchestrator...")
    thanos = ThanosOrchestrator(base_dir=str(project_root))
    
    print(f"Running {len(TEST_CASES)} stress test cases...\n")
    
    passed = 0
    failed = 0
    failures = []
    
    results_by_agent = {"ops": [], "coach": [], "strategy": [], "health": []}
    
    for case in TEST_CASES:
        agent = thanos.find_agent(case.message)
        result_name = agent.name.lower() if agent else "none"
        
        # Heuristic: Coach/Health and Ops/Strategy can sometimes overlap.
        # Strict checking for now.
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
        lines = results_by_agent.get(agent_name, [])
        if not lines:
            print("  (No tests for this agent)")
        for line in lines:
            print(line)
            
    print("\n" + "="*40)
    print(f"STRESS TEST SUMMARY: {passed} Passed, {failed} Failed")
    print("="*40)
    
    if failures:
        print("\nFAILURES LIST:")
        for case, result in failures:
            print(f"- \"{case.message}\" routed to [{result}] instead of [{case.expected_agent}]")
        sys.exit(1)
    else:
        print("\nAll stress tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    run_stress_test()
