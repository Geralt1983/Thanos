"""
MCP Result Caching.

Provides intelligent caching for MCP tool results with TTL-based expiration,
cache key generation, and multiple invalidation strategies.

This module enables caching of expensive MCP tool calls to improve performance
and reduce load on MCP servers. Supports both in-memory and persistent cache backends.
"""

import hashlib
import json
import logging
import pickle
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Optional

from .mcp_errors import MCPError

logger = logging.getLogger(__name__)


class CacheBackend(str, Enum):
    """
    Available cache backend types.

    - MEMORY: In-memory cache using dictionary (fast, not persistent)
    - DISK: Disk-based cache using pickle (persistent, slower)
    """

    MEMORY = "memory"
    DISK = "disk"


class InvalidationStrategy(str, Enum):
    """
    Cache invalidation strategies.

    - TTL: Time-to-live based expiration
    - LRU: Least Recently Used eviction
    - LFU: Least Frequently Used eviction
    - MANUAL: Only invalidate on explicit clear/delete
    """

    TTL = "ttl"
    LRU = "lru"
    LFU = "lfu"
    MANUAL = "manual"


class CacheError(MCPError):
    """
    Error raised during cache operations.

    Includes context about the cache operation that failed.
    """

    def __init__(
        self,
        message: str,
        operation: str,
        cache_key: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize cache error.

        Args:
            message: Error description
            operation: Cache operation being performed (get/set/delete)
            cache_key: Cache key being accessed
            context: Additional error context
        """
        context = context or {}
        context["operation"] = operation
        if cache_key:
            context["cache_key"] = cache_key

        super().__init__(
            message=message,
            context=context,
            retryable=False,
        )
        self.operation = operation
        self.cache_key = cache_key


@dataclass
class CacheConfig:
    """
    Configuration for cache behavior.

    Controls TTL, size limits, invalidation strategy, and backend selection.
    """

    backend: CacheBackend = CacheBackend.MEMORY
    """Cache backend type"""

    strategy: InvalidationStrategy = InvalidationStrategy.TTL
    """Cache invalidation strategy"""

    default_ttl_seconds: int = 300
    """Default TTL for cached entries (5 minutes)"""

    max_size: int = 1000
    """Maximum number of entries in cache"""

    enable_stats: bool = True
    """Enable cache statistics collection"""

    disk_cache_dir: Optional[Path] = None
    """Directory for disk-based cache (required for DISK backend)"""

    key_prefix: str = "mcp"
    """Prefix for all cache keys"""


@dataclass
class CacheEntry:
    """
    A single cache entry with metadata.

    Tracks the cached value, expiration time, access patterns, and statistics.
    """

    key: str
    """Cache key"""

    value: Any
    """Cached value"""

    created_at: datetime = field(default_factory=datetime.now)
    """When entry was created"""

    expires_at: Optional[datetime] = None
    """When entry expires (None = never)"""

    access_count: int = 0
    """Number of times entry has been accessed"""

    last_accessed: Optional[datetime] = None
    """When entry was last accessed"""

    size_bytes: int = 0
    """Estimated size of entry in bytes"""

    tool_name: Optional[str] = None
    """Tool name for invalidation and diagnostics"""

    server_name: Optional[str] = None
    """Server name for invalidation and diagnostics"""

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Ensure new fields exist when unpickling older entries."""
        self.__dict__.update(state)
        if "tool_name" not in state:
            self.tool_name = None
        if "server_name" not in state:
            self.server_name = None

    def is_expired(self) -> bool:
        """
        Check if cache entry has expired.

        Returns:
            True if entry is expired, False otherwise
        """
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at

    def touch(self) -> None:
        """Update access metadata when entry is accessed."""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class CacheStats:
    """
    Cache statistics for monitoring performance.

    Tracks hits, misses, evictions, and other metrics.
    """

    hits: int = 0
    """Number of cache hits"""

    misses: int = 0
    """Number of cache misses"""

    sets: int = 0
    """Number of cache sets"""

    deletes: int = 0
    """Number of cache deletes"""

    evictions: int = 0
    """Number of cache evictions"""

    expirations: int = 0
    """Number of expired entries removed"""

    errors: int = 0
    """Number of cache errors"""

    @property
    def hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Hit rate as a percentage (0.0 to 1.0)
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    @property
    def total_requests(self) -> int:
        """Get total number of cache requests."""
        return self.hits + self.misses

    def to_dict(self) -> dict[str, Any]:
        """
        Convert stats to dictionary.

        Returns:
            Dictionary with all statistics
        """
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "errors": self.errors,
            "hit_rate": self.hit_rate,
            "total_requests": self.total_requests,
        }


class CacheBackendInterface(ABC):
    """
    Abstract base class for cache backends.

    Defines the interface that all cache backends must implement.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """
        Get cache entry by key.

        Args:
            key: Cache key

        Returns:
            Cache entry if found and not expired, None otherwise
        """
        pass

    @abstractmethod
    def set(self, key: str, entry: CacheEntry) -> None:
        """
        Store cache entry.

        Args:
            key: Cache key
            entry: Cache entry to store
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete cache entry.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted, False if not found
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    def size(self) -> int:
        """
        Get current cache size.

        Returns:
            Number of entries in cache
        """
        pass

    @abstractmethod
    def keys(self) -> list[str]:
        """
        Get all cache keys.

        Returns:
            List of cache keys
        """
        pass


class MemoryCacheBackend(CacheBackendInterface):
    """
    In-memory cache backend using a dictionary.

    Fast but not persistent across restarts.
    """

    def __init__(self):
        """Initialize memory cache backend."""
        self._cache: dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.is_expired():
                del self._cache[key]
                return None
            return entry

    def peek(self, key: str) -> Optional[CacheEntry]:
        """
        Get cache entry without removing it if expired.

        Used internally for expiration checks.

        Args:
            key: Cache key

        Returns:
            Cache entry if found (even if expired), None otherwise
        """
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, entry: CacheEntry) -> None:
        """Store cache entry."""
        with self._lock:
            self._cache[key] = entry

    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def keys(self) -> list[str]:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())


class DiskCacheBackend(CacheBackendInterface):
    """
    Disk-based cache backend using pickle.

    Persistent across restarts but slower than memory cache.
    """

    def __init__(self, cache_dir: Path):
        """
        Initialize disk cache backend.

        Args:
            cache_dir: Directory for storing cache files
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _get_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Use hash to create safe filename
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        path = self._get_path(key)
        with self._lock:
            try:
                if not path.exists():
                    return None

                with open(path, "rb") as f:
                    entry = pickle.load(f)

                if entry.is_expired():
                    path.unlink()
                    return None

                return entry
            except Exception as e:
                logger.error(f"Error reading cache file {path}: {e}")
                return None

    def peek(self, key: str) -> Optional[CacheEntry]:
        """
        Get cache entry without removing it if expired.

        Used internally for expiration checks.

        Args:
            key: Cache key

        Returns:
            Cache entry if found (even if expired), None otherwise
        """
        path = self._get_path(key)
        with self._lock:
            try:
                if not path.exists():
                    return None

                with open(path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Error reading cache file {path}: {e}")
                return None

    def set(self, key: str, entry: CacheEntry) -> None:
        """Store cache entry."""
        path = self._get_path(key)
        with self._lock:
            try:
                with open(path, "wb") as f:
                    pickle.dump(entry, f)
            except Exception as e:
                logger.error(f"Error writing cache file {path}: {e}")

    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        path = self._get_path(key)
        with self._lock:
            try:
                if path.exists():
                    path.unlink()
                    return True
                return False
            except Exception as e:
                logger.error(f"Error deleting cache file {path}: {e}")
                return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            try:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
            except Exception as e:
                logger.error(f"Error clearing cache directory: {e}")

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(list(self.cache_dir.glob("*.cache")))

    def keys(self) -> list[str]:
        """Get all cache keys."""
        # Note: We can't easily reconstruct original keys from hashed filenames
        # This is a limitation of the disk backend
        with self._lock:
            return [f.stem for f in self.cache_dir.glob("*.cache")]


class MCPCache:
    """
    Intelligent cache for MCP tool results.

    Provides caching with TTL, multiple invalidation strategies,
    and support for both in-memory and persistent backends.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize MCP cache.

        Args:
            config: Cache configuration (uses defaults if not provided)
        """
        self.config = config or CacheConfig()
        self._stats = CacheStats() if self.config.enable_stats else None
        self._lock = Lock()
        self._server_index: dict[str, set[str]] = {}
        self._tool_index: dict[str, set[str]] = {}

        # Initialize backend
        if self.config.backend == CacheBackend.MEMORY:
            self._backend: CacheBackendInterface = MemoryCacheBackend()
        elif self.config.backend == CacheBackend.DISK:
            if not self.config.disk_cache_dir:
                raise ValueError("disk_cache_dir required for DISK backend")
            self._backend = DiskCacheBackend(self.config.disk_cache_dir)
        else:
            raise ValueError(f"Unknown cache backend: {self.config.backend}")

        logger.info(
            f"Initialized MCP cache with backend={self.config.backend.value}, "
            f"strategy={self.config.strategy.value}, "
            f"ttl={self.config.default_ttl_seconds}s"
        )

    def generate_key(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        server_name: Optional[str] = None,
    ) -> str:
        """
        Generate cache key from tool name and arguments.

        Creates a deterministic cache key by hashing the tool name
        and arguments. Includes optional server name for multi-server scenarios.

        Args:
            tool_name: Name of the MCP tool
            arguments: Tool arguments dictionary
            server_name: Optional server name for namespacing

        Returns:
            Cache key string
        """
        # Sort arguments for deterministic key generation
        sorted_args = json.dumps(arguments, sort_keys=True)

        # Create key components
        components = [self.config.key_prefix, tool_name]
        if server_name:
            components.append(server_name)
        components.append(sorted_args)

        # Hash for compact key
        key_str = "|".join(components)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()

        return f"{self.config.key_prefix}:{tool_name}:{key_hash[:16]}"

    def get(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        server_name: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Get cached tool result.

        Args:
            tool_name: Name of the MCP tool
            arguments: Tool arguments
            server_name: Optional server name

        Returns:
            Cached result if found and valid, None otherwise
        """
        key = self.generate_key(tool_name, arguments, server_name)

        try:
            entry = self._backend.get(key)

            if entry is None:
                if self._stats:
                    self._stats.misses += 1
                logger.debug(f"Cache miss for {key}")
                self._index_remove(key)
                return None

            # Update access metadata
            entry.touch()
            self._backend.set(key, entry)

            if self._stats:
                self._stats.hits += 1

            logger.debug(
                f"Cache hit for {key} (age: {(datetime.now() - entry.created_at).total_seconds():.1f}s)"
            )
            return entry.value

        except Exception as e:
            if self._stats:
                self._stats.errors += 1
            logger.error(f"Cache get error for {key}: {e}")
            return None

    def set(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        server_name: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Cache tool result.

        Args:
            tool_name: Name of the MCP tool
            arguments: Tool arguments
            result: Result to cache
            server_name: Optional server name
            ttl_seconds: TTL in seconds (uses default if not provided)
        """
        key = self.generate_key(tool_name, arguments, server_name)
        ttl = ttl_seconds or self.config.default_ttl_seconds

        try:
            # Check if we need to evict entries
            if self._backend.size() >= self.config.max_size:
                self._evict_one()

            # Calculate expiration
            expires_at = None
            if self.config.strategy == InvalidationStrategy.TTL:
                expires_at = datetime.now() + timedelta(seconds=ttl)

            # Estimate size
            size_bytes = len(pickle.dumps(result))

            # Create entry
            entry = CacheEntry(
                key=key,
                value=result,
                expires_at=expires_at,
                size_bytes=size_bytes,
                tool_name=tool_name,
                server_name=server_name,
            )

            # Store entry
            self._backend.set(key, entry)
            self._index_add(entry)

            if self._stats:
                self._stats.sets += 1

            logger.debug(
                f"Cached result for {key} (ttl: {ttl}s, size: {size_bytes} bytes)"
            )

        except Exception as e:
            if self._stats:
                self._stats.errors += 1
            logger.error(f"Cache set error for {key}: {e}")

    def delete(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        server_name: Optional[str] = None,
    ) -> bool:
        """
        Delete cached result.

        Args:
            tool_name: Name of the MCP tool
            arguments: Tool arguments
            server_name: Optional server name

        Returns:
            True if entry was deleted, False if not found
        """
        key = self.generate_key(tool_name, arguments, server_name)

        try:
            deleted = self._backend.delete(key)
            if deleted and self._stats:
                self._stats.deletes += 1
            if deleted:
                self._index_remove(key)
            return deleted
        except Exception as e:
            if self._stats:
                self._stats.errors += 1
            logger.error(f"Cache delete error for {key}: {e}")
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            self._backend.clear()
            self._server_index.clear()
            self._tool_index.clear()
            logger.info("Cache cleared")
        except Exception as e:
            if self._stats:
                self._stats.errors += 1
            logger.error(f"Cache clear error: {e}")

    def _index_add(self, entry: CacheEntry) -> None:
        """Index cache key by tool and server name."""
        if entry.tool_name:
            self._tool_index.setdefault(entry.tool_name, set()).add(entry.key)
        if entry.server_name:
            self._server_index.setdefault(entry.server_name, set()).add(entry.key)

    def _index_remove(self, key: str) -> None:
        """Remove cache key from indexes."""
        for index in (self._tool_index, self._server_index):
            for name in list(index.keys()):
                if key in index[name]:
                    index[name].discard(key)
                    if not index[name]:
                        del index[name]

    def clear_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        removed = 0
        try:
            for key in self._backend.keys():
                # Use peek to check without triggering auto-cleanup
                if hasattr(self._backend, 'peek'):
                    entry = self._backend.peek(key)  # type: ignore
                else:
                    entry = self._backend.get(key)

                if entry and entry.is_expired():
                    if self._backend.delete(key):
                        removed += 1
                        self._index_remove(key)

            if self._stats:
                self._stats.expirations += removed

            if removed > 0:
                logger.info(f"Removed {removed} expired cache entries")

        except Exception as e:
            if self._stats:
                self._stats.errors += 1
            logger.error(f"Error clearing expired entries: {e}")

        return removed

    def _evict_one(self) -> None:
        """
        Evict one entry based on invalidation strategy.

        Called when cache reaches max_size.
        """
        if self.config.strategy == InvalidationStrategy.MANUAL:
            logger.warning("Cache full but manual invalidation strategy set")
            return

        try:
            keys = self._backend.keys()
            if not keys:
                return

            # Get all entries for comparison
            entries = []
            for key in keys:
                entry = self._backend.get(key)
                if entry:
                    entries.append((key, entry))

            if not entries:
                return

            # Choose victim based on strategy
            if self.config.strategy == InvalidationStrategy.LRU:
                # Evict least recently used
                victim = min(
                    entries,
                    key=lambda x: x[1].last_accessed or x[1].created_at,
                )
            elif self.config.strategy == InvalidationStrategy.LFU:
                # Evict least frequently used
                victim = min(entries, key=lambda x: x[1].access_count)
            else:  # TTL or default
                # Evict oldest entry
                victim = min(entries, key=lambda x: x[1].created_at)

            # Evict the victim
            if self._backend.delete(victim[0]):
                self._index_remove(victim[0])
            if self._stats:
                self._stats.evictions += 1

            logger.debug(f"Evicted cache entry {victim[0]} (strategy: {self.config.strategy.value})")

        except Exception as e:
            logger.error(f"Error during cache eviction: {e}")

    def get_stats(self) -> Optional[CacheStats]:
        """
        Get cache statistics.

        Returns:
            Cache statistics if enabled, None otherwise
        """
        return self._stats

    def invalidate_by_tool(self, tool_name: str) -> int:
        """
        Invalidate all cache entries for a specific tool.

        Useful when a tool's behavior changes or you want to force refresh.

        Args:
            tool_name: Name of the tool to invalidate

        Returns:
            Number of entries invalidated
        """
        invalidated = 0
        try:
            keys = self._tool_index.get(tool_name)
            if not keys:
                keys = self._scan_keys_for_tool(tool_name)
            for key in list(keys):
                if self._backend.delete(key):
                    invalidated += 1
                    self._index_remove(key)

            if invalidated > 0:
                logger.info(f"Invalidated {invalidated} cache entries for tool {tool_name}")

        except Exception as e:
            logger.error(f"Error invalidating cache for tool {tool_name}: {e}")

        return invalidated

    def invalidate_by_server(self, server_name: str) -> int:
        """
        Invalidate all cache entries for a specific server.

        Useful when a server is reconfigured or restarted.

        Args:
            server_name: Name of the server to invalidate

        Returns:
            Number of entries invalidated
        """
        invalidated = 0
        try:
            keys = self._server_index.get(server_name)
            if not keys:
                keys = self._scan_keys_for_server(server_name)
            for key in list(keys):
                if self._backend.delete(key):
                    invalidated += 1
                    self._index_remove(key)

        except Exception as e:
            logger.error(f"Error invalidating cache for server {server_name}: {e}")

        return invalidated

    def _get_entry_for_key(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry without triggering eviction."""
        if hasattr(self._backend, "peek"):
            return self._backend.peek(key)  # type: ignore[no-any-return]
        return self._backend.get(key)

    def _scan_keys_for_tool(self, tool_name: str) -> set[str]:
        """Scan cache entries to find keys for a tool."""
        keys: set[str] = set()
        for key in self._backend.keys():
            entry = self._get_entry_for_key(key)
            if entry and entry.tool_name == tool_name:
                keys.add(key)
        return keys

    def _scan_keys_for_server(self, server_name: str) -> set[str]:
        """Scan cache entries to find keys for a server."""
        keys: set[str] = set()
        for key in self._backend.keys():
            entry = self._get_entry_for_key(key)
            if entry and entry.server_name == server_name:
                keys.add(key)
        return keys


# Global cache instance
_global_cache: Optional[MCPCache] = None
_global_cache_lock = Lock()


def get_global_cache(config: Optional[CacheConfig] = None) -> MCPCache:
    """
    Get or create global cache instance.

    Args:
        config: Cache configuration (only used on first call)

    Returns:
        Global MCP cache instance
    """
    global _global_cache

    if _global_cache is None:
        with _global_cache_lock:
            if _global_cache is None:
                _global_cache = MCPCache(config)

    return _global_cache


def create_cache(config: Optional[CacheConfig] = None) -> MCPCache:
    """
    Create a new cache instance.

    Convenience function for creating standalone cache instances.

    Args:
        config: Cache configuration

    Returns:
        New MCP cache instance
    """
    return MCPCache(config)


def cache_tool_call(
    cache: MCPCache,
    tool_name: str,
    arguments: dict[str, Any],
    call_fn: Callable[[], Any],
    server_name: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
) -> Any:
    """
    Cache-aware tool call wrapper.

    Checks cache first, calls function if not cached, and stores result.

    Args:
        cache: Cache instance to use
        tool_name: Name of the tool
        arguments: Tool arguments
        call_fn: Function to call if not cached
        server_name: Optional server name
        ttl_seconds: Optional TTL override

    Returns:
        Tool result (from cache or fresh call)
    """
    # Try cache first
    result = cache.get(tool_name, arguments, server_name)
    if result is not None:
        return result

    # Call function
    result = call_fn()

    # Cache result
    cache.set(tool_name, arguments, result, server_name, ttl_seconds)

    return result
