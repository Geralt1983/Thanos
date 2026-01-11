#!/usr/bin/env python3
"""
Benchmark comparison: Old O(n*m) implementation vs New O(m) implementation.

This script compares the performance of:
1. OLD: Nested loops checking each keyword (O(n*m) complexity)
2. NEW: Pre-compiled regex patterns (O(m) complexity)

The old implementation iterated through 92 keywords across 4 agents, performing
substring searches for each keyword. The new implementation uses a single
pre-compiled regex pattern with alternation groups.

Usage:
    python tests/benchmarks/bench_comparison.py [iterations]

Example:
    python tests/benchmarks/bench_comparison.py 1000  # Run 1000 iterations
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple
from statistics import mean, median, stdev
import json
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.intent_matcher import KeywordMatcher


class LegacyKeywordMatcher:
    """Legacy O(n*m) implementation using nested loops."""

    def __init__(self, agent_keywords: Dict[str, Dict[str, List[str]]],
                 agent_triggers: Dict[str, List[str]] = None):
        """Initialize with keyword dictionaries.

        Args:
            agent_keywords: Nested dict of {agent: {priority: [keywords]}}
            agent_triggers: Optional dict of {agent: [triggers]}
        """
        self.agent_keywords = agent_keywords
        self.agent_triggers = agent_triggers or {}

        # Count total keywords for analysis
        self.total_keywords = sum(
            len(keywords)
            for agent_kw in agent_keywords.values()
            for keywords in agent_kw.values()
        )
        if self.agent_triggers:
            self.total_keywords += sum(len(t) for t in self.agent_triggers.values())

    def match(self, message: str) -> Dict[str, int]:
        """Match message using O(n*m) nested loops (legacy approach).

        Args:
            message: User message to match

        Returns:
            Dictionary of {agent_name: score}
        """
        message_lower = message.lower()
        agent_scores = {}

        # First pass: Check triggers (10 points each)
        for agent_name, triggers in self.agent_triggers.items():
            if agent_name not in agent_scores:
                agent_scores[agent_name] = 0
            for trigger in triggers:
                if trigger.lower() in message_lower:
                    agent_scores[agent_name] += 10

        # Second pass: Check keywords by priority
        for agent_name, priorities in self.agent_keywords.items():
            if agent_name not in agent_scores:
                agent_scores[agent_name] = 0

            # High priority: 5 points
            for keyword in priorities.get('high', []):
                if keyword in message_lower:
                    agent_scores[agent_name] += 5

            # Medium priority: 2 points
            for keyword in priorities.get('medium', []):
                if keyword in message_lower:
                    agent_scores[agent_name] += 2

            # Low priority: 1 point
            for keyword in priorities.get('low', []):
                if keyword in message_lower:
                    agent_scores[agent_name] += 1

        return agent_scores


class BenchmarkComparison:
    """Benchmark comparison between old and new implementations."""

    def __init__(self, iterations: int = 1000):
        """Initialize benchmark.

        Args:
            iterations: Number of iterations per test case
        """
        self.iterations = iterations
        self.legacy_matcher = None
        self.optimized_matcher = None

    def setup(self):
        """Set up test environment with both matchers."""
        # Define keyword structure (same as used in ThanosOrchestrator)
        agent_keywords = {
            'ops': {
                'high': ['what should i do', 'whats on my plate', 'help me plan', 'overwhelmed',
                         'what did i commit', 'process inbox', 'clear my inbox', 'prioritize'],
                'medium': ['task', 'tasks', 'todo', 'to-do', 'schedule', 'plan', 'organize',
                           'today', 'tomorrow', 'this week', 'deadline', 'due'],
                'low': ['busy', 'work', 'productive', 'efficiency']
            },
            'coach': {
                'high': ['i keep doing this', 'why cant i', 'im struggling', 'pattern',
                         'be honest', 'accountability', 'avoiding', 'procrastinating'],
                'medium': ['habit', 'stuck', 'motivation', 'discipline', 'consistent',
                           'excuse', 'failing', 'trying', 'again'],
                'low': ['feel', 'feeling', 'hard', 'difficult']
            },
            'strategy': {
                'high': ['quarterly', 'long-term', 'strategy', 'goals', 'where am i headed',
                         'big picture', 'priorities', 'direction'],
                'medium': ['should i take this client', 'revenue', 'growth', 'future',
                           'planning', 'decision', 'tradeoff', 'invest'],
                'low': ['career', 'business', 'opportunity', 'risk']
            },
            'health': {
                'high': ['im tired', 'should i take my vyvanse', 'i cant focus', 'supplements',
                         'i crashed', 'energy', 'sleep', 'medication'],
                'medium': ['exhausted', 'fatigue', 'focus', 'concentration', 'adhd',
                           'stimulant', 'caffeine', 'workout', 'exercise'],
                'low': ['rest', 'break', 'recovery', 'burnout']
            }
        }

        agent_triggers = {
            'ops': ['@ops', 'operational'],
            'coach': ['@coach', 'patterns'],
            'strategy': ['@strategy', 'strategic'],
            'health': ['@health', 'wellness']
        }

        # Initialize both matchers
        self.legacy_matcher = LegacyKeywordMatcher(agent_keywords, agent_triggers)
        self.optimized_matcher = KeywordMatcher(agent_keywords, agent_triggers)

        # Print configuration
        print("\n" + "=" * 80)
        print("BENCHMARK CONFIGURATION")
        print("=" * 80)
        print(f"Total keywords: {self.legacy_matcher.total_keywords}")
        print(f"Agents: {len(agent_keywords)}")
        print(f"Iterations per test: {self.iterations:,}")

        # Get optimized matcher info
        info = self.optimized_matcher.get_pattern_info()
        print(f"\nOptimized matcher pattern length: {info['pattern_length']} characters")
        print()

    def _time_function(self, func, *args, **kwargs) -> float:
        """Time a function call in microseconds.

        Args:
            func: Function to time
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Execution time in microseconds
        """
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        return (end - start) * 1_000_000

    def _run_comparison(self, messages: List[str], label: str) -> Dict:
        """Run comparison for a set of messages.

        Args:
            messages: List of test messages
            label: Label for this test

        Returns:
            Dictionary with timing results for both implementations
        """
        legacy_timings = []
        optimized_timings = []

        for _ in range(self.iterations):
            for message in messages:
                # Time legacy implementation
                legacy_time = self._time_function(self.legacy_matcher.match, message)
                legacy_timings.append(legacy_time)

                # Time optimized implementation
                optimized_time = self._time_function(self.optimized_matcher.match, message)
                optimized_timings.append(optimized_time)

        # Calculate statistics
        legacy_timings.sort()
        optimized_timings.sort()

        legacy_mean = mean(legacy_timings)
        optimized_mean = mean(optimized_timings)
        speedup = legacy_mean / optimized_mean if optimized_mean > 0 else 0

        return {
            'label': label,
            'iterations': len(legacy_timings),
            'legacy': {
                'mean_us': legacy_mean,
                'median_us': median(legacy_timings),
                'min_us': min(legacy_timings),
                'max_us': max(legacy_timings),
                'stddev_us': stdev(legacy_timings) if len(legacy_timings) > 1 else 0,
                'p95_us': legacy_timings[int(len(legacy_timings) * 0.95)],
                'p99_us': legacy_timings[int(len(legacy_timings) * 0.99)],
            },
            'optimized': {
                'mean_us': optimized_mean,
                'median_us': median(optimized_timings),
                'min_us': min(optimized_timings),
                'max_us': max(optimized_timings),
                'stddev_us': stdev(optimized_timings) if len(optimized_timings) > 1 else 0,
                'p95_us': optimized_timings[int(len(optimized_timings) * 0.95)],
                'p99_us': optimized_timings[int(len(optimized_timings) * 0.99)],
            },
            'speedup': speedup,
            'improvement_percent': ((legacy_mean - optimized_mean) / legacy_mean * 100) if legacy_mean > 0 else 0
        }

    def benchmark_short_messages(self) -> Dict:
        """Benchmark with short messages (1-5 words)."""
        messages = [
            "help me plan",
            "what should i do",
            "im overwhelmed",
            "task list",
            "schedule today",
        ]
        return self._run_comparison(messages, "Short messages (1-5 words)")

    def benchmark_medium_messages(self) -> Dict:
        """Benchmark with medium messages (10-20 words)."""
        messages = [
            "I need help planning my day and figuring out what to prioritize",
            "Can you help me organize my tasks for the week ahead",
            "I'm feeling overwhelmed with everything on my plate right now",
            "What should I focus on today to make the most progress",
            "I keep procrastinating on this important project, why cant I just start",
        ]
        return self._run_comparison(messages, "Medium messages (10-20 words)")

    def benchmark_long_messages(self) -> Dict:
        """Benchmark with long messages (40+ words)."""
        messages = [
            "I've been trying to get better at planning my day but I keep finding myself "
            "overwhelmed by all the different things I need to do. I have client work, "
            "personal projects, and family commitments all competing for my attention. "
            "Can you help me figure out what to prioritize and how to structure my day?",

            "I keep noticing this pattern where I commit to doing something important like "
            "working out or deep work sessions but then I find excuses to avoid it. I know "
            "this is self-sabotage but I can't seem to break the cycle.",
        ]
        return self._run_comparison(messages, "Long messages (40+ words)")

    def benchmark_keyword_density(self) -> Dict:
        """Benchmark with varying keyword densities."""
        messages = [
            # High density - multiple keywords
            "I need help planning my tasks and schedule for today but I'm feeling overwhelmed",

            # Low density - few keywords
            "I would appreciate assistance with regard to the matter we discussed",

            # No keywords
            "The quick brown fox jumps over the lazy dog",
        ]
        return self._run_comparison(messages, "Keyword density variations")

    def benchmark_edge_cases(self) -> Dict:
        """Benchmark with edge cases."""
        messages = [
            "",  # Empty
            "a",  # Single char
            "x" * 1000,  # Very long, no keywords
        ]
        return self._run_comparison(messages, "Edge cases")

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

        return results

    def print_results(self, results: List[Dict]):
        """Print benchmark results in a readable format.

        Args:
            results: List of benchmark result dictionaries
        """
        print("\n" + "=" * 80)
        print("PERFORMANCE COMPARISON: OLD vs NEW")
        print("=" * 80)
        print()

        for result in results:
            print(f"{result['label']}")
            print("-" * 80)
            print(f"  Total iterations:  {result['iterations']:,}")
            print()

            print(f"  OLD (O(n*m) nested loops):")
            print(f"    Mean:            {result['legacy']['mean_us']:>8.2f} μs  ({result['legacy']['mean_us']/1000:.3f} ms)")
            print(f"    Median:          {result['legacy']['median_us']:>8.2f} μs")
            print(f"    95th percentile: {result['legacy']['p95_us']:>8.2f} μs")
            print()

            print(f"  NEW (O(m) pre-compiled regex):")
            print(f"    Mean:            {result['optimized']['mean_us']:>8.2f} μs  ({result['optimized']['mean_us']/1000:.3f} ms)")
            print(f"    Median:          {result['optimized']['median_us']:>8.2f} μs")
            print(f"    95th percentile: {result['optimized']['p95_us']:>8.2f} μs")
            print()

            print(f"  SPEEDUP:           {result['speedup']:.2f}x faster")
            print(f"  IMPROVEMENT:       {result['improvement_percent']:.1f}% reduction in time")
            print()

        # Calculate overall statistics
        overall_legacy_mean = mean([r['legacy']['mean_us'] for r in results])
        overall_optimized_mean = mean([r['optimized']['mean_us'] for r in results])
        overall_speedup = overall_legacy_mean / overall_optimized_mean

        print("=" * 80)
        print("OVERALL SUMMARY")
        print("=" * 80)
        print(f"Average OLD implementation:       {overall_legacy_mean:>8.2f} μs  ({overall_legacy_mean/1000:.3f} ms)")
        print(f"Average NEW implementation:       {overall_optimized_mean:>8.2f} μs  ({overall_optimized_mean/1000:.3f} ms)")
        print(f"Overall speedup:                  {overall_speedup:.2f}x faster")
        print(f"Overall improvement:              {((overall_legacy_mean - overall_optimized_mean) / overall_legacy_mean * 100):.1f}%")
        print("=" * 80)
        print()

    def save_results(self, results: List[Dict], filename: str = "comparison_results.json"):
        """Save results to a JSON file.

        Args:
            results: List of benchmark result dictionaries
            filename: Output filename
        """
        output_path = project_root / ".auto-claude" / "specs" / "022-pre-compile-agent-keyword-patterns-for-o-1-intent-" / filename

        # Calculate overall stats
        overall_legacy_mean = mean([r['legacy']['mean_us'] for r in results])
        overall_optimized_mean = mean([r['optimized']['mean_us'] for r in results])
        overall_speedup = overall_legacy_mean / overall_optimized_mean

        output = {
            'benchmark_type': 'implementation_comparison',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'iterations': self.iterations,
            'total_keywords': self.legacy_matcher.total_keywords,
            'implementations': {
                'legacy': {
                    'description': 'Nested loops with substring checks',
                    'complexity': 'O(n*m) where n=keywords, m=message length',
                    'method': 'Python "in" operator for each keyword'
                },
                'optimized': {
                    'description': 'Pre-compiled regex with alternation groups',
                    'complexity': 'O(m) where m=message length',
                    'method': 'Single regex.finditer() call'
                }
            },
            'overall_summary': {
                'legacy_mean_us': overall_legacy_mean,
                'optimized_mean_us': overall_optimized_mean,
                'speedup': overall_speedup,
                'improvement_percent': ((overall_legacy_mean - overall_optimized_mean) / overall_legacy_mean * 100)
            },
            'detailed_results': results
        }

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Results saved to: {output_path}")


def main():
    """Main entry point for comparison benchmark."""
    iterations = 1000
    if len(sys.argv) > 1:
        try:
            iterations = int(sys.argv[1])
        except ValueError:
            print(f"Invalid iteration count: {sys.argv[1]}")
            print("Usage: bench_comparison.py [iterations]")
            sys.exit(1)

    print(f"Starting benchmark comparison with {iterations} iterations per test...")

    benchmark = BenchmarkComparison(iterations=iterations)
    results = benchmark.run_all_benchmarks()
    benchmark.print_results(results)
    benchmark.save_results(results)


if __name__ == "__main__":
    main()
