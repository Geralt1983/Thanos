import type { Database, ToolHandler, ContentResponse } from "../../shared/types.js";
import { successResponse, errorResponse } from "../../shared/types.js";
import * as schema from "../../schema.js";
import { desc } from "drizzle-orm";

// =============================================================================
// ENERGY DOMAIN HANDLERS
// =============================================================================

/**
 * Handler: workos_log_energy
 * Log current energy state (high/medium/low) with optional Oura Ring data
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
 * Handler: workos_get_energy
 * Get current/recent energy states
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
