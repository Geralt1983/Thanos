// =============================================================================
// ENERGY DOMAIN VALIDATION SCHEMAS
// =============================================================================
// This file provides comprehensive Zod validation schemas for all energy-related
// MCP tool inputs. These schemas enforce input bounds to prevent:
// - Resource exhaustion from unbounded inputs
// - Database query overload
// - Injection attempts
// - Memory issues
//
// Each schema validates all required and optional fields with appropriate bounds
// as defined in validation-constants.ts
// =============================================================================

import { z } from "zod";
import {
  energyLevelSchema,
  energyNoteSchema,
  ouraReadinessSchema,
  ouraHrvSchema,
  ouraSleepSchema,
  queryLimitSchema,
} from "../../shared/validation-schemas.js";

// =============================================================================
// TOOL INPUT SCHEMAS
// =============================================================================

/**
 * Schema for workos_log_energy tool
 * Validates energy state logging with optional Oura Ring biometric data
 *
 * @property level - Required energy level (high, medium, low)
 * @property note - Optional note about energy state (0-500 chars)
 * @property ouraReadiness - Optional Oura readiness score (0-100)
 * @property ouraHrv - Optional Oura HRV in milliseconds (0-300)
 * @property ouraSleep - Optional Oura sleep score (0-100)
 */
export const LogEnergySchema = z.object({
  level: energyLevelSchema,
  note: energyNoteSchema.optional(),
  ouraReadiness: ouraReadinessSchema.optional(),
  ouraHrv: ouraHrvSchema.optional(),
  ouraSleep: ouraSleepSchema.optional(),
});

/**
 * Schema for workos_get_energy tool
 * Validates energy state query parameters
 *
 * @property limit - Optional result limit (1-100, default: 5)
 */
export const GetEnergySchema = z.object({
  limit: queryLimitSchema.optional(),
});

// =============================================================================
// SCHEMA EXPORT MAP
// =============================================================================

/**
 * Map of tool names to their validation schemas
 * Used for centralized validation in the energy domain handler router
 *
 * @example
 * const schema = ENERGY_SCHEMAS['workos_log_energy'];
 * const result = validateToolInput(schema, args);
 */
export const ENERGY_SCHEMAS = {
  workos_log_energy: LogEnergySchema,
  workos_get_energy: GetEnergySchema,
} as const;
