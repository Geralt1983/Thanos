// =============================================================================
// GET TODAY'S READINESS TOOL
// MCP tool to fetch today's readiness score and contributors
// Implements cache-first strategy with API fallback
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import { getCachedReadiness, setCachedReadiness } from "../cache/operations.js";
import { getAPIClient } from "../api/client.js";
import type { DailyReadiness } from "../api/types.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

/**
 * Tool definition for get_today_readiness
 * Returns readiness score (0-100) and contributors
 */
export const getTodayReadinessTool: ToolDefinition = {
  name: "oura_get_today_readiness",
  description:
    "Get today's Oura readiness score (0-100) and contributing factors. " +
    "Readiness indicates physical and mental recovery. Contributors include: " +
    "sleep quality, HRV balance, body temperature, resting heart rate, " +
    "activity balance, sleep balance, previous night sleep, previous day activity, and recovery index. " +
    "Higher scores (85+) indicate excellent readiness. Lower scores (<70) suggest the body needs rest.",
  inputSchema: {
    type: "object",
    properties: {
      date: {
        type: "string",
        description:
          "Optional date in YYYY-MM-DD format. Defaults to today if not provided.",
      },
    },
    required: [],
  },
};

// =============================================================================
// HANDLER IMPLEMENTATION
// =============================================================================

/**
 * Get today's date in YYYY-MM-DD format
 */
function getTodayDate(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Format readiness data for LLM consumption
 * Provides human-readable interpretation of scores
 */
function formatReadinessData(data: DailyReadiness): any {
  const score = data.score;
  let interpretation = "";

  if (score === null) {
    interpretation = "No readiness score available for this date";
  } else if (score >= 85) {
    interpretation =
      "Excellent - Body is well-recovered and ready for demanding activities";
  } else if (score >= 70) {
    interpretation =
      "Good - Body is ready for normal activities with balanced effort";
  } else if (score >= 60) {
    interpretation =
      "Fair - Consider lighter activities or more recovery time";
  } else {
    interpretation =
      "Pay attention - Body needs rest and recovery. Avoid intense activities.";
  }

  return {
    date: data.day,
    score: score,
    interpretation: interpretation,
    contributors: {
      sleep_quality:
        data.contributors.previous_night !== null
          ? {
              score: data.contributors.previous_night,
              meaning: "How well you slept last night",
            }
          : null,
      hrv_balance:
        data.contributors.hrv_balance !== null
          ? {
              score: data.contributors.hrv_balance,
              meaning: "Heart rate variability balance indicating stress levels",
            }
          : null,
      body_temperature:
        data.contributors.body_temperature !== null
          ? {
              score: data.contributors.body_temperature,
              meaning: "Body temperature deviation from baseline",
            }
          : null,
      resting_heart_rate:
        data.contributors.resting_heart_rate !== null
          ? {
              score: data.contributors.resting_heart_rate,
              meaning: "Resting heart rate compared to your baseline",
            }
          : null,
      activity_balance:
        data.contributors.activity_balance !== null
          ? {
              score: data.contributors.activity_balance,
              meaning: "Balance between activity and recovery",
            }
          : null,
      sleep_balance:
        data.contributors.sleep_balance !== null
          ? {
              score: data.contributors.sleep_balance,
              meaning: "Recent sleep patterns and consistency",
            }
          : null,
      previous_day_activity:
        data.contributors.previous_day_activity !== null
          ? {
              score: data.contributors.previous_day_activity,
              meaning: "Impact of yesterday's physical activity",
            }
          : null,
      recovery_index:
        data.contributors.recovery_index !== null
          ? {
              score: data.contributors.recovery_index,
              meaning: "Overall recovery from recent activities",
            }
          : null,
    },
    metrics: {
      temperature_deviation: data.temperature_deviation,
      temperature_trend_deviation: data.temperature_trend_deviation,
      resting_heart_rate: data.resting_heart_rate,
      hrv_balance: data.hrv_balance,
    },
  };
}

/**
 * Handler for get_today_readiness tool
 * Implements cache-first strategy with API fallback
 */
export async function handleGetTodayReadiness(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    // Determine which date to fetch
    const targetDate = args.date || getTodayDate();

    // Validate date format
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(targetDate)) {
      return errorResponse(
        "Invalid date format. Please use YYYY-MM-DD format.",
        { providedDate: targetDate }
      );
    }

    // Try cache first
    let readinessData = getCachedReadiness(targetDate);

    if (readinessData) {
      // Found in cache
      const formattedData = formatReadinessData(readinessData);
      return successResponse({
        ...formattedData,
        source: "cache",
      });
    }

    // Cache miss - fetch from API
    try {
      const apiClient = getAPIClient();
      readinessData = await apiClient.getReadinessForDate(targetDate);

      if (!readinessData) {
        // No data available for this date
        return errorResponse(
          `No readiness data available for ${targetDate}. ` +
            "This could mean the data hasn't been synced yet or the date is in the future.",
          { date: targetDate }
        );
      }

      // Cache the result
      setCachedReadiness(readinessData);

      // Return formatted data
      const formattedData = formatReadinessData(readinessData);
      return successResponse({
        ...formattedData,
        source: "api",
      });
    } catch (apiError: any) {
      // API failed - check if we have any cached data from before (even if expired)
      // This provides graceful degradation
      const staleData = getCachedReadiness(targetDate);
      if (staleData) {
        const formattedData = formatReadinessData(staleData);
        return successResponse({
          ...formattedData,
          source: "cache_stale",
          warning:
            "API is currently unavailable. Returning cached data which may be stale.",
        });
      }

      // No cached data available at all
      return errorResponse(
        "Failed to fetch readiness data from Oura API and no cached data available",
        {
          date: targetDate,
          error: apiError.message,
        }
      );
    }
  } catch (error: any) {
    return errorResponse("Unexpected error while fetching readiness data", {
      error: error.message,
      stack: error.stack,
    });
  }
}
