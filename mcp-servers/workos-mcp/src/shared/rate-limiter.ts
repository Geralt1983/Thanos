// =============================================================================
// RATE LIMITER FOR MCP TOOL CALLS
// =============================================================================
// This module implements a sliding window rate limiter to prevent abuse and
// resource exhaustion in the workos-mcp server.
//
// Design Philosophy:
// - Simplified approach compared to oura-mcp (no persistence, no queuing)
// - Fail-fast: Immediately reject requests that exceed limits
// - In-memory storage: Fast and sufficient for single-instance deployment
// - Three-tier limiting: Global, write operations, read operations
// - Sliding window algorithm: Prevents burst traffic exploitation
//
// Reference: .auto-claude/specs/.../rate-limiter-architecture.md
// =============================================================================

import { RATE_LIMITS, RATE_LIMIT_CONFIG, ERROR_MESSAGES } from './validation-constants.js';

// =============================================================================
// TYPES
// =============================================================================

/**
 * Rate limit configuration options
 */
export interface RateLimitConfig {
  /** Whether rate limiting is enabled (default: true, can disable for testing) */
  enabled: boolean;
  /** Global requests per minute limit (default: 100) */
  globalPerMinute: number;
  /** Write operations per minute limit (default: 20) */
  writeOpsPerMinute: number;
  /** Read operations per minute limit (default: 60) */
  readOpsPerMinute: number;
  /** Time window in milliseconds (default: 60000 = 1 minute) */
  windowMs: number;
  /** Cleanup interval in milliseconds (default: 300000 = 5 minutes) */
  cleanupIntervalMs: number;
}

/**
 * Rate limit check result
 */
export interface RateLimitResult {
  /** Whether the request is allowed */
  allowed: boolean;
  /** Which limit was exceeded (if not allowed) */
  limitType?: 'global' | 'write' | 'read';
  /** The limit that was exceeded */
  limit?: number;
  /** Current number of requests in window */
  current?: number;
  /** Milliseconds until rate limit resets */
  retryAfterMs?: number;
  /** Seconds until rate limit resets (rounded up) */
  retryAfterSeconds?: number;
  /** User-friendly error message */
  message?: string;
}

/**
 * Rate limit statistics for monitoring
 */
export interface RateLimitStats {
  global: {
    requestsInWindow: number;
    limit: number;
    remaining: number;
    percentageUsed: number;
  };
  write: {
    requestsInWindow: number;
    limit: number;
    remaining: number;
    percentageUsed: number;
  };
  read: {
    requestsInWindow: number;
    limit: number;
    remaining: number;
    percentageUsed: number;
  };
}

// =============================================================================
// RATE LIMITER CLASS
// =============================================================================

/**
 * Rate limiter for MCP tool calls
 * Implements sliding window rate limiting with three-tier limits
 */
export class RateLimiter {
  private config: RateLimitConfig;

  // In-memory request tracking (arrays of timestamps in milliseconds)
  private globalRequests: number[] = [];
  private writeRequests: number[] = [];
  private readRequests: number[] = [];

  // Cleanup timer to prevent unbounded memory growth
  private cleanupTimer?: NodeJS.Timeout;

  /**
   * Creates a new rate limiter instance
   *
   * Default configuration from RATE_LIMIT_CONFIG in validation-constants.ts:
   * - enabled: true (override with RATE_LIMIT_ENABLED=false)
   * - globalPerMinute: 100 (override with RATE_LIMIT_GLOBAL_PER_MINUTE)
   * - writeOpsPerMinute: 20 (override with RATE_LIMIT_WRITE_PER_MINUTE)
   * - readOpsPerMinute: 60 (override with RATE_LIMIT_READ_PER_MINUTE)
   * - windowMs: 60000 (1 minute)
   * - cleanupIntervalMs: 300000 (5 minutes)
   *
   * @param config - Optional configuration overrides (takes precedence over env vars)
   */
  constructor(config?: Partial<RateLimitConfig>) {
    this.config = {
      enabled: config?.enabled ?? RATE_LIMIT_CONFIG.enabled,
      globalPerMinute: config?.globalPerMinute ?? RATE_LIMIT_CONFIG.globalPerMinute,
      writeOpsPerMinute: config?.writeOpsPerMinute ?? RATE_LIMIT_CONFIG.writeOpsPerMinute,
      readOpsPerMinute: config?.readOpsPerMinute ?? RATE_LIMIT_CONFIG.readOpsPerMinute,
      windowMs: config?.windowMs ?? RATE_LIMITS.WINDOW_ONE_MINUTE,
      cleanupIntervalMs: config?.cleanupIntervalMs ?? RATE_LIMITS.CLEANUP_INTERVAL,
    };

    // Start periodic cleanup to prevent memory growth
    this.startCleanupTimer();
  }

  // ===========================================================================
  // PUBLIC API
  // ===========================================================================

  /**
   * Checks if a request is allowed under current rate limits
   * @param toolName - The MCP tool name being called
   * @returns Rate limit check result with allowed/blocked status and details
   */
  public checkRateLimit(toolName: string): RateLimitResult {
    // If rate limiting is disabled, allow all requests
    if (!this.config.enabled) {
      return { allowed: true };
    }

    // Clean up old requests before checking (ensures accurate count)
    this.cleanupOldRequests();

    // 1. Check global limit (applies to all requests)
    const globalCheck = this.checkLimit(
      this.globalRequests,
      this.config.globalPerMinute,
      this.config.windowMs
    );

    if (!globalCheck.allowed) {
      return {
        allowed: false,
        limitType: 'global',
        limit: this.config.globalPerMinute,
        current: globalCheck.count,
        retryAfterMs: globalCheck.retryAfterMs,
        retryAfterSeconds: Math.ceil(globalCheck.retryAfterMs / 1000),
        message: ERROR_MESSAGES.RATE_LIMIT_EXCEEDED(
          'global',
          globalCheck.count,
          this.config.globalPerMinute,
          '1 minute',
          Math.ceil(globalCheck.retryAfterMs / 1000)
        ),
      };
    }

    // 2. Check operation-specific limit (write or read)
    const isWrite = this.isWriteOperation(toolName);
    const operationRequests = isWrite ? this.writeRequests : this.readRequests;
    const operationLimit = isWrite
      ? this.config.writeOpsPerMinute
      : this.config.readOpsPerMinute;
    const operationType = isWrite ? 'write' : 'read';

    const operationCheck = this.checkLimit(
      operationRequests,
      operationLimit,
      this.config.windowMs
    );

    if (!operationCheck.allowed) {
      return {
        allowed: false,
        limitType: operationType,
        limit: operationLimit,
        current: operationCheck.count,
        retryAfterMs: operationCheck.retryAfterMs,
        retryAfterSeconds: Math.ceil(operationCheck.retryAfterMs / 1000),
        message: ERROR_MESSAGES.RATE_LIMIT_EXCEEDED(
          operationType,
          operationCheck.count,
          operationLimit,
          '1 minute',
          Math.ceil(operationCheck.retryAfterMs / 1000)
        ),
      };
    }

    // All checks passed - request is allowed
    return { allowed: true };
  }

  /**
   * Records a successful request for rate limiting tracking
   * Should be called after checkRateLimit() returns allowed: true
   * @param toolName - The MCP tool name being called
   */
  public recordRequest(toolName: string): void {
    if (!this.config.enabled) {
      return;
    }

    const timestamp = Date.now();

    // Record in global tracking
    this.globalRequests.push(timestamp);

    // Record in operation-specific tracking
    if (this.isWriteOperation(toolName)) {
      this.writeRequests.push(timestamp);
    } else {
      this.readRequests.push(timestamp);
    }
  }

  /**
   * Returns current rate limit statistics for monitoring
   * @returns Statistics for all rate limit tiers
   */
  public getStats(): RateLimitStats {
    this.cleanupOldRequests();

    const cutoffTime = Date.now() - this.config.windowMs;

    // Count requests in current window
    const globalCount = this.globalRequests.filter(ts => ts > cutoffTime).length;
    const writeCount = this.writeRequests.filter(ts => ts > cutoffTime).length;
    const readCount = this.readRequests.filter(ts => ts > cutoffTime).length;

    // Calculate remaining and percentage used
    const globalRemaining = Math.max(0, this.config.globalPerMinute - globalCount);
    const writeRemaining = Math.max(0, this.config.writeOpsPerMinute - writeCount);
    const readRemaining = Math.max(0, this.config.readOpsPerMinute - readCount);

    const globalPercentage = (globalCount / this.config.globalPerMinute) * 100;
    const writePercentage = (writeCount / this.config.writeOpsPerMinute) * 100;
    const readPercentage = (readCount / this.config.readOpsPerMinute) * 100;

    return {
      global: {
        requestsInWindow: globalCount,
        limit: this.config.globalPerMinute,
        remaining: globalRemaining,
        percentageUsed: globalPercentage,
      },
      write: {
        requestsInWindow: writeCount,
        limit: this.config.writeOpsPerMinute,
        remaining: writeRemaining,
        percentageUsed: writePercentage,
      },
      read: {
        requestsInWindow: readCount,
        limit: this.config.readOpsPerMinute,
        remaining: readRemaining,
        percentageUsed: readPercentage,
      },
    };
  }

  /**
   * Resets all rate limit counters and clears history
   * Useful for testing purposes
   */
  public reset(): void {
    this.globalRequests = [];
    this.writeRequests = [];
    this.readRequests = [];
  }

  /**
   * Stops the cleanup timer
   * Should be called when shutting down the rate limiter
   */
  public shutdown(): void {
    this.stopCleanupTimer();
  }

  // ===========================================================================
  // PRIVATE HELPERS
  // ===========================================================================

  /**
   * Determines if a tool operation is a write operation
   * Write operations modify data and have stricter rate limits
   * @param toolName - The MCP tool name
   * @returns true if write operation, false if read operation
   */
  private isWriteOperation(toolName: string): boolean {
    const writeKeywords = [
      'create',
      'update',
      'delete',
      'complete',
      'promote',
      'log',
      'dump',
      'process',
      'recalculate',
    ];

    return writeKeywords.some(keyword => toolName.toLowerCase().includes(keyword));
  }

  /**
   * Checks if requests are within limit using sliding window algorithm
   * @param requests - Array of request timestamps
   * @param limit - Maximum allowed requests in window
   * @param windowMs - Time window in milliseconds
   * @returns Check result with allowed status, count, and retry time
   */
  private checkLimit(
    requests: number[],
    limit: number,
    windowMs: number
  ): { allowed: boolean; count: number; retryAfterMs: number } {
    const cutoffTime = Date.now() - windowMs;

    // Count requests within the time window
    const requestsInWindow = requests.filter(ts => ts > cutoffTime);
    const count = requestsInWindow.length;

    // Check if under limit
    const allowed = count < limit;

    // Calculate retry-after time (time until oldest request expires)
    let retryAfterMs = 0;
    if (!allowed && requestsInWindow.length > 0) {
      const oldestRequest = Math.min(...requestsInWindow);
      retryAfterMs = Math.max(0, oldestRequest + windowMs - Date.now());
    }

    return { allowed, count, retryAfterMs };
  }

  /**
   * Removes requests older than the time window to prevent unbounded growth
   * Called periodically and before each rate limit check
   */
  private cleanupOldRequests(): void {
    const cutoffTime = Date.now() - this.config.windowMs;

    // Filter out requests older than the time window
    this.globalRequests = this.globalRequests.filter(ts => ts > cutoffTime);
    this.writeRequests = this.writeRequests.filter(ts => ts > cutoffTime);
    this.readRequests = this.readRequests.filter(ts => ts > cutoffTime);
  }

  /**
   * Calculates milliseconds until the oldest request expires from window
   * @param requests - Array of request timestamps
   * @param windowMs - Time window in milliseconds
   * @returns Milliseconds until rate limit resets
   */
  private getRetryAfterMs(requests: number[], windowMs: number): number {
    if (requests.length === 0) {
      return 0;
    }

    const oldestRequest = Math.min(...requests);
    const expiryTime = oldestRequest + windowMs;
    const now = Date.now();

    return Math.max(0, expiryTime - now);
  }

  /**
   * Starts periodic cleanup timer to prevent memory growth
   */
  private startCleanupTimer(): void {
    // Clear any existing timer
    this.stopCleanupTimer();

    // Start new timer
    this.cleanupTimer = setInterval(
      () => this.cleanupOldRequests(),
      this.config.cleanupIntervalMs
    );

    // Prevent timer from keeping process alive
    this.cleanupTimer.unref();
  }

  /**
   * Stops the cleanup timer
   */
  private stopCleanupTimer(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = undefined;
    }
  }
}

// =============================================================================
// SINGLETON FACTORY
// =============================================================================

/**
 * Singleton instance of the rate limiter
 */
let rateLimiterInstance: RateLimiter | null = null;

/**
 * Gets or creates the singleton rate limiter instance
 *
 * On first call, initializes with RATE_LIMIT_CONFIG from validation-constants.ts
 * which respects environment variable overrides (RATE_LIMIT_ENABLED,
 * RATE_LIMIT_GLOBAL_PER_MINUTE, RATE_LIMIT_WRITE_PER_MINUTE, RATE_LIMIT_READ_PER_MINUTE).
 *
 * @param config - Optional configuration overrides (only used on first call)
 * @returns The singleton rate limiter instance
 */
export function getRateLimiter(config?: Partial<RateLimitConfig>): RateLimiter {
  if (!rateLimiterInstance) {
    rateLimiterInstance = new RateLimiter(config);
  }
  return rateLimiterInstance;
}

/**
 * Resets the singleton rate limiter instance
 * Useful for testing purposes
 */
export function resetRateLimiter(): void {
  if (rateLimiterInstance) {
    rateLimiterInstance.shutdown();
    rateLimiterInstance = null;
  }
}
