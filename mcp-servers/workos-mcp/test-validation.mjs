#!/usr/bin/env node
// =============================================================================
// VALIDATION TEST SUITE
// =============================================================================
// Comprehensive tests for input validation across all domains
// Tests string length validation, numeric range validation, enum validation,
// required field validation, and edge cases
// =============================================================================

import {
  validateToolInput,
  validateAndSanitize,
  sanitizeInput,
  taskIdSchema,
  taskTitleSchema,
  taskDescriptionSchema,
  queryLimitSchema,
  taskStatusSchema,
  taskCategorySchema,
  habitNameSchema,
  habitDescriptionSchema,
  habitEmojiSchema,
  habitNoteSchema,
  brainDumpContentSchema,
  energyLevelSchema,
  ouraReadinessSchema,
  ouraHrvSchema,
  ouraSleepSchema,
  clientNameSchema,
  positiveInt,
  boundedInt,
  minMaxString,
} from './dist/shared/validation-schemas.js';

import {
  GetTasksSchema,
  CreateTaskSchema,
  UpdateTaskSchema,
  GetClientMemorySchema,
} from './dist/domains/tasks/validation.js';

import {
  CreateHabitSchema,
  CompleteHabitSchema,
} from './dist/domains/habits/validation.js';

import {
  BrainDumpSchema,
  GetBrainDumpSchema,
} from './dist/domains/brain-dump/validation.js';

import {
  LogEnergySchema,
  GetEnergySchema,
} from './dist/domains/energy/validation.js';

import { STRING_LIMITS, NUMERIC_LIMITS } from './dist/shared/validation-constants.js';

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

function assertSuccess(result, message) {
  assert(result.success === true, message || 'Expected validation to succeed');
}

function assertFailure(result, message) {
  assert(result.success === false, message || 'Expected validation to fail');
}

// =============================================================================
// TEST SUITE
// =============================================================================

console.log('='.repeat(80));
console.log('Validation Test Suite');
console.log('='.repeat(80));

// =============================================================================
// STRING LENGTH VALIDATION TESTS
// =============================================================================

console.log('\n' + '-'.repeat(80));
console.log('String Length Validation Tests');
console.log('-'.repeat(80));

// Task title - too short
test('Task title - empty string should fail', () => {
  const result = validateToolInput(taskTitleSchema, '');
  assertFailure(result);
  assert(result.error.includes('at least'), 'Error should mention minimum length');
});

// Task title - valid
test('Task title - valid length should pass', () => {
  const result = validateToolInput(taskTitleSchema, 'Valid task title');
  assertSuccess(result);
  assert(result.data === 'Valid task title', 'Data should match input');
});

// Task title - too long
test('Task title - exceeds max length should fail', () => {
  const longTitle = 'a'.repeat(STRING_LIMITS.TASK_TITLE_MAX + 1);
  const result = validateToolInput(taskTitleSchema, longTitle);
  assertFailure(result);
  assert(result.error.includes('exceed'), 'Error should mention maximum length');
});

// Task title - at boundary (exact max)
test('Task title - exactly max length should pass', () => {
  const maxTitle = 'a'.repeat(STRING_LIMITS.TASK_TITLE_MAX);
  const result = validateToolInput(taskTitleSchema, maxTitle);
  assertSuccess(result);
});

// Task description - optional and within bounds
test('Task description - valid optional field should pass', () => {
  const result = validateToolInput(taskDescriptionSchema, 'Valid description');
  assertSuccess(result);
});

// Task description - too long
test('Task description - exceeds max length should fail', () => {
  const longDesc = 'a'.repeat(STRING_LIMITS.TASK_DESCRIPTION_MAX + 1);
  const result = validateToolInput(taskDescriptionSchema, longDesc);
  assertFailure(result);
});

// Habit name - valid
test('Habit name - valid length should pass', () => {
  const result = validateToolInput(habitNameSchema, 'Morning meditation');
  assertSuccess(result);
});

// Habit name - too long
test('Habit name - exceeds max length should fail', () => {
  const longName = 'a'.repeat(STRING_LIMITS.HABIT_NAME_MAX + 1);
  const result = validateToolInput(habitNameSchema, longName);
  assertFailure(result);
});

// Habit emoji - valid
test('Habit emoji - valid emoji should pass', () => {
  const result = validateToolInput(habitEmojiSchema, '🏃‍♂️');
  assertSuccess(result);
});

// Habit emoji - too long
test('Habit emoji - exceeds max length should fail', () => {
  const longEmoji = '😀'.repeat(STRING_LIMITS.HABIT_EMOJI_MAX);
  const result = validateToolInput(habitEmojiSchema, longEmoji);
  assertFailure(result);
});

// Brain dump content - valid
test('Brain dump content - valid length should pass', () => {
  const result = validateToolInput(brainDumpContentSchema, 'Important idea to capture');
  assertSuccess(result);
});

// Brain dump content - too long
test('Brain dump content - exceeds max length should fail', () => {
  const longContent = 'a'.repeat(STRING_LIMITS.BRAIN_DUMP_CONTENT_MAX + 1);
  const result = validateToolInput(brainDumpContentSchema, longContent);
  assertFailure(result);
});

// Client name - valid
test('Client name - valid length should pass', () => {
  const result = validateToolInput(clientNameSchema, 'Acme Corp');
  assertSuccess(result);
});

// Client name - too long
test('Client name - exceeds max length should fail', () => {
  const longName = 'a'.repeat(STRING_LIMITS.CLIENT_NAME_MAX + 1);
  const result = validateToolInput(clientNameSchema, longName);
  assertFailure(result);
});

// =============================================================================
// NUMERIC RANGE VALIDATION TESTS
// =============================================================================

console.log('\n' + '-'.repeat(80));
console.log('Numeric Range Validation Tests');
console.log('-'.repeat(80));

// Task ID - valid positive integer
test('Task ID - valid positive integer should pass', () => {
  const result = validateToolInput(taskIdSchema, 123);
  assertSuccess(result);
  assert(result.data === 123, 'Data should match input');
});

// Task ID - zero should fail
test('Task ID - zero should fail', () => {
  const result = validateToolInput(taskIdSchema, 0);
  assertFailure(result);
  assert(result.error.includes('positive'), 'Error should mention positive integer');
});

// Task ID - negative should fail
test('Task ID - negative integer should fail', () => {
  const result = validateToolInput(taskIdSchema, -5);
  assertFailure(result);
  assert(result.error.includes('positive') || result.error.includes('between'), 'Error should mention valid range');
});

// Task ID - decimal should fail
test('Task ID - decimal number should fail', () => {
  const result = validateToolInput(taskIdSchema, 1.5);
  assertFailure(result);
  assert(result.error.includes('integer'), 'Error should mention integer requirement');
});

// Task ID - max value should pass
test('Task ID - max valid ID should pass', () => {
  const result = validateToolInput(taskIdSchema, NUMERIC_LIMITS.ID_MAX);
  assertSuccess(result);
});

// Query limit - valid range
test('Query limit - valid value should pass', () => {
  const result = validateToolInput(queryLimitSchema, 50);
  assertSuccess(result);
});

// Query limit - below minimum should fail
test('Query limit - below minimum should fail', () => {
  const result = validateToolInput(queryLimitSchema, 0);
  assertFailure(result);
  assert(result.error.includes('between'), 'Error should mention valid range');
});

// Query limit - above maximum should fail
test('Query limit - above maximum should fail', () => {
  const result = validateToolInput(queryLimitSchema, NUMERIC_LIMITS.QUERY_LIMIT_MAX + 1);
  assertFailure(result);
  assert(result.error.includes('between'), 'Error should mention valid range');
});

// Query limit - at boundaries
test('Query limit - minimum boundary should pass', () => {
  const result = validateToolInput(queryLimitSchema, NUMERIC_LIMITS.QUERY_LIMIT_MIN);
  assertSuccess(result);
});

test('Query limit - maximum boundary should pass', () => {
  const result = validateToolInput(queryLimitSchema, NUMERIC_LIMITS.QUERY_LIMIT_MAX);
  assertSuccess(result);
});

// Oura metrics - valid ranges
test('Oura readiness - valid value should pass', () => {
  const result = validateToolInput(ouraReadinessSchema, 75);
  assertSuccess(result);
});

test('Oura readiness - below minimum should fail', () => {
  const result = validateToolInput(ouraReadinessSchema, -1);
  assertFailure(result);
});

test('Oura readiness - above maximum should fail', () => {
  const result = validateToolInput(ouraReadinessSchema, 101);
  assertFailure(result);
});

test('Oura HRV - valid value should pass', () => {
  const result = validateToolInput(ouraHrvSchema, 50);
  assertSuccess(result);
});

test('Oura HRV - above maximum should fail', () => {
  const result = validateToolInput(ouraHrvSchema, 301);
  assertFailure(result);
});

test('Oura sleep - valid value should pass', () => {
  const result = validateToolInput(ouraSleepSchema, 85);
  assertSuccess(result);
});

// =============================================================================
// ENUM VALIDATION TESTS
// =============================================================================

console.log('\n' + '-'.repeat(80));
console.log('Enum Validation Tests');
console.log('-'.repeat(80));

// Task status - valid values
test('Task status - valid value "active" should pass', () => {
  const result = validateToolInput(taskStatusSchema, 'active');
  assertSuccess(result);
});

test('Task status - valid value "queued" should pass', () => {
  const result = validateToolInput(taskStatusSchema, 'queued');
  assertSuccess(result);
});

test('Task status - valid value "backlog" should pass', () => {
  const result = validateToolInput(taskStatusSchema, 'backlog');
  assertSuccess(result);
});

test('Task status - valid value "done" should pass', () => {
  const result = validateToolInput(taskStatusSchema, 'done');
  assertSuccess(result);
});

// Task status - invalid value
test('Task status - invalid value should fail', () => {
  const result = validateToolInput(taskStatusSchema, 'invalid');
  assertFailure(result);
  assert(result.error.includes('one of'), 'Error should list valid options');
});

test('Task status - case sensitive should fail', () => {
  const result = validateToolInput(taskStatusSchema, 'Active');
  assertFailure(result);
});

// Task category - valid values
test('Task category - valid value "work" should pass', () => {
  const result = validateToolInput(taskCategorySchema, 'work');
  assertSuccess(result);
});

test('Task category - valid value "personal" should pass', () => {
  const result = validateToolInput(taskCategorySchema, 'personal');
  assertSuccess(result);
});

// Task category - invalid value
test('Task category - invalid value should fail', () => {
  const result = validateToolInput(taskCategorySchema, 'business');
  assertFailure(result);
});

// Energy level - valid values
test('Energy level - valid value "high" should pass', () => {
  const result = validateToolInput(energyLevelSchema, 'high');
  assertSuccess(result);
});

test('Energy level - invalid value should fail', () => {
  const result = validateToolInput(energyLevelSchema, 'extreme');
  assertFailure(result);
});

// =============================================================================
// MISSING REQUIRED FIELDS TESTS
// =============================================================================

console.log('\n' + '-'.repeat(80));
console.log('Missing Required Fields Tests');
console.log('-'.repeat(80));

// Create task - missing required title
test('Create task - missing title should fail', () => {
  const result = validateToolInput(CreateTaskSchema, {
    description: 'Test description',
  });
  assertFailure(result);
  assert(result.error.toLowerCase().includes('title'), 'Error should mention missing title');
});

// Create task - with required fields
test('Create task - with required title should pass', () => {
  const result = validateToolInput(CreateTaskSchema, {
    title: 'Valid task',
  });
  assertSuccess(result);
});

// Update task - missing required taskId
test('Update task - missing taskId should fail', () => {
  const result = validateToolInput(UpdateTaskSchema, {
    title: 'Updated title',
  });
  assertFailure(result);
  assert(result.error.toLowerCase().includes('taskid'), 'Error should mention missing taskId');
});

// Create habit - missing required name
test('Create habit - missing name should fail', () => {
  const result = validateToolInput(CreateHabitSchema, {
    frequency: 'daily',
  });
  assertFailure(result);
  assert(result.error.toLowerCase().includes('name'), 'Error should mention missing name');
});

// Brain dump - missing required content
test('Brain dump - missing content should fail', () => {
  const result = validateToolInput(BrainDumpSchema, {
    category: 'thought',
  });
  assertFailure(result);
  assert(result.error.toLowerCase().includes('content'), 'Error should mention missing content');
});

// Get client memory - missing required clientName
test('Get client memory - missing clientName should fail', () => {
  const result = validateToolInput(GetClientMemorySchema, {});
  assertFailure(result);
  assert(result.error.toLowerCase().includes('clientname'), 'Error should mention missing clientName');
});

// =============================================================================
// EDGE CASES TESTS
// =============================================================================

console.log('\n' + '-'.repeat(80));
console.log('Edge Cases Tests');
console.log('-'.repeat(80));

// Null values
test('Task title - null should fail', () => {
  const result = validateToolInput(taskTitleSchema, null);
  assertFailure(result);
});

test('Task ID - null should fail', () => {
  const result = validateToolInput(taskIdSchema, null);
  assertFailure(result);
});

// Undefined values
test('Task title - undefined should fail', () => {
  const result = validateToolInput(taskTitleSchema, undefined);
  assertFailure(result);
});

// Optional fields with undefined (should pass)
test('Task description - undefined should pass (optional)', () => {
  const result = validateToolInput(taskDescriptionSchema, undefined);
  assertSuccess(result);
});

// Empty strings
test('Task title - whitespace only should fail after trim', () => {
  const result = validateToolInput(taskTitleSchema, '   ');
  assertFailure(result);
});

// String with leading/trailing whitespace
test('String trimming - should trim whitespace', () => {
  const result = validateToolInput(taskTitleSchema, '  Valid title  ');
  assertSuccess(result);
  assert(result.data === 'Valid title', 'Should trim whitespace');
});

// Wrong type errors
test('Task ID - string should fail', () => {
  const result = validateToolInput(taskIdSchema, '123');
  assertFailure(result);
  assert(result.error.toLowerCase().includes('number'), 'Error should mention type mismatch');
});

test('Task title - number should fail', () => {
  const result = validateToolInput(taskTitleSchema, 123);
  assertFailure(result);
  assert(result.error.toLowerCase().includes('string'), 'Error should mention type mismatch');
});

// Arrays where objects expected
test('Create task - array should fail', () => {
  const result = validateToolInput(CreateTaskSchema, ['title']);
  assertFailure(result);
});

// Objects where primitives expected
test('Task ID - object should fail', () => {
  const result = validateToolInput(taskIdSchema, { id: 123 });
  assertFailure(result);
});

// =============================================================================
// COMPLEX SCHEMA VALIDATION TESTS
// =============================================================================

console.log('\n' + '-'.repeat(80));
console.log('Complex Schema Validation Tests');
console.log('-'.repeat(80));

// Get tasks - all valid optional fields
test('Get tasks - all valid optional fields should pass', () => {
  const result = validateToolInput(GetTasksSchema, {
    status: 'active',
    clientId: 42,
    limit: 25,
  });
  assertSuccess(result);
});

// Get tasks - empty object should pass (all optional)
test('Get tasks - empty object should pass', () => {
  const result = validateToolInput(GetTasksSchema, {});
  assertSuccess(result);
});

// Get tasks - invalid status
test('Get tasks - invalid status should fail', () => {
  const result = validateToolInput(GetTasksSchema, {
    status: 'invalid',
  });
  assertFailure(result);
});

// Create task - all fields valid
test('Create task - all valid fields should pass', () => {
  const result = validateToolInput(CreateTaskSchema, {
    title: 'Complete project',
    description: 'Finish the MVP by end of week',
    clientId: 5,
    status: 'active',
    category: 'work',
    valueTier: 'deliverable',
    drainType: 'deep',
  });
  assertSuccess(result);
});

// Create task - cannot create with status "done"
test('Create task - status "done" should fail', () => {
  const result = validateToolInput(CreateTaskSchema, {
    title: 'Already done task',
    status: 'done',
  });
  assertFailure(result);
  assert(result.error.toLowerCase().includes('done'), 'Error should mention "done" status not allowed');
});

// Update task - partial update valid
test('Update task - partial update should pass', () => {
  const result = validateToolInput(UpdateTaskSchema, {
    taskId: 10,
    title: 'Updated title',
  });
  assertSuccess(result);
});

// Create habit - all fields valid
test('Create habit - all valid fields should pass', () => {
  const result = validateToolInput(CreateHabitSchema, {
    name: 'Morning run',
    description: 'Run 5km every morning',
    frequency: 'daily',
    timeOfDay: 'morning',
    emoji: '🏃',
    targetCount: 1,
    category: 'health',
  });
  assertSuccess(result);
});

// Complete habit - with note
test('Complete habit - with optional note should pass', () => {
  const result = validateToolInput(CompleteHabitSchema, {
    habitId: 5,
    note: 'Felt great today!',
  });
  assertSuccess(result);
});

// Brain dump - valid with category
test('Brain dump - valid with category should pass', () => {
  const result = validateToolInput(BrainDumpSchema, {
    content: 'Need to remember to call the client tomorrow',
    category: 'task',
  });
  assertSuccess(result);
});

// Log energy - with Oura metrics
test('Log energy - with Oura metrics should pass', () => {
  const result = validateToolInput(LogEnergySchema, {
    level: 'high',
    note: 'Great sleep last night',
    ouraReadiness: 85,
    ouraHrv: 45,
    ouraSleep: 90,
  });
  assertSuccess(result);
});

// =============================================================================
// SANITIZATION TESTS
// =============================================================================

console.log('\n' + '-'.repeat(80));
console.log('Sanitization Tests');
console.log('-'.repeat(80));

// Sanitize input - trim strings
test('Sanitize input - should trim strings', () => {
  const input = {
    title: '  Task title  ',
    description: '  Description  ',
  };
  const sanitized = sanitizeInput(input);
  assert(sanitized.title === 'Task title', 'Should trim title');
  assert(sanitized.description === 'Description', 'Should trim description');
});

// Sanitize input - preserve numbers
test('Sanitize input - should preserve numbers', () => {
  const input = {
    taskId: 123,
    limit: 50,
  };
  const sanitized = sanitizeInput(input);
  assert(sanitized.taskId === 123, 'Should preserve taskId');
  assert(sanitized.limit === 50, 'Should preserve limit');
});

// Sanitize input - nested objects
test('Sanitize input - should handle nested objects', () => {
  const input = {
    title: '  Title  ',
    nested: {
      field: '  Value  ',
    },
  };
  const sanitized = sanitizeInput(input);
  assert(sanitized.nested.field === 'Value', 'Should trim nested fields');
});

// Validate and sanitize - combined operation
test('Validate and sanitize - should trim and validate', () => {
  const result = validateAndSanitize(CreateTaskSchema, {
    title: '  Valid task  ',
    description: '  Description  ',
  });
  assertSuccess(result);
  assert(result.data.title === 'Valid task', 'Should trim title');
  assert(result.data.description === 'Description', 'Should trim description');
});

// =============================================================================
// SCHEMA HELPER FUNCTION TESTS
// =============================================================================

console.log('\n' + '-'.repeat(80));
console.log('Schema Helper Function Tests');
console.log('-'.repeat(80));

// minMaxString helper
test('minMaxString - valid string should pass', () => {
  const schema = minMaxString('test', 1, 10);
  const result = validateToolInput(schema, 'hello');
  assertSuccess(result);
});

test('minMaxString - too short should fail', () => {
  const schema = minMaxString('test', 5, 10);
  const result = validateToolInput(schema, 'hi');
  assertFailure(result);
});

test('minMaxString - too long should fail', () => {
  const schema = minMaxString('test', 1, 5);
  const result = validateToolInput(schema, 'toolong');
  assertFailure(result);
});

// positiveInt helper
test('positiveInt - valid positive integer should pass', () => {
  const schema = positiveInt('testId');
  const result = validateToolInput(schema, 42);
  assertSuccess(result);
});

test('positiveInt - negative should fail', () => {
  const schema = positiveInt('testId');
  const result = validateToolInput(schema, -1);
  assertFailure(result);
});

test('positiveInt - zero should fail', () => {
  const schema = positiveInt('testId');
  const result = validateToolInput(schema, 0);
  assertFailure(result);
});

// boundedInt helper
test('boundedInt - within range should pass', () => {
  const schema = boundedInt('count', 1, 100);
  const result = validateToolInput(schema, 50);
  assertSuccess(result);
});

test('boundedInt - below range should fail', () => {
  const schema = boundedInt('count', 10, 100);
  const result = validateToolInput(schema, 5);
  assertFailure(result);
});

test('boundedInt - above range should fail', () => {
  const schema = boundedInt('count', 1, 100);
  const result = validateToolInput(schema, 150);
  assertFailure(result);
});

// =============================================================================
// TEST SUMMARY
// =============================================================================

console.log('\n' + '='.repeat(80));
console.log('Test Summary');
console.log('='.repeat(80));
console.log(`Total tests: ${testCount}`);
console.log(`✓ Passed: ${passCount}`);
console.log(`✗ Failed: ${failCount}`);

if (failCount === 0) {
  console.log('\n🎉 All validation tests passed!');
  process.exit(0);
} else {
  console.log(`\n❌ ${failCount} test(s) failed`);
  process.exit(1);
}
