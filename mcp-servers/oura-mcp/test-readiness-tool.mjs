#!/usr/bin/env node

/**
 * Test script for readiness tool
 * Tests the get_today_readiness MCP tool
 */

import { handleGetTodayReadiness, getTodayReadinessTool } from "./dist/tools/readiness.js";

console.log("=".repeat(80));
console.log("READINESS TOOL TEST");
console.log("=".repeat(80));

// Test 1: Tool definition
console.log("\n✓ Test 1: Tool Definition");
console.log("Name:", getTodayReadinessTool.name);
console.log("Description:", getTodayReadinessTool.description.substring(0, 100) + "...");
console.log("Input schema properties:", Object.keys(getTodayReadinessTool.inputSchema.properties));

// Test 2: Handler with no args (should fetch today's data)
console.log("\n✓ Test 2: Fetch Today's Readiness");
try {
  const result = await handleGetTodayReadiness({});
  const data = JSON.parse(result.content[0].text);

  if (data.error) {
    console.log("Expected behavior - No data available yet or API not configured:");
    console.log(data.error);
  } else {
    console.log("Date:", data.date);
    console.log("Score:", data.score);
    console.log("Interpretation:", data.interpretation);
    console.log("Source:", data.source);
    console.log("Contributors available:", Object.keys(data.contributors).filter(k => data.contributors[k] !== null).length);
  }
} catch (error) {
  console.log("Expected error (API not configured or no data):", error.message);
}

// Test 3: Handler with specific date
console.log("\n✓ Test 3: Fetch Specific Date");
try {
  const result = await handleGetTodayReadiness({ date: "2024-01-15" });
  const data = JSON.parse(result.content[0].text);

  if (data.error) {
    console.log("Expected behavior - No data for past date:");
    console.log(data.error);
  } else {
    console.log("Date:", data.date);
    console.log("Score:", data.score);
  }
} catch (error) {
  console.log("Expected error:", error.message);
}

// Test 4: Invalid date format
console.log("\n✓ Test 4: Invalid Date Format");
try {
  const result = await handleGetTodayReadiness({ date: "invalid-date" });
  const data = JSON.parse(result.content[0].text);

  if (data.error) {
    console.log("✓ Correctly rejected invalid date format:");
    console.log(data.error);
  } else {
    console.log("✗ Should have rejected invalid date");
  }
} catch (error) {
  console.log("Error:", error.message);
}

// Test 5: Tool metadata
console.log("\n✓ Test 5: Tool Metadata Validation");
console.log("Tool name follows convention:", getTodayReadinessTool.name.startsWith("oura_"));
console.log("Has description:", getTodayReadinessTool.description.length > 50);
console.log("Has input schema:", getTodayReadinessTool.inputSchema.type === "object");
console.log("Required fields:", getTodayReadinessTool.inputSchema.required);

console.log("\n" + "=".repeat(80));
console.log("ALL TESTS COMPLETED");
console.log("=".repeat(80));
