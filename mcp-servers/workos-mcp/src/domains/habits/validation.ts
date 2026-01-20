// =============================================================================
// HABIT DOMAIN VALIDATION SCHEMAS
// =============================================================================
// This file provides comprehensive Zod validation schemas for all habit-related
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
  habitIdSchema,
  habitNameSchema,
  habitDescriptionSchema,
  habitEmojiSchema,
  habitNoteSchema,
  targetCountSchema,
  daysStreakSchema,
  daysDashboardSchema,
  habitFrequencySchema,
  habitTimeOfDaySchema,
  habitCategorySchema,
} from "../../shared/validation-schemas.js";

// =============================================================================
// HABIT-SPECIFIC ENUM SCHEMAS
// =============================================================================

/**
 * Time of day filter for habit checkin
 * Includes "all" option for checking all habits regardless of timeOfDay
 */
export const habitCheckinTimeOfDaySchema = z.enum(["morning", "evening", "all"], {
  errorMap: () => ({
    message: "timeOfDay must be one of: morning, evening, all",
  }),
});

/**
 * Dashboard format enum validation
 * Supports compact (ASCII only), detailed (JSON with ASCII), and weekly formats
 */
export const habitDashboardFormatSchema = z.enum(["compact", "detailed", "weekly"], {
  errorMap: () => ({
    message: "format must be one of: compact, detailed, weekly",
  }),
});

// =============================================================================
// TOOL INPUT SCHEMAS
// =============================================================================

/**
 * Schema for workos_get_habits tool
 * No parameters required - validates empty object
 */
export const GetHabitsSchema = z.object({});

/**
 * Schema for workos_create_habit tool
 * Validates all fields for habit creation with comprehensive bounds
 *
 * @property name - Required habit name (1-100 chars)
 * @property description - Optional habit description (0-500 chars)
 * @property emoji - Optional emoji icon (0-10 chars for emoji sequences)
 * @property frequency - Optional frequency (daily, weekdays, weekly; default: daily)
 * @property targetCount - Optional times per period (1-100; default: 1)
 * @property timeOfDay - Optional timing preference (morning, evening, anytime; default: anytime)
 * @property category - Optional habit category (health, productivity, relationship, personal)
 */
export const CreateHabitSchema = z.object({
  name: habitNameSchema,
  description: habitDescriptionSchema.optional(),
  emoji: habitEmojiSchema.optional(),
  frequency: habitFrequencySchema.optional(),
  targetCount: targetCountSchema.optional(),
  timeOfDay: habitTimeOfDaySchema.optional(),
  category: habitCategorySchema.optional(),
});

/**
 * Schema for workos_complete_habit tool
 * Validates habit completion request with optional note
 *
 * @property habitId - Required habit ID to complete (positive integer)
 * @property note - Optional note about the completion (0-500 chars)
 */
export const CompleteHabitSchema = z.object({
  habitId: habitIdSchema,
  note: habitNoteSchema.optional(),
});

/**
 * Schema for workos_get_habit_streaks tool
 * Validates habit streak query parameters
 *
 * @property habitId - Optional habit ID filter (positive integer)
 * @property days - Optional lookback period (1-365 days; default: 7)
 */
export const GetHabitStreaksSchema = z.object({
  habitId: habitIdSchema.optional(),
  days: daysStreakSchema.optional(),
});

/**
 * Schema for workos_habit_checkin tool
 * Validates habit checkin query parameters
 *
 * @property timeOfDay - Optional time filter (morning, evening, all; default: all)
 * @property includeCompleted - Optional flag to show already-completed habits (default: false)
 */
export const HabitCheckinSchema = z.object({
  timeOfDay: habitCheckinTimeOfDaySchema.optional(),
  includeCompleted: z.boolean().optional(),
});

/**
 * Schema for workos_habit_dashboard tool
 * Validates habit dashboard query parameters
 *
 * @property days - Optional lookback period (1-90 days; default: 7)
 * @property format - Optional output format (compact, detailed, weekly; default: compact)
 */
export const HabitDashboardSchema = z.object({
  days: daysDashboardSchema.optional(),
  format: habitDashboardFormatSchema.optional(),
});

/**
 * Schema for workos_recalculate_streaks tool
 * No parameters required - validates empty object
 */
export const RecalculateStreaksSchema = z.object({});

/**
 * Schema for workos_delete_habit tool
 * Validates habit deletion request
 *
 * @property habitId - Required habit ID to delete (positive integer)
 */
export const DeleteHabitSchema = z.object({
  habitId: habitIdSchema,
});

// =============================================================================
// SCHEMA EXPORT MAP
// =============================================================================

/**
 * Map of tool names to their validation schemas
 * Used for centralized validation in the habit domain handler router
 *
 * @example
 * const schema = HABIT_SCHEMAS['workos_create_habit'];
 * const result = validateToolInput(schema, args);
 */
export const HABIT_SCHEMAS = {
  workos_get_habits: GetHabitsSchema,
  workos_create_habit: CreateHabitSchema,
  workos_complete_habit: CompleteHabitSchema,
  workos_get_habit_streaks: GetHabitStreaksSchema,
  workos_habit_checkin: HabitCheckinSchema,
  workos_habit_dashboard: HabitDashboardSchema,
  workos_recalculate_streaks: RecalculateStreaksSchema,
  workos_delete_habit: DeleteHabitSchema,
} as const;
