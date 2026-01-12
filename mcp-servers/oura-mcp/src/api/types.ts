// =============================================================================
// OURA API TYPES
// Type definitions for Oura Ring API v2 responses
// API Reference: https://cloud.ouraring.com/v2/docs
// =============================================================================

// =============================================================================
// COMMON TYPES
// =============================================================================

/**
 * ISO 8601 date string (YYYY-MM-DD)
 */
export type DateString = string;

/**
 * ISO 8601 datetime string with timezone
 */
export type DateTimeString = string;

/**
 * Paginated API response wrapper
 * All Oura API endpoints return data in this format
 */
export interface OuraAPIResponse<T> {
  /** Array of data items */
  data: T[];
  /** Pagination token for next page, null if no more pages */
  next_token: string | null;
}

/**
 * API request options for date-based queries
 */
export interface APIRequestOptions {
  /** Start date (YYYY-MM-DD) */
  startDate?: DateString;
  /** End date (YYYY-MM-DD) */
  endDate?: DateString;
  /** Pagination token from previous response */
  nextToken?: string;
}

/**
 * API error response structure
 */
export interface OuraAPIError {
  /** Error detail message */
  detail?: string;
  /** Error message */
  message?: string;
  /** HTTP status code */
  status?: number;
}

// =============================================================================
// SLEEP DATA TYPES
// =============================================================================

/**
 * Sleep score contributors
 * Each contributor is a score from 0-100 or null if unavailable
 */
export interface SleepContributors {
  /** Deep sleep score (0-100) */
  deep_sleep: number | null;
  /** Sleep efficiency score (0-100) */
  efficiency: number | null;
  /** Sleep latency score (0-100) */
  latency: number | null;
  /** REM sleep score (0-100) */
  rem_sleep: number | null;
  /** Restfulness score (0-100) */
  restfulness: number | null;
  /** Sleep timing score (0-100) */
  timing: number | null;
  /** Total sleep score (0-100) */
  total_sleep: number | null;
}

/**
 * Sleep timing information
 */
export interface SleepTiming {
  /** Bedtime start (ISO 8601) */
  bedtime_start: DateTimeString | null;
  /** Bedtime end (ISO 8601) */
  bedtime_end: DateTimeString | null;
}

/**
 * Sleep period type
 */
export type SleepPeriodType = "long_sleep" | "short_sleep" | "nap" | "rest";

/**
 * Daily sleep data from Oura API
 * Represents a single night's sleep with comprehensive metrics
 */
export interface DailySleep {
  /** Unique identifier for this sleep record */
  id: string;
  /** Date of the sleep period (YYYY-MM-DD) */
  day: DateString;
  /** Overall sleep score (0-100), null if unavailable */
  score: number | null;
  /** Individual contributor scores */
  contributors: SleepContributors;
  /** Total sleep duration in seconds */
  total_sleep_duration: number | null;
  /** Total time in bed in seconds */
  time_in_bed: number | null;
  /** Time awake in seconds */
  awake_time: number | null;
  /** Light sleep duration in seconds */
  light_sleep_duration: number | null;
  /** Deep sleep duration in seconds */
  deep_sleep_duration: number | null;
  /** REM sleep duration in seconds */
  rem_sleep_duration: number | null;
  /** Number of restless periods */
  restless_periods: number | null;
  /** Sleep efficiency percentage (0-100) */
  efficiency: number | null;
  /** Sleep latency (time to fall asleep) in seconds */
  latency: number | null;
  /** Sleep timing information */
  timing: SleepTiming;
  /** Type of sleep period */
  type?: SleepPeriodType;
  /** Average heart rate during sleep (bpm) */
  average_heart_rate?: number | null;
  /** Lowest heart rate during sleep (bpm) */
  lowest_heart_rate?: number | null;
  /** Average HRV (ms) */
  average_hrv?: number | null;
  /** Average breath rate (breaths per minute) */
  average_breath?: number | null;
  /** Body temperature deviation (celsius) */
  temperature_deviation?: number | null;
  /** Skin temperature trend deviation */
  temperature_trend_deviation?: number | null;
}

/**
 * Sleep data alias for consistency with naming convention
 */
export type SleepData = DailySleep;

// =============================================================================
// READINESS DATA TYPES
// =============================================================================

/**
 * Readiness score contributors
 * Each contributor is a score from 0-100 or null if unavailable
 */
export interface ReadinessContributors {
  /** Activity balance score (0-100) */
  activity_balance: number | null;
  /** Body temperature score (0-100) */
  body_temperature: number | null;
  /** HRV balance score (0-100) */
  hrv_balance: number | null;
  /** Previous day activity score (0-100) */
  previous_day_activity: number | null;
  /** Previous night sleep score (0-100) */
  previous_night: number | null;
  /** Recovery index score (0-100) */
  recovery_index: number | null;
  /** Resting heart rate score (0-100) */
  resting_heart_rate: number | null;
  /** Sleep balance score (0-100) */
  sleep_balance: number | null;
}

/**
 * Daily readiness data from Oura API
 * Represents daily readiness for physical and mental performance
 */
export interface DailyReadiness {
  /** Unique identifier for this readiness record */
  id: string;
  /** Date of the readiness data (YYYY-MM-DD) */
  day: DateString;
  /** Overall readiness score (0-100), null if unavailable */
  score: number | null;
  /** Individual contributor scores */
  contributors: ReadinessContributors;
  /** Body temperature deviation from baseline (celsius) */
  temperature_deviation: number | null;
  /** Body temperature trend deviation */
  temperature_trend_deviation: number | null;
  /** Resting heart rate (bpm) */
  resting_heart_rate?: number | null;
  /** HRV balance */
  hrv_balance?: number | null;
}

/**
 * Readiness data alias for consistency with naming convention
 */
export type ReadinessData = DailyReadiness;

// =============================================================================
// ACTIVITY DATA TYPES
// =============================================================================

/**
 * Activity score contributors
 * Each contributor is a score from 0-100 or null if unavailable
 */
export interface ActivityContributors {
  /** Meet daily targets score (0-100) */
  meet_daily_targets: number | null;
  /** Move every hour score (0-100) */
  move_every_hour: number | null;
  /** Recovery time score (0-100) */
  recovery_time: number | null;
  /** Stay active score (0-100) */
  stay_active: number | null;
  /** Training frequency score (0-100) */
  training_frequency: number | null;
  /** Training volume score (0-100) */
  training_volume: number | null;
}

/**
 * Activity class
 */
export type ActivityClass = "non_wear" | "rest" | "inactive" | "low" | "medium" | "high";

/**
 * MET (Metabolic Equivalent of Task) levels
 */
export interface METLevels {
  /** Sedentary MET minutes */
  sedentary: number | null;
  /** Low activity MET minutes */
  low: number | null;
  /** Medium activity MET minutes */
  medium: number | null;
  /** High activity MET minutes */
  high: number | null;
}

/**
 * Daily activity data from Oura API
 * Represents daily movement, calories, and activity patterns
 */
export interface DailyActivity {
  /** Unique identifier for this activity record */
  id: string;
  /** Date of the activity data (YYYY-MM-DD) */
  day: DateString;
  /** Overall activity score (0-100), null if unavailable */
  score: number | null;
  /** Active calories burned (kcal) */
  active_calories: number | null;
  /** Average MET minutes */
  average_met_minutes: number | null;
  /** Individual contributor scores */
  contributors: ActivityContributors;
  /** Equivalent walking distance in meters */
  equivalent_walking_distance: number | null;
  /** High activity MET minutes */
  high_activity_met_minutes: number | null;
  /** High activity time in seconds */
  high_activity_time: number | null;
  /** Number of inactivity alerts */
  inactivity_alerts: number | null;
  /** Low activity MET minutes */
  low_activity_met_minutes: number | null;
  /** Low activity time in seconds */
  low_activity_time: number | null;
  /** Medium activity MET minutes */
  medium_activity_met_minutes: number | null;
  /** Medium activity time in seconds */
  medium_activity_time: number | null;
  /** Meters to target */
  meters_to_target: number | null;
  /** Non-wear time in seconds */
  non_wear_time: number | null;
  /** Resting time in seconds */
  resting_time: number | null;
  /** Sedentary MET minutes */
  sedentary_met_minutes: number | null;
  /** Sedentary time in seconds */
  sedentary_time: number | null;
  /** Step count */
  steps: number | null;
  /** Target calories (kcal) */
  target_calories: number | null;
  /** Target distance in meters */
  target_meters: number | null;
  /** Total calories burned (kcal) */
  total_calories: number | null;
  /** Activity class */
  class?: ActivityClass;
}

/**
 * Activity data alias for consistency with naming convention
 */
export type ActivityData = DailyActivity;

// =============================================================================
// HEART RATE DATA TYPES
// =============================================================================

/**
 * Heart rate data source
 */
export type HeartRateSource = "sleep" | "rest" | "activity" | "live" | "workout";

/**
 * Individual heart rate data point
 */
export interface HeartRateData {
  /** Heart rate in beats per minute */
  bpm: number;
  /** Source of the measurement */
  source: HeartRateSource;
  /** Timestamp of the measurement (ISO 8601) */
  timestamp: DateTimeString;
}

// =============================================================================
// HRV (HEART RATE VARIABILITY) DATA TYPES
// =============================================================================

/**
 * HRV data point
 */
export interface HRVData {
  /** HRV value in milliseconds */
  hrv: number;
  /** Timestamp of the measurement (ISO 8601) */
  timestamp: DateTimeString;
}

// =============================================================================
// WORKOUT DATA TYPES
// =============================================================================

/**
 * Workout activity type
 */
export type WorkoutActivity =
  | "cycling"
  | "running"
  | "swimming"
  | "walking"
  | "strength_training"
  | "yoga"
  | "cross_training"
  | "high_intensity_interval_training"
  | "other";

/**
 * Workout intensity level
 */
export type WorkoutIntensity = "easy" | "moderate" | "hard";

/**
 * Workout data from Oura API
 */
export interface WorkoutData {
  /** Unique identifier for this workout */
  id: string;
  /** Activity type */
  activity: WorkoutActivity;
  /** Workout start time (ISO 8601) */
  start_datetime: DateTimeString;
  /** Workout end time (ISO 8601) */
  end_datetime: DateTimeString;
  /** Workout intensity */
  intensity: WorkoutIntensity;
  /** Calories burned during workout (kcal) */
  calories: number | null;
  /** Distance covered in meters */
  distance: number | null;
  /** Workout label/name */
  label?: string | null;
  /** Source of workout data */
  source?: string;
}

// =============================================================================
// SESSION DATA TYPES
// =============================================================================

/**
 * Session type
 */
export type SessionType =
  | "rest"
  | "breathing"
  | "meditation"
  | "nap"
  | "relaxation"
  | "body_status";

/**
 * Session mood
 */
export type SessionMood = "bad" | "worse" | "same" | "good" | "great";

/**
 * Session data from Oura API
 */
export interface SessionData {
  /** Unique identifier for this session */
  id: string;
  /** Date of the session (YYYY-MM-DD) */
  day: DateString;
  /** Session start time (ISO 8601) */
  start_datetime: DateTimeString;
  /** Session end time (ISO 8601) */
  end_datetime: DateTimeString;
  /** Type of session */
  type: SessionType;
  /** Mood before session */
  mood?: SessionMood | null;
  /** Mood after session */
  mood_after?: SessionMood | null;
  /** Heart rate data during session */
  heart_rate?: {
    /** Average heart rate (bpm) */
    average: number | null;
    /** Minimum heart rate (bpm) */
    minimum: number | null;
    /** Maximum heart rate (bpm) */
    maximum: number | null;
  };
}

// =============================================================================
// TAG DATA TYPES
// =============================================================================

/**
 * Custom tag for tracking habits, events, or notes
 */
export interface TagData {
  /** Unique identifier for this tag */
  id: string;
  /** Tag name/label */
  tag: string;
  /** Timestamp when tag was added (ISO 8601) */
  timestamp: DateTimeString;
  /** Optional comment/note */
  comment?: string | null;
}

// =============================================================================
// PERSONAL INFO TYPES
// =============================================================================

/**
 * User's personal information
 */
export interface PersonalInfo {
  /** User's unique ID */
  id: string;
  /** Age in years */
  age: number | null;
  /** Weight in kilograms */
  weight: number | null;
  /** Height in meters */
  height: number | null;
  /** Biological sex */
  biological_sex: "male" | "female" | null;
  /** Email address */
  email: string | null;
}

// =============================================================================
// RING CONFIGURATION TYPES
// =============================================================================

/**
 * Ring configuration settings
 */
export interface RingConfiguration {
  /** Ring ID */
  id: string;
  /** Ring color */
  color: string | null;
  /** Ring design */
  design: string | null;
  /** Ring size */
  size: number | null;
  /** Firmware version */
  firmware_version: string | null;
  /** Hardware type */
  hardware_type: string | null;
  /** Setup time (ISO 8601) */
  set_up_at: DateTimeString | null;
}

// =============================================================================
// DAILY SUMMARY TYPES (COMPOSITE)
// =============================================================================

/**
 * Comprehensive daily health summary
 * Combines sleep, readiness, and activity data for a single day
 */
export interface DailySummary {
  /** Date of the summary (YYYY-MM-DD) */
  date: DateString;
  /** Sleep data for this day */
  sleep: DailySleep | null;
  /** Readiness data for this day */
  readiness: DailyReadiness | null;
  /** Activity data for this day */
  activity: DailyActivity | null;
}

// =============================================================================
// TRENDS AND ANALYTICS TYPES
// =============================================================================

/**
 * Trend direction indicator
 */
export type TrendDirection = "improving" | "declining" | "stable";

/**
 * Statistical summary for a metric
 */
export interface MetricStatistics {
  /** Average value */
  average: number;
  /** Minimum value */
  min: number;
  /** Maximum value */
  max: number;
  /** Standard deviation */
  std_dev?: number;
  /** Trend direction */
  trend?: TrendDirection;
  /** Array of daily values */
  daily_values: (number | null)[];
}

/**
 * Weekly trends summary
 */
export interface WeeklyTrends {
  /** Time period (start to end date) */
  period: string;
  /** Readiness trend statistics */
  readiness: MetricStatistics;
  /** Sleep trend statistics */
  sleep: MetricStatistics;
  /** Activity trend statistics */
  activity: MetricStatistics;
  /** Insights and patterns */
  insights: string[];
}

// =============================================================================
// CACHE METADATA TYPES
// =============================================================================

/**
 * Cache metadata for tracking freshness
 */
export interface CacheMetadata {
  /** When the data was cached (ISO 8601) */
  cached_at: DateTimeString;
  /** When the cache expires (ISO 8601) */
  expires_at: DateTimeString;
  /** Whether the cache is stale */
  is_stale: boolean;
  /** Source of the data */
  source: "api" | "cache";
}

// =============================================================================
// TYPE GUARDS
// =============================================================================

/**
 * Type guard to check if a value is a valid DateString
 */
export function isDateString(value: unknown): value is DateString {
  if (typeof value !== "string") return false;
  // Basic YYYY-MM-DD format check
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}

/**
 * Type guard to check if a value is a valid DateTimeString
 */
export function isDateTimeString(value: unknown): value is DateTimeString {
  if (typeof value !== "string") return false;
  // Basic ISO 8601 format check
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value);
}

/**
 * Type guard to check if response has data
 */
export function hasData<T>(
  response: OuraAPIResponse<T> | null | undefined
): response is OuraAPIResponse<T> {
  return response !== null && response !== undefined && Array.isArray(response.data);
}

// =============================================================================
// UTILITY TYPES
// =============================================================================

/**
 * Extract the data type from an OuraAPIResponse
 */
export type ExtractData<T> = T extends OuraAPIResponse<infer U> ? U : never;

/**
 * Make all properties optional (for partial updates)
 */
export type PartialRecord<T> = {
  [P in keyof T]?: T[P];
};

/**
 * Score type (0-100 or null)
 */
export type Score = number | null;

/**
 * Duration in seconds
 */
export type DurationSeconds = number | null;

/**
 * Distance in meters
 */
export type DistanceMeters = number | null;

/**
 * Calories in kcal
 */
export type CaloriesKcal = number | null;

/**
 * Heart rate in beats per minute
 */
export type HeartRateBPM = number | null;

/**
 * HRV in milliseconds
 */
export type HRVMilliseconds = number | null;

/**
 * Temperature deviation in celsius
 */
export type TemperatureCelsius = number | null;
