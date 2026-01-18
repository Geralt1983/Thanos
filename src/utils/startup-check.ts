#!/usr/bin/env npx ts-node
// =============================================================================
// STARTUP CHECK - Detect and cleanup duplicate processes before starting
// Run this before starting daemons or new sessions
// =============================================================================

import {
  cleanupStalePidFiles,
  findOrphanedProcesses,
  cleanupOrphanedProcesses,
  listTrackedProcesses,
  checkDuplicateProcess,
  killProcessByName,
} from "./process-manager.js";
import { listSessions, cleanupAllOrphanedProcesses } from "./session-lifecycle.js";

// =============================================================================
// TYPES
// =============================================================================

export interface StartupCheckResult {
  stalePidsRemoved: number;
  orphansFound: number;
  orphansKilled: number;
  duplicateDaemons: number;
  staleSessions: number;
  errors: string[];
  safe: boolean;
}

// =============================================================================
// MAIN CHECK FUNCTION
// =============================================================================

/**
 * Run comprehensive startup checks and cleanup
 */
export async function runStartupCheck(options: {
  autoCleanup?: boolean;
  verbose?: boolean;
} = {}): Promise<StartupCheckResult> {
  const { autoCleanup = true, verbose = false } = options;
  const result: StartupCheckResult = {
    stalePidsRemoved: 0,
    orphansFound: 0,
    orphansKilled: 0,
    duplicateDaemons: 0,
    staleSessions: 0,
    errors: [],
    safe: true,
  };

  // 1. Clean up stale PID files
  try {
    result.stalePidsRemoved = cleanupStalePidFiles();
    if (verbose && result.stalePidsRemoved > 0) {
      console.log(`Cleaned up ${result.stalePidsRemoved} stale PID files`);
    }
  } catch (error) {
    result.errors.push(`PID cleanup error: ${error}`);
  }

  // 2. Find orphaned processes
  try {
    const orphans = findOrphanedProcesses();
    result.orphansFound = orphans.length;

    if (orphans.length > 0) {
      result.safe = false;
      if (verbose) {
        console.log(`\nFound ${orphans.length} orphaned processes:`);
        orphans.forEach(o => {
          console.log(`  - PID ${o.pid}: ${o.name} (started ${o.startTime})`);
        });
      }

      if (autoCleanup) {
        const cleanup = cleanupOrphanedProcesses();
        result.orphansKilled = cleanup.killed;
        result.errors.push(...cleanup.errors);
        if (verbose && cleanup.killed > 0) {
          console.log(`Killed ${cleanup.killed} orphaned processes`);
        }
      }
    }
  } catch (error) {
    result.errors.push(`Orphan detection error: ${error}`);
  }

  // 3. Check for duplicate daemons
  try {
    const daemonPid = checkDuplicateProcess("claude-flow-daemon");
    if (daemonPid) {
      result.duplicateDaemons++;
      result.safe = false;
      if (verbose) {
        console.log(`\nDuplicate daemon found: PID ${daemonPid}`);
      }

      if (autoCleanup) {
        // Keep the oldest daemon, it's probably the legitimate one
        // Only kill if we detect more than one running
        if (verbose) {
          console.log(`Note: Existing daemon kept running`);
        }
      }
    }
  } catch (error) {
    result.errors.push(`Daemon check error: ${error}`);
  }

  // 4. Check for stale sessions
  try {
    if (autoCleanup) {
      const cleanup = await cleanupAllOrphanedProcesses();
      result.staleSessions = cleanup.staleSessions;
      result.orphansKilled += cleanup.killed;
      result.errors.push(...cleanup.errors);
    }
  } catch (error) {
    result.errors.push(`Session cleanup error: ${error}`);
  }

  // 5. Determine if safe to start
  result.safe = result.orphansFound === 0 || result.orphansKilled === result.orphansFound;

  return result;
}

/**
 * Check if it's safe to start a specific process type
 */
export function checkProcessSafe(processName: string): {
  safe: boolean;
  existingPid: number | null;
  message: string;
} {
  const existingPid = checkDuplicateProcess(processName);

  if (existingPid) {
    return {
      safe: false,
      existingPid,
      message: `Process "${processName}" is already running (PID: ${existingPid}). Kill it first or use ensureSingleInstance().`,
    };
  }

  return {
    safe: true,
    existingPid: null,
    message: `Safe to start "${processName}"`,
  };
}

/**
 * Force kill a process by name and start fresh
 */
export function forceRestart(processName: string): {
  killed: boolean;
  previousPid: number | null;
} {
  const existingPid = checkDuplicateProcess(processName);
  let killed = false;

  if (existingPid) {
    killed = killProcessByName(processName);
  }

  return {
    killed,
    previousPid: existingPid,
  };
}

// =============================================================================
// CLI INTERFACE
// =============================================================================

async function main() {
  const args = process.argv.slice(2);
  const verbose = args.includes("--verbose") || args.includes("-v");
  const dryRun = args.includes("--dry-run");
  const forceClean = args.includes("--force");

  console.log("=== Thanos Startup Check ===\n");

  const result = await runStartupCheck({
    autoCleanup: !dryRun,
    verbose: true,
  });

  console.log("\n=== Summary ===");
  console.log(`Stale PIDs removed: ${result.stalePidsRemoved}`);
  console.log(`Orphans found: ${result.orphansFound}`);
  console.log(`Orphans killed: ${result.orphansKilled}`);
  console.log(`Stale sessions cleaned: ${result.staleSessions}`);
  console.log(`Safe to start: ${result.safe ? "YES" : "NO"}`);

  if (result.errors.length > 0) {
    console.log("\nErrors:");
    result.errors.forEach(e => console.log(`  - ${e}`));
  }

  // Show tracked processes
  console.log("\n=== Tracked Processes ===");
  const tracked = listTrackedProcesses();
  if (tracked.length === 0) {
    console.log("No tracked processes");
  } else {
    tracked.forEach(p => {
      const status = p.running ? "running" : "not running";
      console.log(`  - ${p.name}: PID ${p.pid || "?"} (${status})`);
    });
  }

  // Show active sessions
  console.log("\n=== Active Sessions ===");
  const sessions = listSessions();
  if (sessions.length === 0) {
    console.log("No active sessions");
  } else {
    sessions.forEach(s => {
      console.log(`  - ${s.sessionId}`);
      console.log(`    Started: ${s.startTime}`);
      console.log(`    Agents: ${s.agentPids.length}, Background: ${s.backgroundPids.length}`);
    });
  }

  process.exit(result.safe ? 0 : 1);
}

// Run if executed directly
if (process.argv[1]?.includes("startup-check")) {
  main().catch(console.error);
}
