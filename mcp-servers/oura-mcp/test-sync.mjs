#!/usr/bin/env node
/**
 * Test script for cache sync functionality
 * Tests: CacheSync class, status tracking, sync logic
 */

import { getCacheSync, resetCacheSync } from "./dist/cache/sync.js";
import { getLastSyncTime, setLastSyncTime, getCacheMeta } from "./dist/cache/operations.js";
import { initDb, closeDb } from "./dist/cache/db.js";

console.log("=".repeat(80));
console.log("CACHE SYNC TEST SUITE");
console.log("=".repeat(80));

let testsPassed = 0;
let testsFailed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`✓ ${message}`);
    testsPassed++;
  } else {
    console.error(`✗ ${message}`);
    testsFailed++;
  }
}

function assertNotNull(value, message) {
  assert(value !== null && value !== undefined, message);
}

async function runTests() {
  try {
    // Initialize database
    console.log("\n--- Test 1: Database Initialization ---");
    initDb();
    assert(true, "Database initialized successfully");

    // Test 2: CacheSync singleton
    console.log("\n--- Test 2: CacheSync Singleton ---");
    resetCacheSync();
    const sync1 = getCacheSync();
    const sync2 = getCacheSync();
    assert(sync1 === sync2, "getCacheSync returns same instance");

    // Test 3: Initial sync status (never synced)
    console.log("\n--- Test 3: Initial Sync Status ---");
    const initialStatus = sync1.getSyncStatus();
    assert(initialStatus.lastSyncTime === null, "lastSyncTime is null initially");
    assert(initialStatus.isStale === true, "isStale is true when never synced");
    assert(initialStatus.syncInProgress === false, "syncInProgress is false initially");

    // Test 4: Manual last sync time update
    console.log("\n--- Test 4: Last Sync Time Tracking ---");
    const testTime = new Date();
    setLastSyncTime(testTime);
    const retrievedTime = getLastSyncTime();
    assertNotNull(retrievedTime, "getLastSyncTime returns value after set");
    assert(
      Math.abs(retrievedTime.getTime() - testTime.getTime()) < 1000,
      "Retrieved time matches set time (within 1 second)"
    );

    // Test 5: Sync status after manual update
    console.log("\n--- Test 5: Sync Status After Update ---");
    const updatedStatus = sync1.getSyncStatus();
    assertNotNull(updatedStatus.lastSyncTime, "lastSyncTime is set after update");
    assert(updatedStatus.isStale === false, "isStale is false after recent sync");
    assertNotNull(updatedStatus.nextSyncDue, "nextSyncDue is calculated");

    // Test 6: Stale detection (simulate old sync)
    console.log("\n--- Test 6: Stale Detection ---");
    const oldTime = new Date(Date.now() - 2 * 60 * 60 * 1000); // 2 hours ago
    setLastSyncTime(oldTime);
    const staleStatus = sync1.getSyncStatus();
    assert(staleStatus.isStale === true, "isStale is true for 2-hour-old sync");

    // Test 7: Sync status structure
    console.log("\n--- Test 7: Sync Status Structure ---");
    assert("lastSyncTime" in staleStatus, "Status includes lastSyncTime");
    assert("nextSyncDue" in staleStatus, "Status includes nextSyncDue");
    assert("isStale" in staleStatus, "Status includes isStale");
    assert("syncInProgress" in staleStatus, "Status includes syncInProgress");

    // Test 8: Reset functionality
    console.log("\n--- Test 8: Reset Functionality ---");
    resetCacheSync();
    const newSync = getCacheSync();
    assert(newSync !== sync1, "resetCacheSync creates new instance");

    console.log("\n" + "=".repeat(80));
    console.log("TEST SUMMARY");
    console.log("=".repeat(80));
    console.log(`Total tests: ${testsPassed + testsFailed}`);
    console.log(`✓ Passed: ${testsPassed}`);
    console.log(`✗ Failed: ${testsFailed}`);

    if (testsFailed === 0) {
      console.log("\n🎉 All tests passed!");
    } else {
      console.log(`\n⚠️  ${testsFailed} test(s) failed`);
      process.exit(1);
    }
  } catch (error) {
    console.error("\n❌ Test suite failed with error:");
    console.error(error);
    process.exit(1);
  } finally {
    // Cleanup
    closeDb();
  }
}

// Run tests
runTests().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
