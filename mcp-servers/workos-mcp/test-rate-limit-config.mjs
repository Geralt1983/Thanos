#!/usr/bin/env node
/**
 * Test script to verify rate limit configuration with environment variables
 */

import { getRateLimiter, resetRateLimiter } from './dist/shared/rate-limiter.js';

console.log('================================================================================');
console.log('Rate Limit Configuration Test');
console.log('================================================================================\n');

// Test 1: Default configuration (from validation-constants.ts)
console.log('[Test 1] Testing default configuration...');
const limiter1 = getRateLimiter();
const stats1 = limiter1.getStats();
console.log(`Global limit: ${stats1.global.limit} (expected: 100)`);
console.log(`Write limit: ${stats1.write.limit} (expected: 20)`);
console.log(`Read limit: ${stats1.read.limit} (expected: 60)`);

if (stats1.global.limit === 100 && stats1.write.limit === 20 && stats1.read.limit === 60) {
  console.log('✓ Default configuration correct\n');
} else {
  console.log('✗ Default configuration incorrect\n');
  process.exit(1);
}

// Test 2: Custom configuration via constructor
console.log('[Test 2] Testing custom configuration via constructor...');
resetRateLimiter();
const limiter2 = getRateLimiter({
  globalPerMinute: 50,
  writeOpsPerMinute: 10,
  readOpsPerMinute: 30,
});
const stats2 = limiter2.getStats();
console.log(`Global limit: ${stats2.global.limit} (expected: 50)`);
console.log(`Write limit: ${stats2.write.limit} (expected: 10)`);
console.log(`Read limit: ${stats2.read.limit} (expected: 30)`);

if (stats2.global.limit === 50 && stats2.write.limit === 10 && stats2.read.limit === 30) {
  console.log('✓ Custom configuration correct\n');
} else {
  console.log('✗ Custom configuration incorrect\n');
  process.exit(1);
}

// Test 3: Rate limiting disabled
console.log('[Test 3] Testing rate limiting disabled...');
resetRateLimiter();
const limiter3 = getRateLimiter({ enabled: false });
const result = limiter3.checkRateLimit('workos_create_task');
console.log(`Rate limiting enabled: ${!result.allowed} (expected: false)`);

if (result.allowed) {
  console.log('✓ Rate limiting can be disabled\n');
} else {
  console.log('✗ Rate limiting should be disabled\n');
  process.exit(1);
}

// Cleanup
resetRateLimiter();

console.log('================================================================================');
console.log('All configuration tests passed! ✓');
console.log('================================================================================');
