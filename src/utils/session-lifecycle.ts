// =============================================================================
// SESSION LIFECYCLE MANAGER
// Tracks processes spawned during a Claude Code session for cleanup
// =============================================================================

import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execSync } from "child_process";
import {
  isProcessRunning,
  findOrphanedProcesses,
  cleanupStalePidFiles,
} from "./process-manager.js";

// =============================================================================
// CONFIGURATION
// =============================================================================

const SESSION_DIR = process.env.THANOS_SESSION_DIR ||
  path.join(os.homedir(), ".thanos", "sessions");

// =============================================================================
// TYPES
// =============================================================================

export interface SessionProcessMap {
  sessionId: string;
  parentPid: number;
  startTime: string;
  workingDirectory: string;
  mcpPids: number[];
  agentPids: number[];
  backgroundPids: number[];
}

// =============================================================================
// SESSION FILE MANAGEMENT
// =============================================================================

function ensureSessionDir(): void {
  if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
  }
}

function getSessionFilePath(sessionId: string): string {
  return path.join(SESSION_DIR, `${sessionId}.json`);
}

/**
 * Generate a session ID based on timestamp and parent PID
 */
export function generateSessionId(): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `session-${timestamp}-${process.ppid || process.pid}`;
}

/**
 * Track session start - records the parent process and initial state
 */
export async function trackSessionStart(sessionId?: string): Promise<SessionProcessMap> {
  ensureSessionDir();

  const id = sessionId || generateSessionId();
  const session: SessionProcessMap = {
    sessionId: id,
    parentPid: process.ppid || process.pid,
    startTime: new Date().toISOString(),
    workingDirectory: process.cwd(),
    mcpPids: [],
    agentPids: [],
    backgroundPids: [],
  };

  // Try to detect currently running MCP servers for this session
  try {
    const mcpPids = detectMcpServers();
    session.mcpPids = mcpPids;
  } catch {
    // MCP detection failed, continue without
  }

  fs.writeFileSync(getSessionFilePath(id), JSON.stringify(session, null, 2));
  return session;
}

/**
 * Load session data
 */
export function loadSession(sessionId: string): SessionProcessMap | null {
  const filePath = getSessionFilePath(sessionId);
  if (!fs.existsSync(filePath)) {
    return null;
  }
  try {
    const content = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(content) as SessionProcessMap;
  } catch {
    return null;
  }
}

/**
 * Save session data
 */
export function saveSession(session: SessionProcessMap): void {
  ensureSessionDir();
  fs.writeFileSync(getSessionFilePath(session.sessionId), JSON.stringify(session, null, 2));
}

/**
 * Track a spawned agent PID
 */
export function trackAgentPid(sessionId: string, pid: number): void {
  const session = loadSession(sessionId);
  if (session) {
    if (!session.agentPids.includes(pid)) {
      session.agentPids.push(pid);
      saveSession(session);
    }
  }
}

/**
 * Track a background process PID
 */
export function trackBackgroundPid(sessionId: string, pid: number): void {
  const session = loadSession(sessionId);
  if (session) {
    if (!session.backgroundPids.includes(pid)) {
      session.backgroundPids.push(pid);
      saveSession(session);
    }
  }
}

// =============================================================================
// MCP SERVER DETECTION
// =============================================================================

/**
 * Detect running MCP server PIDs
 */
function detectMcpServers(): number[] {
  const pids: number[] = [];
  try {
    const psOutput = execSync(
      'ps aux | grep -E "(workos-mcp|oura-mcp|flow-nexus|ruv-swarm|claude-flow.*mcp)" | grep -v grep',
      { encoding: "utf-8", timeout: 5000 }
    ).trim();

    if (psOutput) {
      const lines = psOutput.split("\n");
      for (const line of lines) {
        const parts = line.split(/\s+/);
        if (parts.length > 1) {
          const pid = parseInt(parts[1], 10);
          if (!isNaN(pid)) {
            pids.push(pid);
          }
        }
      }
    }
  } catch {
    // ps command failed
  }
  return pids;
}

// =============================================================================
// SESSION CLEANUP
// =============================================================================

/**
 * Clean up all processes tracked in a session
 */
export async function cleanupSession(sessionId: string): Promise<{
  killed: number;
  errors: string[];
}> {
  const session = loadSession(sessionId);
  if (!session) {
    return { killed: 0, errors: [`Session ${sessionId} not found`] };
  }

  let killed = 0;
  const errors: string[] = [];

  // Kill agent processes
  for (const pid of session.agentPids) {
    if (isProcessRunning(pid)) {
      try {
        process.kill(pid, "SIGTERM");
        killed++;
      } catch (error) {
        errors.push(`Failed to kill agent PID ${pid}: ${error}`);
      }
    }
  }

  // Kill background processes
  for (const pid of session.backgroundPids) {
    if (isProcessRunning(pid)) {
      try {
        process.kill(pid, "SIGTERM");
        killed++;
      } catch (error) {
        errors.push(`Failed to kill background PID ${pid}: ${error}`);
      }
    }
  }

  // Remove session file
  const filePath = getSessionFilePath(sessionId);
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
  }

  return { killed, errors };
}

/**
 * Clean up orphaned processes from all sessions
 * This is the main cleanup function to call on session end
 */
export async function cleanupAllOrphanedProcesses(): Promise<{
  killed: number;
  errors: string[];
  staleSessions: number;
}> {
  // Clean up stale PID files first
  cleanupStalePidFiles();

  // Find and kill orphaned processes
  const orphans = findOrphanedProcesses();
  let killed = 0;
  const errors: string[] = [];

  for (const orphan of orphans) {
    try {
      process.kill(orphan.pid, "SIGTERM");
      killed++;
    } catch (error) {
      errors.push(`Failed to kill orphan PID ${orphan.pid} (${orphan.name}): ${error}`);
    }
  }

  // Clean up stale session files
  let staleSessions = 0;
  ensureSessionDir();
  try {
    const files = fs.readdirSync(SESSION_DIR);
    for (const file of files) {
      if (file.endsWith(".json")) {
        const filePath = path.join(SESSION_DIR, file);
        const session = JSON.parse(fs.readFileSync(filePath, "utf-8")) as SessionProcessMap;

        // Check if parent process is still running
        if (!isProcessRunning(session.parentPid)) {
          // Session is orphaned, clean it up
          await cleanupSession(session.sessionId);
          staleSessions++;
        }
      }
    }
  } catch {
    // Directory doesn't exist or other error
  }

  return { killed, errors, staleSessions };
}

// =============================================================================
// SESSION LISTING
// =============================================================================

/**
 * List all tracked sessions
 */
export function listSessions(): SessionProcessMap[] {
  ensureSessionDir();
  const sessions: SessionProcessMap[] = [];

  try {
    const files = fs.readdirSync(SESSION_DIR);
    for (const file of files) {
      if (file.endsWith(".json")) {
        const filePath = path.join(SESSION_DIR, file);
        try {
          const content = fs.readFileSync(filePath, "utf-8");
          sessions.push(JSON.parse(content) as SessionProcessMap);
        } catch {
          // Invalid session file
        }
      }
    }
  } catch {
    // Directory doesn't exist
  }

  return sessions;
}

/**
 * Get the most recent active session
 */
export function getCurrentSession(): SessionProcessMap | null {
  const sessions = listSessions();
  if (sessions.length === 0) return null;

  // Sort by start time descending
  sessions.sort((a, b) =>
    new Date(b.startTime).getTime() - new Date(a.startTime).getTime()
  );

  // Return the most recent session whose parent is still running
  for (const session of sessions) {
    if (isProcessRunning(session.parentPid)) {
      return session;
    }
  }

  return sessions[0]; // Return most recent even if parent died
}
