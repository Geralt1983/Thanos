/**
 * Validation utilities
 */

/**
 * Check if write operations are allowed
 * @throws Error if write access is not enabled
 */
export function requireWriteAccess(): void {
  const writeEnabled = process.env.ALLOW_WRITE === "true";
  if (!writeEnabled) {
    throw new Error(
      "Write access not enabled. Set ALLOW_WRITE=true environment variable to enable create/update/delete operations."
    );
  }
}

/**
 * Sanitize string input to prevent injection attacks
 */
export function sanitizeString(input: string): string {
  // Remove control characters
  return input.replace(/[\x00-\x1F\x7F]/g, "");
}

/**
 * Validate that a value is within allowed range
 */
export function validateRange(
  value: number,
  min: number,
  max: number,
  fieldName: string
): void {
  if (value < min || value > max) {
    throw new Error(
      `${fieldName} must be between ${min} and ${max}, got ${value}`
    );
  }
}
