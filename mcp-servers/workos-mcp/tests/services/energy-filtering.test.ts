/**
 * Unit tests for filterTasksByEnergy() function
 * Tests energy-based task gating logic that filters tasks based on Oura readiness scores
 * to protect wellbeing on low-energy days and optimize task suggestions
 */

import {
  filterTasksByEnergy,
  type TaskFilterResult,
} from "../../src/services/energy-prioritization.js";
import type { Task, CognitiveLoad } from "../../src/schema.js";

// =============================================================================
// TEST HELPERS
// =============================================================================

/**
 * Create a mock task for testing
 */
function createMockTask(
  overrides: Partial<Task> = {}
): Task {
  return {
    id: 1,
    clientId: null,
    title: "Test Task",
    description: null,
    status: "backlog",
    category: "work",
    valueTier: "progress",
    effortEstimate: 2,
    effortActual: null,
    drainType: null,
    cognitiveLoad: "medium",
    sortOrder: 0,
    subtasks: [],
    createdAt: new Date(),
    updatedAt: new Date(),
    completedAt: null,
    backlogEnteredAt: null,
    pointsAiGuess: null,
    pointsFinal: null,
    pointsAdjustedAt: null,
    ...overrides,
  } as Task;
}

/**
 * Assert helper for test results
 */
function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`❌ Assertion failed: ${message}`);
  }
  console.log(`✅ ${message}`);
}

/**
 * Assert equality with detailed error message
 */
function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) {
    throw new Error(
      `❌ ${message}\n   Expected: ${expected}\n   Actual: ${actual}`
    );
  }
  console.log(`✅ ${message}`);
}

/**
 * Assert that a string contains a substring
 */
function assertContains(
  actual: string,
  expected: string,
  message: string
): void {
  if (!actual.includes(expected)) {
    throw new Error(
      `❌ ${message}\n   Expected to contain: "${expected}"\n   Actual: "${actual}"`
    );
  }
  console.log(`✅ ${message}`);
}

/**
 * Assert that an array has a specific length
 */
function assertLength<T>(
  array: T[],
  expectedLength: number,
  message: string
): void {
  if (array.length !== expectedLength) {
    throw new Error(
      `❌ ${message}\n   Expected length: ${expectedLength}\n   Actual length: ${array.length}`
    );
  }
  console.log(`✅ ${message}`);
}

// =============================================================================
// TEST SUITES
// =============================================================================

/**
 * Test suite for low energy filtering (readiness < 60)
 * Should only allow low cognitive load tasks (recovery mode)
 */
function testLowEnergyFiltering(): void {
  console.log("\n📋 Testing Low Energy Filtering (readiness < 60)");
  console.log("━".repeat(60));

  // Create test tasks with different cognitive loads
  const lowTask = createMockTask({ id: 1, cognitiveLoad: "low", title: "Low task" });
  const mediumTask = createMockTask({ id: 2, cognitiveLoad: "medium", title: "Medium task" });
  const highTask = createMockTask({ id: 3, cognitiveLoad: "high", title: "High task" });
  const tasks = [lowTask, mediumTask, highTask];

  // Test at readiness 55 (low energy)
  const result = filterTasksByEnergy(tasks, 55);

  // Should only allow low cognitive load tasks
  assertLength(
    result.allowedTasks,
    1,
    "Low energy should allow only 1 task (low cognitive load)"
  );
  assertEqual(
    result.allowedTasks[0].id,
    lowTask.id,
    "Low energy should allow the low cognitive load task"
  );

  // Should filter out medium and high cognitive load tasks
  assertLength(
    result.filteredOutTasks,
    2,
    "Low energy should filter out 2 tasks (medium + high)"
  );

  // Check filter reason
  assertContains(
    result.filterReason,
    "Readiness 55/100",
    "Filter reason should include readiness score"
  );
  assertContains(
    result.filterReason,
    "low cognitive load tasks only",
    "Filter reason should mention low cognitive load only"
  );
  assertContains(
    result.filterReason,
    "Recovery mode active",
    "Filter reason should mention recovery mode"
  );

  // Test at readiness 59 (boundary - still low energy)
  const result59 = filterTasksByEnergy(tasks, 59);
  assertLength(
    result59.allowedTasks,
    1,
    "Readiness 59 should still be recovery mode (only low cognitive load)"
  );

  // Test at readiness 30 (very low)
  const result30 = filterTasksByEnergy(tasks, 30);
  assertLength(
    result30.allowedTasks,
    1,
    "Readiness 30 should be recovery mode (only low cognitive load)"
  );
  assertContains(
    result30.filterReason,
    "Readiness 30/100",
    "Very low readiness should be reflected in reason"
  );

  console.log("✨ All low energy filtering tests passed!");
}

/**
 * Test suite for medium energy filtering (readiness 60-75)
 * Should allow low + medium cognitive load tasks
 */
function testMediumEnergyFiltering(): void {
  console.log("\n📋 Testing Medium Energy Filtering (readiness 60-75)");
  console.log("━".repeat(60));

  // Create test tasks with different cognitive loads
  const lowTask = createMockTask({ id: 1, cognitiveLoad: "low", title: "Low task" });
  const mediumTask1 = createMockTask({ id: 2, cognitiveLoad: "medium", title: "Medium task 1" });
  const mediumTask2 = createMockTask({ id: 3, cognitiveLoad: "medium", title: "Medium task 2" });
  const highTask = createMockTask({ id: 4, cognitiveLoad: "high", title: "High task" });
  const tasks = [lowTask, mediumTask1, mediumTask2, highTask];

  // Test at readiness 60 (lower boundary - medium energy)
  const result60 = filterTasksByEnergy(tasks, 60);
  assertLength(
    result60.allowedTasks,
    3,
    "Readiness 60 should allow 3 tasks (low + medium)"
  );
  assertLength(
    result60.filteredOutTasks,
    1,
    "Readiness 60 should filter out 1 task (high)"
  );
  assertEqual(
    result60.filteredOutTasks[0].id,
    highTask.id,
    "Should filter out the high cognitive load task"
  );

  // Test at readiness 68 (mid-range medium energy)
  const result68 = filterTasksByEnergy(tasks, 68);
  assertLength(
    result68.allowedTasks,
    3,
    "Readiness 68 should allow low + medium tasks"
  );
  assertContains(
    result68.filterReason,
    "Readiness 68/100",
    "Filter reason should include readiness score"
  );
  assertContains(
    result68.filterReason,
    "low and medium cognitive load",
    "Filter reason should mention low and medium allowed"
  );
  assertContains(
    result68.filterReason,
    "Moderate energy",
    "Filter reason should mention moderate energy"
  );

  // Test at readiness 75 (upper boundary - still medium energy)
  const result75 = filterTasksByEnergy(tasks, 75);
  assertLength(
    result75.allowedTasks,
    3,
    "Readiness 75 should allow low + medium tasks (boundary)"
  );
  assertLength(
    result75.filteredOutTasks,
    1,
    "Readiness 75 should still filter out high cognitive load"
  );

  console.log("✨ All medium energy filtering tests passed!");
}

/**
 * Test suite for high energy filtering (readiness > 75)
 * Should allow all tasks including high cognitive load
 */
function testHighEnergyFiltering(): void {
  console.log("\n📋 Testing High Energy Filtering (readiness > 75)");
  console.log("━".repeat(60));

  // Create test tasks with different cognitive loads
  const lowTask = createMockTask({ id: 1, cognitiveLoad: "low", title: "Low task" });
  const mediumTask = createMockTask({ id: 2, cognitiveLoad: "medium", title: "Medium task" });
  const highTask1 = createMockTask({ id: 3, cognitiveLoad: "high", title: "High task 1" });
  const highTask2 = createMockTask({ id: 4, cognitiveLoad: "high", title: "High task 2" });
  const tasks = [lowTask, mediumTask, highTask1, highTask2];

  // Test at readiness 76 (just above boundary)
  const result76 = filterTasksByEnergy(tasks, 76);
  assertLength(
    result76.allowedTasks,
    4,
    "Readiness 76 should allow all tasks"
  );
  assertLength(
    result76.filteredOutTasks,
    0,
    "Readiness 76 should filter out no tasks"
  );
  assertContains(
    result76.filterReason,
    "Readiness 76/100",
    "Filter reason should include readiness score"
  );
  assertContains(
    result76.filterReason,
    "Full energy - all tasks available",
    "Filter reason should indicate all tasks available"
  );

  // Test at readiness 85 (high energy)
  const result85 = filterTasksByEnergy(tasks, 85);
  assertLength(
    result85.allowedTasks,
    4,
    "Readiness 85 should allow all tasks"
  );
  assertLength(
    result85.filteredOutTasks,
    0,
    "Readiness 85 should filter out no tasks"
  );

  // Test at readiness 100 (max energy)
  const result100 = filterTasksByEnergy(tasks, 100);
  assertLength(
    result100.allowedTasks,
    4,
    "Readiness 100 should allow all tasks"
  );
  assertContains(
    result100.filterReason,
    "Readiness 100/100",
    "Max readiness should show 100/100"
  );

  console.log("✨ All high energy filtering tests passed!");
}

/**
 * Test suite for null readiness score
 * Should return all tasks unfiltered when no energy data is available
 */
function testNullReadinessScore(): void {
  console.log("\n📋 Testing Null Readiness Score");
  console.log("━".repeat(60));

  // Create test tasks with different cognitive loads
  const lowTask = createMockTask({ id: 1, cognitiveLoad: "low" });
  const mediumTask = createMockTask({ id: 2, cognitiveLoad: "medium" });
  const highTask = createMockTask({ id: 3, cognitiveLoad: "high" });
  const tasks = [lowTask, mediumTask, highTask];

  // Test with null readiness score
  const result = filterTasksByEnergy(tasks, null);

  // Should return all tasks unfiltered
  assertLength(
    result.allowedTasks,
    3,
    "Null readiness should allow all tasks"
  );
  assertLength(
    result.filteredOutTasks,
    0,
    "Null readiness should filter out no tasks"
  );
  assertContains(
    result.filterReason,
    "No energy data available",
    "Filter reason should mention no energy data"
  );
  assertContains(
    result.filterReason,
    "showing all tasks",
    "Filter reason should indicate all tasks shown"
  );

  console.log("✨ All null readiness score tests passed!");
}

/**
 * Test suite for tasks without cognitive load metadata
 * Tasks without cognitive load should default to "medium"
 */
function testTasksWithoutCognitiveLoad(): void {
  console.log("\n📋 Testing Tasks Without Cognitive Load");
  console.log("━".repeat(60));

  // Create tasks without cognitive load (will default to medium)
  const task1 = createMockTask({ id: 1, cognitiveLoad: null as any, title: "Task 1" });
  const task2 = createMockTask({ id: 2, cognitiveLoad: undefined as any, title: "Task 2" });
  const lowTask = createMockTask({ id: 3, cognitiveLoad: "low", title: "Low task" });
  const tasks = [task1, task2, lowTask];

  // Test at low energy (< 60) - should only allow low cognitive load
  const resultLow = filterTasksByEnergy(tasks, 50);
  assertLength(
    resultLow.allowedTasks,
    1,
    "Low energy should allow only low cognitive load task"
  );
  assertEqual(
    resultLow.allowedTasks[0].id,
    lowTask.id,
    "Should allow the explicitly low cognitive load task"
  );

  // Test at medium energy (60-75) - should allow tasks without cognitive load (default to medium)
  const resultMedium = filterTasksByEnergy(tasks, 65);
  assertLength(
    resultMedium.allowedTasks,
    3,
    "Medium energy should allow all tasks (defaults treated as medium)"
  );

  // Test at high energy (> 75) - should allow all tasks
  const resultHigh = filterTasksByEnergy(tasks, 80);
  assertLength(
    resultHigh.allowedTasks,
    3,
    "High energy should allow all tasks"
  );

  console.log("✨ All tasks without cognitive load tests passed!");
}

/**
 * Test suite for empty task list
 * Should handle empty arrays gracefully
 */
function testEmptyTaskList(): void {
  console.log("\n📋 Testing Empty Task List");
  console.log("━".repeat(60));

  const emptyTasks: Task[] = [];

  // Test with various readiness scores
  const resultLow = filterTasksByEnergy(emptyTasks, 50);
  assertLength(
    resultLow.allowedTasks,
    0,
    "Empty task list should return empty allowed tasks at low energy"
  );
  assertLength(
    resultLow.filteredOutTasks,
    0,
    "Empty task list should return empty filtered tasks at low energy"
  );

  const resultMedium = filterTasksByEnergy(emptyTasks, 70);
  assertLength(
    resultMedium.allowedTasks,
    0,
    "Empty task list should return empty allowed tasks at medium energy"
  );

  const resultHigh = filterTasksByEnergy(emptyTasks, 85);
  assertLength(
    resultHigh.allowedTasks,
    0,
    "Empty task list should return empty allowed tasks at high energy"
  );

  const resultNull = filterTasksByEnergy(emptyTasks, null);
  assertLength(
    resultNull.allowedTasks,
    0,
    "Empty task list should return empty allowed tasks with null readiness"
  );

  console.log("✨ All empty task list tests passed!");
}

/**
 * Test suite for filter explanation generation
 * Should provide detailed breakdown of filtered tasks
 */
function testFilterExplanation(): void {
  console.log("\n📋 Testing Filter Explanation Generation");
  console.log("━".repeat(60));

  // Create tasks with different cognitive loads
  const highTask1 = createMockTask({ id: 1, cognitiveLoad: "high", title: "High 1" });
  const highTask2 = createMockTask({ id: 2, cognitiveLoad: "high", title: "High 2" });
  const mediumTask = createMockTask({ id: 3, cognitiveLoad: "medium", title: "Medium" });
  const lowTask = createMockTask({ id: 4, cognitiveLoad: "low", title: "Low" });

  // Test explanation with multiple filtered tasks at low energy
  const resultLow = filterTasksByEnergy([highTask1, highTask2, mediumTask, lowTask], 50);
  assertContains(
    resultLow.filterReason,
    "2 high cognitive load tasks",
    "Explanation should count high cognitive load tasks"
  );
  assertContains(
    resultLow.filterReason,
    "1 medium cognitive load task",
    "Explanation should count medium cognitive load task (singular)"
  );
  assertContains(
    resultLow.filterReason,
    "Recovery mode active",
    "Low energy explanation should mention recovery mode"
  );

  // Test explanation at medium energy (filters only high)
  const resultMedium = filterTasksByEnergy([highTask1, highTask2, mediumTask, lowTask], 65);
  assertContains(
    resultMedium.filterReason,
    "2 high cognitive load tasks",
    "Medium energy should filter high cognitive tasks"
  );
  assertContains(
    resultMedium.filterReason,
    "Moderate energy",
    "Medium energy explanation should mention moderate energy"
  );
  // Extract the breakdown portion (after "Filtered:") and verify medium tasks not in filtered list
  const filteredPortion = resultMedium.filterReason.split("Filtered:")[1] || "";
  assert(
    !filteredPortion.includes("medium cognitive load task"),
    "Medium energy should not mention medium tasks in filtered breakdown"
  );

  // Test explanation at high energy (no filtering)
  const resultHigh = filterTasksByEnergy([highTask1, highTask2, mediumTask, lowTask], 85);
  assert(
    !resultHigh.filterReason.includes("Filtered:"),
    "High energy with no filtering should not have detailed breakdown"
  );
  assertContains(
    resultHigh.filterReason,
    "all tasks available",
    "High energy should indicate all tasks available"
  );

  // Test with single filtered task (singular form)
  const resultSingle = filterTasksByEnergy([highTask1, lowTask], 50);
  assertContains(
    resultSingle.filterReason,
    "1 high cognitive load task",
    "Single filtered task should use singular form"
  );
  // Validate breakdown uses singular (not "1 high cognitive load tasks")
  assert(
    !resultSingle.filterReason.includes("1 high cognitive load tasks"),
    "Breakdown should not use plural 'tasks' for singular count"
  );

  console.log("✨ All filter explanation tests passed!");
}

/**
 * Test suite for boundary conditions
 * Edge cases at readiness thresholds
 */
function testBoundaryConditions(): void {
  console.log("\n📋 Testing Boundary Conditions");
  console.log("━".repeat(60));

  const lowTask = createMockTask({ id: 1, cognitiveLoad: "low" });
  const mediumTask = createMockTask({ id: 2, cognitiveLoad: "medium" });
  const highTask = createMockTask({ id: 3, cognitiveLoad: "high" });
  const tasks = [lowTask, mediumTask, highTask];

  // Test readiness = 0 (minimum)
  const result0 = filterTasksByEnergy(tasks, 0);
  assertLength(
    result0.allowedTasks,
    1,
    "Readiness 0 should be recovery mode (only low)"
  );
  assertContains(result0.filterReason, "Readiness 0/100", "Should show 0/100");

  // Test readiness = 59.99 (just below medium threshold)
  const result59 = filterTasksByEnergy(tasks, 59.99);
  assertLength(
    result59.allowedTasks,
    1,
    "Readiness 59.99 should still be low energy"
  );

  // Test readiness = 60 (exact medium threshold)
  const result60 = filterTasksByEnergy(tasks, 60);
  assertLength(
    result60.allowedTasks,
    2,
    "Readiness 60 should allow low + medium"
  );

  // Test readiness = 75 (exact high threshold boundary)
  const result75 = filterTasksByEnergy(tasks, 75);
  assertLength(
    result75.allowedTasks,
    2,
    "Readiness 75 should still be medium energy (not high)"
  );

  // Test readiness = 75.01 (just above high threshold)
  const result75_01 = filterTasksByEnergy(tasks, 75.01);
  assertLength(
    result75_01.allowedTasks,
    3,
    "Readiness 75.01 should be high energy (all tasks)"
  );

  // Test readiness = 76 (just above high threshold)
  const result76 = filterTasksByEnergy(tasks, 76);
  assertLength(
    result76.allowedTasks,
    3,
    "Readiness 76 should be high energy (all tasks)"
  );

  console.log("✨ All boundary condition tests passed!");
}

/**
 * Test suite for mixed cognitive load scenarios
 * Real-world task list compositions
 */
function testMixedCognitiveLoadScenarios(): void {
  console.log("\n📋 Testing Mixed Cognitive Load Scenarios");
  console.log("━".repeat(60));

  // Scenario 1: All low cognitive load tasks
  const allLowTasks = [
    createMockTask({ id: 1, cognitiveLoad: "low" }),
    createMockTask({ id: 2, cognitiveLoad: "low" }),
    createMockTask({ id: 3, cognitiveLoad: "low" }),
  ];

  const resultAllLow = filterTasksByEnergy(allLowTasks, 50);
  assertLength(
    resultAllLow.allowedTasks,
    3,
    "Low energy with all low tasks should allow all"
  );
  assertLength(
    resultAllLow.filteredOutTasks,
    0,
    "Low energy with all low tasks should filter none"
  );

  // Scenario 2: All high cognitive load tasks on low energy
  const allHighTasks = [
    createMockTask({ id: 1, cognitiveLoad: "high" }),
    createMockTask({ id: 2, cognitiveLoad: "high" }),
    createMockTask({ id: 3, cognitiveLoad: "high" }),
  ];

  const resultAllHigh = filterTasksByEnergy(allHighTasks, 50);
  assertLength(
    resultAllHigh.allowedTasks,
    0,
    "Low energy with all high tasks should allow none"
  );
  assertLength(
    resultAllHigh.filteredOutTasks,
    3,
    "Low energy with all high tasks should filter all"
  );
  assertContains(
    resultAllHigh.filterReason,
    "3 high cognitive load tasks",
    "Should count all high tasks in explanation"
  );

  // Scenario 3: Only medium tasks at low energy
  const allMediumTasks = [
    createMockTask({ id: 1, cognitiveLoad: "medium" }),
    createMockTask({ id: 2, cognitiveLoad: "medium" }),
  ];

  const resultAllMedium = filterTasksByEnergy(allMediumTasks, 55);
  assertLength(
    resultAllMedium.allowedTasks,
    0,
    "Low energy with all medium tasks should allow none"
  );
  assertLength(
    resultAllMedium.filteredOutTasks,
    2,
    "Low energy with all medium tasks should filter all"
  );

  console.log("✨ All mixed cognitive load scenario tests passed!");
}

// =============================================================================
// MAIN TEST RUNNER
// =============================================================================

/**
 * Run all test suites
 */
async function runAllTests(): Promise<void> {
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║  Energy Filtering Test Suite                            ║");
  console.log("╚══════════════════════════════════════════════════════════╝");

  try {
    testLowEnergyFiltering();
    testMediumEnergyFiltering();
    testHighEnergyFiltering();
    testNullReadinessScore();
    testTasksWithoutCognitiveLoad();
    testEmptyTaskList();
    testFilterExplanation();
    testBoundaryConditions();
    testMixedCognitiveLoadScenarios();

    console.log("\n╔══════════════════════════════════════════════════════════╗");
    console.log("║  ✅ ALL TESTS PASSED!                                    ║");
    console.log("╚══════════════════════════════════════════════════════════╝\n");
  } catch (error) {
    console.error("\n╔══════════════════════════════════════════════════════════╗");
    console.error("║  ❌ TEST SUITE FAILED                                    ║");
    console.error("╚══════════════════════════════════════════════════════════╝\n");
    console.error(error);
    process.exit(1);
  }
}

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runAllTests();
}

export { runAllTests };
