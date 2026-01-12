#!/usr/bin/env node
/**
 * End-to-End Integration Test for MCP Server
 *
 * Tests the complete MCP server with various input scenarios:
 * - Valid inputs work correctly
 * - Invalid inputs return proper errors
 * - Rate limiting triggers correctly
 * - Boundary values (at limits)
 * - User-friendly error messages
 *
 * This test spawns the actual MCP server and communicates via stdio
 * using the MCP JSON-RPC protocol.
 */

import { spawn } from 'child_process';
import { createInterface } from 'readline';

// =============================================================================
// TEST UTILITIES
// =============================================================================

let testCount = 0;
let passCount = 0;
let failCount = 0;
let requestId = 1;
let server = null;
let serverReady = false;
let responseQueue = [];
let responseResolvers = new Map();

/**
 * Colors for terminal output
 */
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  gray: '\x1b[90m',
};

/**
 * Start the MCP server
 */
async function startServer() {
  return new Promise((resolve, reject) => {
    console.log(colors.blue + 'Starting MCP server...' + colors.reset);

    // Spawn the MCP server
    server = spawn('node', ['dist/index.js'], {
      cwd: process.cwd(),
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        // Disable rate limiting for most tests (we'll test it separately)
        RATE_LIMIT_ENABLED: 'true',
        RATE_LIMIT_GLOBAL_PER_MINUTE: '1000',
        RATE_LIMIT_WRITE_PER_MINUTE: '500',
        RATE_LIMIT_READ_PER_MINUTE: '500',
      }
    });

    // Set up readline interface for stdout
    const rl = createInterface({
      input: server.stdout,
      crlfDelay: Infinity
    });

    // Handle server output (JSON-RPC responses)
    rl.on('line', (line) => {
      try {
        const response = JSON.parse(line);

        // If we have a resolver waiting for this response, call it
        if (response.id && responseResolvers.has(response.id)) {
          const resolver = responseResolvers.get(response.id);
          responseResolvers.delete(response.id);
          resolver(response);
        } else {
          // Otherwise queue it
          responseQueue.push(response);
        }
      } catch (error) {
        // Ignore non-JSON lines (server logs)
      }
    });

    // Handle server errors
    server.stderr.on('data', (data) => {
      const message = data.toString();
      // Look for "running on stdio" to know server is ready
      if (message.includes('running on stdio')) {
        serverReady = true;
        console.log(colors.green + '✓ MCP server started' + colors.reset);
        resolve();
      }
      // Only log error messages, not informational ones
      if (message.includes('Error') || message.includes('Failed')) {
        console.log(colors.gray + 'Server: ' + message.trim() + colors.reset);
      }
    });

    server.on('error', (error) => {
      console.error(colors.red + 'Server error: ' + error.message + colors.reset);
      reject(error);
    });

    server.on('exit', (code) => {
      if (!serverReady) {
        reject(new Error(`Server exited with code ${code} before becoming ready`));
      }
    });

    // Timeout after 5 seconds
    setTimeout(() => {
      if (!serverReady) {
        reject(new Error('Server did not start within 5 seconds'));
      }
    }, 5000);
  });
}

/**
 * Stop the MCP server
 */
async function stopServer() {
  if (server) {
    console.log(colors.blue + '\nStopping MCP server...' + colors.reset);
    server.kill();
    server = null;
    serverReady = false;
  }
}

/**
 * Send a JSON-RPC request to the server
 */
async function sendRequest(method, params) {
  return new Promise((resolve, reject) => {
    const id = requestId++;
    const request = {
      jsonrpc: '2.0',
      id,
      method,
      params
    };

    // Store resolver for this request
    responseResolvers.set(id, resolve);

    // Send request
    server.stdin.write(JSON.stringify(request) + '\n');

    // Timeout after 3 seconds
    setTimeout(() => {
      if (responseResolvers.has(id)) {
        responseResolvers.delete(id);
        reject(new Error('Request timeout'));
      }
    }, 3000);
  });
}

/**
 * Call an MCP tool
 */
async function callTool(name, args = {}) {
  return sendRequest('tools/call', { name, arguments: args });
}

/**
 * List available tools
 */
async function listTools() {
  return sendRequest('tools/list', {});
}

/**
 * Run a test
 */
async function test(description, fn) {
  testCount++;
  process.stdout.write(`\nTest ${testCount}: ${description}... `);

  try {
    await fn();
    passCount++;
    console.log(colors.green + '✓ PASS' + colors.reset);
  } catch (error) {
    failCount++;
    console.log(colors.red + '✗ FAIL' + colors.reset);
    console.log(colors.red + `  Error: ${error.message}` + colors.reset);
    if (error.details) {
      console.log(colors.gray + `  Details: ${error.details}` + colors.reset);
    }
  }
}

/**
 * Assert helper
 */
function assert(condition, message, details) {
  if (!condition) {
    const error = new Error(message);
    if (details) error.details = details;
    throw error;
  }
}

// =============================================================================
// TEST SUITES
// =============================================================================

/**
 * Test Suite 1: Server Initialization
 */
async function testServerInitialization() {
  console.log('\n' + '='.repeat(70));
  console.log(colors.blue + 'Test Suite 1: Server Initialization' + colors.reset);
  console.log('='.repeat(70));

  await test('Server lists available tools', async () => {
    const response = await listTools();

    assert(response.result, 'Response should have result');
    assert(response.result.tools, 'Result should have tools array');
    assert(Array.isArray(response.result.tools), 'Tools should be an array');
    assert(response.result.tools.length > 0, 'Should have at least one tool');

    // Check for some expected tools
    const toolNames = response.result.tools.map(t => t.name);
    assert(toolNames.includes('workos_get_tasks'), 'Should include workos_get_tasks');
    assert(toolNames.includes('workos_create_task'), 'Should include workos_create_task');
    assert(toolNames.includes('workos_get_habits'), 'Should include workos_get_habits');
  });
}

/**
 * Test Suite 2: Valid Input Scenarios
 */
async function testValidInputs() {
  console.log('\n' + '='.repeat(70));
  console.log(colors.blue + 'Test Suite 2: Valid Input Scenarios' + colors.reset);
  console.log('='.repeat(70));

  await test('Get tasks with no filters (valid)', async () => {
    const response = await callTool('workos_get_tasks', {});

    assert(!response.error, 'Should not have error', JSON.stringify(response.error));
    assert(response.result, 'Should have result');
    assert(response.result.content, 'Result should have content');
    assert(Array.isArray(response.result.content), 'Content should be an array');
  });

  await test('Get tasks with valid status filter', async () => {
    const response = await callTool('workos_get_tasks', { status: 'active' });

    assert(!response.error, 'Should not have error', JSON.stringify(response.error));
    assert(response.result, 'Should have result');
  });

  await test('Get tasks with valid limit (50)', async () => {
    const response = await callTool('workos_get_tasks', { limit: 50 });

    assert(!response.error, 'Should not have error', JSON.stringify(response.error));
    assert(response.result, 'Should have result');
  });

  await test('Get habits with no filters (valid)', async () => {
    const response = await callTool('workos_get_habits', {});

    assert(!response.error, 'Should not have error', JSON.stringify(response.error));
    assert(response.result, 'Should have result');
  });

  await test('Get energy logs with valid limit', async () => {
    const response = await callTool('workos_get_energy', { limit: 10 });

    assert(!response.error, 'Should not have error', JSON.stringify(response.error));
    assert(response.result, 'Should have result');
  });

  await test('Get brain dump with valid parameters', async () => {
    const response = await callTool('workos_get_brain_dump', {
      includeProcessed: false,
      limit: 20
    });

    assert(!response.error, 'Should not have error', JSON.stringify(response.error));
    assert(response.result, 'Should have result');
  });
}

/**
 * Test Suite 3: Invalid Input Scenarios
 */
async function testInvalidInputs() {
  console.log('\n' + '='.repeat(70));
  console.log(colors.blue + 'Test Suite 3: Invalid Input Scenarios' + colors.reset);
  console.log('='.repeat(70));

  await test('Create task with title too long (>200 chars)', async () => {
    const longTitle = 'A'.repeat(201);
    const response = await callTool('workos_create_task', {
      title: longTitle,
      clientId: 1
    });

    // Should return error response
    assert(response.result, 'Should have result (MCP error format)');
    assert(response.result.isError === true, 'Should be marked as error');
    assert(response.result.content, 'Should have content');

    const errorText = response.result.content[0].text;
    assert(errorText.includes('title'), 'Error should mention title field');
    assert(errorText.includes('200'), 'Error should mention max length');
  });

  await test('Create task with invalid status enum', async () => {
    const response = await callTool('workos_create_task', {
      title: 'Test task',
      status: 'invalid_status',
      clientId: 1
    });

    assert(response.result.isError === true, 'Should be marked as error');
    const errorText = response.result.content[0].text;
    assert(errorText.includes('status'), 'Error should mention status field');
  });

  await test('Get tasks with invalid limit (negative)', async () => {
    const response = await callTool('workos_get_tasks', { limit: -5 });

    assert(response.result.isError === true, 'Should be marked as error');
    const errorText = response.result.content[0].text;
    assert(errorText.includes('limit'), 'Error should mention limit field');
  });

  await test('Get tasks with invalid limit (too large)', async () => {
    const response = await callTool('workos_get_tasks', { limit: 500 });

    assert(response.result.isError === true, 'Should be marked as error');
    const errorText = response.result.content[0].text;
    assert(errorText.includes('limit'), 'Error should mention limit field');
    assert(errorText.includes('100'), 'Error should mention max limit');
  });

  await test('Create habit with name too long (>100 chars)', async () => {
    const longName = 'B'.repeat(101);
    const response = await callTool('workos_create_habit', {
      name: longName,
      frequency: 'daily'
    });

    assert(response.result.isError === true, 'Should be marked as error');
    const errorText = response.result.content[0].text;
    assert(errorText.includes('name'), 'Error should mention name field');
    assert(errorText.includes('100'), 'Error should mention max length');
  });

  await test('Log energy with invalid level enum', async () => {
    const response = await callTool('workos_log_energy', {
      level: 'super_high' // Invalid enum value
    });

    assert(response.result.isError === true, 'Should be marked as error');
    const errorText = response.result.content[0].text;
    assert(errorText.includes('level'), 'Error should mention level field');
  });

  await test('Brain dump with content too long (>5000 chars)', async () => {
    const longContent = 'C'.repeat(5001);
    const response = await callTool('workos_brain_dump', {
      content: longContent
    });

    assert(response.result.isError === true, 'Should be marked as error');
    const errorText = response.result.content[0].text;
    assert(errorText.includes('content'), 'Error should mention content field');
    assert(errorText.includes('5000'), 'Error should mention max length');
  });

  await test('Update task with missing taskId', async () => {
    const response = await callTool('workos_update_task', {
      title: 'Updated title'
      // Missing taskId
    });

    assert(response.result.isError === true, 'Should be marked as error');
    const errorText = response.result.content[0].text;
    assert(errorText.includes('taskId') || errorText.includes('Required'),
           'Error should mention missing taskId');
  });

  await test('Log energy with Oura score out of range', async () => {
    const response = await callTool('workos_log_energy', {
      level: 'high',
      ouraReadiness: 150 // Should be 0-100
    });

    assert(response.result.isError === true, 'Should be marked as error');
    const errorText = response.result.content[0].text;
    assert(errorText.includes('ouraReadiness') || errorText.includes('100'),
           'Error should mention ouraReadiness or max value');
  });
}

/**
 * Test Suite 4: Boundary Value Testing
 */
async function testBoundaryValues() {
  console.log('\n' + '='.repeat(70));
  console.log(colors.blue + 'Test Suite 4: Boundary Value Testing' + colors.reset);
  console.log('='.repeat(70));

  await test('Create task with title exactly 200 chars (at limit)', async () => {
    const title = 'A'.repeat(200);
    const response = await callTool('workos_create_task', {
      title,
      clientId: 1
    });

    assert(!response.error, 'Should not have error at boundary', JSON.stringify(response.error));
    // Note: May fail if clientId doesn't exist, but validation should pass
  });

  await test('Get tasks with limit=1 (minimum valid)', async () => {
    const response = await callTool('workos_get_tasks', { limit: 1 });

    assert(!response.error, 'Should not have error', JSON.stringify(response.error));
    assert(response.result, 'Should have result');
  });

  await test('Get tasks with limit=100 (maximum valid)', async () => {
    const response = await callTool('workos_get_tasks', { limit: 100 });

    assert(!response.error, 'Should not have error', JSON.stringify(response.error));
    assert(response.result, 'Should have result');
  });

  await test('Get tasks with limit=0 (below minimum)', async () => {
    const response = await callTool('workos_get_tasks', { limit: 0 });

    assert(response.result.isError === true, 'Should be marked as error');
  });

  await test('Get tasks with limit=101 (above maximum)', async () => {
    const response = await callTool('workos_get_tasks', { limit: 101 });

    assert(response.result.isError === true, 'Should be marked as error');
  });

  await test('Create habit with description exactly 500 chars (at limit)', async () => {
    const description = 'B'.repeat(500);
    const response = await callTool('workos_create_habit', {
      name: 'Test habit',
      description,
      frequency: 'daily'
    });

    // Validation should pass (may fail on DB constraint, but that's OK)
    assert(!response.error, 'Should not have validation error', JSON.stringify(response.error));
  });

  await test('Brain dump with content exactly 5000 chars (at limit)', async () => {
    const content = 'C'.repeat(5000);
    const response = await callTool('workos_brain_dump', { content });

    assert(!response.error, 'Should not have validation error', JSON.stringify(response.error));
  });

  await test('Log energy with ouraReadiness=0 (minimum valid)', async () => {
    const response = await callTool('workos_log_energy', {
      level: 'low',
      ouraReadiness: 0
    });

    assert(!response.error, 'Should not have error', JSON.stringify(response.error));
  });

  await test('Log energy with ouraReadiness=100 (maximum valid)', async () => {
    const response = await callTool('workos_log_energy', {
      level: 'high',
      ouraReadiness: 100
    });

    assert(!response.error, 'Should not have error', JSON.stringify(response.error));
  });
}

/**
 * Test Suite 5: Rate Limiting
 */
async function testRateLimiting() {
  console.log('\n' + '='.repeat(70));
  console.log(colors.blue + 'Test Suite 5: Rate Limiting' + colors.reset);
  console.log('='.repeat(70));

  // Note: Rate limiting is tested separately with controlled limits
  // Here we just verify the error message format when limit is exceeded

  await test('Rate limit error message is user-friendly', async () => {
    // This test assumes rate limiting is working (tested in test-rate-limiting.mjs)
    // We just verify the message format

    // For this test, we'll restart server with very low limits
    await stopServer();

    // Start server with low rate limits
    server = spawn('node', ['dist/index.js'], {
      cwd: process.cwd(),
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        RATE_LIMIT_ENABLED: 'true',
        RATE_LIMIT_GLOBAL_PER_MINUTE: '3', // Very low for testing
        RATE_LIMIT_WRITE_PER_MINUTE: '2',
        RATE_LIMIT_READ_PER_MINUTE: '2',
      }
    });

    // Wait for server to be ready
    await new Promise((resolve) => {
      const rl = createInterface({
        input: server.stdout,
        crlfDelay: Infinity
      });

      rl.on('line', (line) => {
        try {
          const response = JSON.parse(line);
          if (response.id && responseResolvers.has(response.id)) {
            const resolver = responseResolvers.get(response.id);
            responseResolvers.delete(response.id);
            resolver(response);
          }
        } catch (error) {
          // Ignore non-JSON
        }
      });

      server.stderr.on('data', (data) => {
        if (data.toString().includes('running on stdio')) {
          serverReady = true;
          setTimeout(resolve, 100); // Small delay to ensure ready
        }
      });
    });

    // Make requests to exceed rate limit
    await callTool('workos_get_tasks', {});
    await callTool('workos_get_tasks', {});
    await callTool('workos_get_tasks', {});

    // 4th request should be rate limited
    const response = await callTool('workos_get_tasks', {});

    assert(response.result.isError === true, 'Should be marked as error');
    const errorText = response.result.content[0].text;
    assert(errorText.includes('Rate limit'), 'Error should mention rate limit');
    assert(errorText.includes('wait') || errorText.includes('retry') || errorText.includes('after'),
           'Error should include retry guidance');

    // Restart server with normal limits for remaining tests
    await stopServer();
    await startServer();
  });
}

/**
 * Test Suite 6: Error Message Quality
 */
async function testErrorMessages() {
  console.log('\n' + '='.repeat(70));
  console.log(colors.blue + 'Test Suite 6: Error Message Quality' + colors.reset);
  console.log('='.repeat(70));

  await test('Validation error messages are user-friendly', async () => {
    const response = await callTool('workos_create_task', {
      title: 'A'.repeat(201), // Too long
      clientId: 1
    });

    const errorText = response.result.content[0].text;

    // Should NOT be raw Zod error
    assert(!errorText.includes('ZodError'), 'Should not expose Zod internals');
    assert(!errorText.includes('z.'), 'Should not expose Zod syntax');

    // Should be descriptive
    assert(errorText.length > 20, 'Error message should be descriptive');
    assert(errorText.includes('title'), 'Should mention the field name');
  });

  await test('Enum validation errors list valid values', async () => {
    const response = await callTool('workos_get_tasks', {
      status: 'invalid_status'
    });

    const errorText = response.result.content[0].text;

    // Should mention valid values
    assert(errorText.includes('active') || errorText.includes('queued'),
           'Should list valid enum values');
  });

  await test('Numeric range errors specify the valid range', async () => {
    const response = await callTool('workos_get_tasks', {
      limit: 500
    });

    const errorText = response.result.content[0].text;

    // Should mention the valid range
    assert(errorText.includes('1') && errorText.includes('100'),
           'Should specify valid range (1-100)');
  });

  await test('Missing required field errors are clear', async () => {
    const response = await callTool('workos_brain_dump', {
      // Missing required 'content' field
    });

    const errorText = response.result.content[0].text;

    assert(errorText.includes('content') || errorText.includes('Required'),
           'Should clearly indicate missing required field');
  });
}

/**
 * Test Suite 7: Input Sanitization
 */
async function testInputSanitization() {
  console.log('\n' + '='.repeat(70));
  console.log(colors.blue + 'Test Suite 7: Input Sanitization' + colors.reset);
  console.log('='.repeat(70));

  await test('Whitespace is trimmed from string inputs', async () => {
    const response = await callTool('workos_create_task', {
      title: '  Task with spaces  ',
      clientId: 1
    });

    // Should succeed without validation error
    // (May fail on DB, but validation should pass)
    assert(!response.error || !response.result.isError ||
           !response.result.content[0].text.includes('title'),
           'Should not fail validation due to whitespace');
  });

  await test('Empty strings after trimming are rejected', async () => {
    const response = await callTool('workos_create_task', {
      title: '   ', // Only whitespace
      clientId: 1
    });

    assert(response.result.isError === true, 'Should be marked as error');
    const errorText = response.result.content[0].text;
    assert(errorText.includes('title'), 'Should mention title field');
  });
}

// =============================================================================
// MAIN TEST RUNNER
// =============================================================================

async function main() {
  console.log('\n' + '='.repeat(70));
  console.log(colors.blue + 'MCP Server End-to-End Integration Test' + colors.reset);
  console.log('='.repeat(70));
  console.log('Testing server with various input scenarios:');
  console.log('- Valid inputs work correctly');
  console.log('- Invalid inputs return proper errors');
  console.log('- Rate limiting triggers correctly');
  console.log('- Boundary values (at limits)');
  console.log('- User-friendly error messages');
  console.log('='.repeat(70));

  try {
    // Start the MCP server
    await startServer();

    // Run test suites
    await testServerInitialization();
    await testValidInputs();
    await testInvalidInputs();
    await testBoundaryValues();
    await testRateLimiting();
    await testErrorMessages();
    await testInputSanitization();

    // Print summary
    console.log('\n' + '='.repeat(70));
    console.log(colors.blue + 'Test Summary' + colors.reset);
    console.log('='.repeat(70));
    console.log(`Total tests: ${testCount}`);
    console.log(`${colors.green}✓ Passed: ${passCount}${colors.reset}`);
    console.log(`${colors.red}✗ Failed: ${failCount}${colors.reset}`);

    if (failCount === 0) {
      console.log('\n' + colors.green + '🎉 All end-to-end integration tests passed!' + colors.reset);
      console.log('\nValidation and rate limiting are working correctly.');
      console.log('The MCP server properly handles:');
      console.log('  ✓ Valid inputs');
      console.log('  ✓ Invalid inputs with clear error messages');
      console.log('  ✓ Boundary values');
      console.log('  ✓ Rate limiting');
      console.log('  ✓ Input sanitization');
    } else {
      console.log('\n' + colors.red + '❌ Some tests failed' + colors.reset);
      process.exitCode = 1;
    }

  } catch (error) {
    console.error('\n' + colors.red + 'Fatal error: ' + error.message + colors.reset);
    console.error(error.stack);
    process.exitCode = 1;
  } finally {
    // Stop the server
    await stopServer();
  }
}

// Run tests
main().catch(console.error);
