"""
Pytest configuration and shared fixtures for MCP integration tests.

Provides fixtures for:
- Real MCP server connections
- Test configuration
- Performance measurement utilities
- Cleanup management
"""

import asyncio
import json
import logging
import os
import pytest
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging for integration tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring real MCP servers"
    )
    config.addinivalue_line(
        "markers", "benchmark: Performance benchmark tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running tests (> 5 seconds)"
    )


# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ============================================================================
# Test Configuration
# ============================================================================


@pytest.fixture(scope="session")
def integration_test_config() -> Dict[str, Any]:
    """Load integration test configuration."""
    config = {
        "timeout": int(os.getenv("MCP_TEST_TIMEOUT", "30")),
        "benchmark_iterations": int(os.getenv("MCP_TEST_ITERATIONS", "5")),
        "concurrent_calls": int(os.getenv("MCP_TEST_CONCURRENT", "10")),
        "enable_performance_tests": os.getenv("MCP_TEST_PERFORMANCE", "true").lower() == "true",
    }

    logger.info(f"Integration test configuration: {config}")
    return config


@pytest.fixture(scope="session")
def test_environment() -> Dict[str, str]:
    """Gather test environment information."""
    env = {
        "database_url": os.getenv("DATABASE_URL", ""),
        "workos_database_url": os.getenv("WORKOS_DATABASE_URL", ""),
        "workos_mcp_path": os.getenv("WORKOS_MCP_PATH", ""),
        "node_env": os.getenv("NODE_ENV", "test"),
        "ci": os.getenv("CI", "false"),
    }

    # Sanitize for logging (hide passwords)
    sanitized = env.copy()
    for key in ["database_url", "workos_database_url"]:
        if sanitized[key] and "://" in sanitized[key]:
            parts = sanitized[key].split("://")
            if "@" in parts[1]:
                auth, host = parts[1].split("@")
                sanitized[key] = f"{parts[0]}://***@{host}"

    logger.info(f"Test environment: {sanitized}")
    return env


# ============================================================================
# Performance Measurement Utilities
# ============================================================================


@pytest.fixture
def performance_timer():
    """Context manager for timing operations."""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, *args):
            self.elapsed = time.time() - self.start_time

        def __call__(self):
            """Get elapsed time in seconds."""
            if self.elapsed is None:
                raise RuntimeError("Timer not used as context manager")
            return self.elapsed

        @property
        def ms(self) -> float:
            """Get elapsed time in milliseconds."""
            return self.elapsed * 1000 if self.elapsed else 0

    return Timer


@pytest.fixture
def benchmark_logger():
    """Helper for logging benchmark results."""
    def log_benchmark(
        name: str,
        times: list[float],
        unit: str = "ms",
        multiplier: float = 1000.0
    ):
        """Log benchmark statistics."""
        if not times:
            logger.warning(f"No timing data for {name}")
            return

        times_ms = [t * multiplier for t in times]
        avg = sum(times_ms) / len(times_ms)
        min_time = min(times_ms)
        max_time = max(times_ms)

        # Calculate percentiles if enough data
        if len(times_ms) >= 10:
            sorted_times = sorted(times_ms)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]

            logger.info(f"\n{name} Performance:")
            logger.info(f"  Iterations: {len(times_ms)}")
            logger.info(f"  Average:    {avg:.2f}{unit}")
            logger.info(f"  Min:        {min_time:.2f}{unit}")
            logger.info(f"  Max:        {max_time:.2f}{unit}")
            logger.info(f"  p50:        {p50:.2f}{unit}")
            logger.info(f"  p95:        {p95:.2f}{unit}")
            logger.info(f"  p99:        {p99:.2f}{unit}")
        else:
            logger.info(f"\n{name} Performance:")
            logger.info(f"  Iterations: {len(times_ms)}")
            logger.info(f"  Average:    {avg:.2f}{unit}")
            logger.info(f"  Min:        {min_time:.2f}{unit}")
            logger.info(f"  Max:        {max_time:.2f}{unit}")

    return log_benchmark


# ============================================================================
# Cleanup Management
# ============================================================================


@pytest.fixture
def cleanup_tasks():
    """Track cleanup tasks to run after test."""
    tasks = []

    def register(coro):
        """Register a coroutine to run during cleanup."""
        tasks.append(coro)

    yield register

    # Run cleanup tasks
    loop = asyncio.get_event_loop()
    for task in tasks:
        try:
            loop.run_until_complete(task)
        except Exception as e:
            logger.warning(f"Cleanup task failed: {e}")


# ============================================================================
# Test Data Helpers
# ============================================================================


@pytest.fixture
def sample_test_data() -> Dict[str, Any]:
    """Provide sample test data for tool calls."""
    return {
        "task": {
            "title": "Integration Test Task",
            "description": "Created by integration test",
            "priority": "medium",
            "status": "active",
        },
        "habit": {
            "name": "Test Habit",
            "frequency": "daily",
            "target": 1,
        },
        "metric": {
            "date": "2024-01-01",
            "completed_tasks": 5,
            "completed_habits": 3,
        }
    }


# ============================================================================
# Test Results Collection
# ============================================================================


@pytest.fixture(scope="session")
def test_results():
    """Collect test results for reporting."""
    results = {
        "passed": [],
        "failed": [],
        "skipped": [],
        "benchmarks": {},
    }

    yield results

    # Log summary at end of session
    logger.info("\n" + "="*60)
    logger.info("INTEGRATION TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Passed:  {len(results['passed'])}")
    logger.info(f"Failed:  {len(results['failed'])}")
    logger.info(f"Skipped: {len(results['skipped'])}")

    if results['benchmarks']:
        logger.info("\nBenchmark Results:")
        for name, times in results['benchmarks'].items():
            if times:
                avg = sum(times) / len(times) * 1000
                logger.info(f"  {name}: {avg:.2f}ms avg ({len(times)} runs)")


# ============================================================================
# Conditional Imports and Availability Checks
# ============================================================================


@pytest.fixture(scope="session")
def mcp_sdk_available() -> bool:
    """Check if MCP SDK is available."""
    try:
        import mcp
        from Tools.adapters.mcp_bridge import MCPBridge
        return True
    except ImportError:
        return False


@pytest.fixture(scope="session")
def workos_server_info(test_environment) -> Optional[Dict[str, str]]:
    """Get WorkOS server information if available."""
    server_path = test_environment["workos_mcp_path"]

    if not server_path:
        # Try default location
        default_path = Path.home() / "Projects/Thanos/mcp-servers/workos-mcp/dist/index.js"
        if default_path.exists():
            server_path = str(default_path)

    if server_path and not server_path.startswith("${"):
        path = Path(server_path)
        if path.exists():
            return {
                "path": str(path),
                "exists": True,
                "size": path.stat().st_size,
            }

    return None


# ============================================================================
# Retry Utilities
# ============================================================================


@pytest.fixture
def retry_on_failure():
    """Helper to retry flaky operations."""
    async def retry(
        coro_func,
        max_attempts: int = 3,
        delay: float = 1.0,
        exceptions: tuple = (Exception,)
    ):
        """Retry an async operation on failure."""
        for attempt in range(max_attempts):
            try:
                return await coro_func()
            except exceptions as e:
                if attempt == max_attempts - 1:
                    raise
                logger.warning(
                    f"Attempt {attempt+1}/{max_attempts} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)

    return retry


# ============================================================================
# Assertion Helpers
# ============================================================================


@pytest.fixture
def assert_tool_result():
    """Helper for asserting ToolResult properties."""
    def assert_result(
        result,
        success: Optional[bool] = None,
        has_data: Optional[bool] = None,
        has_error: Optional[bool] = None,
    ):
        """Assert properties of a ToolResult."""
        from Tools.adapters.base import ToolResult

        assert isinstance(result, ToolResult), "Result must be a ToolResult"

        if success is not None:
            assert result.success == success, \
                f"Expected success={success}, got {result.success}"

        if has_data is not None:
            if has_data:
                assert result.data is not None, "Expected data but got None"
            else:
                assert result.data is None, f"Expected no data but got {result.data}"

        if has_error is not None:
            if has_error:
                assert result.error is not None, "Expected error but got None"
            else:
                assert result.error is None, f"Expected no error but got {result.error}"

    return assert_result


# ============================================================================
# Logging Helpers
# ============================================================================


@pytest.fixture(autouse=True)
def log_test_info(request):
    """Log test information at start and end."""
    test_name = request.node.name
    logger.info(f"\n{'='*60}")
    logger.info(f"Starting test: {test_name}")
    logger.info(f"{'='*60}")

    yield

    logger.info(f"{'='*60}")
    logger.info(f"Completed test: {test_name}")
    logger.info(f"{'='*60}\n")


# ============================================================================
# Skip Conditions
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add skip markers."""
    # Skip integration tests if MCP not available
    try:
        import mcp
        from Tools.adapters.mcp_bridge import MCPBridge
        mcp_available = True
    except ImportError:
        mcp_available = False

    if not mcp_available:
        skip_mcp = pytest.mark.skip(reason="MCP SDK not available")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_mcp)

    # Skip benchmarks in CI unless explicitly enabled
    if os.getenv("CI") == "true" and os.getenv("RUN_BENCHMARKS") != "true":
        skip_benchmark = pytest.mark.skip(reason="Benchmarks disabled in CI")
        for item in items:
            if "benchmark" in item.keywords:
                item.add_marker(skip_benchmark)
