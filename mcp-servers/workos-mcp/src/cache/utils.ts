import { initCache, isCacheStale, getCacheStats } from "./cache.js";
import { syncAll } from "./sync.js";

/**
 * MCP CallToolResult type
 * Represents the standard response format for MCP tool handlers
 */
interface CallToolResult {
  content: [
    {
      type: "text";
      text: string;
    }
  ];
}

// =============================================================================
// CACHE INITIALIZATION STATE
// =============================================================================
let cacheInitialized = false;

/**
 * Ensure the cache is initialized and synced
 * This is an internal helper that mimics the ensureCache() pattern from index.ts
 *
 * @returns Promise<boolean> - true if cache is ready, false if initialization failed
 */
async function ensureCache(): Promise<boolean> {
  if (!cacheInitialized) {
    try {
      initCache();
      cacheInitialized = true;
      console.error("[Cache] SQLite cache initialized");

      // Check if cache is empty or stale
      const stats = getCacheStats();
      if (stats.taskCount === 0 || stats.isStale) {
        console.error("[Cache] Cache empty or stale, syncing from Neon...");
        await syncAll();
      }
    } catch (error) {
      console.error("[Cache] Failed to initialize cache:", error);
      return false;
    }
  }
  return true;
}

/**
 * Higher-order function that implements cache-first-with-fallback pattern
 *
 * This function encapsulates the repetitive cache-first logic used across multiple
 * WorkOS MCP server handlers. It handles:
 * 1. Cache initialization via ensureCache()
 * 2. Cache staleness check via isCacheStale()
 * 3. Try-catch wrapper for cache reads with error logging
 * 4. Automatic fallback to Neon database on cache miss/error
 * 5. Consistent logging format
 * 6. MCP response formatting
 *
 * @template T - The type of data being cached (e.g., CachedTask[], CachedClient[])
 * @param cacheReader - Synchronous function that reads from cache
 * @param neonFallback - Async function that queries Neon database as fallback
 * @param entityName - Human-readable entity name for logging (e.g., "tasks", "clients", "habits")
 * @returns Promise<CallToolResult> - MCP-formatted response with cached or fresh data
 *
 * @example
 * ```typescript
 * // Simple cache read
 * return withCacheFirst(
 *   () => getCachedClients(),
 *   async () => db.select().from(schema.clients).where(eq(schema.clients.isActive, 1)),
 *   "clients"
 * );
 *
 * // Complex cache read with filtering and enrichment
 * return withCacheFirst(
 *   () => {
 *     const tasks = getCachedTasks(status, limit);
 *     const clients = getCachedClients();
 *     const clientMap = new Map(clients.map(c => [c.id, c.name]));
 *     return tasks.map(t => ({
 *       ...t,
 *       clientName: t.clientId ? clientMap.get(t.clientId) || null : null,
 *     }));
 *   },
 *   async () => {
 *     const conditions = [];
 *     if (status) conditions.push(eq(schema.tasks.status, status));
 *     return db.select().from(schema.tasks).where(and(...conditions));
 *   },
 *   "tasks"
 * );
 * ```
 */
export async function withCacheFirst<T>(
  cacheReader: () => T,
  neonFallback: () => Promise<T>,
  entityName: string
): Promise<CallToolResult> {
  // Step 1: Ensure cache is initialized
  const cacheAvailable = await ensureCache();

  // Step 2: Check if cache is available and fresh
  if (cacheAvailable && !isCacheStale()) {
    // Step 3: Try to read from cache
    try {
      const data = cacheReader();

      // Step 4: Log cache hit with count (if array)
      const count = Array.isArray(data) ? data.length : "N/A";
      console.error(`[Cache] Served ${count} ${entityName} from cache`);

      // Step 5: Return cached data in MCP format
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(data, null, 2),
          },
        ],
      };
    } catch (cacheError) {
      // Log cache read error and fall through to Neon fallback
      console.error("[Cache] Error reading from cache, falling back to Neon:", cacheError);
    }
  }

  // Step 6: Fallback to Neon database query
  const data = await neonFallback();

  // Step 7: Return Neon data in MCP format (same format as cache)
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(data, null, 2),
      },
    ],
  };
}
