#!/usr/bin/env python3
"""
RAG Integration Test Suite
Runs 100+ randomized human-like queries against all notebooks.
All queries must pass for the integration to be considered working.
"""

import subprocess
import random
import json
import time
import sys
from pathlib import Path
from typing import Tuple, List, Dict
from dataclasses import dataclass, field
from datetime import datetime

THANOS_ROOT = Path(__file__).parent.parent
RAG_CLI = THANOS_ROOT / "scripts" / "rag-cli.sh"

# Notebooks with their domains and sample query templates
# Only include notebooks that have actual documents in their vector stores
NOTEBOOKS = {
    "orders_hod": {
        "domain": "Epic Orders / HOD",
        "topics": ["order sets", "SmartSets", "SmartGroups", "order composers", "preference lists", "panels", "OSQ"],
        "query_templates": [
            "What is a {topic}?",
            "How do I create a {topic}?",
            "Explain {topic} configuration",
            "What are best practices for {topic}?",
            "How does {topic} work in Epic?",
            "Steps to build a {topic}",
            "What's the difference between {topic} and order panels?",
            "Can you describe {topic}?",
            "Tell me about {topic}",
            "What are {topic} used for?",
            "How are {topic} organized?",
            "What settings affect {topic}?",
            "Troubleshooting {topic} issues",
            "Common problems with {topic}",
        ],
    },
    # ncdhhs_radiology_pdf has 28 files - use it via the "ncdhhs" alias
    "ncdhhs_radiology_pdf": {
        "domain": "NCDHHS Radiology",
        "topics": ["radiology", "NCDHHS", "imaging", "preference lists", "workflows", "requirements"],
        "query_templates": [
            "What {topic} are documented?",
            "Summarize {topic} requirements",
            "List {topic} topics",
            "What does NCDHHS say about {topic}?",
            "Key {topic} information",
            "What emails discuss {topic}?",
            "Explain the {topic} process",
            "Tell me about {topic}",
        ],
    },
}

# Notebooks that are empty and excluded from testing (no documents uploaded yet)
# Uncomment and add to NOTEBOOKS when documents are available:
# EMPTY_NOTEBOOKS = {
#     "versacare": {...},  # 0 files - needs ScottCare/Kentucky docs
#     "drive_inbox": {...},  # 0 files - needs Drive inbox sync
#     "harry": {...},  # 0 files - needs Harry docs
# }

# Additional free-form query patterns that work across notebooks
GENERIC_QUERIES = [
    "What documents are stored here?",
    "Summarize the main topics",
    "What is the most important information?",
    "List all available content",
    "What are the key points?",
    "Give me an overview",
    "What should I know about this?",
    "Main takeaways",
    "Important details",
    "Critical information",
]

# Alias variations to test notebook resolution
# Only test aliases for notebooks that have actual documents
NOTEBOOK_ALIAS_TESTS = [
    # NCDHHS/Radiology aliases -> ncdhhs_radiology_pdf (has 28 files)
    ("ncdhhs", "ncdhhs_radiology_pdf"),
    ("radiology", "ncdhhs_radiology_pdf"),

    # Orders/HOD aliases -> orders_hod (has 6 files)
    ("orders", "orders_hod"),
    ("hod", "orders_hod"),
    ("epic", "orders_hod"),
]

# Aliases for empty notebooks - commented out until documents are uploaded
# ("scottcare", "versacare"),  # versacare has 0 files
# ("kentucky", "versacare"),
# ("ky", "versacare"),
# ("inbox", "drive_inbox"),  # drive_inbox has 0 files
# ("drive inbox", "drive_inbox"),
# ("harry", "harry"),  # harry has 0 files


@dataclass
class TestResult:
    """Result of a single test query."""
    notebook: str
    query: str
    success: bool
    response_length: int
    has_content: bool
    has_sources: bool
    error: str = ""
    duration_ms: int = 0


@dataclass
class TestSuite:
    """Collection of test results."""
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
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0


def run_rag_query(notebook: str, query: str) -> Tuple[bool, str, int]:
    """
    Execute a RAG query and return (success, response, duration_ms).
    """
    start = time.time()
    try:
        result = subprocess.run(
            ["bash", str(RAG_CLI), "query", notebook, query],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(THANOS_ROOT),
        )
        duration = int((time.time() - start) * 1000)

        if result.returncode != 0:
            return False, f"Exit code {result.returncode}: {result.stderr}", duration

        response = result.stdout.strip()
        if not response:
            return False, "Empty response", duration

        # Check for error patterns
        error_patterns = ["Error:", "error:", "not found", "failed", "Unable to"]
        for pattern in error_patterns:
            if pattern.lower() in response.lower() and "Reference" not in response:
                # Allow error patterns in context of sources/references
                if len(response) < 200:
                    return False, f"Error pattern detected: {response[:200]}", duration

        return True, response, duration

    except subprocess.TimeoutExpired:
        return False, "Query timed out after 120s", 120000
    except Exception as e:
        return False, f"Exception: {str(e)}", 0


def run_rag_list() -> Tuple[bool, str]:
    """Test the list command."""
    try:
        result = subprocess.run(
            ["bash", str(RAG_CLI), "list"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(THANOS_ROOT),
        )
        if result.returncode != 0:
            return False, result.stderr
        return True, result.stdout
    except Exception as e:
        return False, str(e)


def generate_queries(notebook: str, count: int) -> List[str]:
    """Generate random queries for a notebook."""
    config = NOTEBOOKS.get(notebook)
    if not config:
        return GENERIC_QUERIES[:count]

    queries = []
    templates = config["query_templates"]
    topics = config["topics"]

    for _ in range(count):
        template = random.choice(templates)
        topic = random.choice(topics)
        query = template.format(topic=topic)
        queries.append(query)

    # Add some generic queries
    queries.extend(random.sample(GENERIC_QUERIES, min(3, len(GENERIC_QUERIES))))

    return queries[:count]


def test_notebook_aliases() -> List[TestResult]:
    """Test that all notebook aliases resolve correctly."""
    results = []

    print("\n" + "="*60)
    print("TESTING NOTEBOOK ALIAS RESOLUTION")
    print("="*60)

    for alias, expected in NOTEBOOK_ALIAS_TESTS:
        # Use a simple query to test alias resolution
        success, response, duration = run_rag_query(alias, "list topics")

        # Check if we got a valid response (not an "unknown notebook" error)
        is_valid = success and "Unknown notebook" not in response and len(response) > 50

        status = "✅" if is_valid else "❌"
        print(f"{status} Alias '{alias}' -> {expected}: {'OK' if is_valid else 'FAILED'}")

        results.append(TestResult(
            notebook=alias,
            query=f"alias_test:{alias}",
            success=is_valid,
            response_length=len(response),
            has_content=len(response) > 50,
            has_sources="Sources:" in response or "Reference" in response,
            error="" if is_valid else response[:200],
            duration_ms=duration,
        ))

    return results


def test_list_command() -> TestResult:
    """Test the list command."""
    print("\n" + "="*60)
    print("TESTING LIST COMMAND")
    print("="*60)

    success, response = run_rag_list()

    # Validate response contains expected notebooks (only those with documents)
    expected_notebooks = ["orders_hod", "ncdhhs_radiology"]  # Notebooks with actual documents
    all_present = all(nb in response for nb in expected_notebooks)

    is_valid = success and all_present
    status = "✅" if is_valid else "❌"
    print(f"{status} List command: {'OK' if is_valid else 'FAILED'}")
    if not is_valid:
        print(f"   Response: {response[:200]}")

    return TestResult(
        notebook="*",
        query="list",
        success=is_valid,
        response_length=len(response),
        has_content=len(response) > 50,
        has_sources=False,
        error="" if is_valid else response[:200],
        duration_ms=0,
    )


def test_queries(notebook: str, queries: List[str]) -> List[TestResult]:
    """Run a batch of queries against a notebook."""
    results = []

    print(f"\n" + "-"*40)
    print(f"Testing {notebook} ({len(queries)} queries)")
    print("-"*40)

    for i, query in enumerate(queries, 1):
        success, response, duration = run_rag_query(notebook, query)

        has_content = len(response) > 100
        has_sources = "Sources:" in response or "Reference" in response

        # A valid response should have meaningful content
        is_valid = success and has_content

        status = "✅" if is_valid else "❌"
        short_query = query[:40] + "..." if len(query) > 40 else query
        print(f"  [{i:3d}] {status} {short_query} ({duration}ms, {len(response)} chars)")

        if not is_valid:
            print(f"        Error: {response[:100]}...")

        results.append(TestResult(
            notebook=notebook,
            query=query,
            success=is_valid,
            response_length=len(response),
            has_content=has_content,
            has_sources=has_sources,
            error="" if is_valid else response[:200],
            duration_ms=duration,
        ))

    return results


def run_full_test_suite(min_queries: int = 100) -> TestSuite:
    """Run the complete test suite with at least min_queries total queries."""
    suite = TestSuite()

    print("\n" + "="*60)
    print("THANOS RAG INTEGRATION TEST SUITE")
    print(f"Target: {min_queries}+ queries, 100% pass rate required")
    print("="*60)

    # Test list command
    suite.add(test_list_command())

    # Test notebook aliases
    alias_results = test_notebook_aliases()
    for r in alias_results:
        suite.add(r)

    # Calculate queries per notebook to reach target
    notebooks_to_test = list(NOTEBOOKS.keys())
    remaining = min_queries - len(alias_results) - 1  # Subtract alias tests and list
    queries_per_notebook = max(15, remaining // len(notebooks_to_test))

    # Run queries for each notebook
    for notebook in notebooks_to_test:
        queries = generate_queries(notebook, queries_per_notebook)
        results = test_queries(notebook, queries)
        for r in results:
            suite.add(r)

    suite.end_time = datetime.now()
    return suite


def print_summary(suite: TestSuite):
    """Print test results summary."""
    duration = (suite.end_time - suite.start_time).total_seconds()

    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    print(f"Total Tests:    {suite.total}")
    print(f"Passed:         {suite.passed} ✅")
    print(f"Failed:         {suite.failed} ❌")
    print(f"Pass Rate:      {suite.pass_rate:.1f}%")
    print(f"Duration:       {duration:.1f}s")

    if suite.failed > 0:
        print("\n" + "-"*40)
        print("FAILED TESTS:")
        print("-"*40)
        for r in suite.results:
            if not r.success:
                print(f"  ❌ [{r.notebook}] {r.query[:50]}")
                print(f"     Error: {r.error[:100]}")

    # Per-notebook breakdown
    print("\n" + "-"*40)
    print("PER-NOTEBOOK RESULTS:")
    print("-"*40)

    notebook_stats = {}
    for r in suite.results:
        if r.notebook not in notebook_stats:
            notebook_stats[r.notebook] = {"passed": 0, "failed": 0}
        if r.success:
            notebook_stats[r.notebook]["passed"] += 1
        else:
            notebook_stats[r.notebook]["failed"] += 1

    for nb, stats in sorted(notebook_stats.items()):
        total = stats["passed"] + stats["failed"]
        rate = stats["passed"] / total * 100 if total > 0 else 0
        status = "✅" if stats["failed"] == 0 else "❌"
        print(f"  {status} {nb}: {stats['passed']}/{total} ({rate:.0f}%)")

    print("\n" + "="*60)
    if suite.pass_rate == 100:
        print("🎉 ALL TESTS PASSED! RAG integration is bulletproof.")
    else:
        print(f"⚠️  {suite.failed} tests failed. Integration needs fixes.")
    print("="*60)


def save_results(suite: TestSuite, filepath: Path):
    """Save test results to JSON file."""
    data = {
        "timestamp": suite.start_time.isoformat(),
        "duration_seconds": (suite.end_time - suite.start_time).total_seconds(),
        "total": suite.total,
        "passed": suite.passed,
        "failed": suite.failed,
        "pass_rate": suite.pass_rate,
        "results": [
            {
                "notebook": r.notebook,
                "query": r.query,
                "success": r.success,
                "response_length": r.response_length,
                "has_content": r.has_content,
                "has_sources": r.has_sources,
                "error": r.error,
                "duration_ms": r.duration_ms,
            }
            for r in suite.results
        ],
    }

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved to: {filepath}")


def main():
    """Run the test suite."""
    # Parse arguments
    min_queries = 100
    if len(sys.argv) > 1:
        try:
            min_queries = int(sys.argv[1])
        except ValueError:
            pass

    # Run tests
    suite = run_full_test_suite(min_queries)

    # Print summary
    print_summary(suite)

    # Save results
    results_file = THANOS_ROOT / "tests" / "results" / f"rag_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    save_results(suite, results_file)

    # Exit with appropriate code
    sys.exit(0 if suite.pass_rate == 100 else 1)


if __name__ == "__main__":
    main()
