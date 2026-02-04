#!/usr/bin/env python3
"""
Epic Expert Learning - Targeted Questioning Workflow

Context-aware question generation to learn from Jeremy during Epic work sessions.
Respects timing constraints and knowledge gaps to ask relevant, non-intrusive questions.

Usage:
    python ask_question.py --context "User is working on orderset builds"
    python ask_question.py --suggest-question
"""

import json
import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Paths
SKILL_DIR = Path(__file__).parent.parent
STATE_FILE = SKILL_DIR / "references" / "learning-state.json"

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from openai_rag_crossref import OpenAIRagCrossRef


class QuestionAsker:
    """Handles context-aware question generation and timing."""

    def __init__(self):
        self.state = self.load_state()
        self.question_bank = self.load_question_bank()
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

    def load_question_bank(self) -> Dict[str, List[Dict]]:
        """
        Question bank organized by domain and knowledge gap.
        
        Each question has:
        - question: The actual question text
        - targets: Knowledge gaps it addresses
        - follow_ups: Potential follow-up questions
        - priority: How important this question is (1-5)
        """
        return {
            "orderset_builds": [
                {
                    "question": "When do you use redirector sections vs direct ordering in ordersets?",
                    "targets": ["redirector sections", "orderset structure"],
                    "follow_ups": ["What are common pitfalls with redirectors?"],
                    "priority": 4
                },
                {
                    "question": "How do phantom defaults in OCC interact with user selections?",
                    "targets": ["phantom defaults", "OCC behavior"],
                    "follow_ups": ["Can you override phantom defaults?"],
                    "priority": 5
                },
                {
                    "question": "What's the difference between SmartSet and Quick List in practice?",
                    "targets": ["SmartSet", "Quick List", "orderset types"],
                    "follow_ups": ["When do you choose one over the other?"],
                    "priority": 3
                },
                {
                    "question": "How does preference list cascading work (system → dept → provider)?",
                    "targets": ["preference list cascading logic"],
                    "follow_ups": ["What causes cascading to break?"],
                    "priority": 4
                }
            ],
            "interfaces": [
                {
                    "question": "Why does provider matching fail so often in interfaces?",
                    "targets": ["provider matching", "identifier mismatches"],
                    "follow_ups": ["How do you troubleshoot provider matching issues?"],
                    "priority": 5
                },
                {
                    "question": "What's the difference between using NPI vs internal Epic ID for provider matching?",
                    "targets": ["provider matching: NPI vs internal ID"],
                    "follow_ups": ["When do external systems lack Epic IDs?"],
                    "priority": 4
                },
                {
                    "question": "How do you configure a Bridge interface from scratch?",
                    "targets": ["Bridges configuration workflow"],
                    "follow_ups": ["What are common Bridge configuration mistakes?"],
                    "priority": 5
                },
                {
                    "question": "Why does HL7 segment ordering matter?",
                    "targets": ["HL7 segment ordering rules"],
                    "follow_ups": ["Which parsers are sensitive to segment order?"],
                    "priority": 3
                }
            ],
            "clindoc_configuration": [
                {
                    "question": "How do SmartTexts pull in patient-specific data?",
                    "targets": ["SmartText syntax and patient data"],
                    "follow_ups": ["What's the syntax for common data elements?"],
                    "priority": 4
                },
                {
                    "question": "How does template inheritance work in ClinDoc?",
                    "targets": ["template inheritance rules"],
                    "follow_ups": ["How do you override inherited elements?"],
                    "priority": 3
                }
            ],
            "cardiac_rehab_integrations": [
                {
                    "question": "What's the difference between VersaCare and ScottCare data structures?",
                    "targets": ["ScottCare vs VersaCare data differences"],
                    "follow_ups": ["Do they use different HL7 segments?"],
                    "priority": 4
                },
                {
                    "question": "How do device identifiers get mapped to Epic patients?",
                    "targets": ["device identifier mapping strategies"],
                    "follow_ups": ["What happens when mapping fails?"],
                    "priority": 5
                }
            ],
            "workflow_optimization": [
                {
                    "question": "How do you decide when a BPA will cause alert fatigue?",
                    "targets": ["BPA firing logic", "alert fatigue"],
                    "follow_ups": ["What's your BPA suppression strategy?"],
                    "priority": 3
                },
                {
                    "question": "What's your process for click reduction analysis?",
                    "targets": ["click reduction analysis methodology"],
                    "follow_ups": ["How many clicks is 'too many'?"],
                    "priority": 3
                }
            ],
            "cutover_procedures": [
                {
                    "question": "What are the critical items on a cutover checklist?",
                    "targets": ["cutover checklist components"],
                    "follow_ups": ["What gets missed most often?"],
                    "priority": 4
                },
                {
                    "question": "How does command center triage work during go-live?",
                    "targets": ["command center operations"],
                    "follow_ups": ["How do you prioritize break-fix issues?"],
                    "priority": 4
                }
            ]
        }

    def detect_work_context(self, message: str) -> Optional[str]:
        """
        Detect Epic work context from user message.
        
        Returns domain name if detected, None otherwise.
        """
        context_keywords = {
            "orderset_builds": ["orderset", "order set", "smartset", "quick list", 
                               "preference", "building orders"],
            "interfaces": ["interface", "hl7", "bridge", "provider matching",
                          "integration", "versacare", "scottcare"],
            "clindoc_configuration": ["smartphrase", "template", "clindoc", 
                                     "documentation", "flowsheet"],
            "cardiac_rehab_integrations": ["versacare", "scottcare", "rehab",
                                          "cardiac", "telemonitoring"],
            "workflow_optimization": ["workflow", "efficiency", "optimization",
                                     "bpa", "click reduction"],
            "cutover_procedures": ["cutover", "go-live", "migration", 
                                  "command center"]
        }

        message_lower = message.lower()
        for domain, keywords in context_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return domain

        return None

    def should_ask_question(self) -> Tuple[bool, str]:
        """
        Check if it's appropriate to ask a question based on timing constraints.
        
        Returns (should_ask: bool, reason: str)
        """
        settings = self.state.get("settings", {})
        session = self.state.get("session_history", {})

        # Check max questions per session
        max_questions = settings.get("max_questions_per_session", 2)
        questions_today = session.get("questions_asked_today", 0)

        if questions_today >= max_questions:
            return False, f"Already asked {questions_today} questions today (max: {max_questions})"

        # Check minimum interval between questions
        last_question_str = session.get("last_question_timestamp")
        if last_question_str:
            last_question = datetime.fromisoformat(last_question_str)
            now = datetime.now(timezone.utc)
            min_interval = settings.get("min_question_interval_minutes", 30)
            
            elapsed_minutes = (now - last_question).total_seconds() / 60
            if elapsed_minutes < min_interval:
                return False, f"Last question was {int(elapsed_minutes)} min ago (min: {min_interval})"

        # Check if in learning session cooldown
        cooldown_hours = settings.get("learning_session_cooldown_hours", 2)
        last_capture_str = session.get("last_capture_timestamp")
        if last_capture_str:
            last_capture = datetime.fromisoformat(last_capture_str)
            now = datetime.now(timezone.utc)
            elapsed_hours = (now - last_capture).total_seconds() / 3600
            
            if elapsed_hours < cooldown_hours:
                return False, f"In cooldown after recent capture ({int(elapsed_hours)}h ago)"

        return True, "OK to ask"

    def select_question(self, domain: str) -> Optional[Dict]:
        """
        Select best question for the given domain based on knowledge gaps.
        
        Prioritizes:
        1. Questions targeting current knowledge gaps
        2. Higher priority questions
        3. Questions not asked recently
        """
        domain_questions = self.question_bank.get(domain, [])
        if not domain_questions:
            return None

        domain_state = self.state.get("domains", {}).get(domain, {})
        knowledge_gaps = domain_state.get("knowledge_gaps", [])

        # Score questions
        scored_questions = []
        for q in domain_questions:
            score = q["priority"]

            # Bonus for targeting knowledge gaps
            for gap in knowledge_gaps:
                if any(gap.lower() in target.lower() for target in q["targets"]):
                    score += 3

            scored_questions.append((score, q))

        # Sort by score (highest first)
        scored_questions.sort(key=lambda x: x[0], reverse=True)

        # Return top question
        return scored_questions[0][1] if scored_questions else None

    def generate_question_prompt(self, question_obj: Dict, notebook_summary: Optional[str] = None) -> str:
        """
        Generate natural question prompt for the agent to ask.
        
        Includes permission request and question text.
        """
        permission = "Mind if I ask a quick question to learn?"
        question = question_obj["question"]

        summary_block = ""
        if notebook_summary:
            summary_block = (
                f"{notebook_summary}\n\n"
                "Is that accurate for our build? If not, what’s the real rule?\n\n"
            )

        return f"{permission}\n\n{summary_block}{question}"

    def record_question_asked(self, domain: str, question_obj: Dict):
        """Update learning state after asking a question."""
        now = datetime.now(timezone.utc).isoformat()

        # Update session history
        if "session_history" not in self.state:
            self.state["session_history"] = {}

        self.state["session_history"]["last_question_timestamp"] = now
        self.state["session_history"]["questions_asked_today"] = \
            self.state["session_history"].get("questions_asked_today", 0) + 1

        # Update domain stats
        if domain in self.state.get("domains", {}):
            domain_state = self.state["domains"][domain]
            domain_state["questions_asked"] = domain_state.get("questions_asked", 0) + 1
            domain_state["last_updated"] = now

        # Update global stats
        if "global_stats" in self.state:
            self.state["global_stats"]["total_questions_asked"] = \
                self.state["global_stats"].get("total_questions_asked", 0) + 1

        self.save_state()

        print(f"  → Question recorded: {domain}")
        print(f"     Questions today: {self.state['session_history']['questions_asked_today']}")

    def process_answer(self, domain: str, question_obj: Dict, answer: str):
        """
        Process Jeremy's answer and store as learning.
        
        In practice, this would:
        1. Extract key concepts from answer
        2. Store in Memory V2
        3. Store in Graphiti
        4. Update knowledge gaps (mark as addressed)
        """
        # TODO: Integrate with Memory V2 and Graphiti
        # from memory_v2 import store_fact
        # from graphiti import add_relationship

        # Store answer as concept
        concept = {
            "date": datetime.now(timezone.utc).isoformat().split("T")[0],
            "domain": domain,
            "concept": question_obj["question"],
            "answer": answer,
            "source": "targeted_question",
            "confidence": "high"
        }

        # Update domain concepts
        if domain in self.state.get("domains", {}):
            domain_state = self.state["domains"][domain]
            domain_state["concepts_learned"] += 1

            if "recent_concepts" not in domain_state:
                domain_state["recent_concepts"] = []

            domain_state["recent_concepts"].insert(0, {
                "concept": question_obj["question"],
                "learned_date": concept["date"],
                "confidence": "high",
                "source": "targeted_question"
            })

            domain_state["recent_concepts"] = domain_state["recent_concepts"][:5]

            # Remove addressed knowledge gaps
            for target in question_obj["targets"]:
                gaps = domain_state.get("knowledge_gaps", [])
                domain_state["knowledge_gaps"] = [
                    gap for gap in gaps 
                    if target.lower() not in gap.lower()
                ]

        self.save_state()

        print(f"\n✅ Answer captured and stored!")
        print(f"   Domain: {domain}")
        print(f"   Concepts learned: {self.state['domains'][domain]['concepts_learned']}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Epic Targeted Questioning")
    parser.add_argument("--context", "-c", type=str,
                       help="Work context to detect domain")
    parser.add_argument("--suggest-question", "-s", action="store_true",
                       help="Suggest a question based on current state")
    parser.add_argument("--domain", "-d", type=str,
                       help="Specific domain to ask about")

    args = parser.parse_args()

    asker = QuestionAsker()

    if args.suggest_question or args.domain:
        # Check if we should ask
        should_ask, reason = asker.should_ask_question()
        if not should_ask:
            print(f"❌ Cannot ask question: {reason}")
            return

        # Determine domain
        domain = args.domain
        if not domain and args.context:
            domain = asker.detect_work_context(args.context)

        if not domain:
            print("❌ No domain detected. Specify --domain or provide --context")
            return

        # Select question
        question_obj = asker.select_question(domain)
        if not question_obj:
            print(f"❌ No questions available for domain: {domain}")
            return

        # Pull NotebookLM cross-reference before asking
        notebook_summary = asker.crossref.summarize_for_question(
            domain=domain,
            question=question_obj["question"],
            timeout=120,
        )

        # Generate prompt
        prompt = asker.generate_question_prompt(question_obj, notebook_summary=notebook_summary)
        print(f"\n📝 Suggested question for {domain}:\n")
        print(prompt)
        print(f"\nPriority: {question_obj['priority']}/5")
        print(f"Targets: {', '.join(question_obj['targets'])}")

        # Record (in real use, only after asking and getting answer)
        # asker.record_question_asked(domain, question_obj)

    elif args.context:
        domain = asker.detect_work_context(args.context)
        if domain:
            print(f"✅ Detected domain: {domain}")
        else:
            print("❌ No Epic work context detected")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
