// =============================================================================
// GET WEEKLY TRENDS TOOL
// MCP tool to fetch weekly health trends and patterns
// Implements cache-first strategy with API fallback
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import {
  getCachedSleep,
  getCachedReadiness,
  getCachedActivity,
  setCachedSleep,
  setCachedReadiness,
  setCachedActivity,
  getCachedSleepRange,
  getCachedReadinessRange,
  getCachedActivityRange,
} from "../cache/operations.js";
import { getAPIClient } from "../api/client.js";
import type { DailySleep, DailyReadiness, DailyActivity } from "../api/types.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

/**
 * Tool definition for get_weekly_trends
 * Returns 7-day trends for readiness, sleep, and activity scores
 */
export const getWeeklyTrendsTool: ToolDefinition = {
  name: "oura_get_weekly_trends",
  description:
    "Get 7-day health trends from Oura Ring data. Returns readiness, sleep, and activity scores " +
    "with statistical analysis (average, min, max) and trend direction (improving/stable/declining). " +
    "Identifies patterns like 'declining sleep quality' or 'improving recovery'. " +
    "Useful for understanding health patterns over time and making data-driven lifestyle adjustments.",
  inputSchema: {
    type: "object",
    properties: {
      end_date: {
        type: "string",
        description:
          "End date in YYYY-MM-DD format. Defaults to today. Trends will go back 7 days from this date.",
      },
      days: {
        type: "number",
        description:
          "Number of days to analyze (default: 7). Must be between 1 and 30.",
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
 */
function getTodayDate(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Get date N days before a given date
 */
function getDaysAgo(dateString: string, days: number): string {
  const date = new Date(dateString);
  date.setDate(date.getDate() - days);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Calculate statistics for an array of scores
 */
interface Statistics {
  average: number | null;
  min: number | null;
  max: number | null;
  count: number;
  trend: "improving" | "stable" | "declining" | "insufficient_data";
  trend_percentage: number | null;
}

function calculateStatistics(scores: (number | null)[]): Statistics {
  const validScores = scores.filter((s) => s !== null) as number[];

  if (validScores.length === 0) {
    return {
      average: null,
      min: null,
      max: null,
      count: 0,
      trend: "insufficient_data",
      trend_percentage: null,
    };
  }

  const average = Math.round(
    validScores.reduce((sum, score) => sum + score, 0) / validScores.length
  );
  const min = Math.min(...validScores);
  const max = Math.max(...validScores);

  // Calculate trend by comparing first half to second half
  let trend: "improving" | "stable" | "declining" | "insufficient_data" =
    "insufficient_data";
  let trend_percentage: number | null = null;

  if (validScores.length >= 4) {
    const midpoint = Math.floor(validScores.length / 2);
    const firstHalf = validScores.slice(0, midpoint);
    const secondHalf = validScores.slice(midpoint);

    const firstAvg =
      firstHalf.reduce((sum, score) => sum + score, 0) / firstHalf.length;
    const secondAvg =
      secondHalf.reduce((sum, score) => sum + score, 0) / secondHalf.length;

    const diff = secondAvg - firstAvg;
    trend_percentage = Math.round((diff / firstAvg) * 100);

    // Threshold: >3% change is considered improving/declining
    if (diff > 3) {
      trend = "improving";
    } else if (diff < -3) {
      trend = "declining";
    } else {
      trend = "stable";
    }
  }

  return {
    average,
    min,
    max,
    count: validScores.length,
    trend,
    trend_percentage,
  };
}

/**
 * Identify patterns in the data
 */
function identifyPatterns(
  sleepStats: Statistics,
  readinessStats: Statistics,
  activityStats: Statistics
): string[] {
  const patterns: string[] = [];

  // Sleep patterns
  if (sleepStats.trend === "declining" && sleepStats.average && sleepStats.average < 75) {
    patterns.push(
      "⚠️ Sleep quality declining and below optimal (< 75). Consider improving sleep hygiene."
    );
  } else if (sleepStats.trend === "declining") {
    patterns.push("Sleep quality is declining. Monitor sleep patterns closely.");
  } else if (sleepStats.trend === "improving") {
    patterns.push("✅ Sleep quality is improving. Keep up the good habits!");
  }

  if (sleepStats.average && sleepStats.average < 70) {
    patterns.push(
      "⚠️ Average sleep score is low (< 70). Focus on getting more consistent, quality sleep."
    );
  } else if (sleepStats.average && sleepStats.average >= 85) {
    patterns.push("✅ Excellent average sleep score (85+). Sleep habits are working well!");
  }

  // Readiness patterns
  if (readinessStats.trend === "declining" && readinessStats.average && readinessStats.average < 70) {
    patterns.push(
      "⚠️ Readiness declining and low. Body needs more rest and recovery time."
    );
  } else if (readinessStats.trend === "declining") {
    patterns.push(
      "Readiness is declining. Consider reducing training intensity or increasing rest."
    );
  } else if (readinessStats.trend === "improving") {
    patterns.push("✅ Recovery is improving. Body is adapting well to current routine.");
  }

  if (readinessStats.average && readinessStats.average < 70) {
    patterns.push(
      "⚠️ Low average readiness (< 70). Prioritize recovery activities and rest."
    );
  } else if (readinessStats.average && readinessStats.average >= 85) {
    patterns.push("✅ Excellent readiness (85+). Body is well-recovered and ready for challenges!");
  }

  // Activity patterns
  if (activityStats.trend === "declining") {
    patterns.push(
      "Activity levels declining. Consider increasing daily movement or exercise."
    );
  } else if (activityStats.trend === "improving") {
    patterns.push("✅ Activity levels improving. Good progress on movement goals!");
  }

  // Cross-metric patterns
  if (
    sleepStats.trend === "declining" &&
    readinessStats.trend === "declining" &&
    activityStats.trend === "improving"
  ) {
    patterns.push(
      "⚠️ Pattern detected: Increasing activity while sleep and recovery decline. " +
        "Consider reducing training intensity to allow recovery."
    );
  }

  if (
    sleepStats.trend === "improving" &&
    readinessStats.trend === "improving"
  ) {
    patterns.push(
      "✅ Positive pattern: Both sleep and recovery improving together. " +
        "Current lifestyle choices are supporting health well."
    );
  }

  if (patterns.length === 0) {
    patterns.push("No significant patterns detected. Health metrics appear stable.");
  }

  return patterns;
}

/**
 * Format trend data for LLM consumption
 */
function formatTrendData(
  sleepData: DailySleep[],
  readinessData: DailyReadiness[],
  activityData: DailyActivity[],
  startDate: string,
  endDate: string,
  days: number
): any {
  // Extract scores
  const sleepScores = sleepData.map((d) => d.score);
  const readinessScores = readinessData.map((d) => d.score);
  const activityScores = activityData.map((d) => d.score);

  // Calculate statistics
  const sleepStats = calculateStatistics(sleepScores);
  const readinessStats = calculateStatistics(readinessScores);
  const activityStats = calculateStatistics(activityScores);

  // Identify patterns
  const patterns = identifyPatterns(sleepStats, readinessStats, activityStats);

  // Format daily data for reference
  const dailyData = [];
  const dateRange = [];
  for (let i = 0; i < days; i++) {
    const date = getDaysAgo(endDate, days - 1 - i);
    dateRange.push(date);
  }

  for (const date of dateRange) {
    const sleep = sleepData.find((d) => d.day === date);
    const readiness = readinessData.find((d) => d.day === date);
    const activity = activityData.find((d) => d.day === date);

    dailyData.push({
      date,
      sleep_score: sleep?.score ?? null,
      readiness_score: readiness?.score ?? null,
      activity_score: activity?.score ?? null,
    });
  }

  return {
    period: {
      start_date: startDate,
      end_date: endDate,
      days: days,
    },
    sleep: {
      ...sleepStats,
      interpretation: sleepStats.average
        ? sleepStats.average >= 85
          ? "Excellent"
          : sleepStats.average >= 70
          ? "Good"
          : sleepStats.average >= 60
          ? "Fair"
          : "Poor"
        : "No data",
    },
    readiness: {
      ...readinessStats,
      interpretation: readinessStats.average
        ? readinessStats.average >= 85
          ? "Excellent"
          : readinessStats.average >= 70
          ? "Good"
          : readinessStats.average >= 60
          ? "Fair"
          : "Poor"
        : "No data",
    },
    activity: {
      ...activityStats,
      interpretation: activityStats.average
        ? activityStats.average >= 85
          ? "Excellent"
          : activityStats.average >= 70
          ? "Good"
          : activityStats.average >= 60
          ? "Fair"
          : "Poor"
        : "No data",
    },
    patterns,
    daily_data: dailyData,
  };
}

// =============================================================================
// HANDLER IMPLEMENTATION
// =============================================================================

/**
 * Handler for get_weekly_trends tool
 * Implements cache-first strategy with API fallback
 */
export async function handleGetWeeklyTrends(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    // Parse parameters
    const endDate = args.end_date || getTodayDate();
    const days = args.days && typeof args.days === "number" ? args.days : 7;

    // Validate parameters
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(endDate)) {
      return errorResponse(
        "Invalid end_date format. Please use YYYY-MM-DD format.",
        { providedDate: endDate }
      );
    }

    if (days < 1 || days > 30) {
      return errorResponse(
        "Invalid days parameter. Must be between 1 and 30.",
        { providedDays: days }
      );
    }

    // Calculate date range
    const startDate = getDaysAgo(endDate, days - 1);

    // Try cache first for all data types
    let sleepData = getCachedSleepRange(startDate, endDate);
    let readinessData = getCachedReadinessRange(startDate, endDate);
    let activityData = getCachedActivityRange(startDate, endDate);

    let source = "cache";
    let missingDates: string[] = [];

    // Check if we have all the dates in cache
    const allDates: string[] = [];
    for (let i = 0; i < days; i++) {
      allDates.push(getDaysAgo(endDate, days - 1 - i));
    }

    const sleepDates = new Set(sleepData.map((d) => d.day));
    const readinessDates = new Set(readinessData.map((d) => d.day));
    const activityDates = new Set(activityData.map((d) => d.day));

    for (const date of allDates) {
      if (!sleepDates.has(date) || !readinessDates.has(date) || !activityDates.has(date)) {
        missingDates.push(date);
      }
    }

    // If we have missing dates, fetch from API
    if (missingDates.length > 0) {
      try {
        const apiClient = getAPIClient();

        // Fetch all three data types in parallel
        const [apiSleep, apiReadiness, apiActivity] = await Promise.all([
          apiClient.getDailySleep({ startDate, endDate }),
          apiClient.getDailyReadiness({ startDate, endDate }),
          apiClient.getDailyActivity({ startDate, endDate }),
        ]);

        // Cache new data
        if (apiSleep && apiSleep.length > 0) {
          for (const item of apiSleep) {
            setCachedSleep(item);
          }
        }
        if (apiReadiness && apiReadiness.length > 0) {
          for (const item of apiReadiness) {
            setCachedReadiness(item);
          }
        }
        if (apiActivity && apiActivity.length > 0) {
          for (const item of apiActivity) {
            setCachedActivity(item);
          }
        }

        // Merge with cached data (API data takes precedence)
        const sleepMap = new Map(sleepData.map((d) => [d.day, d]));
        for (const item of apiSleep) {
          sleepMap.set(item.day, item);
        }
        sleepData = Array.from(sleepMap.values());

        const readinessMap = new Map(readinessData.map((d) => [d.day, d]));
        for (const item of apiReadiness) {
          readinessMap.set(item.day, item);
        }
        readinessData = Array.from(readinessMap.values());

        const activityMap = new Map(activityData.map((d) => [d.day, d]));
        for (const item of apiActivity) {
          activityMap.set(item.day, item);
        }
        activityData = Array.from(activityMap.values());

        source = "api";
      } catch (apiError: any) {
        // API failed - use cached data if available (graceful degradation)
        if (sleepData.length > 0 || readinessData.length > 0 || activityData.length > 0) {
          source = "cache_stale";
        } else {
          return errorResponse(
            "Failed to fetch weekly trends from Oura API and no cached data available",
            {
              startDate,
              endDate,
              error: apiError.message,
            }
          );
        }
      }
    }

    // Format and return data
    const formattedData = formatTrendData(
      sleepData,
      readinessData,
      activityData,
      startDate,
      endDate,
      days
    );

    return successResponse({
      ...formattedData,
      source,
      ...(source === "cache_stale" && {
        warning:
          "API is currently unavailable. Returning cached data which may be incomplete or stale.",
      }),
    });
  } catch (error: any) {
    return errorResponse("Unexpected error while fetching weekly trends", {
      error: error.message,
      stack: error.stack,
    });
  }
}
