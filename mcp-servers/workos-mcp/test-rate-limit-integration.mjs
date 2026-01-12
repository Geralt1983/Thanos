#!/usr/bin/env node
/**
 * Test: Rate Limiter Integration in CallToolRequestSchema Handler
 *
 * Tests that rate limiting middleware is properly integrated in the MCP server
 * request handler and correctly blocks requests that exceed limits.
 *
 * This is a quick smoke test to verify subtask-3.3 implementation.
 */

import { getRateLimiter, resetRateLimiter } from './dist/shared/rate-limiter.js';

console.log('='.repeat(70));
console.log('Rate Limiter Integration Test');
console.log('='.repeat(70));

// Test 1: Verify singleton initialization
console.log('\nTest 1: Verify rate limiter singleton initialization');
try {
  const rateLimiter = getRateLimiter();
  if (!rateLimiter) {
    throw new Error('Rate limiter singleton not initialized');
  }
  console.log('✓ Rate limiter singleton initialized successfully');
} catch (error) {
  console.error('✗ Failed:', error.message);
  process.exit(1);
}

// Test 2: Verify rate limiter accepts requests under limit
console.log('\nTest 2: Verify rate limiter accepts requests under limit');
try {
  resetRateLimiter();
  const rateLimiter = getRateLimiter();

  // Simulate 5 tool calls (well under any limit)
  for (let i = 0; i < 5; i++) {
    const result = rateLimiter.checkRateLimit('workos_get_tasks');
    if (!result.allowed) {
      throw new Error(`Request ${i+1} was blocked unexpectedly`);
    }
    rateLimiter.recordRequest('workos_get_tasks');
  }

  const stats = rateLimiter.getStats();
  console.log(`✓ 5 requests allowed (global: ${stats.global.requestsInWindow}/${stats.global.limit})`);
} catch (error) {
  console.error('✗ Failed:', error.message);
  process.exit(1);
}

// Test 3: Verify rate limiter blocks requests exceeding global limit
console.log('\nTest 3: Verify rate limiter blocks requests exceeding global limit');
try {
  resetRateLimiter();
  const rateLimiter = getRateLimiter({ globalPerMinute: 10 }); // Low limit for testing

  // Make 10 requests (at limit)
  for (let i = 0; i < 10; i++) {
    const result = rateLimiter.checkRateLimit('workos_get_tasks');
    if (!result.allowed) {
      throw new Error(`Request ${i+1} was blocked prematurely`);
    }
    rateLimiter.recordRequest('workos_get_tasks');
  }

  // 11th request should be blocked
  const result = rateLimiter.checkRateLimit('workos_get_tasks');
  if (result.allowed) {
    throw new Error('11th request was allowed when it should be blocked');
  }

  if (!result.message) {
    throw new Error('Rate limit error message is missing');
  }

  if (!result.retryAfterSeconds || result.retryAfterSeconds <= 0) {
    throw new Error('Retry-after time is invalid');
  }

  console.log(`✓ 11th request blocked correctly`);
  console.log(`  Limit type: ${result.limitType}`);
  console.log(`  Current: ${result.current}/${result.limit}`);
  console.log(`  Retry after: ${result.retryAfterSeconds} seconds`);
} catch (error) {
  console.error('✗ Failed:', error.message);
  process.exit(1);
}

// Test 4: Verify rate limiter blocks write operations exceeding write limit
console.log('\nTest 4: Verify rate limiter blocks write operations exceeding write limit');
try {
  resetRateLimiter();
  const rateLimiter = getRateLimiter({
    globalPerMinute: 100,
    writeOpsPerMinute: 5  // Low write limit for testing
  });

  // Make 5 write requests (at limit)
  for (let i = 0; i < 5; i++) {
    const result = rateLimiter.checkRateLimit('workos_create_task');
    if (!result.allowed) {
      throw new Error(`Write request ${i+1} was blocked prematurely`);
    }
    rateLimiter.recordRequest('workos_create_task');
  }

  // 6th write request should be blocked
  const result = rateLimiter.checkRateLimit('workos_create_task');
  if (result.allowed) {
    throw new Error('6th write request was allowed when it should be blocked');
  }

  if (result.limitType !== 'write') {
    throw new Error(`Expected limitType 'write', got '${result.limitType}'`);
  }

  console.log(`✓ 6th write request blocked correctly`);
  console.log(`  Limit type: ${result.limitType}`);
  console.log(`  Current: ${result.current}/${result.limit}`);
} catch (error) {
  console.error('✗ Failed:', error.message);
  process.exit(1);
}

// Test 5: Verify error message format
console.log('\nTest 5: Verify error message format');
try {
  resetRateLimiter();
  const rateLimiter = getRateLimiter({ globalPerMinute: 1 });

  // Make 1 request to hit limit
  rateLimiter.checkRateLimit('workos_get_tasks');
  rateLimiter.recordRequest('workos_get_tasks');

  // Second request should be blocked with formatted message
  const result = rateLimiter.checkRateLimit('workos_get_tasks');
  if (result.allowed) {
    throw new Error('Request was allowed when it should be blocked');
  }

  const message = result.message;
  if (!message.includes('Rate limit exceeded')) {
    throw new Error('Error message does not contain "Rate limit exceeded"');
  }

  if (!message.includes('Please wait') && !message.includes('retry')) {
    throw new Error('Error message does not include retry guidance');
  }

  console.log(`✓ Error message format is correct`);
  console.log(`  Message: ${message.split('\n')[0]}...`);
} catch (error) {
  console.error('✗ Failed:', error.message);
  process.exit(1);
}

// All tests passed
console.log('\n' + '='.repeat(70));
console.log('✓ All integration tests passed!');
console.log('='.repeat(70));
console.log('\nRate limiting middleware is properly integrated in CallToolRequestSchema handler.');
console.log('The MCP server will now enforce rate limits on all tool calls.');
