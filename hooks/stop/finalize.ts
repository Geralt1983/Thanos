/**
 * Thanos Session Stop Hook
 * Runs at the end of each Claude Code session
 */

import { writeFile, appendFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';
import { cleanupAllOrphanedProcesses } from '../../src/utils/session-lifecycle.js';

const CLAUDE_DIR = join(process.env.HOME!, '.claude');

interface SessionData {
  transcript: string;
  startTime: string;
  endTime: string;
  topic: string;
  commitmentsMade: string[];
  decisionsRecorded: string[];
  learnings: string[];
}

export default async function sessionStop(data: SessionData): Promise<{ sessionId: string; summary: string }> {
  const sessionId = `${data.startTime.split('T')[0]}-${Date.now()}-${data.topic.replace(/\s+/g, '-').toLowerCase().slice(0, 30)}`;
  const sessionDir = join(CLAUDE_DIR, 'History/Sessions', sessionId);

  // Ensure session directory exists
  if (!existsSync(sessionDir)) {
    await mkdir(sessionDir, { recursive: true });
  }

  // 1. Save full transcript
  await writeFile(
    join(sessionDir, 'transcript.md'),
    `# Session: ${data.topic}

**Start:** ${data.startTime}
**End:** ${data.endTime}
**Session ID:** ${sessionId}

---

${data.transcript}`
  );

  // 2. Save context snapshot
  await writeFile(
    join(sessionDir, 'context-snapshot.md'),
    `# Context Snapshot

## Commitments Made
${data.commitmentsMade.length > 0 ? data.commitmentsMade.map(c => `- ${c}`).join('\n') : 'None'}

## Decisions Recorded
${data.decisionsRecorded.length > 0 ? data.decisionsRecorded.map(d => `- ${d}`).join('\n') : 'None'}

## Learnings
${data.learnings.length > 0 ? data.learnings.map(l => `- ${l}`).join('\n') : 'None'}

## Metadata
- Duration: ${calculateDuration(data.startTime, data.endTime)}
- Topic: ${data.topic}
`
  );

  // 3. Record new commitments to State
  if (data.commitmentsMade.length > 0) {
    const commitmentFile = join(CLAUDE_DIR, 'State/Commitments.md');
    const newCommitments = data.commitmentsMade
      .map(c => `- [ ] ${c} | [DATE] | Not Started\n  - Added: ${data.endTime} (Session: ${sessionId})`)
      .join('\n');

    try {
      await appendFile(commitmentFile, `\n${newCommitments}\n`);
    } catch (e) {
      console.error('Failed to append commitments:', e);
    }
  }

  // 4. Update daily log
  const today = data.endTime.split('T')[0];
  const dailyLogPath = join(CLAUDE_DIR, `History/DailyLogs/${today}.md`);

  const logEntry = `
### Session: ${data.topic} (${new Date(data.endTime).toLocaleTimeString()})
- **Session ID:** ${sessionId}
${data.learnings.length > 0 ? `- **Learnings:** ${data.learnings.join(', ')}` : ''}
${data.commitmentsMade.length > 0 ? `- **Commitments:** ${data.commitmentsMade.join(', ')}` : ''}
${data.decisionsRecorded.length > 0 ? `- **Decisions:** ${data.decisionsRecorded.join(', ')}` : ''}
`;

  try {
    // Check if daily log exists, create if not
    if (!existsSync(dailyLogPath)) {
      await writeFile(dailyLogPath, `# Daily Log - ${today}\n`);
    }
    await appendFile(dailyLogPath, logEntry);
  } catch (e) {
    console.error('Failed to update daily log:', e);
  }

  // 5. Save learnings to domain-specific locations
  if (data.learnings.length > 0) {
    const learningsDir = join(CLAUDE_DIR, 'History/Learnings');
    const generalLearningsFile = join(learningsDir, 'general.md');

    const learningsEntry = `
## ${data.endTime.split('T')[0]} - ${data.topic}
${data.learnings.map(l => `- ${l}`).join('\n')}
`;

    try {
      if (!existsSync(generalLearningsFile)) {
        await writeFile(generalLearningsFile, '# Learnings Archive\n');
      }
      await appendFile(generalLearningsFile, learningsEntry);
    } catch (e) {
      console.error('Failed to save learnings:', e);
    }
  }

  // 6. Generate summary
  const summary = generateSummary(data);
  console.log(`\n🎯 SESSION COMPLETE: ${summary}`);
  console.log(`📁 Session saved: ${sessionId}`);

  // 7. Clean up orphaned processes (Task agents, duplicate daemons, etc.)
  try {
    const cleanup = await cleanupAllOrphanedProcesses();
    if (cleanup.killed > 0) {
      console.log(`🧹 Cleaned up ${cleanup.killed} orphaned process${cleanup.killed > 1 ? 'es' : ''}`);
    }
    if (cleanup.staleSessions > 0) {
      console.log(`🧹 Removed ${cleanup.staleSessions} stale session${cleanup.staleSessions > 1 ? 's' : ''}`);
    }
    if (cleanup.errors.length > 0) {
      console.error(`⚠️  Cleanup errors: ${cleanup.errors.join(', ')}`);
    }
  } catch (e) {
    console.error('Failed to cleanup orphaned processes:', e);
  }

  return { sessionId, summary };
}

/**
 * Calculate session duration
 */
function calculateDuration(start: string, end: string): string {
  const startDate = new Date(start);
  const endDate = new Date(end);
  const diffMs = endDate.getTime() - startDate.getTime();
  const diffMins = Math.round(diffMs / 60000);

  if (diffMins < 60) {
    return `${diffMins} minutes`;
  }
  const hours = Math.floor(diffMins / 60);
  const mins = diffMins % 60;
  return `${hours}h ${mins}m`;
}

/**
 * Generate session summary
 */
function generateSummary(data: SessionData): string {
  const parts: string[] = [];

  if (data.commitmentsMade.length > 0) {
    parts.push(`${data.commitmentsMade.length} commitment${data.commitmentsMade.length > 1 ? 's' : ''} captured`);
  }
  if (data.learnings.length > 0) {
    parts.push(`${data.learnings.length} learning${data.learnings.length > 1 ? 's' : ''} recorded`);
  }
  if (data.decisionsRecorded.length > 0) {
    parts.push(`${data.decisionsRecorded.length} decision${data.decisionsRecorded.length > 1 ? 's' : ''} logged`);
  }

  if (parts.length === 0) {
    parts.push('Session logged');
  }

  return parts.join(', ');
}

// Export for use as hook
export { sessionStop };
