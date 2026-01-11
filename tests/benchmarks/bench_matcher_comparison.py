#!/usr/bin/env python3
"""
Benchmark comparison: Regex vs Trie-based keyword matching.

This benchmark compares the performance of:
1. KeywordMatcher: Regex-based with pre-compiled patterns (O(m))
2. TrieKeywordMatcher: Aho-Corasick trie-based (O(m + z))

Usage:
    python tests/benchmarks/bench_matcher_comparison.py [iterations]

Example:
    python tests/benchmarks/bench_matcher_comparison.py 1000  # Run 1000 iterations
"""

import sys
import time
from pathlib import Path
from typing import List, Dict
from statistics import mean, median, stdev
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.intent_matcher import KeywordMatcher, TrieKeywordMatcher
from Tools.thanos_orchestrator import ThanosOrchestrator


class MatcherComparisonBenchmark:
    """Benchmark suite comparing regex vs trie-based matchers."""

    def __init__(self, iterations: int = 1000):
        """Initialize benchmark with specified iteration count.

        Args:
            iterations: Number of iterations per test case
        """
        self.iterations = iterations
        self.keywords = None
        self.triggers = None
        self.regex_matcher = None
        self.trie_matcher = None

    def setup(self):
        """Set up test environment with both matchers."""
        # Load keywords from ThanosOrchestrator for realistic testing
        orchestrator = ThanosOrchestrator(base_dir=str(project_root))

        # Extract keywords and triggers from orchestrator
        self.keywords = {
            'ops': {
                'high': [
                    'what should i do', 'what do i do', 'what to do',
                    'how do i', 'how should i',
                    'overwhelmed', 'swamped', 'drowning',
                    'prioritize', 'priorities', 'priority'
                ],
                'medium': [
                    'task', 'tasks', 'todo', 'to-do', 'to do',
                    'schedule', 'calendar', 'agenda',
                    'plan', 'planning',
                    'today', 'tomorrow', 'this week',
                    'organize', 'organizing'
                ],
                'low': [
                    'busy', 'swamped', 'loaded',
                    'work', 'working',
                    'meeting', 'meetings',
                    'deadline', 'deadlines',
                    'email', 'emails'
                ]
            },
            'coach': {
                'high': [
                    'i keep doing this', 'i keep', 'keep doing',
                    'pattern', 'patterns', 'repeating',
                    'accountability', 'accountable',
                    'self-sabotage', 'sabotaging',
                    'procrastinating', 'procrastination'
                ],
                'medium': [
                    'habit', 'habits',
                    'stuck', 'blocked',
                    'motivation', 'motivated',
                    'discipline', 'disciplined',
                    'commitment', 'committed',
                    'follow through'
                ],
                'low': [
                    'feel', 'feeling', 'felt',
                    'avoid', 'avoiding', 'avoidance',
                    'resistance',
                    'mindset'
                ]
            },
            'strategy': {
                'high': [
                    'long-term', 'long term',
                    'strategy', 'strategic',
                    'goals', 'goal', 'objective', 'objectives',
                    'direction', 'roadmap',
                    'should i', 'or should i'
                ],
                'medium': [
                    'revenue', 'income', 'money',
                    'growth', 'growing', 'scale', 'scaling',
                    'decision', 'decide', 'choice',
                    'client', 'clients', 'customer', 'customers',
                    'business', 'company'
                ],
                'low': [
                    'career', 'job',
                    'opportunity', 'opportunities',
                    'market', 'industry',
                    'competition', 'competitive'
                ]
            },
            'health': {
                'high': [
                    'im tired', "i'm tired", 'so tired',
                    'i cant focus', "i can't focus", 'cant focus',
                    'energy', 'energized', 'depleted',
                    'crashed', 'crashing', 'crash'
                ],
                'medium': [
                    'exhausted', 'exhausting',
                    'fatigue', 'fatigued',
                    'focus', 'focused', 'focusing',
                    'sleep', 'sleeping', 'slept',
                    'rest', 'resting'
                ],
                'low': [
                    'tired', 'sleepy',
                    'break', 'breaks',
                    'exercise', 'workout',
                    'eat', 'eating', 'food'
                ]
            }
        }

        self.triggers = {
            'ops': ['urgent', 'asap', 'immediately', 'right now'],
            'health': ['medication', 'vyvanse', 'adderall', 'meds']
        }

        # Initialize both matchers
        self.regex_matcher = KeywordMatcher(self.keywords, self.triggers)
        self.trie_matcher = TrieKeywordMatcher(self.keywords, self.triggers)

        # Print matcher info
        print("\nMatcher Configuration:")
        print("=" * 80)

        regex_info = self.regex_matcher.get_pattern_info()
        print(f"\nKeywordMatcher (Regex):")
        print(f"  Total keywords: {regex_info['total_keywords']}")
        print(f"  Pattern length: {regex_info['pattern_length']} characters")
        print(f"  Agents: {', '.join(regex_info['agents'].keys())}")
        for agent, count in regex_info['agents'].items():
            print(f"    - {agent}: {count} keywords")

        trie_info = self.trie_matcher.get_pattern_info()
        print(f"\nTrieKeywordMatcher (Aho-Corasick):")
        print(f"  Total keywords: {trie_info['total_keywords']}")
        print(f"  Matcher type: {trie_info.get('matcher_type', 'trie')}")
        print(f"  Agents: {', '.join(trie_info['agents'].keys())}")
        for agent, count in trie_info['agents'].items():
            print(f"    - {agent}: {count} keywords")
        print()

    def teardown(self):
        """Clean up test environment."""
        self.regex_matcher = None
        self.trie_matcher = None

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
        """Run benchmark for both matchers on a set of messages.

        Args:
            messages: List of messages to test
            label: Label for this benchmark

        Returns:
            Dictionary with timing statistics for both matchers
        """
        regex_timings = []
        trie_timings = []

        for _ in range(self.iterations):
            for message in messages:
                # Time regex matcher
                regex_time = self._time_function(
                    self.regex_matcher.match,
                    message
                )
                regex_timings.append(regex_time)

                # Time trie matcher
                trie_time = self._time_function(
                    self.trie_matcher.match,
                    message
                )
                trie_timings.append(trie_time)

        # Calculate statistics for both
        regex_timings.sort()
        trie_timings.sort()

        return {
            'label': label,
            'iterations': len(regex_timings),
            'regex': {
                'mean_us': mean(regex_timings),
                'median_us': median(regex_timings),
                'min_us': min(regex_timings),
                'max_us': max(regex_timings),
                'stddev_us': stdev(regex_timings) if len(regex_timings) > 1 else 0,
                'p95_us': regex_timings[int(len(regex_timings) * 0.95)],
                'p99_us': regex_timings[int(len(regex_timings) * 0.99)],
            },
            'trie': {
                'mean_us': mean(trie_timings),
                'median_us': median(trie_timings),
                'min_us': min(trie_timings),
                'max_us': max(trie_timings),
                'stddev_us': stdev(trie_timings) if len(trie_timings) > 1 else 0,
                'p95_us': trie_timings[int(len(trie_timings) * 0.95)],
                'p99_us': trie_timings[int(len(trie_timings) * 0.99)],
            },
            'speedup': {
                'mean': mean(regex_timings) / mean(trie_timings) if mean(trie_timings) > 0 else 0,
                'median': median(regex_timings) / median(trie_timings) if median(trie_timings) > 0 else 0,
            }
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

            "I keep doing this and feel stuck in a pattern where I commit to doing something important like "
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
        print("MATCHER COMPARISON BENCHMARK: REGEX vs TRIE")
        print("=" * 80)
        print(f"Iterations per test case: {self.iterations}")
        print()

        for result in results:
            print(f"{result['label']}")
            print("-" * 80)
            print(f"  Total iterations:  {result['iterations']:,}")
            print()

            print("  Regex Matcher:")
            regex = result['regex']
            print(f"    Mean time:         {regex['mean_us']:>8.2f} μs  ({regex['mean_us']/1000:.3f} ms)")
            print(f"    Median time:       {regex['median_us']:>8.2f} μs  ({regex['median_us']/1000:.3f} ms)")
            print(f"    Std deviation:     {regex['stddev_us']:>8.2f} μs")
            print(f"    Min time:          {regex['min_us']:>8.2f} μs")
            print(f"    Max time:          {regex['max_us']:>8.2f} μs")
            print(f"    95th percentile:   {regex['p95_us']:>8.2f} μs")
            print(f"    99th percentile:   {regex['p99_us']:>8.2f} μs")
            print()

            print("  Trie Matcher (Aho-Corasick):")
            trie = result['trie']
            print(f"    Mean time:         {trie['mean_us']:>8.2f} μs  ({trie['mean_us']/1000:.3f} ms)")
            print(f"    Median time:       {trie['median_us']:>8.2f} μs  ({trie['median_us']/1000:.3f} ms)")
            print(f"    Std deviation:     {trie['stddev_us']:>8.2f} μs")
            print(f"    Min time:          {trie['min_us']:>8.2f} μs")
            print(f"    Max time:          {trie['max_us']:>8.2f} μs")
            print(f"    95th percentile:   {trie['p95_us']:>8.2f} μs")
            print(f"    99th percentile:   {trie['p99_us']:>8.2f} μs")
            print()

            speedup = result['speedup']
            print(f"  Speedup (Regex/Trie):")
            print(f"    Mean speedup:      {speedup['mean']:>8.2f}x")
            print(f"    Median speedup:    {speedup['median']:>8.2f}x")

            if speedup['mean'] > 1:
                print(f"    → Trie is {speedup['mean']:.2f}x FASTER")
            elif speedup['mean'] < 1:
                print(f"    → Regex is {1/speedup['mean']:.2f}x FASTER")
            else:
                print(f"    → Performance is EQUAL")
            print()

        # Calculate overall statistics
        regex_means = [r['regex']['mean_us'] for r in results]
        trie_means = [r['trie']['mean_us'] for r in results]
        overall_speedup = mean(regex_means) / mean(trie_means) if mean(trie_means) > 0 else 0

        print("=" * 80)
        print(f"Overall Results:")
        print(f"  Regex mean across all tests:  {mean(regex_means):>8.2f} μs ({mean(regex_means)/1000:.3f} ms)")
        print(f"  Trie mean across all tests:   {mean(trie_means):>8.2f} μs ({mean(trie_means)/1000:.3f} ms)")
        print(f"  Overall speedup:              {overall_speedup:>8.2f}x")

        if overall_speedup > 1:
            print(f"\n  🏆 Winner: Trie matcher is {overall_speedup:.2f}x faster overall")
        elif overall_speedup < 1:
            print(f"\n  🏆 Winner: Regex matcher is {1/overall_speedup:.2f}x faster overall")
        else:
            print(f"\n  🤝 Tie: Both matchers have equal performance")

        print("=" * 80)
        print()

    def save_results(self, results: List[Dict], filename: str = "matcher_comparison.json"):
        """Save results to a JSON file.

        Args:
            results: List of benchmark result dictionaries
            filename: Output filename
        """
        output_path = project_root / ".auto-claude" / "specs" / "022-pre-compile-agent-keyword-patterns-for-o-1-intent-" / filename

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Calculate overall statistics
        regex_means = [r['regex']['mean_us'] for r in results]
        trie_means = [r['trie']['mean_us'] for r in results]
        overall_speedup = mean(regex_means) / mean(trie_means) if mean(trie_means) > 0 else 0

        # Add metadata
        output = {
            'benchmark_type': 'matcher_comparison',
            'description': 'Performance comparison between regex and trie-based matchers',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'iterations': self.iterations,
            'overall_statistics': {
                'regex_mean_us': mean(regex_means),
                'trie_mean_us': mean(trie_means),
                'overall_speedup': overall_speedup,
                'winner': 'trie' if overall_speedup > 1 else 'regex' if overall_speedup < 1 else 'tie'
            },
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
            print("Usage: bench_matcher_comparison.py [iterations]")
            sys.exit(1)

    print(f"Starting matcher comparison benchmark with {iterations} iterations per test...")

    benchmark = MatcherComparisonBenchmark(iterations=iterations)
    results = benchmark.run_all_benchmarks()
    benchmark.print_results(results)
    benchmark.save_results(results)


if __name__ == "__main__":
    main()
