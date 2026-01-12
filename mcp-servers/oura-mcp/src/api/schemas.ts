// =============================================================================
// OURA API ZOD SCHEMAS
// Runtime validation schemas for Oura Ring API v2 responses
// Matches types defined in types.ts
// =============================================================================

import { z } from "zod";

// =============================================================================
// COMMON SCHEMAS
// =============================================================================

/**
 * ISO 8601 date string (YYYY-MM-DD)
 */
export const DateStringSchema = z.string().regex(
  /^\d{4}-\d{2}-\d{2}$/,
  "Must be a valid date in YYYY-MM-DD format"
);

/**
 * ISO 8601 datetime string with timezone
 */
export const DateTimeStringSchema = z.string().regex(
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/,
  "Must be a valid ISO 8601 datetime string"
);

/**
 * Score value (0-100 or null)
 */
export const ScoreSchema = z.number().min(0).max(100).nullable();

/**
 * Paginated API response wrapper
 */
export const OuraAPIResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    data: z.array(dataSchema),
    next_token: z.string().nullable(),
  });

/**
 * API request options for date-based queries
 */
export const APIRequestOptionsSchema = z.object({
  startDate: DateStringSchema.optional(),
  endDate: DateStringSchema.optional(),
  nextToken: z.string().optional(),
});

/**
 * API error response structure
 */
export const OuraAPIErrorSchema = z.object({
  detail: z.string().optional(),
  message: z.string().optional(),
  status: z.number().optional(),
});

// =============================================================================
// SLEEP DATA SCHEMAS
// =============================================================================

/**
 * Sleep score contributors
 */
export const SleepContributorsSchema = z.object({
  deep_sleep: ScoreSchema,
  efficiency: ScoreSchema,
  latency: ScoreSchema,
  rem_sleep: ScoreSchema,
  restfulness: ScoreSchema,
  timing: ScoreSchema,
  total_sleep: ScoreSchema,
});

/**
 * Sleep timing information
 */
export const SleepTimingSchema = z.object({
  bedtime_start: DateTimeStringSchema.nullable(),
  bedtime_end: DateTimeStringSchema.nullable(),
});

/**
 * Sleep period type
 */
export const SleepPeriodTypeSchema = z.enum([
  "long_sleep",
  "short_sleep",
  "nap",
  "rest",
]);

/**
 * Daily sleep data from Oura API
 */
export const DailySleepSchema = z.object({
  id: z.string(),
  day: DateStringSchema,
  score: ScoreSchema,
  contributors: SleepContributorsSchema,
  total_sleep_duration: z.number().nullable(),
  time_in_bed: z.number().nullable(),
  awake_time: z.number().nullable(),
  light_sleep_duration: z.number().nullable(),
  deep_sleep_duration: z.number().nullable(),
  rem_sleep_duration: z.number().nullable(),
  restless_periods: z.number().nullable(),
  efficiency: z.number().min(0).max(100).nullable(),
  latency: z.number().nullable(),
  timing: SleepTimingSchema,
  type: SleepPeriodTypeSchema.optional(),
  average_heart_rate: z.number().nullable().optional(),
  lowest_heart_rate: z.number().nullable().optional(),
  average_hrv: z.number().nullable().optional(),
  average_breath: z.number().nullable().optional(),
  temperature_deviation: z.number().nullable().optional(),
  temperature_trend_deviation: z.number().nullable().optional(),
});

/**
 * Sleep data alias for consistency
 */
export const SleepDataSchema = DailySleepSchema;

/**
 * Paginated sleep response
 */
export const SleepResponseSchema = OuraAPIResponseSchema(DailySleepSchema);

// =============================================================================
// READINESS DATA SCHEMAS
// =============================================================================

/**
 * Readiness score contributors
 */
export const ReadinessContributorsSchema = z.object({
  activity_balance: ScoreSchema,
  body_temperature: ScoreSchema,
  hrv_balance: ScoreSchema,
  previous_day_activity: ScoreSchema,
  previous_night: ScoreSchema,
  recovery_index: ScoreSchema,
  resting_heart_rate: ScoreSchema,
  sleep_balance: ScoreSchema,
});

/**
 * Daily readiness data from Oura API
 */
export const DailyReadinessSchema = z.object({
  id: z.string(),
  day: DateStringSchema,
  score: ScoreSchema,
  contributors: ReadinessContributorsSchema,
  temperature_deviation: z.number().nullable(),
  temperature_trend_deviation: z.number().nullable(),
  resting_heart_rate: z.number().nullable().optional(),
  hrv_balance: z.number().nullable().optional(),
});

/**
 * Readiness data alias for consistency
 */
export const ReadinessDataSchema = DailyReadinessSchema;

/**
 * Paginated readiness response
 */
export const ReadinessResponseSchema = OuraAPIResponseSchema(DailyReadinessSchema);

// =============================================================================
// ACTIVITY DATA SCHEMAS
// =============================================================================

/**
 * Activity score contributors
 */
export const ActivityContributorsSchema = z.object({
  meet_daily_targets: ScoreSchema,
  move_every_hour: ScoreSchema,
  recovery_time: ScoreSchema,
  stay_active: ScoreSchema,
  training_frequency: ScoreSchema,
  training_volume: ScoreSchema,
});

/**
 * Activity class
 */
export const ActivityClassSchema = z.enum([
  "non_wear",
  "rest",
  "inactive",
  "low",
  "medium",
  "high",
]);

/**
 * MET (Metabolic Equivalent of Task) levels
 */
export const METLevelsSchema = z.object({
  sedentary: z.number().nullable(),
  low: z.number().nullable(),
  medium: z.number().nullable(),
  high: z.number().nullable(),
});

/**
 * Daily activity data from Oura API
 */
export const DailyActivitySchema = z.object({
  id: z.string(),
  day: DateStringSchema,
  score: ScoreSchema,
  active_calories: z.number().nullable(),
  average_met_minutes: z.number().nullable(),
  contributors: ActivityContributorsSchema,
  equivalent_walking_distance: z.number().nullable(),
  high_activity_met_minutes: z.number().nullable(),
  high_activity_time: z.number().nullable(),
  inactivity_alerts: z.number().nullable(),
  low_activity_met_minutes: z.number().nullable(),
  low_activity_time: z.number().nullable(),
  medium_activity_met_minutes: z.number().nullable(),
  medium_activity_time: z.number().nullable(),
  meters_to_target: z.number().nullable(),
  non_wear_time: z.number().nullable(),
  resting_time: z.number().nullable(),
  sedentary_met_minutes: z.number().nullable(),
  sedentary_time: z.number().nullable(),
  steps: z.number().nullable(),
  target_calories: z.number().nullable(),
  target_meters: z.number().nullable(),
  total_calories: z.number().nullable(),
  class: ActivityClassSchema.optional(),
});

/**
 * Activity data alias for consistency
 */
export const ActivityDataSchema = DailyActivitySchema;

/**
 * Paginated activity response
 */
export const ActivityResponseSchema = OuraAPIResponseSchema(DailyActivitySchema);

// =============================================================================
// HEART RATE DATA SCHEMAS
// =============================================================================

/**
 * Heart rate data source
 */
export const HeartRateSourceSchema = z.enum([
  "sleep",
  "rest",
  "activity",
  "live",
  "workout",
]);

/**
 * Individual heart rate data point
 */
export const HeartRateDataSchema = z.object({
  bpm: z.number().min(0).max(300),
  source: HeartRateSourceSchema,
  timestamp: DateTimeStringSchema,
});

/**
 * Paginated heart rate response
 */
export const HeartRateResponseSchema = OuraAPIResponseSchema(HeartRateDataSchema);

// =============================================================================
// HRV DATA SCHEMAS
// =============================================================================

/**
 * HRV data point
 */
export const HRVDataSchema = z.object({
  hrv: z.number(),
  timestamp: DateTimeStringSchema,
});

/**
 * Paginated HRV response
 */
export const HRVResponseSchema = OuraAPIResponseSchema(HRVDataSchema);

// =============================================================================
// WORKOUT DATA SCHEMAS
// =============================================================================

/**
 * Workout activity type
 */
export const WorkoutActivitySchema = z.enum([
  "cycling",
  "running",
  "swimming",
  "walking",
  "strength_training",
  "yoga",
  "cross_training",
  "high_intensity_interval_training",
  "other",
]);

/**
 * Workout intensity level
 */
export const WorkoutIntensitySchema = z.enum(["easy", "moderate", "hard"]);

/**
 * Workout data from Oura API
 */
export const WorkoutDataSchema = z.object({
  id: z.string(),
  activity: WorkoutActivitySchema,
  start_datetime: DateTimeStringSchema,
  end_datetime: DateTimeStringSchema,
  intensity: WorkoutIntensitySchema,
  calories: z.number().nullable(),
  distance: z.number().nullable(),
  label: z.string().nullable().optional(),
  source: z.string().optional(),
});

/**
 * Paginated workout response
 */
export const WorkoutResponseSchema = OuraAPIResponseSchema(WorkoutDataSchema);

// =============================================================================
// SESSION DATA SCHEMAS
// =============================================================================

/**
 * Session type
 */
export const SessionTypeSchema = z.enum([
  "rest",
  "breathing",
  "meditation",
  "nap",
  "relaxation",
  "body_status",
]);

/**
 * Session mood
 */
export const SessionMoodSchema = z.enum(["bad", "worse", "same", "good", "great"]);

/**
 * Session data from Oura API
 */
export const SessionDataSchema = z.object({
  id: z.string(),
  day: DateStringSchema,
  start_datetime: DateTimeStringSchema,
  end_datetime: DateTimeStringSchema,
  type: SessionTypeSchema,
  mood: SessionMoodSchema.nullable().optional(),
  mood_after: SessionMoodSchema.nullable().optional(),
  heart_rate: z
    .object({
      average: z.number().nullable(),
      minimum: z.number().nullable(),
      maximum: z.number().nullable(),
    })
    .optional(),
});

/**
 * Paginated session response
 */
export const SessionResponseSchema = OuraAPIResponseSchema(SessionDataSchema);

// =============================================================================
// TAG DATA SCHEMAS
// =============================================================================

/**
 * Custom tag for tracking habits, events, or notes
 */
export const TagDataSchema = z.object({
  id: z.string(),
  tag: z.string(),
  timestamp: DateTimeStringSchema,
  comment: z.string().nullable().optional(),
});

/**
 * Paginated tag response
 */
export const TagResponseSchema = OuraAPIResponseSchema(TagDataSchema);

// =============================================================================
// PERSONAL INFO SCHEMAS
// =============================================================================

/**
 * User's personal information
 */
export const PersonalInfoSchema = z.object({
  id: z.string(),
  age: z.number().nullable(),
  weight: z.number().nullable(),
  height: z.number().nullable(),
  biological_sex: z.enum(["male", "female"]).nullable(),
  email: z.string().email().nullable(),
});

// =============================================================================
// RING CONFIGURATION SCHEMAS
// =============================================================================

/**
 * Ring configuration settings
 */
export const RingConfigurationSchema = z.object({
  id: z.string(),
  color: z.string().nullable(),
  design: z.string().nullable(),
  size: z.number().nullable(),
  firmware_version: z.string().nullable(),
  hardware_type: z.string().nullable(),
  set_up_at: DateTimeStringSchema.nullable(),
});

// =============================================================================
// DAILY SUMMARY SCHEMAS
// =============================================================================

/**
 * Comprehensive daily health summary
 */
export const DailySummarySchema = z.object({
  date: DateStringSchema,
  sleep: DailySleepSchema.nullable(),
  readiness: DailyReadinessSchema.nullable(),
  activity: DailyActivitySchema.nullable(),
});

// =============================================================================
// TRENDS AND ANALYTICS SCHEMAS
// =============================================================================

/**
 * Trend direction indicator
 */
export const TrendDirectionSchema = z.enum(["improving", "declining", "stable"]);

/**
 * Statistical summary for a metric
 */
export const MetricStatisticsSchema = z.object({
  average: z.number(),
  min: z.number(),
  max: z.number(),
  std_dev: z.number().optional(),
  trend: TrendDirectionSchema.optional(),
  daily_values: z.array(z.number().nullable()),
});

/**
 * Weekly trends summary
 */
export const WeeklyTrendsSchema = z.object({
  period: z.string(),
  readiness: MetricStatisticsSchema,
  sleep: MetricStatisticsSchema,
  activity: MetricStatisticsSchema,
  insights: z.array(z.string()),
});

// =============================================================================
// CACHE METADATA SCHEMAS
// =============================================================================

/**
 * Cache metadata for tracking freshness
 */
export const CacheMetadataSchema = z.object({
  cached_at: DateTimeStringSchema,
  expires_at: DateTimeStringSchema,
  is_stale: z.boolean(),
  source: z.enum(["api", "cache"]),
});

// =============================================================================
// VALIDATION HELPERS
// =============================================================================

/**
 * Validates API response data and returns typed result
 * Throws descriptive error if validation fails
 */
export function validateResponse<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  context?: string
): T {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      const issues = error.issues.map((issue) => {
        const path = issue.path.join(".");
        return `${path}: ${issue.message}`;
      });
      throw new Error(
        `Validation failed${context ? ` for ${context}` : ""}: ${issues.join(", ")}`
      );
    }
    throw error;
  }
}

/**
 * Safely validates data and returns result or null
 * Useful for optional/graceful validation
 */
export function safeValidate<T>(
  schema: z.ZodSchema<T>,
  data: unknown
): T | null {
  const result = schema.safeParse(data);
  return result.success ? result.data : null;
}

/**
 * Validates paginated API response
 */
export function validatePaginatedResponse<T>(
  itemSchema: z.ZodSchema<T>,
  data: unknown,
  context?: string
): { data: T[]; next_token: string | null } {
  return validateResponse(OuraAPIResponseSchema(itemSchema), data, context);
}

// =============================================================================
// SCHEMA EXPORTS FOR TYPE INFERENCE
// =============================================================================

// Export all schemas for use in validation
export const schemas = {
  // Common
  DateString: DateStringSchema,
  DateTime: DateTimeStringSchema,
  Score: ScoreSchema,
  OuraAPIResponse: OuraAPIResponseSchema,
  OuraAPIError: OuraAPIErrorSchema,

  // Sleep
  SleepContributors: SleepContributorsSchema,
  SleepTiming: SleepTimingSchema,
  SleepPeriodType: SleepPeriodTypeSchema,
  DailySleep: DailySleepSchema,
  SleepData: SleepDataSchema,
  SleepResponse: SleepResponseSchema,

  // Readiness
  ReadinessContributors: ReadinessContributorsSchema,
  DailyReadiness: DailyReadinessSchema,
  ReadinessData: ReadinessDataSchema,
  ReadinessResponse: ReadinessResponseSchema,

  // Activity
  ActivityContributors: ActivityContributorsSchema,
  ActivityClass: ActivityClassSchema,
  METLevels: METLevelsSchema,
  DailyActivity: DailyActivitySchema,
  ActivityData: ActivityDataSchema,
  ActivityResponse: ActivityResponseSchema,

  // Heart Rate & HRV
  HeartRateSource: HeartRateSourceSchema,
  HeartRateData: HeartRateDataSchema,
  HeartRateResponse: HeartRateResponseSchema,
  HRVData: HRVDataSchema,
  HRVResponse: HRVResponseSchema,

  // Workout
  WorkoutActivity: WorkoutActivitySchema,
  WorkoutIntensity: WorkoutIntensitySchema,
  WorkoutData: WorkoutDataSchema,
  WorkoutResponse: WorkoutResponseSchema,

  // Session
  SessionType: SessionTypeSchema,
  SessionMood: SessionMoodSchema,
  SessionData: SessionDataSchema,
  SessionResponse: SessionResponseSchema,

  // Tag
  TagData: TagDataSchema,
  TagResponse: TagResponseSchema,

  // Personal Info & Ring
  PersonalInfo: PersonalInfoSchema,
  RingConfiguration: RingConfigurationSchema,

  // Summary & Trends
  DailySummary: DailySummarySchema,
  TrendDirection: TrendDirectionSchema,
  MetricStatistics: MetricStatisticsSchema,
  WeeklyTrends: WeeklyTrendsSchema,

  // Cache
  CacheMetadata: CacheMetadataSchema,
};

// Export type inference helpers
export type ValidatedSleepData = z.infer<typeof DailySleepSchema>;
export type ValidatedReadinessData = z.infer<typeof DailyReadinessSchema>;
export type ValidatedActivityData = z.infer<typeof DailyActivitySchema>;
export type ValidatedHeartRateData = z.infer<typeof HeartRateDataSchema>;
export type ValidatedWorkoutData = z.infer<typeof WorkoutDataSchema>;
export type ValidatedSessionData = z.infer<typeof SessionDataSchema>;
export type ValidatedTagData = z.infer<typeof TagDataSchema>;
export type ValidatedDailySummary = z.infer<typeof DailySummarySchema>;
export type ValidatedWeeklyTrends = z.infer<typeof WeeklyTrendsSchema>;
