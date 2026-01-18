/**
 * Thanos Session Start Hook
 * Runs at the beginning of each Claude Code session
 */

import { readFile, readdir } from 'fs/promises';
import { join } from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import {
  cleanupStalePidFiles,
  findOrphanedProcesses,
  cleanupOrphanedProcesses,
} from '../../src/utils/process-manager.js';
import { trackSessionStart } from '../../src/utils/session-lifecycle.js';

const execAsync = promisify(exec);
const CLAUDE_DIR = join(process.env.HOME!, '.claude');
const PROJECT_ROOT = join(process.env.HOME!, 'Projects/Thanos');

/**
 * Get quick status from unified state store via Python status command
 */
async function quickStatus(): Promise<string | null> {
  try {
    const { stdout } = await execAsync(
      `cd "${PROJECT_ROOT}" && python3 -m commands.status --brief`,
      { timeout: 10000 }
    );
    return stdout.trim();
  } catch (error) {
    // Graceful fallback - status command may not be available
    return null;
  }
}

interface SessionStartResult {
  hasInbox: boolean;
  inboxCount: number;
  dueCommitments: string[];
  currentFocus: string;
  commitmentCheck?: CommitmentCheckResult;
}

interface CommitmentCheckResult {
  prompts: Array<{
    commitment_id: string;
    commitment_title: string;
    reason: string;
    urgency: number;
    days_overdue?: number;
    streak_count?: number;
  }>;
  total_active: number;
  overdue_count: number;
  due_today_count: number;
  habit_reminder_count: number;
  in_quiet_hours: boolean;
  check_timestamp: string;
}

export default async function sessionStart(): Promise<SessionStartResult> {
  console.log('🚀 Thanos initializing...\n');

  // 0. Startup cleanup - remove stale PIDs and orphaned processes
  try {
    const stalePids = cleanupStalePidFiles();
    if (stalePids > 0) {
      console.log(`🧹 Cleaned up ${stalePids} stale PID file${stalePids > 1 ? 's' : ''}`);
    }

    const orphans = findOrphanedProcesses();
    if (orphans.length > 0) {
      console.log(`🔍 Found ${orphans.length} orphaned process${orphans.length > 1 ? 'es' : ''}:`);
      orphans.forEach(o => console.log(`   - PID ${o.pid}: ${o.name}`));
      const cleanup = cleanupOrphanedProcesses();
      if (cleanup.killed > 0) {
        console.log(`🧹 Killed ${cleanup.killed} orphaned process${cleanup.killed > 1 ? 'es' : ''}`);
      }
    }

    // Track this session
    await trackSessionStart();
  } catch (e) {
    // Don't fail startup if cleanup fails
    console.error('⚠️  Startup cleanup error:', e);
  }

  // 1. Load current state
  let currentFocus = '';
  let commitments = '';
  let today = '';

  try {
    currentFocus = await readFile(join(CLAUDE_DIR, 'State/CurrentFocus.md'), 'utf-8');
  } catch { currentFocus = 'No focus set'; }

  try {
    commitments = await readFile(join(CLAUDE_DIR, 'State/Commitments.md'), 'utf-8');
  } catch { commitments = ''; }

  try {
    today = await readFile(join(CLAUDE_DIR, 'State/Today.md'), 'utf-8');
  } catch { today = ''; }

  // 2. Check inbox for new items
  const inboxPath = join(CLAUDE_DIR, 'Inbox');
  let inboxItems: string[] = [];
  try {
    inboxItems = await readdir(inboxPath);
    // Filter out hidden files and processed folder
    inboxItems = inboxItems.filter(f => !f.startsWith('.') && f !== 'processed');
  } catch {
    inboxItems = [];
  }
  const hasInbox = inboxItems.length > 0;

  // 3. Check for due commitments using the enhanced commitment system
  let commitmentCheckResult: CommitmentCheckResult | null = null;
  let dueCommitments: string[] = [];

  commitmentCheckResult = await checkCommitments();

  // Fallback to old method if new system not available
  if (!commitmentCheckResult) {
    dueCommitments = extractDueCommitments(commitments);
  }

  // 4. Generate session brief
  console.log('═══════════════════════════════════════');
  console.log('         THANOS SESSION START          ');
  console.log('═══════════════════════════════════════\n');

  // Quick status from unified state store
  try {
    const statusOutput = await quickStatus();
    if (statusOutput) {
      console.log(statusOutput);
    }
  } catch (e) {
    // Graceful fallback - don't break startup
  }

  if (hasInbox) {
    console.log(`📥 INBOX: ${inboxItems.length} items waiting to process`);
    inboxItems.forEach(item => console.log(`   - ${item}`));
    console.log('');
  }

  // Display commitment check results (new system or fallback)
  if (commitmentCheckResult && commitmentCheckResult.prompts.length > 0) {
    displayCommitmentPrompts(commitmentCheckResult);
  } else if (dueCommitments.length > 0) {
    console.log('⚠️  DUE SOON:');
    dueCommitments.forEach(c => console.log(`   - ${c}`));
    console.log('');
  }

  const focusSection = extractSection(currentFocus, 'Right Now');
  console.log('📋 CURRENT FOCUS:');
  console.log(focusSection || '   No focus set');
  console.log('');

  const top3 = extractSection(currentFocus, "Today's Top 3");
  console.log("✅ TODAY'S TOP 3:");
  console.log(top3 || '   No priorities set');
  console.log('');

  console.log('═══════════════════════════════════════\n');

  return {
    hasInbox,
    inboxCount: inboxItems.length,
    dueCommitments: commitmentCheckResult
      ? commitmentCheckResult.prompts.map(p => p.commitment_title)
      : dueCommitments,
    currentFocus: focusSection,
    commitmentCheck: commitmentCheckResult || undefined,
  };
}

/**
 * Extract commitments due within 48 hours
 */
function extractDueCommitments(content: string): string[] {
  const lines = content.split('\n');
  const due: string[] = [];
  const now = new Date();
  const in48Hours = new Date(now.getTime() + 48 * 60 * 60 * 1000);

  for (const line of lines) {
    // Look for lines with dates that might be due soon
    // Format: - [ ] Task | Person | DATE | Status
    const match = line.match(/- \[ \] (.+?) \| .+? \| (\d{4}-\d{2}-\d{2}|\w+day|today|tomorrow)/i);
    if (match) {
      const [, task, dateStr] = match;
      const dueDate = parseDate(dateStr);
      if (dueDate && dueDate <= in48Hours) {
        due.push(`${task} (${dateStr})`);
      }
    }
  }

  return due;
}

/**
 * Parse various date formats
 */
function parseDate(dateStr: string): Date | null {
  const lower = dateStr.toLowerCase();
  const now = new Date();

  if (lower === 'today') {
    return now;
  }
  if (lower === 'tomorrow') {
    return new Date(now.getTime() + 24 * 60 * 60 * 1000);
  }
  if (lower.includes('day')) {
    // Handle "Monday", "Tuesday", etc.
    return null; // Would need more logic
  }

  // Try ISO date format
  const parsed = new Date(dateStr);
  return isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * Extract a section from markdown by header
 */
function extractSection(content: string, header: string): string {
  const regex = new RegExp(`## ${header}\\n([\\s\\S]*?)(?=\\n##|$)`, 'i');
  const match = content.match(regex);
  return match ? match[1].trim() : '';
}

/**
 * Check commitments using the Python commitment_check tool
 * Returns null if check fails (graceful fallback)
 */
async function checkCommitments(): Promise<CommitmentCheckResult | null> {
  try {
    // Try multiple potential paths for the Tools directory
    const toolsPaths = [
      join(process.env.HOME!, 'Projects/Thanos/Tools'),
      join(CLAUDE_DIR, '../Tools'),
      join(process.cwd(), 'Tools'),
    ];

    let toolsPath = '';
    for (const path of toolsPaths) {
      try {
        await readFile(join(path, 'commitment_check.py'));
        toolsPath = path;
        break;
      } catch {
        continue;
      }
    }

    if (!toolsPath) {
      return null; // commitment_check.py not found
    }

    const command = `cd "${toolsPath}" && python3 commitment_check.py --json --dry-run`;
    const { stdout } = await execAsync(command, { timeout: 5000 });
    const result = JSON.parse(stdout) as CommitmentCheckResult;

    return result;
  } catch (error) {
    // Graceful fallback - don't block session start if commitment check fails
    return null;
  }
}

/**
 * Format and display commitment prompts
 */
function displayCommitmentPrompts(result: CommitmentCheckResult): void {
  const overdue = result.prompts.filter(p => p.reason === 'overdue');
  const dueToday = result.prompts.filter(p => p.reason === 'due_today');

  if (overdue.length > 0) {
    console.log('🚨 OVERDUE COMMITMENTS:');
    overdue.forEach(p => {
      const days = p.days_overdue || 0;
      const emoji = days > 7 ? '🚨' : '⚠️';
      console.log(`   ${emoji} ${p.commitment_title} (${days} day${days > 1 ? 's' : ''})`);
    });
    console.log('');
  }

  if (dueToday.length > 0) {
    console.log('📅 DUE TODAY:');
    dueToday.forEach(p => {
      console.log(`   📅 ${p.commitment_title}`);
    });
    console.log('');
  }
}

// Run if executed directly
if (import.meta.main) {
  sessionStart();
}
