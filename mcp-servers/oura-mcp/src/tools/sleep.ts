// =============================================================================
// GET SLEEP SUMMARY TOOL
// MCP tool to fetch sleep summary for a given date
// Implements cache-first strategy with API fallback
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import { getCachedSleep, setCachedSleep } from "../cache/operations.js";
import { getAPIClient } from "../api/client.js";
import type { DailySleep } from "../api/types.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

/**
 * Tool definition for get_sleep_summary
 * Returns sleep score, duration, stages, and efficiency
 */
export const getSleepSummaryTool: ToolDefinition = {
  name: "oura_get_sleep_summary",
  description:
    "Get sleep summary for a specific date including sleep score (0-100), " +
    "total sleep duration, sleep stages (REM, deep, light), sleep efficiency, " +
    "and timing information. Sleep score reflects overall sleep quality based on " +
    "duration, efficiency, restfulness, REM sleep, deep sleep, latency, and timing. " +
    "Higher scores (85+) indicate excellent sleep. Lower scores (<70) suggest poor sleep quality.",
  inputSchema: {
    type: "object",
    properties: {
      date: {
        type: "string",
        description:
          "Date in YYYY-MM-DD format. Defaults to last night (today's date) if not provided.",
      },
    },
    required: [],
  },
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get today's date in YYYY-MM-DD format
 * This represents "last night" in Oura's terminology
 */
function getTodayDate(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Convert seconds to hours and minutes string
 */
function formatDuration(seconds: number | null): string {
  if (seconds === null) return "N/A";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

/**
 * Format sleep data for LLM consumption
 * Provides human-readable interpretation of scores and durations
 */
function formatSleepData(data: DailySleep): any {
  const score = data.score;
  let interpretation = "";

  if (score === null) {
    interpretation = "No sleep score available for this date";
  } else if (score >= 85) {
    interpretation =
      "Excellent - High-quality sleep with optimal duration and efficiency";
  } else if (score >= 70) {
    interpretation =
      "Good - Sleep quality was satisfactory with decent recovery";
  } else if (score >= 60) {
    interpretation =
      "Fair - Sleep quality was below optimal, consider improving sleep habits";
  } else {
    interpretation =
      "Poor - Sleep quality was low. Focus on better sleep hygiene and longer sleep duration.";
  }

  // Calculate percentages for sleep stages
  const totalSleep = data.total_sleep_duration || 0;
  const remPercent = totalSleep > 0 && data.rem_sleep_duration
    ? Math.round((data.rem_sleep_duration / totalSleep) * 100)
    : null;
  const deepPercent = totalSleep > 0 && data.deep_sleep_duration
    ? Math.round((data.deep_sleep_duration / totalSleep) * 100)
    : null;
  const lightPercent = totalSleep > 0 && data.light_sleep_duration
    ? Math.round((data.light_sleep_duration / totalSleep) * 100)
    : null;

  return {
    date: data.day,
    score: score,
    interpretation: interpretation,
    duration: {
      total_sleep: formatDuration(data.total_sleep_duration),
      total_sleep_seconds: data.total_sleep_duration,
      time_in_bed: formatDuration(data.time_in_bed),
      awake_time: formatDuration(data.awake_time),
    },
    sleep_stages: {
      rem: {
        duration: formatDuration(data.rem_sleep_duration),
        seconds: data.rem_sleep_duration,
        percentage: remPercent !== null ? `${remPercent}%` : "N/A",
        meaning: "REM sleep - critical for memory consolidation and learning",
      },
      deep: {
        duration: formatDuration(data.deep_sleep_duration),
        seconds: data.deep_sleep_duration,
        percentage: deepPercent !== null ? `${deepPercent}%` : "N/A",
        meaning: "Deep sleep - essential for physical recovery and immune function",
      },
      light: {
        duration: formatDuration(data.light_sleep_duration),
        seconds: data.light_sleep_duration,
        percentage: lightPercent !== null ? `${lightPercent}%` : "N/A",
        meaning: "Light sleep - facilitates transition between sleep stages",
      },
    },
    efficiency: {
      percentage: data.efficiency !== null ? `${data.efficiency}%` : "N/A",
      value: data.efficiency,
      meaning:
        data.efficiency !== null
          ? data.efficiency >= 90
            ? "Excellent - Very efficient sleep"
            : data.efficiency >= 85
            ? "Good - Efficient sleep"
            : data.efficiency >= 75
            ? "Fair - Could be improved"
            : "Poor - Low efficiency, many awakenings"
          : "N/A",
    },
    timing: {
      bedtime_start: data.timing?.bedtime_start ?? null,
      bedtime_end: data.timing?.bedtime_end ?? null,
      latency: formatDuration(data.latency ?? null),
      latency_seconds: data.latency ?? null,
      latency_meaning:
        data.latency !== null
          ? data.latency <= 600
            ? "Good - Fell asleep quickly"
            : data.latency <= 1800
            ? "Fair - Took some time to fall asleep"
            : "Poor - Took a long time to fall asleep"
          : "N/A",
    },
    contributors: {
      deep_sleep:
        data.contributors.deep_sleep !== null
          ? {
              score: data.contributors.deep_sleep,
              meaning: "Quality of deep sleep phase",
            }
          : null,
      efficiency:
        data.contributors.efficiency !== null
          ? {
              score: data.contributors.efficiency,
              meaning: "How efficiently you slept without interruptions",
            }
          : null,
      latency:
        data.contributors.latency !== null
          ? {
              score: data.contributors.latency,
              meaning: "How quickly you fell asleep",
            }
          : null,
      rem_sleep:
        data.contributors.rem_sleep !== null
          ? {
              score: data.contributors.rem_sleep,
              meaning: "Quality and duration of REM sleep",
            }
          : null,
      restfulness:
        data.contributors.restfulness !== null
          ? {
              score: data.contributors.restfulness,
              meaning: "How restful your sleep was",
            }
          : null,
      timing:
        data.contributors.timing !== null
          ? {
              score: data.contributors.timing,
              meaning: "Alignment with your natural circadian rhythm",
            }
          : null,
      total_sleep:
        data.contributors.total_sleep !== null
          ? {
              score: data.contributors.total_sleep,
              meaning: "Total duration of sleep",
            }
          : null,
    },
    additional_metrics: {
      restless_periods: data.restless_periods,
      average_heart_rate: data.average_heart_rate,
      lowest_heart_rate: data.lowest_heart_rate,
      average_hrv: data.average_hrv,
      average_breath_rate: data.average_breath,
      temperature_deviation: data.temperature_deviation,
    },
  };
}

// =============================================================================
// HANDLER IMPLEMENTATION
// =============================================================================

/**
 * Handler for get_sleep_summary tool
 * Implements cache-first strategy with API fallback
 */
export async function handleGetSleepSummary(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    // Determine which date to fetch (defaults to today/last night)
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
    let sleepData = getCachedSleep(targetDate);

    if (sleepData) {
      // Found in cache
      const formattedData = formatSleepData(sleepData);
      return successResponse({
        ...formattedData,
        source: "cache",
      });
    }

    // Cache miss - fetch from API
    try {
      const apiClient = getAPIClient();
      sleepData = await apiClient.getSleepForDate(targetDate);

      if (!sleepData) {
        // No data available for this date
        return errorResponse(
          `No sleep data available for ${targetDate}. ` +
            "This could mean the data hasn't been synced yet, the date is in the future, " +
            "or the ring wasn't worn during sleep.",
          { date: targetDate }
        );
      }

      // Cache the result
      setCachedSleep(sleepData);

      // Return formatted data
      const formattedData = formatSleepData(sleepData);
      return successResponse({
        ...formattedData,
        source: "api",
      });
    } catch (apiError: any) {
      // API failed - check if we have any cached data from before (even if expired)
      // This provides graceful degradation
      const staleData = getCachedSleep(targetDate);
      if (staleData) {
        const formattedData = formatSleepData(staleData);
        return successResponse({
          ...formattedData,
          source: "cache_stale",
          warning:
            "API is currently unavailable. Returning cached data which may be stale.",
        });
      }

      // No cached data available at all
      return errorResponse(
        "Failed to fetch sleep data from Oura API and no cached data available",
        {
          date: targetDate,
          error: apiError.message,
        }
      );
    }
  } catch (error: any) {
    return errorResponse("Unexpected error while fetching sleep data", {
      error: error.message,
      stack: error.stack,
    });
  }
}
