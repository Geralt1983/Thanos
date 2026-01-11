#!/usr/bin/env node
/**
 * Smoke test for task domain tools
 * Verifies that all 11 task handlers are callable and return proper response format
 */

import { getDb } from './dist/shared/db.js';
import { taskTools, handleTaskTool } from './dist/domains/tasks/index.js';

console.log('='.repeat(80));
console.log('TASK DOMAIN SMOKE TEST');
console.log('='.repeat(80));
console.log();

// =============================================================================
// TEST 1: Verify all tools are exported
// =============================================================================

console.log('TEST 1: Verify tool definitions');
console.log('-'.repeat(80));

const expectedTools = [
  'workos_get_today_metrics',
  'workos_get_tasks',
  'workos_get_clients',
  'workos_create_task',
  'workos_complete_task',
  'workos_promote_task',
  'workos_get_streak',
  'workos_get_client_memory',
  'workos_daily_summary',
  'workos_update_task',
  'workos_delete_task',
];

const toolNames = taskTools.map(t => t.name);
console.log(`Expected tools: ${expectedTools.length}`);
console.log(`Exported tools: ${toolNames.length}`);

let allToolsPresent = true;
for (const toolName of expectedTools) {
  const found = toolNames.includes(toolName);
  console.log(`  ${found ? '✓' : '✗'} ${toolName}`);
  if (!found) allToolsPresent = false;
}

console.log();
console.log(`Result: ${allToolsPresent ? '✓ PASS' : '✗ FAIL'} - All tools ${allToolsPresent ? 'present' : 'missing'}`);
console.log();

// =============================================================================
// TEST 2: Verify router handles all tools
// =============================================================================

console.log('TEST 2: Verify router routing');
console.log('-'.repeat(80));

let db;
try {
  db = getDb();
  console.log('✓ Database connection established');
} catch (error) {
  console.error('✗ Database connection failed:', error.message);
  process.exit(1);
}

// Test read-only tools that shouldn't modify data
const readOnlyTests = [
  { name: 'workos_get_today_metrics', args: {} },
  { name: 'workos_get_tasks', args: { status: 'active', limit: 1 } },
  { name: 'workos_get_clients', args: {} },
  { name: 'workos_get_streak', args: {} },
  { name: 'workos_daily_summary', args: {} },
];

let routerTests = 0;
let routerPassed = 0;

for (const test of readOnlyTests) {
  routerTests++;
  try {
    const result = await handleTaskTool(test.name, test.args, db);

    // Verify response format
    if (result && result.content && Array.isArray(result.content)) {
      console.log(`  ✓ ${test.name} - returned valid response`);
      routerPassed++;
    } else {
      console.log(`  ✗ ${test.name} - invalid response format`);
      console.log(`    Response:`, result);
    }
  } catch (error) {
    console.log(`  ✗ ${test.name} - threw error: ${error.message}`);
  }
}

// Test unknown tool
routerTests++;
try {
  const result = await handleTaskTool('workos_unknown_tool', {}, db);
  if (result && result.content && result.content[0]?.text?.includes('Unknown task tool')) {
    console.log(`  ✓ Unknown tool - properly rejected`);
    routerPassed++;
  } else {
    console.log(`  ✗ Unknown tool - unexpected response`);
  }
} catch (error) {
  console.log(`  ✗ Unknown tool - threw error: ${error.message}`);
}

console.log();
console.log(`Result: ${routerPassed === routerTests ? '✓ PASS' : '⚠ PARTIAL'} - ${routerPassed}/${routerTests} router tests passed`);
console.log();

// =============================================================================
// SUMMARY
// =============================================================================

console.log('='.repeat(80));
console.log('SUMMARY');
console.log('='.repeat(80));

const allPassed = allToolsPresent && (routerPassed === routerTests);

console.log(`Tool Definitions: ${allToolsPresent ? '✓ PASS' : '✗ FAIL'}`);
console.log(`Router Routing: ${routerPassed === routerTests ? '✓ PASS' : '⚠ PARTIAL'} (${routerPassed}/${routerTests})`);
console.log();
console.log(`Overall: ${allPassed ? '✓ ALL TESTS PASSED' : '⚠ SOME TESTS FAILED'}`);
console.log();

process.exit(allPassed ? 0 : 1);
