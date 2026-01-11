#!/usr/bin/env node

/**
 * Test script for cache CRUD operations
 * Tests all cache operations for sleep, readiness, activity, and heart rate data
 */

import { resetDb, getDb } from "./dist/cache/db.js";
import {
  getCachedSleep,
  setCachedSleep,
  deleteCachedSleep,
  getCachedSleepRange,
  getCachedReadiness,
  setCachedReadiness,
  deleteCachedReadiness,
  getCachedReadinessRange,
  getCachedActivity,
  setCachedActivity,
  deleteCachedActivity,
  getCachedActivityRange,
  getCachedHeartRate,
  setCachedHeartRate,
  deleteCachedHeartRate,
  getCachedHeartRateRange,
  getCacheMeta,
  setCacheMeta,
  getLastSyncTime,
  setLastSyncTime,
  clearHealthCache,
  clearExpiredCache,
  invalidateCacheForDate,
  getCacheStats,
  getCacheCoverageForDate,
} from "./dist/cache/operations.js";
import { calculateExpiresAt } from "./dist/cache/schema.js";

// Test data
const testDate = "2024-01-15";
const testDate2 = "2024-01-16";
const testDate3 = "2024-01-17";

const testSleepData = {
  id: "sleep-123",
  day: testDate,
  score: 85,
  contributors: {
    deep_sleep: 90,
    efficiency: 85,
    latency: 80,
    rem_sleep: 85,
    restfulness: 88,
    timing: 82,
    total_sleep: 87,
  },
  bedtime_start: "2024-01-14T22:30:00Z",
  bedtime_end: "2024-01-15T07:00:00Z",
  average_breath: 15,
  average_heart_rate: 55,
  average_hrv: 45,
  awake_time: 1800,
  deep_sleep_duration: 5400,
  efficiency: 92,
  latency: 600,
  light_sleep_duration: 14400,
  low_battery_alert: false,
  lowest_heart_rate: 48,
  movement_30_sec: "<base64-data>",
  period: 0,
  readiness_score_delta: 5,
  rem_sleep_duration: 7200,
  restless_periods: 3,
  sleep_phase_5_min: "<base64-data>",
  sleep_score_delta: 3,
  time_in_bed: 30600,
  total_sleep_duration: 27000,
  type: "long_sleep",
};

const testReadinessData = {
  id: "readiness-123",
  day: testDate,
  score: 78,
  contributors: {
    activity_balance: 80,
    body_temperature: 75,
    hrv_balance: 82,
    previous_day_activity: 85,
    previous_night: 88,
    recovery_index: 77,
    resting_heart_rate: 79,
    sleep_balance: 81,
  },
  temperature_deviation: -0.2,
  temperature_trend_deviation: 0.1,
};

const testActivityData = {
  id: "activity-123",
  day: testDate,
  score: 82,
  active_calories: 450,
  average_met_minutes: 1.5,
  contributors: {
    meet_daily_targets: 85,
    move_every_hour: 80,
    recovery_time: 88,
    stay_active: 83,
    training_frequency: 78,
    training_volume: 81,
  },
  equivalent_walking_distance: 8500,
  high_activity_met_minutes: 120,
  high_activity_time: 3600,
  inactivity_alerts: 2,
  low_activity_met_minutes: 180,
  low_activity_time: 7200,
  medium_activity_met_minutes: 200,
  medium_activity_time: 10800,
  meters_to_target: 1500,
  non_wear_time: 600,
  resting_time: 18000,
  sedentary_met_minutes: 300,
  sedentary_time: 28800,
  steps: 8500,
  target_calories: 500,
  target_meters: 10000,
  total_calories: 2100,
  class: "medium",
};

const testHeartRateData = [
  { bpm: 55, source: "sleep", timestamp: "2024-01-15T00:00:00Z" },
  { bpm: 58, source: "sleep", timestamp: "2024-01-15T01:00:00Z" },
  { bpm: 62, source: "activity", timestamp: "2024-01-15T10:00:00Z" },
  { bpm: 75, source: "activity", timestamp: "2024-01-15T15:00:00Z" },
];

// Helper to run tests
function runTest(name, fn) {
  try {
    fn();
    console.log(`✅ ${name}`);
  } catch (error) {
    console.error(`❌ ${name}`);
    console.error(`   Error: ${error.message}`);
    process.exit(1);
  }
}

// Reset database before tests
console.log("Resetting database...");
resetDb();

// =============================================================================
// SLEEP DATA TESTS
// =============================================================================

console.log("\n📊 Testing Sleep Data Operations:");

runTest("Set cached sleep data", () => {
  setCachedSleep(testSleepData);
  const cached = getCachedSleep(testDate);
  if (!cached || cached.id !== testSleepData.id) {
    throw new Error("Failed to set cached sleep data");
  }
  if (cached.score !== 85) {
    throw new Error("Sleep score not preserved");
  }
});

runTest("Get cached sleep data", () => {
  const cached = getCachedSleep(testDate);
  if (!cached) {
    throw new Error("Failed to get cached sleep data");
  }
  if (cached.contributors.deep_sleep !== 90) {
    throw new Error("Contributors not preserved");
  }
});

runTest("Get cached sleep range", () => {
  // Add more sleep data
  setCachedSleep({ ...testSleepData, id: "sleep-124", day: testDate2 });
  setCachedSleep({ ...testSleepData, id: "sleep-125", day: testDate3 });

  const range = getCachedSleepRange(testDate, testDate3);
  if (range.length !== 3) {
    throw new Error(`Expected 3 sleep records, got ${range.length}`);
  }
});

runTest("Delete cached sleep data", () => {
  deleteCachedSleep(testDate);
  const cached = getCachedSleep(testDate);
  if (cached !== null) {
    throw new Error("Failed to delete cached sleep data");
  }
});

// =============================================================================
// READINESS DATA TESTS
// =============================================================================

console.log("\n💪 Testing Readiness Data Operations:");

runTest("Set cached readiness data", () => {
  setCachedReadiness(testReadinessData);
  const cached = getCachedReadiness(testDate);
  if (!cached || cached.id !== testReadinessData.id) {
    throw new Error("Failed to set cached readiness data");
  }
  if (cached.score !== 78) {
    throw new Error("Readiness score not preserved");
  }
});

runTest("Get cached readiness data", () => {
  const cached = getCachedReadiness(testDate);
  if (!cached) {
    throw new Error("Failed to get cached readiness data");
  }
  if (cached.contributors.activity_balance !== 80) {
    throw new Error("Contributors not preserved");
  }
});

runTest("Get cached readiness range", () => {
  // Add more readiness data
  setCachedReadiness({ ...testReadinessData, id: "readiness-124", day: testDate2 });
  setCachedReadiness({ ...testReadinessData, id: "readiness-125", day: testDate3 });

  const range = getCachedReadinessRange(testDate, testDate3);
  if (range.length !== 3) {
    throw new Error(`Expected 3 readiness records, got ${range.length}`);
  }
});

runTest("Delete cached readiness data", () => {
  deleteCachedReadiness(testDate);
  const cached = getCachedReadiness(testDate);
  if (cached !== null) {
    throw new Error("Failed to delete cached readiness data");
  }
});

// =============================================================================
// ACTIVITY DATA TESTS
// =============================================================================

console.log("\n🏃 Testing Activity Data Operations:");

runTest("Set cached activity data", () => {
  setCachedActivity(testActivityData);
  const cached = getCachedActivity(testDate);
  if (!cached || cached.id !== testActivityData.id) {
    throw new Error("Failed to set cached activity data");
  }
  if (cached.score !== 82) {
    throw new Error("Activity score not preserved");
  }
});

runTest("Get cached activity data", () => {
  const cached = getCachedActivity(testDate);
  if (!cached) {
    throw new Error("Failed to get cached activity data");
  }
  if (cached.steps !== 8500) {
    throw new Error("Steps not preserved");
  }
});

runTest("Get cached activity range", () => {
  // Add more activity data
  setCachedActivity({ ...testActivityData, id: "activity-124", day: testDate2 });
  setCachedActivity({ ...testActivityData, id: "activity-125", day: testDate3 });

  const range = getCachedActivityRange(testDate, testDate3);
  if (range.length !== 3) {
    throw new Error(`Expected 3 activity records, got ${range.length}`);
  }
});

runTest("Delete cached activity data", () => {
  deleteCachedActivity(testDate);
  const cached = getCachedActivity(testDate);
  if (cached !== null) {
    throw new Error("Failed to delete cached activity data");
  }
});

// =============================================================================
// HEART RATE DATA TESTS
// =============================================================================

console.log("\n❤️  Testing Heart Rate Data Operations:");

runTest("Set cached heart rate data", () => {
  setCachedHeartRate(testDate, testHeartRateData);
  const cached = getCachedHeartRate(testDate);
  if (cached.length !== 4) {
    throw new Error(`Expected 4 heart rate points, got ${cached.length}`);
  }
});

runTest("Get cached heart rate data", () => {
  const cached = getCachedHeartRate(testDate);
  if (!cached || cached.length === 0) {
    throw new Error("Failed to get cached heart rate data");
  }
  if (cached[0].bpm !== 55) {
    throw new Error("Heart rate BPM not preserved");
  }
  if (cached[0].source !== "sleep") {
    throw new Error("Heart rate source not preserved");
  }
});

runTest("Get cached heart rate range", () => {
  // Add heart rate data for more dates
  setCachedHeartRate(testDate2, testHeartRateData);
  setCachedHeartRate(testDate3, testHeartRateData);

  const range = getCachedHeartRateRange(testDate, testDate3);
  if (range.length !== 12) {
    throw new Error(`Expected 12 heart rate points, got ${range.length}`);
  }
});

runTest("Delete cached heart rate data", () => {
  deleteCachedHeartRate(testDate);
  const cached = getCachedHeartRate(testDate);
  if (cached.length !== 0) {
    throw new Error("Failed to delete cached heart rate data");
  }
});

// =============================================================================
// CACHE METADATA TESTS
// =============================================================================

console.log("\n🔧 Testing Cache Metadata Operations:");

runTest("Set and get cache metadata", () => {
  setCacheMeta("test_key", "test_value");
  const value = getCacheMeta("test_key");
  if (value !== "test_value") {
    throw new Error("Failed to set/get cache metadata");
  }
});

runTest("Get non-existent metadata", () => {
  const value = getCacheMeta("non_existent_key");
  if (value !== null) {
    throw new Error("Should return null for non-existent key");
  }
});

runTest("Set and get last sync time", () => {
  const now = new Date();
  setLastSyncTime(now);
  const syncTime = getLastSyncTime();
  if (!syncTime || Math.abs(syncTime.getTime() - now.getTime()) > 1000) {
    throw new Error("Failed to set/get last sync time");
  }
});

// =============================================================================
// CACHE INVALIDATION TESTS
// =============================================================================

console.log("\n🗑️  Testing Cache Invalidation:");

// Repopulate cache with test data
setCachedSleep({ ...testSleepData, day: testDate });
setCachedReadiness({ ...testReadinessData, day: testDate });
setCachedActivity({ ...testActivityData, day: testDate });
setCachedHeartRate(testDate, testHeartRateData);

runTest("Invalidate cache for specific date", () => {
  invalidateCacheForDate(testDate);
  const sleep = getCachedSleep(testDate);
  const readiness = getCachedReadiness(testDate);
  const activity = getCachedActivity(testDate);
  const heartRate = getCachedHeartRate(testDate);

  if (sleep !== null || readiness !== null || activity !== null || heartRate.length !== 0) {
    throw new Error("Failed to invalidate cache for date");
  }
});

// Repopulate for clear test
setCachedSleep({ ...testSleepData, day: testDate });
setCachedReadiness({ ...testReadinessData, day: testDate });
setCachedActivity({ ...testActivityData, day: testDate });
setCachedHeartRate(testDate, testHeartRateData);

runTest("Clear health cache", () => {
  clearHealthCache();
  const stats = getCacheStats();
  if (stats.sleepCount !== 0 || stats.readinessCount !== 0 || stats.activityCount !== 0) {
    throw new Error("Failed to clear health cache");
  }
});

// =============================================================================
// CACHE STATISTICS TESTS
// =============================================================================

console.log("\n📈 Testing Cache Statistics:");

// Repopulate cache for stats tests
setCachedSleep({ ...testSleepData, day: testDate });
setCachedReadiness({ ...testReadinessData, day: testDate });
setCachedActivity({ ...testActivityData, day: testDate });
setCachedHeartRate(testDate, testHeartRateData);

runTest("Get cache stats", () => {
  const stats = getCacheStats();
  if (stats.sleepCount !== 1 || stats.readinessCount !== 1 || stats.activityCount !== 1) {
    throw new Error("Cache stats incorrect");
  }
  if (stats.heartRateCount !== 4) {
    throw new Error(`Expected 4 heart rate points in stats, got ${stats.heartRateCount}`);
  }
});

runTest("Get cache coverage for date", () => {
  const coverage = getCacheCoverageForDate(testDate);
  if (!coverage.hasSleep || !coverage.hasReadiness || !coverage.hasActivity || !coverage.hasHeartRate) {
    throw new Error("Cache coverage check failed");
  }

  const noCoverage = getCacheCoverageForDate("2099-12-31");
  if (noCoverage.hasSleep || noCoverage.hasReadiness || noCoverage.hasActivity || noCoverage.hasHeartRate) {
    throw new Error("Should report no coverage for date without data");
  }
});

// =============================================================================
// TTL AND EXPIRY TESTS
// =============================================================================

console.log("\n⏰ Testing TTL and Expiry:");

runTest("Cache entry expires after TTL", () => {
  // Clear and set with very short TTL (0 hours - should be expired immediately)
  clearHealthCache();

  // Manually insert expired data
  const db = getDb();
  const pastTime = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(); // 2 hours ago
  const stmt = db.prepare(`
    INSERT INTO sleep_data (id, day, data, cached_at, expires_at)
    VALUES (?, ?, ?, ?, ?)
  `);
  stmt.run("expired-sleep", testDate, JSON.stringify(testSleepData), pastTime, pastTime);

  // Should return null because expired
  const cached = getCachedSleep(testDate);
  if (cached !== null) {
    throw new Error("Expired cache entry was not filtered out");
  }
});

runTest("Clear expired cache", () => {
  // Add some fresh data
  setCachedSleep({ ...testSleepData, day: testDate2 });

  // Manually insert more expired data (without reading it first)
  const db = getDb();
  const pastTime = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(); // 2 hours ago
  const stmt = db.prepare(`
    INSERT INTO readiness_data (id, day, data, cached_at, expires_at)
    VALUES (?, ?, ?, ?, ?)
  `);
  stmt.run("expired-readiness", "2024-01-10", JSON.stringify(testReadinessData), pastTime, pastTime);

  // Clear expired entries
  const deleted = clearExpiredCache();
  if (deleted < 1) {
    throw new Error(`Should have deleted at least 1 expired entry, deleted ${deleted}`);
  }

  // Fresh data should still be there
  const fresh = getCachedSleep(testDate2);
  if (!fresh) {
    throw new Error("Fresh cache entry was incorrectly deleted");
  }
});

// =============================================================================
// SUMMARY
// =============================================================================

console.log("\n✅ All cache operation tests passed!");
console.log("\nFinal cache stats:");
const finalStats = getCacheStats();
console.log(`  Sleep records: ${finalStats.sleepCount}`);
console.log(`  Readiness records: ${finalStats.readinessCount}`);
console.log(`  Activity records: ${finalStats.activityCount}`);
console.log(`  Heart rate points: ${finalStats.heartRateCount}`);
console.log(`  Last sync: ${finalStats.lastSyncAt}`);
console.log(`  DB size: ${finalStats.dbSize} bytes`);

process.exit(0);
