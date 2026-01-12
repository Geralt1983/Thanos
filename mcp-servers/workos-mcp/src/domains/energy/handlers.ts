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
