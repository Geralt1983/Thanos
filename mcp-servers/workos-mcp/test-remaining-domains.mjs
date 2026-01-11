#!/usr/bin/env node
/**
 * Smoke test for remaining domain tools (energy, brain-dump, personal-tasks)
 * Verifies that all 6 remaining handlers are callable and return proper response format
 */

import { getDb } from './dist/shared/db.js';
import { energyTools, handleEnergyTool } from './dist/domains/energy/index.js';
import { brainDumpTools, handleBrainDumpTool } from './dist/domains/brain-dump/index.js';
import { personalTasksTools, handlePersonalTasksTool } from './dist/domains/personal-tasks/index.js';

console.log('='.repeat(80));
console.log('REMAINING DOMAINS SMOKE TEST');
console.log('Energy (2 tools) + Brain Dump (3 tools) + Personal Tasks (1 tool) = 6 total');
console.log('='.repeat(80));
console.log();

// =============================================================================
// TEST 1: Verify all tools are exported
// =============================================================================

console.log('TEST 1: Verify tool definitions');
console.log('-'.repeat(80));

const expectedEnergyTools = [
  'workos_log_energy',
  'workos_get_energy',
];

const expectedBrainDumpTools = [
  'workos_brain_dump',
  'workos_get_brain_dump',
  'workos_process_brain_dump',
];

const expectedPersonalTasksTools = [
  'workos_get_personal_tasks',
];

const energyToolNames = energyTools.map(t => t.name);
const brainDumpToolNames = brainDumpTools.map(t => t.name);
const personalTasksToolNames = personalTasksTools.map(t => t.name);

console.log('\nEnergy Domain:');
console.log(`  Expected tools: ${expectedEnergyTools.length}`);
console.log(`  Exported tools: ${energyToolNames.length}`);

let allEnergyToolsPresent = true;
for (const toolName of expectedEnergyTools) {
  const found = energyToolNames.includes(toolName);
  console.log(`    ${found ? '✓' : '✗'} ${toolName}`);
  if (!found) allEnergyToolsPresent = false;
}

console.log('\nBrain Dump Domain:');
console.log(`  Expected tools: ${expectedBrainDumpTools.length}`);
console.log(`  Exported tools: ${brainDumpToolNames.length}`);

let allBrainDumpToolsPresent = true;
for (const toolName of expectedBrainDumpTools) {
  const found = brainDumpToolNames.includes(toolName);
  console.log(`    ${found ? '✓' : '✗'} ${toolName}`);
  if (!found) allBrainDumpToolsPresent = false;
}

console.log('\nPersonal Tasks Domain:');
console.log(`  Expected tools: ${expectedPersonalTasksTools.length}`);
console.log(`  Exported tools: ${personalTasksToolNames.length}`);

let allPersonalTasksToolsPresent = true;
for (const toolName of expectedPersonalTasksTools) {
  const found = personalTasksToolNames.includes(toolName);
  console.log(`    ${found ? '✓' : '✗'} ${toolName}`);
  if (!found) allPersonalTasksToolsPresent = false;
}

const allToolsPresent = allEnergyToolsPresent && allBrainDumpToolsPresent && allPersonalTasksToolsPresent;

console.log();
console.log(`Result: ${allToolsPresent ? '✓ PASS' : '✗ FAIL'} - All tools ${allToolsPresent ? 'present' : 'missing'}`);
console.log();

// =============================================================================
// TEST 2: Verify routers handle all tools
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
  // Energy domain
  { domain: 'energy', handler: handleEnergyTool, name: 'workos_get_energy', args: { limit: 5 } },

  // Brain dump domain
  { domain: 'brain-dump', handler: handleBrainDumpTool, name: 'workos_get_brain_dump', args: { limit: 5 } },

  // Personal tasks domain
  { domain: 'personal-tasks', handler: handlePersonalTasksTool, name: 'workos_get_personal_tasks', args: { status: 'active', limit: 5 } },
];

let routerTests = 0;
let routerPassed = 0;

console.log('\nRead-only tool tests:');
for (const test of readOnlyTests) {
  routerTests++;
  try {
    const result = await test.handler(test.name, test.args, db);

    // Verify response format
    if (result && result.content && Array.isArray(result.content)) {
      console.log(`  ✓ ${test.name} (${test.domain}) - returned valid response`);
      routerPassed++;
    } else {
      console.log(`  ✗ ${test.name} (${test.domain}) - invalid response format`);
      console.log(`    Response:`, result);
    }
  } catch (error) {
    console.log(`  ✗ ${test.name} (${test.domain}) - threw error: ${error.message}`);
  }
}

// Test unknown tools for each domain
const unknownToolTests = [
  { domain: 'energy', handler: handleEnergyTool, name: 'workos_unknown_energy', errorText: 'Unknown energy tool' },
  { domain: 'brain-dump', handler: handleBrainDumpTool, name: 'workos_unknown_brain_dump', errorText: 'Unknown brain dump tool' },
  { domain: 'personal-tasks', handler: handlePersonalTasksTool, name: 'workos_unknown_personal', errorText: 'Unknown personal tasks tool' },
];

console.log('\nUnknown tool rejection tests:');
for (const test of unknownToolTests) {
  routerTests++;
  try {
    const result = await test.handler(test.name, {}, db);
    if (result && result.content && result.content[0]?.text?.includes(test.errorText)) {
      console.log(`  ✓ ${test.domain} - unknown tool properly rejected`);
      routerPassed++;
    } else {
      console.log(`  ✗ ${test.domain} - unexpected response to unknown tool`);
    }
  } catch (error) {
    console.log(`  ✗ ${test.domain} - threw error: ${error.message}`);
  }
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

console.log(`Tool Definitions:`);
console.log(`  Energy: ${allEnergyToolsPresent ? '✓ PASS' : '✗ FAIL'} (2/2 tools)`);
console.log(`  Brain Dump: ${allBrainDumpToolsPresent ? '✓ PASS' : '✗ FAIL'} (3/3 tools)`);
console.log(`  Personal Tasks: ${allPersonalTasksToolsPresent ? '✓ PASS' : '✗ FAIL'} (1/1 tools)`);
console.log(`Router Routing: ${routerPassed === routerTests ? '✓ PASS' : '⚠ PARTIAL'} (${routerPassed}/${routerTests})`);
console.log();
console.log(`Overall: ${allPassed ? '✓ ALL TESTS PASSED' : '⚠ SOME TESTS FAILED'}`);
console.log();

console.log('Note: Write operations (log_energy, brain_dump, process_brain_dump) should be');
console.log('tested manually to verify data persistence and side effects.');
console.log();

process.exit(allPassed ? 0 : 1);
