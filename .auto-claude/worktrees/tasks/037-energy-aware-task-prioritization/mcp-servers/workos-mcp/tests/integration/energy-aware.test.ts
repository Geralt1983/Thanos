/**
 * Integration tests for energy-aware task prioritization MCP tools
 *
 * Tests the full integration of:
 * 1. workos_get_energy_aware_tasks with various energy levels
 * 2. Daily goal adjustment with different readiness scores
 * 3. Override functionality
 *
 * These tests mock the database layer and test the service integration
 * that would power the MCP tool handlers.
 */

import {
  getEnergyContext,
  rankTasksByEnergy,
  calculateDailyGoalAdjustment,
  applyDailyGoalAdjustment,
  type EnergyContext,
  type ScoredTask,
  type GoalAdjustment,
} from "../../src/services/energy-prioritization.js";
import type { Task, EnergyLevel } from "../../src/schema.js";

// =============================================================================
// TEST CONFIGURATION
// =============================================================================

// Since this is integration testing and the actual database/handlers don't
// exist in this worktree, we'll test the service layer integration that
// would power the MCP tools

// =============================================================================
// MOCK DATA & HELPERS
// =============================================================================

/**
 * Create a mock task for testing
 */
function createMockTask(overrides: Partial<Task> = {}): Task {
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
 * Create a diverse set of tasks for testing
 */
function createDiverseTaskSet(): Task[] {
  return [
    // High cognitive load tasks
    createMockTask({
      id: 1,
      title: "Architect new microservice",
      cognitiveLoad: "high",
      valueTier: "milestone",
      drainType: "deep",
      effortEstimate: 8,
      category: "work",
    }),
    createMockTask({
      id: 2,
      title: "Write technical spec",
      cognitiveLoad: "high",
      valueTier: "deliverable",
      drainType: "deep",
      effortEstimate: 5,
      category: "work",
    }),
    createMockTask({
      id: 3,
      title: "Solve complex algorithm bug",
      cognitiveLoad: "high",
      valueTier: "progress",
      drainType: "deep",
      effortEstimate: 4,
      category: "work",
      status: "active",
    }),

    // Medium cognitive load tasks
    createMockTask({
      id: 4,
      title: "Code review PR #123",
      cognitiveLoad: "medium",
      valueTier: "progress",
      drainType: "shallow",
      effortEstimate: 3,
      category: "work",
    }),
    createMockTask({
      id: 5,
      title: "Update documentation",
      cognitiveLoad: "medium",
      valueTier: "progress",
      drainType: "shallow",
      effortEstimate: 2,
      category: "work",
    }),
    createMockTask({
      id: 6,
      title: "Refactor helper functions",
      cognitiveLoad: "medium",
      valueTier: "progress",
      drainType: "shallow",
      effortEstimate: 4,
      category: "work",
      status: "active",
    }),

    // Low cognitive load tasks
    createMockTask({
      id: 7,
      title: "Reply to emails",
      cognitiveLoad: "low",
      valueTier: "checkbox",
      drainType: "admin",
      effortEstimate: 1,
      category: "work",
    }),
    createMockTask({
      id: 8,
      title: "File expense reports",
      cognitiveLoad: "low",
      valueTier: "checkbox",
      drainType: "admin",
      effortEstimate: 1,
      category: "work",
    }),
    createMockTask({
      id: 9,
      title: "Organize workspace",
      cognitiveLoad: "low",
      valueTier: "checkbox",
      drainType: "admin",
      effortEstimate: 2,
      category: "personal",
    }),
    createMockTask({
      id: 10,
      title: "Schedule meetings",
      cognitiveLoad: "low",
      valueTier: "checkbox",
      drainType: "admin",
      effortEstimate: 1,
      category: "work",
    }),
  ];
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
 * Assert that a value is within a range
 */
function assertInRange(
  value: number,
  min: number,
  max: number,
  message: string
): void {
  if (value < min || value > max) {
    throw new Error(
      `❌ ${message}\n   Expected: ${min} <= ${value} <= ${max}\n   Actual: ${value}`
    );
  }
  console.log(`✅ ${message}`);
}

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

/**
 * Test: workos_get_energy_aware_tasks with HIGH energy level
 *
 * Simulates the MCP tool being called with high energy
 * Should prioritize high cognitive load tasks, deep work, and milestones
 */
function testGetEnergyAwareTasksHighEnergy(): void {
  console.log("\n📋 Testing workos_get_energy_aware_tasks - High Energy");
  console.log("━".repeat(60));

  const tasks = createDiverseTaskSet();
  const energyLevel: EnergyLevel = "high";

  // Simulate the handler logic: rank tasks by energy
  const rankedTasks = rankTasksByEnergy(tasks, energyLevel, 5);

  // Assertions
  assert(
    rankedTasks.length === 5,
    "Should return 5 tasks when limit=5"
  );

  // First task should be high cognitive load
  assert(
    rankedTasks[0].cognitiveLoad === "high",
    "Top task should have high cognitive load for high energy"
  );

  // Check that high cognitive tasks are ranked higher
  const highCogTasksInTop3 = rankedTasks
    .slice(0, 3)
    .filter((t) => t.cognitiveLoad === "high").length;
  assert(
    highCogTasksInTop3 >= 2,
    "At least 2 of top 3 tasks should be high cognitive load"
  );

  // All tasks should have energy scores and match reasons
  assert(
    rankedTasks.every((t) => t.energyScore > 0),
    "All tasks should have energy scores > 0"
  );
  assert(
    rankedTasks.every((t) => t.matchReason && t.matchReason.length > 0),
    "All tasks should have match reasons"
  );

  // Tasks should be sorted descending by energy score
  for (let i = 0; i < rankedTasks.length - 1; i++) {
    assert(
      rankedTasks[i].energyScore >= rankedTasks[i + 1].energyScore,
      `Task ${i} should have higher or equal score than task ${i + 1}`
    );
  }

  // Active tasks should get a bonus (check if active task is ranked well)
  const activeTask = rankedTasks.find((t) => t.status === "active");
  if (activeTask) {
    assert(
      activeTask.matchReason.includes("active") ||
        activeTask.matchReason.includes("momentum"),
      "Active task should mention active/momentum in match reason"
    );
  }

  console.log("\n🎯 Top 5 tasks for HIGH energy:");
  rankedTasks.forEach((task, idx) => {
    console.log(`   ${idx + 1}. [${task.cognitiveLoad?.toUpperCase()}] ${task.title}`);
    console.log(`      Score: ${task.energyScore} | ${task.matchReason}`);
  });

  console.log("\n✨ High energy task selection tests passed!");
}

/**
 * Test: workos_get_energy_aware_tasks with MEDIUM energy level
 *
 * Simulates the MCP tool being called with medium energy
 * Should prioritize medium cognitive load tasks and progress work
 */
function testGetEnergyAwareTasksMediumEnergy(): void {
  console.log("\n📋 Testing workos_get_energy_aware_tasks - Medium Energy");
  console.log("━".repeat(60));

  const tasks = createDiverseTaskSet();
  const energyLevel: EnergyLevel = "medium";

  // Simulate the handler logic: rank tasks by energy
  const rankedTasks = rankTasksByEnergy(tasks, energyLevel, 5);

  // Assertions
  assert(
    rankedTasks.length === 5,
    "Should return 5 tasks when limit=5"
  );

  // First task should be medium cognitive load
  assert(
    rankedTasks[0].cognitiveLoad === "medium",
    "Top task should have medium cognitive load for medium energy"
  );

  // Check that medium cognitive tasks are prioritized
  const mediumCogTasksInTop3 = rankedTasks
    .slice(0, 3)
    .filter((t) => t.cognitiveLoad === "medium").length;
  assert(
    mediumCogTasksInTop3 >= 1,
    "At least 1 of top 3 tasks should be medium cognitive load"
  );

  // Medium energy can handle variety, so we should see mixed tasks
  const uniqueCognitiveLoads = new Set(
    rankedTasks.map((t) => t.cognitiveLoad)
  );
  assert(
    uniqueCognitiveLoads.size >= 2,
    "Medium energy should handle variety of cognitive loads"
  );

  console.log("\n🎯 Top 5 tasks for MEDIUM energy:");
  rankedTasks.forEach((task, idx) => {
    console.log(`   ${idx + 1}. [${task.cognitiveLoad?.toUpperCase()}] ${task.title}`);
    console.log(`      Score: ${task.energyScore} | ${task.matchReason}`);
  });

  console.log("\n✨ Medium energy task selection tests passed!");
}

/**
 * Test: workos_get_energy_aware_tasks with LOW energy level
 *
 * Simulates the MCP tool being called with low energy
 * Should prioritize low cognitive load tasks, admin work, and quick wins
 */
function testGetEnergyAwareTasksLowEnergy(): void {
  console.log("\n📋 Testing workos_get_energy_aware_tasks - Low Energy");
  console.log("━".repeat(60));

  const tasks = createDiverseTaskSet();
  const energyLevel: EnergyLevel = "low";

  // Simulate the handler logic: rank tasks by energy
  const rankedTasks = rankTasksByEnergy(tasks, energyLevel, 5);

  // Assertions
  assert(
    rankedTasks.length === 5,
    "Should return 5 tasks when limit=5"
  );

  // First task should be low cognitive load
  assert(
    rankedTasks[0].cognitiveLoad === "low",
    "Top task should have low cognitive load for low energy"
  );

  // Check that low cognitive tasks dominate the top rankings
  const lowCogTasksInTop3 = rankedTasks
    .slice(0, 3)
    .filter((t) => t.cognitiveLoad === "low").length;
  assert(
    lowCogTasksInTop3 >= 2,
    "At least 2 of top 3 tasks should be low cognitive load"
  );

  // High cognitive tasks should be ranked last
  const lastTask = rankedTasks[rankedTasks.length - 1];
  assert(
    lastTask.cognitiveLoad !== "low",
    "Last task should not be low cognitive (poor match should be last)"
  );

  // Quick wins (effort <= 2) should be prioritized
  const quickWinsInTop3 = rankedTasks
    .slice(0, 3)
    .filter((t) => t.effortEstimate && t.effortEstimate <= 2).length;
  assert(
    quickWinsInTop3 >= 1,
    "At least 1 quick win (effort <= 2) should be in top 3"
  );

  // Admin work should be highlighted
  const adminTasksInTop5 = rankedTasks.filter(
    (t) => t.drainType === "admin"
  ).length;
  assert(
    adminTasksInTop5 >= 1,
    "At least 1 admin task should be in top 5 for low energy"
  );

  console.log("\n🎯 Top 5 tasks for LOW energy:");
  rankedTasks.forEach((task, idx) => {
    console.log(`   ${idx + 1}. [${task.cognitiveLoad?.toUpperCase()}] ${task.title}`);
    console.log(`      Score: ${task.energyScore} | Effort: ${task.effortEstimate}pts`);
    console.log(`      ${task.matchReason}`);
  });

  console.log("\n✨ Low energy task selection tests passed!");
}

/**
 * Test: Energy level override functionality
 *
 * Simulates workos_override_energy_suggestion behavior
 * User manually sets energy level, overriding auto-detection
 */
function testEnergyOverride(): void {
  console.log("\n📋 Testing Energy Override Functionality");
  console.log("━".repeat(60));

  const tasks = createDiverseTaskSet();

  // Scenario: User has low readiness (60) but feels energized after coffee/medication
  console.log("\n🔄 Scenario: Low readiness (60) but user overrides to HIGH");

  // Auto-detected would be low energy (readiness 60)
  const autoEnergyLevel: EnergyLevel = "low";
  const autoRanked = rankTasksByEnergy(tasks, autoEnergyLevel, 3);

  console.log("\n   Auto-detected (LOW energy) top 3:");
  autoRanked.forEach((task, idx) => {
    console.log(
      `   ${idx + 1}. [${task.cognitiveLoad?.toUpperCase()}] ${task.title} (score: ${task.energyScore})`
    );
  });

  // User overrides to high energy
  const overrideEnergyLevel: EnergyLevel = "high";
  const overrideRanked = rankTasksByEnergy(tasks, overrideEnergyLevel, 3);

  console.log("\n   User override (HIGH energy) top 3:");
  overrideRanked.forEach((task, idx) => {
    console.log(
      `   ${idx + 1}. [${task.cognitiveLoad?.toUpperCase()}] ${task.title} (score: ${task.energyScore})`
    );
  });

  // Assertions: Override should change task recommendations
  assert(
    autoRanked[0].id !== overrideRanked[0].id,
    "Override should change top task recommendation"
  );

  assert(
    autoRanked[0].cognitiveLoad === "low",
    "Auto-detect should prioritize low cognitive load"
  );

  assert(
    overrideRanked[0].cognitiveLoad === "high",
    "Override to high should prioritize high cognitive load"
  );

  // Scenario 2: User has high readiness (90) but feeling tired/distracted
  console.log("\n🔄 Scenario: High readiness (90) but user overrides to LOW");

  const autoHighRanked = rankTasksByEnergy(tasks, "high", 3);
  const overrideLowRanked = rankTasksByEnergy(tasks, "low", 3);

  console.log("\n   Auto-detected (HIGH energy) top 3:");
  autoHighRanked.forEach((task, idx) => {
    console.log(
      `   ${idx + 1}. [${task.cognitiveLoad?.toUpperCase()}] ${task.title}`
    );
  });

  console.log("\n   User override (LOW energy) top 3:");
  overrideLowRanked.forEach((task, idx) => {
    console.log(
      `   ${idx + 1}. [${task.cognitiveLoad?.toUpperCase()}] ${task.title}`
    );
  });

  assert(
    autoHighRanked[0].cognitiveLoad === "high",
    "Auto high energy should prioritize high cognitive load"
  );

  assert(
    overrideLowRanked[0].cognitiveLoad === "low",
    "Override to low should prioritize low cognitive load"
  );

  console.log("\n✨ Energy override tests passed!");
}

/**
 * Test: Daily goal adjustment with HIGH readiness
 *
 * Simulates workos_adjust_daily_goal with high readiness score
 * Should increase target by 15%
 */
function testDailyGoalAdjustmentHighReadiness(): void {
  console.log("\n📋 Testing Daily Goal Adjustment - High Readiness");
  console.log("━".repeat(60));

  // Scenario: User has excellent readiness and sleep
  const readinessScore = 92;
  const sleepScore = 88;
  const baseTarget = 18;

  const adjustment = calculateDailyGoalAdjustment(
    readinessScore,
    sleepScore,
    baseTarget
  );

  console.log("\n🎯 High Readiness Scenario:");
  console.log(`   Readiness: ${readinessScore}/100`);
  console.log(`   Sleep: ${sleepScore}/100`);
  console.log(`   Base Target: ${baseTarget} points`);
  console.log(`   Adjusted Target: ${adjustment.adjustedTarget} points`);
  console.log(`   Adjustment: ${adjustment.adjustmentPercentage}%`);
  console.log(`   Energy Level: ${adjustment.energyLevel}`);
  console.log(`   Reasoning: ${adjustment.reason}`);

  // Assertions
  assertEqual(
    adjustment.energyLevel,
    "high",
    "High readiness (92) should map to high energy"
  );

  assertEqual(
    adjustment.adjustmentPercentage,
    15,
    "High readiness should have +15% adjustment"
  );

  assertEqual(
    adjustment.adjustedTarget,
    Math.round(baseTarget * 1.15),
    "Adjusted target should be base * 1.15"
  );

  assert(
    adjustment.reason.includes("High readiness"),
    "Reason should mention high readiness"
  );

  assert(
    adjustment.reason.includes("Sleep quality"),
    "Reason should include sleep score context"
  );

  assertEqual(
    adjustment.readinessScore,
    readinessScore,
    "Should preserve readiness score"
  );

  assertEqual(
    adjustment.sleepScore,
    sleepScore,
    "Should preserve sleep score"
  );

  console.log("\n✨ High readiness adjustment tests passed!");
}

/**
 * Test: Daily goal adjustment with MEDIUM readiness
 *
 * Simulates workos_adjust_daily_goal with medium readiness score
 * Should maintain standard target (0% adjustment)
 */
function testDailyGoalAdjustmentMediumReadiness(): void {
  console.log("\n📋 Testing Daily Goal Adjustment - Medium Readiness");
  console.log("━".repeat(60));

  // Scenario: User has good readiness
  const readinessScore = 77;
  const sleepScore = 75;
  const baseTarget = 18;

  const adjustment = calculateDailyGoalAdjustment(
    readinessScore,
    sleepScore,
    baseTarget
  );

  console.log("\n🎯 Medium Readiness Scenario:");
  console.log(`   Readiness: ${readinessScore}/100`);
  console.log(`   Sleep: ${sleepScore}/100`);
  console.log(`   Base Target: ${baseTarget} points`);
  console.log(`   Adjusted Target: ${adjustment.adjustedTarget} points`);
  console.log(`   Adjustment: ${adjustment.adjustmentPercentage}%`);
  console.log(`   Energy Level: ${adjustment.energyLevel}`);
  console.log(`   Reasoning: ${adjustment.reason}`);

  // Assertions
  assertEqual(
    adjustment.energyLevel,
    "medium",
    "Medium readiness (77) should map to medium energy"
  );

  assertEqual(
    adjustment.adjustmentPercentage,
    0,
    "Medium readiness should have 0% adjustment"
  );

  assertEqual(
    adjustment.adjustedTarget,
    baseTarget,
    "Adjusted target should equal base target"
  );

  assert(
    adjustment.reason.includes("Good readiness"),
    "Reason should mention good readiness"
  );

  console.log("\n✨ Medium readiness adjustment tests passed!");
}

/**
 * Test: Daily goal adjustment with LOW readiness
 *
 * Simulates workos_adjust_daily_goal with low readiness score
 * Should reduce target by 25%
 */
function testDailyGoalAdjustmentLowReadiness(): void {
  console.log("\n📋 Testing Daily Goal Adjustment - Low Readiness");
  console.log("━".repeat(60));

  // Scenario: User had poor sleep and low readiness
  const readinessScore = 55;
  const sleepScore = 48;
  const baseTarget = 18;

  const adjustment = calculateDailyGoalAdjustment(
    readinessScore,
    sleepScore,
    baseTarget
  );

  console.log("\n🎯 Low Readiness Scenario:");
  console.log(`   Readiness: ${readinessScore}/100`);
  console.log(`   Sleep: ${sleepScore}/100`);
  console.log(`   Base Target: ${baseTarget} points`);
  console.log(`   Adjusted Target: ${adjustment.adjustedTarget} points`);
  console.log(`   Adjustment: ${adjustment.adjustmentPercentage}%`);
  console.log(`   Energy Level: ${adjustment.energyLevel}`);
  console.log(`   Reasoning: ${adjustment.reason}`);

  // Assertions
  assertEqual(
    adjustment.energyLevel,
    "low",
    "Low readiness (55) should map to low energy"
  );

  assertEqual(
    adjustment.adjustmentPercentage,
    -25,
    "Low readiness should have -25% adjustment"
  );

  assertEqual(
    adjustment.adjustedTarget,
    Math.round(baseTarget * 0.75),
    "Adjusted target should be base * 0.75"
  );

  assert(
    adjustment.reason.includes("Low readiness"),
    "Reason should mention low readiness"
  );

  assert(
    adjustment.reason.includes("prevent burnout"),
    "Reason should mention preventing burnout"
  );

  assertEqual(
    adjustment.readinessScore,
    readinessScore,
    "Should preserve readiness score"
  );

  console.log("\n✨ Low readiness adjustment tests passed!");
}

/**
 * Test: Daily goal adjustment with different base targets
 *
 * Tests that adjustment percentages work correctly with non-standard targets
 */
function testDailyGoalAdjustmentVariousTargets(): void {
  console.log("\n📋 Testing Daily Goal Adjustment - Various Base Targets");
  console.log("━".repeat(60));

  const scenarios = [
    { baseTarget: 12, readiness: 90, expectedAdjustment: 15 },
    { baseTarget: 24, readiness: 75, expectedAdjustment: 0 },
    { baseTarget: 30, readiness: 60, expectedAdjustment: -25 },
  ];

  scenarios.forEach(({ baseTarget, readiness, expectedAdjustment }) => {
    const adjustment = calculateDailyGoalAdjustment(readiness, null, baseTarget);

    console.log(
      `\n   Base: ${baseTarget}pts, Readiness: ${readiness} → Adjusted: ${adjustment.adjustedTarget}pts (${adjustment.adjustmentPercentage}%)`
    );

    assertEqual(
      adjustment.adjustmentPercentage,
      expectedAdjustment,
      `Readiness ${readiness} should have ${expectedAdjustment}% adjustment`
    );

    const expectedTarget = Math.round(
      baseTarget * (1 + expectedAdjustment / 100)
    );
    assertEqual(
      adjustment.adjustedTarget,
      expectedTarget,
      `Adjusted target should be ${expectedTarget} for base ${baseTarget}`
    );
  });

  console.log("\n✨ Various target adjustment tests passed!");
}

/**
 * Test: Realistic workflow scenarios
 *
 * End-to-end simulation of typical user workflows
 */
function testRealisticWorkflows(): void {
  console.log("\n📋 Testing Realistic User Workflows");
  console.log("━".repeat(60));

  // Workflow 1: Monday morning after poor weekend sleep
  console.log("\n🌅 Workflow 1: Monday Morning Recovery");
  console.log("   Context: Poor sleep, low readiness, need to ease into week");

  const mondayReadiness = 58;
  const mondaySleep = 52;
  const mondayGoal = calculateDailyGoalAdjustment(
    mondayReadiness,
    mondaySleep,
    18
  );

  console.log(`   → Readiness: ${mondayReadiness}, Sleep: ${mondaySleep}`);
  console.log(`   → Goal: ${mondayGoal.originalTarget} → ${mondayGoal.adjustedTarget} points (${mondayGoal.adjustmentPercentage}%)`);
  console.log(`   → Energy: ${mondayGoal.energyLevel}`);

  const mondayTasks = rankTasksByEnergy(createDiverseTaskSet(), "low", 3);
  console.log("   → Top 3 recommended tasks:");
  mondayTasks.forEach((task, idx) => {
    console.log(`      ${idx + 1}. ${task.title} (${task.cognitiveLoad}, effort: ${task.effortEstimate}pts)`);
  });

  assert(
    mondayGoal.adjustedTarget < mondayGoal.originalTarget,
    "Monday recovery should reduce target"
  );
  assert(
    mondayTasks.every((t) => (t.effortEstimate || 0) <= 2),
    "Monday tasks should be quick wins (effort <= 2)"
  );

  // Workflow 2: Friday high energy sprint
  console.log("\n⚡ Workflow 2: Friday High Energy Sprint");
  console.log("   Context: Great sleep, high readiness, maximize impact");

  const fridayReadiness = 94;
  const fridaySleep = 90;
  const fridayGoal = calculateDailyGoalAdjustment(
    fridayReadiness,
    fridaySleep,
    18
  );

  console.log(`   → Readiness: ${fridayReadiness}, Sleep: ${fridaySleep}`);
  console.log(`   → Goal: ${fridayGoal.originalTarget} → ${fridayGoal.adjustedTarget} points (+${fridayGoal.adjustmentPercentage}%)`);
  console.log(`   → Energy: ${fridayGoal.energyLevel}`);

  const fridayTasks = rankTasksByEnergy(createDiverseTaskSet(), "high", 3);
  console.log("   → Top 3 recommended tasks:");
  fridayTasks.forEach((task, idx) => {
    console.log(`      ${idx + 1}. ${task.title} (${task.cognitiveLoad}, value: ${task.valueTier})`);
  });

  assert(
    fridayGoal.adjustedTarget > fridayGoal.originalTarget,
    "Friday high energy should increase target"
  );
  assert(
    fridayTasks.every((t) => t.cognitiveLoad === "high"),
    "Friday tasks should be high cognitive load"
  );

  // Workflow 3: ADHD user with medication timing
  console.log("\n💊 Workflow 3: ADHD User - Medication Window");
  console.log("   Context: Low morning readiness, but medication provides 4hr high-energy window");

  // Morning: Low readiness detected
  const morningReadiness = 65;
  const morningEnergy: EnergyLevel = "low";

  // User takes medication and overrides to high energy
  const medicationEnergy: EnergyLevel = "high";

  console.log(`   → Morning readiness: ${morningReadiness} (auto: ${morningEnergy})`);
  console.log(`   → After medication: User override to ${medicationEnergy}`);

  const morningTasks = rankTasksByEnergy(createDiverseTaskSet(), morningEnergy, 3);
  const medicatedTasks = rankTasksByEnergy(createDiverseTaskSet(), medicationEnergy, 3);

  console.log("   → Without override (LOW energy):");
  morningTasks.forEach((task, idx) => {
    console.log(`      ${idx + 1}. ${task.title}`);
  });

  console.log("   → With override (HIGH energy):");
  medicatedTasks.forEach((task, idx) => {
    console.log(`      ${idx + 1}. ${task.title}`);
  });

  assert(
    morningTasks[0].cognitiveLoad === "low",
    "Without override should suggest low cognitive tasks"
  );
  assert(
    medicatedTasks[0].cognitiveLoad === "high",
    "With override should suggest high cognitive tasks"
  );
  assert(
    medicatedTasks[0].valueTier === "milestone" ||
      medicatedTasks[0].valueTier === "deliverable",
    "Override should prioritize high-value work during medication window"
  );

  console.log("\n✨ All realistic workflow tests passed!");
}

// =============================================================================
// TEST RUNNER
// =============================================================================

/**
 * Run all integration tests
 */
async function runAllTests(): Promise<void> {
  console.log("\n" + "=".repeat(60));
  console.log("🧪 Energy-Aware MCP Tools - Integration Tests");
  console.log("=".repeat(60));

  try {
    // Test 1: workos_get_energy_aware_tasks with various energy levels
    testGetEnergyAwareTasksHighEnergy();
    testGetEnergyAwareTasksMediumEnergy();
    testGetEnergyAwareTasksLowEnergy();

    // Test 2: Energy override functionality
    testEnergyOverride();

    // Test 3: Daily goal adjustment with different readiness scores
    testDailyGoalAdjustmentHighReadiness();
    testDailyGoalAdjustmentMediumReadiness();
    testDailyGoalAdjustmentLowReadiness();
    testDailyGoalAdjustmentVariousTargets();

    // Test 4: Realistic workflows
    testRealisticWorkflows();

    console.log("\n" + "=".repeat(60));
    console.log("🎉 ALL INTEGRATION TESTS PASSED!");
    console.log("=".repeat(60));
    console.log("\n✅ Test Summary:");
    console.log("   • workos_get_energy_aware_tasks (high/medium/low): ✓");
    console.log("   • Energy override functionality: ✓");
    console.log("   • Daily goal adjustments (all readiness levels): ✓");
    console.log("   • Various base targets: ✓");
    console.log("   • Realistic user workflows: ✓");
    console.log("\n📊 Coverage:");
    console.log("   • Energy-aware task selection: 3 scenarios");
    console.log("   • Override behavior: 2 scenarios");
    console.log("   • Goal adjustments: 7 scenarios");
    console.log("   • Real-world workflows: 3 scenarios");
    console.log("\n");

  } catch (error) {
    console.error("\n" + "=".repeat(60));
    console.error("❌ INTEGRATION TEST FAILED");
    console.error("=".repeat(60));
    console.error(error);
    process.exit(1);
  }
}

// Run tests if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runAllTests();
}

export {
  runAllTests,
  testGetEnergyAwareTasksHighEnergy,
  testGetEnergyAwareTasksMediumEnergy,
  testGetEnergyAwareTasksLowEnergy,
  testEnergyOverride,
  testDailyGoalAdjustmentHighReadiness,
  testDailyGoalAdjustmentMediumReadiness,
  testDailyGoalAdjustmentLowReadiness,
  testRealisticWorkflows,
};
