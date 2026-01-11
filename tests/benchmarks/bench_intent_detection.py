#!/usr/bin/env python3
"""
Benchmark for find_agent intent detection performance.

This benchmark measures the current O(n*m) complexity of the find_agent method
to establish a baseline for optimization work.

Usage:
    python tests/benchmarks/bench_intent_detection.py
    pytest tests/benchmarks/bench_intent_detection.py -v
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple
from statistics import mean, median, stdev
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.thanos_orchestrator import ThanosOrchestrator


class IntentDetectionBenchmark:
    """Benchmark suite for intent detection performance."""

    def __init__(self, iterations: int = 1000):
        """Initialize benchmark with specified iteration count.

        Args:
            iterations: Number of iterations per test case
        """
        self.iterations = iterations
        self.orchestrator = None

    def setup(self):
        """Set up test environment."""
        # Initialize orchestrator (without API client for speed)
        self.orchestrator = ThanosOrchestrator(base_dir=str(project_root))

    def teardown(self):
        """Clean up test environment."""
        self.orchestrator = None

    def _time_function(self, func, *args, **kwargs) -> float:
        """Time a function call in microseconds.

        Args:
            func: Function to time
            *args: Positional arguments to pass
            **kwargs: Keyword arguments to pass

        Returns:
            Execution time in microseconds
        """
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        return (end - start) * 1_000_000  # Convert to microseconds

    def _run_benchmark(self, messages: List[str], label: str) -> Dict:
        """Run benchmark for a set of messages.

        Args:
            messages: List of messages to test
            label: Label for this benchmark

        Returns:
            Dictionary of timing statistics
        """
        timings = []

        for _ in range(self.iterations):
            for message in messages:
                time_us = self._time_function(
                    self.orchestrator.find_agent,
                    message
                )
                timings.append(time_us)

        # Calculate statistics
        timings.sort()
        return {
            'label': label,
            'iterations': len(timings),
            'mean_us': mean(timings),
            'median_us': median(timings),
            'min_us': min(timings),
            'max_us': max(timings),
            'stddev_us': stdev(timings) if len(timings) > 1 else 0,
            'p95_us': timings[int(len(timings) * 0.95)],
            'p99_us': timings[int(len(timings) * 0.99)],
        }

    def benchmark_short_messages(self) -> Dict:
        """Benchmark with short messages (1-5 words)."""
        messages = [
            "help me plan",
            "what should i do",
            "im overwhelmed",
            "task list",
            "schedule today",
            "email",
            "quarterly goals",
            "im tired",
            "cant focus",
            "motivation",
        ]
        return self._run_benchmark(messages, "Short messages (1-5 words)")

    def benchmark_medium_messages(self) -> Dict:
        """Benchmark with medium messages (10-20 words)."""
        messages = [
            "I need help planning my day and figuring out what to prioritize",
            "Can you help me organize my tasks for the week ahead",
            "I'm feeling overwhelmed with everything on my plate right now",
            "What should I focus on today to make the most progress",
            "I keep procrastinating on this important project, why cant I just start",
            "Should I take this new client or focus on existing work",
            "I crashed in the afternoon and couldn't focus on anything",
            "I need accountability for following through on my commitments",
            "What are my quarterly goals and how am I tracking against them",
            "I'm struggling to maintain consistent habits and discipline",
        ]
        return self._run_benchmark(messages, "Medium messages (10-20 words)")

    def benchmark_long_messages(self) -> Dict:
        """Benchmark with long messages (40+ words)."""
        messages = [
            "I've been trying to get better at planning my day but I keep finding myself "
            "overwhelmed by all the different things I need to do. I have client work, "
            "personal projects, and family commitments all competing for my attention. "
            "Can you help me figure out what to prioritize and how to structure my day "
            "so I actually make progress on the important stuff instead of just reacting "
            "to whatever seems most urgent in the moment?",

            "I keep noticing this pattern where I commit to doing something important like "
            "working out or deep work sessions but then I find excuses to avoid it. I know "
            "this is self-sabotage but I can't seem to break the cycle. What's going on here "
            "and how can I build better accountability systems?",

            "I'm thinking about my long-term strategy and where I want to be in the next year "
            "or two. Should I focus on growing my current business or explore new opportunities? "
            "I have several potential clients interested but I'm not sure if taking on more work "
            "is the right move or if I should invest time in building systems and delegation.",

            "I took my Vyvanse this morning but I still feel foggy and can't focus on deep work. "
            "I've been staying up too late and not getting enough sleep. My energy levels are "
            "all over the place and I'm relying too much on caffeine to get through the day. "
            "What changes should I make to my routine to get back on track?",
        ]
        return self._run_benchmark(messages, "Long messages (40+ words)")

    def benchmark_keyword_density(self) -> Dict:
        """Benchmark with messages containing multiple keywords."""
        messages = [
            # High keyword density - multiple agent triggers
            "I need help planning my tasks and schedule for today and tomorrow "
            "but I'm also feeling overwhelmed and stuck on this pattern of procrastinating",

            "What should I prioritize for my quarterly goals while also managing "
            "my daily todo list and maintaining my workout routine and focus",

            # Low keyword density - mostly filler words
            "I would really appreciate it if you could perhaps provide some assistance "
            "with regard to the matter we discussed previously about the thing",

            # No keywords - edge case
            "The quick brown fox jumps over the lazy dog repeatedly",
        ]
        return self._run_benchmark(messages, "Keyword density variations")

    def benchmark_edge_cases(self) -> Dict:
        """Benchmark with edge cases."""
        messages = [
            "",  # Empty string
            "a",  # Single character
            "x" * 1000,  # Very long message with no keywords
            "task " * 200,  # Very long message with repeated keyword
        ]
        return self._run_benchmark(messages, "Edge cases")

    def run_all_benchmarks(self) -> List[Dict]:
        """Run all benchmarks and return results.

        Returns:
            List of benchmark result dictionaries
        """
        self.setup()

        results = []
        benchmarks = [
            self.benchmark_short_messages,
            self.benchmark_medium_messages,
            self.benchmark_long_messages,
            self.benchmark_keyword_density,
            self.benchmark_edge_cases,
        ]

        for benchmark_func in benchmarks:
            print(f"Running {benchmark_func.__name__}...", flush=True)
            result = benchmark_func()
            results.append(result)

        self.teardown()
        return results

    def print_results(self, results: List[Dict]):
        """Print benchmark results in a readable format.

        Args:
            results: List of benchmark result dictionaries
        """
        print("\n" + "=" * 80)
        print("INTENT DETECTION PERFORMANCE BENCHMARK")
        print("=" * 80)
        print(f"Iterations per test case: {self.iterations}")
        print()

        for result in results:
            print(f"{result['label']}")
            print("-" * 80)
            print(f"  Total iterations:  {result['iterations']:,}")
            print(f"  Mean time:         {result['mean_us']:>8.2f} μs  ({result['mean_us']/1000:.3f} ms)")
            print(f"  Median time:       {result['median_us']:>8.2f} μs  ({result['median_us']/1000:.3f} ms)")
            print(f"  Std deviation:     {result['stddev_us']:>8.2f} μs")
            print(f"  Min time:          {result['min_us']:>8.2f} μs")
            print(f"  Max time:          {result['max_us']:>8.2f} μs")
            print(f"  95th percentile:   {result['p95_us']:>8.2f} μs  ({result['p95_us']/1000:.3f} ms)")
            print(f"  99th percentile:   {result['p99_us']:>8.2f} μs  ({result['p99_us']/1000:.3f} ms)")
            print()

        # Calculate overall statistics
        all_means = [r['mean_us'] for r in results]
        print("=" * 80)
        print(f"Overall mean across all tests: {mean(all_means):.2f} μs ({mean(all_means)/1000:.3f} ms)")
        print("=" * 80)
        print()

    def save_results(self, results: List[Dict], filename: str = "benchmark_results.json"):
        """Save results to a JSON file.

        Args:
            results: List of benchmark result dictionaries
            filename: Output filename
        """
        output_path = project_root / ".auto-claude" / "specs" / "022-pre-compile-agent-keyword-patterns-for-o-1-intent-" / filename

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Add metadata
        output = {
            'benchmark_type': 'intent_detection',
            'implementation': 'current_o_n_m',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'iterations': self.iterations,
            'results': results
        }

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Results saved to: {output_path}")


def main():
    """Main entry point for benchmark."""
    # Allow specifying iterations via command line
    iterations = 1000
    if len(sys.argv) > 1:
        try:
            iterations = int(sys.argv[1])
        except ValueError:
            print(f"Invalid iteration count: {sys.argv[1]}")
            print("Usage: bench_intent_detection.py [iterations]")
            sys.exit(1)

    print(f"Starting intent detection benchmark with {iterations} iterations per test...")

    benchmark = IntentDetectionBenchmark(iterations=iterations)
    results = benchmark.run_all_benchmarks()
    benchmark.print_results(results)
    benchmark.save_results(results)


if __name__ == "__main__":
    main()
