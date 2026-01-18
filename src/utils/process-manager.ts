// =============================================================================
// PROCESS MANAGER - PID File Management & Process Tracking
// Prevents duplicate daemons and tracks orphaned processes
// =============================================================================

import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execSync } from "child_process";

// =============================================================================
// CONFIGURATION
// =============================================================================

const PID_DIR = process.env.THANOS_PID_DIR || path.join(os.homedir(), ".thanos", "pids");

// Known process types and their expected patterns
const PROCESS_PATTERNS: Record<string, string> = {
  "claude-flow-daemon": "claude-flow.*daemon",
  "chroma-server": "chroma run|chroma-mcp",
  "workos-mcp": "workos-mcp",
  "oura-mcp": "oura-mcp",
  "flow-nexus": "flow-nexus",
  "ruv-swarm": "ruv-swarm",
};

// =============================================================================
// PID FILE MANAGEMENT
// =============================================================================

/**
 * Ensure PID directory exists
 */
function ensurePidDir(): void {
  if (!fs.existsSync(PID_DIR)) {
    fs.mkdirSync(PID_DIR, { recursive: true });
  }
}

/**
 * Get PID file path for a process name
 */
function getPidFilePath(name: string): string {
  return path.join(PID_DIR, `${name}.pid`);
}

/**
 * Write PID file for a process
 */
export function writePidFile(name: string, pid?: number): void {
  ensurePidDir();
  const pidToWrite = pid || process.pid;
  fs.writeFileSync(getPidFilePath(name), pidToWrite.toString(), "utf-8");
}

/**
 * Read PID from file
 */
export function readPidFile(name: string): number | null {
  const pidPath = getPidFilePath(name);
  if (!fs.existsSync(pidPath)) {
    return null;
  }
  try {
    const content = fs.readFileSync(pidPath, "utf-8").trim();
    const pid = parseInt(content, 10);
    return isNaN(pid) ? null : pid;
  } catch {
    return null;
  }
}

/**
 * Remove PID file
 */
export function removePidFile(name: string): void {
  const pidPath = getPidFilePath(name);
  if (fs.existsSync(pidPath)) {
    fs.unlinkSync(pidPath);
  }
}

/**
 * Check if a process is running by PID
 */
export function isProcessRunning(pid: number): boolean {
  try {
    // Send signal 0 to check if process exists (doesn't actually send a signal)
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

/**
 * Kill a process by its tracked name
 */
export function killProcessByName(name: string): boolean {
  const pid = readPidFile(name);
  if (pid && isProcessRunning(pid)) {
    try {
      process.kill(pid, "SIGTERM");
      removePidFile(name);
      return true;
    } catch {
      return false;
    }
  }
  removePidFile(name); // Clean up stale PID file
  return false;
}

// =============================================================================
// DUPLICATE DETECTION
// =============================================================================

/**
 * Check if a process type is already running
 * Returns the PID if running, null if not
 */
export function checkDuplicateProcess(name: string): number | null {
  const existingPid = readPidFile(name);
  if (existingPid && isProcessRunning(existingPid)) {
    return existingPid;
  }
  // Clean up stale PID file
  if (existingPid) {
    removePidFile(name);
  }
  return null;
}

/**
 * Ensure only one instance of a process type is running
 * Throws if duplicate found, otherwise writes PID file
 */
export function ensureSingleInstance(name: string): void {
  const existingPid = checkDuplicateProcess(name);
  if (existingPid) {
    throw new Error(
      `Process "${name}" is already running (PID: ${existingPid}). ` +
      `Kill it first or use a different instance name.`
    );
  }
  writePidFile(name);
}

// =============================================================================
// ORPHAN DETECTION
// =============================================================================

interface OrphanedProcess {
  pid: number;
  name: string;
  command: string;
  startTime: string;
}

/**
 * Find orphaned processes matching known patterns
 */
export function findOrphanedProcesses(): OrphanedProcess[] {
  const orphans: OrphanedProcess[] = [];

  try {
    // Get all claude-related processes
    const psOutput = execSync(
      'ps aux | grep -E "(claude|swarm|flow|chroma)" | grep -v grep',
      { encoding: "utf-8", timeout: 5000 }
    ).trim();

    if (!psOutput) return orphans;

    const lines = psOutput.split("\n");
    for (const line of lines) {
      const parts = line.split(/\s+/);
      if (parts.length < 11) continue;

      const pid = parseInt(parts[1], 10);
      const startTime = parts[8];
      const command = parts.slice(10).join(" ");

      // Check if it's a known orphan pattern (Task agents with --resume)
      if (command.includes("--resume") && command.includes("--disallowedTools")) {
        orphans.push({
          pid,
          name: "task-agent",
          command: command.substring(0, 100) + "...",
          startTime,
        });
      }

      // Check for duplicate daemons (more than one daemon process)
      if (command.includes("daemon start") && command.includes("claude-flow")) {
        const existingPid = readPidFile("claude-flow-daemon");
        if (existingPid && existingPid !== pid) {
          orphans.push({
            pid,
            name: "duplicate-daemon",
            command: command.substring(0, 100) + "...",
            startTime,
          });
        }
      }
    }
  } catch {
    // ps command failed or no matches
  }

  return orphans;
}

/**
 * Kill all orphaned processes
 */
export function cleanupOrphanedProcesses(): { killed: number; errors: string[] } {
  const orphans = findOrphanedProcesses();
  let killed = 0;
  const errors: string[] = [];

  for (const orphan of orphans) {
    try {
      process.kill(orphan.pid, "SIGTERM");
      killed++;
    } catch (error) {
      errors.push(`Failed to kill PID ${orphan.pid}: ${error}`);
    }
  }

  return { killed, errors };
}

// =============================================================================
// CLEANUP ALL
// =============================================================================

/**
 * Clean up all PID files (useful on startup)
 */
export function cleanupStalePidFiles(): number {
  ensurePidDir();
  let cleaned = 0;

  try {
    const files = fs.readdirSync(PID_DIR);
    for (const file of files) {
      if (file.endsWith(".pid")) {
        const name = file.replace(".pid", "");
        const pid = readPidFile(name);
        if (pid && !isProcessRunning(pid)) {
          removePidFile(name);
          cleaned++;
        }
      }
    }
  } catch {
    // Directory doesn't exist or other error
  }

  return cleaned;
}

/**
 * List all tracked processes and their status
 */
export function listTrackedProcesses(): Array<{
  name: string;
  pid: number | null;
  running: boolean;
}> {
  ensurePidDir();
  const result: Array<{ name: string; pid: number | null; running: boolean }> = [];

  try {
    const files = fs.readdirSync(PID_DIR);
    for (const file of files) {
      if (file.endsWith(".pid")) {
        const name = file.replace(".pid", "");
        const pid = readPidFile(name);
        result.push({
          name,
          pid,
          running: pid ? isProcessRunning(pid) : false,
        });
      }
    }
  } catch {
    // Directory doesn't exist
  }

  return result;
}
