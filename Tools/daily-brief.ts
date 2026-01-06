#!/usr/bin/env bun
/**
 * Daily Brief Generator
 * Generate morning brief from Life OS state files
 *
 * Usage:
 *   bun daily-brief.ts              # Generate brief
 *   bun daily-brief.ts --save       # Save to State/Today.md
 */

import { readFile, writeFile, readdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';

const CLAUDE_DIR = join(process.env.HOME!, '.claude');

interface BriefData {
  date: string;
  focus: string;
  top3: string[];
  dueCommitments: string[];
  waitingFor: string[];
  inboxCount: number;
  weekTheme: string;
  billableTarget: string;
}

async function readStateFile(filename: string): Promise<string> {
  try {
    return await readFile(join(CLAUDE_DIR, 'State', filename), 'utf-8');
  } catch {
    return '';
  }
}

function extractSection(content: string, header: string): string {
  const regex = new RegExp(`## ${header}\\n([\\s\\S]*?)(?=\\n##|$)`, 'i');
  const match = content.match(regex);
  return match ? match[1].trim() : '';
}

function extractListItems(content: string): string[] {
  const items: string[] = [];
  const lines = content.split('\n');

  for (const line of lines) {
    const match = line.match(/^[-*]\s*\[[ x]\]\s*(.+)/);
    if (match && !match[1].includes('[Add')) {
      items.push(match[1].split('|')[0].trim());
    }
  }

  return items;
}

async function gatherBriefData(): Promise<BriefData> {
  const today = new Date().toISOString().split('T')[0];
  const dayName = new Date().toLocaleDateString('en-US', { weekday: 'long' });

  // Read state files
  const currentFocus = await readStateFile('CurrentFocus.md');
  const commitments = await readStateFile('Commitments.md');
  const waitingFor = await readStateFile('WaitingFor.md');
  const thisWeek = await readStateFile('ThisWeek.md');

  // Check inbox
  let inboxCount = 0;
  try {
    const inboxFiles = await readdir(join(CLAUDE_DIR, 'Inbox'));
    inboxCount = inboxFiles.filter(f => !f.startsWith('.') && f !== 'processed').length;
  } catch {}

  // Extract data
  const focusSection = extractSection(currentFocus, 'Right Now');
  const focus = focusSection.split('\n')[0]?.replace(/^\*\*Primary focus\*\*:\s*/, '') || 'Not set';

  const top3Section = extractSection(currentFocus, "Today's Top 3");
  const top3 = extractListItems(top3Section).slice(0, 3);

  // Find due commitments (parse for today/tomorrow or dates within 48h)
  const dueCommitments: string[] = [];
  const commitmentLines = commitments.split('\n');
  const now = new Date();
  const in48h = new Date(now.getTime() + 48 * 60 * 60 * 1000);

  for (const line of commitmentLines) {
    const match = line.match(/- \[ \] (.+?) \| .+? \| (today|tomorrow|\d{4}-\d{2}-\d{2})/i);
    if (match) {
      const [, task, dateStr] = match;
      const lower = dateStr.toLowerCase();

      if (lower === 'today' || lower === 'tomorrow') {
        dueCommitments.push(task.trim());
      } else {
        const dueDate = new Date(dateStr);
        if (!isNaN(dueDate.getTime()) && dueDate <= in48h) {
          dueCommitments.push(task.trim());
        }
      }
    }
  }

  // Extract waiting for items
  const waitingForItems = extractListItems(waitingFor).slice(0, 5);

  // Get week theme
  const weekTheme = extractSection(thisWeek, 'Theme').split('\n')[0]?.replace(/^\*\*Focus\*\*:\s*/, '') || 'Not set';

  return {
    date: `${dayName}, ${today}`,
    focus,
    top3,
    dueCommitments,
    waitingFor: waitingForItems,
    inboxCount,
    weekTheme,
    billableTarget: '15-20 hours',
  };
}

function generateBrief(data: BriefData): string {
  let brief = `
═══════════════════════════════════════════════════════════
                    DAILY BRIEF
                  ${data.date}
═══════════════════════════════════════════════════════════

📋 FOCUS: ${data.focus}

🎯 TODAY'S TOP 3:
${data.top3.length > 0 ? data.top3.map((t, i) => `   ${i + 1}. ${t}`).join('\n') : '   Not set - define your priorities!'}

`;

  if (data.dueCommitments.length > 0) {
    brief += `⚠️  DUE TODAY/SOON:
${data.dueCommitments.map(c => `   • ${c}`).join('\n')}

`;
  }

  if (data.inboxCount > 0) {
    brief += `📥 INBOX: ${data.inboxCount} item(s) waiting

`;
  }

  if (data.waitingFor.length > 0) {
    brief += `⏳ WAITING FOR:
${data.waitingFor.map(w => `   • ${w}`).join('\n')}

`;
  }

  brief += `📅 THIS WEEK: ${data.weekTheme}
💰 BILLABLE TARGET: ${data.billableTarget}

═══════════════════════════════════════════════════════════
        Ready to start? Pick your first task!
═══════════════════════════════════════════════════════════
`;

  return brief;
}

async function main() {
  const args = process.argv.slice(2);
  const shouldSave = args.includes('--save') || args.includes('-s');

  const data = await gatherBriefData();
  const brief = generateBrief(data);

  console.log(brief);

  if (shouldSave) {
    const todayFile = join(CLAUDE_DIR, 'State/Today.md');
    const today = new Date().toISOString().split('T')[0];

    const todayContent = `# Today - ${today}

## Morning Brief
- Energy: [1-10]
- Sleep: [hours]
- Vyvanse: [time taken / not yet]

## Top 3 Priorities
${data.top3.map((t, i) => `${i + 1}. [ ] ${t}`).join('\n')}

## Due Today
${data.dueCommitments.map(c => `- [ ] ${c}`).join('\n') || '- None due today'}

## Schedule
- [ ] [Add time blocks as needed]

## End of Day Review
- [ ] Update Commitments.md
- [ ] Log to History/DailyLogs/
- [ ] Set tomorrow's priorities

---

## Notes
[Capture anything that comes up during the day]

---

*Generated: ${new Date().toISOString()}*
`;

    await writeFile(todayFile, todayContent);
    console.log(`\n✅ Saved to State/Today.md`);
  }
}

main().catch(console.error);
