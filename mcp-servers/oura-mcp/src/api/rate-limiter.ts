import fs from "fs";
import path from "path";
import os from "os";

// =============================================================================
// CONSTANTS
// =============================================================================

const DEFAULT_MAX_REQUESTS = 5000; // Oura API limit: 5000 requests/day
const DEFAULT_WINDOW_MS = 24 * 60 * 60 * 1000; // 24 hours
const RATE_LIMIT_STORAGE_PATH = path.join(
  os.homedir(),
  ".oura-cache",
  "rate-limit.json"
);

// =============================================================================
// TYPES
// =============================================================================

/**
 * Rate limit configuration options
 */
export interface RateLimitConfig {
  maxRequests?: number;
  windowMs?: number;
  storagePath?: string;
}

/**
 * Request record for tracking
 */
interface RequestRecord {
  timestamp: number;
  endpoint: string;
}

/**
 * Rate limit statistics
 */
export interface RateLimitStats {
  requestsInWindow: number;
  remainingRequests: number;
  maxRequests: number;
  windowStartTime: number;
  windowEndTime: number;
  oldestRequestTime: number | null;
  newestRequestTime: number | null;
  percentageUsed: number;
}

/**
 * Stored rate limit data
 */
interface StoredRateLimitData {
  requests: RequestRecord[];
  lastResetTime: number;
}

/**
 * Queued request
 */
interface QueuedRequest<T> {
  execute: () => Promise<T>;
  resolve: (value: T) => void;
  reject: (error: Error) => void;
  endpoint: string;
}

// =============================================================================
// RATE LIMITER CLASS
// =============================================================================

/**
 * Rate limiter for Oura API requests
 * Implements sliding window rate limiting with persistence
 */
export class RateLimiter {
  private maxRequests: number;
  private windowMs: number;
  private storagePath: string;
  private requests: RequestRecord[];
  private lastResetTime: number;
  private requestQueue: QueuedRequest<any>[];
  private isProcessingQueue: boolean;
  private minRequestInterval: number = 100; // Minimum 100ms between requests

  constructor(config: RateLimitConfig = {}) {
    this.maxRequests =
      config.maxRequests ||
      parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || String(DEFAULT_MAX_REQUESTS));
    this.windowMs =
      config.windowMs ||
      parseInt(process.env.RATE_LIMIT_WINDOW || String(DEFAULT_WINDOW_MS));
    this.storagePath = config.storagePath || RATE_LIMIT_STORAGE_PATH;
    this.requestQueue = [];
    this.isProcessingQueue = false;

    // Load existing rate limit data from storage
    const storedData = this.loadFromStorage();
    this.requests = storedData.requests;
    this.lastResetTime = storedData.lastResetTime;

    // Clean up old requests on initialization
    this.cleanupOldRequests();
  }

  // ===========================================================================
  // RATE LIMITING LOGIC
  // ===========================================================================

  /**
   * Checks if a request can be made within the rate limit
   */
  public canMakeRequest(): boolean {
    this.cleanupOldRequests();
    return this.requests.length < this.maxRequests;
  }

  /**
   * Records a request and checks if it's within the rate limit
   * @param endpoint - The API endpoint being called
   * @throws Error if rate limit is exceeded
   */
  public async recordRequest(endpoint: string): Promise<void> {
    this.cleanupOldRequests();

    if (!this.canMakeRequest()) {
      const stats = this.getStats();
      const timeUntilReset = stats.windowEndTime - Date.now();
      const minutesUntilReset = Math.ceil(timeUntilReset / 60000);

      throw new Error(
        `Rate limit exceeded: ${this.requests.length}/${this.maxRequests} requests used. ` +
          `Limit will reset in ${minutesUntilReset} minutes.`
      );
    }

    // Record the request
    const record: RequestRecord = {
      timestamp: Date.now(),
      endpoint,
    };

    this.requests.push(record);
    this.saveToStorage();
  }

  /**
   * Wraps a request function with rate limiting and queuing
   * @param endpoint - The API endpoint being called
   * @param requestFn - The function to execute
   * @returns Promise that resolves with the request result
   */
  public async executeWithRateLimit<T>(
    endpoint: string,
    requestFn: () => Promise<T>
  ): Promise<T> {
    // Check if we can make the request immediately
    if (this.canMakeRequest()) {
      await this.recordRequest(endpoint);
      return requestFn();
    }

    // Queue the request if rate limit is reached
    return this.queueRequest(endpoint, requestFn);
  }

  /**
   * Removes requests outside the current time window
   */
  private cleanupOldRequests(): void {
    const cutoffTime = Date.now() - this.windowMs;
    const initialCount = this.requests.length;

    this.requests = this.requests.filter((req) => req.timestamp > cutoffTime);

    // Save if any requests were removed
    if (this.requests.length !== initialCount) {
      this.saveToStorage();
    }
  }

  /**
   * Waits for the specified duration
   */
  private async sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // ===========================================================================
  // REQUEST QUEUE MANAGEMENT
  // ===========================================================================

  /**
   * Queues a request to be executed when rate limit allows
   */
  private queueRequest<T>(
    endpoint: string,
    requestFn: () => Promise<T>
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      this.requestQueue.push({
        execute: requestFn,
        resolve,
        reject,
        endpoint,
      });

      // Start processing the queue if not already processing
      if (!this.isProcessingQueue) {
        this.processQueue();
      }
    });
  }

  /**
   * Processes queued requests when rate limit allows
   */
  private async processQueue(): Promise<void> {
    if (this.isProcessingQueue) return;

    this.isProcessingQueue = true;

    while (this.requestQueue.length > 0) {
      // Wait until we can make a request
      while (!this.canMakeRequest()) {
        const stats = this.getStats();
        const timeUntilOldestExpires =
          stats.oldestRequestTime !== null
            ? stats.oldestRequestTime + this.windowMs - Date.now()
            : 1000;

        // Wait at least 1 second or until the oldest request expires
        const waitTime = Math.max(1000, Math.min(timeUntilOldestExpires, 60000));
        await this.sleep(waitTime);
        this.cleanupOldRequests();
      }

      // Get the next request from the queue
      const queuedRequest = this.requestQueue.shift();
      if (!queuedRequest) break;

      try {
        // Record the request and execute it
        await this.recordRequest(queuedRequest.endpoint);

        // Add small delay between requests to avoid overwhelming the API
        await this.sleep(this.minRequestInterval);

        const result = await queuedRequest.execute();
        queuedRequest.resolve(result);
      } catch (error) {
        queuedRequest.reject(
          error instanceof Error ? error : new Error(String(error))
        );
      }
    }

    this.isProcessingQueue = false;
  }

  /**
   * Returns the number of queued requests
   */
  public getQueueLength(): number {
    return this.requestQueue.length;
  }

  /**
   * Clears all queued requests
   */
  public clearQueue(): void {
    // Reject all queued requests
    while (this.requestQueue.length > 0) {
      const request = this.requestQueue.shift();
      if (request) {
        request.reject(new Error("Request queue cleared"));
      }
    }
  }

  // ===========================================================================
  // EXPONENTIAL BACKOFF FOR 429 RESPONSES
  // ===========================================================================

  /**
   * Handles 429 (Too Many Requests) response with exponential backoff
   * @param retryAfter - Retry-After header value in seconds (if provided by API)
   * @param attemptNumber - Current retry attempt number (for exponential backoff)
   * @returns Wait time in milliseconds
   */
  public static calculateBackoff(
    retryAfter?: number,
    attemptNumber: number = 0
  ): number {
    // If Retry-After header is provided, use it
    if (retryAfter && retryAfter > 0) {
      return retryAfter * 1000; // Convert to milliseconds
    }

    // Otherwise, use exponential backoff: 2^attempt * 1000ms
    // Capped at 5 minutes (300000ms)
    const backoff = Math.pow(2, attemptNumber) * 1000;
    return Math.min(backoff, 300000);
  }

  /**
   * Waits for the appropriate backoff period after a 429 response
   */
  public async handleRateLimitResponse(
    retryAfter?: number,
    attemptNumber: number = 0
  ): Promise<void> {
    const backoffMs = RateLimiter.calculateBackoff(retryAfter, attemptNumber);
    const backoffSeconds = Math.round(backoffMs / 1000);

    console.warn(
      `Rate limit hit (429). Waiting ${backoffSeconds} seconds before retry...`
    );

    await this.sleep(backoffMs);
  }

  // ===========================================================================
  // STATISTICS
  // ===========================================================================

  /**
   * Returns current rate limit statistics
   */
  public getStats(): RateLimitStats {
    this.cleanupOldRequests();

    const now = Date.now();
    const windowStartTime = now - this.windowMs;
    const requestsInWindow = this.requests.length;
    const remainingRequests = Math.max(0, this.maxRequests - requestsInWindow);
    const percentageUsed =
      this.maxRequests > 0 ? (requestsInWindow / this.maxRequests) * 100 : 0;

    const timestamps = this.requests.map((r) => r.timestamp).sort();
    const oldestRequestTime = timestamps.length > 0 ? timestamps[0] : null;
    const newestRequestTime =
      timestamps.length > 0 ? timestamps[timestamps.length - 1] : null;

    return {
      requestsInWindow,
      remainingRequests,
      maxRequests: this.maxRequests,
      windowStartTime,
      windowEndTime: now,
      oldestRequestTime,
      newestRequestTime,
      percentageUsed,
    };
  }

  /**
   * Returns a human-readable summary of rate limit status
   */
  public getStatusSummary(): string {
    const stats = this.getStats();
    const queueLength = this.getQueueLength();

    let summary = `Rate Limit Status:\n`;
    summary += `- Requests used: ${stats.requestsInWindow}/${stats.maxRequests} (${stats.percentageUsed.toFixed(1)}%)\n`;
    summary += `- Remaining: ${stats.remainingRequests} requests\n`;

    if (stats.oldestRequestTime) {
      const timeUntilReset = stats.oldestRequestTime + this.windowMs - Date.now();
      const hoursUntilReset = Math.floor(timeUntilReset / 3600000);
      const minutesUntilReset = Math.floor((timeUntilReset % 3600000) / 60000);
      summary += `- Next reset: in ${hoursUntilReset}h ${minutesUntilReset}m\n`;
    }

    if (queueLength > 0) {
      summary += `- Queued requests: ${queueLength}\n`;
    }

    return summary;
  }

  /**
   * Resets the rate limiter (for testing purposes)
   */
  public reset(): void {
    this.requests = [];
    this.lastResetTime = Date.now();
    this.clearQueue();
    this.saveToStorage();
  }

  // ===========================================================================
  // PERSISTENCE
  // ===========================================================================

  /**
   * Loads rate limit data from storage
   */
  private loadFromStorage(): StoredRateLimitData {
    try {
      if (fs.existsSync(this.storagePath)) {
        const data = fs.readFileSync(this.storagePath, "utf-8");
        const parsed = JSON.parse(data) as StoredRateLimitData;

        // Validate the data structure
        if (Array.isArray(parsed.requests) && typeof parsed.lastResetTime === "number") {
          return parsed;
        }
      }
    } catch (error) {
      console.warn("Failed to load rate limit data from storage:", error);
    }

    // Return default data if loading fails
    return {
      requests: [],
      lastResetTime: Date.now(),
    };
  }

  /**
   * Saves rate limit data to storage
   */
  private saveToStorage(): void {
    try {
      const dir = path.dirname(this.storagePath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }

      const data: StoredRateLimitData = {
        requests: this.requests,
        lastResetTime: this.lastResetTime,
      };

      fs.writeFileSync(this.storagePath, JSON.stringify(data, null, 2), "utf-8");
    } catch (error) {
      console.warn("Failed to save rate limit data to storage:", error);
    }
  }
}

// =============================================================================
// FACTORY FUNCTION
// =============================================================================

/**
 * Singleton instance of the rate limiter
 */
let rateLimiterInstance: RateLimiter | null = null;

/**
 * Gets or creates the singleton rate limiter instance
 */
export function getRateLimiter(config?: RateLimitConfig): RateLimiter {
  if (!rateLimiterInstance) {
    rateLimiterInstance = new RateLimiter(config);
  }
  return rateLimiterInstance;
}
