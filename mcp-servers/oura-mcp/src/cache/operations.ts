// =============================================================================
// OURA MCP CACHE OPERATIONS
// CRUD operations for cached Oura health data
// Implements cache-first strategy with TTL-based staleness detection
// =============================================================================

import type Database from "better-sqlite3";
import { getDb } from "./db.js";
import { calculateExpiresAt, isExpired } from "./schema.js";
import type {
  CachedSleep,
  CachedReadiness,
  CachedActivity,
  CachedHeartRate,
  CachedToken,
  CacheMeta,
} from "./schema.js";
import type {
  DailySleep,
  DailyReadiness,
  DailyActivity,
  HeartRateData,
  DateString,
  DateTimeString,
} from "../api/types.js";

// =============================================================================
// CONFIGURATION
// =============================================================================

/**
 * Default cache TTL in hours
 * Acceptance criteria specifies 1 hour for stale data detection
 */
const DEFAULT_CACHE_TTL_HOURS = 1;

// =============================================================================
// SLEEP DATA OPERATIONS
// =============================================================================

/**
 * Get cached sleep data by date
 * Returns null if not found or expired
 *
 * @param day - Date string (YYYY-MM-DD)
 * @returns Parsed sleep data or null
 */
export function getCachedSleep(day: DateString): DailySleep | null {
  const db = getDb();
  const stmt = db.prepare<[string]>(`
    SELECT * FROM sleep_data WHERE day = ?
  `);
  const row = stmt.get(day) as CachedSleep | undefined;

  if (!row) {
    return null;
  }

  // Check if cache entry is expired
  if (isExpired(row.expires_at)) {
    // Delete expired entry
    deleteCachedSleep(day);
    return null;
  }

  // Parse and return the data
  return JSON.parse(row.data) as DailySleep;
}

/**
 * Get cached sleep data for a date range
 *
 * @param startDate - Start date (YYYY-MM-DD)
 * @param endDate - End date (YYYY-MM-DD)
 * @returns Array of sleep data
 */
export function getCachedSleepRange(
  startDate: DateString,
  endDate: DateString
): DailySleep[] {
  const db = getDb();
  const stmt = db.prepare<[string, string]>(`
    SELECT * FROM sleep_data
    WHERE day >= ? AND day <= ?
    ORDER BY day DESC
  `);
  const rows = stmt.all(startDate, endDate) as CachedSleep[];

  return rows
    .filter((row) => !isExpired(row.expires_at))
    .map((row) => JSON.parse(row.data) as DailySleep);
}

/**
 * Set cached sleep data
 *
 * @param data - Sleep data from Oura API
 * @param ttlHours - Time to live in hours (default: 1)
 */
export function setCachedSleep(
  data: DailySleep,
  ttlHours: number = DEFAULT_CACHE_TTL_HOURS
): void {
  const db = getDb();
  const now = new Date().toISOString();
  const expiresAt = calculateExpiresAt(ttlHours);

  const stmt = db.prepare(`
    INSERT OR REPLACE INTO sleep_data (id, day, data, cached_at, expires_at)
    VALUES (?, ?, ?, ?, ?)
  `);

  stmt.run(data.id, data.day, JSON.stringify(data), now, expiresAt);
}

/**
 * Delete cached sleep data by date
 *
 * @param day - Date string (YYYY-MM-DD)
 */
export function deleteCachedSleep(day: DateString): void {
  const db = getDb();
  const stmt = db.prepare<[string]>(`
    DELETE FROM sleep_data WHERE day = ?
  `);
  stmt.run(day);
}

// =============================================================================
// READINESS DATA OPERATIONS
// =============================================================================

/**
 * Get cached readiness data by date
 * Returns null if not found or expired
 *
 * @param day - Date string (YYYY-MM-DD)
 * @returns Parsed readiness data or null
 */
export function getCachedReadiness(day: DateString): DailyReadiness | null {
  const db = getDb();
  const stmt = db.prepare<[string]>(`
    SELECT * FROM readiness_data WHERE day = ?
  `);
  const row = stmt.get(day) as CachedReadiness | undefined;

  if (!row) {
    return null;
  }

  // Check if cache entry is expired
  if (isExpired(row.expires_at)) {
    // Delete expired entry
    deleteCachedReadiness(day);
    return null;
  }

  // Parse and return the data
  return JSON.parse(row.data) as DailyReadiness;
}

/**
 * Get cached readiness data for a date range
 *
 * @param startDate - Start date (YYYY-MM-DD)
 * @param endDate - End date (YYYY-MM-DD)
 * @returns Array of readiness data
 */
export function getCachedReadinessRange(
  startDate: DateString,
  endDate: DateString
): DailyReadiness[] {
  const db = getDb();
  const stmt = db.prepare<[string, string]>(`
    SELECT * FROM readiness_data
    WHERE day >= ? AND day <= ?
    ORDER BY day DESC
  `);
  const rows = stmt.all(startDate, endDate) as CachedReadiness[];

  return rows
    .filter((row) => !isExpired(row.expires_at))
    .map((row) => JSON.parse(row.data) as DailyReadiness);
}

/**
 * Set cached readiness data
 *
 * @param data - Readiness data from Oura API
 * @param ttlHours - Time to live in hours (default: 1)
 */
export function setCachedReadiness(
  data: DailyReadiness,
  ttlHours: number = DEFAULT_CACHE_TTL_HOURS
): void {
  const db = getDb();
  const now = new Date().toISOString();
  const expiresAt = calculateExpiresAt(ttlHours);

  const stmt = db.prepare(`
    INSERT OR REPLACE INTO readiness_data (id, day, data, cached_at, expires_at)
    VALUES (?, ?, ?, ?, ?)
  `);

  stmt.run(data.id, data.day, JSON.stringify(data), now, expiresAt);
}

/**
 * Delete cached readiness data by date
 *
 * @param day - Date string (YYYY-MM-DD)
 */
export function deleteCachedReadiness(day: DateString): void {
  const db = getDb();
  const stmt = db.prepare<[string]>(`
    DELETE FROM readiness_data WHERE day = ?
  `);
  stmt.run(day);
}

// =============================================================================
// ACTIVITY DATA OPERATIONS
// =============================================================================

/**
 * Get cached activity data by date
 * Returns null if not found or expired
 *
 * @param day - Date string (YYYY-MM-DD)
 * @returns Parsed activity data or null
 */
export function getCachedActivity(day: DateString): DailyActivity | null {
  const db = getDb();
  const stmt = db.prepare<[string]>(`
    SELECT * FROM activity_data WHERE day = ?
  `);
  const row = stmt.get(day) as CachedActivity | undefined;

  if (!row) {
    return null;
  }

  // Check if cache entry is expired
  if (isExpired(row.expires_at)) {
    // Delete expired entry
    deleteCachedActivity(day);
    return null;
  }

  // Parse and return the data
  return JSON.parse(row.data) as DailyActivity;
}

/**
 * Get cached activity data for a date range
 *
 * @param startDate - Start date (YYYY-MM-DD)
 * @param endDate - End date (YYYY-MM-DD)
 * @returns Array of activity data
 */
export function getCachedActivityRange(
  startDate: DateString,
  endDate: DateString
): DailyActivity[] {
  const db = getDb();
  const stmt = db.prepare<[string, string]>(`
    SELECT * FROM activity_data
    WHERE day >= ? AND day <= ?
    ORDER BY day DESC
  `);
  const rows = stmt.all(startDate, endDate) as CachedActivity[];

  return rows
    .filter((row) => !isExpired(row.expires_at))
    .map((row) => JSON.parse(row.data) as DailyActivity);
}

/**
 * Set cached activity data
 *
 * @param data - Activity data from Oura API
 * @param ttlHours - Time to live in hours (default: 1)
 */
export function setCachedActivity(
  data: DailyActivity,
  ttlHours: number = DEFAULT_CACHE_TTL_HOURS
): void {
  const db = getDb();
  const now = new Date().toISOString();
  const expiresAt = calculateExpiresAt(ttlHours);

  const stmt = db.prepare(`
    INSERT OR REPLACE INTO activity_data (id, day, data, cached_at, expires_at)
    VALUES (?, ?, ?, ?, ?)
  `);

  stmt.run(data.id, data.day, JSON.stringify(data), now, expiresAt);
}

/**
 * Delete cached activity data by date
 *
 * @param day - Date string (YYYY-MM-DD)
 */
export function deleteCachedActivity(day: DateString): void {
  const db = getDb();
  const stmt = db.prepare<[string]>(`
    DELETE FROM activity_data WHERE day = ?
  `);
  stmt.run(day);
}

// =============================================================================
// HEART RATE DATA OPERATIONS
// =============================================================================

/**
 * Get cached heart rate data by date
 * Returns all heart rate data points for the given date
 *
 * @param day - Date string (YYYY-MM-DD)
 * @returns Array of heart rate data points
 */
export function getCachedHeartRate(day: DateString): HeartRateData[] {
  const db = getDb();
  const stmt = db.prepare<[string]>(`
    SELECT * FROM heart_rate_data
    WHERE day = ?
    ORDER BY timestamp ASC
  `);
  const rows = stmt.all(day) as CachedHeartRate[];

  return rows
    .filter((row) => !isExpired(row.expires_at))
    .map((row) => ({
      bpm: row.bpm,
      source: row.source as import("../api/types.js").HeartRateSource,
      timestamp: row.timestamp,
    }));
}

/**
 * Get cached heart rate data for a date range
 *
 * @param startDate - Start date (YYYY-MM-DD)
 * @param endDate - End date (YYYY-MM-DD)
 * @returns Array of heart rate data points
 */
export function getCachedHeartRateRange(
  startDate: DateString,
  endDate: DateString
): HeartRateData[] {
  const db = getDb();
  const stmt = db.prepare<[string, string]>(`
    SELECT * FROM heart_rate_data
    WHERE day >= ? AND day <= ?
    ORDER BY timestamp ASC
  `);
  const rows = stmt.all(startDate, endDate) as CachedHeartRate[];

  return rows
    .filter((row) => !isExpired(row.expires_at))
    .map((row) => ({
      bpm: row.bpm,
      source: row.source as import("../api/types.js").HeartRateSource,
      timestamp: row.timestamp,
    }));
}

/**
 * Set cached heart rate data for a specific date
 * Replaces all heart rate data for the given date
 *
 * @param day - Date string (YYYY-MM-DD)
 * @param dataPoints - Array of heart rate data points
 * @param ttlHours - Time to live in hours (default: 1)
 */
export function setCachedHeartRate(
  day: DateString,
  dataPoints: HeartRateData[],
  ttlHours: number = DEFAULT_CACHE_TTL_HOURS
): void {
  const db = getDb();

  // First, delete existing data for this date
  deleteCachedHeartRate(day);

  if (dataPoints.length === 0) {
    return;
  }

  const now = new Date().toISOString();
  const expiresAt = calculateExpiresAt(ttlHours);

  const stmt = db.prepare(`
    INSERT INTO heart_rate_data (timestamp, bpm, source, day, cached_at, expires_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);

  // Use a transaction for bulk insert
  const insertMany = db.transaction((data: HeartRateData[]) => {
    for (const point of data) {
      stmt.run(point.timestamp, point.bpm, point.source, day, now, expiresAt);
    }
  });

  insertMany(dataPoints);
}

/**
 * Delete cached heart rate data by date
 *
 * @param day - Date string (YYYY-MM-DD)
 */
export function deleteCachedHeartRate(day: DateString): void {
  const db = getDb();
  const stmt = db.prepare<[string]>(`
    DELETE FROM heart_rate_data WHERE day = ?
  `);
  stmt.run(day);
}

// =============================================================================
// CACHE METADATA OPERATIONS
// =============================================================================

/**
 * Get cache metadata value
 *
 * @param key - Metadata key
 * @returns Metadata value or null if not found
 */
export function getCacheMeta(key: string): string | null {
  const db = getDb();
  const stmt = db.prepare<[string]>(`
    SELECT value FROM cache_meta WHERE key = ?
  `);
  const row = stmt.get(key) as CacheMeta | undefined;
  return row ? row.value : null;
}

/**
 * Set cache metadata value
 *
 * @param key - Metadata key
 * @param value - Metadata value
 */
export function setCacheMeta(key: string, value: string): void {
  const db = getDb();
  const now = new Date().toISOString();

  const stmt = db.prepare(`
    INSERT OR REPLACE INTO cache_meta (key, value, updated_at)
    VALUES (?, ?, ?)
  `);

  stmt.run(key, value, now);
}

/**
 * Get last sync timestamp
 *
 * @returns Last sync time as Date or null if never synced
 */
export function getLastSyncTime(): Date | null {
  const value = getCacheMeta("last_sync_time");
  return value ? new Date(value) : null;
}

/**
 * Update last sync timestamp
 *
 * @param time - Sync time (defaults to now)
 */
export function setLastSyncTime(time: Date = new Date()): void {
  setCacheMeta("last_sync_time", time.toISOString());
}

// =============================================================================
// CACHE INVALIDATION
// =============================================================================

/**
 * Clear all cached health data
 * Does NOT clear api_tokens or cache_meta
 */
export function clearHealthCache(): void {
  const db = getDb();

  db.exec(`
    DELETE FROM sleep_data;
    DELETE FROM readiness_data;
    DELETE FROM activity_data;
    DELETE FROM heart_rate_data;
  `);
}

/**
 * Clear expired cache entries from all tables
 *
 * @returns Number of deleted rows
 */
export function clearExpiredCache(): number {
  const db = getDb();
  const now = new Date().toISOString();
  let totalDeleted = 0;

  const tables = ["sleep_data", "readiness_data", "activity_data", "heart_rate_data"];

  for (const table of tables) {
    const stmt = db.prepare(`DELETE FROM ${table} WHERE expires_at < ?`);
    const result = stmt.run(now);
    totalDeleted += result.changes;
  }

  return totalDeleted;
}

/**
 * Invalidate cache for a specific date across all data types
 * Forces fresh fetch from API on next request
 *
 * @param day - Date string (YYYY-MM-DD)
 */
export function invalidateCacheForDate(day: DateString): void {
  deleteCachedSleep(day);
  deleteCachedReadiness(day);
  deleteCachedActivity(day);
  deleteCachedHeartRate(day);
}

// =============================================================================
// CACHE STATISTICS
// =============================================================================

/**
 * Get cache statistics for monitoring and debugging
 *
 * @returns Object with cache statistics
 */
export function getCacheStats(): {
  sleepCount: number;
  readinessCount: number;
  activityCount: number;
  heartRateCount: number;
  lastSyncAt: string | null;
  dbSize: number;
} {
  const db = getDb();

  // Count non-expired entries
  const now = new Date().toISOString();

  const getSleepCount = db.prepare(`SELECT COUNT(*) as count FROM sleep_data WHERE expires_at > ?`);
  const getReadinessCount = db.prepare(`SELECT COUNT(*) as count FROM readiness_data WHERE expires_at > ?`);
  const getActivityCount = db.prepare(`SELECT COUNT(*) as count FROM activity_data WHERE expires_at > ?`);
  const getHeartRateCount = db.prepare(`SELECT COUNT(*) as count FROM heart_rate_data WHERE expires_at > ?`);

  const sleepCount = (getSleepCount.get(now) as { count: number }).count;
  const readinessCount = (getReadinessCount.get(now) as { count: number }).count;
  const activityCount = (getActivityCount.get(now) as { count: number }).count;
  const heartRateCount = (getHeartRateCount.get(now) as { count: number }).count;

  const lastSync = getLastSyncTime();

  // Get database file size
  const dbStats = db.prepare("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()").get() as { size: number };

  return {
    sleepCount,
    readinessCount,
    activityCount,
    heartRateCount,
    lastSyncAt: lastSync?.toISOString() || null,
    dbSize: dbStats.size,
  };
}

/**
 * Check if cache has data for a specific date
 *
 * @param day - Date string (YYYY-MM-DD)
 * @returns Object indicating which data types are cached for this date
 */
export function getCacheCoverageForDate(day: DateString): {
  hasSleep: boolean;
  hasReadiness: boolean;
  hasActivity: boolean;
  hasHeartRate: boolean;
} {
  return {
    hasSleep: getCachedSleep(day) !== null,
    hasReadiness: getCachedReadiness(day) !== null,
    hasActivity: getCachedActivity(day) !== null,
    hasHeartRate: getCachedHeartRate(day).length > 0,
  };
}
