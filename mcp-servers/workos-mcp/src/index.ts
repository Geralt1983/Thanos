#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Shared utilities
import { getDb } from "./shared/db.js";
import { getRateLimiter } from "./shared/rate-limiter.js";

// Cache imports
import {
  initCache,
  getCacheStats,
  closeCache,
} from "./cache/cache.js";
import { syncAll } from "./cache/sync.js";

// Domain module imports
import { taskTools, handleTaskTool } from "./domains/tasks/index.js";
import { habitTools, handleHabitTool } from "./domains/habits/index.js";
import { energyTools, handleEnergyTool } from "./domains/energy/index.js";
import { brainDumpTools, handleBrainDumpTool } from "./domains/brain-dump/index.js";
import { personalTasksTools, handlePersonalTasksTool } from "./domains/personal-tasks/index.js";

// =============================================================================
// CACHE LAYER
// =============================================================================
let cacheInitialized = false;
let syncInterval: ReturnType<typeof setInterval> | null = null;

// Auto-sync interval (5 minutes)
const AUTO_SYNC_INTERVAL_MS = 5 * 60 * 1000;

async function ensureCache(): Promise<boolean> {
  if (!cacheInitialized) {
    try {
      initCache();
      cacheInitialized = true;
      // Debug: Cache initialized (silent by default)

      // Check if cache is empty or stale
      const stats = getCacheStats();
      if (stats.taskCount === 0 || stats.isStale) {
        // Debug: syncing (silent by default)
        await syncAll();
      }
    } catch (error) {
      // Keep error logging - this is important
      console.error("[Cache] Failed to initialize cache:", error);
      return false;
    }
  }
  return true;
}

/**
 * Start automatic background sync interval
 */
function startAutoSync(): void {
  if (syncInterval) return; // Already running

  syncInterval = setInterval(async () => {
    try {
      await syncAll();
    } catch (error) {
      // Silent failure - will retry next interval
    }
  }, AUTO_SYNC_INTERVAL_MS);

  // Don't block process exit
  if (syncInterval.unref) {
    syncInterval.unref();
  }
}

/**
 * Stop automatic background sync
 */
function stopAutoSync(): void {
  if (syncInterval) {
    clearInterval(syncInterval);
    syncInterval = null;
  }
}

// =============================================================================
// RATE LIMITING
// =============================================================================
// Initialize rate limiter singleton
// Configuration is loaded from RATE_LIMIT_CONFIG in validation-constants.ts
// which respects environment variables (RATE_LIMIT_ENABLED, etc.)
const rateLimiter = getRateLimiter();

// =============================================================================
// MCP SERVER SETUP
// =============================================================================
const server = new Server(
  {
    name: "workos-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// =============================================================================
// TOOL DEFINITIONS
// =============================================================================
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      ...taskTools,
      ...habitTools,
      ...energyTools,
      ...brainDumpTools,
      ...personalTasksTools,
    ],
  };
});

// =============================================================================
// TOOL HANDLERS
// =============================================================================
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;

  // ===== RATE LIMITING CHECK =====
  // Check if request is allowed under current rate limits
  const rateLimitResult = rateLimiter.checkRateLimit(name);

  if (!rateLimitResult.allowed) {
    // Log rate limit violation for monitoring
    console.error(
      `[Rate Limit] Blocked ${name}: ${rateLimitResult.limitType} limit exceeded ` +
      `(${rateLimitResult.current}/${rateLimitResult.limit}), ` +
      `retry after ${rateLimitResult.retryAfterSeconds}s`
    );

    // Return error response with user-friendly message
    return {
      content: [
        {
          type: "text",
          text: rateLimitResult.message || "Rate limit exceeded. Please try again later.",
        },
      ],
      isError: true,
    };
  }

  // Record the request for sliding window tracking
  rateLimiter.recordRequest(name);

  // ===== EXISTING ROUTING =====
  const db = getDb();

  try {
    // Route to appropriate domain handler based on tool name
    if (name.includes("habit")) {
      return await handleHabitTool(name, args, db);
    } else if (name.includes("energy")) {
      return await handleEnergyTool(name, args, db);
    } else if (name.includes("brain") || name.includes("dump")) {
      return await handleBrainDumpTool(name, args, db);
    } else if (name.includes("personal_task")) {
      return await handlePersonalTasksTool(name, args, db);
    } else {
      // Default: route to task handler
      return await handleTaskTool(name, args, db);
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
    };
  }
});

// =============================================================================
// START SERVER
// =============================================================================
async function main() {
  // Initialize cache at startup (non-blocking, silent)
  ensureCache().then(success => {
    if (success) {
      // Start automatic sync every 5 minutes
      startAutoSync();
    }
  }).catch(err => {
    console.error("[Cache] Startup initialization failed:", err);
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Silent startup - only log when something goes wrong
}

// =============================================================================
// GRACEFUL SHUTDOWN HANDLERS
// =============================================================================
function shutdown(_signal: string) {
  // Silent shutdown
  stopAutoSync();
  closeCache();
  process.exit(0);
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("uncaughtException", (error) => {
  console.error("[WorkOS] Uncaught exception:", error);
  closeCache();
  process.exit(1);
});
process.on("unhandledRejection", (reason, promise) => {
  console.error("[WorkOS] Unhandled rejection at:", promise, "reason:", reason);
});

main().catch((error) => {
  console.error("[WorkOS] Fatal error:", error);
  closeCache();
  process.exit(1);
});
