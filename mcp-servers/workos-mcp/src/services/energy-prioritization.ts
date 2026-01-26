import type { Database } from "../shared/types.js";
import type { Task, EnergyLevel, CognitiveLoad } from "../schema.js";
import { eq, desc } from "drizzle-orm";
import * as schema from "../schema.js";
import { getESTDateString } from "../shared/utils.js";
import { getTodayOuraData } from "./oura-cache.js";

// =============================================================================
// TYPES
// =============================================================================

/**
 * Energy context containing all current energy-related data
 */
export interface EnergyContext {
  energyLevel: EnergyLevel;
  readinessScore: number | null;
  sleepScore: number | null;
  source: "oura" | "manual" | "default";
  timestamp: Date;
}

/**
 * Task with calculated energy score
 */
export interface ScoredTask extends Task {
  energyScore: number;
  matchReason: string;
}

/**
 * Daily goal adjustment result
 */
export interface GoalAdjustment {
  originalTarget: number;
  adjustedTarget: number;
  adjustmentPercentage: number;
  reason: string;
  energyLevel: EnergyLevel;
  readinessScore: number | null;
  sleepScore: number | null;
}

/**
 * Task filtering result with energy-based gating
 */
export interface TaskFilterResult {
  allowedTasks: Task[];
  filteredOutTasks: Task[];
  filterReason: string;
}

// =============================================================================
// ENERGY CONTEXT RETRIEVAL
// =============================================================================

/**
 * Get current energy context by combining multiple data sources
 *
 * Priority order:
 * 1. Today's manual energy_states entry (highest priority - user knows best)
 * 2. Today's Oura readiness & sleep scores from oura-mcp cache
 * 3. Historical energy_states with Oura data
 * 4. Default to medium energy
 *
 * @param db - Database instance
 * @returns Promise resolving to EnergyContext with current energy level, readiness, sleep scores, and source
 */
export async function getEnergyContext(
  db: Database
): Promise<EnergyContext> {
  const today = getESTDateString();

  // First priority: Check for manual energy log from today
  const [latestEnergyState] = await db
    .select()
    .from(schema.energyStates)
    .orderBy(desc(schema.energyStates.recordedAt))
    .limit(1);

  // If we have a manual energy log from today, use it (but still fetch Oura scores for context)
  if (latestEnergyState) {
    const logDate = getESTDateString(new Date(latestEnergyState.recordedAt));
    if (logDate === today) {
      // Try to enrich with today's Oura data for additional context
      const ouraData = getTodayOuraData();

      return {
        energyLevel: latestEnergyState.level as EnergyLevel,
        readinessScore: ouraData.readinessScore ?? latestEnergyState.ouraReadiness,
        sleepScore: ouraData.sleepScore,
        source: "manual",
        timestamp: new Date(latestEnergyState.recordedAt),
      };
    }
  }

  // Second priority: Use today's Oura data from cache
  const ouraData = getTodayOuraData();

  if (ouraData.readinessScore !== null) {
    return {
      energyLevel: mapReadinessToEnergyLevel(ouraData.readinessScore),
      readinessScore: ouraData.readinessScore,
      sleepScore: ouraData.sleepScore,
      source: "oura",
      timestamp: new Date(),
    };
  }

  // Third priority: Check if historical Oura data exists in energy_states
  if (latestEnergyState?.ouraReadiness) {
    return {
      energyLevel: mapReadinessToEnergyLevel(latestEnergyState.ouraReadiness),
      readinessScore: latestEnergyState.ouraReadiness,
      sleepScore: null,
      source: "oura",
      timestamp: new Date(latestEnergyState.recordedAt),
    };
  }

  // Fallback: Default to medium energy
  return {
    energyLevel: "medium",
    readinessScore: null,
    sleepScore: null,
    source: "default",
    timestamp: new Date(),
  };
}

// =============================================================================
// ENERGY MAPPING
// =============================================================================

/**
 * Map Oura readiness score (0-100) to energy level
 * - High: readiness > 75
 * - Medium: readiness 60-75
 * - Low: readiness < 60
 *
 * @param readiness - Oura readiness score (0-100)
 * @returns EnergyLevel (high, medium, or low)
 */
export function mapReadinessToEnergyLevel(readiness: number): EnergyLevel {
  if (readiness > 75) return "high";
  if (readiness >= 60) return "medium";
  return "low";
}

// =============================================================================
// TASK FILTERING
// =============================================================================

/**
 * Generate detailed explanation for why tasks were filtered
 * Provides breakdown of filtered tasks by cognitive load
 *
 * @param filteredTasks - Array of tasks that were filtered out
 * @param readinessScore - Oura readiness score that triggered filtering
 * @returns Detailed explanation string
 */
function generateFilterExplanation(
  filteredTasks: Task[],
  readinessScore: number
): string {
  if (filteredTasks.length === 0) {
    return "";
  }

  // Count tasks by cognitive load
  const loadCounts: Record<CognitiveLoad, number> = {
    low: 0,
    medium: 0,
    high: 0,
  };

  for (const task of filteredTasks) {
    const load = (task.cognitiveLoad || "medium") as CognitiveLoad;
    loadCounts[load]++;
  }

  // Build breakdown string
  const breakdown: string[] = [];
  if (loadCounts.high > 0) {
    breakdown.push(
      `${loadCounts.high} high cognitive load task${loadCounts.high === 1 ? "" : "s"}`
    );
  }
  if (loadCounts.medium > 0) {
    breakdown.push(
      `${loadCounts.medium} medium cognitive load task${loadCounts.medium === 1 ? "" : "s"}`
    );
  }
  if (loadCounts.low > 0) {
    breakdown.push(
      `${loadCounts.low} low cognitive load task${loadCounts.low === 1 ? "" : "s"}`
    );
  }

  // Generate explanation based on readiness threshold
  let explanation = ` (Filtered: ${breakdown.join(", ")}.`;

  if (readinessScore < 60) {
    explanation += " Recovery mode active - prioritizing wellbeing over productivity.)";
  } else if (readinessScore <= 75) {
    explanation += " Moderate energy - protecting capacity by avoiding high-intensity work.)";
  } else {
    explanation += ")";
  }

  return explanation;
}

/**
 * Filter tasks based on readiness score using strict energy gates
 *
 * This implements hard filtering thresholds to protect wellbeing on low-energy days:
 * - Readiness < 60: Only allow low cognitive load tasks (recovery mode)
 * - Readiness 60-75: Allow low + medium cognitive load tasks (moderate capacity)
 * - Readiness > 75: Allow all tasks including high cognitive load (full power)
 *
 * Tasks without cognitive_load metadata default to "medium" and are treated accordingly.
 *
 * @param tasks - Array of tasks to filter
 * @param readinessScore - Oura readiness score (0-100), or null to skip filtering
 * @returns TaskFilterResult with allowedTasks, filteredOutTasks, and explanation
 *
 * @example
 * ```typescript
 * const result = filterTasksByEnergy(tasks, 55);
 * // Returns only low cognitive load tasks
 * // result.filterReason: "Readiness 55/100: Filtering to low cognitive load tasks only to protect energy"
 * ```
 */
export function filterTasksByEnergy(
  tasks: Task[],
  readinessScore: number | null
): TaskFilterResult {
  // If no readiness score, return all tasks unfiltered
  if (readinessScore === null) {
    return {
      allowedTasks: tasks,
      filteredOutTasks: [],
      filterReason: "No energy data available - showing all tasks",
    };
  }

  const allowedTasks: Task[] = [];
  const filteredOutTasks: Task[] = [];

  // Determine which cognitive loads are allowed based on readiness
  let allowedLoads: CognitiveLoad[];
  let filterReason: string;

  if (readinessScore < 60) {
    // Recovery mode: only low cognitive load
    allowedLoads = ["low"];
    filterReason = `Readiness ${readinessScore}/100: Filtering to low cognitive load tasks only to protect energy`;
  } else if (readinessScore <= 75) {
    // Moderate capacity: low + medium cognitive load
    allowedLoads = ["low", "medium"];
    filterReason = `Readiness ${readinessScore}/100: Allowing low and medium cognitive load tasks`;
  } else {
    // Full power: all cognitive loads allowed
    allowedLoads = ["low", "medium", "high"];
    filterReason = `Readiness ${readinessScore}/100: Full energy - all tasks available`;
  }

  // Filter tasks based on cognitive load
  for (const task of tasks) {
    const cognitiveLoad = (task.cognitiveLoad || "medium") as CognitiveLoad;

    if (allowedLoads.includes(cognitiveLoad)) {
      allowedTasks.push(task);
    } else {
      filteredOutTasks.push(task);
    }
  }

  // Enhance filter reason with detailed explanation if tasks were filtered
  if (filteredOutTasks.length > 0) {
    const detailedExplanation = generateFilterExplanation(
      filteredOutTasks,
      readinessScore
    );
    filterReason = `${filterReason}${detailedExplanation}`;
  }

  return {
    allowedTasks,
    filteredOutTasks,
    filterReason,
  };
}

// =============================================================================
// TASK SCORING & RANKING
// =============================================================================

/**
 * Calculate energy match score for a task based on current energy level
 * Higher scores indicate better match between task requirements and current energy
 *
 * Scoring algorithm:
 * - Perfect cognitive load match: +100 points
 * - Adjacent cognitive load match: +50 points
 * - Mismatched cognitive load: 0 points
 * - Value tier alignment: +20 points (milestone/deliverable on high, checkbox on low)
 * - Drain type alignment: +10 points (deep on high, admin on low)
 * - Effort consideration: +5-15 points (quick wins on low energy)
 * - Status bonus: +5 points (active tasks to maintain momentum)
 * - Category consideration: +5 points (personal tasks easier on low energy)
 *
 * @param task - Task to score
 * @param energyLevel - Current energy level
 * @returns Score (0-165) and explanation of match
 */
export function calculateEnergyScore(
  task: Task,
  energyLevel: EnergyLevel
): { score: number; reason: string } {
  let score = 0;
  const reasons: string[] = [];

  const cognitiveLoad = (task.cognitiveLoad || "medium") as CognitiveLoad;

  // Core matching: cognitive load to energy level
  if (energyLevel === "high") {
    if (cognitiveLoad === "high") {
      score += 100;
      reasons.push("Perfect match: High cognitive load task for high energy");
    } else if (cognitiveLoad === "medium") {
      score += 50;
      reasons.push("Good match: Medium cognitive load acceptable for high energy");
    } else {
      reasons.push("Low priority: Low cognitive load task when energy is high");
    }

    // High energy bonuses
    if (task.valueTier === "milestone" || task.valueTier === "deliverable") {
      score += 20;
      reasons.push("Bonus: High-value work best done with high energy");
    }
    if (task.drainType === "deep") {
      score += 10;
      reasons.push("Bonus: Deep work suited for high energy");
    }
    // Larger tasks are fine on high energy
    if (task.effortEstimate && task.effortEstimate >= 5) {
      score += 10;
      reasons.push("Bonus: High energy allows tackling larger tasks");
    }
  } else if (energyLevel === "medium") {
    if (cognitiveLoad === "medium") {
      score += 100;
      reasons.push("Perfect match: Medium cognitive load for medium energy");
    } else if (cognitiveLoad === "high" || cognitiveLoad === "low") {
      score += 50;
      reasons.push("Acceptable match: Can handle varied tasks at medium energy");
    }

    // Medium energy bonuses
    if (task.valueTier === "progress") {
      score += 20;
      reasons.push("Bonus: Progress tasks ideal for medium energy");
    }
    if (task.drainType === "shallow") {
      score += 10;
      reasons.push("Bonus: Shallow work matches medium energy");
    }
    // Medium-sized tasks are good for medium energy
    if (task.effortEstimate && task.effortEstimate >= 2 && task.effortEstimate <= 4) {
      score += 5;
      reasons.push("Bonus: Medium-sized tasks fit medium energy well");
    }
  } else {
    // Low energy
    if (cognitiveLoad === "low") {
      score += 100;
      reasons.push("Perfect match: Low cognitive load for low energy");
    } else if (cognitiveLoad === "medium") {
      score += 50;
      reasons.push("Acceptable: Medium cognitive load manageable with low energy");
    } else {
      reasons.push("Avoid: High cognitive load task when energy is low");
    }

    // Low energy bonuses
    if (task.valueTier === "checkbox") {
      score += 20;
      reasons.push("Bonus: Checkbox tasks perfect for low energy");
    }
    if (task.drainType === "admin") {
      score += 10;
      reasons.push("Bonus: Admin work ideal when energy is low");
    }
    // Quick wins on low energy (effort <= 2)
    if (task.effortEstimate && task.effortEstimate <= 2) {
      score += 15;
      reasons.push("Bonus: Quick wins help build momentum on low energy");
    }
    // Personal tasks might be easier on low energy
    if (task.category === "personal") {
      score += 5;
      reasons.push("Bonus: Personal tasks often easier when energy is low");
    }
  }

  // Cross-energy bonuses: Encourage finishing what's started
  if (task.status === "active") {
    score += 5;
    reasons.push("Bonus: Finish active tasks to maintain momentum");
  }

  return {
    score,
    reason: reasons.join(". "),
  };
}

/**
 * Score and rank tasks based on current energy level
 * Returns tasks sorted by energy match score (highest first)
 *
 * @param tasks - Array of tasks to score and rank
 * @param energyLevel - Current energy level
 * @param limit - Maximum number of tasks to return (default: all)
 * @returns Array of ScoredTask objects sorted by energy score
 */
export function rankTasksByEnergy(
  tasks: Task[],
  energyLevel: EnergyLevel,
  limit?: number
): ScoredTask[] {
  const scoredTasks = tasks.map((task) => {
    const { score, reason } = calculateEnergyScore(task, energyLevel);
    return {
      ...task,
      energyScore: score,
      matchReason: reason,
    };
  });

  // Sort by energy score (highest first)
  scoredTasks.sort((a, b) => b.energyScore - a.energyScore);

  return limit ? scoredTasks.slice(0, limit) : scoredTasks;
}

// =============================================================================
// DAILY GOAL ADJUSTMENT
// =============================================================================

/**
 * Calculate adjusted daily target points based on readiness score
 * Adjustment rules:
 * - Readiness >= 85 (high): Optional +10-20% increase (use +15%)
 * - Readiness 70-84 (medium): No adjustment (100% of target)
 * - Readiness < 70 (low): Reduce by 20-30% (use -25%)
 *
 * @param readinessScore - Oura readiness score (0-100), or null for no adjustment
 * @param sleepScore - Oura sleep score (0-100), or null if unavailable
 * @param baseTarget - Base daily target points (default: 18)
 * @returns GoalAdjustment with original target, adjusted target, and explanation
 */
export function calculateDailyGoalAdjustment(
  readinessScore: number | null,
  sleepScore: number | null = null,
  baseTarget: number = 18
): GoalAdjustment {
  // No adjustment if no readiness score
  if (readinessScore === null) {
    return {
      originalTarget: baseTarget,
      adjustedTarget: baseTarget,
      adjustmentPercentage: 0,
      reason: "No energy data available, using standard target",
      energyLevel: "medium",
      readinessScore: null,
      sleepScore: null,
    };
  }

  const energyLevel = mapReadinessToEnergyLevel(readinessScore);
  let adjustmentPercentage = 0;
  let reason = "";
  let adjustedTarget = baseTarget;

  // Build reason with both readiness and sleep context
  const sleepContext =
    sleepScore !== null ? ` Sleep quality: ${sleepScore}/100.` : "";

  if (readinessScore >= 85) {
    // High energy: +15% increase
    adjustmentPercentage = 15;
    adjustedTarget = Math.round(baseTarget * 1.15);
    reason = `High readiness (${readinessScore}/100) - increased target by 15% to leverage peak energy.${sleepContext}`;
  } else if (readinessScore >= 70) {
    // Medium energy: No adjustment
    adjustmentPercentage = 0;
    adjustedTarget = baseTarget;
    reason = `Good readiness (${readinessScore}/100) - maintaining standard target.${sleepContext}`;
  } else {
    // Low energy: -25% reduction
    adjustmentPercentage = -25;
    adjustedTarget = Math.round(baseTarget * 0.75);
    reason = `Low readiness (${readinessScore}/100) - reduced target by 25% to prevent burnout and protect wellbeing.${sleepContext}`;
  }

  return {
    originalTarget: baseTarget,
    adjustedTarget,
    adjustmentPercentage,
    reason,
    energyLevel,
    readinessScore,
    sleepScore,
  };
}

/**
 * Apply daily goal adjustment to database
 * Updates today's daily_goals record with energy-adjusted values
 *
 * @param db - Database instance
 * @param readinessScore - Oura readiness score (0-100), or null
 * @param sleepScore - Oura sleep score (0-100), or null
 * @param baseTarget - Base daily target points (default: 18)
 * @returns Promise resolving to GoalAdjustment with updated values
 */
export async function applyDailyGoalAdjustment(
  db: Database,
  readinessScore: number | null,
  sleepScore: number | null = null,
  baseTarget: number = 18
): Promise<GoalAdjustment> {
  const adjustment = calculateDailyGoalAdjustment(
    readinessScore,
    sleepScore,
    baseTarget
  );
  const today = getESTDateString();

  // Update or create today's daily goal
  await db
    .insert(schema.dailyGoals)
    .values({
      date: today,
      targetPoints: baseTarget,
      adjustedTargetPoints: adjustment.adjustedTarget,
      readinessScore: adjustment.readinessScore,
      energyLevel: adjustment.energyLevel,
      adjustmentReason: adjustment.reason,
    })
    .onConflictDoUpdate({
      target: schema.dailyGoals.date,
      set: {
        adjustedTargetPoints: adjustment.adjustedTarget,
        readinessScore: adjustment.readinessScore,
        energyLevel: adjustment.energyLevel,
        adjustmentReason: adjustment.reason,
        updatedAt: new Date(),
      },
    });

  return adjustment;
}
