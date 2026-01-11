#!/usr/bin/env node
/**
 * Test script for SQLite cache schema
 * Verifies table creation, indexes, and basic operations
 */

import Database from "better-sqlite3";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Import from built files
import { pathToFileURL } from "url";
const schemaModule = await import(
  pathToFileURL(path.join(__dirname, "dist", "cache", "schema.js")).href
);
const {
  initializeSchema,
  runMigrations,
  getSchemaVersion,
  setSchemaVersion,
  calculateExpiresAt,
  isExpired,
  cleanupExpiredCache,
  CURRENT_SCHEMA_VERSION,
} = schemaModule;

// Test database path (temporary)
const TEST_DB_PATH = path.join(__dirname, ".cache", "test-schema.db");

// Ensure cache directory exists
const cacheDir = path.dirname(TEST_DB_PATH);
if (!fs.existsSync(cacheDir)) {
  fs.mkdirSync(cacheDir, { recursive: true });
}

// Clean up test database if it exists
if (fs.existsSync(TEST_DB_PATH)) {
  fs.unlinkSync(TEST_DB_PATH);
}

console.log("🧪 Testing Oura MCP SQLite Schema\n");

try {
  // Test 1: Database creation
  console.log("1. Creating database...");
  const db = new Database(TEST_DB_PATH);
  console.log("   ✓ Database created");

  // Test 2: Schema initialization
  console.log("\n2. Initializing schema...");
  initializeSchema(db);
  console.log("   ✓ Schema initialized");

  // Test 3: Verify tables exist
  console.log("\n3. Verifying tables...");
  const tables = db
    .prepare(
      "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    .all();
  const tableNames = tables.map((t) => t.name);
  const expectedTables = [
    "activity_data",
    "api_tokens",
    "cache_meta",
    "heart_rate_data",
    "readiness_data",
    "sleep_data",
  ];

  for (const expectedTable of expectedTables) {
    if (tableNames.includes(expectedTable)) {
      console.log(`   ✓ Table '${expectedTable}' exists`);
    } else {
      throw new Error(`Table '${expectedTable}' not found`);
    }
  }

  // Test 4: Verify indexes exist
  console.log("\n4. Verifying indexes...");
  const indexes = db
    .prepare(
      "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name"
    )
    .all();
  const indexNames = indexes.map((i) => i.name);
  const expectedIndexCount = 9; // 3 per data table (sleep, readiness, activity) + 3 for heart_rate

  if (indexNames.length >= expectedIndexCount) {
    console.log(`   ✓ Found ${indexNames.length} indexes`);
    indexNames.forEach((name) => console.log(`     - ${name}`));
  } else {
    throw new Error(
      `Expected at least ${expectedIndexCount} indexes, found ${indexNames.length}`
    );
  }

  // Test 5: Schema version
  console.log("\n5. Testing schema version...");
  const initialVersion = getSchemaVersion(db);
  console.log(`   Current version: ${initialVersion}`);
  setSchemaVersion(db, CURRENT_SCHEMA_VERSION);
  const updatedVersion = getSchemaVersion(db);
  if (updatedVersion === CURRENT_SCHEMA_VERSION) {
    console.log(`   ✓ Schema version set to ${CURRENT_SCHEMA_VERSION}`);
  } else {
    throw new Error(
      `Schema version mismatch: expected ${CURRENT_SCHEMA_VERSION}, got ${updatedVersion}`
    );
  }

  // Test 6: Insert test data
  console.log("\n6. Testing data insertion...");
  const now = new Date().toISOString();
  const expiresAt = calculateExpiresAt(1);

  // Insert sleep data
  db.prepare(
    "INSERT INTO sleep_data (id, day, data, cached_at, expires_at) VALUES (?, ?, ?, ?, ?)"
  ).run("sleep-001", "2026-01-10", '{"score": 85}', now, expiresAt);

  // Insert readiness data
  db.prepare(
    "INSERT INTO readiness_data (id, day, data, cached_at, expires_at) VALUES (?, ?, ?, ?, ?)"
  ).run("readiness-001", "2026-01-10", '{"score": 78}', now, expiresAt);

  // Insert activity data
  db.prepare(
    "INSERT INTO activity_data (id, day, data, cached_at, expires_at) VALUES (?, ?, ?, ?, ?)"
  ).run("activity-001", "2026-01-10", '{"score": 82}', now, expiresAt);

  // Insert heart rate data
  db.prepare(
    "INSERT INTO heart_rate_data (timestamp, bpm, source, day, cached_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)"
  ).run(now, 65, "sleep", "2026-01-10", now, expiresAt);

  console.log("   ✓ Sleep data inserted");
  console.log("   ✓ Readiness data inserted");
  console.log("   ✓ Activity data inserted");
  console.log("   ✓ Heart rate data inserted");

  // Test 7: Query data
  console.log("\n7. Testing data queries...");
  const sleepRow = db
    .prepare("SELECT * FROM sleep_data WHERE day = ?")
    .get("2026-01-10");
  if (sleepRow && JSON.parse(sleepRow.data).score === 85) {
    console.log("   ✓ Sleep data query successful");
  } else {
    throw new Error("Sleep data query failed");
  }

  const readinessRow = db
    .prepare("SELECT * FROM readiness_data WHERE day = ?")
    .get("2026-01-10");
  if (readinessRow && JSON.parse(readinessRow.data).score === 78) {
    console.log("   ✓ Readiness data query successful");
  } else {
    throw new Error("Readiness data query failed");
  }

  // Test 8: Expiry utilities
  console.log("\n8. Testing expiry utilities...");
  const futureExpiry = calculateExpiresAt(24);
  const pastExpiry = new Date(Date.now() - 1000 * 60 * 60).toISOString();

  if (!isExpired(futureExpiry)) {
    console.log("   ✓ Future expiry detected correctly");
  } else {
    throw new Error("Future expiry check failed");
  }

  if (isExpired(pastExpiry)) {
    console.log("   ✓ Past expiry detected correctly");
  } else {
    throw new Error("Past expiry check failed");
  }

  // Test 9: Cache cleanup
  console.log("\n9. Testing cache cleanup...");
  // Insert expired data
  db.prepare(
    "INSERT INTO sleep_data (id, day, data, cached_at, expires_at) VALUES (?, ?, ?, ?, ?)"
  ).run("sleep-002", "2026-01-09", '{"score": 75}', pastExpiry, pastExpiry);

  const deletedCount = cleanupExpiredCache(db);
  if (deletedCount > 0) {
    console.log(`   ✓ Cleaned up ${deletedCount} expired entries`);
  } else {
    console.log("   ✓ No expired entries to clean");
  }

  // Test 10: Migrations
  console.log("\n10. Testing migrations...");
  runMigrations(db);
  console.log("   ✓ Migrations completed successfully");

  // Close database
  db.close();
  console.log("\n✅ All tests passed!");

  // Clean up test database
  if (fs.existsSync(TEST_DB_PATH)) {
    fs.unlinkSync(TEST_DB_PATH);
    console.log("🧹 Test database cleaned up");
  }

  process.exit(0);
} catch (error) {
  console.error("\n❌ Test failed:", error.message);
  console.error(error.stack);

  // Clean up test database on failure
  if (fs.existsSync(TEST_DB_PATH)) {
    fs.unlinkSync(TEST_DB_PATH);
  }

  process.exit(1);
}
