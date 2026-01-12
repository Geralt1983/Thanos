#!/usr/bin/env node
// Simple test script to verify rate limiter functionality

import { RateLimiter, getRateLimiter, resetRateLimiter } from './dist/shared/rate-limiter.js';

console.log('='.repeat(80));
console.log('Rate Limiter Test Suite');
console.log('='.repeat(80));

// Test 1: Basic initialization
console.log('\n[Test 1] Rate limiter initialization...');
const limiter = new RateLimiter({
  enabled: true,
  globalPerMinute: 5,
  writeOpsPerMinute: 2,
  readOpsPerMinute: 3,
  windowMs: 60000,
  cleanupIntervalMs: 300000,
});
console.log('✓ Rate limiter initialized');

// Test 2: Get initial stats
console.log('\n[Test 2] Initial statistics...');
const initialStats = limiter.getStats();
console.log('Global:', initialStats.global);
console.log('Write:', initialStats.write);
console.log('Read:', initialStats.read);
console.log('✓ Statistics retrieved');

// Test 3: Allow requests under limit
console.log('\n[Test 3] Checking requests under limit...');
const writeCheck1 = limiter.checkRateLimit('workos_create_task');
console.log('Create task (write):', writeCheck1.allowed ? '✓ Allowed' : '✗ Blocked');

if (writeCheck1.allowed) {
  limiter.recordRequest('workos_create_task');
  console.log('✓ Request recorded');
}

const readCheck1 = limiter.checkRateLimit('workos_get_tasks');
console.log('Get tasks (read):', readCheck1.allowed ? '✓ Allowed' : '✗ Blocked');

if (readCheck1.allowed) {
  limiter.recordRequest('workos_get_tasks');
  console.log('✓ Request recorded');
}

// Test 4: Check stats after requests
console.log('\n[Test 4] Statistics after requests...');
const afterStats = limiter.getStats();
console.log('Global:', afterStats.global);
console.log('Write:', afterStats.write);
console.log('Read:', afterStats.read);

// Test 5: Exceed write limit
console.log('\n[Test 5] Testing write operation limit (max 2)...');
for (let i = 0; i < 3; i++) {
  const check = limiter.checkRateLimit('workos_create_task');
  console.log(`Request ${i + 1}:`, check.allowed ? '✓ Allowed' : '✗ Blocked');

  if (check.allowed) {
    limiter.recordRequest('workos_create_task');
  } else {
    console.log(`  Message: ${check.message}`);
    console.log(`  Retry after: ${check.retryAfterSeconds} seconds`);
  }
}

// Test 6: Exceed read limit
console.log('\n[Test 6] Testing read operation limit (max 3)...');
limiter.reset(); // Reset counters
for (let i = 0; i < 4; i++) {
  const check = limiter.checkRateLimit('workos_get_tasks');
  console.log(`Request ${i + 1}:`, check.allowed ? '✓ Allowed' : '✗ Blocked');

  if (check.allowed) {
    limiter.recordRequest('workos_get_tasks');
  } else {
    console.log(`  Message: ${check.message}`);
    console.log(`  Retry after: ${check.retryAfterSeconds} seconds`);
  }
}

// Test 7: Exceed global limit
console.log('\n[Test 7] Testing global limit (max 5)...');
limiter.reset(); // Reset counters
for (let i = 0; i < 6; i++) {
  const toolName = i % 2 === 0 ? 'workos_create_task' : 'workos_get_tasks';
  const check = limiter.checkRateLimit(toolName);
  console.log(`Request ${i + 1} (${toolName}):`, check.allowed ? '✓ Allowed' : '✗ Blocked');

  if (check.allowed) {
    limiter.recordRequest(toolName);
  } else {
    console.log(`  Limit type: ${check.limitType}`);
    console.log(`  Message: ${check.message}`);
  }
}

// Test 8: Operation classification
console.log('\n[Test 8] Testing operation classification...');
const writeTools = [
  'workos_create_task',
  'workos_update_task',
  'workos_delete_task',
  'workos_complete_task',
  'workos_promote_task',
  'workos_create_habit',
  'workos_log_energy',
  'workos_brain_dump',
];

const readTools = [
  'workos_get_tasks',
  'workos_get_clients',
  'workos_get_habits',
  'workos_habit_checkin',
  'workos_get_energy',
];

limiter.reset();
console.log('Write operations:');
writeTools.forEach(tool => {
  limiter.recordRequest(tool);
});

console.log('Read operations:');
readTools.forEach(tool => {
  limiter.recordRequest(tool);
});

const finalStats = limiter.getStats();
console.log(`Total write requests: ${finalStats.write.requestsInWindow}`);
console.log(`Total read requests: ${finalStats.read.requestsInWindow}`);
console.log(`Total global requests: ${finalStats.global.requestsInWindow}`);

if (finalStats.write.requestsInWindow === writeTools.length &&
    finalStats.read.requestsInWindow === readTools.length &&
    finalStats.global.requestsInWindow === writeTools.length + readTools.length) {
  console.log('✓ Operation classification working correctly');
} else {
  console.log('✗ Operation classification issue detected');
}

// Test 9: Singleton pattern
console.log('\n[Test 9] Testing singleton pattern...');
const singleton1 = getRateLimiter();
const singleton2 = getRateLimiter();
console.log('Same instance?', singleton1 === singleton2 ? '✓ Yes' : '✗ No');

resetRateLimiter();
const singleton3 = getRateLimiter();
console.log('New instance after reset?', singleton1 !== singleton3 ? '✓ Yes' : '✗ No');

// Cleanup
limiter.shutdown();
console.log('\n✓ Rate limiter shutdown');

console.log('\n' + '='.repeat(80));
console.log('All tests completed!');
console.log('='.repeat(80));
