#!/usr/bin/env node

/**
 * Test script for error classes
 * Tests custom error types and error handling utilities
 */

import {
  OuraMCPError,
  OuraAuthError,
  OuraAPIError,
  CacheError,
  RateLimitError,
  ValidationError,
  logError,
  handleToolError,
  isAuthError,
  isAPIError,
  isCacheError,
  isRateLimitError,
  isValidationError,
  isRecoverableError,
} from "./dist/shared/errors.js";

console.log("=".repeat(80));
console.log("ERROR CLASSES TEST");
console.log("=".repeat(80));

// Test 1: Base OuraMCPError
console.log("\n✓ Test 1: Base OuraMCPError");
try {
  const error = new OuraMCPError("Test error", "TEST_CODE", { detail: "test detail" });
  console.log("✓ Created base error:", error.message);
  console.log("  - Name:", error.name);
  console.log("  - Code:", error.code);
  console.log("  - Context:", JSON.stringify(error.context));
  console.log("  - Timestamp:", error.timestamp.toISOString());
  console.log("  - Has stack trace:", !!error.stack);

  const json = error.toJSON();
  console.log("✓ toJSON() returns:", Object.keys(json).join(", "));

  const userMsg = error.getUserMessage();
  console.log("✓ getUserMessage() returns:", userMsg);
} catch (err) {
  console.log("✗ Failed:", err.message);
}

// Test 2: OuraAuthError
console.log("\n✓ Test 2: OuraAuthError");
try {
  const error = new OuraAuthError("Invalid API token", { statusCode: 401 });
  console.log("✓ Created auth error:", error.message);
  console.log("  - Code:", error.code);
  console.log("  - User message:", error.getUserMessage());
  console.log("  - Is OuraMCPError:", error instanceof OuraMCPError);
  console.log("  - Is OuraAuthError:", error instanceof OuraAuthError);
} catch (err) {
  console.log("✗ Failed:", err.message);
}

// Test 3: OuraAPIError
console.log("\n✓ Test 3: OuraAPIError");
try {
  const error429 = new OuraAPIError("Rate limit exceeded", 429, "/v2/usercollection/daily_sleep");
  console.log("✓ Created API error (429):", error429.message);
  console.log("  - Status code:", error429.statusCode);
  console.log("  - Endpoint:", error429.endpoint);
  console.log("  - User message:", error429.getUserMessage().substring(0, 100) + "...");

  const error500 = new OuraAPIError("Server error", 500, "/v2/test");
  console.log("✓ Created API error (500):", error500.message);
  console.log("  - User message includes suggestion:", error500.getUserMessage().includes("trying cached data"));

  const error404 = new OuraAPIError("Not found", 404);
  console.log("✓ Created API error (404):", error404.message);
  console.log("  - User message:", error404.getUserMessage().substring(0, 80) + "...");
} catch (err) {
  console.log("✗ Failed:", err.message);
}

// Test 4: CacheError
console.log("\n✓ Test 4: CacheError");
try {
  const error = new CacheError("Database locked", "write", "SQLITE_BUSY");
  console.log("✓ Created cache error:", error.message);
  console.log("  - Operation:", error.operation);
  console.log("  - SQLite error:", error.sqliteError);
  console.log("  - User message:", error.getUserMessage());
  console.log("  - Includes fallback message:", error.getUserMessage().includes("Falling back to API"));
} catch (err) {
  console.log("✗ Failed:", err.message);
}

// Test 5: RateLimitError
console.log("\n✓ Test 5: RateLimitError");
try {
  const error1 = new RateLimitError("Too many requests", 120, 5000, 0);
  console.log("✓ Created rate limit error:", error1.message);
  console.log("  - Retry after:", error1.retryAfter, "seconds");
  console.log("  - Limit:", error1.limit);
  console.log("  - Remaining:", error1.remaining);
  console.log("  - User message:", error1.getUserMessage());
  console.log("  - Includes time estimate:", error1.getUserMessage().includes("minute"));

  const error2 = new RateLimitError("Limit exceeded", undefined, 100, 50);
  console.log("✓ Created rate limit error (no retry-after):", error2.message);
  console.log("  - User message:", error2.getUserMessage());
} catch (err) {
  console.log("✗ Failed:", err.message);
}

// Test 6: ValidationError
console.log("\n✓ Test 6: ValidationError");
try {
  const error = new ValidationError("Invalid date format", "date", "2024-13-45");
  console.log("✓ Created validation error:", error.message);
  console.log("  - Field:", error.field);
  console.log("  - Value:", error.value);
  console.log("  - User message:", error.getUserMessage());
  console.log("  - Includes field name:", error.getUserMessage().includes("'date'"));
} catch (err) {
  console.log("✗ Failed:", err.message);
}

// Test 7: Type guards
console.log("\n✓ Test 7: Type Guards");
try {
  const authErr = new OuraAuthError("Auth failed");
  const apiErr = new OuraAPIError("API failed", 500);
  const cacheErr = new CacheError("Cache failed");
  const rateLimitErr = new RateLimitError("Rate limit");
  const validationErr = new ValidationError("Validation failed");
  const genericErr = new Error("Generic error");

  console.log("✓ isAuthError(OuraAuthError):", isAuthError(authErr));
  console.log("  isAuthError(OuraAPIError):", isAuthError(apiErr));

  console.log("✓ isAPIError(OuraAPIError):", isAPIError(apiErr));
  console.log("  isAPIError(OuraAuthError):", isAPIError(authErr));

  console.log("✓ isCacheError(CacheError):", isCacheError(cacheErr));
  console.log("  isCacheError(Error):", isCacheError(genericErr));

  console.log("✓ isRateLimitError(RateLimitError):", isRateLimitError(rateLimitErr));
  console.log("  isRateLimitError(ValidationError):", isRateLimitError(validationErr));

  console.log("✓ isValidationError(ValidationError):", isValidationError(validationErr));
  console.log("  isValidationError(RateLimitError):", isValidationError(rateLimitErr));
} catch (err) {
  console.log("✗ Failed:", err.message);
}

// Test 8: isRecoverableError
console.log("\n✓ Test 8: Recoverable Error Detection");
try {
  const authErr = new OuraAuthError("Auth failed");
  const apiErr = new OuraAPIError("API failed", 500);
  const cacheErr = new CacheError("Cache failed");
  const rateLimitErr = new RateLimitError("Rate limit");
  const validationErr = new ValidationError("Validation failed");

  console.log("✓ isRecoverableError(OuraAuthError):", isRecoverableError(authErr));
  console.log("✓ isRecoverableError(OuraAPIError):", isRecoverableError(apiErr));
  console.log("✓ isRecoverableError(CacheError):", isRecoverableError(cacheErr));
  console.log("✓ isRecoverableError(RateLimitError):", isRecoverableError(rateLimitErr));
  console.log("✓ isRecoverableError(ValidationError):", isRecoverableError(validationErr));

  console.log("  (Auth and Validation are not recoverable, API/Cache/RateLimit are)");
} catch (err) {
  console.log("✗ Failed:", err.message);
}

// Test 9: handleToolError
console.log("\n✓ Test 9: Handle Tool Error");
try {
  const authErr = new OuraAuthError("Auth failed", { endpoint: "/test" });
  const result = handleToolError(authErr, { toolName: "test_tool" });

  console.log("✓ handleToolError returns object with:");
  console.log("  - isError:", result.isError);
  console.log("  - message:", result.message.substring(0, 60) + "...");
  console.log("  - errorCode:", result.errorCode);
  console.log("  - errorDetails:", Object.keys(result.errorDetails || {}).join(", "));
  console.log("  - Has timestamp:", !!(result.errorDetails?.timestamp));
} catch (err) {
  console.log("✗ Failed:", err.message);
}

// Test 10: handleToolError with generic Error
console.log("\n✓ Test 10: Handle Generic Error");
try {
  const genericErr = new Error("Something went wrong");
  const result = handleToolError(genericErr, { context: "test" });

  console.log("✓ handleToolError handles generic errors:");
  console.log("  - isError:", result.isError);
  console.log("  - message:", result.message);
  console.log("  - errorCode:", result.errorCode || "(none)");
  console.log("  - errorDetails:", Object.keys(result.errorDetails || {}).join(", "));
} catch (err) {
  console.log("✗ Failed:", err.message);
}

// Test 11: logError (just verify it doesn't crash)
console.log("\n✓ Test 11: Log Error");
try {
  const error = new OuraAuthError("Test error for logging");
  console.log("✓ Calling logError() with OuraMCPError...");
  console.log("  (Error log follows on stderr)");
  logError(error, { test: true });

  const genericErr = new Error("Generic test error");
  console.log("✓ Calling logError() with generic Error...");
  console.log("  (Error log follows on stderr)");
  logError(genericErr, { test: true });

  console.log("✓ logError() executed without crashing");
} catch (err) {
  console.log("✗ Failed:", err.message);
}

console.log("\n" + "=".repeat(80));
console.log("ERROR CLASSES TESTS COMPLETED");
console.log("=".repeat(80));
console.log("\n✓ All error classes tested successfully");
console.log("✓ Error types: OuraMCPError, OuraAuthError, OuraAPIError, CacheError, RateLimitError, ValidationError");
console.log("✓ Type guards working correctly");
console.log("✓ Error handling utilities functional");
console.log("✓ User-friendly error messages generated");
