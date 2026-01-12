/**
 * Unit tests for energy-aware task prioritization service
 * Tests energy-to-task matching logic, daily goal adjustment calculations,
 * and edge cases (missing Oura data, no energy logs)
 */

import {
  mapReadinessToEnergyLevel,
  calculateEnergyScore,
  rankTasksByEnergy,
  calculateDailyGoalAdjustment,
  type EnergyContext,
  type ScoredTask,
  type GoalAdjustment,
} from "../../src/services/energy-prioritization.js";
import type { Task, EnergyLevel, CognitiveLoad } from "../../src/schema.js";

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
// TEST SUITES
// =============================================================================

/**
 * Test suite for mapReadinessToEnergyLevel()
 */
function testMapReadinessToEnergyLevel(): void {
  console.log("\n📋 Testing mapReadinessToEnergyLevel()");
  console.log("━".repeat(60));

  // Test high energy mapping (>= 85)
  assertEqual(
    mapReadinessToEnergyLevel(85),
    "high",
    "Readiness 85 should map to high energy"
  );
  assertEqual(
    mapReadinessToEnergyLevel(90),
    "high",
    "Readiness 90 should map to high energy"
  );
  assertEqual(
    mapReadinessToEnergyLevel(100),
    "high",
    "Readiness 100 should map to high energy"
  );

  // Test medium energy mapping (70-84)
  assertEqual(
    mapReadinessToEnergyLevel(70),
    "medium",
    "Readiness 70 should map to medium energy"
  );
  assertEqual(
    mapReadinessToEnergyLevel(77),
    "medium",
    "Readiness 77 should map to medium energy"
  );
  assertEqual(
    mapReadinessToEnergyLevel(84),
    "medium",
    "Readiness 84 should map to medium energy"
  );

  // Test low energy mapping (< 70)
  assertEqual(
    mapReadinessToEnergyLevel(69),
    "low",
    "Readiness 69 should map to low energy"
  );
  assertEqual(
    mapReadinessToEnergyLevel(50),
    "low",
    "Readiness 50 should map to low energy"
  );
  assertEqual(
    mapReadinessToEnergyLevel(0),
    "low",
    "Readiness 0 should map to low energy"
  );

  // Test boundary conditions
  assertEqual(
    mapReadinessToEnergyLevel(84.9),
    "medium",
    "Readiness 84.9 should map to medium energy (boundary)"
  );
  assertEqual(
    mapReadinessToEnergyLevel(69.9),
    "low",
    "Readiness 69.9 should map to low energy (boundary)"
  );

  console.log("✨ All mapReadinessToEnergyLevel tests passed!");
}

/**
 * Test suite for calculateEnergyScore() - High Energy
 */
function testCalculateEnergyScoreHighEnergy(): void {
  console.log("\n📋 Testing calculateEnergyScore() - High Energy");
  console.log("━".repeat(60));

  // Perfect match: High cognitive load on high energy
  const highCogTask = createMockTask({ cognitiveLoad: "high" });
  const { score: score1, reason: reason1 } = calculateEnergyScore(
    highCogTask,
    "high"
  );
  assertInRange(
    score1,
    100,
    165,
    "High cognitive task on high energy should score 100+"
  );
  assert(
    reason1.includes("Perfect match"),
    "Reason should mention perfect match"
  );

  // High energy + High value task
  const milestoneTask = createMockTask({
    cognitiveLoad: "high",
    valueTier: "milestone",
  });
  const { score: score2 } = calculateEnergyScore(milestoneTask, "high");
  assertInRange(
    score2,
    120,
    165,
    "High cognitive milestone task should score 120+ (100 base + 20 value bonus)"
  );

  // High energy + Deep work
  const deepWorkTask = createMockTask({
    cognitiveLoad: "high",
    drainType: "deep",
  });
  const { score: score3 } = calculateEnergyScore(deepWorkTask, "high");
  assertInRange(
    score3,
    110,
    165,
    "High cognitive deep work task should score 110+ (100 base + 10 drain bonus)"
  );

  // High energy + Large effort
  const largeTask = createMockTask({
    cognitiveLoad: "high",
    effortEstimate: 6,
  });
  const { score: score4 } = calculateEnergyScore(largeTask, "high");
  assertInRange(
    score4,
    110,
    165,
    "High cognitive large task should score 110+ (100 base + 10 effort bonus)"
  );

  // Medium cognitive load on high energy (acceptable)
  const mediumCogTask = createMockTask({ cognitiveLoad: "medium" });
  const { score: score5, reason: reason5 } = calculateEnergyScore(
    mediumCogTask,
    "high"
  );
  assertInRange(
    score5,
    50,
    99,
    "Medium cognitive task on high energy should score 50+"
  );
  assert(
    reason5.includes("Good match") || reason5.includes("Acceptable"),
    "Reason should mention good/acceptable match"
  );

  // Low cognitive load on high energy (poor match)
  const lowCogTask = createMockTask({ cognitiveLoad: "low" });
  const { score: score6, reason: reason6 } = calculateEnergyScore(
    lowCogTask,
    "high"
  );
  assertInRange(
    score6,
    0,
    49,
    "Low cognitive task on high energy should score low (0-49)"
  );
  assert(
    reason6.includes("Low priority") || reason6.includes("Avoid"),
    "Reason should mention low priority or avoid"
  );

  console.log("✨ All high energy scoring tests passed!");
}

/**
 * Test suite for calculateEnergyScore() - Medium Energy
 */
function testCalculateEnergyScoreMediumEnergy(): void {
  console.log("\n📋 Testing calculateEnergyScore() - Medium Energy");
  console.log("━".repeat(60));

  // Perfect match: Medium cognitive load on medium energy
  const mediumCogTask = createMockTask({ cognitiveLoad: "medium" });
  const { score: score1, reason: reason1 } = calculateEnergyScore(
    mediumCogTask,
    "medium"
  );
  assertInRange(
    score1,
    100,
    165,
    "Medium cognitive task on medium energy should score 100+"
  );
  assert(
    reason1.includes("Perfect match"),
    "Reason should mention perfect match"
  );

  // Medium energy + Progress task
  const progressTask = createMockTask({
    cognitiveLoad: "medium",
    valueTier: "progress",
  });
  const { score: score2 } = calculateEnergyScore(progressTask, "medium");
  assertInRange(
    score2,
    120,
    165,
    "Medium cognitive progress task should score 120+ (100 base + 20 value bonus)"
  );

  // Medium energy + Shallow work
  const shallowTask = createMockTask({
    cognitiveLoad: "medium",
    drainType: "shallow",
  });
  const { score: score3 } = calculateEnergyScore(shallowTask, "medium");
  assertInRange(
    score3,
    110,
    165,
    "Medium cognitive shallow work should score 110+ (100 base + 10 drain bonus)"
  );

  // Medium energy + Medium effort (2-4 points)
  const mediumEffortTask = createMockTask({
    cognitiveLoad: "medium",
    effortEstimate: 3,
  });
  const { score: score4 } = calculateEnergyScore(mediumEffortTask, "medium");
  assertInRange(
    score4,
    105,
    165,
    "Medium cognitive medium-effort task should score 105+ (100 base + 5 effort bonus)"
  );

  // High/low cognitive load on medium energy (acceptable)
  const highCogTask = createMockTask({ cognitiveLoad: "high" });
  const { score: score5 } = calculateEnergyScore(highCogTask, "medium");
  assertInRange(
    score5,
    50,
    99,
    "High cognitive task on medium energy should score 50+"
  );

  const lowCogTask = createMockTask({ cognitiveLoad: "low" });
  const { score: score6 } = calculateEnergyScore(lowCogTask, "medium");
  assertInRange(
    score6,
    50,
    99,
    "Low cognitive task on medium energy should score 50+"
  );

  console.log("✨ All medium energy scoring tests passed!");
}

/**
 * Test suite for calculateEnergyScore() - Low Energy
 */
function testCalculateEnergyScoreLowEnergy(): void {
  console.log("\n📋 Testing calculateEnergyScore() - Low Energy");
  console.log("━".repeat(60));

  // Perfect match: Low cognitive load on low energy
  const lowCogTask = createMockTask({ cognitiveLoad: "low" });
  const { score: score1, reason: reason1 } = calculateEnergyScore(
    lowCogTask,
    "low"
  );
  assertInRange(
    score1,
    100,
    165,
    "Low cognitive task on low energy should score 100+"
  );
  assert(
    reason1.includes("Perfect match"),
    "Reason should mention perfect match"
  );

  // Low energy + Checkbox task
  const checkboxTask = createMockTask({
    cognitiveLoad: "low",
    valueTier: "checkbox",
  });
  const { score: score2 } = calculateEnergyScore(checkboxTask, "low");
  assertInRange(
    score2,
    120,
    165,
    "Low cognitive checkbox task should score 120+ (100 base + 20 value bonus)"
  );

  // Low energy + Admin work
  const adminTask = createMockTask({
    cognitiveLoad: "low",
    drainType: "admin",
  });
  const { score: score3 } = calculateEnergyScore(adminTask, "low");
  assertInRange(
    score3,
    110,
    165,
    "Low cognitive admin work should score 110+ (100 base + 10 drain bonus)"
  );

  // Low energy + Quick win (effort <= 2)
  const quickWinTask = createMockTask({
    cognitiveLoad: "low",
    effortEstimate: 1,
  });
  const { score: score4 } = calculateEnergyScore(quickWinTask, "low");
  assertInRange(
    score4,
    115,
    165,
    "Low cognitive quick win should score 115+ (100 base + 15 effort bonus)"
  );

  // Low energy + Personal task
  const personalTask = createMockTask({
    cognitiveLoad: "low",
    category: "personal",
  });
  const { score: score5 } = calculateEnergyScore(personalTask, "low");
  assertInRange(
    score5,
    105,
    165,
    "Low cognitive personal task should score 105+ (100 base + 5 category bonus)"
  );

  // Medium cognitive load on low energy (acceptable)
  const mediumCogTask = createMockTask({ cognitiveLoad: "medium" });
  const { score: score6 } = calculateEnergyScore(mediumCogTask, "low");
  assertInRange(
    score6,
    50,
    99,
    "Medium cognitive task on low energy should score 50+"
  );

  // High cognitive load on low energy (poor match - should avoid)
  const highCogTask = createMockTask({ cognitiveLoad: "high" });
  const { score: score7, reason: reason7 } = calculateEnergyScore(
    highCogTask,
    "low"
  );
  assertInRange(
    score7,
    0,
    49,
    "High cognitive task on low energy should score low (0-49)"
  );
  assert(
    reason7.includes("Avoid"),
    "Reason should mention avoiding this task"
  );

  console.log("✨ All low energy scoring tests passed!");
}

/**
 * Test suite for calculateEnergyScore() - Cross-energy bonuses
 */
function testCalculateEnergyScoreCrossEnergyBonuses(): void {
  console.log("\n📋 Testing calculateEnergyScore() - Cross-Energy Bonuses");
  console.log("━".repeat(60));

  // Active task bonus (applies to all energy levels)
  const activeTask = createMockTask({
    cognitiveLoad: "medium",
    status: "active",
  });

  const highEnergyScore = calculateEnergyScore(activeTask, "high").score;
  const mediumEnergyScore = calculateEnergyScore(activeTask, "medium").score;
  const lowEnergyScore = calculateEnergyScore(activeTask, "low").score;

  // All should include the +5 active bonus
  assert(
    highEnergyScore >= 55,
    "Active task on high energy should include +5 bonus"
  );
  assert(
    mediumEnergyScore >= 105,
    "Active task on medium energy should include +5 bonus (100 base + 5 active)"
  );
  assert(
    lowEnergyScore >= 55,
    "Active task on low energy should include +5 bonus"
  );

  // Combined bonuses test: All applicable bonuses
  const superTask = createMockTask({
    cognitiveLoad: "low",
    valueTier: "checkbox",
    drainType: "admin",
    effortEstimate: 1,
    category: "personal",
    status: "active",
  });
  const { score: superScore, reason: superReason } = calculateEnergyScore(
    superTask,
    "low"
  );

  // Should have: 100 base + 20 value + 10 drain + 15 effort + 5 category + 5 active = 155
  assertInRange(
    superScore,
    150,
    160,
    "Task with all low-energy bonuses should score ~155 points"
  );
  assert(
    superReason.includes("Perfect match"),
    "Super task should have perfect match reason"
  );

  console.log("✨ All cross-energy bonus tests passed!");
}

/**
 * Test suite for rankTasksByEnergy()
 */
function testRankTasksByEnergy(): void {
  console.log("\n📋 Testing rankTasksByEnergy()");
  console.log("━".repeat(60));

  // Create a diverse set of tasks
  const tasks: Task[] = [
    createMockTask({
      id: 1,
      title: "High cognitive deep work",
      cognitiveLoad: "high",
      drainType: "deep",
    }),
    createMockTask({
      id: 2,
      title: "Medium cognitive progress",
      cognitiveLoad: "medium",
      valueTier: "progress",
    }),
    createMockTask({
      id: 3,
      title: "Low cognitive admin",
      cognitiveLoad: "low",
      drainType: "admin",
    }),
    createMockTask({
      id: 4,
      title: "Quick win checkbox",
      cognitiveLoad: "low",
      valueTier: "checkbox",
      effortEstimate: 1,
    }),
    createMockTask({
      id: 5,
      title: "High value milestone",
      cognitiveLoad: "high",
      valueTier: "milestone",
    }),
  ];

  // Test ranking for high energy
  const highEnergyRanked = rankTasksByEnergy(tasks, "high");
  assert(
    highEnergyRanked.length === 5,
    "High energy ranking should return all 5 tasks"
  );
  assert(
    highEnergyRanked[0].cognitiveLoad === "high",
    "First task for high energy should have high cognitive load"
  );
  assert(
    highEnergyRanked[0].energyScore > highEnergyRanked[1].energyScore,
    "Tasks should be sorted by energy score (descending)"
  );

  // Test ranking for medium energy
  const mediumEnergyRanked = rankTasksByEnergy(tasks, "medium");
  assert(
    mediumEnergyRanked.length === 5,
    "Medium energy ranking should return all 5 tasks"
  );
  assert(
    mediumEnergyRanked[0].cognitiveLoad === "medium",
    "First task for medium energy should have medium cognitive load"
  );

  // Test ranking for low energy
  const lowEnergyRanked = rankTasksByEnergy(tasks, "low");
  assert(
    lowEnergyRanked.length === 5,
    "Low energy ranking should return all 5 tasks"
  );
  assert(
    lowEnergyRanked[0].cognitiveLoad === "low",
    "First task for low energy should have low cognitive load"
  );
  assert(
    lowEnergyRanked[lowEnergyRanked.length - 1].cognitiveLoad !== "low",
    "Last task for low energy should not be low cognitive (poor match)"
  );

  // Test with limit parameter
  const limitedRanked = rankTasksByEnergy(tasks, "high", 3);
  assert(
    limitedRanked.length === 3,
    "Ranking with limit=3 should return exactly 3 tasks"
  );

  // Test that all scored tasks have matchReason
  assert(
    highEnergyRanked.every((task) => task.matchReason && task.matchReason.length > 0),
    "All ranked tasks should have non-empty matchReason"
  );

  console.log("✨ All rankTasksByEnergy tests passed!");
}

/**
 * Test suite for calculateDailyGoalAdjustment()
 */
function testCalculateDailyGoalAdjustment(): void {
  console.log("\n📋 Testing calculateDailyGoalAdjustment()");
  console.log("━".repeat(60));

  const baseTarget = 18;

  // Test high readiness (>= 85): +15% increase
  const highAdjustment = calculateDailyGoalAdjustment(90, 85, baseTarget);
  assertEqual(
    highAdjustment.adjustmentPercentage,
    15,
    "High readiness (90) should have +15% adjustment"
  );
  assertEqual(
    highAdjustment.adjustedTarget,
    Math.round(baseTarget * 1.15),
    "High readiness adjusted target should be base * 1.15"
  );
  assertEqual(
    highAdjustment.energyLevel,
    "high",
    "High readiness should map to high energy level"
  );
  assert(
    highAdjustment.reason.includes("High readiness"),
    "High readiness reason should mention high readiness"
  );
  assert(
    highAdjustment.reason.includes("Sleep quality: 85"),
    "Reason should include sleep score when provided"
  );

  // Test medium readiness (70-84): no adjustment
  const mediumAdjustment = calculateDailyGoalAdjustment(77, 75, baseTarget);
  assertEqual(
    mediumAdjustment.adjustmentPercentage,
    0,
    "Medium readiness (77) should have 0% adjustment"
  );
  assertEqual(
    mediumAdjustment.adjustedTarget,
    baseTarget,
    "Medium readiness adjusted target should equal base target"
  );
  assertEqual(
    mediumAdjustment.energyLevel,
    "medium",
    "Medium readiness should map to medium energy level"
  );
  assert(
    mediumAdjustment.reason.includes("Good readiness"),
    "Medium readiness reason should mention good readiness"
  );

  // Test low readiness (< 70): -25% reduction
  const lowAdjustment = calculateDailyGoalAdjustment(60, 55, baseTarget);
  assertEqual(
    lowAdjustment.adjustmentPercentage,
    -25,
    "Low readiness (60) should have -25% adjustment"
  );
  assertEqual(
    lowAdjustment.adjustedTarget,
    Math.round(baseTarget * 0.75),
    "Low readiness adjusted target should be base * 0.75"
  );
  assertEqual(
    lowAdjustment.energyLevel,
    "low",
    "Low readiness should map to low energy level"
  );
  assert(
    lowAdjustment.reason.includes("Low readiness"),
    "Low readiness reason should mention low readiness"
  );
  assert(
    lowAdjustment.reason.includes("prevent burnout"),
    "Low readiness reason should mention preventing burnout"
  );

  // Test boundary conditions
  const boundary85 = calculateDailyGoalAdjustment(85, null, baseTarget);
  assertEqual(
    boundary85.adjustmentPercentage,
    15,
    "Readiness exactly 85 should trigger +15% adjustment"
  );

  const boundary70 = calculateDailyGoalAdjustment(70, null, baseTarget);
  assertEqual(
    boundary70.adjustmentPercentage,
    0,
    "Readiness exactly 70 should have 0% adjustment"
  );

  const boundary69 = calculateDailyGoalAdjustment(69, null, baseTarget);
  assertEqual(
    boundary69.adjustmentPercentage,
    -25,
    "Readiness 69 should trigger -25% reduction"
  );

  console.log("✨ All calculateDailyGoalAdjustment tests passed!");
}

/**
 * Test suite for edge cases - Missing Oura data
 */
function testEdgeCasesMissingOuraData(): void {
  console.log("\n📋 Testing Edge Cases - Missing Oura Data");
  console.log("━".repeat(60));

  // Test null readiness score
  const nullAdjustment = calculateDailyGoalAdjustment(null, null, 18);
  assertEqual(
    nullAdjustment.adjustmentPercentage,
    0,
    "Null readiness should have 0% adjustment"
  );
  assertEqual(
    nullAdjustment.adjustedTarget,
    18,
    "Null readiness should use base target without adjustment"
  );
  assertEqual(
    nullAdjustment.energyLevel,
    "medium",
    "Null readiness should default to medium energy"
  );
  assertEqual(
    nullAdjustment.readinessScore,
    null,
    "Null readiness should preserve null in result"
  );
  assertEqual(
    nullAdjustment.sleepScore,
    null,
    "Null sleep score should preserve null in result"
  );
  assert(
    nullAdjustment.reason.includes("No energy data available"),
    "Null readiness reason should mention no data available"
  );

  // Test with readiness but no sleep score
  const noSleepAdjustment = calculateDailyGoalAdjustment(85, null, 18);
  assertEqual(
    noSleepAdjustment.readinessScore,
    85,
    "Readiness should be preserved even without sleep score"
  );
  assertEqual(
    noSleepAdjustment.sleepScore,
    null,
    "Sleep score should be null when not provided"
  );
  assert(
    !noSleepAdjustment.reason.includes("Sleep quality"),
    "Reason should not mention sleep when sleep score is null"
  );

  // Test tasks with missing cognitive load (should default to medium)
  const taskNoCognitiveLoad = createMockTask({ cognitiveLoad: null as any });
  const { score, reason } = calculateEnergyScore(taskNoCognitiveLoad, "medium");
  assertInRange(
    score,
    100,
    165,
    "Task with null cognitive load should default to medium and score high on medium energy"
  );

  // Test empty task array
  const emptyRanked = rankTasksByEnergy([], "high");
  assert(
    emptyRanked.length === 0,
    "Ranking empty task array should return empty array"
  );

  // Test single task
  const singleTask = [createMockTask({ cognitiveLoad: "high" })];
  const singleRanked = rankTasksByEnergy(singleTask, "high");
  assert(
    singleRanked.length === 1,
    "Ranking single task should return array with one task"
  );
  assert(
    singleRanked[0].energyScore > 0,
    "Single task should have energy score calculated"
  );

  console.log("✨ All edge case tests passed!");
}

/**
 * Test suite for edge cases - No energy logs
 */
function testEdgeCasesNoEnergyLogs(): void {
  console.log("\n📋 Testing Edge Cases - No Energy Logs");
  console.log("━".repeat(60));

  // These tests would require mocking the database
  // For now, we verify the pure functions handle null/missing data gracefully

  // Test very low readiness scores
  const veryLowAdjustment = calculateDailyGoalAdjustment(10, 20, 18);
  assertEqual(
    veryLowAdjustment.energyLevel,
    "low",
    "Very low readiness (10) should map to low energy"
  );
  assertEqual(
    veryLowAdjustment.adjustmentPercentage,
    -25,
    "Very low readiness should still use -25% reduction"
  );

  // Test very high readiness scores
  const veryHighAdjustment = calculateDailyGoalAdjustment(100, 100, 18);
  assertEqual(
    veryHighAdjustment.energyLevel,
    "high",
    "Very high readiness (100) should map to high energy"
  );
  assertEqual(
    veryHighAdjustment.adjustmentPercentage,
    15,
    "Very high readiness should still use +15% increase"
  );

  // Test with different base targets
  const customBaseTarget = calculateDailyGoalAdjustment(85, null, 24);
  assertEqual(
    customBaseTarget.originalTarget,
    24,
    "Custom base target should be preserved"
  );
  assertEqual(
    customBaseTarget.adjustedTarget,
    Math.round(24 * 1.15),
    "Custom base target should be adjusted correctly"
  );

  // Test zero base target edge case
  const zeroBaseTarget = calculateDailyGoalAdjustment(85, null, 0);
  assertEqual(
    zeroBaseTarget.adjustedTarget,
    0,
    "Zero base target should remain zero even with adjustment"
  );

  console.log("✨ All no-energy-logs edge case tests passed!");
}

/**
 * Test suite for realistic scenarios
 */
function testRealisticScenarios(): void {
  console.log("\n📋 Testing Realistic Scenarios");
  console.log("━".repeat(60));

  // Scenario 1: Monday morning after poor sleep
  console.log("\n🌅 Scenario: Monday morning after poor sleep (readiness: 55)");
  const mondayAdjustment = calculateDailyGoalAdjustment(55, 45, 18);
  console.log(`   Original target: ${mondayAdjustment.originalTarget} points`);
  console.log(`   Adjusted target: ${mondayAdjustment.adjustedTarget} points (${mondayAdjustment.adjustmentPercentage}%)`);
  console.log(`   Energy level: ${mondayAdjustment.energyLevel}`);
  console.log(`   Reasoning: ${mondayAdjustment.reason}`);

  // Scenario 2: Friday feeling great
  console.log("\n🎉 Scenario: Friday feeling great (readiness: 92)");
  const fridayAdjustment = calculateDailyGoalAdjustment(92, 88, 18);
  console.log(`   Original target: ${fridayAdjustment.originalTarget} points`);
  console.log(`   Adjusted target: ${fridayAdjustment.adjustedTarget} points (${fridayAdjustment.adjustmentPercentage}%)`);
  console.log(`   Energy level: ${fridayAdjustment.energyLevel}`);
  console.log(`   Reasoning: ${fridayAdjustment.reason}`);

  // Scenario 3: Task selection for ADHD user with low energy
  console.log("\n🧠 Scenario: ADHD user with low energy selecting tasks");
  const adhdTasks: Task[] = [
    createMockTask({ id: 1, title: "Write technical documentation", cognitiveLoad: "high", drainType: "deep" }),
    createMockTask({ id: 2, title: "Reply to emails", cognitiveLoad: "low", drainType: "admin", effortEstimate: 1 }),
    createMockTask({ id: 3, title: "File expense reports", cognitiveLoad: "low", valueTier: "checkbox" }),
    createMockTask({ id: 4, title: "Code review", cognitiveLoad: "medium", drainType: "shallow" }),
    createMockTask({ id: 5, title: "Organize workspace", cognitiveLoad: "low", category: "personal", effortEstimate: 1 }),
  ];

  const lowEnergyRanked = rankTasksByEnergy(adhdTasks, "low", 3);
  console.log("   Top 3 recommended tasks:");
  lowEnergyRanked.forEach((task, idx) => {
    console.log(`   ${idx + 1}. ${task.title} (score: ${task.energyScore})`);
    console.log(`      → ${task.matchReason}`);
  });

  assert(
    lowEnergyRanked[0].cognitiveLoad === "low",
    "Top task for low energy ADHD user should be low cognitive load"
  );

  // Scenario 4: High energy day - maximize impact
  console.log("\n⚡ Scenario: High energy day - maximize impact");
  const highEnergyRanked = rankTasksByEnergy(adhdTasks, "high", 3);
  console.log("   Top 3 recommended tasks:");
  highEnergyRanked.forEach((task, idx) => {
    console.log(`   ${idx + 1}. ${task.title} (score: ${task.energyScore})`);
    console.log(`      → ${task.matchReason}`);
  });

  assert(
    highEnergyRanked[0].cognitiveLoad === "high" || highEnergyRanked[0].drainType === "deep",
    "Top task for high energy should be high cognitive load or deep work"
  );

  console.log("\n✨ All realistic scenario tests passed!");
}

// =============================================================================
// TEST RUNNER
// =============================================================================

/**
 * Run all test suites
 */
async function runAllTests(): Promise<void> {
  console.log("\n" + "=".repeat(60));
  console.log("🧪 Energy-Aware Task Prioritization Service - Unit Tests");
  console.log("=".repeat(60));

  try {
    // Core function tests
    testMapReadinessToEnergyLevel();
    testCalculateEnergyScoreHighEnergy();
    testCalculateEnergyScoreMediumEnergy();
    testCalculateEnergyScoreLowEnergy();
    testCalculateEnergyScoreCrossEnergyBonuses();
    testRankTasksByEnergy();
    testCalculateDailyGoalAdjustment();

    // Edge case tests
    testEdgeCasesMissingOuraData();
    testEdgeCasesNoEnergyLogs();

    // Realistic scenarios
    testRealisticScenarios();

    console.log("\n" + "=".repeat(60));
    console.log("🎉 ALL TESTS PASSED!");
    console.log("=".repeat(60));
    console.log("\n✅ Summary:");
    console.log("   • Energy mapping: ✓");
    console.log("   • Task scoring (all energy levels): ✓");
    console.log("   • Task ranking: ✓");
    console.log("   • Daily goal adjustment: ✓");
    console.log("   • Edge cases (missing data): ✓");
    console.log("   • Realistic scenarios: ✓");
    console.log("\n");

  } catch (error) {
    console.error("\n" + "=".repeat(60));
    console.error("❌ TEST FAILED");
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
  testMapReadinessToEnergyLevel,
  testCalculateEnergyScoreHighEnergy,
  testCalculateEnergyScoreMediumEnergy,
  testCalculateEnergyScoreLowEnergy,
  testRankTasksByEnergy,
  testCalculateDailyGoalAdjustment,
  testEdgeCasesMissingOuraData,
  testEdgeCasesNoEnergyLogs,
};
