import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from "axios";
import { getOAuthClient, OuraOAuthClient } from "./oauth.js";

// =============================================================================
// CONSTANTS
// =============================================================================

const OURA_API_BASE_URL = "https://api.ouraring.com/v2";
const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY = 1000; // 1 second
const DEBUG = process.env.DEBUG_API_CALLS === "true";

// =============================================================================
// TYPES
// =============================================================================

/**
 * Daily sleep data from Oura API
 */
export interface DailySleep {
  id: string;
  day: string; // YYYY-MM-DD
  score: number | null;
  contributors: {
    deep_sleep: number | null;
    efficiency: number | null;
    latency: number | null;
    rem_sleep: number | null;
    restfulness: number | null;
    timing: number | null;
    total_sleep: number | null;
  };
  total_sleep_duration: number | null; // seconds
  time_in_bed: number | null; // seconds
  awake_time: number | null; // seconds
  light_sleep_duration: number | null; // seconds
  deep_sleep_duration: number | null; // seconds
  rem_sleep_duration: number | null; // seconds
  restless_periods: number | null;
  efficiency: number | null; // percentage
  latency: number | null; // seconds
  timing: {
    bedtime_start: string | null; // ISO 8601
    bedtime_end: string | null; // ISO 8601
  };
}

/**
 * Daily readiness data from Oura API
 */
export interface DailyReadiness {
  id: string;
  day: string; // YYYY-MM-DD
  score: number | null;
  contributors: {
    activity_balance: number | null;
    body_temperature: number | null;
    hrv_balance: number | null;
    previous_day_activity: number | null;
    previous_night: number | null;
    recovery_index: number | null;
    resting_heart_rate: number | null;
    sleep_balance: number | null;
  };
  temperature_deviation: number | null;
  temperature_trend_deviation: number | null;
}

/**
 * Daily activity data from Oura API
 */
export interface DailyActivity {
  id: string;
  day: string; // YYYY-MM-DD
  score: number | null;
  active_calories: number | null;
  average_met_minutes: number | null;
  contributors: {
    meet_daily_targets: number | null;
    move_every_hour: number | null;
    recovery_time: number | null;
    stay_active: number | null;
    training_frequency: number | null;
    training_volume: number | null;
  };
  equivalent_walking_distance: number | null; // meters
  high_activity_met_minutes: number | null;
  high_activity_time: number | null; // seconds
  inactivity_alerts: number | null;
  low_activity_met_minutes: number | null;
  low_activity_time: number | null; // seconds
  medium_activity_met_minutes: number | null;
  medium_activity_time: number | null; // seconds
  meters_to_target: number | null;
  non_wear_time: number | null; // seconds
  resting_time: number | null; // seconds
  sedentary_met_minutes: number | null;
  sedentary_time: number | null; // seconds
  steps: number | null;
  target_calories: number | null;
  target_meters: number | null;
  total_calories: number | null;
}

/**
 * Heart rate data from Oura API
 */
export interface HeartRateData {
  bpm: number;
  source: string;
  timestamp: string; // ISO 8601
}

/**
 * Paginated API response wrapper
 */
interface OuraAPIResponse<T> {
  data: T[];
  next_token: string | null;
}

/**
 * API request options
 */
export interface APIRequestOptions {
  startDate?: string; // YYYY-MM-DD
  endDate?: string; // YYYY-MM-DD
  nextToken?: string;
}

/**
 * API error response
 */
interface OuraAPIError {
  detail?: string;
  message?: string;
}

// =============================================================================
// OURA API CLIENT
// =============================================================================

/**
 * Client for interacting with the Oura Ring API
 * Provides typed methods for fetching health metrics
 */
export class OuraAPIClient {
  private oauthClient: OuraOAuthClient;
  private axiosInstance: AxiosInstance;

  constructor(oauthClient?: OuraOAuthClient) {
    this.oauthClient = oauthClient || getOAuthClient();

    // Create axios instance with base configuration
    this.axiosInstance = axios.create({
      baseURL: OURA_API_BASE_URL,
      timeout: 30000, // 30 seconds
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Add request interceptor for authentication
    this.axiosInstance.interceptors.request.use(
      async (config) => {
        const accessToken = await this.oauthClient.getValidAccessToken();
        config.headers.Authorization = `Bearer ${accessToken}`;

        if (DEBUG) {
          console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
          if (config.params) {
            console.log(`[API] Query params:`, config.params);
          }
        }

        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Add response interceptor for logging
    this.axiosInstance.interceptors.response.use(
      (response) => {
        if (DEBUG) {
          console.log(
            `[API] Response ${response.status} from ${response.config.url}`
          );
          console.log(
            `[API] Data items:`,
            Array.isArray(response.data?.data)
              ? response.data.data.length
              : "N/A"
          );
        }
        return response;
      },
      (error) => {
        if (DEBUG && error.response) {
          console.error(
            `[API] Error ${error.response.status} from ${error.config?.url}`
          );
          console.error(`[API] Error details:`, error.response.data);
        }
        return Promise.reject(error);
      }
    );
  }

  // ===========================================================================
  // REQUEST METHODS WITH RETRY LOGIC
  // ===========================================================================

  /**
   * Makes an API request with exponential backoff retry logic
   */
  private async requestWithRetry<T>(
    config: AxiosRequestConfig,
    retries: number = MAX_RETRIES
  ): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await this.axiosInstance.request<T>(config);
        return response.data;
      } catch (error) {
        lastError = this.handleAPIError(error);

        // Don't retry on certain errors
        if (this.shouldNotRetry(error)) {
          throw lastError;
        }

        // Calculate delay with exponential backoff
        if (attempt < retries) {
          const delay = INITIAL_RETRY_DELAY * Math.pow(2, attempt);
          const jitter = Math.random() * 1000; // Add jitter to prevent thundering herd

          if (DEBUG) {
            console.log(
              `[API] Retry attempt ${attempt + 1}/${retries} after ${Math.round(delay + jitter)}ms`
            );
          }

          await this.sleep(delay + jitter);
        }
      }
    }

    throw lastError || new Error("API request failed after retries");
  }

  /**
   * Determines if an error should not be retried
   */
  private shouldNotRetry(error: unknown): boolean {
    if (!axios.isAxiosError(error)) {
      return true;
    }

    const status = error.response?.status;

    // Don't retry on client errors (except 429 Too Many Requests)
    if (status && status >= 400 && status < 500 && status !== 429) {
      return true;
    }

    // Don't retry on authentication errors
    if (status === 401 || status === 403) {
      return true;
    }

    return false;
  }

  /**
   * Sleep helper for retry delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // ===========================================================================
  // API ENDPOINTS
  // ===========================================================================

  /**
   * Fetches daily sleep data for a given date range
   * @param options - Optional date range and pagination parameters
   * @returns Array of daily sleep records
   */
  public async getDailySleep(
    options: APIRequestOptions = {}
  ): Promise<DailySleep[]> {
    const params: Record<string, string> = {};

    if (options.startDate) params.start_date = options.startDate;
    if (options.endDate) params.end_date = options.endDate;
    if (options.nextToken) params.next_token = options.nextToken;

    const response = await this.requestWithRetry<OuraAPIResponse<DailySleep>>({
      method: "GET",
      url: "/usercollection/daily_sleep",
      params,
    });

    // Handle pagination if next_token is present
    if (response.next_token) {
      const nextPage = await this.getDailySleep({
        ...options,
        nextToken: response.next_token,
      });
      return [...response.data, ...nextPage];
    }

    return response.data;
  }

  /**
   * Fetches daily readiness data for a given date range
   * @param options - Optional date range and pagination parameters
   * @returns Array of daily readiness records
   */
  public async getDailyReadiness(
    options: APIRequestOptions = {}
  ): Promise<DailyReadiness[]> {
    const params: Record<string, string> = {};

    if (options.startDate) params.start_date = options.startDate;
    if (options.endDate) params.end_date = options.endDate;
    if (options.nextToken) params.next_token = options.nextToken;

    const response = await this.requestWithRetry<
      OuraAPIResponse<DailyReadiness>
    >({
      method: "GET",
      url: "/usercollection/daily_readiness",
      params,
    });

    // Handle pagination if next_token is present
    if (response.next_token) {
      const nextPage = await this.getDailyReadiness({
        ...options,
        nextToken: response.next_token,
      });
      return [...response.data, ...nextPage];
    }

    return response.data;
  }

  /**
   * Fetches daily activity data for a given date range
   * @param options - Optional date range and pagination parameters
   * @returns Array of daily activity records
   */
  public async getDailyActivity(
    options: APIRequestOptions = {}
  ): Promise<DailyActivity[]> {
    const params: Record<string, string> = {};

    if (options.startDate) params.start_date = options.startDate;
    if (options.endDate) params.end_date = options.endDate;
    if (options.nextToken) params.next_token = options.nextToken;

    const response = await this.requestWithRetry<
      OuraAPIResponse<DailyActivity>
    >({
      method: "GET",
      url: "/usercollection/daily_activity",
      params,
    });

    // Handle pagination if next_token is present
    if (response.next_token) {
      const nextPage = await this.getDailyActivity({
        ...options,
        nextToken: response.next_token,
      });
      return [...response.data, ...nextPage];
    }

    return response.data;
  }

  /**
   * Fetches heart rate data for a given date range
   * @param options - Optional date range and pagination parameters
   * @returns Array of heart rate data points
   */
  public async getHeartRate(
    options: APIRequestOptions = {}
  ): Promise<HeartRateData[]> {
    const params: Record<string, string> = {};

    if (options.startDate) params.start_date = options.startDate;
    if (options.endDate) params.end_date = options.endDate;
    if (options.nextToken) params.next_token = options.nextToken;

    const response = await this.requestWithRetry<
      OuraAPIResponse<HeartRateData>
    >({
      method: "GET",
      url: "/usercollection/heartrate",
      params,
    });

    // Handle pagination if next_token is present
    if (response.next_token) {
      const nextPage = await this.getHeartRate({
        ...options,
        nextToken: response.next_token,
      });
      return [...response.data, ...nextPage];
    }

    return response.data;
  }

  // ===========================================================================
  // CONVENIENCE METHODS
  // ===========================================================================

  /**
   * Fetches sleep data for a specific date
   * @param date - Date in YYYY-MM-DD format
   * @returns Sleep data for the specified date, or null if not found
   */
  public async getSleepForDate(date: string): Promise<DailySleep | null> {
    const data = await this.getDailySleep({
      startDate: date,
      endDate: date,
    });
    return data.length > 0 ? data[0] : null;
  }

  /**
   * Fetches readiness data for a specific date
   * @param date - Date in YYYY-MM-DD format
   * @returns Readiness data for the specified date, or null if not found
   */
  public async getReadinessForDate(
    date: string
  ): Promise<DailyReadiness | null> {
    const data = await this.getDailyReadiness({
      startDate: date,
      endDate: date,
    });
    return data.length > 0 ? data[0] : null;
  }

  /**
   * Fetches activity data for a specific date
   * @param date - Date in YYYY-MM-DD format
   * @returns Activity data for the specified date, or null if not found
   */
  public async getActivityForDate(date: string): Promise<DailyActivity | null> {
    const data = await this.getDailyActivity({
      startDate: date,
      endDate: date,
    });
    return data.length > 0 ? data[0] : null;
  }

  /**
   * Fetches sleep data for the last N days
   * @param days - Number of days to fetch (default: 7)
   * @returns Array of sleep data for the last N days
   */
  public async getRecentSleep(days: number = 7): Promise<DailySleep[]> {
    const endDate = this.formatDate(new Date());
    const startDate = this.formatDate(
      new Date(Date.now() - days * 24 * 60 * 60 * 1000)
    );

    return this.getDailySleep({ startDate, endDate });
  }

  /**
   * Fetches readiness data for the last N days
   * @param days - Number of days to fetch (default: 7)
   * @returns Array of readiness data for the last N days
   */
  public async getRecentReadiness(days: number = 7): Promise<DailyReadiness[]> {
    const endDate = this.formatDate(new Date());
    const startDate = this.formatDate(
      new Date(Date.now() - days * 24 * 60 * 60 * 1000)
    );

    return this.getDailyReadiness({ startDate, endDate });
  }

  /**
   * Fetches activity data for the last N days
   * @param days - Number of days to fetch (default: 7)
   * @returns Array of activity data for the last N days
   */
  public async getRecentActivity(days: number = 7): Promise<DailyActivity[]> {
    const endDate = this.formatDate(new Date());
    const startDate = this.formatDate(
      new Date(Date.now() - days * 24 * 60 * 60 * 1000)
    );

    return this.getDailyActivity({ startDate, endDate });
  }

  // ===========================================================================
  // HELPER METHODS
  // ===========================================================================

  /**
   * Formats a Date object to YYYY-MM-DD string
   */
  private formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  // ===========================================================================
  // ERROR HANDLING
  // ===========================================================================

  /**
   * Handles API errors and provides helpful error messages
   */
  private handleAPIError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<OuraAPIError>;

      // Handle specific HTTP status codes
      if (axiosError.response?.status === 401) {
        return new Error(
          "Authentication failed. Please check your access token or re-authenticate."
        );
      }

      if (axiosError.response?.status === 403) {
        return new Error(
          "Access forbidden. Please check your API scopes and permissions."
        );
      }

      if (axiosError.response?.status === 429) {
        const retryAfter = axiosError.response.headers["retry-after"];
        return new Error(
          `Rate limit exceeded. ${retryAfter ? `Retry after ${retryAfter} seconds.` : "Please try again later."}`
        );
      }

      if (axiosError.response?.status === 404) {
        return new Error(
          "Resource not found. The requested data may not be available."
        );
      }

      if (axiosError.response?.status && axiosError.response.status >= 500) {
        return new Error(
          `Oura API server error (${axiosError.response.status}). Please try again later.`
        );
      }

      // Extract error message from response
      if (axiosError.response?.data) {
        const apiError = axiosError.response.data;
        const errorMessage = apiError.detail || apiError.message;
        if (errorMessage) {
          return new Error(`Oura API error: ${errorMessage}`);
        }
      }

      // Generic HTTP error
      return new Error(
        `HTTP ${axiosError.response?.status || "error"}: ${axiosError.message}`
      );
    }

    // Network or other errors
    if (error instanceof Error) {
      return new Error(`API request failed: ${error.message}`);
    }

    return new Error(`Unknown API error: ${String(error)}`);
  }
}

// =============================================================================
// FACTORY FUNCTION
// =============================================================================

/**
 * Creates and returns a singleton instance of the API client
 */
let apiClientInstance: OuraAPIClient | null = null;

export function getAPIClient(oauthClient?: OuraOAuthClient): OuraAPIClient {
  if (!apiClientInstance) {
    apiClientInstance = new OuraAPIClient(oauthClient);
  }
  return apiClientInstance;
}
