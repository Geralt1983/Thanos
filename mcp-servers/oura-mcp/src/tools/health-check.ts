// =============================================================================
// HEALTH CHECK TOOL
// MCP tool to check Oura API connectivity and cache status
// Provides diagnostics for troubleshooting
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import { getAPIClient } from "../api/client.js";
import { initDb } from "../cache/db.js";
import { getCachedReadiness, getCachedSleep, getCachedActivity } from "../cache/operations.js";
import { RateLimitError, logError } from "../shared/errors.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

/**
 * Tool definition for health_check
 * Returns API status, cache status, and diagnostics
 */
export const healthCheckTool: ToolDefinition = {
  name: "oura_health_check",
  description:
    "Check the health status of the Oura MCP server. Returns API connectivity status, " +
    "cache status, last sync time, rate limit status, and diagnostic information. " +
    "Useful for troubleshooting connection issues or understanding system state.",
  inputSchema: {
    type: "object",
    properties: {
      include_cache_samples: {
        type: "boolean",
        description:
          "If true, includes sample data from cache for verification (default: false)",
      },
    },
    required: [],
  },
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get today's date in YYYY-MM-DD format
 */
function getTodayDate(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Test Oura API connectivity
 * Makes a lightweight request to verify authentication and connectivity
 */
async function testAPIConnectivity(): Promise<{
  status: "connected" | "error" | "rate_limited";
  message: string;
  responseTime?: number;
  statusCode?: number;
  rateLimitInfo?: {
    limit?: number;
    remaining?: number;
    reset?: string;
  };
}> {
  const startTime = Date.now();

  try {
    const apiClient = getAPIClient();

    // Try to fetch today's readiness as a lightweight connectivity test
    const today = getTodayDate();
    await apiClient.getReadinessForDate(today);

    const responseTime = Date.now() - startTime;

    return {
      status: "connected",
      message: "Successfully connected to Oura API",
      responseTime,
      statusCode: 200,
    };
  } catch (error: any) {
    const responseTime = Date.now() - startTime;

    // Check for rate limit error
    if (error instanceof RateLimitError || error.statusCode === 429) {
      return {
        status: "rate_limited",
        message: error.message || "Rate limit exceeded",
        responseTime,
        statusCode: 429,
        rateLimitInfo: {
          limit: error.limit,
          remaining: error.remaining,
          reset: error.retryAfter
            ? new Date(Date.now() + error.retryAfter * 1000).toISOString()
            : undefined,
        },
      };
    }

    // Check for authentication error
    if (error.statusCode === 401 || error.statusCode === 403) {
      return {
        status: "error",
        message: `Authentication failed: ${error.message}`,
        responseTime,
        statusCode: error.statusCode,
      };
    }

    // Other API errors
    return {
      status: "error",
      message: error.message || "Failed to connect to Oura API",
      responseTime,
      statusCode: error.statusCode,
    };
  }
}

/**
 * Check cache database status and gather statistics
 */
function checkCacheStatus(): {
  status: "healthy" | "error";
  message: string;
  statistics?: {
    readiness_entries: number;
    sleep_entries: number;
    activity_entries: number;
    total_entries: number;
    database_size_kb?: number;
  };
  lastSync?: {
    date: string;
    hasDataToday: boolean;
  };
  error?: string;
} {
  try {
    const db = initDb();

    // Get entry counts for each data type
    const readinessCount = db
      .prepare("SELECT COUNT(*) as count FROM daily_readiness")
      .get() as { count: number };

    const sleepCount = db
      .prepare("SELECT COUNT(*) as count FROM daily_sleep")
      .get() as { count: number };

    const activityCount = db
      .prepare("SELECT COUNT(*) as count FROM daily_activity")
      .get() as { count: number };

    const totalEntries =
      readinessCount.count + sleepCount.count + activityCount.count;

    // Check if we have data for today
    const today = getTodayDate();
    const todayReadiness = getCachedReadiness(today);
    const todaySleep = getCachedSleep(today);
    const todayActivity = getCachedActivity(today);

    const hasDataToday =
      todayReadiness !== null || todaySleep !== null || todayActivity !== null;

    // Get most recent entry date to determine last sync
    const mostRecentReadiness = db
      .prepare(
        "SELECT day FROM daily_readiness ORDER BY day DESC LIMIT 1"
      )
      .get() as { day: string } | undefined;

    const mostRecentSleep = db
      .prepare("SELECT day FROM daily_sleep ORDER BY day DESC LIMIT 1")
      .get() as { day: string } | undefined;

    const mostRecentActivity = db
      .prepare("SELECT day FROM daily_activity ORDER BY day DESC LIMIT 1")
      .get() as { day: string } | undefined;

    const dates = [
      mostRecentReadiness?.day,
      mostRecentSleep?.day,
      mostRecentActivity?.day,
    ].filter(Boolean);

    const lastSyncDate = dates.length > 0
      ? dates.sort().reverse()[0] // Most recent date
      : undefined;

    return {
      status: "healthy",
      message: `Cache is healthy with ${totalEntries} total entries`,
      statistics: {
        readiness_entries: readinessCount.count,
        sleep_entries: sleepCount.count,
        activity_entries: activityCount.count,
        total_entries: totalEntries,
      },
      lastSync: lastSyncDate
        ? {
            date: lastSyncDate,
            hasDataToday,
          }
        : undefined,
    };
  } catch (error: any) {
    logError(error, { operation: "cache_health_check" });

    return {
      status: "error",
      message: "Failed to check cache status",
      error: error.message,
    };
  }
}

/**
 * Get sample data from cache if requested
 */
function getCacheSamples(today: string): {
  readiness: any | null;
  sleep: any | null;
  activity: any | null;
} | null {
  try {
    return {
      readiness: getCachedReadiness(today),
      sleep: getCachedSleep(today),
      activity: getCachedActivity(today),
    };
  } catch (error) {
    return null;
  }
}

// =============================================================================
// HANDLER IMPLEMENTATION
// =============================================================================

/**
 * Handler for health_check tool
 * Performs comprehensive diagnostics of the MCP server
 */
export async function handleHealthCheck(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    const includeSamples = args.include_cache_samples === true;
    const today = getTodayDate();

    // Run diagnostics in parallel for faster response
    const [apiStatus, cacheStatus] = await Promise.all([
      testAPIConnectivity(),
      Promise.resolve(checkCacheStatus()),
    ]);

    // Get cache samples if requested
    const cacheSamples = includeSamples ? getCacheSamples(today) : null;

    // Determine overall health status
    const isHealthy =
      (apiStatus.status === "connected" || apiStatus.status === "rate_limited") &&
      cacheStatus.status === "healthy";

    // Build response
    const response: any = {
      overall_status: isHealthy ? "healthy" : "degraded",
      timestamp: new Date().toISOString(),
      components: {
        api: {
          status: apiStatus.status,
          message: apiStatus.message,
          response_time_ms: apiStatus.responseTime,
          status_code: apiStatus.statusCode,
          rate_limit: apiStatus.rateLimitInfo,
        },
        cache: {
          status: cacheStatus.status,
          message: cacheStatus.message,
          statistics: cacheStatus.statistics,
          last_sync: cacheStatus.lastSync,
          error: cacheStatus.error,
        },
      },
      diagnostics: {
        can_fetch_fresh_data: apiStatus.status === "connected",
        can_use_cached_data: cacheStatus.status === "healthy",
        has_today_data: cacheStatus.lastSync?.hasDataToday || false,
        recommendations: [] as string[],
      },
    };

    // Add recommendations based on status
    if (apiStatus.status === "error") {
      if (apiStatus.statusCode === 401 || apiStatus.statusCode === 403) {
        response.diagnostics.recommendations.push(
          "⚠️ API authentication failed. Check your OURA_API_KEY environment variable."
        );
      } else {
        response.diagnostics.recommendations.push(
          "⚠️ API connection failed. Check network connectivity and Oura API status."
        );
      }
    }

    if (apiStatus.status === "rate_limited") {
      response.diagnostics.recommendations.push(
        "⚠️ Rate limit exceeded. Relying on cached data. Try again later."
      );
    }

    if (cacheStatus.status === "error") {
      response.diagnostics.recommendations.push(
        "⚠️ Cache database error. Fresh API data will be used but not cached."
      );
    }

    if (
      cacheStatus.statistics &&
      cacheStatus.statistics.total_entries === 0
    ) {
      response.diagnostics.recommendations.push(
        "💡 Cache is empty. First API requests will populate the cache."
      );
    }

    if (
      cacheStatus.lastSync &&
      !cacheStatus.lastSync.hasDataToday &&
      apiStatus.status === "connected"
    ) {
      response.diagnostics.recommendations.push(
        "💡 No data cached for today yet. Consider fetching today's metrics."
      );
    }

    if (isHealthy && cacheStatus.lastSync?.hasDataToday) {
      response.diagnostics.recommendations.push(
        "✅ System is healthy and ready. Today's data is available."
      );
    }

    // Add cache samples if requested
    if (includeSamples && cacheSamples) {
      response.cache_samples = {
        date: today,
        readiness: cacheSamples.readiness
          ? {
              score: cacheSamples.readiness.score,
              day: cacheSamples.readiness.day,
            }
          : null,
        sleep: cacheSamples.sleep
          ? {
              score: cacheSamples.sleep.score,
              day: cacheSamples.sleep.day,
            }
          : null,
        activity: cacheSamples.activity
          ? {
              score: cacheSamples.activity.score,
              day: cacheSamples.activity.day,
            }
          : null,
      };
    }

    return successResponse(response);
  } catch (error: any) {
    return errorResponse("Unexpected error during health check", {
      error: error.message,
      stack: error.stack,
    });
  }
}
