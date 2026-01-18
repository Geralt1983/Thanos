import type { ToolHandler, Database, ContentResponse } from "../../shared/types.js";
import * as schema from "../../schema.js";
import { eq, desc, and } from "drizzle-orm";
import { validateAndSanitize } from "../../shared/validation-schemas.js";
import {
  BrainDumpSchema,
  GetBrainDumpSchema,
  ProcessBrainDumpSchema,
} from "./validation.js";

// =============================================================================
// BRAIN DUMP DOMAIN - HANDLER IMPLEMENTATIONS
// =============================================================================

/**
 * Quick capture a thought, idea, or worry
 * Low friction brain dump for rapid capture
 *
 * @param args - { content: string, category?: "thought" | "task" | "idea" | "worry" }
 * @param db - Database instance
 * @returns Promise resolving to MCP ContentResponse with created entry
 */
export const handleBrainDump: ToolHandler = async (
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> => {
  // Validate input
  const validation = validateAndSanitize(BrainDumpSchema, args);
  if (!validation.success) {
    return {
      content: [{ type: "text", text: `Error: ${validation.error}` }],
      isError: true,
    };
  }

  const { content, category, context } = args;

  const [entry] = await db
    .insert(schema.brainDump)
    .values({
      content,
      category: category || null,
      context: context || "personal",
    })
    .returning();

  return {
    content: [{ type: "text", text: JSON.stringify({ success: true, entry }, null, 2) }],
  };
};

/**
 * Get unprocessed brain dump entries
 * Optionally include processed entries
 *
 * @param args - { includeProcessed?: boolean, limit?: number }
 * @param db - Database instance
 * @returns Promise resolving to MCP ContentResponse with brain dump entries
 */
export const handleGetBrainDump: ToolHandler = async (
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> => {
  // Validate input
  const validation = validateAndSanitize(GetBrainDumpSchema, args);
  if (!validation.success) {
    return {
      content: [{ type: "text", text: `Error: ${validation.error}` }],
      isError: true,
    };
  }

  const { includeProcessed = false, limit = 20, context, category } = args;

  // Build filter conditions
  const conditions = [];

  if (!includeProcessed) {
    conditions.push(eq(schema.brainDump.processed, 0));
  }

  if (context) {
    conditions.push(eq(schema.brainDump.context, context));
  }

  if (category) {
    conditions.push(eq(schema.brainDump.category, category));
  }

  const query = db
    .select()
    .from(schema.brainDump)
    .orderBy(desc(schema.brainDump.createdAt))
    .limit(limit);

  const entries = conditions.length > 0
    ? await query.where(and(...conditions))
    : await query;

  return {
    content: [{ type: "text", text: JSON.stringify(entries, null, 2) }],
  };
};

/**
 * Mark a brain dump entry as processed
 * Optionally convert the entry to a task
 *
 * @param args - { entryId: number, convertToTask?: boolean, taskCategory?: "work" | "personal" }
 * @param db - Database instance
 * @returns Promise resolving to MCP ContentResponse with processing result
 */
export const handleProcessBrainDump: ToolHandler = async (
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> => {
  // Validate input
  const validation = validateAndSanitize(ProcessBrainDumpSchema, args);
  if (!validation.success) {
    return {
      content: [{ type: "text", text: `Error: ${validation.error}` }],
      isError: true,
    };
  }

  const { entryId, convertToTask = false, taskCategory = "personal" } = args;

  // Get the entry first
  const [entry] = await db
    .select()
    .from(schema.brainDump)
    .where(eq(schema.brainDump.id, entryId));

  if (!entry) {
    return {
      content: [{ type: "text", text: `Error: Entry ${entryId} not found` }],
    };
  }

  let taskId = null;

  // Convert to task if requested
  if (convertToTask) {
    const [newTask] = await db
      .insert(schema.tasks)
      .values({
        title: entry.content.substring(0, 100),
        description: entry.content,
        status: "backlog",
        category: taskCategory,
      })
      .returning();
    taskId = newTask.id;
  }

  // Mark as processed
  await db
    .update(schema.brainDump)
    .set({
      processed: 1,
      processedAt: new Date(),
      convertedToTaskId: taskId,
    })
    .where(eq(schema.brainDump.id, entryId));

  return {
    content: [{ type: "text", text: JSON.stringify({ success: true, convertedToTaskId: taskId }, null, 2) }],
  };
};
