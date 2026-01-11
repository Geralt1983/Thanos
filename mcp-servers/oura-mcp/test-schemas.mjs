#!/usr/bin/env node

/**
 * Test script for Zod validation schemas
 * Validates that schemas correctly parse valid data and reject invalid data
 */

import {
  DailySleepSchema,
  DailyReadinessSchema,
  DailyActivitySchema,
  HeartRateDataSchema,
  validateResponse,
  safeValidate,
  schemas,
} from "./dist/api/schemas.js";

// ANSI color codes for output
const GREEN = "\x1b[32m";
const RED = "\x1b[31m";
const YELLOW = "\x1b[33m";
const RESET = "\x1b[0m";

let testsRun = 0;
let testsPassed = 0;
let testsFailed = 0;

function test(description, fn) {
  testsRun++;
  try {
    fn();
    console.log(`${GREEN}✓${RESET} ${description}`);
    testsPassed++;
  } catch (error) {
    console.log(`${RED}✗${RESET} ${description}`);
    console.error(`  ${RED}Error: ${error.message}${RESET}`);
    testsFailed++;
  }
}

console.log("\n🧪 Running Zod Schema Validation Tests\n");

// =============================================================================
// SLEEP DATA VALIDATION TESTS
// =============================================================================

console.log("Sleep Data Schemas:");

test("validates valid sleep data", () => {
  const validSleep = {
    id: "sleep-123",
    day: "2024-01-15",
    score: 85,
    contributors: {
      deep_sleep: 80,
      efficiency: 90,
      latency: 75,
      rem_sleep: 85,
      restfulness: 80,
      timing: 70,
      total_sleep: 85,
    },
    total_sleep_duration: 28800,
    time_in_bed: 30000,
    awake_time: 1200,
    light_sleep_duration: 14400,
    deep_sleep_duration: 7200,
    rem_sleep_duration: 7200,
    restless_periods: 3,
    efficiency: 96,
    latency: 300,
    timing: {
      bedtime_start: "2024-01-14T22:30:00+00:00",
      bedtime_end: "2024-01-15T06:30:00+00:00",
    },
  };

  const result = DailySleepSchema.parse(validSleep);
  if (result.score !== 85) throw new Error("Score mismatch");
});

test("rejects invalid sleep score", () => {
  const invalidSleep = {
    id: "sleep-123",
    day: "2024-01-15",
    score: 150, // Invalid: > 100
    contributors: {
      deep_sleep: 80,
      efficiency: 90,
      latency: 75,
      rem_sleep: 85,
      restfulness: 80,
      timing: 70,
      total_sleep: 85,
    },
    total_sleep_duration: 28800,
    time_in_bed: 30000,
    awake_time: 1200,
    light_sleep_duration: 14400,
    deep_sleep_duration: 7200,
    rem_sleep_duration: 7200,
    restless_periods: 3,
    efficiency: 96,
    latency: 300,
    timing: {
      bedtime_start: "2024-01-14T22:30:00+00:00",
      bedtime_end: "2024-01-15T06:30:00+00:00",
    },
  };

  const result = DailySleepSchema.safeParse(invalidSleep);
  if (result.success) throw new Error("Should have rejected invalid score");
});

test("accepts null contributors", () => {
  const sleepWithNullContributors = {
    id: "sleep-123",
    day: "2024-01-15",
    score: null,
    contributors: {
      deep_sleep: null,
      efficiency: null,
      latency: null,
      rem_sleep: null,
      restfulness: null,
      timing: null,
      total_sleep: null,
    },
    total_sleep_duration: null,
    time_in_bed: null,
    awake_time: null,
    light_sleep_duration: null,
    deep_sleep_duration: null,
    rem_sleep_duration: null,
    restless_periods: null,
    efficiency: null,
    latency: null,
    timing: {
      bedtime_start: null,
      bedtime_end: null,
    },
  };

  const result = DailySleepSchema.parse(sleepWithNullContributors);
  if (result.score !== null) throw new Error("Should accept null score");
});

// =============================================================================
// READINESS DATA VALIDATION TESTS
// =============================================================================

console.log("\nReadiness Data Schemas:");

test("validates valid readiness data", () => {
  const validReadiness = {
    id: "readiness-123",
    day: "2024-01-15",
    score: 78,
    contributors: {
      activity_balance: 75,
      body_temperature: 80,
      hrv_balance: 70,
      previous_day_activity: 85,
      previous_night: 82,
      recovery_index: 76,
      resting_heart_rate: 79,
      sleep_balance: 81,
    },
    temperature_deviation: 0.2,
    temperature_trend_deviation: 0.1,
  };

  const result = DailyReadinessSchema.parse(validReadiness);
  if (result.score !== 78) throw new Error("Score mismatch");
});

test("rejects invalid date format", () => {
  const invalidReadiness = {
    id: "readiness-123",
    day: "2024/01/15", // Invalid format: should be YYYY-MM-DD
    score: 78,
    contributors: {
      activity_balance: 75,
      body_temperature: 80,
      hrv_balance: 70,
      previous_day_activity: 85,
      previous_night: 82,
      recovery_index: 76,
      resting_heart_rate: 79,
      sleep_balance: 81,
    },
    temperature_deviation: 0.2,
    temperature_trend_deviation: 0.1,
  };

  const result = DailyReadinessSchema.safeParse(invalidReadiness);
  if (result.success) throw new Error("Should have rejected invalid date format");
});

// =============================================================================
// ACTIVITY DATA VALIDATION TESTS
// =============================================================================

console.log("\nActivity Data Schemas:");

test("validates valid activity data", () => {
  const validActivity = {
    id: "activity-123",
    day: "2024-01-15",
    score: 82,
    active_calories: 450,
    average_met_minutes: 1.2,
    contributors: {
      meet_daily_targets: 85,
      move_every_hour: 70,
      recovery_time: 80,
      stay_active: 75,
      training_frequency: 90,
      training_volume: 85,
    },
    equivalent_walking_distance: 8500,
    high_activity_met_minutes: 120,
    high_activity_time: 3600,
    inactivity_alerts: 2,
    low_activity_met_minutes: 300,
    low_activity_time: 10800,
    medium_activity_met_minutes: 200,
    medium_activity_time: 7200,
    meters_to_target: 1500,
    non_wear_time: 0,
    resting_time: 28800,
    sedentary_met_minutes: 500,
    sedentary_time: 18000,
    steps: 8500,
    target_calories: 500,
    target_meters: 10000,
    total_calories: 2200,
    class: "medium",
  };

  const result = DailyActivitySchema.parse(validActivity);
  if (result.steps !== 8500) throw new Error("Steps mismatch");
});

test("accepts valid activity class", () => {
  const activityWithClass = {
    id: "activity-123",
    day: "2024-01-15",
    score: 82,
    active_calories: 450,
    average_met_minutes: 1.2,
    contributors: {
      meet_daily_targets: 85,
      move_every_hour: 70,
      recovery_time: 80,
      stay_active: 75,
      training_frequency: 90,
      training_volume: 85,
    },
    equivalent_walking_distance: 8500,
    high_activity_met_minutes: 120,
    high_activity_time: 3600,
    inactivity_alerts: 2,
    low_activity_met_minutes: 300,
    low_activity_time: 10800,
    medium_activity_met_minutes: 200,
    medium_activity_time: 7200,
    meters_to_target: 1500,
    non_wear_time: 0,
    resting_time: 28800,
    sedentary_met_minutes: 500,
    sedentary_time: 18000,
    steps: 8500,
    target_calories: 500,
    target_meters: 10000,
    total_calories: 2200,
    class: "high",
  };

  const result = DailyActivitySchema.parse(activityWithClass);
  if (result.class !== "high") throw new Error("Class mismatch");
});

// =============================================================================
// HEART RATE DATA VALIDATION TESTS
// =============================================================================

console.log("\nHeart Rate Data Schemas:");

test("validates valid heart rate data", () => {
  const validHeartRate = {
    bpm: 65,
    source: "sleep",
    timestamp: "2024-01-15T02:30:00+00:00",
  };

  const result = HeartRateDataSchema.parse(validHeartRate);
  if (result.bpm !== 65) throw new Error("BPM mismatch");
});

test("rejects invalid BPM", () => {
  const invalidHeartRate = {
    bpm: 350, // Invalid: > 300
    source: "sleep",
    timestamp: "2024-01-15T02:30:00+00:00",
  };

  const result = HeartRateDataSchema.safeParse(invalidHeartRate);
  if (result.success) throw new Error("Should have rejected invalid BPM");
});

test("rejects invalid heart rate source", () => {
  const invalidSource = {
    bpm: 65,
    source: "invalid_source",
    timestamp: "2024-01-15T02:30:00+00:00",
  };

  const result = HeartRateDataSchema.safeParse(invalidSource);
  if (result.success) throw new Error("Should have rejected invalid source");
});

// =============================================================================
// VALIDATION HELPER TESTS
// =============================================================================

console.log("\nValidation Helper Functions:");

test("validateResponse throws on invalid data", () => {
  const invalidData = { score: 150 };

  try {
    validateResponse(DailyReadinessSchema, invalidData, "readiness");
    throw new Error("Should have thrown validation error");
  } catch (error) {
    if (!error.message.includes("Validation failed")) {
      throw new Error("Wrong error type");
    }
  }
});

test("safeValidate returns null on invalid data", () => {
  const invalidData = { score: 150 };
  const result = safeValidate(DailyReadinessSchema, invalidData);

  if (result !== null) {
    throw new Error("Should have returned null for invalid data");
  }
});

test("safeValidate returns data on valid input", () => {
  const validReadiness = {
    id: "readiness-123",
    day: "2024-01-15",
    score: 78,
    contributors: {
      activity_balance: 75,
      body_temperature: 80,
      hrv_balance: 70,
      previous_day_activity: 85,
      previous_night: 82,
      recovery_index: 76,
      resting_heart_rate: 79,
      sleep_balance: 81,
    },
    temperature_deviation: 0.2,
    temperature_trend_deviation: 0.1,
  };

  const result = safeValidate(DailyReadinessSchema, validReadiness);
  if (result === null || result.score !== 78) {
    throw new Error("Should have returned valid data");
  }
});

// =============================================================================
// PAGINATED RESPONSE TESTS
// =============================================================================

console.log("\nPaginated Response Schemas:");

test("validates paginated response", () => {
  const paginatedResponse = {
    data: [
      {
        bpm: 65,
        source: "sleep",
        timestamp: "2024-01-15T02:30:00+00:00",
      },
      {
        bpm: 68,
        source: "rest",
        timestamp: "2024-01-15T08:00:00+00:00",
      },
    ],
    next_token: "abc123",
  };

  const HeartRateResponseSchema = schemas.OuraAPIResponse(HeartRateDataSchema);
  const result = HeartRateResponseSchema.parse(paginatedResponse);

  if (result.data.length !== 2) throw new Error("Data length mismatch");
  if (result.next_token !== "abc123") throw new Error("Token mismatch");
});

test("validates paginated response with null token", () => {
  const paginatedResponse = {
    data: [
      {
        bpm: 65,
        source: "sleep",
        timestamp: "2024-01-15T02:30:00+00:00",
      },
    ],
    next_token: null,
  };

  const HeartRateResponseSchema = schemas.OuraAPIResponse(HeartRateDataSchema);
  const result = HeartRateResponseSchema.parse(paginatedResponse);

  if (result.next_token !== null) throw new Error("Should accept null token");
});

// =============================================================================
// TEST SUMMARY
// =============================================================================

console.log("\n" + "=".repeat(60));
console.log("Test Summary:");
console.log("=".repeat(60));
console.log(`Total tests: ${testsRun}`);
console.log(`${GREEN}Passed: ${testsPassed}${RESET}`);
console.log(`${RED}Failed: ${testsFailed}${RESET}`);
console.log("=".repeat(60));

if (testsFailed > 0) {
  console.log(`\n${RED}❌ Some tests failed${RESET}\n`);
  process.exit(1);
} else {
  console.log(`\n${GREEN}✅ All tests passed!${RESET}\n`);
  process.exit(0);
}
