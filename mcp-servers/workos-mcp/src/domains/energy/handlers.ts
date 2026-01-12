import type { Database, ToolHandler, ContentResponse } from "../../shared/types.js";
import { successResponse, errorResponse } from "../../shared/types.js";
import * as schema from "../../schema.js";
import type { EnergyLevel } from "../../schema.js";
import { desc, eq } from "drizzle-orm";
import { getESTTodayStart } from "../../shared/utils.js";
import { applyDailyGoalAdjustment } from "../../services/energy-prioritization.js";

// =============================================================================
// ENERGY DOMAIN HANDLERS
// =============================================================================

/**
 * Log current energy state with optional Oura Ring biometric data
 * Records energy level (high/medium/low) with timestamp and optional wellness metrics
 * Automatically sets source to "oura" when Oura Ring data is provided
 *
 * @param args - { level: "high" | "medium" | "low", note?: string, ouraReadiness?: number, ouraHrv?: number, ouraSleep?: number }
 * @param db - Database instance for creating the energy state entry
 * @returns Promise resolving to MCP ContentResponse with success status and created energy state entry
 */
export async function handleLogEnergy(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { level, note, ouraReadiness, ouraHrv, ouraSleep } = args;

  const [entry] = await db
    .insert(schema.energyStates)
    .values({
      level,
      source: ouraReadiness ? "oura" : "manual",
      note: note || null,
      ouraReadiness: ouraReadiness || null,
      ouraHrv: ouraHrv || null,
      ouraSleep: ouraSleep || null,
    })
    .returning();

  return {
    content: [{ type: "text", text: JSON.stringify({ success: true, entry }, null, 2) }],
  };
}

/**
 * Get current and recent energy states
 * Returns most recent energy entries with timestamps, levels, sources, and optional Oura metrics
 * Sorted by most recent first
 *
 * @param args - { limit?: number } - Maximum number of entries to return (default: 5)
 * @param db - Database instance for querying energy states
 * @returns Promise resolving to MCP ContentResponse with array of energy state entries
 */
export async function handleGetEnergy(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { limit = 5 } = args;

  const entries = await db
    .select()
    .from(schema.energyStates)
    .orderBy(desc(schema.energyStates.recordedAt))
    .limit(limit);

  return {
    content: [{ type: "text", text: JSON.stringify(entries, null, 2) }],
  };
}

/**
 * Manually override auto-detected energy level or task suggestions
 * Records override with reason for algorithm learning and improvement
 * Optionally recalculates daily goal based on manual energy override
 *
 * This is critical for ADHD users who know their energy better than metrics suggest.
 * Common override scenarios:
 * - "Feel more energized than readiness suggests" (medication, coffee, good mood)
 * - "Need to push through despite low energy" (deadline, commitment)
 * - "Readiness doesn't account for X factor" (excitement, anxiety, context)
 *
 * @param args - { energyLevel: "high" | "medium" | "low", reason: string, taskId?: number, adjustDailyGoal?: boolean }
 * @param db - Database instance for creating energy state entry and updating daily goal
 * @returns Promise resolving to MCP ContentResponse with override confirmation, energy context, optional task info, and optional goal adjustment
 */
export async function handleOverrideEnergySuggestion(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { energyLevel, reason, taskId, adjustDailyGoal = true } = args;

  // Validate energy level
  const validLevels: EnergyLevel[] = ["high", "medium", "low"];
  if (!validLevels.includes(energyLevel)) {
    return errorResponse(`Invalid energy level: ${energyLevel}. Must be one of: ${validLevels.join(", ")}`);
  }

  // Log the manual override as an energy state entry
  const [entry] = await db
    .insert(schema.energyStates)
    .values({
      level: energyLevel,
      source: "manual",
      note: `OVERRIDE: ${reason}`,
    })
    .returning();

  // Build response data
  const responseData: any = {
    success: true,
    override: {
      energyLevel,
      reason,
      recordedAt: entry.recordedAt,
      entryId: entry.id,
    },
  };

  // If task ID provided, fetch task details for context
  if (taskId) {
    const task = await db
      .select()
      .from(schema.tasks)
      .where(eq(schema.tasks.id, taskId))
      .limit(1);

    if (task.length > 0) {
      responseData.task = {
        id: task[0].id,
        title: task[0].title,
        cognitiveLoad: task[0].cognitiveLoad,
        valueTier: task[0].valueTier,
        status: task[0].status,
      };
    }
  }

  // Optionally recalculate daily goal based on manual energy override
  if (adjustDailyGoal) {
    try {
      // Map energy level to a readiness score for goal adjustment
      // High energy: 90 (upper range), Medium: 77 (mid range), Low: 60 (lower range)
      const readinessMapping: Record<EnergyLevel, number> = {
        high: 90,
        medium: 77,
        low: 60,
      };
      const mappedReadiness = readinessMapping[energyLevel as EnergyLevel];

      // Apply daily goal adjustment using energy-prioritization service
      // Signature: applyDailyGoalAdjustment(db, readinessScore, sleepScore, baseTarget)
      const adjustment = await applyDailyGoalAdjustment(db, mappedReadiness, null, 18);

      responseData.dailyGoalAdjustment = {
        originalTarget: adjustment.originalTarget,
        adjustedTarget: adjustment.adjustedTarget,
        adjustmentPercentage: adjustment.adjustmentPercentage,
        reason: adjustment.reason,
        energyLevel: adjustment.energyLevel,
        mappedReadiness: mappedReadiness,
      };
    } catch (error) {
      console.error("[Override] Failed to adjust daily goal:", error);
      responseData.dailyGoalAdjustment = {
        error: "Failed to adjust daily goal",
        details: error instanceof Error ? error.message : String(error),
      };
    }
  }

  return {
    content: [{
      type: "text",
      text: JSON.stringify(responseData, null, 2),
    }],
  };
}

/**
 * Record user feedback on energy-based task suggestion
 * Tracks whether energy-task match was helpful for algorithm refinement
 *
 * This feedback is critical for improving the energy-aware prioritization algorithm over time.
 * By tracking when suggestions work well vs. poorly, we can:
 * - Refine cognitive load mappings to energy levels
 * - Identify tasks that need cognitive load adjustments
 * - Understand user-specific energy patterns
 * - Improve the scoring algorithm for better task-energy matches
 *
 * Common feedback scenarios:
 * - "Task was perfect for my energy level" (successful match)
 * - "Task was too complex for my energy" (mismatch - suggested energy too low)
 * - "I had more energy than expected" (actual energy higher than suggested)
 * - "Should have waited for higher energy" (learned from experience)
 *
 * @param args - { taskId: number, suggestedEnergyLevel: "high" | "medium" | "low", actualEnergyLevel: "high" | "medium" | "low", completedSuccessfully: boolean, userFeedback?: string }
 * @param db - Database instance for creating energy feedback entry
 * @returns Promise resolving to MCP ContentResponse with feedback confirmation and task context
 */
export async function handleProvideEnergyFeedback(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const {
    taskId,
    suggestedEnergyLevel,
    actualEnergyLevel,
    completedSuccessfully,
    userFeedback,
  } = args;

  // Validate energy levels
  const validLevels: EnergyLevel[] = ["high", "medium", "low"];
  if (!validLevels.includes(suggestedEnergyLevel)) {
    return errorResponse(
      `Invalid suggestedEnergyLevel: ${suggestedEnergyLevel}. Must be one of: ${validLevels.join(", ")}`
    );
  }
  if (!validLevels.includes(actualEnergyLevel)) {
    return errorResponse(
      `Invalid actualEnergyLevel: ${actualEnergyLevel}. Must be one of: ${validLevels.join(", ")}`
    );
  }

  // Fetch task details for context
  const task = await db
    .select()
    .from(schema.tasks)
    .where(eq(schema.tasks.id, taskId))
    .limit(1);

  if (task.length === 0) {
    return errorResponse(`Task not found: ${taskId}`);
  }

  const taskData = task[0];

  // Insert feedback into energy_feedback table
  const [feedbackEntry] = await db
    .insert(schema.energyFeedback)
    .values({
      taskId,
      suggestedEnergyLevel,
      actualEnergyLevel,
      completedSuccessfully,
      userFeedback: userFeedback || null,
    })
    .returning();

  // Determine if this was a good match or mismatch
  const isMatch = suggestedEnergyLevel === actualEnergyLevel;
  const energyDelta = getEnergyDelta(suggestedEnergyLevel, actualEnergyLevel);

  // Build response with feedback confirmation and insights
  const responseData = {
    success: true,
    feedback: {
      id: feedbackEntry.id,
      taskId: feedbackEntry.taskId,
      suggestedEnergyLevel: feedbackEntry.suggestedEnergyLevel,
      actualEnergyLevel: feedbackEntry.actualEnergyLevel,
      completedSuccessfully: feedbackEntry.completedSuccessfully,
      userFeedback: feedbackEntry.userFeedback,
      recordedAt: feedbackEntry.createdAt,
    },
    task: {
      id: taskData.id,
      title: taskData.title,
      cognitiveLoad: taskData.cognitiveLoad,
      valueTier: taskData.valueTier,
      status: taskData.status,
    },
    analysis: {
      isMatch,
      energyDelta, // positive = had more energy than suggested, negative = had less
      message: generateFeedbackMessage(
        isMatch,
        energyDelta,
        completedSuccessfully,
        taskData.cognitiveLoad
      ),
    },
  };

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(responseData, null, 2),
      },
    ],
  };
}

/**
 * Calculate energy level delta between suggested and actual
 * @returns 0 if match, +1 if actual > suggested (had more energy), -1 if actual < suggested (had less)
 */
function getEnergyDelta(suggested: string, actual: string): number {
  const levels = ["low", "medium", "high"];
  const suggestedIdx = levels.indexOf(suggested);
  const actualIdx = levels.indexOf(actual);
  return actualIdx - suggestedIdx;
}

/**
 * Generate insightful feedback message based on the energy match and completion status
 */
function generateFeedbackMessage(
  isMatch: boolean,
  energyDelta: number,
  completedSuccessfully: boolean,
  cognitiveLoad: string | null
): string {
  if (isMatch && completedSuccessfully) {
    return "Perfect match! The energy-task suggestion worked well. This data helps confirm the algorithm is working correctly for similar tasks.";
  }

  if (isMatch && !completedSuccessfully) {
    return `Energy level matched, but task wasn't completed. This might indicate the cognitive load (${cognitiveLoad}) needs adjustment, or there were other factors at play.`;
  }

  if (energyDelta > 0 && completedSuccessfully) {
    return `You had more energy than suggested and completed the task successfully. This suggests the algorithm may be underestimating your capacity or this task's cognitive load could be adjusted.`;
  }

  if (energyDelta > 0 && !completedSuccessfully) {
    return `You had more energy than suggested but didn't complete the task. This may indicate non-energy factors (context switching, interruptions, etc.) affected completion.`;
  }

  if (energyDelta < 0 && completedSuccessfully) {
    return `You had less energy than suggested but still completed the task! This is valuable data - perhaps this task's cognitive load is overestimated, or you're getting better at this type of work.`;
  }

  if (energyDelta < 0 && !completedSuccessfully) {
    return `You had less energy than suggested and couldn't complete the task. This confirms the importance of respecting energy levels. The algorithm may need to be more conservative for similar tasks.`;
  }

  return "Thank you for the feedback. This data will help refine the energy-task matching algorithm.";
}
