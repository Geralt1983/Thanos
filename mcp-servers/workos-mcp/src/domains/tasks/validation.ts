// =============================================================================
// TASK DOMAIN VALIDATION SCHEMAS
// =============================================================================
// This file provides comprehensive Zod validation schemas for all task-related
// MCP tool inputs. These schemas enforce input bounds to prevent:
// - Resource exhaustion from unbounded inputs
// - Database query overload
// - Injection attempts
// - Memory issues
//
// Each schema validates all required and optional fields with appropriate bounds
// as defined in validation-constants.ts
// =============================================================================

import { z } from "zod";
import {
  taskIdSchema,
  clientIdSchema,
  taskTitleSchema,
  taskDescriptionSchema,
  clientNameSchema,
  queryLimitSchema,
  taskStatusSchema,
  taskCategorySchema,
  valueTierSchema,
  drainTypeSchema,
  cognitiveLoadSchema,
} from "../../shared/validation-schemas.js";

// =============================================================================
// TOOL INPUT SCHEMAS
// =============================================================================

/**
 * Schema for workos_get_tasks tool
 * Validates filtering parameters for task queries
 *
 * @property status - Optional task status filter (active, queued, backlog, done)
 * @property clientId - Optional client ID filter (positive integer)
 * @property clientName - Optional client name filter (case-insensitive lookup)
 * @property limit - Optional result limit (1-100, default handled by handler)
 * @property applyEnergyFilter - Optional boolean to enable energy-based task filtering (default: false)
 */
export const GetTasksSchema = z.object({
  status: taskStatusSchema.optional(),
  clientId: clientIdSchema.optional(),
  clientName: clientNameSchema.optional(),
  limit: queryLimitSchema.optional(),
  applyEnergyFilter: z.boolean().optional(),
});

/**
 * Schema for workos_get_server_version tool
 * No inputs required
 */
export const GetServerVersionSchema = z.object({});

/**
 * Schema for workos_create_task tool
 * Validates all fields for task creation with comprehensive bounds
 *
 * @property title - Required task title (1-200 chars)
 * @property description - Optional task description (0-2000 chars)
 * @property clientId - Optional client assignment (positive integer)
 * @property status - Optional initial status (active, queued, backlog; default: backlog)
 * @property category - Optional task category (work, personal; default: work)
 * @property valueTier - Optional value tier (checkbox, progress, deliverable, milestone)
 * @property drainType - Optional energy drain type (deep, shallow, admin)
 */
export const CreateTaskSchema = z.object({
  title: taskTitleSchema,
  description: taskDescriptionSchema.optional(),
  clientId: clientIdSchema.optional(),
  status: taskStatusSchema
    .refine((val) => val !== "done", {
      message: "Cannot create a task with status 'done'",
    })
    .optional(),
  category: taskCategorySchema.optional(),
  valueTier: valueTierSchema.optional(),
  drainType: drainTypeSchema.optional(),
});

/**
 * Schema for workos_update_task tool
 * Validates task updates with partial field updates
 * All fields optional except taskId (required)
 *
 * @property taskId - Required task ID to update (positive integer)
 * @property title - Optional new task title (1-200 chars)
 * @property description - Optional new task description (0-2000 chars)
 * @property clientId - Optional new client assignment (positive integer, null to unassign)
 * @property status - Optional new status (active, queued, backlog, done)
 * @property valueTier - Optional new value tier (checkbox, progress, deliverable, milestone)
 * @property drainType - Optional new energy drain type (deep, shallow, admin)
 */
/**
 * Schema for subtask items
 * Each subtask has a title and done status
 */
const subtaskSchema = z.object({
  title: z.string().min(1).max(500),
  done: z.boolean().default(false),
});

export const UpdateTaskSchema = z.object({
  taskId: taskIdSchema,
  title: taskTitleSchema.optional(),
  description: taskDescriptionSchema.optional(),
  clientId: clientIdSchema.optional(),
  status: taskStatusSchema.optional(),
  valueTier: valueTierSchema.optional(),
  drainType: drainTypeSchema.optional(),
  cognitiveLoad: cognitiveLoadSchema.optional(),
  subtasks: z.array(subtaskSchema).max(50).optional(),
});

/**
 * Schema for workos_complete_task tool
 * Validates task completion request
 *
 * @property taskId - Required task ID to complete (positive integer)
 */
export const CompleteTaskSchema = z.object({
  taskId: taskIdSchema,
});

/**
 * Schema for workos_promote_task tool
 * Validates task promotion request (move to active status)
 *
 * @property taskId - Required task ID to promote (positive integer)
 */
export const PromoteTaskSchema = z.object({
  taskId: taskIdSchema,
});

/**
 * Schema for workos_delete_task tool
 * Validates task deletion request
 *
 * @property taskId - Required task ID to delete (positive integer)
 */
export const DeleteTaskSchema = z.object({
  taskId: taskIdSchema,
});

/**
 * Schema for workos_get_client_memory tool
 * Validates client memory lookup request
 *
 * @property clientName - Required client name (1-100 chars)
 */
export const GetClientMemorySchema = z.object({
  clientName: clientNameSchema,
});

/**
 * Schema for workos_get_today_metrics tool
 * No parameters required - validates empty object
 */
export const GetTodayMetricsSchema = z.object({});

/**
 * Schema for workos_get_metrics_for_date tool
 * Validates date parameter for historical metrics lookup
 *
 * @property date - Required date in YYYY-MM-DD format
 */
export const GetMetricsForDateSchema = z.object({
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, {
    message: "Date must be in YYYY-MM-DD format",
  }),
});

/**
 * Schema for workos_get_clients tool
 * No parameters required - validates empty object
 */
export const GetClientsSchema = z.object({});

/**
 * Schema for workos_get_streak tool
 * No parameters required - validates empty object
 */
export const GetStreakSchema = z.object({});

/**
 * Schema for workos_daily_summary tool
 * No parameters required - validates empty object
 */
export const DailySummarySchema = z.object({});

// =============================================================================
// SCHEMA EXPORT MAP
// =============================================================================

/**
 * Map of tool names to their validation schemas
 * Used for centralized validation in the task domain handler router
 *
 * @example
 * const schema = TASK_SCHEMAS['workos_create_task'];
 * const result = validateToolInput(schema, args);
 */
export const TASK_SCHEMAS = {
  workos_get_server_version: GetServerVersionSchema,
  workos_get_today_metrics: GetTodayMetricsSchema,
  workos_get_metrics_for_date: GetMetricsForDateSchema,
  workos_get_tasks: GetTasksSchema,
  workos_get_clients: GetClientsSchema,
  workos_create_task: CreateTaskSchema,
  workos_complete_task: CompleteTaskSchema,
  workos_promote_task: PromoteTaskSchema,
  workos_get_streak: GetStreakSchema,
  workos_get_client_memory: GetClientMemorySchema,
  workos_daily_summary: DailySummarySchema,
  workos_update_task: UpdateTaskSchema,
  workos_delete_task: DeleteTaskSchema,
} as const;
