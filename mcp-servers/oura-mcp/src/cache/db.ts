// =============================================================================
// OURA MCP DATABASE INITIALIZATION
// SQLite database setup for caching Oura Ring API data locally
// Uses better-sqlite3 for fast, synchronous database operations
// =============================================================================

import Database from "better-sqlite3";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";
import { initializeSchema, runMigrations } from "./schema.js";

// =============================================================================
// DATABASE CONFIGURATION
// =============================================================================

/**
 * Cache directory path - can be overridden via environment variable
 */
const CACHE_DIR = process.env.OURA_CACHE_DIR || path.join(os.homedir(), ".oura-cache");

/**
 * Database file path
 */
const DB_PATH = path.join(CACHE_DIR, "oura-health.db");

/**
 * Singleton database instance
 */
let dbInstance: Database.Database | null = null;

// =============================================================================
// DATABASE INITIALIZATION
// =============================================================================

/**
 * Initialize the SQLite cache database
 * Creates the cache directory and database file if they don't exist
 * This function is idempotent - safe to call multiple times
 *
 * @returns better-sqlite3 database instance
 */
export function initDb(): Database.Database {
  // Return existing instance if already initialized
  if (dbInstance) {
    return dbInstance;
  }

  // Ensure cache directory exists
  if (!fs.existsSync(CACHE_DIR)) {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
  }

  // Create SQLite database
  dbInstance = new Database(DB_PATH);

  // Enable WAL mode for better concurrent access
  // WAL (Write-Ahead Logging) allows multiple readers while a write is in progress
  dbInstance.pragma("journal_mode = WAL");

  // Run migrations to set up schema
  runMigrations(dbInstance);

  return dbInstance;
}

/**
 * Get the database instance, initializing if needed
 * This is the primary method to use for accessing the database
 *
 * @returns better-sqlite3 database instance
 */
export function getDb(): Database.Database {
  if (!dbInstance) {
    return initDb();
  }
  return dbInstance;
}

/**
 * Close the database connection
 * Should be called when shutting down the MCP server
 */
export function closeDb(): void {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}

/**
 * Get the database file path
 * Useful for debugging and testing
 *
 * @returns Absolute path to the SQLite database file
 */
export function getDbPath(): string {
  return DB_PATH;
}

/**
 * Get the cache directory path
 * Useful for debugging and testing
 *
 * @returns Absolute path to the cache directory
 */
export function getCacheDir(): string {
  return CACHE_DIR;
}

/**
 * Check if the database exists
 *
 * @returns true if the database file exists, false otherwise
 */
export function dbExists(): boolean {
  return fs.existsSync(DB_PATH);
}

/**
 * Reset the database by deleting and reinitializing it
 * WARNING: This will delete all cached data!
 * Use with caution - primarily for testing and development
 */
export function resetDb(): void {
  // Close existing connection
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }

  // Delete database file if it exists
  if (fs.existsSync(DB_PATH)) {
    fs.unlinkSync(DB_PATH);
  }

  // Delete WAL and SHM files if they exist
  const walPath = `${DB_PATH}-wal`;
  const shmPath = `${DB_PATH}-shm`;
  if (fs.existsSync(walPath)) {
    fs.unlinkSync(walPath);
  }
  if (fs.existsSync(shmPath)) {
    fs.unlinkSync(shmPath);
  }

  // Reinitialize
  initDb();
}

/**
 * Get database statistics for monitoring and debugging
 *
 * @returns Object containing database stats (size, page count, etc.)
 */
export function getDbStats(): {
  path: string;
  exists: boolean;
  size: number;
  pageCount: number;
  pageSize: number;
  walMode: boolean;
} {
  const exists = dbExists();
  const size = exists ? fs.statSync(DB_PATH).size : 0;

  if (!exists) {
    return {
      path: DB_PATH,
      exists: false,
      size: 0,
      pageCount: 0,
      pageSize: 0,
      walMode: false,
    };
  }

  const db = getDb();
  const pageCountResult = db.pragma("page_count", { simple: true }) as number;
  const pageSizeResult = db.pragma("page_size", { simple: true }) as number;
  const journalModeResult = db.pragma("journal_mode", { simple: true }) as string;

  return {
    path: DB_PATH,
    exists: true,
    size,
    pageCount: pageCountResult,
    pageSize: pageSizeResult,
    walMode: journalModeResult === "wal",
  };
}

// =============================================================================
// GRACEFUL SHUTDOWN
// =============================================================================

/**
 * Register graceful shutdown handlers
 * Ensures the database is properly closed when the process exits
 */
export function registerShutdownHandlers(): void {
  // Handle SIGINT (Ctrl+C)
  process.on("SIGINT", () => {
    closeDb();
    process.exit(0);
  });

  // Handle SIGTERM (process termination)
  process.on("SIGTERM", () => {
    closeDb();
    process.exit(0);
  });

  // Handle uncaught exceptions
  process.on("uncaughtException", (error) => {
    console.error("Uncaught exception:", error);
    closeDb();
    process.exit(1);
  });
}
