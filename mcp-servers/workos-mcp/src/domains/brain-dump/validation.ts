// =============================================================================
// BRAIN DUMP DOMAIN VALIDATION SCHEMAS
// =============================================================================
// This file provides comprehensive Zod validation schemas for all brain dump
// related MCP tool inputs. These schemas enforce input bounds to prevent:
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
  brainDumpIdSchema,
  brainDumpContentSchema,
  brainDumpCategorySchema,
  queryLimitSchema,
  taskCategorySchema,
} from "../../shared/validation-schemas.js";

// =============================================================================
// TOOL INPUT SCHEMAS
// =============================================================================

/**
 * Schema for brain dump context (work vs personal)
 */
export const brainDumpContextSchema = z.enum(["work", "personal"]).optional();

/**
 * Schema for workos_brain_dump tool
 * Validates quick capture of thoughts, ideas, or worries
 *
 * @property content - Required thought/idea content (1-5000 chars)
 * @property category - Optional category filter (thought, task, idea, worry)
 * @property context - Optional work/personal context
 */
export const BrainDumpSchema = z.object({
  content: brainDumpContentSchema,
  category: brainDumpCategorySchema,
  context: brainDumpContextSchema,
});

/**
 * Schema for workos_get_brain_dump tool
 * Validates retrieval parameters for brain dump entries
 *
 * @property includeProcessed - Optional flag to include already processed items (boolean)
 * @property limit - Optional result limit (1-100, default 20)
 * @property context - Optional filter by work/personal context
 * @property category - Optional filter by category (thought, task, idea, worry)
 */
export const GetBrainDumpSchema = z.object({
  includeProcessed: z.boolean().optional(),
  limit: queryLimitSchema.optional(),
  context: brainDumpContextSchema,
  category: brainDumpCategorySchema,
});

/**
 * Schema for workos_process_brain_dump tool
 * Validates processing a brain dump entry with optional task conversion
 *
 * @property entryId - Required brain dump entry ID (positive integer)
 * @property convertToTask - Optional flag to convert entry to a task (boolean)
 * @property taskCategory - Optional task category if converting (work, personal)
 */
export const ProcessBrainDumpSchema = z.object({
  entryId: brainDumpIdSchema,
  convertToTask: z.boolean().optional(),
  taskCategory: taskCategorySchema.optional(),
});

// =============================================================================
// SCHEMA EXPORT MAP
// =============================================================================

/**
 * Map of tool names to their validation schemas
 * Used for centralized validation in the brain dump domain handler router
 *
 * @example
 * const schema = BRAIN_DUMP_SCHEMAS['workos_brain_dump'];
 * const result = validateToolInput(schema, args);
 */
export const BRAIN_DUMP_SCHEMAS = {
  workos_brain_dump: BrainDumpSchema,
  workos_get_brain_dump: GetBrainDumpSchema,
  workos_process_brain_dump: ProcessBrainDumpSchema,
} as const;
