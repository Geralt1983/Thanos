// =============================================================================
// OURA MCP CACHE SYNC
// Background sync process for keeping cache fresh
// Automatically syncs data on startup if stale, with manual sync support
// =============================================================================

import { getAPIClient, OuraAPIClient } from "../api/client.js";
import {
  getCachedSleep,
  getCachedReadiness,
  getCachedActivity,
  setCachedSleep,
  setCachedReadiness,
  setCachedActivity,
  getCacheMeta,
  setCacheMeta,
  getLastSyncTime,
  setLastSyncTime,
} from "./operations.js";
import type { DateString } from "../api/types.js";

// =============================================================================
// CONFIGURATION
// =============================================================================

/**
 * Default sync interval in hours
 * Data older than this will trigger a sync on startup
 */
const DEFAULT_SYNC_INTERVAL_HOURS = 1;

/**
 * Number of days of historical data to sync
 */
const SYNC_HISTORY_DAYS = 7;

/**
 * Debug logging enabled via environment variable
 */
const DEBUG = process.env.DEBUG_SYNC === "true";

// =============================================================================
// TYPES
// =============================================================================

export interface SyncStatus {
  lastSyncTime: Date | null;
  nextSyncDue: Date | null;
  isStale: boolean;
  syncInProgress: boolean;
  lastSyncResult?: SyncResult;
}

export interface SyncResult {
  success: boolean;
  timestamp: string;
  sleepRecordsSynced: number;
  readinessRecordsSynced: number;
  activityRecordsSynced: number;
  errors: string[];
}

// =============================================================================
// CACHE SYNC CLASS
// =============================================================================

/**
 * Manages background synchronization of Oura health data
 * Implements automatic sync on startup if stale, and manual sync commands
 */
export class CacheSync {
  private apiClient: OuraAPIClient;
  private syncInProgress: boolean = false;
  private lastSyncResult: SyncResult | null = null;

  constructor(apiClient?: OuraAPIClient) {
    this.apiClient = apiClient || getAPIClient();
  }

  /**
   * Initialize sync - automatically syncs if data is stale
   * Call this on MCP server startup
   */
  async initializeSync(): Promise<void> {
    if (DEBUG) {
      console.log("[Sync] Initializing cache sync...");
    }

    const status = this.getSyncStatus();

    if (status.isStale) {
      if (DEBUG) {
        console.log(
          `[Sync] Cache is stale (last sync: ${status.lastSyncTime?.toISOString() || "never"}), starting automatic sync...`
        );
      }
      await this.syncNow();
    } else {
      if (DEBUG) {
        console.log(
          `[Sync] Cache is fresh (last sync: ${status.lastSyncTime?.toISOString()}), no sync needed.`
        );
      }
    }
  }

  /**
   * Get current sync status
   * Includes staleness check and last sync information
   */
  getSyncStatus(): SyncStatus {
    const lastSyncTime = getLastSyncTime();
    const isStale = this.isCacheStale(lastSyncTime);

    let nextSyncDue: Date | null = null;
    if (lastSyncTime) {
      nextSyncDue = new Date(
        lastSyncTime.getTime() + DEFAULT_SYNC_INTERVAL_HOURS * 60 * 60 * 1000
      );
    }

    return {
      lastSyncTime,
      nextSyncDue,
      isStale,
      syncInProgress: this.syncInProgress,
      lastSyncResult: this.lastSyncResult || undefined,
    };
  }

  /**
   * Check if cache is stale and needs syncing
   */
  private isCacheStale(lastSyncTime: Date | null): boolean {
    if (!lastSyncTime) {
      return true; // Never synced before
    }

    const now = new Date();
    const hoursSinceSync =
      (now.getTime() - lastSyncTime.getTime()) / (1000 * 60 * 60);

    return hoursSinceSync >= DEFAULT_SYNC_INTERVAL_HOURS;
  }

  /**
   * Manual sync command - sync all health data now
   * Can be called via MCP tool or internal trigger
   */
  async syncNow(): Promise<SyncResult> {
    if (this.syncInProgress) {
      if (DEBUG) {
        console.log("[Sync] Sync already in progress, skipping...");
      }
      return {
        success: false,
        timestamp: new Date().toISOString(),
        sleepRecordsSynced: 0,
        readinessRecordsSynced: 0,
        activityRecordsSynced: 0,
        errors: ["Sync already in progress"],
      };
    }

    this.syncInProgress = true;
    const startTime = new Date();
    const errors: string[] = [];
    let sleepCount = 0;
    let readinessCount = 0;
    let activityCount = 0;

    if (DEBUG) {
      console.log(`[Sync] Starting sync at ${startTime.toISOString()}`);
    }

    try {
      // Calculate date range (last N days)
      const endDate = this.formatDate(new Date());
      const startDate = this.formatDate(
        new Date(Date.now() - SYNC_HISTORY_DAYS * 24 * 60 * 60 * 1000)
      );

      if (DEBUG) {
        console.log(`[Sync] Syncing data from ${startDate} to ${endDate}`);
      }

      // Sync sleep data
      try {
        const sleepData = await this.apiClient.getDailySleep({
          startDate: startDate,
          endDate: endDate,
        });

        for (const record of sleepData) {
          setCachedSleep(record);
          sleepCount++;
        }

        if (DEBUG) {
          console.log(`[Sync] Synced ${sleepCount} sleep records`);
        }
      } catch (error) {
        const errorMsg = `Failed to sync sleep data: ${error instanceof Error ? error.message : String(error)}`;
        errors.push(errorMsg);
        if (DEBUG) {
          console.error(`[Sync] ${errorMsg}`);
        }
      }

      // Sync readiness data
      try {
        const readinessData = await this.apiClient.getDailyReadiness({
          startDate: startDate,
          endDate: endDate,
        });

        for (const record of readinessData) {
          setCachedReadiness(record);
          readinessCount++;
        }

        if (DEBUG) {
          console.log(`[Sync] Synced ${readinessCount} readiness records`);
        }
      } catch (error) {
        const errorMsg = `Failed to sync readiness data: ${error instanceof Error ? error.message : String(error)}`;
        errors.push(errorMsg);
        if (DEBUG) {
          console.error(`[Sync] ${errorMsg}`);
        }
      }

      // Sync activity data
      try {
        const activityData = await this.apiClient.getDailyActivity({
          startDate: startDate,
          endDate: endDate,
        });

        for (const record of activityData) {
          setCachedActivity(record);
          activityCount++;
        }

        if (DEBUG) {
          console.log(`[Sync] Synced ${activityCount} activity records`);
        }
      } catch (error) {
        const errorMsg = `Failed to sync activity data: ${error instanceof Error ? error.message : String(error)}`;
        errors.push(errorMsg);
        if (DEBUG) {
          console.error(`[Sync] ${errorMsg}`);
        }
      }

      // Update last sync time
      const syncTime = new Date();
      setLastSyncTime(syncTime);

      const result: SyncResult = {
        success: errors.length === 0,
        timestamp: syncTime.toISOString(),
        sleepRecordsSynced: sleepCount,
        readinessRecordsSynced: readinessCount,
        activityRecordsSynced: activityCount,
        errors,
      };

      this.lastSyncResult = result;

      if (DEBUG) {
        console.log(
          `[Sync] Sync completed in ${Date.now() - startTime.getTime()}ms`
        );
        console.log(
          `[Sync] Results: ${sleepCount} sleep, ${readinessCount} readiness, ${activityCount} activity`
        );
        if (errors.length > 0) {
          console.log(`[Sync] Errors encountered: ${errors.length}`);
        }
      }

      return result;
    } catch (error) {
      const errorMsg = `Sync failed: ${error instanceof Error ? error.message : String(error)}`;
      errors.push(errorMsg);

      if (DEBUG) {
        console.error(`[Sync] ${errorMsg}`);
      }

      const result: SyncResult = {
        success: false,
        timestamp: new Date().toISOString(),
        sleepRecordsSynced: sleepCount,
        readinessRecordsSynced: readinessCount,
        activityRecordsSynced: activityCount,
        errors,
      };

      this.lastSyncResult = result;
      return result;
    } finally {
      this.syncInProgress = false;
    }
  }

  /**
   * Format date as YYYY-MM-DD for Oura API
   */
  private formatDate(date: Date): DateString {
    return date.toISOString().split("T")[0] as DateString;
  }
}

// =============================================================================
// SINGLETON INSTANCE
// =============================================================================

let cacheSyncInstance: CacheSync | null = null;

/**
 * Get or create singleton CacheSync instance
 */
export function getCacheSync(apiClient?: OuraAPIClient): CacheSync {
  if (!cacheSyncInstance) {
    cacheSyncInstance = new CacheSync(apiClient);
  }
  return cacheSyncInstance;
}

/**
 * Create a new CacheSync instance (non-singleton, for testing)
 */
export function createCacheSync(apiClient?: OuraAPIClient): CacheSync {
  return new CacheSync(apiClient);
}

/**
 * Reset singleton instance (useful for testing)
 */
export function resetCacheSync(): void {
  cacheSyncInstance = null;
}
