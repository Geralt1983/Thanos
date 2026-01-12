// =============================================================================
// PERSONAL TASKS DOMAIN VALIDATION SCHEMAS
// =============================================================================
// This file provides comprehensive Zod validation schemas for all personal
// tasks-related MCP tool inputs. These schemas enforce input bounds to prevent:
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
  taskStatusSchema,
  queryLimitSchema,
} from "../../shared/validation-schemas.js";

// =============================================================================
// TOOL INPUT SCHEMAS
// =============================================================================

/**
 * Schema for workos_get_personal_tasks tool
 * Validates personal task query parameters
 *
 * @property status - Optional task status filter (active, queued, backlog, done)
 * @property limit - Optional result limit (1-100, default: 20)
 */
export const GetPersonalTasksSchema = z.object({
  status: taskStatusSchema.optional(),
  limit: queryLimitSchema.optional(),
});

// =============================================================================
// SCHEMA EXPORT MAP
// =============================================================================

/**
 * Map of tool names to their validation schemas
 * Used for centralized validation in the personal tasks domain handler router
 *
 * @example
 * const schema = PERSONAL_TASKS_SCHEMAS['workos_get_personal_tasks'];
 * const result = validateToolInput(schema, args);
 */
export const PERSONAL_TASKS_SCHEMAS = {
  workos_get_personal_tasks: GetPersonalTasksSchema,
} as const;
