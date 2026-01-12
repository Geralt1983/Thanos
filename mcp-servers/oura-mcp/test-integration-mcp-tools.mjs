#!/usr/bin/env node

/**
 * INTEGRATION TESTS FOR OURA MCP SERVER
 * Tests end-to-end tool functionality including:
 * - Full MCP tool execution flow
 * - Cache-first behavior
 * - API fallback when cache empty
 * - Error handling scenarios
 * - Multi-component integration
 */

import { handleGetTodayReadiness } from "./dist/tools/readiness.js";
import { handleGetSleepSummary } from "./dist/tools/sleep.js";
import { handleGetWeeklyTrends } from "./dist/tools/trends.js";
import { handleHealthCheck } from "./dist/tools/health-check.js";
import { initDb, closeDb, resetDb } from "./dist/cache/db.js";
import {
  setCachedReadiness,
  setCachedSleep,
  setCachedActivity,
  clearHealthCache,
  getCacheStats,
} from "./dist/cache/operations.js";

console.log("=".repeat(80));
console.log("OURA MCP SERVER - INTEGRATION TESTS");
console.log("=".repeat(80));

let testsPassed = 0;
let testsFailed = 0;

/**
 * Helper: Run a test with error handling
 */
async function runTest(testName, testFn) {
  console.log(`\n${"=".repeat(80)}`);
  console.log(`TEST: ${testName}`);
  console.log("=".repeat(80));

  try {
    await testFn();
    console.log(`✅ PASS: ${testName}`);
    testsPassed++;
  } catch (error) {
    console.error(`❌ FAIL: ${testName}`);
    console.error(`Error: ${error.message}`);
    if (error.stack) {
      console.error(error.stack);
    }
    testsFailed++;
  }
}

/**
 * Helper: Assert condition
 */
function assert(condition, message) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

/**
 * Helper: Parse tool response
 */
function parseToolResponse(response) {
  assert(response.content && response.content.length > 0, "Response should have content");
  assert(response.content[0].type === "text", "Content should be text");
  return JSON.parse(response.content[0].text);
}

/**
 * Helper: Create mock readiness data
 */
function createMockReadinessData(date, score) {
  return {
    id: `${date}-readiness`,
    day: date,
    score: score,
    temperature_deviation: 0.1,
    temperature_trend_deviation: 0.05,
    contributors: {
      activity_balance: 85,
      body_temperature: 90,
      hrv_balance: 88,
      previous_day_activity: 82,
      previous_night: 87,
      recovery_index: 86,
      resting_heart_rate: 89,
      sleep_balance: 91,
    },
  };
}

/**
 * Helper: Create mock sleep data
 */
function createMockSleepData(date, score) {
  return {
    id: `${date}-sleep`,
    day: date,
    score: score,
    total_sleep_duration: 27000, // 7.5 hours
    rem_sleep_duration: 6480, // 1.8 hours
    deep_sleep_duration: 5400, // 1.5 hours
    light_sleep_duration: 14400, // 4 hours
    awake_time: 720, // 12 minutes
    efficiency: 95,
    latency: 300, // 5 minutes
    restless_periods: 2,
    average_heart_rate: 55,
    average_hrv: 45,
    breath_average: 14.5,
    contributors: {
      deep_sleep: 90,
      efficiency: 95,
      latency: 88,
      rem_sleep: 85,
      restfulness: 92,
      timing: 87,
      total_sleep: 89,
    },
  };
}

/**
 * Helper: Create mock activity data
 */
function createMockActivityData(date, score) {
  return {
    id: `${date}-activity`,
    day: date,
    score: score,
    active_calories: 450,
    steps: 8500,
    equivalent_walking_distance: 6800,
    high_activity_met_minutes: 45,
    medium_activity_met_minutes: 120,
    low_activity_met_minutes: 180,
    contributors: {
      meet_daily_targets: 85,
      move_every_hour: 80,
      recovery_time: 90,
      stay_active: 87,
      training_frequency: 82,
      training_volume: 88,
    },
  };
}

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

await runTest("1. Health Check Tool - System Status", async () => {
  const response = await handleHealthCheck({});
  const data = parseToolResponse(response);

  console.log("Overall status:", data.overall_status);
  console.log("API status:", data.components.api.status);
  console.log("Cache status:", data.components.cache.status);

  assert(data.timestamp, "Should have timestamp");
  assert(data.components.api, "Should have API component");
  assert(data.components.cache, "Should have cache component");
  assert(data.diagnostics, "Should have diagnostics");
  assert(Array.isArray(data.diagnostics.recommendations), "Should have recommendations array");

  console.log(`Recommendations: ${data.diagnostics.recommendations.length}`);
});

await runTest("2. Cache-First Behavior - Empty Cache Falls Back to API", async () => {
  // Clear cache to ensure we test API fallback
  initDb();
  await clearHealthCache();

  const today = new Date().toISOString().split("T")[0];

  const response = await handleGetTodayReadiness({ date: today });
  const data = parseToolResponse(response);

  console.log("Date:", data.date);
  console.log("Source:", data.source);

  // Should either get data from API or gracefully handle no data
  if (data.error) {
    console.log("Expected: No data available (API not configured or no data)");
    assert(data.error.includes("No readiness data") ||
           data.error.includes("API") ||
           data.error.includes("authentication"),
           "Error should be about missing data or API");
  } else {
    console.log("Got data - Score:", data.score);
    assert(data.source === "api" || data.source === "cache", "Source should be api or cache");
  }
});

await runTest("3. Cache-First Behavior - Returns Cached Data When Available", async () => {
  initDb();

  const testDate = "2024-01-15";
  const mockData = createMockReadinessData(testDate, 85);

  // Seed cache with test data
  setCachedReadiness(testDate, mockData);

  const response = await handleGetTodayReadiness({ date: testDate });
  const data = parseToolResponse(response);

  console.log("Date:", data.date);
  console.log("Score:", data.score);
  console.log("Source:", data.source);

  assert(data.date === testDate, "Should return requested date");
  assert(data.score === 85, "Should return cached score");
  assert(data.source === "cache", "Should indicate cache source");
  assert(data.interpretation, "Should have interpretation");
  assert(data.contributors, "Should have contributors");

  console.log("✓ Successfully retrieved cached data");
});

await runTest("4. Sleep Summary Tool - Cache Integration", async () => {
  initDb();

  const testDate = "2024-01-16";
  const mockData = createMockSleepData(testDate, 88);

  // Seed cache with test data
  setCachedSleep(testDate, mockData);

  const response = await handleGetSleepSummary({ date: testDate });
  const data = parseToolResponse(response);

  console.log("Date:", data.date);
  console.log("Score:", data.score);
  console.log("Total sleep:", data.total_sleep);
  console.log("Source:", data.source);

  assert(data.date === testDate, "Should return requested date");
  assert(data.score === 88, "Should return cached score");
  assert(data.source === "cache", "Should indicate cache source");
  assert(data.sleep_stages, "Should have sleep stages");
  assert(data.efficiency, "Should have efficiency");
  assert(data.timing, "Should have timing");

  console.log("✓ Successfully retrieved cached sleep data");
});

await runTest("5. Weekly Trends Tool - Multi-Source Cache Integration", async () => {
  initDb();
  await clearHealthCache();

  // Seed cache with a week of test data
  const today = new Date();
  for (let i = 0; i < 7; i++) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    const dateStr = date.toISOString().split("T")[0];

    const readinessScore = 80 + i; // Increasing trend
    const sleepScore = 85 - i; // Decreasing trend
    const activityScore = 75 + (i % 3); // Stable trend

    setCachedReadiness(dateStr, createMockReadinessData(dateStr, readinessScore));
    setCachedSleep(dateStr, createMockSleepData(dateStr, sleepScore));
    setCachedActivity(dateStr, createMockActivityData(dateStr, activityScore));
  }

  const endDate = today.toISOString().split("T")[0];
  const response = await handleGetWeeklyTrends({ end_date: endDate, days: 7 });
  const data = parseToolResponse(response);

  console.log("Period:", `${data.period.start_date} to ${data.period.end_date}`);
  console.log("Readiness avg:", data.statistics.readiness.average);
  console.log("Readiness trend:", data.statistics.readiness.trend);
  console.log("Sleep avg:", data.statistics.sleep.average);
  console.log("Sleep trend:", data.statistics.sleep.trend);
  console.log("Activity avg:", data.statistics.activity.average);
  console.log("Activity trend:", data.statistics.activity.trend);
  console.log("Patterns found:", data.patterns.length);

  assert(data.period.days === 7, "Should cover 7 days");
  assert(data.statistics.readiness.average > 0, "Should have readiness average");
  assert(data.statistics.sleep.average > 0, "Should have sleep average");
  assert(data.statistics.activity.average > 0, "Should have activity average");
  assert(data.statistics.readiness.trend, "Should detect readiness trend");
  assert(data.statistics.sleep.trend, "Should detect sleep trend");
  assert(Array.isArray(data.patterns), "Should have patterns array");
  assert(data.daily_data.length === 7, "Should have 7 days of data");

  console.log("✓ Successfully analyzed weekly trends from cache");
});

await runTest("6. Error Handling - Invalid Date Format", async () => {
  const response = await handleGetTodayReadiness({ date: "invalid-date" });
  const data = parseToolResponse(response);

  console.log("Error message:", data.error);

  assert(data.error, "Should return error");
  assert(data.error.includes("Invalid date format") ||
         data.error.includes("date"),
         "Error should mention date format");

  console.log("✓ Properly handled invalid date");
});

await runTest("7. Error Handling - Missing Data Graceful Response", async () => {
  initDb();
  await clearHealthCache();

  const futureDate = "2030-12-31";
  const response = await handleGetTodayReadiness({ date: futureDate });
  const data = parseToolResponse(response);

  console.log("Response for future date:", data.error || "Has data");

  // Should gracefully handle missing data
  if (data.error) {
    assert(data.error.includes("No readiness data") ||
           data.error.includes("not available"),
           "Should explain data is not available");
    console.log("✓ Gracefully handled missing data");
  } else {
    console.log("⚠️  Got unexpected data for future date");
  }
});

await runTest("8. Cache Statistics Verification", async () => {
  initDb();

  const stats = getCacheStats();

  console.log("Total entries:", stats.total_entries);
  console.log("Readiness entries:", stats.readiness_count);
  console.log("Sleep entries:", stats.sleep_count);
  console.log("Activity entries:", stats.activity_count);
  console.log("Last sync:", stats.last_sync || "Never");

  assert(typeof stats.total_entries === "number", "Should have total_entries count");
  assert(typeof stats.readiness_count === "number", "Should have readiness_count");
  assert(typeof stats.sleep_count === "number", "Should have sleep_count");
  assert(typeof stats.activity_count === "number", "Should have activity_count");

  console.log("✓ Cache statistics working correctly");
});

await runTest("9. Tool Response Format Validation - Readiness", async () => {
  initDb();

  const testDate = "2024-01-20";
  const mockData = createMockReadinessData(testDate, 92);
  setCachedReadiness(testDate, mockData);

  const response = await handleGetTodayReadiness({ date: testDate });
  const data = parseToolResponse(response);

  // Validate response structure
  assert(typeof data.date === "string", "date should be string");
  assert(typeof data.score === "number", "score should be number");
  assert(typeof data.interpretation === "string", "interpretation should be string");
  assert(typeof data.source === "string", "source should be string");
  assert(typeof data.contributors === "object", "contributors should be object");
  assert(typeof data.metrics === "object", "metrics should be object");

  // Validate contributors have required fields
  const contributor = data.contributors.sleep_balance || data.contributors.activity_balance;
  if (contributor) {
    assert(typeof contributor.score === "number", "contributor should have score");
    assert(typeof contributor.meaning === "string", "contributor should have meaning");
  }

  console.log("✓ Response format validated");
});

await runTest("10. Tool Response Format Validation - Sleep", async () => {
  initDb();

  const testDate = "2024-01-21";
  const mockData = createMockSleepData(testDate, 87);
  setCachedSleep(testDate, mockData);

  const response = await handleGetSleepSummary({ date: testDate });
  const data = parseToolResponse(response);

  // Validate response structure
  assert(typeof data.date === "string", "date should be string");
  assert(typeof data.score === "number", "score should be number");
  assert(typeof data.interpretation === "string", "interpretation should be string");
  assert(typeof data.total_sleep === "string", "total_sleep should be formatted string");
  assert(typeof data.sleep_stages === "object", "sleep_stages should be object");
  assert(typeof data.efficiency === "object", "efficiency should be object");
  assert(typeof data.timing === "object", "timing should be object");
  assert(typeof data.contributors === "object", "contributors should be object");

  // Validate sleep stages
  assert(data.sleep_stages.rem, "Should have REM sleep");
  assert(data.sleep_stages.deep, "Should have deep sleep");
  assert(data.sleep_stages.light, "Should have light sleep");

  console.log("✓ Response format validated");
});

await runTest("11. Default Parameters - Readiness Defaults to Today", async () => {
  const response = await handleGetTodayReadiness({});
  const data = parseToolResponse(response);

  const today = new Date().toISOString().split("T")[0];

  console.log("Requested date:", data.date);
  console.log("Today's date:", today);

  assert(data.date === today, "Should default to today's date");

  console.log("✓ Default parameter working correctly");
});

await runTest("12. Default Parameters - Trends Defaults to 7 Days", async () => {
  initDb();

  const response = await handleGetWeeklyTrends({});
  const data = parseToolResponse(response);

  if (!data.error) {
    console.log("Period days:", data.period.days);
    assert(data.period.days === 7, "Should default to 7 days");
    console.log("✓ Default parameter working correctly");
  } else {
    console.log("No data available (expected if API not configured)");
  }
});

// =============================================================================
// CLEANUP AND SUMMARY
// =============================================================================

console.log("\n" + "=".repeat(80));
console.log("TEST SUMMARY");
console.log("=".repeat(80));
console.log(`✅ Tests Passed: ${testsPassed}`);
console.log(`❌ Tests Failed: ${testsFailed}`);
console.log(`📊 Total Tests: ${testsPassed + testsFailed}`);
console.log(`🎯 Success Rate: ${((testsPassed / (testsPassed + testsFailed)) * 100).toFixed(1)}%`);
console.log("=".repeat(80));

// Close database connection
try {
  closeDb();
  console.log("\n✓ Database connection closed");
} catch (error) {
  console.error("\n⚠️  Error closing database:", error.message);
}

// Exit with appropriate code
process.exit(testsFailed > 0 ? 1 : 0);
