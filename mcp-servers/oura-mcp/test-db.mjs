#!/usr/bin/env node

/**
 * Test script for database initialization
 * Tests:
 * - Database and directory creation
 * - Schema initialization
 * - Migration system
 * - Database statistics
 * - Graceful shutdown
 */

import { initDb, getDb, closeDb, getDbPath, getCacheDir, dbExists, resetDb, getDbStats } from "./dist/cache/db.js";
import { getSchemaVersion, cleanupExpiredCache, calculateExpiresAt, isExpired } from "./dist/cache/schema.js";

console.log("🧪 Testing Oura MCP Database Initialization\n");

let testsPassed = 0;
let testsFailed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`✅ ${name}`);
    testsPassed++;
  } catch (error) {
    console.error(`❌ ${name}`);
    console.error(`   Error: ${error.message}`);
    testsFailed++;
  }
}

// Test 1: Database initialization creates directory
test("Database initialization creates cache directory", () => {
  const cacheDir = getCacheDir();
  console.log(`   Cache directory: ${cacheDir}`);
  if (!cacheDir.includes(".oura-cache")) {
    throw new Error("Cache directory path incorrect");
  }
});

// Test 2: Database file is created
test("Database file is created", () => {
  const db = initDb();
  const dbPath = getDbPath();
  console.log(`   Database path: ${dbPath}`);
  if (!dbExists()) {
    throw new Error("Database file was not created");
  }
  if (!dbPath.includes("oura-health.db")) {
    throw new Error("Database filename incorrect");
  }
});

// Test 3: Schema version is set
test("Schema version is initialized", () => {
  const db = getDb();
  const version = getSchemaVersion(db);
  console.log(`   Schema version: ${version}`);
  if (version !== 1) {
    throw new Error(`Expected schema version 1, got ${version}`);
  }
});

// Test 4: All tables are created
test("All required tables are created", () => {
  const db = getDb();
  const tables = db
    .prepare(
      "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    .all();
  const tableNames = tables.map((t) => t.name);
  console.log(`   Tables: ${tableNames.join(", ")}`);

  const requiredTables = [
    "sleep_data",
    "readiness_data",
    "activity_data",
    "heart_rate_data",
    "api_tokens",
    "cache_meta",
  ];

  for (const table of requiredTables) {
    if (!tableNames.includes(table)) {
      throw new Error(`Required table '${table}' not found`);
    }
  }
});

// Test 5: All indexes are created
test("All required indexes are created", () => {
  const db = getDb();
  const indexes = db
    .prepare(
      "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name"
    )
    .all();
  const indexNames = indexes.map((i) => i.name);
  console.log(`   Indexes: ${indexNames.length} total`);

  const requiredIndexes = [
    "idx_sleep_data_day",
    "idx_sleep_data_expires",
    "idx_readiness_data_day",
    "idx_readiness_data_expires",
    "idx_activity_data_day",
    "idx_activity_data_expires",
    "idx_heart_rate_data_day",
    "idx_heart_rate_data_timestamp",
    "idx_heart_rate_data_expires",
  ];

  for (const index of requiredIndexes) {
    if (!indexNames.includes(index)) {
      throw new Error(`Required index '${index}' not found`);
    }
  }
});

// Test 6: WAL mode is enabled
test("WAL mode is enabled", () => {
  const stats = getDbStats();
  console.log(`   WAL mode: ${stats.walMode}`);
  if (!stats.walMode) {
    throw new Error("WAL mode is not enabled");
  }
});

// Test 7: Database stats are available
test("Database statistics are available", () => {
  const stats = getDbStats();
  console.log(`   Size: ${stats.size} bytes`);
  console.log(`   Page count: ${stats.pageCount}`);
  console.log(`   Page size: ${stats.pageSize}`);
  if (!stats.exists) {
    throw new Error("Database stats show database doesn't exist");
  }
});

// Test 8: Can insert and query data
test("Can insert and query cache data", () => {
  const db = getDb();
  const testData = {
    id: "test-sleep-123",
    day: "2026-01-11",
    data: JSON.stringify({ score: 85, total_sleep_duration: 28800 }),
    cached_at: new Date().toISOString(),
    expires_at: calculateExpiresAt(1),
  };

  // Insert test data
  const insertStmt = db.prepare(`
    INSERT INTO sleep_data (id, day, data, cached_at, expires_at)
    VALUES (?, ?, ?, ?, ?)
  `);
  insertStmt.run(
    testData.id,
    testData.day,
    testData.data,
    testData.cached_at,
    testData.expires_at
  );

  // Query it back
  const selectStmt = db.prepare(`SELECT * FROM sleep_data WHERE id = ?`);
  const result = selectStmt.get(testData.id);

  if (!result) {
    throw new Error("Failed to retrieve inserted data");
  }
  if (result.day !== testData.day) {
    throw new Error("Retrieved data doesn't match inserted data");
  }
  console.log(`   Inserted and retrieved sleep data for ${testData.day}`);

  // Clean up
  db.prepare(`DELETE FROM sleep_data WHERE id = ?`).run(testData.id);
});

// Test 9: Expiry calculation works
test("Cache expiry calculation works", () => {
  const expiresIn1Hour = calculateExpiresAt(1);
  const expiresIn24Hours = calculateExpiresAt(24);

  const date1h = new Date(expiresIn1Hour);
  const date24h = new Date(expiresIn24Hours);
  const now = new Date();

  const diff1h = (date1h - now) / (1000 * 60 * 60); // Hours
  const diff24h = (date24h - now) / (1000 * 60 * 60); // Hours

  if (Math.abs(diff1h - 1) > 0.1) {
    throw new Error(`1 hour expiry calculation incorrect: ${diff1h}`);
  }
  if (Math.abs(diff24h - 24) > 0.1) {
    throw new Error(`24 hour expiry calculation incorrect: ${diff24h}`);
  }
  console.log(`   1 hour: ${expiresIn1Hour}`);
  console.log(`   24 hours: ${expiresIn24Hours}`);
});

// Test 10: isExpired works correctly
test("isExpired detection works", () => {
  const pastDate = new Date(Date.now() - 1000 * 60 * 60).toISOString(); // 1 hour ago
  const futureDate = new Date(Date.now() + 1000 * 60 * 60).toISOString(); // 1 hour from now

  if (!isExpired(pastDate)) {
    throw new Error("Past date should be expired");
  }
  if (isExpired(futureDate)) {
    throw new Error("Future date should not be expired");
  }
  console.log(`   Past date correctly detected as expired`);
  console.log(`   Future date correctly detected as not expired`);
});

// Test 11: Cleanup expired cache works
test("Cleanup expired cache works", () => {
  const db = getDb();

  // Insert expired test data
  const expiredData = {
    id: "test-sleep-expired",
    day: "2026-01-10",
    data: JSON.stringify({ score: 80 }),
    cached_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    expires_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(), // Expired 1 hour ago
  };

  db.prepare(`
    INSERT INTO sleep_data (id, day, data, cached_at, expires_at)
    VALUES (?, ?, ?, ?, ?)
  `).run(
    expiredData.id,
    expiredData.day,
    expiredData.data,
    expiredData.cached_at,
    expiredData.expires_at
  );

  // Run cleanup
  const deletedCount = cleanupExpiredCache(db);
  console.log(`   Cleaned up ${deletedCount} expired entries`);

  // Verify it was deleted
  const result = db
    .prepare(`SELECT * FROM sleep_data WHERE id = ?`)
    .get(expiredData.id);
  if (result) {
    throw new Error("Expired data was not cleaned up");
  }
});

// Test 12: Singleton pattern works
test("Singleton pattern returns same instance", () => {
  const db1 = getDb();
  const db2 = getDb();
  if (db1 !== db2) {
    throw new Error("getDb() returned different instances");
  }
  console.log(`   Same instance returned on multiple calls`);
});

// Summary
console.log("\n" + "=".repeat(50));
console.log(`✅ Tests passed: ${testsPassed}`);
console.log(`❌ Tests failed: ${testsFailed}`);
console.log("=".repeat(50));

// Close database
closeDb();
console.log("\n✅ Database closed successfully");

if (testsFailed > 0) {
  process.exit(1);
}
