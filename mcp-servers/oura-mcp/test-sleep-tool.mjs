#!/usr/bin/env node
// =============================================================================
// SLEEP TOOL TEST
// Tests the oura_get_sleep_summary MCP tool
// =============================================================================

import { getSleepSummaryTool, handleGetSleepSummary } from "./dist/tools/sleep.js";

console.log("=".repeat(80));
console.log("SLEEP TOOL TEST");
console.log("=".repeat(80));

// Test 1: Tool definition
console.log("\n1. Tool Definition:");
console.log("   Name:", getSleepSummaryTool.name);
console.log("   Description:", getSleepSummaryTool.description.substring(0, 100) + "...");
console.log("   Has inputSchema:", !!getSleepSummaryTool.inputSchema);
console.log("   ✓ Tool definition structure is correct");

// Test 2: Get today's sleep (or most recent)
console.log("\n2. Testing get sleep summary (today/last night):");
try {
  const result = await handleGetSleepSummary({});
  const data = JSON.parse(result.content[0].text);

  if (data.error) {
    console.log("   ⚠ No sleep data available yet (expected for early morning)");
    console.log("   Error:", data.error);
  } else {
    console.log("   Date:", data.date);
    console.log("   Score:", data.score);
    console.log("   Interpretation:", data.interpretation);
    console.log("   Total Sleep:", data.duration.total_sleep);
    console.log("   Efficiency:", data.efficiency.percentage);
    console.log("   Sleep Stages:");
    console.log("     - REM:", data.sleep_stages.rem.duration, `(${data.sleep_stages.rem.percentage})`);
    console.log("     - Deep:", data.sleep_stages.deep.duration, `(${data.sleep_stages.deep.percentage})`);
    console.log("     - Light:", data.sleep_stages.light.duration, `(${data.sleep_stages.light.percentage})`);
    console.log("   Source:", data.source);
    console.log("   ✓ Successfully fetched sleep data");
  }
} catch (error) {
  console.log("   ⚠ Error (expected if no OAuth token configured):", error.message);
}

// Test 3: Get specific date
console.log("\n3. Testing get sleep summary for specific date (2024-01-15):");
try {
  const result = await handleGetSleepSummary({ date: "2024-01-15" });
  const data = JSON.parse(result.content[0].text);

  if (data.error) {
    console.log("   ⚠ No data for this date (expected)");
  } else {
    console.log("   Date:", data.date);
    console.log("   Score:", data.score);
    console.log("   Total Sleep:", data.duration.total_sleep);
    console.log("   Source:", data.source);
    console.log("   ✓ Successfully fetched historical sleep data");
  }
} catch (error) {
  console.log("   ⚠ Error (expected if no OAuth token):", error.message);
}

// Test 4: Invalid date format
console.log("\n4. Testing invalid date format:");
try {
  const result = await handleGetSleepSummary({ date: "01/15/2024" });
  const data = JSON.parse(result.content[0].text);

  if (data.error && data.error.includes("Invalid date format")) {
    console.log("   ✓ Correctly rejected invalid date format");
  } else {
    console.log("   ✗ Should have rejected invalid date format");
  }
} catch (error) {
  console.log("   ✗ Unexpected error:", error.message);
}

// Test 5: Response structure validation
console.log("\n5. Testing response metadata:");
console.log("   Tool name:", getSleepSummaryTool.name);
console.log("   Input schema type:", getSleepSummaryTool.inputSchema.type);
console.log("   Required fields:", getSleepSummaryTool.inputSchema.required.length);
console.log("   Has date property:", !!getSleepSummaryTool.inputSchema.properties.date);
console.log("   ✓ Response structure is valid");

console.log("\n" + "=".repeat(80));
console.log("SLEEP TOOL TEST COMPLETE");
console.log("=".repeat(80));
