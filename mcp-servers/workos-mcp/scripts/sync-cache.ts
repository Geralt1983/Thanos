#!/usr/bin/env npx tsx
/**
 * Standalone cache sync script for launchd scheduling
 *
 * Usage:
 *   npx tsx scripts/sync-cache.ts
 *
 * Environment:
 *   WORKOS_DATABASE_URL or DATABASE_URL - Neon connection string
 *
 * Schedule with launchd:
 *   ~/Library/LaunchAgents/com.workos.cache-sync.plist
 */

import { initCache, closeCache, getCacheStats } from "../src/cache/cache.js";
import { syncAll } from "../src/cache/sync.js";

async function main() {
  const startTime = Date.now();
  console.log(`[${new Date().toISOString()}] Starting WorkOS cache sync...`);

  try {
    // Initialize cache
    initCache();

    // Get pre-sync stats
    const preStats = getCacheStats();
    console.log(`[Pre-sync] Tasks: ${preStats.taskCount}, Clients: ${preStats.clientCount}, Last sync: ${preStats.lastSyncAt || "never"}`);

    // Run full sync
    const result = await syncAll();

    // Get post-sync stats
    const postStats = getCacheStats();
    const duration = Date.now() - startTime;

    console.log(`[Sync complete] ${duration}ms`);
    console.log(`  Clients: ${result.clients}`);
    console.log(`  Tasks: ${result.tasks}`);
    console.log(`  Daily Goals: ${result.dailyGoals}`);
    console.log(`  Habits: ${result.habits}`);
    console.log(`  Synced at: ${result.syncedAt}`);

    // Close cache
    closeCache();

    process.exit(0);
  } catch (error) {
    console.error(`[ERROR] Cache sync failed:`, error);
    closeCache();
    process.exit(1);
  }
}

main();
