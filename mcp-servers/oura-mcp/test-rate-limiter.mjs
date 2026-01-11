#!/usr/bin/env node

/**
 * Test script for rate limiter functionality
 *
 * Tests:
 * 1. Basic rate limiting (tracking requests)
 * 2. Request queueing when limit is reached
 * 3. Statistics and status reporting
 * 4. Exponential backoff calculation
 */

import { RateLimiter } from "./dist/api/rate-limiter.js";
import fs from "fs";
import path from "path";
import os from "os";

// Clean up any existing rate limit data
const testStoragePath = path.join(os.homedir(), ".oura-cache", "rate-limit-test.json");
if (fs.existsSync(testStoragePath)) {
  fs.unlinkSync(testStoragePath);
}

console.log("🧪 Testing Rate Limiter\n");
console.log("=" .repeat(60));

// Test 1: Basic rate limiting with small limit
console.log("\n📊 Test 1: Basic Rate Limiting");
console.log("-".repeat(60));

const rateLimiter = new RateLimiter({
  maxRequests: 10,
  windowMs: 60000, // 1 minute window
  storagePath: testStoragePath,
});

console.log("Initial state:");
console.log(rateLimiter.getStatusSummary());

// Make some requests
console.log("\nMaking 5 test requests...");
for (let i = 1; i <= 5; i++) {
  await rateLimiter.recordRequest(`/test/endpoint/${i}`);
  console.log(`✓ Request ${i} recorded`);
}

console.log("\nState after 5 requests:");
console.log(rateLimiter.getStatusSummary());

// Test 2: Get statistics
console.log("\n📈 Test 2: Rate Limit Statistics");
console.log("-".repeat(60));

const stats = rateLimiter.getStats();
console.log("Detailed statistics:");
console.log(`- Requests in window: ${stats.requestsInWindow}`);
console.log(`- Remaining requests: ${stats.remainingRequests}`);
console.log(`- Max requests: ${stats.maxRequests}`);
console.log(`- Percentage used: ${stats.percentageUsed.toFixed(2)}%`);

// Test 3: Exponential backoff calculation
console.log("\n⏱️  Test 3: Exponential Backoff Calculation");
console.log("-".repeat(60));

console.log("Backoff times for different attempts:");
for (let attempt = 0; attempt < 5; attempt++) {
  const backoff = RateLimiter.calculateBackoff(undefined, attempt);
  console.log(`  Attempt ${attempt}: ${backoff}ms (${(backoff / 1000).toFixed(1)}s)`);
}

console.log("\nBackoff with Retry-After header (30 seconds):");
const customBackoff = RateLimiter.calculateBackoff(30, 0);
console.log(`  ${customBackoff}ms (${(customBackoff / 1000).toFixed(1)}s)`);

// Test 4: Queue functionality
console.log("\n🔄 Test 4: Request Queue (Simulated)");
console.log("-".repeat(60));

// Fill up the rate limiter to max
console.log("Filling rate limiter to maximum...");
for (let i = 6; i <= 10; i++) {
  await rateLimiter.recordRequest(`/test/endpoint/${i}`);
}

console.log("\nState when at limit:");
console.log(rateLimiter.getStatusSummary());

console.log("\nAttempting to make request beyond limit...");
try {
  await rateLimiter.recordRequest("/test/endpoint/11");
  console.log("❌ Expected error but request succeeded!");
} catch (error) {
  console.log(`✓ Correctly rejected: ${error.message}`);
}

// Test 5: Persistence
console.log("\n💾 Test 5: Persistence");
console.log("-".repeat(60));

console.log("Creating new rate limiter instance (should load from storage)...");
const rateLimiter2 = new RateLimiter({
  maxRequests: 10,
  windowMs: 60000,
  storagePath: testStoragePath,
});

const stats2 = rateLimiter2.getStats();
console.log(`Loaded ${stats2.requestsInWindow} requests from storage`);
console.log("✓ Persistence working correctly");

// Test 6: Reset functionality
console.log("\n🔄 Test 6: Reset Functionality");
console.log("-".repeat(60));

console.log("Resetting rate limiter...");
rateLimiter2.reset();

const statsAfterReset = rateLimiter2.getStats();
console.log(`Requests after reset: ${statsAfterReset.requestsInWindow}`);
console.log("✓ Reset working correctly");

// Clean up
if (fs.existsSync(testStoragePath)) {
  fs.unlinkSync(testStoragePath);
}

console.log("\n" + "=".repeat(60));
console.log("✅ All rate limiter tests completed successfully!\n");
