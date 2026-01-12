// =============================================================================
// VALIDATION SCHEMAS
// =============================================================================
// This file provides Zod schemas with comprehensive input validation bounds.
// All schemas enforce limits defined in validation-constants.ts to prevent:
// - Resource exhaustion from unbounded inputs
// - Database query overload
// - Injection attempts
// - Memory issues
// =============================================================================

import { z } from "zod";
import {
  STRING_LIMITS,
  NUMERIC_LIMITS,
  ERROR_MESSAGES,
} from "./validation-constants.js";

// =============================================================================
// SCHEMA HELPER FUNCTIONS
// =============================================================================

/**
 * Creates a bounded string schema with min/max length validation
 *
 * @param fieldName - Field name for error messages
 * @param min - Minimum length (inclusive)
 * @param max - Maximum length (inclusive)
 * @param options - Optional configuration
 * @returns Zod string schema with length bounds
 *
 * @example
 * const titleSchema = minMaxString('title', 1, 200);
 * titleSchema.parse('Valid title'); // OK
 * titleSchema.parse(''); // Error: title must be at least 1 character
 */
export function minMaxString(
  fieldName: string,
  min: number,
  max: number,
  options: {
    trim?: boolean;
    optional?: boolean;
  } = {}
): z.ZodString | z.ZodOptional<z.ZodString> {
  const { trim = true, optional = false } = options;

  let schema = z.string({
    required_error: ERROR_MESSAGES.STRING_EMPTY(fieldName),
    invalid_type_error: `${fieldName} must be a string`,
  });

  // Apply trimming if requested
  if (trim) {
    schema = schema.trim();
  }

  // Apply length validation
  schema = schema
    .min(min, {
      message: ERROR_MESSAGES.STRING_TOO_SHORT(fieldName, min, 0),
    })
    .max(max, {
      message: ERROR_MESSAGES.STRING_TOO_LONG(fieldName, max, 0),
    });

  return optional ? schema.optional() : schema;
}

/**
 * Creates a positive integer schema with validation
 *
 * @param fieldName - Field name for error messages
 * @returns Zod number schema for positive integers
 *
 * @example
 * const idSchema = positiveInt('taskId');
 * idSchema.parse(123); // OK
 * idSchema.parse(-1); // Error: taskId must be a positive integer
 * idSchema.parse(1.5); // Error: taskId must be an integer
 */
export function positiveInt(fieldName: string): z.ZodNumber {
  return z
    .number({
      required_error: `${fieldName} is required`,
      invalid_type_error: `${fieldName} must be a number`,
    })
    .int({
      message: ERROR_MESSAGES.NUMBER_NOT_INTEGER(fieldName),
    })
    .min(NUMERIC_LIMITS.ID_MIN, {
      message: ERROR_MESSAGES.NUMBER_NOT_POSITIVE_INT(fieldName, 0),
    })
    .max(NUMERIC_LIMITS.ID_MAX, {
      message: ERROR_MESSAGES.NUMBER_OUT_OF_RANGE(
        fieldName,
        NUMERIC_LIMITS.ID_MIN,
        NUMERIC_LIMITS.ID_MAX,
        0
      ),
    });
}

/**
 * Creates a bounded integer schema with min/max range validation
 *
 * @param fieldName - Field name for error messages
 * @param min - Minimum value (inclusive)
 * @param max - Maximum value (inclusive)
 * @param options - Optional configuration
 * @returns Zod number schema with range bounds
 *
 * @example
 * const limitSchema = boundedInt('limit', 1, 100, { defaultValue: 50 });
 * limitSchema.parse(50); // OK
 * limitSchema.parse(101); // Error: limit must be between 1 and 100
 */
export function boundedInt(
  fieldName: string,
  min: number,
  max: number,
  options: {
    defaultValue?: number;
    optional?: boolean;
  } = {}
): z.ZodNumber | z.ZodOptional<z.ZodNumber> | z.ZodDefault<z.ZodNumber> {
  const { defaultValue, optional = false } = options;

  let schema = z
    .number({
      required_error: `${fieldName} is required`,
      invalid_type_error: `${fieldName} must be a number`,
    })
    .int({
      message: ERROR_MESSAGES.NUMBER_NOT_INTEGER(fieldName),
    })
    .min(min, {
      message: ERROR_MESSAGES.NUMBER_OUT_OF_RANGE(fieldName, min, max, 0),
    })
    .max(max, {
      message: ERROR_MESSAGES.NUMBER_OUT_OF_RANGE(fieldName, min, max, 0),
    });

  if (defaultValue !== undefined) {
    return schema.default(defaultValue);
  }

  return optional ? schema.optional() : schema;
}

// =============================================================================
// COMMON FIELD SCHEMAS
// =============================================================================

/**
 * Task ID validation - must be a positive integer
 */
export const taskIdSchema = positiveInt("taskId");

/**
 * Client ID validation - must be a positive integer
 * Can be null/undefined in some contexts (optional client assignment)
 */
export const clientIdSchema = positiveInt("clientId").optional();

/**
 * Habit ID validation - must be a positive integer
 */
export const habitIdSchema = positiveInt("habitId");

/**
 * Brain dump entry ID validation - must be a positive integer
 */
export const brainDumpIdSchema = positiveInt("entryId");

/**
 * Query limit validation - bounded between 1 and 100
 */
export const queryLimitSchema = boundedInt(
  "limit",
  NUMERIC_LIMITS.QUERY_LIMIT_MIN,
  NUMERIC_LIMITS.QUERY_LIMIT_MAX,
  { optional: true }
);

/**
 * Task title validation - 1 to 200 characters
 */
export const taskTitleSchema = minMaxString(
  "title",
  STRING_LIMITS.TASK_TITLE_MIN,
  STRING_LIMITS.TASK_TITLE_MAX
);

/**
 * Task description validation - up to 2000 characters (optional)
 */
export const taskDescriptionSchema = minMaxString(
  "description",
  0,
  STRING_LIMITS.TASK_DESCRIPTION_MAX,
  { optional: true }
);

/**
 * Client name validation - 1 to 100 characters
 */
export const clientNameSchema = minMaxString(
  "clientName",
  STRING_LIMITS.CLIENT_NAME_MIN,
  STRING_LIMITS.CLIENT_NAME_MAX
);

/**
 * Habit name validation - 1 to 100 characters
 */
export const habitNameSchema = minMaxString(
  "name",
  STRING_LIMITS.HABIT_NAME_MIN,
  STRING_LIMITS.HABIT_NAME_MAX
);

/**
 * Habit description validation - up to 500 characters (optional)
 */
export const habitDescriptionSchema = minMaxString(
  "description",
  0,
  STRING_LIMITS.HABIT_DESCRIPTION_MAX,
  { optional: true }
);

/**
 * Habit emoji validation - up to 10 characters for emoji sequences (optional)
 */
export const habitEmojiSchema = minMaxString(
  "emoji",
  0,
  STRING_LIMITS.HABIT_EMOJI_MAX,
  { optional: true }
);

/**
 * Habit note validation - up to 500 characters (optional)
 */
export const habitNoteSchema = minMaxString(
  "note",
  0,
  STRING_LIMITS.HABIT_NOTE_MAX,
  { optional: true }
);

/**
 * Energy note validation - up to 500 characters (optional)
 */
export const energyNoteSchema = minMaxString(
  "note",
  0,
  STRING_LIMITS.ENERGY_NOTE_MAX,
  { optional: true }
);

/**
 * Brain dump content validation - 1 to 5000 characters
 */
export const brainDumpContentSchema = minMaxString(
  "content",
  STRING_LIMITS.BRAIN_DUMP_CONTENT_MIN,
  STRING_LIMITS.BRAIN_DUMP_CONTENT_MAX
);

/**
 * Days validation for streak calculations - 1 to 365 days
 */
export const daysStreakSchema = boundedInt(
  "days",
  NUMERIC_LIMITS.DAYS_MIN,
  NUMERIC_LIMITS.DAYS_MAX_STREAKS,
  { optional: true }
);

/**
 * Days validation for dashboard visualizations - 1 to 90 days
 */
export const daysDashboardSchema = boundedInt(
  "days",
  NUMERIC_LIMITS.DAYS_MIN,
  NUMERIC_LIMITS.DAYS_MAX_DASHBOARD,
  { optional: true }
);

/**
 * Habit target count validation - 1 to 100 completions
 */
export const targetCountSchema = boundedInt(
  "targetCount",
  NUMERIC_LIMITS.TARGET_COUNT_MIN,
  NUMERIC_LIMITS.TARGET_COUNT_MAX,
  { optional: true }
);

/**
 * Oura readiness score validation - 0 to 100
 */
export const ouraReadinessSchema = boundedInt(
  "ouraReadiness",
  NUMERIC_LIMITS.OURA_READINESS_MIN,
  NUMERIC_LIMITS.OURA_READINESS_MAX,
  { optional: true }
);

/**
 * Oura HRV validation - 0 to 300 ms
 */
export const ouraHrvSchema = boundedInt(
  "ouraHrv",
  NUMERIC_LIMITS.OURA_HRV_MIN,
  NUMERIC_LIMITS.OURA_HRV_MAX,
  { optional: true }
);

/**
 * Oura sleep score validation - 0 to 100
 */
export const ouraSleepSchema = boundedInt(
  "ouraSleep",
  NUMERIC_LIMITS.OURA_SLEEP_MIN,
  NUMERIC_LIMITS.OURA_SLEEP_MAX,
  { optional: true }
);

// =============================================================================
// ENUM SCHEMAS
// =============================================================================

/**
 * Task status enum validation
 */
export const taskStatusSchema = z.enum(["active", "queued", "backlog", "done"], {
  errorMap: () => ({
    message: "status must be one of: active, queued, backlog, done",
  }),
});

/**
 * Task category enum validation
 */
export const taskCategorySchema = z.enum(["work", "personal"], {
  errorMap: () => ({
    message: "category must be one of: work, personal",
  }),
});

/**
 * Task value tier enum validation
 */
export const valueTierSchema = z.enum(
  ["checkbox", "progress", "deliverable", "milestone"],
  {
    errorMap: () => ({
      message:
        "valueTier must be one of: checkbox, progress, deliverable, milestone",
    }),
  }
);

/**
 * Task drain type enum validation
 */
export const drainTypeSchema = z.enum(["deep", "shallow", "admin"], {
  errorMap: () => ({
    message: "drainType must be one of: deep, shallow, admin",
  }),
});

/**
 * Habit frequency enum validation
 */
export const habitFrequencySchema = z.enum(["daily", "weekdays", "weekly"], {
  errorMap: () => ({
    message: "frequency must be one of: daily, weekdays, weekly",
  }),
});

/**
 * Habit time of day enum validation
 */
export const habitTimeOfDaySchema = z.enum(["morning", "evening", "anytime"], {
  errorMap: () => ({
    message: "timeOfDay must be one of: morning, evening, anytime",
  }),
});

/**
 * Habit category enum validation (optional)
 */
export const habitCategorySchema = z
  .enum(["health", "productivity", "relationship", "personal"])
  .optional();

/**
 * Energy level enum validation
 */
export const energyLevelSchema = z.enum(["high", "medium", "low"], {
  errorMap: () => ({
    message: "level must be one of: high, medium, low",
  }),
});

/**
 * Energy source enum validation
 */
export const energySourceSchema = z.enum(["manual", "oura"], {
  errorMap: () => ({
    message: "source must be one of: manual, oura",
  }),
});

/**
 * Brain dump category enum validation (optional)
 */
export const brainDumpCategorySchema = z
  .enum(["thought", "task", "idea", "worry"])
  .optional();

/**
 * Dashboard format enum validation (optional)
 */
export const dashboardFormatSchema = z
  .enum(["simple", "detailed"])
  .optional();

// =============================================================================
// VALIDATION UTILITY FUNCTIONS
// =============================================================================

/**
 * Validates tool input using a Zod schema and returns friendly error messages
 *
 * @param schema - Zod schema to validate against
 * @param input - Input data to validate
 * @returns Validation result with success flag and data or error messages
 *
 * @example
 * const result = validateToolInput(taskIdSchema, { taskId: 123 });
 * if (!result.success) {
 *   return errorResponse(result.error);
 * }
 * const validatedData = result.data;
 */
export function validateToolInput<T>(
  schema: z.ZodSchema<T>,
  input: unknown
): { success: true; data: T } | { success: false; error: string } {
  try {
    const data = schema.parse(input);
    return { success: true, data };
  } catch (error: unknown) {
    if (error instanceof z.ZodError) {
      // Format Zod errors into user-friendly messages
      const zodError = error as z.ZodError;
      const errorMessages = zodError.errors.map((err: z.ZodIssue) => {
        const path = err.path.length > 0 ? err.path.join(".") : "input";
        return `${path}: ${err.message}`;
      });

      return {
        success: false,
        error: `Validation failed: ${errorMessages.join("; ")}`,
      };
    }

    return {
      success: false,
      error: `Validation failed: ${error instanceof Error ? error.message : "Unknown error"}`,
    };
  }
}

/**
 * Creates a sanitized version of input by trimming strings and normalizing values
 * This is a safe operation that doesn't modify the original input
 *
 * @param input - Input data to sanitize
 * @returns Sanitized copy of input data
 *
 * @example
 * const sanitized = sanitizeInput({ title: '  Hello  ', count: 5 });
 * // Returns: { title: 'Hello', count: 5 }
 */
export function sanitizeInput<T extends Record<string, any>>(input: T): T {
  const sanitized: any = {};

  for (const [key, value] of Object.entries(input)) {
    if (typeof value === "string") {
      // Trim whitespace from strings
      sanitized[key] = value.trim();
    } else if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      // Recursively sanitize nested objects
      sanitized[key] = sanitizeInput(value);
    } else {
      // Keep other values as-is (numbers, booleans, arrays, null)
      sanitized[key] = value;
    }
  }

  return sanitized as T;
}

/**
 * Validates and sanitizes tool input in one operation
 * Combines validation and sanitization for convenience
 *
 * @param schema - Zod schema to validate against
 * @param input - Input data to validate and sanitize
 * @returns Validation result with success flag and sanitized data or error messages
 *
 * @example
 * const result = validateAndSanitize(createTaskSchema, args);
 * if (!result.success) {
 *   return errorResponse(result.error);
 * }
 * const { title, description } = result.data;
 */
export function validateAndSanitize<T>(
  schema: z.ZodSchema<T>,
  input: unknown
): { success: true; data: T } | { success: false; error: string } {
  // First sanitize the input (safe for any input type)
  const sanitized = typeof input === "object" && input !== null
    ? sanitizeInput(input as Record<string, any>)
    : input;

  // Then validate the sanitized input
  return validateToolInput(schema, sanitized);
}
