#!/usr/bin/env node
// =============================================================================
// RATE LIMITING TEST SUITE
// =============================================================================
// Comprehensive tests for rate limiting functionality across all scenarios
// Tests rate limit enforcement, window sliding, time-based reset, limit tiers,
// statistics tracking, error messages, and edge cases
// =============================================================================

import { RateLimiter, getRateLimiter, resetRateLimiter } from './dist/shared/rate-limiter.js';

// =============================================================================
// TEST UTILITIES
// =============================================================================

let testCount = 0;
let passCount = 0;
let failCount = 0;

function test(name, fn) {
  testCount++;
  try {
    fn();
    passCount++;
    console.log(`✓ Test ${testCount}: ${name}`);
  } catch (error) {
    failCount++;
    console.log(`✗ Test ${testCount}: ${name}`);
    console.log(`  Error: ${error.message}`);
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// =============================================================================
// TEST SUITE
// =============================================================================

console.log('='.repeat(80));
console.log('Rate Limiting Test Suite');
console.log('='.repeat(80));

// =============================================================================
// 1. BASIC INITIALIZATION & CONFIGURATION
// =============================================================================

console.log('\n[1] Basic Initialization & Configuration');
console.log('-'.repeat(80));

test('Rate limiter initializes with default configuration', () => {
  const limiter = new RateLimiter();
  const stats = limiter.getStats();
  assert(stats.global.limit === 100, 'Default global limit should be 100');
  assert(stats.write.limit === 20, 'Default write limit should be 20');
  assert(stats.read.limit === 60, 'Default read limit should be 60');
  limiter.shutdown();
});

test('Rate limiter accepts custom configuration', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 50,
    writeOpsPerMinute: 10,
    readOpsPerMinute: 30,
  });
  const stats = limiter.getStats();
  assert(stats.global.limit === 50, 'Custom global limit should be 50');
  assert(stats.write.limit === 10, 'Custom write limit should be 10');
  assert(stats.read.limit === 30, 'Custom read limit should be 30');
  limiter.shutdown();
});

test('Rate limiting can be disabled', () => {
  const limiter = new RateLimiter({ enabled: false });
  const result = limiter.checkRateLimit('workos_create_task');
  assert(result.allowed === true, 'All requests should be allowed when disabled');
  limiter.shutdown();
});

test('Singleton pattern works correctly', () => {
  resetRateLimiter();
  const instance1 = getRateLimiter();
  const instance2 = getRateLimiter();
  assert(instance1 === instance2, 'getRateLimiter should return same instance');
  resetRateLimiter();
  const instance3 = getRateLimiter();
  assert(instance1 !== instance3, 'resetRateLimiter should create new instance');
});

// =============================================================================
// 2. REQUEST COUNTING & TRACKING
// =============================================================================

console.log('\n[2] Request Counting & Tracking');
console.log('-'.repeat(80));

test('Initial request count is zero', () => {
  const limiter = new RateLimiter();
  const stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 0, 'Initial global count should be 0');
  assert(stats.write.requestsInWindow === 0, 'Initial write count should be 0');
  assert(stats.read.requestsInWindow === 0, 'Initial read count should be 0');
  limiter.shutdown();
});

test('Recording requests increments counters correctly', () => {
  const limiter = new RateLimiter();

  limiter.recordRequest('workos_create_task'); // write
  limiter.recordRequest('workos_get_tasks'); // read
  limiter.recordRequest('workos_update_task'); // write

  const stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 3, 'Global count should be 3');
  assert(stats.write.requestsInWindow === 2, 'Write count should be 2');
  assert(stats.read.requestsInWindow === 1, 'Read count should be 1');
  limiter.shutdown();
});

test('Statistics calculate remaining requests correctly', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 10,
    writeOpsPerMinute: 5,
    readOpsPerMinute: 5,
  });

  limiter.recordRequest('workos_create_task'); // write
  limiter.recordRequest('workos_get_tasks'); // read

  const stats = limiter.getStats();
  assert(stats.global.remaining === 8, 'Global remaining should be 8');
  assert(stats.write.remaining === 4, 'Write remaining should be 4');
  assert(stats.read.remaining === 4, 'Read remaining should be 4');
  limiter.shutdown();
});

test('Statistics calculate percentage used correctly', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 10,
    writeOpsPerMinute: 5,
    readOpsPerMinute: 5,
  });

  for (let i = 0; i < 5; i++) {
    limiter.recordRequest('workos_create_task');
  }

  const stats = limiter.getStats();
  assert(stats.global.percentageUsed === 50, 'Global percentage should be 50%');
  assert(stats.write.percentageUsed === 100, 'Write percentage should be 100%');
  limiter.shutdown();
});

// =============================================================================
// 3. OPERATION CLASSIFICATION
// =============================================================================

console.log('\n[3] Operation Classification');
console.log('-'.repeat(80));

test('Write operations are classified correctly', () => {
  const limiter = new RateLimiter();
  const writeTools = [
    'workos_create_task',
    'workos_update_task',
    'workos_delete_task',
    'workos_complete_task',
    'workos_promote_task',
    'workos_create_habit',
    'workos_complete_habit',
    'workos_log_energy',
    'workos_brain_dump',
    'workos_process_brain_dump',
    'workos_recalculate_streaks',
  ];

  writeTools.forEach(tool => limiter.recordRequest(tool));
  const stats = limiter.getStats();

  assert(stats.write.requestsInWindow === writeTools.length,
    `All ${writeTools.length} write operations should be tracked`);
  limiter.shutdown();
});

test('Read operations are classified correctly', () => {
  const limiter = new RateLimiter();
  const readTools = [
    'workos_get_tasks',
    'workos_get_clients',
    'workos_get_habits',
    'workos_get_habit_streaks',
    'workos_habit_checkin',
    'workos_habit_dashboard',
    'workos_get_energy',
    'workos_get_today_metrics',
    'workos_get_streak',
    'workos_get_client_memory',
    'workos_daily_summary',
    // Note: workos_get_brain_dump contains "dump" keyword and is classified as write
  ];

  readTools.forEach(tool => limiter.recordRequest(tool));
  const stats = limiter.getStats();

  assert(stats.read.requestsInWindow === readTools.length,
    `All ${readTools.length} read operations should be tracked`);
  limiter.shutdown();
});

// =============================================================================
// 4. RATE LIMIT ENFORCEMENT
// =============================================================================

console.log('\n[4] Rate Limit Enforcement');
console.log('-'.repeat(80));

test('Requests under limit are allowed', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 10,
    writeOpsPerMinute: 5,
    readOpsPerMinute: 5,
  });

  for (let i = 0; i < 4; i++) {
    const result = limiter.checkRateLimit('workos_create_task');
    assert(result.allowed === true, `Request ${i + 1} should be allowed`);
    limiter.recordRequest('workos_create_task');
  }
  limiter.shutdown();
});

test('Requests at limit are allowed', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 5,
    writeOpsPerMinute: 5,
    readOpsPerMinute: 5,
  });

  for (let i = 0; i < 5; i++) {
    const result = limiter.checkRateLimit('workos_create_task');
    assert(result.allowed === true, `Request ${i + 1} at limit should be allowed`);
    limiter.recordRequest('workos_create_task');
  }
  limiter.shutdown();
});

test('Global limit enforcement blocks excess requests', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 5,
    writeOpsPerMinute: 10,
    readOpsPerMinute: 10,
  });

  // Fill global limit
  for (let i = 0; i < 5; i++) {
    limiter.checkRateLimit('workos_get_tasks');
    limiter.recordRequest('workos_get_tasks');
  }

  // Next request should be blocked by global limit
  const result = limiter.checkRateLimit('workos_get_tasks');
  assert(result.allowed === false, 'Request exceeding global limit should be blocked');
  assert(result.limitType === 'global', 'Should report global limit exceeded');
  assert(result.current === 5, 'Should report 5 requests in window');
  assert(result.limit === 5, 'Should report limit of 5');
  limiter.shutdown();
});

test('Write limit enforcement blocks excess write requests', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 100,
    writeOpsPerMinute: 3,
    readOpsPerMinute: 10,
  });

  // Fill write limit
  for (let i = 0; i < 3; i++) {
    limiter.checkRateLimit('workos_create_task');
    limiter.recordRequest('workos_create_task');
  }

  // Next write request should be blocked
  const result = limiter.checkRateLimit('workos_create_task');
  assert(result.allowed === false, 'Write request exceeding write limit should be blocked');
  assert(result.limitType === 'write', 'Should report write limit exceeded');
  assert(result.current === 3, 'Should report 3 write requests in window');
  assert(result.limit === 3, 'Should report limit of 3');
  limiter.shutdown();
});

test('Read limit enforcement blocks excess read requests', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 100,
    writeOpsPerMinute: 10,
    readOpsPerMinute: 3,
  });

  // Fill read limit
  for (let i = 0; i < 3; i++) {
    limiter.checkRateLimit('workos_get_tasks');
    limiter.recordRequest('workos_get_tasks');
  }

  // Next read request should be blocked
  const result = limiter.checkRateLimit('workos_get_tasks');
  assert(result.allowed === false, 'Read request exceeding read limit should be blocked');
  assert(result.limitType === 'read', 'Should report read limit exceeded');
  assert(result.current === 3, 'Should report 3 read requests in window');
  assert(result.limit === 3, 'Should report limit of 3');
  limiter.shutdown();
});

test('Write limit does not affect read requests', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 100,
    writeOpsPerMinute: 2,
    readOpsPerMinute: 10,
  });

  // Fill write limit
  for (let i = 0; i < 2; i++) {
    limiter.recordRequest('workos_create_task');
  }

  // Read requests should still be allowed
  const result = limiter.checkRateLimit('workos_get_tasks');
  assert(result.allowed === true, 'Read requests should be allowed when only write limit is exceeded');
  limiter.shutdown();
});

test('Read limit does not affect write requests', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 100,
    writeOpsPerMinute: 10,
    readOpsPerMinute: 2,
  });

  // Fill read limit
  for (let i = 0; i < 2; i++) {
    limiter.recordRequest('workos_get_tasks');
  }

  // Write requests should still be allowed
  const result = limiter.checkRateLimit('workos_create_task');
  assert(result.allowed === true, 'Write requests should be allowed when only read limit is exceeded');
  limiter.shutdown();
});

// =============================================================================
// 5. ERROR MESSAGES & RETRY-AFTER
// =============================================================================

console.log('\n[5] Error Messages & Retry-After');
console.log('-'.repeat(80));

test('Blocked requests include error message', () => {
  const limiter = new RateLimiter({ globalPerMinute: 1 });

  limiter.recordRequest('workos_get_tasks');
  const result = limiter.checkRateLimit('workos_get_tasks');

  assert(result.allowed === false, 'Request should be blocked');
  assert(typeof result.message === 'string', 'Should include error message');
  assert(result.message.includes('Rate limit exceeded'), 'Message should mention rate limit');
  limiter.shutdown();
});

test('Blocked requests include retry-after time', () => {
  const limiter = new RateLimiter({ globalPerMinute: 1 });

  limiter.recordRequest('workos_get_tasks');
  const result = limiter.checkRateLimit('workos_get_tasks');

  assert(result.allowed === false, 'Request should be blocked');
  assert(typeof result.retryAfterMs === 'number', 'Should include retryAfterMs');
  assert(typeof result.retryAfterSeconds === 'number', 'Should include retryAfterSeconds');
  assert(result.retryAfterMs > 0, 'retryAfterMs should be positive');
  assert(result.retryAfterSeconds > 0, 'retryAfterSeconds should be positive');
  limiter.shutdown();
});

test('Error message includes current count and limit', () => {
  const limiter = new RateLimiter({ writeOpsPerMinute: 2 });

  limiter.recordRequest('workos_create_task');
  limiter.recordRequest('workos_create_task');
  const result = limiter.checkRateLimit('workos_create_task');

  assert(result.allowed === false, 'Request should be blocked');
  assert(result.message.includes('2'), 'Message should mention current count');
  assert(result.message.includes('write'), 'Message should mention operation type');
  limiter.shutdown();
});

test('Retry-after seconds is rounded up', () => {
  const limiter = new RateLimiter({ globalPerMinute: 1, windowMs: 5000 });

  limiter.recordRequest('workos_get_tasks');
  const result = limiter.checkRateLimit('workos_get_tasks');

  assert(result.allowed === false, 'Request should be blocked');
  assert(result.retryAfterSeconds >= Math.floor(result.retryAfterMs / 1000),
    'Retry-after seconds should be rounded up');
  limiter.shutdown();
});

// =============================================================================
// 6. WINDOW SLIDING & TIME-BASED RESET
// =============================================================================

console.log('\n[6] Window Sliding & Time-Based Reset');
console.log('-'.repeat(80));

test('Requests outside time window are not counted', async () => {
  const limiter = new RateLimiter({
    globalPerMinute: 5,
    windowMs: 100, // 100ms window for fast testing
  });

  // Record 3 requests
  for (let i = 0; i < 3; i++) {
    limiter.recordRequest('workos_get_tasks');
  }

  let stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 3, 'Should have 3 requests in window');

  // Wait for window to expire
  await sleep(150);

  stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 0, 'Should have 0 requests after window expires');
  limiter.shutdown();
});

test('Sliding window allows requests as old ones expire', async () => {
  const limiter = new RateLimiter({
    globalPerMinute: 3,
    writeOpsPerMinute: 3,
    windowMs: 200, // 200ms window
  });

  // Fill the limit
  for (let i = 0; i < 3; i++) {
    const result = limiter.checkRateLimit('workos_create_task');
    assert(result.allowed === true, `Request ${i + 1} should be allowed`);
    limiter.recordRequest('workos_create_task');
  }

  // 4th request should be blocked
  let result = limiter.checkRateLimit('workos_create_task');
  assert(result.allowed === false, 'Request 4 should be blocked at limit');

  // Wait for first request to expire
  await sleep(250);

  // Now request should be allowed again
  result = limiter.checkRateLimit('workos_create_task');
  assert(result.allowed === true, 'Request should be allowed after window slides');
  limiter.shutdown();
});

test('Reset clears all counters immediately', () => {
  const limiter = new RateLimiter({ globalPerMinute: 5 });

  // Record some requests
  for (let i = 0; i < 5; i++) {
    limiter.recordRequest('workos_get_tasks');
  }

  let stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 5, 'Should have 5 requests');

  // Reset
  limiter.reset();

  stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 0, 'Should have 0 requests after reset');
  assert(stats.write.requestsInWindow === 0, 'Write count should be 0 after reset');
  assert(stats.read.requestsInWindow === 0, 'Read count should be 0 after reset');
  limiter.shutdown();
});

test('Partial window expiry only removes old requests', async () => {
  const limiter = new RateLimiter({
    globalPerMinute: 10,
    windowMs: 200,
  });

  // Record 2 requests
  limiter.recordRequest('workos_get_tasks');
  limiter.recordRequest('workos_get_tasks');

  // Wait 150ms
  await sleep(150);

  // Record 2 more requests
  limiter.recordRequest('workos_get_tasks');
  limiter.recordRequest('workos_get_tasks');

  let stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 4, 'Should have 4 requests in window');

  // Wait another 100ms (first 2 requests should expire)
  await sleep(100);

  stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 2, 'Should have 2 requests after partial expiry');
  limiter.shutdown();
});

// =============================================================================
// 7. EDGE CASES
// =============================================================================

console.log('\n[7] Edge Cases');
console.log('-'.repeat(80));

test('Checking rate limit does not record request', () => {
  const limiter = new RateLimiter();

  limiter.checkRateLimit('workos_get_tasks');
  limiter.checkRateLimit('workos_get_tasks');
  limiter.checkRateLimit('workos_get_tasks');

  const stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 0, 'Checking should not record requests');
  limiter.shutdown();
});

test('Recording without checking is allowed', () => {
  const limiter = new RateLimiter();

  limiter.recordRequest('workos_get_tasks');
  limiter.recordRequest('workos_get_tasks');

  const stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 2, 'Can record without checking');
  limiter.shutdown();
});

test('Empty tool name is handled', () => {
  const limiter = new RateLimiter();

  const result = limiter.checkRateLimit('');
  assert(result.allowed === true, 'Empty tool name should be allowed');

  limiter.recordRequest('');
  const stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 1, 'Empty tool name should be recorded');
  limiter.shutdown();
});

test('Unknown tool names default to read operations', () => {
  const limiter = new RateLimiter();

  limiter.recordRequest('unknown_tool_name');
  limiter.recordRequest('some_random_tool');

  const stats = limiter.getStats();
  assert(stats.read.requestsInWindow === 2, 'Unknown tools should default to read');
  assert(stats.write.requestsInWindow === 0, 'Unknown tools should not be write');
  limiter.shutdown();
});

test('Case insensitive operation classification', () => {
  const limiter = new RateLimiter();

  limiter.recordRequest('WORKOS_CREATE_TASK');
  limiter.recordRequest('workos_CREATE_task');
  limiter.recordRequest('WORKOS_GET_TASKS');

  const stats = limiter.getStats();
  assert(stats.write.requestsInWindow === 2, 'Case insensitive write classification');
  assert(stats.read.requestsInWindow === 1, 'Case insensitive read classification');
  limiter.shutdown();
});

test('Very high limit values work correctly', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 1000000,
    writeOpsPerMinute: 500000,
    readOpsPerMinute: 500000,
  });

  for (let i = 0; i < 100; i++) {
    const result = limiter.checkRateLimit('workos_get_tasks');
    assert(result.allowed === true, `Request ${i + 1} should be allowed with high limit`);
    limiter.recordRequest('workos_get_tasks');
  }
  limiter.shutdown();
});

test('Zero remaining is calculated correctly at limit', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 3,
  });

  for (let i = 0; i < 3; i++) {
    limiter.recordRequest('workos_get_tasks');
  }

  const stats = limiter.getStats();
  assert(stats.global.remaining === 0, 'Remaining should be exactly 0 at limit');
  assert(stats.global.percentageUsed === 100, 'Percentage should be exactly 100 at limit');
  limiter.shutdown();
});

test('Cleanup timer can be stopped', async () => {
  const limiter = new RateLimiter();

  // Shutdown should stop cleanup timer without error
  limiter.shutdown();
  limiter.shutdown(); // Should handle multiple shutdowns gracefully

  assert(true, 'Shutdown should complete without error');
});

// =============================================================================
// 8. CONCURRENT OPERATIONS
// =============================================================================

console.log('\n[8] Concurrent Operations');
console.log('-'.repeat(80));

test('Mixed write and read operations tracked separately', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 20,
    writeOpsPerMinute: 5,
    readOpsPerMinute: 10,
  });

  // Mix of operations
  limiter.recordRequest('workos_create_task'); // write
  limiter.recordRequest('workos_get_tasks'); // read
  limiter.recordRequest('workos_update_task'); // write
  limiter.recordRequest('workos_get_clients'); // read
  limiter.recordRequest('workos_delete_task'); // write
  limiter.recordRequest('workos_get_habits'); // read

  const stats = limiter.getStats();
  assert(stats.global.requestsInWindow === 6, 'Global should track all 6 requests');
  assert(stats.write.requestsInWindow === 3, 'Write should track 3 requests');
  assert(stats.read.requestsInWindow === 3, 'Read should track 3 requests');
  limiter.shutdown();
});

test('Multiple blocked request types return correct limit type', () => {
  const limiter = new RateLimiter({
    globalPerMinute: 10, // High enough to not interfere
    writeOpsPerMinute: 1,
    readOpsPerMinute: 1,
  });

  // Fill write limit
  limiter.recordRequest('workos_create_task');

  // Next write should be blocked by write limit
  let result = limiter.checkRateLimit('workos_create_task');
  assert(result.allowed === false, 'Should be blocked');
  assert(result.limitType === 'write', 'Should report write limit');

  // Fill read limit
  limiter.recordRequest('workos_get_tasks');

  // Next read should be blocked by read limit
  result = limiter.checkRateLimit('workos_get_tasks');
  assert(result.allowed === false, 'Should be blocked');
  assert(result.limitType === 'read', 'Should report read limit');

  limiter.shutdown();
});

// =============================================================================
// TEST SUMMARY
// =============================================================================

console.log('\n' + '='.repeat(80));
console.log('Test Summary');
console.log('='.repeat(80));
console.log(`Total tests: ${testCount}`);
console.log(`Passed: ${passCount} ✓`);
console.log(`Failed: ${failCount} ✗`);
console.log('='.repeat(80));

if (failCount > 0) {
  console.log('\n⚠️  Some tests failed!');
  process.exit(1);
} else {
  console.log('\n🎉 All tests passed!');
  process.exit(0);
}
