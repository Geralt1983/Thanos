import type { Database, ToolHandler, ContentResponse } from "../../shared/types.js";
import { successResponse, errorResponse } from "../../shared/types.js";
import * as schema from "../../schema.js";
import { eq, and, asc, desc } from "drizzle-orm";
import { validateAndSanitize } from "../../shared/validation-schemas.js";
import { GetPersonalTasksSchema } from "./validation.js";

// =============================================================================
// PERSONAL TASKS DOMAIN HANDLERS
// =============================================================================

/**
 * Get personal (non-work) tasks with optional status filtering
 * Returns tasks with category="personal" sorted by sortOrder and createdAt
 * Useful for separating personal life tasks from work/client tasks
 *
 * @param args - { status?: "active" | "queued" | "backlog" | "done", limit?: number } - Optional status filter and result limit (default: 20)
 * @param db - Database instance for querying personal tasks
 * @returns Promise resolving to MCP ContentResponse with array of personal tasks
 */
export async function handleGetPersonalTasks(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  // Validate input
  const validation = validateAndSanitize(GetPersonalTasksSchema, args);
  if (!validation.success) {
    return {
      content: [{ type: "text", text: `Error: ${validation.error}` }],
    };
  }

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
