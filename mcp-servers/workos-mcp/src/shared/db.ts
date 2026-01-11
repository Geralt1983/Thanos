import { neon } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-http";
import * as schema from "../schema.js";
import type { Database } from "./types.js";

// =============================================================================
// DATABASE CONNECTION
// =============================================================================

/**
 * Creates and returns a configured database connection instance
 * Uses WORKOS_DATABASE_URL or DATABASE_URL environment variable for connection
 * @returns Configured Drizzle database instance with schema
 * @throws Error if neither WORKOS_DATABASE_URL nor DATABASE_URL is set
 */
export function getDb(): Database {
  const url = process.env.WORKOS_DATABASE_URL || process.env.DATABASE_URL;
  if (!url) {
    throw new Error("WORKOS_DATABASE_URL or DATABASE_URL environment variable required");
  }
  const sql = neon(url);
  return drizzle(sql, { schema });
}
