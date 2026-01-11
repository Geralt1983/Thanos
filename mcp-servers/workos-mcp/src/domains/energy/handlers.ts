import type { Database, ToolHandler, ContentResponse } from "../../shared/types.js";
import { successResponse, errorResponse } from "../../shared/types.js";
import * as schema from "../../schema.js";
import { desc } from "drizzle-orm";

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
