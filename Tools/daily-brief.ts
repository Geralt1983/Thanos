#!/usr/bin/env bun
/**
 * Daily Brief Generator
 * Generate morning brief from Thanos state files
 *
 * Usage:
 *   bun daily-brief.ts              # Generate brief
 *   bun daily-brief.ts --save       # Save to State/Today.md
 */

import { readFile, writeFile, readdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';
import { spawnSync } from 'child_process';

const CLAUDE_DIR = join(process.env.HOME!, '.claude');

interface CalendarEvent {
  summary: string;
  start: string;
  end: string;
  is_all_day: boolean;
  location: string;
  attendees_count: number;
}

interface CalendarData {
  success: boolean;
  events: CalendarEvent[];
  upcoming: CalendarEvent[];
  focus_blocks: CalendarEvent[];
  summary?: {
    total_events?: number;
    meeting_minutes?: number;
    free_minutes?: number;
  };
  error?: string;
}

interface BriefData {
  date: string;
  focus: string;
  top3: string[];
  dueCommitments: string[];
  waitingFor: string[];
  inboxCount: number;
  weekTheme: string;
  billableTarget: string;
  calendar: CalendarData;
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

async function fetchCalendarEvents(): Promise<CalendarData> {
  try {
    // Get the directory of the current script
    const scriptDir = new URL('.', import.meta.url).pathname;
    const calendarScript = join(scriptDir, 'get-calendar-events.py');

    // Call the Python script to fetch calendar events
    const result = spawnSync('python3', [calendarScript], {
      encoding: 'utf-8',
      timeout: 10000, // 10 second timeout
    });

    if (result.error) {
      return {
        success: false,
        events: [],
        upcoming: [],
        focus_blocks: [],
        error: `Failed to execute calendar script: ${result.error.message}`,
      };
    }

    if (result.status !== 0) {
      return {
        success: false,
        events: [],
        upcoming: [],
        focus_blocks: [],
        error: `Calendar script exited with code ${result.status}`,
      };
    }

    // Parse JSON output
    const data = JSON.parse(result.stdout);
    return data;
  } catch (error) {
    // Gracefully handle errors - calendar integration is optional
    return {
      success: false,
      events: [],
      upcoming: [],
      focus_blocks: [],
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
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

  // Fetch calendar events
  const calendar = await fetchCalendarEvents();

  return {
    date: `${dayName}, ${today}`,
    focus,
    top3,
    dueCommitments,
    waitingFor: waitingForItems,
    inboxCount,
    weekTheme,
    billableTarget: '15-20 hours',
    calendar,
  };
}

function formatTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  } catch {
    return isoString;
  }
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

  // Calendar section - show if available
  if (data.calendar.success && data.calendar.events.length > 0) {
    const { events, upcoming, focus_blocks, summary } = data.calendar;

    brief += `📆 CALENDAR TODAY:\n`;

    // Show summary stats if available
    if (summary && summary.total_events !== undefined) {
      brief += `   ${summary.total_events} event(s)`;
      if (summary.meeting_minutes !== undefined && summary.free_minutes !== undefined) {
        const meetingHours = Math.floor(summary.meeting_minutes / 60);
        const meetingMins = summary.meeting_minutes % 60;
        const freeHours = Math.floor(summary.free_minutes / 60);
        brief += ` • ${meetingHours}h${meetingMins}m busy, ${freeHours}h free`;
      }
      brief += '\n';
    }

    // Show upcoming events (within 2 hours)
    if (upcoming.length > 0) {
      brief += `\n   🔔 UPCOMING (next 2 hours):\n`;
      upcoming.forEach(event => {
        const time = formatTime(event.start);
        brief += `      • ${time} - ${event.summary}`;
        if (event.location) {
          brief += ` (${event.location})`;
        }
        brief += '\n';
      });
    }

    // Show focus blocks
    if (focus_blocks.length > 0) {
      brief += `\n   🎯 FOCUS BLOCKS:\n`;
      focus_blocks.forEach(event => {
        const time = event.is_all_day ? 'All day' : formatTime(event.start);
        brief += `      • ${time} - ${event.summary}\n`;
      });
    }

    brief += '\n';
  }

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

    // Generate calendar schedule section
    let calendarSection = '';
    if (data.calendar.success && data.calendar.events.length > 0) {
      calendarSection = '\n## Calendar Events\n';

      const timedEvents = data.calendar.events.filter(e => !e.is_all_day);
      const allDayEvents = data.calendar.events.filter(e => e.is_all_day);

      // Sort timed events by start time
      timedEvents.sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());

      if (timedEvents.length > 0) {
        timedEvents.forEach(event => {
          const start = formatTime(event.start);
          const end = formatTime(event.end);
          calendarSection += `- ${start} - ${end}: ${event.summary}`;
          if (event.location) {
            calendarSection += ` (${event.location})`;
          }
          calendarSection += '\n';
        });
      }

      if (allDayEvents.length > 0) {
        calendarSection += '\n**All-day:**\n';
        allDayEvents.forEach(event => {
          calendarSection += `- ${event.summary}\n`;
        });
      }
    }

    const todayContent = `# Today - ${today}

## Morning Brief
- Energy: [1-10]
- Sleep: [hours]
- Vyvanse: [time taken / not yet]

## Top 3 Priorities
${data.top3.map((t, i) => `${i + 1}. [ ] ${t}`).join('\n')}

## Due Today
${data.dueCommitments.map(c => `- [ ] ${c}`).join('\n') || '- None due today'}
${calendarSection}
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
