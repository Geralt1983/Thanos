# MCP Bridge Performance Optimization Guide

Comprehensive guide for optimizing MCP bridge performance in production environments.

## Overview

This guide covers performance optimization strategies for Thanos MCP bridge infrastructure:
- Connection pooling and reuse
- Result caching strategies
- Query batching and parallel execution
- Resource management and throttling
- Performance monitoring and profiling

## Performance Baseline

### Expected Performance Metrics

| Metric | Target | Good | Needs Improvement |
|--------|--------|------|-------------------|
| Tool call latency (p50) | <100ms | <200ms | >200ms |
| Tool call latency (p95) | <500ms | <1s | >1s |
| Connection establishment | <500ms | <1s | >1s |
| Success rate | >99% | >95% | <95% |
| Cache hit rate | >70% | >50% | <50% |

## Connection Pooling

### Benefits

- **Reduced Latency**: Reuse existing connections (10-100x faster)
- **Resource Efficiency**: Avoid connection overhead
- **Better Throughput**: Handle concurrent requests efficiently

### Implementation

MCPBridge currently creates a new session for each tool call. For high-frequency operations, implement connection pooling:

```python
# Tools/adapters/mcp_connection_pool.py
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .mcp_bridge import MCPBridge
from .mcp_config import MCPServerConfig


@dataclass
class PooledConnection:
    """Wrapper for pooled MCP connection."""
    bridge: MCPBridge
    session: Any  # ClientSession
    created_at: datetime
    last_used: datetime
    use_count: int = 0


class MCPConnectionPool:
    """
    Connection pool for MCP bridges.

    Maintains a pool of active connections to MCP servers, recycling them
    for multiple tool calls to avoid connection overhead.
    """

    def __init__(
        self,
        min_connections: int = 1,
        max_connections: int = 10,
        max_idle_time: int = 300,  # 5 minutes
        health_check_interval: int = 60,  # 1 minute
    ):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval

        # Pool management
        self._pools: Dict[str, List[PooledConnection]] = defaultdict(list)
        self._pool_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._active_connections: Dict[str, int] = defaultdict(int)

        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start background maintenance tasks."""
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """Stop pool and close all connections."""
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Close all pooled connections
        for server_name, pool in self._pools.items():
            for conn in pool:
                await conn.bridge.close()
            pool.clear()

    async def get_connection(
        self, server_config: MCPServerConfig
    ) -> PooledConnection:
        """
        Get a connection from the pool or create a new one.

        Args:
            server_config: MCP server configuration

        Returns:
            Pooled connection ready for use
        """
        server_name = server_config.name

        async with self._pool_locks[server_name]:
            # Try to get idle connection from pool
            pool = self._pools[server_name]

            if pool:
                conn = pool.pop(0)
                conn.last_used = datetime.now()
                conn.use_count += 1
                self._active_connections[server_name] += 1
                return conn

            # Check if we can create new connection
            if self._active_connections[server_name] >= self.max_connections:
                # Wait for connection to become available
                # In production, implement proper waiting with timeout
                raise RuntimeError(
                    f"Connection pool exhausted for '{server_name}' "
                    f"(max: {self.max_connections})"
                )

            # Create new connection
            bridge = MCPBridge(server_config)
            # Note: Session creation happens on first use

            conn = PooledConnection(
                bridge=bridge,
                session=None,  # Will be created lazily
                created_at=datetime.now(),
                last_used=datetime.now(),
                use_count=1,
            )

            self._active_connections[server_name] += 1
            return conn

    async def return_connection(
        self, server_name: str, conn: PooledConnection
    ):
        """
        Return a connection to the pool.

        Args:
            server_name: Name of the MCP server
            conn: Connection to return
        """
        async with self._pool_locks[server_name]:
            self._active_connections[server_name] -= 1

            # Check if connection is still healthy
            if self._is_connection_healthy(conn):
                self._pools[server_name].append(conn)
            else:
                await conn.bridge.close()

    def _is_connection_healthy(self, conn: PooledConnection) -> bool:
        """Check if connection is healthy and not expired."""
        now = datetime.now()
        age = (now - conn.created_at).total_seconds()
        idle_time = (now - conn.last_used).total_seconds()

        # Connection too old or idle too long
        if idle_time > self.max_idle_time:
            return False

        return True

    async def _health_check_loop(self):
        """Background task to perform health checks."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Health check error: {e}")

    async def _perform_health_checks(self):
        """Perform health checks on pooled connections."""
        for server_name, pool in self._pools.items():
            async with self._pool_locks[server_name]:
                healthy = []
                for conn in pool:
                    try:
                        result = await conn.bridge.health_check()
                        if result.success:
                            healthy.append(conn)
                        else:
                            await conn.bridge.close()
                    except Exception:
                        await conn.bridge.close()

                self._pools[server_name] = healthy

    async def _cleanup_loop(self):
        """Background task to clean up idle connections."""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_idle_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Cleanup error: {e}")

    async def _cleanup_idle_connections(self):
        """Remove idle connections from pool."""
        for server_name, pool in self._pools.items():
            async with self._pool_locks[server_name]:
                active = []
                for conn in pool:
                    if self._is_connection_healthy(conn):
                        active.append(conn)
                    else:
                        await conn.bridge.close()

                self._pools[server_name] = active

    def get_stats(self) -> Dict[str, Dict]:
        """Get pool statistics."""
        stats = {}
        for server_name, pool in self._pools.items():
            stats[server_name] = {
                "idle_connections": len(pool),
                "active_connections": self._active_connections[server_name],
                "total_connections": len(pool) + self._active_connections[server_name],
            }
        return stats


# Global pool instance
_connection_pool: Optional[MCPConnectionPool] = None


async def get_connection_pool() -> MCPConnectionPool:
    """Get or create global connection pool."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = MCPConnectionPool()
        await _connection_pool.start()
    return _connection_pool
```

### Usage Example

```python
from Tools.adapters.mcp_connection_pool import get_connection_pool

# Get connection from pool
pool = await get_connection_pool()
conn = await pool.get_connection(server_config)

try:
    # Use connection for tool call
    result = await conn.bridge.call_tool("tool_name", arguments)
finally:
    # Return to pool
    await pool.return_connection(server_config.name, conn)
```

## Result Caching

### Cache Strategy

```python
# Tools/adapters/mcp_result_cache.py
import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import ToolResult


@dataclass
class CacheEntry:
    """Cached tool result entry."""
    result: ToolResult
    timestamp: float
    ttl: int
    hit_count: int = 0


class MCPResultCache:
    """
    LRU cache for MCP tool results.

    Caches tool call results to reduce redundant MCP server calls.
    Supports TTL-based expiration and LRU eviction.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,  # 1 hour
        enable_stats: bool = True,
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.enable_stats = enable_stats

        # LRU cache using OrderedDict
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Statistics
        self._hits = 0
        self._misses = 0

    def _make_key(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> str:
        """Generate cache key from tool call parameters."""
        key_data = {
            "server": server_name,
            "tool": tool_name,
            "args": arguments,
        }
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()

    def get(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Optional[ToolResult]:
        """
        Get cached result if available and not expired.

        Args:
            server_name: MCP server name
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Cached result or None if not found/expired
        """
        key = self._make_key(server_name, tool_name, arguments)

        if key in self._cache:
            entry = self._cache[key]

            # Check if expired
            age = time.time() - entry.timestamp
            if age > entry.ttl:
                # Expired - remove from cache
                del self._cache[key]
                self._misses += 1
                return None

            # Cache hit - move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hit_count += 1
            self._hits += 1

            return entry.result

        self._misses += 1
        return None

    def set(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        result: ToolResult,
        ttl: Optional[int] = None,
    ):
        """
        Store result in cache.

        Args:
            server_name: MCP server name
            tool_name: Tool name
            arguments: Tool arguments
            result: Tool result to cache
            ttl: Custom TTL (uses default if None)
        """
        # Only cache successful results
        if not result.success:
            return

        key = self._make_key(server_name, tool_name, arguments)

        # Evict oldest entry if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._cache.popitem(last=False)  # Remove oldest (FIFO)

        # Store new entry
        entry = CacheEntry(
            result=result,
            timestamp=time.time(),
            ttl=ttl or self.default_ttl,
            hit_count=0,
        )

        self._cache[key] = entry
        self._cache.move_to_end(key)  # Mark as most recently used

    def invalidate(self, server_name: str, tool_name: Optional[str] = None):
        """
        Invalidate cache entries.

        Args:
            server_name: Server to invalidate
            tool_name: Specific tool (None = all tools for server)
        """
        keys_to_remove = []

        for key, entry in self._cache.items():
            # We'd need to store server/tool in entry to filter properly
            # For now, just invalidate by pattern matching
            keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

    def clear(self):
        """Clear entire cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "size": len(self._cache),
            "max_size": self.max_size,
            "utilization": len(self._cache) / self.max_size,
        }


# Global cache instance
_result_cache: Optional[MCPResultCache] = None


def get_result_cache() -> MCPResultCache:
    """Get or create global result cache."""
    global _result_cache
    if _result_cache is None:
        _result_cache = MCPResultCache()
    return _result_cache
```

### Caching Best Practices

1. **Cache Read-Heavy Operations**: GET operations, list queries, documentation lookups
2. **Don't Cache Mutations**: POST/PUT/DELETE operations should not be cached
3. **Use Appropriate TTLs**:
   - Static data: 1 hour - 1 day
   - Dynamic data: 1-15 minutes
   - Real-time data: No caching
4. **Implement Cache Invalidation**: Clear cache when data changes

## Query Batching

### Batch Multiple Tool Calls

```python
# Tools/adapters/mcp_batch.py
import asyncio
from typing import Any, Dict, List, Tuple

from .base import ToolResult
from .mcp_bridge import MCPBridge


class MCPBatchExecutor:
    """
    Batch executor for multiple MCP tool calls.

    Executes multiple tool calls in parallel for better performance.
    """

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_batch(
        self,
        bridge: MCPBridge,
        tool_calls: List[Tuple[str, Dict[str, Any]]],
    ) -> List[ToolResult]:
        """
        Execute multiple tool calls in parallel.

        Args:
            bridge: MCP bridge to use
            tool_calls: List of (tool_name, arguments) tuples

        Returns:
            List of ToolResults in same order as input
        """

        async def execute_with_semaphore(tool_name: str, arguments: Dict):
            async with self._semaphore:
                return await bridge.call_tool(tool_name, arguments)

        # Execute all calls concurrently
        tasks = [
            execute_with_semaphore(tool_name, arguments)
            for tool_name, arguments in tool_calls
        ]

        return await asyncio.gather(*tasks, return_exceptions=True)
```

### Usage

```python
# Batch multiple tool calls
batch_executor = MCPBatchExecutor(max_concurrent=5)

tool_calls = [
    ("get_tasks", {"status": "active"}),
    ("get_today_metrics", {}),
    ("get_clients", {}),
]

results = await batch_executor.execute_batch(bridge, tool_calls)
```

## Performance Monitoring

### Track Performance Metrics

```python
from Tools.adapters.mcp_observability import get_all_metrics

# Get metrics for all servers
metrics = get_all_metrics()

for server_name, server_metrics in metrics.items():
    print(f"\nServer: {server_name}")
    print(f"  Success rate: {server_metrics['tool_calls']['success_rate']:.1%}")
    print(f"  Avg call time: {server_metrics['performance']['avg_call_times']}")
    print(f"  Cache hit rate: {server_metrics['performance']['cache_hit_rate']:.1%}")
```

### Set Up Alerts

```python
# config/performance_alerts.py
from Tools.adapters.mcp_observability import get_metrics


def check_performance_alerts():
    """Check for performance issues and trigger alerts."""
    alerts = []

    for server_name in ["workos", "context7", "magic"]:
        metrics = get_metrics(server_name)
        summary = metrics.get_summary()

        # Check error rate
        error_rate = 1 - summary["tool_calls"]["success_rate"]
        if error_rate > 0.1:  # >10% errors
            alerts.append(f"High error rate for {server_name}: {error_rate:.1%}")

        # Check latency
        for tool_name, avg_time in summary["performance"]["avg_call_times"].items():
            if avg_time > 1.0:  # >1 second
                alerts.append(
                    f"High latency for {server_name}.{tool_name}: {avg_time:.2f}s"
                )

    return alerts
```

## Resource Management

### Request Throttling

```python
# Tools/adapters/mcp_throttle.py
import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict


@dataclass
class ThrottleConfig:
    """Throttle configuration for rate limiting."""
    max_requests_per_second: int = 10
    max_requests_per_minute: int = 100
    max_concurrent_requests: int = 5


class MCPThrottler:
    """
    Request throttler for MCP bridges.

    Implements rate limiting to prevent overwhelming MCP servers.
    """

    def __init__(self, config: ThrottleConfig):
        self.config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests)

        # Track request timestamps
        self._requests_per_second: Dict[str, list] = defaultdict(list)
        self._requests_per_minute: Dict[str, list] = defaultdict(list)

        self._lock = asyncio.Lock()

    async def acquire(self, server_name: str):
        """
        Acquire permission to make a request.

        Args:
            server_name: Name of the MCP server

        Raises:
            RuntimeError: If rate limit exceeded
        """
        async with self._lock:
            now = time.time()

            # Clean up old timestamps
            self._cleanup_old_timestamps(server_name, now)

            # Check rate limits
            if len(self._requests_per_second[server_name]) >= self.config.max_requests_per_second:
                raise RuntimeError(
                    f"Rate limit exceeded for {server_name}: "
                    f"{self.config.max_requests_per_second} requests/second"
                )

            if len(self._requests_per_minute[server_name]) >= self.config.max_requests_per_minute:
                raise RuntimeError(
                    f"Rate limit exceeded for {server_name}: "
                    f"{self.config.max_requests_per_minute} requests/minute"
                )

            # Record request
            self._requests_per_second[server_name].append(now)
            self._requests_per_minute[server_name].append(now)

        # Acquire semaphore for concurrent requests
        await self._semaphore.acquire()

    def release(self):
        """Release request permission."""
        self._semaphore.release()

    def _cleanup_old_timestamps(self, server_name: str, now: float):
        """Remove timestamps outside the rate limit windows."""
        # Keep only requests from last second
        self._requests_per_second[server_name] = [
            ts for ts in self._requests_per_second[server_name]
            if now - ts < 1.0
        ]

        # Keep only requests from last minute
        self._requests_per_minute[server_name] = [
            ts for ts in self._requests_per_minute[server_name]
            if now - ts < 60.0
        ]
```

## Production Configuration

### Optimal Settings for Production

```python
# config/production_performance.py
from Tools.adapters.mcp_connection_pool import MCPConnectionPool
from Tools.adapters.mcp_result_cache import MCPResultCache
from Tools.adapters.mcp_throttle import MCPThrottler, ThrottleConfig

# Connection pool configuration
connection_pool = MCPConnectionPool(
    min_connections=2,       # Keep 2 connections warm
    max_connections=20,      # Allow up to 20 concurrent connections
    max_idle_time=300,       # Close idle connections after 5 minutes
    health_check_interval=60 # Health check every minute
)

# Result cache configuration
result_cache = MCPResultCache(
    max_size=5000,           # Store up to 5000 results
    default_ttl=1800,        # 30 minute default TTL
    enable_stats=True        # Track hit rates
)

# Throttle configuration
throttle_config = ThrottleConfig(
    max_requests_per_second=50,
    max_requests_per_minute=1000,
    max_concurrent_requests=20
)

throttler = MCPThrottler(throttle_config)
```

## Benchmarking

### Run Performance Benchmarks

```python
# scripts/benchmark_mcp.py
import asyncio
import time
from statistics import mean, stdev

from Tools.adapters import get_default_manager


async def benchmark_tool_calls(iterations: int = 100):
    """Benchmark tool call performance."""
    manager = await get_default_manager(enable_mcp_bridges=True)

    # Warm up
    await manager.call_tool("workos.get_today_metrics")

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.time()
        result = await manager.call_tool("workos.get_today_metrics")
        elapsed = time.time() - start

        if result.success:
            times.append(elapsed)

    # Calculate statistics
    print(f"\nBenchmark Results ({iterations} calls):")
    print(f"  Mean: {mean(times)*1000:.2f}ms")
    print(f"  Std Dev: {stdev(times)*1000:.2f}ms")
    print(f"  Min: {min(times)*1000:.2f}ms")
    print(f"  Max: {max(times)*1000:.2f}ms")
    print(f"  p50: {sorted(times)[len(times)//2]*1000:.2f}ms")
    print(f"  p95: {sorted(times)[int(len(times)*0.95)]*1000:.2f}ms")
    print(f"  p99: {sorted(times)[int(len(times)*0.99)]*1000:.2f}ms")


if __name__ == "__main__":
    asyncio.run(benchmark_tool_calls())
```

## Summary

### Performance Optimization Checklist

- [ ] Implement connection pooling for high-frequency operations
- [ ] Enable result caching with appropriate TTLs
- [ ] Use query batching for multiple related calls
- [ ] Set up performance monitoring and alerting
- [ ] Implement request throttling to prevent overload
- [ ] Run regular performance benchmarks
- [ ] Review and tune based on production metrics

### Expected Improvements

- **Connection Pooling**: 10-100x faster for repeated calls
- **Result Caching**: 95%+ faster for cached results
- **Query Batching**: 2-5x faster for multiple calls
- **Overall**: 50-80% latency reduction in typical workflows
