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
 * ## Problem This Solves
 * The WorkOS MCP server had repetitive cache-first logic duplicated across 8+ handlers,
 * resulting in ~150 lines of near-duplicate code. Each handler repeated the same pattern:
 * ensureCache() call, isCacheStale() check, try-catch for cache reads, error logging,
 * and fallback to Neon queries. This function abstracts that cross-cutting concern into
 * a reusable, type-safe utility.
 *
 * ## What It Does
 * This function encapsulates the complete cache-first-with-fallback lifecycle:
 * 1. **Cache initialization**: Calls ensureCache() to initialize SQLite cache if needed
 * 2. **Staleness check**: Uses isCacheStale() to determine if cache data is too old
 * 3. **Cache read**: Executes cacheReader() function with try-catch error handling
 * 4. **Automatic fallback**: Falls back to neonFallback() on cache miss, staleness, or errors
 * 5. **Consistent logging**: Logs cache hits/misses with entity counts for debugging
 * 6. **MCP formatting**: Returns data in standard MCP CallToolResult format
 *
 * ## Error Handling
 * - Cache initialization failures are logged but don't throw (falls back to Neon)
 * - Cache read exceptions are caught and logged, triggering automatic Neon fallback
 * - Neon fallback errors propagate to the caller (intentional - DB errors should surface)
 * - All errors include detailed context for debugging (entity name, error details)
 *
 * ## Edge Cases Handled
 * - Empty cache (first run): Automatically syncs from Neon via ensureCache()
 * - Stale cache: Detected via isCacheStale() and triggers Neon fallback
 * - Cache corruption: Try-catch catches read errors and falls back gracefully
 * - Cache unavailable: If ensureCache() fails, immediately uses Neon fallback
 * - Complex data transformations: Supports arbitrary logic in cacheReader (filtering, enrichment, etc.)
 *
 * ## Type Safety
 * The generic type parameter `T` ensures type consistency between cache and Neon data:
 * - cacheReader() must return type T
 * - neonFallback() must return Promise<T>
 * - Both must return the same data structure (though types may need assertions for Date/string)
 *
 * ## When to Use This Function
 * Use `withCacheFirst` for any handler that needs cache-first behavior:
 * ✅ Reading tasks, clients, habits, projects, time entries, etc.
 * ✅ Handlers that need filtering, sorting, or data enrichment from cache
 * ✅ Any pattern that needs cache-first-with-fallback behavior
 *
 * Do NOT use for:
 * ❌ Write operations (use direct DB access)
 * ❌ Real-time data that should never be cached
 * ❌ Handlers that don't have a Neon fallback option
 *
 * @template T - The type of data being cached and returned (e.g., CachedTask[], CachedClient[], CachedHabit[])
 *               Must match the return type of both cacheReader and neonFallback
 *
 * @param {() => T} cacheReader - Synchronous function that reads from SQLite cache.
 *                                 Can include filtering, sorting, enrichment, or any data transformation.
 *                                 Should be a pure function (no side effects).
 *                                 Example: () => getCachedClients()
 *                                 Example: () => getCachedTasks(status, limit).map(enrichTask)
 *
 * @param {() => Promise<T>} neonFallback - Async function that queries Neon Postgres as fallback.
 *                                           Called when cache is unavailable, stale, or throws an error.
 *                                           Should return the same data structure as cacheReader.
 *                                           Example: async () => db.select().from(schema.clients)
 *
 * @param {string} entityName - Human-readable entity name for logging (e.g., "tasks", "clients", "habits").
 *                               Used in console.error messages to track cache hits/misses.
 *                               Should be plural lowercase (matches database table conventions).
 *
 * @returns {Promise<CallToolResult>} MCP-formatted response containing the data as JSON text.
 *                                     Structure: { content: [{ type: "text", text: JSON.stringify(data) }] }
 *                                     Data source is transparent to caller (could be cache or Neon).
 *
 * @throws {Error} Only throws if neonFallback() throws (cache errors are caught and logged).
 *                 This is intentional - database errors should surface to the caller.
 *
 * @example
 * // Simple cache read with direct fallback
 * return withCacheFirst(
 *   () => getCachedClients(),
 *   async () => db.select().from(schema.clients).where(eq(schema.clients.isActive, 1)),
 *   "clients"
 * );
 *
 * @example
 * // Complex cache read with filtering and enrichment
 * return withCacheFirst(
 *   () => {
 *     // Read from cache with filters
 *     const tasks = status ? getCachedTasksByStatus(status, limit) : getCachedTasks(limit);
 *
 *     // Enrich with client names from cache
 *     const clients = getCachedClients();
 *     const clientMap = new Map(clients.map(c => [c.id, c.name]));
 *
 *     return tasks.map(t => ({
 *       ...t,
 *       clientName: t.clientId ? clientMap.get(t.clientId) || null : null,
 *     }));
 *   },
 *   async () => {
 *     // Neon fallback with same filters
 *     const conditions = [eq(schema.tasks.isActive, 1)];
 *     if (status) conditions.push(eq(schema.tasks.status, status));
 *
 *     return db.select().from(schema.tasks)
 *       .where(and(...conditions))
 *       .limit(limit || 100);
 *   },
 *   "tasks"
 * );
 *
 * @example
 * // Conditional cache read based on parameters
 * return withCacheFirst(
 *   () => {
 *     // Use different cache readers based on parameters
 *     if (clientId) {
 *       return getCachedTasksByClient(clientId, status, limit);
 *     }
 *     return getCachedTasks(status, limit);
 *   },
 *   async () => {
 *     // Neon fallback with same conditional logic
 *     const conditions = [eq(schema.tasks.isActive, 1)];
 *     if (clientId) conditions.push(eq(schema.tasks.clientId, clientId));
 *     if (status) conditions.push(eq(schema.tasks.status, status));
 *
 *     return db.select().from(schema.tasks).where(and(...conditions));
 *   },
 *   "tasks"
 * );
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
