import { Database } from "bun:sqlite";
import { drizzle, BunSQLiteDatabase } from "drizzle-orm/bun-sqlite";
import { eq, and, ne, asc, desc } from "drizzle-orm";
import * as cacheSchema from "./schema.js";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

// =============================================================================
// CACHE CONFIGURATION
// =============================================================================
const CACHE_DIR = path.join(os.homedir(), ".workos-cache");
const CACHE_DB_PATH = path.join(CACHE_DIR, "cache.db");
const STALENESS_THRESHOLD_MS = 15 * 60 * 1000; // 15 minutes

// =============================================================================
// CACHE MANAGER (Bun Native SQLite)
// =============================================================================
let cacheDb: BunSQLiteDatabase<typeof cacheSchema> | null = null;
let sqliteDb: Database | null = null;

/**
 * Initialize the SQLite cache database using Bun's native Database
 * Creates the cache directory and database file if they don't exist
 */
export function initCache(): BunSQLiteDatabase<typeof cacheSchema> {
  if (cacheDb) return cacheDb;

  try {
    // Ensure cache directory exists
    if (!fs.existsSync(CACHE_DIR)) {
      fs.mkdirSync(CACHE_DIR, { recursive: true });
    }

    // Create SQLite database using Bun's native API
    sqliteDb = new Database(CACHE_DB_PATH);

    // Enable WAL mode for better concurrent access
    sqliteDb.run("PRAGMA journal_mode = WAL");

    // Create all tables if they don't exist
    sqliteDb.run(`
      CREATE TABLE IF NOT EXISTS cached_clients (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'client',
        color TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
      )
    `);

    sqliteDb.run(`
      CREATE TABLE IF NOT EXISTS cached_tasks (
        id INTEGER PRIMARY KEY,
        client_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'backlog',
        category TEXT NOT NULL DEFAULT 'work',
        value_tier TEXT DEFAULT 'progress',
        effort_estimate INTEGER DEFAULT 2,
        effort_actual INTEGER,
        drain_type TEXT,
        sort_order INTEGER DEFAULT 0,
        subtasks TEXT DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT,
        backlog_entered_at TEXT,
        points_ai_guess INTEGER,
        points_final INTEGER,
        points_adjusted_at TEXT
      )
    `);

    sqliteDb.run(`
      CREATE TABLE IF NOT EXISTS cached_daily_goals (
        id INTEGER PRIMARY KEY,
        date TEXT NOT NULL UNIQUE,
        target_points INTEGER DEFAULT 18,
        earned_points INTEGER DEFAULT 0,
        task_count INTEGER DEFAULT 0,
        current_streak INTEGER DEFAULT 0,
        longest_streak INTEGER DEFAULT 0,
        last_goal_hit_date TEXT,
        daily_debt INTEGER DEFAULT 0,
        weekly_debt INTEGER DEFAULT 0,
        pressure_level INTEGER DEFAULT 0,
        updated_at TEXT
      )
    `);

    sqliteDb.run(`
      CREATE TABLE IF NOT EXISTS cached_habits (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        emoji TEXT,
        frequency TEXT NOT NULL DEFAULT 'daily',
        target_count INTEGER DEFAULT 1,
        current_streak INTEGER DEFAULT 0,
        longest_streak INTEGER DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )
    `);

    sqliteDb.run(`
      CREATE TABLE IF NOT EXISTS cache_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )
    `);

    // Create indexes
    sqliteDb.run("CREATE INDEX IF NOT EXISTS idx_cached_tasks_status ON cached_tasks(status)");
    sqliteDb.run("CREATE INDEX IF NOT EXISTS idx_cached_tasks_client_id ON cached_tasks(client_id)");
    sqliteDb.run("CREATE INDEX IF NOT EXISTS idx_cached_tasks_completed_at ON cached_tasks(completed_at)");

    // Create Drizzle ORM instance with Bun SQLite
    cacheDb = drizzle(sqliteDb, { schema: cacheSchema });

    console.error("[Cache] ✓ Cache initialized successfully (Bun SQLite)");
    return cacheDb;
  } catch (error) {
    console.error("[Cache] Failed to initialize cache:", error);
    throw error;
  }
}

/**
 * Close the cache database connection
 */
export function closeCache(): void {
  if (sqliteDb) {
    sqliteDb.close();
    sqliteDb = null;
    cacheDb = null;
  }
}

/**
 * Get the cache database instance
 */
export function getCacheDb(): BunSQLiteDatabase<typeof cacheSchema> {
  if (!cacheDb) {
    return initCache();
  }
  return cacheDb;
}

/**
 * Get the last sync timestamp
 */
export function getLastSyncTime(): Date | null {
  const db = getCacheDb();
  const [meta] = db
    .select()
    .from(cacheSchema.cacheMeta)
    .where(eq(cacheSchema.cacheMeta.key, "lastSyncAt"))
    .all();

  if (!meta) return null;
  return new Date(meta.value);
}

/**
 * Update the last sync timestamp
 */
export function setLastSyncTime(time: Date = new Date()): void {
  const db = getCacheDb();
  const now = new Date().toISOString();

  db.insert(cacheSchema.cacheMeta)
    .values({
      key: "lastSyncAt",
      value: time.toISOString(),
      updatedAt: now,
    })
    .onConflictDoUpdate({
      target: cacheSchema.cacheMeta.key,
      set: {
        value: time.toISOString(),
        updatedAt: now,
      },
    })
    .run();
}

/**
 * Check if the cache is stale (older than threshold)
 */
export function isCacheStale(): boolean {
  const lastSync = getLastSyncTime();
  if (!lastSync) return true;

  const age = Date.now() - lastSync.getTime();
  return age > STALENESS_THRESHOLD_MS;
}

// =============================================================================
// CACHED DATA ACCESS
// =============================================================================

/**
 * Get cached tasks with optional status filter
 */
export function getCachedTasks(status?: string, limit = 50): cacheSchema.CachedTask[] {
  const db = getCacheDb();

  if (status) {
    // Explicit status filter - return exactly what's requested
    return db
      .select()
      .from(cacheSchema.cachedTasks)
      .where(
        and(
          eq(cacheSchema.cachedTasks.category, "work"),
          eq(cacheSchema.cachedTasks.status, status),
        ),
      )
      .orderBy(asc(cacheSchema.cachedTasks.sortOrder), desc(cacheSchema.cachedTasks.createdAt))
      .limit(limit)
      .all();
  }

  // No status filter - exclude completed tasks by default
  return db
    .select()
    .from(cacheSchema.cachedTasks)
    .where(
      and(
        eq(cacheSchema.cachedTasks.category, "work"),
        ne(cacheSchema.cachedTasks.status, "done"),
      ),
    )
    .orderBy(asc(cacheSchema.cachedTasks.sortOrder), desc(cacheSchema.cachedTasks.createdAt))
    .limit(limit)
    .all();
}

/**
 * Get tasks by client ID
 */
export function getCachedTasksByClient(clientId: number, status?: string, limit = 50): cacheSchema.CachedTask[] {
  const db = getCacheDb();

  const conditions = [
    eq(cacheSchema.cachedTasks.category, "work"),
    eq(cacheSchema.cachedTasks.clientId, clientId),
  ];
  if (status) {
    // Explicit status filter - return exactly what's requested
    conditions.push(eq(cacheSchema.cachedTasks.status, status));
  } else {
    // No status filter - exclude completed tasks by default
    conditions.push(ne(cacheSchema.cachedTasks.status, "done"));
  }

  return db
    .select()
    .from(cacheSchema.cachedTasks)
    .where(and(...conditions))
    .orderBy(asc(cacheSchema.cachedTasks.sortOrder), desc(cacheSchema.cachedTasks.createdAt))
    .limit(limit)
    .all();
}

/**
 * Get a single cached task by ID
 */
export function getCachedTask(id: number): cacheSchema.CachedTask | undefined {
  const db = getCacheDb();
  const [task] = db
    .select()
    .from(cacheSchema.cachedTasks)
    .where(eq(cacheSchema.cachedTasks.id, id))
    .all();
  return task;
}

/**
 * Get all cached clients
 */
export function getCachedClients(): cacheSchema.CachedClient[] {
  const db = getCacheDb();
  return db
    .select()
    .from(cacheSchema.cachedClients)
    .where(eq(cacheSchema.cachedClients.isActive, 1))
    .all();
}

/**
 * Get a single cached client by ID
 */
export function getCachedClient(id: number): cacheSchema.CachedClient | undefined {
  const db = getCacheDb();
  const [client] = db
    .select()
    .from(cacheSchema.cachedClients)
    .where(eq(cacheSchema.cachedClients.id, id))
    .all();
  return client;
}

/**
 * Get cached daily goals
 */
export function getCachedDailyGoals(limit = 7): cacheSchema.CachedDailyGoal[] {
  const db = getCacheDb();
  return db
    .select()
    .from(cacheSchema.cachedDailyGoals)
    .orderBy(desc(cacheSchema.cachedDailyGoals.date))
    .limit(limit)
    .all();
}

/**
 * Get the latest cached daily goal
 */
export function getLatestCachedDailyGoal(): cacheSchema.CachedDailyGoal | undefined {
  const db = getCacheDb();
  const [goal] = db
    .select()
    .from(cacheSchema.cachedDailyGoals)
    .orderBy(desc(cacheSchema.cachedDailyGoals.date))
    .limit(1)
    .all();
  return goal;
}

/**
 * Get cached habits
 */
export function getCachedHabits(): cacheSchema.CachedHabit[] {
  const db = getCacheDb();
  return db
    .select()
    .from(cacheSchema.cachedHabits)
    .where(eq(cacheSchema.cachedHabits.isActive, 1))
    .orderBy(asc(cacheSchema.cachedHabits.sortOrder))
    .all();
}

// =============================================================================
// CACHE INVALIDATION (Write-through support)
// =============================================================================

/**
 * Upsert a single task into the cache
 */
export function upsertCachedTask(task: Partial<cacheSchema.CachedTask> & { id: number }): void {
  const db = getCacheDb();
  const now = new Date().toISOString();

  const existing = getCachedTask(task.id);
  if (existing) {
    db.update(cacheSchema.cachedTasks)
      .set({ ...task, updatedAt: now })
      .where(eq(cacheSchema.cachedTasks.id, task.id))
      .run();
  } else {
    db.insert(cacheSchema.cachedTasks)
      .values({
        ...task,
        createdAt: task.createdAt || now,
        updatedAt: now,
      } as any)
      .run();
  }
}

/**
 * Delete a task from the cache
 */
export function deleteCachedTask(id: number): void {
  const db = getCacheDb();
  db.delete(cacheSchema.cachedTasks)
    .where(eq(cacheSchema.cachedTasks.id, id))
    .run();
}

/**
 * Upsert a single client into the cache
 */
export function upsertCachedClient(client: Partial<cacheSchema.CachedClient> & { id: number }): void {
  const db = getCacheDb();
  const now = new Date().toISOString();

  const existing = getCachedClient(client.id);
  if (existing) {
    db.update(cacheSchema.cachedClients)
      .set(client)
      .where(eq(cacheSchema.cachedClients.id, client.id))
      .run();
  } else {
    db.insert(cacheSchema.cachedClients)
      .values({
        ...client,
        createdAt: client.createdAt || now,
      } as any)
      .run();
  }
}

/**
 * Clear all cached data (used before full sync)
 */
export function clearCache(): void {
  const db = getCacheDb();
  db.delete(cacheSchema.cachedTasks).run();
  db.delete(cacheSchema.cachedClients).run();
  db.delete(cacheSchema.cachedDailyGoals).run();
  db.delete(cacheSchema.cachedHabits).run();
  // Don't clear cache_meta to preserve sync timestamps
}

/**
 * Get cache statistics
 */
export function getCacheStats(): {
  taskCount: number;
  clientCount: number;
  dailyGoalCount: number;
  habitCount: number;
  lastSyncAt: string | null;
  isStale: boolean;
} {
  const db = getCacheDb();

  const taskCount = db.select().from(cacheSchema.cachedTasks).all().length;
  const clientCount = db.select().from(cacheSchema.cachedClients).all().length;
  const dailyGoalCount = db.select().from(cacheSchema.cachedDailyGoals).all().length;
  const habitCount = db.select().from(cacheSchema.cachedHabits).all().length;

  const lastSync = getLastSyncTime();

  return {
    taskCount,
    clientCount,
    dailyGoalCount,
    habitCount,
    lastSyncAt: lastSync?.toISOString() || null,
    isStale: isCacheStale(),
  };
}
