#!/usr/bin/env node
/**
 * Smoke test for habit domain tools
 * Verifies that all 7 habit handlers are callable and return proper response format
 */

import { getDb } from './dist/shared/db.js';
import { habitTools, handleHabitTool } from './dist/domains/habits/index.js';

console.log('='.repeat(80));
console.log('HABIT DOMAIN SMOKE TEST');
console.log('='.repeat(80));
console.log();

// =============================================================================
// TEST 1: Verify all tools are exported
// =============================================================================

console.log('TEST 1: Verify tool definitions');
console.log('-'.repeat(80));

const expectedTools = [
  'workos_get_habits',
  'workos_create_habit',
  'workos_complete_habit',
  'workos_get_habit_streaks',
  'workos_habit_checkin',
  'workos_habit_dashboard',
  'workos_recalculate_streaks',
];

const toolNames = habitTools.map(t => t.name);
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
  { name: 'workos_get_habits', args: {} },
  { name: 'workos_get_habit_streaks', args: {} },
  { name: 'workos_habit_checkin', args: { timeOfDay: 'morning' } },
  { name: 'workos_habit_dashboard', args: { format: 'text' } },
];

let routerTests = 0;
let routerPassed = 0;

for (const test of readOnlyTests) {
  routerTests++;
  try {
    const result = await handleHabitTool(test.name, test.args, db);

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
  const result = await handleHabitTool('workos_unknown_habit', {}, db);
  if (result && result.content && result.content[0]?.text?.includes('Unknown habit tool')) {
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
