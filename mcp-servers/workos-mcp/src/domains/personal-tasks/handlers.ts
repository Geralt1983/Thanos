import type { Database, ToolHandler, ContentResponse } from "../../shared/types.js";
import { successResponse, errorResponse } from "../../shared/types.js";
import * as schema from "../../schema.js";
import { eq, and, asc, desc } from "drizzle-orm";

// =============================================================================
// PERSONAL TASKS DOMAIN HANDLERS
// =============================================================================

/**
 * Handler: workos_get_personal_tasks
 * Get personal (non-work) tasks with optional status filtering
 */
export async function handleGetPersonalTasks(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { status, limit = 20 } = args;

  const conditions = [eq(schema.tasks.category, "personal")];
  if (status) conditions.push(eq(schema.tasks.status, status));

  const tasks = await db
    .select()
    .from(schema.tasks)
    .where(and(...conditions))
    .orderBy(asc(schema.tasks.sortOrder), desc(schema.tasks.createdAt))
    .limit(limit);

  return {
    content: [{ type: "text", text: JSON.stringify(tasks, null, 2) }],
  };
}
