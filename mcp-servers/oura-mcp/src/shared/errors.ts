// =============================================================================
// CUSTOM ERROR TYPES
// Typed error system for different failure modes in oura-mcp
// =============================================================================

/**
 * Base error class for all oura-mcp errors
 * Extends Error with additional context properties
 */
export class OuraMCPError extends Error {
  public readonly code: string;
  public readonly context?: Record<string, any>;
  public readonly timestamp: Date;

  constructor(
    message: string,
    code: string,
    context?: Record<string, any>
  ) {
    super(message);
    this.name = this.constructor.name;
    this.code = code;
    this.context = context;
    this.timestamp = new Date();

    // Maintain proper stack trace for where error was thrown (Node.js only)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }

  /**
   * Convert error to JSON for logging
   */
  toJSON(): Record<string, any> {
    return {
      name: this.name,
      message: this.message,
      code: this.code,
      context: this.context,
      timestamp: this.timestamp.toISOString(),
      stack: this.stack,
    };
  }

  /**
   * Get user-friendly error message for LLM consumption
   */
  getUserMessage(): string {
    return this.message;
  }
}

// =============================================================================
// AUTHENTICATION ERRORS
// =============================================================================

/**
 * OuraAuthError - Authentication and authorization failures
 *
 * Common causes:
 * - Missing or invalid API token
 * - Expired OAuth token
 * - Insufficient permissions
 */
export class OuraAuthError extends OuraMCPError {
  constructor(message: string, context?: Record<string, any>) {
    super(message, "OURA_AUTH_ERROR", context);
  }

  getUserMessage(): string {
    return (
      `Authentication failed with Oura API: ${this.message}. ` +
      "Please check your OURA_API_KEY environment variable or OAuth token."
    );
  }
}

// =============================================================================
// API ERRORS
// =============================================================================

/**
 * OuraAPIError - General Oura API failures
 *
 * Common causes:
 * - API server down or unavailable
 * - Malformed request
 * - Network connectivity issues
 * - Invalid date ranges
 */
export class OuraAPIError extends OuraMCPError {
  public readonly statusCode?: number;
  public readonly endpoint?: string;

  constructor(
    message: string,
    statusCode?: number,
    endpoint?: string,
    context?: Record<string, any>
  ) {
    super(message, "OURA_API_ERROR", {
      statusCode,
      endpoint,
      ...context,
    });
    this.statusCode = statusCode;
    this.endpoint = endpoint;
  }

  getUserMessage(): string {
    let msg = `Oura API request failed: ${this.message}`;

    if (this.statusCode) {
      msg += ` (HTTP ${this.statusCode})`;
    }

    if (this.endpoint) {
      msg += `. Endpoint: ${this.endpoint}`;
    }

    // Add helpful suggestions based on status code
    if (this.statusCode === 429) {
      msg += ". Rate limit exceeded - please try again in a few minutes.";
    } else if (this.statusCode === 404) {
      msg += ". The requested data may not exist or the date may be invalid.";
    } else if (this.statusCode && this.statusCode >= 500) {
      msg += ". Oura API servers may be experiencing issues - trying cached data.";
    }

    return msg;
  }
}

// =============================================================================
// CACHE ERRORS
// =============================================================================

/**
 * CacheError - SQLite cache operation failures
 *
 * Common causes:
 * - Database file corruption
 * - Disk space issues
 * - Permission problems
 * - Schema migration failures
 */
export class CacheError extends OuraMCPError {
  public readonly operation?: string;
  public readonly sqliteError?: string;

  constructor(
    message: string,
    operation?: string,
    sqliteError?: string,
    context?: Record<string, any>
  ) {
    super(message, "CACHE_ERROR", {
      operation,
      sqliteError,
      ...context,
    });
    this.operation = operation;
    this.sqliteError = sqliteError;
  }

  getUserMessage(): string {
    let msg = `Cache operation failed: ${this.message}`;

    if (this.operation) {
      msg += ` during ${this.operation}`;
    }

    msg += ". Falling back to API for fresh data.";

    return msg;
  }
}

// =============================================================================
// RATE LIMIT ERRORS
// =============================================================================

/**
 * RateLimitError - Rate limit exceeded
 *
 * Common causes:
 * - Too many API requests in short time window
 * - Concurrent requests exceeding limit
 * - Oura API rate limits enforced
 */
export class RateLimitError extends OuraMCPError {
  public readonly retryAfter?: number; // Seconds until rate limit resets
  public readonly limit?: number;
  public readonly remaining?: number;

  constructor(
    message: string,
    retryAfter?: number,
    limit?: number,
    remaining?: number,
    context?: Record<string, any>
  ) {
    super(message, "RATE_LIMIT_ERROR", {
      retryAfter,
      limit,
      remaining,
      ...context,
    });
    this.retryAfter = retryAfter;
    this.limit = limit;
    this.remaining = remaining;
  }

  getUserMessage(): string {
    let msg = `Rate limit exceeded: ${this.message}`;

    if (this.retryAfter) {
      const minutes = Math.ceil(this.retryAfter / 60);
      msg += `. Please try again in ${minutes} minute${minutes !== 1 ? "s" : ""}.`;
    } else {
      msg += ". Please try again in a few minutes.";
    }

    if (this.remaining !== undefined && this.limit !== undefined) {
      msg += ` (${this.remaining}/${this.limit} requests remaining)`;
    }

    return msg;
  }
}

// =============================================================================
// DATA VALIDATION ERRORS
// =============================================================================

/**
 * ValidationError - Data validation failures
 *
 * Common causes:
 * - Invalid date format
 * - Out of range values
 * - Schema validation failures
 * - Unexpected data structure from API
 */
export class ValidationError extends OuraMCPError {
  public readonly field?: string;
  public readonly value?: any;

  constructor(
    message: string,
    field?: string,
    value?: any,
    context?: Record<string, any>
  ) {
    super(message, "VALIDATION_ERROR", {
      field,
      value,
      ...context,
    });
    this.field = field;
    this.value = value;
  }

  getUserMessage(): string {
    let msg = `Validation failed: ${this.message}`;

    if (this.field) {
      msg += ` for field '${this.field}'`;
    }

    return msg + ". Please check your input parameters.";
  }
}

// =============================================================================
// ERROR LOGGING UTILITY
// =============================================================================

/**
 * Log error to stderr with contextual information
 * Does not interfere with stdio transport for MCP communication
 */
export function logError(error: Error | OuraMCPError, additionalContext?: Record<string, any>): void {
  const timestamp = new Date().toISOString();

  if (error instanceof OuraMCPError) {
    console.error(`[${timestamp}] ${error.name}:`, {
      message: error.message,
      code: error.code,
      context: {
        ...error.context,
        ...additionalContext,
      },
      stack: error.stack,
    });
  } else {
    console.error(`[${timestamp}] Error:`, {
      name: error.name,
      message: error.message,
      context: additionalContext,
      stack: error.stack,
    });
  }
}

// =============================================================================
// ERROR HANDLER FOR MCP TOOLS
// =============================================================================

/**
 * Convert any error to user-friendly MCP error response
 *
 * @param error - The error to convert
 * @param additionalContext - Additional context to include
 * @returns Object with isError flag, user message, and error details
 */
export function handleToolError(
  error: Error | OuraMCPError,
  additionalContext?: Record<string, any>
): {
  isError: true;
  message: string;
  errorCode?: string;
  errorDetails?: Record<string, any>;
} {
  // Log error for debugging
  logError(error, additionalContext);

  // Convert to user-friendly message
  if (error instanceof OuraMCPError) {
    return {
      isError: true,
      message: error.getUserMessage(),
      errorCode: error.code,
      errorDetails: {
        ...error.context,
        ...additionalContext,
        timestamp: error.timestamp.toISOString(),
      },
    };
  }

  // Generic error handling
  return {
    isError: true,
    message: `An unexpected error occurred: ${error.message}`,
    errorDetails: {
      name: error.name,
      ...additionalContext,
      timestamp: new Date().toISOString(),
    },
  };
}

// =============================================================================
// ERROR TYPE GUARDS
// =============================================================================

/**
 * Check if error is an authentication error
 */
export function isAuthError(error: any): error is OuraAuthError {
  return error instanceof OuraAuthError;
}

/**
 * Check if error is an API error
 */
export function isAPIError(error: any): error is OuraAPIError {
  return error instanceof OuraAPIError;
}

/**
 * Check if error is a cache error
 */
export function isCacheError(error: any): error is CacheError {
  return error instanceof CacheError;
}

/**
 * Check if error is a rate limit error
 */
export function isRateLimitError(error: any): error is RateLimitError {
  return error instanceof RateLimitError;
}

/**
 * Check if error is a validation error
 */
export function isValidationError(error: any): error is ValidationError {
  return error instanceof ValidationError;
}

/**
 * Check if error is recoverable (can retry or use fallback)
 */
export function isRecoverableError(error: any): boolean {
  return (
    isAPIError(error) ||
    isCacheError(error) ||
    isRateLimitError(error)
  );
}
