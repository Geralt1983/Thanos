#!/usr/bin/env python3
"""
Thanos v2.0 Performance Benchmarking Suite
Comprehensive performance testing across all system components.
"""

import time
import timeit
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.command_router import CommandRouter
from Tools.state_reader import StateReader
from Tools.unified_state import StateStore
from Tools.session_manager import SessionManager
from Tools.alert_checker import AlertManager


@dataclass
class BenchmarkResult:
    """Results from a single benchmark."""
    component: str
    operation: str
    mean_time_ms: float
    std_dev_ms: float
    min_time_ms: float
    max_time_ms: float
    iterations: int
    throughput_ops_sec: float
    memory_mb: float = 0.0
    success_rate: float = 100.0


class PerformanceBenchmark:
    """Main benchmarking coordinator."""

    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.thanos_root = Path.home() / "Projects" / "Thanos"

    def measure(self, func: Callable, iterations: int = 100) -> Dict[str, float]:
        """Measure function performance over multiple iterations."""
        times = []
        failures = 0

        for _ in range(iterations):
            start = time.perf_counter()
            try:
                func()
            except Exception as e:
                failures += 1
                continue
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms

        if not times:
            return {
                "mean": 0.0,
                "std_dev": 0.0,
                "min": 0.0,
                "max": 0.0,
                "success_rate": 0.0
            }

        return {
            "mean": statistics.mean(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0.0,
            "min": min(times),
            "max": max(times),
            "success_rate": ((iterations - failures) / iterations) * 100
        }

    def benchmark_command_router(self):
        """Phase 1: Command Router Performance."""
        print("\n=== PHASE 1: Command Router Benchmarks ===")

        router = CommandRouter()

        # Test 1: Classification speed
        test_inputs = [
            "Add a task to review the quarterly report",
            "What's on my calendar today?",
            "I'm feeling overwhelmed",
            "Help me plan my morning",
            "I'm wondering about career changes"
        ]

        def classify_batch():
            for inp in test_inputs:
                router.classify_input(inp)

        metrics = self.measure(classify_batch, iterations=50)
        self.results.append(BenchmarkResult(
            component="CommandRouter",
            operation="Classification (5 inputs)",
            mean_time_ms=metrics["mean"],
            std_dev_ms=metrics["std_dev"],
            min_time_ms=metrics["min"],
            max_time_ms=metrics["max"],
            iterations=50,
            throughput_ops_sec=5000 / metrics["mean"] if metrics["mean"] > 0 else 0,
            success_rate=metrics["success_rate"]
        ))

        # Test 2: State file reading
        state_reader = StateReader()

        def read_state():
            state_reader.get_current_state()

        metrics = self.measure(read_state, iterations=100)
        self.results.append(BenchmarkResult(
            component="StateReader",
            operation="Read Current State",
            mean_time_ms=metrics["mean"],
            std_dev_ms=metrics["std_dev"],
            min_time_ms=metrics["min"],
            max_time_ms=metrics["max"],
            iterations=100,
            throughput_ops_sec=1000 / metrics["mean"] if metrics["mean"] > 0 else 0,
            success_rate=metrics["success_rate"]
        ))

        # Test 3: StateStore performance
        store = StateStore()

        def state_store_tasks():
            store.get_tasks_due_today()

        metrics = self.measure(state_store_tasks, iterations=100)
        self.results.append(BenchmarkResult(
            component="StateStore",
            operation="Get Tasks Due Today",
            mean_time_ms=metrics["mean"],
            std_dev_ms=metrics["std_dev"],
            min_time_ms=metrics["min"],
            max_time_ms=metrics["max"],
            iterations=100,
            throughput_ops_sec=1000 / metrics["mean"] if metrics["mean"] > 0 else 0,
            success_rate=metrics["success_rate"]
        ))

    def benchmark_operator_daemon(self):
        """Phase 3: Operator Daemon Performance."""
        print("\n=== PHASE 3: Operator Daemon Benchmarks ===")

        # Test 1: Alert manager initialization
        def init_alert_manager():
            AlertManager()

        metrics = self.measure(init_alert_manager, iterations=50)
        self.results.append(BenchmarkResult(
            component="AlertManager",
            operation="Initialization",
            mean_time_ms=metrics["mean"],
            std_dev_ms=metrics["std_dev"],
            min_time_ms=metrics["min"],
            max_time_ms=metrics["max"],
            iterations=50,
            throughput_ops_sec=1000 / metrics["mean"] if metrics["mean"] > 0 else 0,
            success_rate=metrics["success_rate"]
        ))

        # Test 2: SQLite database query performance
        db_path = self.thanos_root / "State" / "unified_state.db"
        if db_path.exists():
            def query_db():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM state_cache LIMIT 10")
                cursor.fetchall()
                conn.close()

            metrics = self.measure(query_db, iterations=100)
            self.results.append(BenchmarkResult(
                component="SQLite",
                operation="Query Cache (10 rows)",
                mean_time_ms=metrics["mean"],
                std_dev_ms=metrics["std_dev"],
                min_time_ms=metrics["min"],
                max_time_ms=metrics["max"],
                iterations=100,
                throughput_ops_sec=1000 / metrics["mean"] if metrics["mean"] > 0 else 0,
                success_rate=metrics["success_rate"]
            ))

    def benchmark_session_management(self):
        """Phase 2: Session Management Performance."""
        print("\n=== PHASE 2: Session Management Benchmarks ===")

        # Test 1: Session manager initialization
        def init_session():
            SessionManager()

        metrics = self.measure(init_session, iterations=50)
        self.results.append(BenchmarkResult(
            component="SessionManager",
            operation="Initialization",
            mean_time_ms=metrics["mean"],
            std_dev_ms=metrics["std_dev"],
            min_time_ms=metrics["min"],
            max_time_ms=metrics["max"],
            iterations=50,
            throughput_ops_sec=1000 / metrics["mean"] if metrics["mean"] > 0 else 0,
            success_rate=metrics["success_rate"]
        ))

    def benchmark_file_io(self):
        """System-wide I/O performance."""
        print("\n=== System-Wide: File I/O Benchmarks ===")

        # Test 1: State file read
        state_file = self.thanos_root / "State" / "CurrentFocus.md"

        def read_focus():
            if state_file.exists():
                state_file.read_text()

        metrics = self.measure(read_focus, iterations=200)
        self.results.append(BenchmarkResult(
            component="FileSystem",
            operation="Read CurrentFocus.md",
            mean_time_ms=metrics["mean"],
            std_dev_ms=metrics["std_dev"],
            min_time_ms=metrics["min"],
            max_time_ms=metrics["max"],
            iterations=200,
            throughput_ops_sec=1000 / metrics["mean"] if metrics["mean"] > 0 else 0,
            success_rate=metrics["success_rate"]
        ))

        # Test 2: JSON parsing
        time_state = self.thanos_root / "State" / "TimeState.json"

        def parse_json():
            if time_state.exists():
                json.loads(time_state.read_text())

        metrics = self.measure(parse_json, iterations=200)
        self.results.append(BenchmarkResult(
            component="FileSystem",
            operation="Parse TimeState.json",
            mean_time_ms=metrics["mean"],
            std_dev_ms=metrics["std_dev"],
            min_time_ms=metrics["min"],
            max_time_ms=metrics["max"],
            iterations=200,
            throughput_ops_sec=1000 / metrics["mean"] if metrics["mean"] > 0 else 0,
            success_rate=metrics["success_rate"]
        ))

    def benchmark_external_commands(self):
        """External command execution performance."""
        print("\n=== System-Wide: External Commands ===")

        # Test 1: Date command
        def run_date():
            subprocess.run(["date"], capture_output=True, text=True)

        metrics = self.measure(run_date, iterations=50)
        self.results.append(BenchmarkResult(
            component="ExternalCommand",
            operation="date",
            mean_time_ms=metrics["mean"],
            std_dev_ms=metrics["std_dev"],
            min_time_ms=metrics["min"],
            max_time_ms=metrics["max"],
            iterations=50,
            throughput_ops_sec=1000 / metrics["mean"] if metrics["mean"] > 0 else 0,
            success_rate=metrics["success_rate"]
        ))

    def run_all_benchmarks(self):
        """Execute all benchmark suites."""
        print("╔══════════════════════════════════════════════════════╗")
        print("║   THANOS V2.0 PERFORMANCE BENCHMARK SUITE            ║")
        print("╚══════════════════════════════════════════════════════╝")
        print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        start_time = time.time()

        try:
            self.benchmark_command_router()
            self.benchmark_session_management()
            self.benchmark_operator_daemon()
            self.benchmark_file_io()
            self.benchmark_external_commands()
        except Exception as e:
            print(f"\n❌ Benchmark failed: {e}")
            import traceback
            traceback.print_exc()

        total_time = time.time() - start_time

        print(f"\n✓ Benchmarking completed in {total_time:.2f}s")
        print(f"✓ Total benchmarks: {len(self.results)}")

        return self.results

    def generate_report(self) -> str:
        """Generate markdown report."""
        report = []
        report.append("# Thanos v2.0 Performance Benchmarks\n")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**Platform:** macOS (Darwin 24.6.0)\n")
        report.append(f"**Total Benchmarks:** {len(self.results)}\n")

        # Group by component
        by_component: Dict[str, List[BenchmarkResult]] = {}
        for result in self.results:
            if result.component not in by_component:
                by_component[result.component] = []
            by_component[result.component].append(result)

        # Generate tables
        for component, results in by_component.items():
            report.append(f"\n## {component}\n")
            report.append("| Operation | Mean (ms) | Std Dev | Min | Max | Throughput (ops/s) | Success Rate |")
            report.append("|-----------|-----------|---------|-----|-----|-------------------|--------------|")

            for r in results:
                report.append(
                    f"| {r.operation} | {r.mean_time_ms:.2f} | {r.std_dev_ms:.2f} | "
                    f"{r.min_time_ms:.2f} | {r.max_time_ms:.2f} | {r.throughput_ops_sec:.1f} | "
                    f"{r.success_rate:.1f}% |"
                )

        # Performance analysis
        report.append("\n## Performance Analysis\n")

        # Find slowest operations
        sorted_results = sorted(self.results, key=lambda x: x.mean_time_ms, reverse=True)
        report.append("### Slowest Operations\n")
        for r in sorted_results[:5]:
            report.append(f"- **{r.component}.{r.operation}**: {r.mean_time_ms:.2f}ms")

        # Find fastest operations
        report.append("\n### Fastest Operations\n")
        for r in sorted_results[-5:]:
            report.append(f"- **{r.component}.{r.operation}**: {r.mean_time_ms:.2f}ms")

        # Recommendations
        report.append("\n## Recommendations\n")
        report.append("### High Priority\n")

        for r in sorted_results[:3]:
            if r.mean_time_ms > 100:
                report.append(f"- **Optimize {r.component}.{r.operation}**: "
                           f"Currently {r.mean_time_ms:.0f}ms, target <100ms")

        report.append("\n### Optimization Opportunities\n")

        # Identify high variance
        high_variance = [r for r in self.results if r.std_dev_ms > r.mean_time_ms * 0.5]
        if high_variance:
            report.append("#### High Variance (Inconsistent Performance)\n")
            for r in high_variance:
                report.append(f"- {r.component}.{r.operation}: "
                           f"±{r.std_dev_ms:.1f}ms variance")

        # Success rate issues
        low_success = [r for r in self.results if r.success_rate < 100]
        if low_success:
            report.append("\n#### Reliability Issues\n")
            for r in low_success:
                report.append(f"- {r.component}.{r.operation}: "
                           f"{r.success_rate:.1f}% success rate")

        return "\n".join(report)


def main():
    """Run benchmarks and generate report."""
    benchmark = PerformanceBenchmark()
    benchmark.run_all_benchmarks()

    # Generate report
    report = benchmark.generate_report()

    # Save to file
    output_path = Path(__file__).parent / "PERFORMANCE_BENCHMARKS.md"
    output_path.write_text(report)

    print(f"\n📊 Report saved to: {output_path}")
    print("\n" + "="*60)
    print(report)
    print("="*60)

    # Also save JSON data
    json_path = Path(__file__).parent / "benchmark_results.json"
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "results": [asdict(r) for r in benchmark.results]
    }
    json_path.write_text(json.dumps(json_data, indent=2))
    print(f"\n📈 Raw data saved to: {json_path}")


if __name__ == "__main__":
    main()
