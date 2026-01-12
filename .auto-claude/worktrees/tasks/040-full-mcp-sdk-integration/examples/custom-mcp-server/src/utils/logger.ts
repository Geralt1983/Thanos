/**
 * Logging utilities
 *
 * Important: All logs must go to stderr, not stdout
 * Stdout is reserved for MCP protocol messages
 */

const DEBUG = process.env.DEBUG === "true";

export const logger = {
  debug(...args: unknown[]) {
    if (DEBUG) {
      console.error("[DEBUG]", new Date().toISOString(), ...args);
    }
  },

  info(...args: unknown[]) {
    console.error("[INFO]", new Date().toISOString(), ...args);
  },

  warn(...args: unknown[]) {
    console.error("[WARN]", new Date().toISOString(), ...args);
  },

  error(...args: unknown[]) {
    console.error("[ERROR]", new Date().toISOString(), ...args);
  },
};
