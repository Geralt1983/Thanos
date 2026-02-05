#!/usr/bin/env python3
"""
Natural Language RAG Test Suite

Tests 100+ human-like queries as if sent via Telegram.
All queries must return meaningful results for the test to pass.

These are REAL conversational queries, not programmatic ones.
"""

import json
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Tools.rag_natural import query_natural, detect_notebook


# Human-like queries organized by expected notebook
# These are the kinds of questions someone would actually ask via Telegram
NATURAL_QUERIES = {
    "orders_hod": [
        # Basic order set questions
        "how does an order set work",
        "tell me about order sets",
        "what is an order set",
        "explain order sets to me",
        "how do I use order sets",
        "what are order sets used for",
        "describe how order sets function",
        "give me the basics on order sets",

        # SmartSet questions
        "what is a SmartSet",
        "how do SmartSets work",
        "tell me about SmartSets",
        "explain SmartSets",
        "whats the deal with smartsets",
        "how do I build a smartset",
        "smartset configuration basics",

        # SmartGroup questions
        "what is a SmartGroup",
        "explain SmartGroups",
        "how do SmartGroups work",
        "tell me about smart groups",
        "difference between smartset and smartgroup",

        # Order Composer
        "how does order composer work",
        "what is order composer",
        "tell me about order composer",
        "order composer basics",

        # Preference Lists
        "what are preference lists",
        "how do preference lists work",
        "explain preference lists",
        "tell me about preference lists",
        "preference list setup",

        # Patient Lists
        "how do patient lists work",
        "what are patient lists",
        "tell me about patient lists",
        "patient list configuration",

        # Panels
        "what are order panels",
        "how do panels work in epic",
        "tell me about panels",
        "order panel setup",

        # OSQ (Order-Specific Questions)
        "what are order specific questions",
        "how do OSQ work",
        "tell me about osq",
        "order specific question configuration",

        # Workflow questions
        "how do I set up order workflows",
        "order workflow configuration",
        "tell me about order workflows",
        "workflow setup in epic",

        # General Epic questions
        "how does epic handle orders",
        "epic ordering basics",
        "tell me about epic orders",
        "how to manage orders in epic",

        # Complex/compound questions
        "how do I create an order set with multiple smart groups",
        "what's the relationship between order sets and preference lists",
        "explain the order entry process",
        "how does manage orders work",
        "tell me about the order entry activity",
        "inpatient orders setup",
        "how do I configure orders for the ED",

        # Casual/informal phrasing
        "whats the best way to do order sets",
        "can you explain how to build orders",
        "help me understand order sets",
        "i need to know about smartsets",
        "quick question about order panels",
        "hey whats an order composer",

        # Troubleshooting questions
        "my order set isnt working",
        "common order set problems",
        "order set troubleshooting",
        "why isnt my smartset showing up",

        # How-to questions
        "how do I create an order set",
        "steps to build a smartset",
        "how to add orders to a panel",
        "how to configure preference lists",
        "setting up patient lists",

        # Comparison questions
        "whats the difference between an order set and a panel",
        "order set vs smartgroup",
        "when should I use a preference list vs order set",

        # Context-dependent questions
        "tell me more about that order stuff",
        "explain the order system",
        "how does ordering work",
        "what should I know about orders",

        # Building/Configuration
        "how do I build an extension record",
        "extension record configuration",
        "smartset editor basics",
        "using the smartset editor",

        # Notes/Documentation
        "how do notes work in epic",
        "patient notes setup",
        "notes configuration",
    ],

    "ncdhhs_radiology": [
        "what does ncdhhs say about radiology",
        "ncdhhs radiology requirements",
        "tell me about ncdhhs radiology",
        "north carolina radiology rules",
        "ncdhhs imaging requirements",
        "whats in the ncdhhs radiology emails",
        "ncdhhs radiology workflow",
        "nc dhhs radiology guidelines",
    ],

    "versacare": [
        "tell me about versacare",
        "what is scottcare",
        "versacare integration",
        "cardiac rehab system",
        "kentucky integration",
        "telemonitoring setup",
    ],

    "harry": [
        "what does harry say",
        "harrys emails",
        "tell me about harry documents",
        "whats in harry",
    ],
}

# Additional random natural variations
CASUAL_PREFIXES = [
    "hey ",
    "quick question - ",
    "can you tell me ",
    "I need to know ",
    "what's the deal with ",
    "help me understand ",
    "explain ",
    "tell me about ",
    "",  # no prefix
]

CASUAL_SUFFIXES = [
    "",
    "?",
    " please",
    " real quick",
    " - thanks",
]


@dataclass
class TestResult:
    query: str
    expected_notebook: str
    detected_notebook: str
    confidence: float
    got_answer: bool
    answer_length: int
    has_sources: bool
    is_error: bool
    duration_ms: int
    answer_preview: str = ""


@dataclass
class TestSuite:
    results: List[TestResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = None

    def add(self, result: TestResult):
        self.results.append(result)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.got_answer and not r.is_error)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def correct_routing(self) -> int:
        return sum(1 for r in self.results if r.expected_notebook == r.detected_notebook)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0


def randomize_query(query: str) -> str:
    """Add natural variation to a query."""
    prefix = random.choice(CASUAL_PREFIXES)
    suffix = random.choice(CASUAL_SUFFIXES)

    # Random case variations
    if random.random() < 0.3:
        query = query.lower()
    elif random.random() < 0.1:
        query = query.upper()

    return f"{prefix}{query}{suffix}"


def run_natural_query_test(query: str, expected_notebook: str) -> TestResult:
    """Run a single natural language query test."""
    start = time.time()

    try:
        result = query_natural(query)
        duration = int((time.time() - start) * 1000)

        # Determine if we got a meaningful answer
        answer = result.get("answer", "")
        is_error = result.get("error", False)
        not_found = "couldn't find specific information" in answer.lower()
        has_sources = len(result.get("sources", [])) > 0

        # Got answer if not an error and either has sources or meaningful text
        got_answer = not is_error and not not_found and len(answer) > 50

        return TestResult(
            query=query,
            expected_notebook=expected_notebook,
            detected_notebook=result.get("notebook", "unknown"),
            confidence=result.get("confidence", 0),
            got_answer=got_answer,
            answer_length=len(answer),
            has_sources=has_sources,
            is_error=is_error,
            duration_ms=duration,
            answer_preview=answer[:100] if answer else "",
        )

    except Exception as e:
        return TestResult(
            query=query,
            expected_notebook=expected_notebook,
            detected_notebook="error",
            confidence=0,
            got_answer=False,
            answer_length=0,
            has_sources=False,
            is_error=True,
            duration_ms=int((time.time() - start) * 1000),
            answer_preview=str(e)[:100],
        )


def run_test_suite(target_count: int = 100, randomize: bool = True, queries_dict: Dict[str, List[str]] = None) -> TestSuite:
    """
    Run the natural language test suite.

    Args:
        target_count: Minimum number of queries to run
        randomize: Whether to add natural variations to queries
        queries_dict: Optional dict of queries to use (defaults to NATURAL_QUERIES)
    """
    suite = TestSuite()
    test_queries = queries_dict or NATURAL_QUERIES

    print("\n" + "=" * 60)
    print("NATURAL LANGUAGE RAG TEST SUITE")
    print(f"Target: {target_count}+ queries, testing like Telegram messages")
    print("=" * 60)

    # Build the test list
    all_queries: List[tuple] = []

    for notebook, queries in test_queries.items():
        for q in queries:
            # Add original
            all_queries.append((q, notebook))
            # Add randomized version
            if randomize and len(all_queries) < target_count:
                all_queries.append((randomize_query(q), notebook))

    # Shuffle for realistic testing
    random.shuffle(all_queries)

    # Trim or pad to target
    if len(all_queries) > target_count:
        all_queries = all_queries[:target_count]
    elif len(all_queries) < target_count:
        # Duplicate with variations to reach target
        while len(all_queries) < target_count:
            notebook, queries_list = random.choice(list(test_queries.items()))
            q = random.choice(queries_list)
            all_queries.append((randomize_query(q), notebook))

    print(f"\nRunning {len(all_queries)} natural language queries...")
    print("-" * 60)

    for i, (query, expected_notebook) in enumerate(all_queries, 1):
        result = run_natural_query_test(query, expected_notebook)
        suite.add(result)

        # Status indicator
        status = "✅" if result.got_answer else "❌"
        routing = "→" if result.detected_notebook == expected_notebook else "⚠"

        # Truncate for display
        display_query = query[:45] + "..." if len(query) > 45 else query

        print(f"[{i:3d}/{len(all_queries)}] {status} {routing} {display_query}")

        if not result.got_answer:
            print(f"         └─ {result.answer_preview[:60]}...")

    suite.end_time = datetime.now()
    return suite


def print_summary(suite: TestSuite):
    """Print test results summary."""
    duration = (suite.end_time - suite.start_time).total_seconds()

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Queries:      {suite.total}")
    print(f"Got Answers:        {suite.passed} ✅")
    print(f"No Answer/Error:    {suite.failed} ❌")
    print(f"Correct Routing:    {suite.correct_routing}/{suite.total} ({suite.correct_routing/suite.total*100:.0f}%)")
    print(f"Pass Rate:          {suite.pass_rate:.1f}%")
    print(f"Duration:           {duration:.1f}s ({duration/suite.total:.1f}s avg)")

    # Per-notebook breakdown
    print("\n" + "-" * 40)
    print("PER-NOTEBOOK RESULTS:")
    print("-" * 40)

    notebook_stats: Dict[str, Dict[str, int]] = {}
    for r in suite.results:
        nb = r.expected_notebook
        if nb not in notebook_stats:
            notebook_stats[nb] = {"passed": 0, "failed": 0, "correct_route": 0}
        if r.got_answer:
            notebook_stats[nb]["passed"] += 1
        else:
            notebook_stats[nb]["failed"] += 1
        if r.detected_notebook == r.expected_notebook:
            notebook_stats[nb]["correct_route"] += 1

    for nb, stats in sorted(notebook_stats.items()):
        total = stats["passed"] + stats["failed"]
        rate = stats["passed"] / total * 100 if total > 0 else 0
        route_rate = stats["correct_route"] / total * 100 if total > 0 else 0
        status = "✅" if stats["failed"] == 0 else ("⚠️" if rate >= 80 else "❌")
        print(f"  {status} {nb}: {stats['passed']}/{total} ({rate:.0f}%) | routing: {route_rate:.0f}%")

    # Show failures
    if suite.failed > 0:
        print("\n" + "-" * 40)
        print("FAILED QUERIES (first 10):")
        print("-" * 40)
        failed = [r for r in suite.results if not r.got_answer][:10]
        for r in failed:
            print(f"  ❌ [{r.expected_notebook}] {r.query[:50]}")
            print(f"     └─ {r.answer_preview[:60]}")

    print("\n" + "=" * 60)
    if suite.pass_rate == 100:
        print("🎉 ALL TESTS PASSED! Natural language RAG is bulletproof.")
    elif suite.pass_rate >= 80:
        print(f"⚠️  {suite.pass_rate:.1f}% pass rate. Some queries need attention.")
    else:
        print(f"❌ {suite.pass_rate:.1f}% pass rate. Significant issues to fix.")
    print("=" * 60)


def save_results(suite: TestSuite, filepath: Path):
    """Save test results to JSON."""
    data = {
        "timestamp": suite.start_time.isoformat(),
        "duration_seconds": (suite.end_time - suite.start_time).total_seconds(),
        "total": suite.total,
        "passed": suite.passed,
        "failed": suite.failed,
        "pass_rate": suite.pass_rate,
        "correct_routing": suite.correct_routing,
        "results": [
            {
                "query": r.query,
                "expected_notebook": r.expected_notebook,
                "detected_notebook": r.detected_notebook,
                "confidence": r.confidence,
                "got_answer": r.got_answer,
                "answer_length": r.answer_length,
                "has_sources": r.has_sources,
                "is_error": r.is_error,
                "duration_ms": r.duration_ms,
                "answer_preview": r.answer_preview,
            }
            for r in suite.results
        ],
    }

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved to: {filepath}")


def main():
    """Run the natural language test suite."""
    import argparse

    parser = argparse.ArgumentParser(description="Natural Language RAG Test Suite")
    parser.add_argument("--count", "-c", type=int, default=100, help="Number of queries to run")
    parser.add_argument("--no-randomize", action="store_true", help="Don't add natural variations")
    parser.add_argument("--notebook", "-n", help="Test only specific notebook")

    args = parser.parse_args()

    # Filter by notebook if specified
    queries_to_test = NATURAL_QUERIES
    if args.notebook:
        if args.notebook not in NATURAL_QUERIES:
            print(f"Unknown notebook: {args.notebook}")
            print(f"Available: {list(NATURAL_QUERIES.keys())}")
            sys.exit(1)
        queries_to_test = {args.notebook: NATURAL_QUERIES[args.notebook]}

    # Run tests
    suite = run_test_suite(
        target_count=args.count,
        randomize=not args.no_randomize,
        queries_dict=queries_to_test,
    )

    # Print summary
    print_summary(suite)

    # Save results
    results_file = PROJECT_ROOT / "tests" / "results" / f"rag_natural_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    save_results(suite, results_file)

    # Exit code based on pass rate
    if suite.pass_rate >= 95:
        sys.exit(0)
    elif suite.pass_rate >= 80:
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
