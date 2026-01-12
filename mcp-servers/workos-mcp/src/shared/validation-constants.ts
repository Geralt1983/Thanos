// =============================================================================
// INPUT VALIDATION CONSTANTS
// =============================================================================
// This file defines all input validation bounds for the workos-mcp server.
// These limits prevent abuse, resource exhaustion, and injection attempts.
//
// Design Rationale:
// - Security First: Prevent unbounded inputs that could cause resource exhaustion
// - Generous Bounds: Set limits high enough for legitimate use cases
// - Consistency: Use similar bounds for similar field types across domains
// - Performance: Limit query parameters to prevent database overload
// - User-Friendly: Choose limits that feel natural and won't surprise users
// =============================================================================

// =============================================================================
// STRING LENGTH LIMITS
// =============================================================================

/**
 * String field length limits
 *
 * Rationale:
 * - Prevents memory exhaustion from massive strings
 * - Improves database performance (VARCHAR fields with max lengths)
 * - Encourages concise, useful content
 * - Limits database storage growth
 */
export const STRING_LIMITS = {
  // Task domain
  /** Task titles should be concise. 200 chars = ~30 words, sufficient for clarity without verbosity. */
  TASK_TITLE_MAX: 200,
  /** Minimum 1 character to prevent empty titles */
  TASK_TITLE_MIN: 1,
  /** Detailed task descriptions. 2000 chars = ~300 words, enough for comprehensive context. */
  TASK_DESCRIPTION_MAX: 2000,
  /** Client names (company names or identifiers). 100 chars accommodates long names. */
  CLIENT_NAME_MAX: 100,
  /** Minimum 1 character for client names */
  CLIENT_NAME_MIN: 1,

  // Habit domain
  /** Habit names should be concise. 100 chars accommodates verbose habit names. */
  HABIT_NAME_MAX: 100,
  /** Minimum 1 character for habit names */
  HABIT_NAME_MIN: 1,
  /** Habit descriptions are shorter than task descriptions. 500 chars = ~75 words. */
  HABIT_DESCRIPTION_MAX: 500,
  /** Emojis are 1-4 bytes in UTF-8. Allow up to 10 chars for multi-codepoint emojis or emoji sequences. */
  HABIT_EMOJI_MAX: 10,
  /** Quick notes on habit completions. 500 chars for brief reflections without essay-length entries. */
  HABIT_NOTE_MAX: 500,

  // Energy domain
  /** Energy log notes for context. 500 chars for brief reflections. */
  ENERGY_NOTE_MAX: 500,

  // Brain dump domain
  /** Brain dumps can be longer-form thoughts/ideas. 5000 chars = ~750 words, enough for comprehensive idea capture. */
  BRAIN_DUMP_CONTENT_MAX: 5000,
  /** Minimum 1 character for brain dump content */
  BRAIN_DUMP_CONTENT_MIN: 1,
} as const;

// =============================================================================
// NUMERIC FIELD LIMITS
// =============================================================================

/**
 * Numeric field validation limits
 *
 * Rationale:
 * - Query Limits: Prevent database overload from massive result sets
 * - ID Validation: Ensure IDs are valid database primary keys (positive integers)
 * - Range Validation: Enforce documented ranges (e.g., Oura scores 0-100)
 * - Performance: Prevent expensive operations (e.g., calculating 10,000 days of habit streaks)
 */
export const NUMERIC_LIMITS = {
  // Query limits (consistent across all domains)
  /** Minimum query limit - can't request 0 or negative items */
  QUERY_LIMIT_MIN: 1,
  /** Maximum query limit - prevents massive queries while being generous for legitimate use */
  QUERY_LIMIT_MAX: 100,
  /** Default limit for task queries */
  QUERY_LIMIT_DEFAULT_TASKS: 50,
  /** Default limit for brain dump queries */
  QUERY_LIMIT_DEFAULT_BRAIN_DUMP: 20,
  /** Default limit for personal task queries */
  QUERY_LIMIT_DEFAULT_PERSONAL: 20,
  /** Default limit for energy log queries */
  QUERY_LIMIT_DEFAULT_ENERGY: 5,

  // ID validation (all positive integers)
  /** Minimum valid ID - all database IDs start at 1 */
  ID_MIN: 1,
  /** Maximum valid ID - PostgreSQL INT32_MAX */
  ID_MAX: 2147483647,

  // Date ranges
  /** Minimum days for lookback periods */
  DAYS_MIN: 1,
  /** Maximum days for streak calculations - 1 year for performance balance */
  DAYS_MAX_STREAKS: 365,
  /** Maximum days for dashboard visualizations - 90 days (3 months) for readability */
  DAYS_MAX_DASHBOARD: 90,

  // Habit counts
  /** Minimum habit target count - must complete at least once */
  TARGET_COUNT_MIN: 1,
  /** Maximum habit target count - prevents absurd values (e.g., 10,000 daily completions) */
  TARGET_COUNT_MAX: 100,

  // Oura health metrics (based on manufacturer-documented ranges)
  /** Oura Ring readiness score minimum - official range is 0-100 */
  OURA_READINESS_MIN: 0,
  /** Oura Ring readiness score maximum - official range is 0-100 */
  OURA_READINESS_MAX: 100,
  /** Heart Rate Variability minimum - 0 allows null-equivalent if not measured */
  OURA_HRV_MIN: 0,
  /** Heart Rate Variability maximum - typical range 20-100ms, 300ms max captures outliers */
  OURA_HRV_MAX: 300,
  /** Oura Ring sleep score minimum - official range is 0-100 */
  OURA_SLEEP_MIN: 0,
  /** Oura Ring sleep score maximum - official range is 0-100 */
  OURA_SLEEP_MAX: 100,
} as const;

// =============================================================================
// RATE LIMITING CONFIGURATION
// =============================================================================

/**
 * Rate limiting constants
 *
 * Rationale:
 * - Abuse Prevention: Stop malicious actors from overwhelming the server
 * - Cost Control: Prevent runaway database query costs
 * - Fair Usage: Ensure resources available for all users
 * - Resource Protection: Prevent single client from exhausting connections/memory
 * - Gradual Limits: Different tiers for different operation types
 *
 * Strategy:
 * - Sliding Window Algorithm: Track timestamps of recent requests
 * - In-Memory Storage: Faster than database/Redis, sufficient for single-instance
 * - Environment Variable Overrides: Allow operators to adjust without code changes
 */
export const RATE_LIMITS = {
  // Global limits
  /** Global requests per minute - allows burst activity while preventing abuse (~1.7 req/sec) */
  GLOBAL_PER_MINUTE: Number(process.env.RATE_LIMIT_GLOBAL_PER_MINUTE) || 100,
  /** Global requests per hour - hourly cap to prevent sustained abuse (~50 req/min sustained) */
  GLOBAL_PER_HOUR: Number(process.env.RATE_LIMIT_GLOBAL_PER_HOUR) || 3000,

  // Operation type limits
  /** Write operations per minute - lower limit prevents rapid creation/deletion abuse */
  WRITE_OPS_PER_MINUTE: Number(process.env.RATE_LIMIT_WRITE_PER_MINUTE) || 20,
  /** Read operations per minute - higher limit for legitimate monitoring/dashboards */
  READ_OPS_PER_MINUTE: Number(process.env.RATE_LIMIT_READ_PER_MINUTE) || 60,

  // Window durations (milliseconds)
  /** One minute window in milliseconds */
  WINDOW_ONE_MINUTE: 60 * 1000,
  /** One hour window in milliseconds */
  WINDOW_ONE_HOUR: 60 * 60 * 1000,

  // Cleanup interval (remove old requests periodically to prevent memory growth)
  /** Cleanup old request records every 5 minutes */
  CLEANUP_INTERVAL: 5 * 60 * 1000,
} as const;

/**
 * Rate limit configuration with environment variable overrides
 *
 * Environment Variables:
 * - RATE_LIMIT_ENABLED: Set to 'false' to disable rate limiting (default: true)
 * - RATE_LIMIT_GLOBAL_PER_MINUTE: Override global per-minute limit
 * - RATE_LIMIT_GLOBAL_PER_HOUR: Override global per-hour limit
 * - RATE_LIMIT_WRITE_PER_MINUTE: Override write operations per-minute limit
 * - RATE_LIMIT_READ_PER_MINUTE: Override read operations per-minute limit
 */
export const RATE_LIMIT_CONFIG = {
  /** Whether rate limiting is enabled - default true, set RATE_LIMIT_ENABLED=false to disable */
  enabled: process.env.RATE_LIMIT_ENABLED !== 'false',
  /** Global requests per minute limit */
  globalPerMinute: RATE_LIMITS.GLOBAL_PER_MINUTE,
  /** Global requests per hour limit */
  globalPerHour: RATE_LIMITS.GLOBAL_PER_HOUR,
  /** Write operations per minute limit */
  writeOpsPerMinute: RATE_LIMITS.WRITE_OPS_PER_MINUTE,
  /** Read operations per minute limit */
  readOpsPerMinute: RATE_LIMITS.READ_OPS_PER_MINUTE,
} as const;

// =============================================================================
// VALIDATION ERROR MESSAGE TEMPLATES
// =============================================================================

/**
 * Standardized error message templates for validation failures
 *
 * Design Principles:
 * - Be Specific: Tell user exactly what's wrong
 * - Show Limits: Display the valid range
 * - Suggest Fix: Guide user to correct input
 * - Be Consistent: Use same format across all validation errors
 */
export const ERROR_MESSAGES = {
  // String validation errors
  /** Error message for string too short */
  STRING_TOO_SHORT: (field: string, min: number, actual: number) =>
    `${field} must be at least ${min} character${min !== 1 ? 's' : ''} (received: ${actual} character${actual !== 1 ? 's' : ''})`,

  /** Error message for string too long */
  STRING_TOO_LONG: (field: string, max: number, actual: number) =>
    `${field} must not exceed ${max} character${max !== 1 ? 's' : ''} (received: ${actual} character${actual !== 1 ? 's' : ''})`,

  /** Error message for empty required field */
  STRING_EMPTY: (field: string) =>
    `${field} is required and cannot be empty`,

  // Numeric validation errors
  /** Error message for number out of range */
  NUMBER_OUT_OF_RANGE: (field: string, min: number, max: number, actual: number) =>
    `${field} must be between ${min} and ${max} (received: ${actual})`,

  /** Error message for non-positive integer */
  NUMBER_NOT_POSITIVE_INT: (field: string, actual: number) =>
    `${field} must be a positive integer (received: ${actual})`,

  /** Error message for non-integer value */
  NUMBER_NOT_INTEGER: (field: string) =>
    `${field} must be an integer`,

  // Rate limiting errors
  /** Error message for rate limit exceeded */
  RATE_LIMIT_EXCEEDED: (type: string, count: number, limit: number, window: string, retryAfter: number) =>
    `Rate limit exceeded: You have made ${count} ${type} request${count !== 1 ? 's' : ''} in the last ${window} (limit: ${limit}). Please wait ${retryAfter} second${retryAfter !== 1 ? 's' : ''} and try again.`,
} as const;
