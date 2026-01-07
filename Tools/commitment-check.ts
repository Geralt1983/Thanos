#!/usr/bin/env bun
/**
 * Commitment Check Tool
 * Surface due and overdue commitments from Thanos
 *
 * Usage:
 *   bun commitment-check.ts           # Show due within 48 hours
 *   bun commitment-check.ts --all     # Show all active commitments
 *   bun commitment-check.ts --overdue # Show only overdue
 */

import { readFile } from 'fs/promises';
import { join } from 'path';

const CLAUDE_DIR = join(process.env.HOME!, '.claude');
const COMMITMENTS_FILE = join(CLAUDE_DIR, 'State/Commitments.md');

interface Commitment {
  task: string;
  toWhom: string;
  dueDate: string;
  status: string;
  context?: string;
  isOverdue: boolean;
  isDueSoon: boolean;
}

function parseCommitments(content: string): Commitment[] {
  const commitments: Commitment[] = [];
  const lines = content.split('\n');

  const now = new Date();
  const in48Hours = new Date(now.getTime() + 48 * 60 * 60 * 1000);

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Match: - [ ] Task | Person | Date | Status
    const match = line.match(/- \[( |x)\] (.+?) \| (.+?) \| (.+?) \| (.+)/);
    if (match) {
      const [, checked, task, toWhom, dueDate, status] = match;

      // Skip completed items
      if (checked === 'x') continue;

      // Get context from next line if exists
      let context: string | undefined;
      if (lines[i + 1]?.trim().startsWith('- Context:')) {
        context = lines[i + 1].replace(/^\s*- Context:\s*/, '').trim();
      }

      const parsedDate = parseDate(dueDate);
      const isOverdue = parsedDate ? parsedDate < now : false;
      const isDueSoon = parsedDate ? (parsedDate <= in48Hours && !isOverdue) : false;

      commitments.push({
        task: task.trim(),
        toWhom: toWhom.trim(),
        dueDate: dueDate.trim(),
        status: status.trim(),
        context,
        isOverdue,
        isDueSoon,
      });
    }
  }

  return commitments;
}

function parseDate(dateStr: string): Date | null {
  const lower = dateStr.toLowerCase().trim();

  if (lower === 'today') {
    return new Date();
  }
  if (lower === 'tomorrow') {
    return new Date(Date.now() + 24 * 60 * 60 * 1000);
  }
  if (lower === 'tbd' || lower === 'ongoing' || lower === 'weekly') {
    return null;
  }

  // Try ISO format
  const parsed = new Date(dateStr);
  return isNaN(parsed.getTime()) ? null : parsed;
}

function formatCommitment(c: Commitment, showStatus = true): string {
  let output = `  • ${c.task}`;
  output += `\n    To: ${c.toWhom} | Due: ${c.dueDate}`;
  if (showStatus) {
    output += ` | Status: ${c.status}`;
  }
  if (c.context) {
    output += `\n    Context: ${c.context}`;
  }
  return output;
}

async function main() {
  const args = process.argv.slice(2);
  const showAll = args.includes('--all') || args.includes('-a');
  const showOverdueOnly = args.includes('--overdue') || args.includes('-o');

  console.log('📋 Thanos Commitment Check\n');

  let content: string;
  try {
    content = await readFile(COMMITMENTS_FILE, 'utf-8');
  } catch {
    console.log('❌ Could not read Commitments.md');
    process.exit(1);
  }

  const commitments = parseCommitments(content);

  if (commitments.length === 0) {
    console.log('✅ No active commitments found.');
    return;
  }

  const overdue = commitments.filter(c => c.isOverdue);
  const dueSoon = commitments.filter(c => c.isDueSoon);
  const upcoming = commitments.filter(c => !c.isOverdue && !c.isDueSoon);

  // Show overdue
  if (overdue.length > 0) {
    console.log('🚨 OVERDUE:');
    overdue.forEach(c => console.log(formatCommitment(c)));
    console.log('');
  }

  // Show due soon (unless only showing overdue)
  if (!showOverdueOnly && dueSoon.length > 0) {
    console.log('⚠️  DUE WITHIN 48 HOURS:');
    dueSoon.forEach(c => console.log(formatCommitment(c)));
    console.log('');
  }

  // Show all upcoming (if --all flag)
  if (showAll && upcoming.length > 0) {
    console.log('📅 UPCOMING:');
    upcoming.forEach(c => console.log(formatCommitment(c)));
    console.log('');
  }

  // Summary
  console.log('─────────────────────────────────────');
  console.log(`Total active: ${commitments.length}`);
  console.log(`  Overdue: ${overdue.length}`);
  console.log(`  Due soon: ${dueSoon.length}`);
  console.log(`  Upcoming: ${upcoming.length}`);

  if (overdue.length > 0) {
    console.log('\n⚠️  You have overdue commitments. Address these first!');
  }
}

main().catch(console.error);
