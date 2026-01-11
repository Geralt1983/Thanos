// =============================================================================
// OURA MCP CACHE SCHEMA
// SQLite schema for caching Oura Ring API data locally
// Uses better-sqlite3 for fast, synchronous database operations
// =============================================================================

import type Database from "better-sqlite3";
import type {
  DailySleep,
  DailyReadiness,
  DailyActivity,
  HeartRateData,
  DateString,
  DateTimeString,
} from "../api/types.js";

// =============================================================================
// CACHED DATA TYPES
// =============================================================================

/**
 * Cached sleep data with metadata
 */
export interface CachedSleep {
  /** Unique identifier from Oura API */
  id: string;
  /** Date of the sleep period (YYYY-MM-DD) */
  day: DateString;
  /** Full sleep data as JSON string */
  data: string;
  /** When this data was cached (ISO 8601) */
  cached_at: DateTimeString;
  /** When this cache entry expires (ISO 8601) */
  expires_at: DateTimeString;
}

/**
 * Cached readiness data with metadata
 */
export interface CachedReadiness {
  /** Unique identifier from Oura API */
  id: string;
  /** Date of the readiness data (YYYY-MM-DD) */
  day: DateString;
  /** Full readiness data as JSON string */
  data: string;
  /** When this data was cached (ISO 8601) */
  cached_at: DateTimeString;
  /** When this cache entry expires (ISO 8601) */
  expires_at: DateTimeString;
}

/**
 * Cached activity data with metadata
 */
export interface CachedActivity {
  /** Unique identifier from Oura API */
  id: string;
  /** Date of the activity data (YYYY-MM-DD) */
  day: DateString;
  /** Full activity data as JSON string */
  data: string;
  /** When this data was cached (ISO 8601) */
  cached_at: DateTimeString;
  /** When this cache entry expires (ISO 8601) */
  expires_at: DateTimeString;
}

/**
 * Cached heart rate data with metadata
 */
export interface CachedHeartRate {
  /** Auto-incrementing ID for SQLite */
  id?: number;
  /** Timestamp of the measurement (ISO 8601) */
  timestamp: DateTimeString;
  /** Heart rate in beats per minute */
  bpm: number;
  /** Source of the measurement */
  source: string;
  /** Date for easier querying (YYYY-MM-DD) */
  day: DateString;
  /** When this data was cached (ISO 8601) */
  cached_at: DateTimeString;
  /** When this cache entry expires (ISO 8601) */
  expires_at: DateTimeString;
}

/**
 * Cached API tokens
 */
export interface CachedToken {
  /** Token type identifier (always 'oura_oauth' for now) */
  token_type: string;
  /** Access token for API calls */
  access_token: string;
  /** Refresh token for getting new access tokens */
  refresh_token: string | null;
  /** When the access token expires (ISO 8601) */
  expires_at: DateTimeString;
  /** When this token was last updated (ISO 8601) */
  updated_at: DateTimeString;
}

/**
 * Cache metadata for tracking sync status
 */
export interface CacheMeta {
  /** Metadata key */
  key: string;
  /** Metadata value (stored as JSON string if needed) */
  value: string;
  /** When this metadata was last updated (ISO 8601) */
  updated_at: DateTimeString;
}

// =============================================================================
// TABLE CREATION SQL
// =============================================================================

/**
 * SQL statement to create the sleep_data table
 */
export const CREATE_SLEEP_DATA_TABLE = `
  CREATE TABLE IF NOT EXISTS sleep_data (
    id TEXT PRIMARY KEY,
    day TEXT NOT NULL,
    data TEXT NOT NULL,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
  )
`;

/**
 * SQL statement to create index on sleep_data.day for fast date queries
 */
export const CREATE_SLEEP_DATA_DAY_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_sleep_data_day ON sleep_data(day)
`;

/**
 * SQL statement to create index on sleep_data.expires_at for cache cleanup
 */
export const CREATE_SLEEP_DATA_EXPIRES_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_sleep_data_expires ON sleep_data(expires_at)
`;

/**
 * SQL statement to create the readiness_data table
 */
export const CREATE_READINESS_DATA_TABLE = `
  CREATE TABLE IF NOT EXISTS readiness_data (
    id TEXT PRIMARY KEY,
    day TEXT NOT NULL,
    data TEXT NOT NULL,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
  )
`;

/**
 * SQL statement to create index on readiness_data.day for fast date queries
 */
export const CREATE_READINESS_DATA_DAY_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_readiness_data_day ON readiness_data(day)
`;

/**
 * SQL statement to create index on readiness_data.expires_at for cache cleanup
 */
export const CREATE_READINESS_DATA_EXPIRES_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_readiness_data_expires ON readiness_data(expires_at)
`;

/**
 * SQL statement to create the activity_data table
 */
export const CREATE_ACTIVITY_DATA_TABLE = `
  CREATE TABLE IF NOT EXISTS activity_data (
    id TEXT PRIMARY KEY,
    day TEXT NOT NULL,
    data TEXT NOT NULL,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
  )
`;

/**
 * SQL statement to create index on activity_data.day for fast date queries
 */
export const CREATE_ACTIVITY_DATA_DAY_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_activity_data_day ON activity_data(day)
`;

/**
 * SQL statement to create index on activity_data.expires_at for cache cleanup
 */
export const CREATE_ACTIVITY_DATA_EXPIRES_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_activity_data_expires ON activity_data(expires_at)
`;

/**
 * SQL statement to create the heart_rate_data table
 */
export const CREATE_HEART_RATE_DATA_TABLE = `
  CREATE TABLE IF NOT EXISTS heart_rate_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    bpm INTEGER NOT NULL,
    source TEXT NOT NULL,
    day TEXT NOT NULL,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
  )
`;

/**
 * SQL statement to create index on heart_rate_data.day for fast date queries
 */
export const CREATE_HEART_RATE_DATA_DAY_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_heart_rate_data_day ON heart_rate_data(day)
`;

/**
 * SQL statement to create index on heart_rate_data.timestamp for time-based queries
 */
export const CREATE_HEART_RATE_DATA_TIMESTAMP_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_heart_rate_data_timestamp ON heart_rate_data(timestamp)
`;

/**
 * SQL statement to create index on heart_rate_data.expires_at for cache cleanup
 */
export const CREATE_HEART_RATE_DATA_EXPIRES_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_heart_rate_data_expires ON heart_rate_data(expires_at)
`;

/**
 * SQL statement to create the api_tokens table
 */
export const CREATE_API_TOKENS_TABLE = `
  CREATE TABLE IF NOT EXISTS api_tokens (
    token_type TEXT PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )
`;

/**
 * SQL statement to create the cache_meta table
 */
export const CREATE_CACHE_META_TABLE = `
  CREATE TABLE IF NOT EXISTS cache_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )
`;

// =============================================================================
// SCHEMA INITIALIZATION
// =============================================================================

/**
 * Initialize all database tables and indexes
 * This is idempotent - safe to call multiple times
 *
 * @param db - better-sqlite3 database instance
 */
export function initializeSchema(db: Database.Database): void {
  // Create tables
  db.exec(CREATE_SLEEP_DATA_TABLE);
  db.exec(CREATE_READINESS_DATA_TABLE);
  db.exec(CREATE_ACTIVITY_DATA_TABLE);
  db.exec(CREATE_HEART_RATE_DATA_TABLE);
  db.exec(CREATE_API_TOKENS_TABLE);
  db.exec(CREATE_CACHE_META_TABLE);

  // Create indexes for sleep_data
  db.exec(CREATE_SLEEP_DATA_DAY_INDEX);
  db.exec(CREATE_SLEEP_DATA_EXPIRES_INDEX);

  // Create indexes for readiness_data
  db.exec(CREATE_READINESS_DATA_DAY_INDEX);
  db.exec(CREATE_READINESS_DATA_EXPIRES_INDEX);

  // Create indexes for activity_data
  db.exec(CREATE_ACTIVITY_DATA_DAY_INDEX);
  db.exec(CREATE_ACTIVITY_DATA_EXPIRES_INDEX);

  // Create indexes for heart_rate_data
  db.exec(CREATE_HEART_RATE_DATA_DAY_INDEX);
  db.exec(CREATE_HEART_RATE_DATA_TIMESTAMP_INDEX);
  db.exec(CREATE_HEART_RATE_DATA_EXPIRES_INDEX);
}

/**
 * Get current schema version from cache_meta
 *
 * @param db - better-sqlite3 database instance
 * @returns Current schema version number
 */
export function getSchemaVersion(db: Database.Database): number {
  const stmt = db.prepare("SELECT value FROM cache_meta WHERE key = ?");
  const row = stmt.get("schema_version") as CacheMeta | undefined;
  return row ? parseInt(row.value, 10) : 0;
}

/**
 * Set schema version in cache_meta
 *
 * @param db - better-sqlite3 database instance
 * @param version - Schema version number to set
 */
export function setSchemaVersion(db: Database.Database, version: number): void {
  const now = new Date().toISOString();
  const stmt = db.prepare(`
    INSERT OR REPLACE INTO cache_meta (key, value, updated_at)
    VALUES (?, ?, ?)
  `);
  stmt.run("schema_version", version.toString(), now);
}

/**
 * Current schema version
 * Increment this when making schema changes
 */
export const CURRENT_SCHEMA_VERSION = 1;

/**
 * Run database migrations if needed
 *
 * @param db - better-sqlite3 database instance
 */
export function runMigrations(db: Database.Database): void {
  const currentVersion = getSchemaVersion(db);

  if (currentVersion < CURRENT_SCHEMA_VERSION) {
    // Initialize schema if version 0 (new database)
    if (currentVersion === 0) {
      initializeSchema(db);
      setSchemaVersion(db, CURRENT_SCHEMA_VERSION);
    }

    // Future migrations would go here
    // if (currentVersion < 2) {
    //   // Migration for version 2
    // }
  }
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Calculate expiration time based on TTL
 *
 * @param ttlHours - Time to live in hours (default: 1 hour)
 * @returns ISO 8601 datetime string for expiration
 */
export function calculateExpiresAt(ttlHours: number = 1): DateTimeString {
  const expiresAt = new Date();
  expiresAt.setHours(expiresAt.getHours() + ttlHours);
  return expiresAt.toISOString();
}

/**
 * Check if a cache entry is expired
 *
 * @param expiresAt - ISO 8601 datetime string
 * @returns true if expired, false otherwise
 */
export function isExpired(expiresAt: DateTimeString): boolean {
  return new Date(expiresAt) < new Date();
}

/**
 * Clean up expired cache entries from all tables
 *
 * @param db - better-sqlite3 database instance
 * @returns Number of deleted rows across all tables
 */
export function cleanupExpiredCache(db: Database.Database): number {
  const now = new Date().toISOString();
  let totalDeleted = 0;

  const tables = [
    "sleep_data",
    "readiness_data",
    "activity_data",
    "heart_rate_data",
  ];

  for (const table of tables) {
    const stmt = db.prepare(`DELETE FROM ${table} WHERE expires_at < ?`);
    const result = stmt.run(now);
    totalDeleted += result.changes;
  }

  return totalDeleted;
}
