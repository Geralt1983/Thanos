// =============================================================================
// OURA CACHE READER
// Helper module to read from Oura MCP cache database
// Provides read-only access to cached Oura health data
// =============================================================================

import Database from "better-sqlite3";
import * as path from "path";
import * as os from "os";
import * as fs from "fs";

// =============================================================================
// TYPES
// =============================================================================

/**
 * Oura readiness data structure
 */
export interface OuraReadiness {
  score: number | null;
  day: string;
  contributors: {
    activity_balance: number | null;
    body_temperature: number | null;
    hrv_balance: number | null;
    previous_day_activity: number | null;
    previous_night: number | null;
    recovery_index: number | null;
    resting_heart_rate: number | null;
    sleep_balance: number | null;
  };
}

/**
 * Oura sleep data structure
 */
export interface OuraSleep {
  score: number | null;
  day: string;
  total_sleep_duration: number | null;
  efficiency: number | null;
  rem_sleep_duration: number | null;
  deep_sleep_duration: number | null;
  light_sleep_duration: number | null;
}

// =============================================================================
// CONFIGURATION
// =============================================================================

/**
 * Oura cache directory - matches oura-mcp configuration
 */
const OURA_CACHE_DIR =
  process.env.OURA_CACHE_DIR || path.join(os.homedir(), ".oura-cache");

/**
 * Oura database path
 */
const OURA_DB_PATH = path.join(OURA_CACHE_DIR, "oura-health.db");

// =============================================================================
// DATABASE ACCESS
// =============================================================================

/**
 * Check if Oura cache database exists
 */
export function ouraDbExists(): boolean {
  return fs.existsSync(OURA_DB_PATH);
}

/**
 * Get Oura database instance (read-only)
 * Returns null if database doesn't exist
 */
function getOuraDb(): Database.Database | null {
  if (!ouraDbExists()) {
    return null;
  }

  try {
    // Open in read-only mode to avoid locking issues with oura-mcp
    const db = new Database(OURA_DB_PATH, { readonly: true });
    return db;
  } catch (error) {
    // If we can't open the database, return null
    return null;
  }
}

// =============================================================================
// DATA RETRIEVAL
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
 * Check if a cache entry is expired
 */
function isExpired(expiresAt: string): boolean {
  return new Date(expiresAt) < new Date();
}

/**
 * Get cached readiness data for a specific date
 * Returns null if not found, expired, or database unavailable
 *
 * @param date - Date in YYYY-MM-DD format (defaults to today)
 * @returns OuraReadiness or null
 */
export function getCachedReadiness(date?: string): OuraReadiness | null {
  const db = getOuraDb();
  if (!db) return null;

  try {
    const targetDate = date || getTodayDate();

    const stmt = db.prepare<[string]>(`
      SELECT * FROM readiness_data WHERE day = ?
    `);
    const row = stmt.get(targetDate) as
      | { data: string; expires_at: string }
      | undefined;

    if (!row) {
      db.close();
      return null;
    }

    // Check if expired
    if (isExpired(row.expires_at)) {
      db.close();
      return null;
    }

    // Parse and return the data
    const data = JSON.parse(row.data) as OuraReadiness;
    db.close();
    return data;
  } catch (error) {
    // Silently fail and return null
    try {
      db.close();
    } catch {
      // Ignore close errors
    }
    return null;
  }
}

/**
 * Get cached sleep data for a specific date
 * Returns null if not found, expired, or database unavailable
 *
 * @param date - Date in YYYY-MM-DD format (defaults to today)
 * @returns OuraSleep or null
 */
export function getCachedSleep(date?: string): OuraSleep | null {
  const db = getOuraDb();
  if (!db) return null;

  try {
    const targetDate = date || getTodayDate();

    const stmt = db.prepare<[string]>(`
      SELECT * FROM sleep_data WHERE day = ?
    `);
    const row = stmt.get(targetDate) as
      | { data: string; expires_at: string }
      | undefined;

    if (!row) {
      db.close();
      return null;
    }

    // Check if expired
    if (isExpired(row.expires_at)) {
      db.close();
      return null;
    }

    // Parse and return the data
    const data = JSON.parse(row.data) as OuraSleep;
    db.close();
    return data;
  } catch (error) {
    // Silently fail and return null
    try {
      db.close();
    } catch {
      // Ignore close errors
    }
    return null;
  }
}

/**
 * Get today's energy data from Oura cache
 * Returns both readiness and sleep scores for the current day
 *
 * @returns Object with readiness and sleep scores, or nulls if unavailable
 */
export function getTodayOuraData(): {
  readinessScore: number | null;
  sleepScore: number | null;
} {
  const readiness = getCachedReadiness();
  const sleep = getCachedSleep();

  return {
    readinessScore: readiness?.score ?? null,
    sleepScore: sleep?.score ?? null,
  };
}
