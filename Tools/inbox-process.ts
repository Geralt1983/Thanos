#!/usr/bin/env bun
/**
 * Inbox Processing Tool
 * Process items in the Thanos inbox
 *
 * Usage:
 *   bun inbox-process.ts          # List inbox items
 *   bun inbox-process.ts --auto   # Auto-categorize items
 */

import { readdir, readFile, rename, mkdir } from 'fs/promises';
import { join, basename } from 'path';
import { existsSync } from 'fs';

const CLAUDE_DIR = join(process.env.HOME!, '.claude');
const INBOX_DIR = join(CLAUDE_DIR, 'Inbox');
const PROCESSED_DIR = join(CLAUDE_DIR, 'History/Inbox/processed');

interface InboxItem {
  filename: string;
  path: string;
  content: string;
  created: Date;
}

async function getInboxItems(): Promise<InboxItem[]> {
  const items: InboxItem[] = [];

  try {
    const files = await readdir(INBOX_DIR);

    for (const file of files) {
      if (file.startsWith('.') || file === 'processed') continue;

      const path = join(INBOX_DIR, file);
      const content = await readFile(path, 'utf-8');
      const stats = await Bun.file(path).stat();

      items.push({
        filename: file,
        path,
        content,
        created: stats?.mtime || new Date(),
      });
    }
  } catch (e) {
    console.error('Error reading inbox:', e);
  }

  return items.sort((a, b) => a.created.getTime() - b.created.getTime());
}

function categorizeItem(content: string): string {
  const lower = content.toLowerCase();

  // Task indicators
  if (lower.includes('todo') || lower.includes('need to') || lower.includes('should') ||
      lower.includes('must') || lower.includes('deadline') || lower.includes('by ')) {
    return 'task';
  }

  // Commitment indicators
  if (lower.includes('promise') || lower.includes('committed') || lower.includes('will do') ||
      lower.includes('i will') || lower.includes('agreed to')) {
    return 'commitment';
  }

  // Question indicators
  if (content.includes('?') || lower.includes('wondering') || lower.includes('question')) {
    return 'question';
  }

  // Idea indicators
  if (lower.includes('idea') || lower.includes('maybe') || lower.includes('could') ||
      lower.includes('what if') || lower.includes('might')) {
    return 'idea';
  }

  // Client-related
  if (lower.includes('memphis') || lower.includes('raleigh') || lower.includes('orlando') ||
      lower.includes('nova') || lower.includes('baptist') || lower.includes('client')) {
    return 'client';
  }

  return 'reference';
}

async function moveToProcessed(item: InboxItem): Promise<void> {
  const month = item.created.toISOString().slice(0, 7); // YYYY-MM
  const monthDir = join(PROCESSED_DIR, month);

  if (!existsSync(monthDir)) {
    await mkdir(monthDir, { recursive: true });
  }

  const destPath = join(monthDir, item.filename);
  await rename(item.path, destPath);
}

async function main() {
  const args = process.argv.slice(2);
  const autoMode = args.includes('--auto') || args.includes('-a');

  console.log('📥 Thanos Inbox Processor\n');

  const items = await getInboxItems();

  if (items.length === 0) {
    console.log('✅ Inbox is empty!');
    return;
  }

  console.log(`Found ${items.length} item(s) to process:\n`);

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const category = categorizeItem(item.content);

    console.log(`─────────────────────────────────────`);
    console.log(`[${i + 1}/${items.length}] ${item.filename}`);
    console.log(`    Created: ${item.created.toLocaleDateString()}`);
    console.log(`    Category: ${category}`);
    console.log(`\n    Content:`);
    console.log(`    ${item.content.slice(0, 200).split('\n').join('\n    ')}${item.content.length > 200 ? '...' : ''}`);
    console.log('');

    if (autoMode) {
      console.log(`    → Auto-categorized as: ${category}`);
      console.log(`    → Action needed: Add to appropriate State/ or Context/ file`);
    } else {
      console.log(`    Suggested action based on category "${category}":`);
      switch (category) {
        case 'task':
        case 'commitment':
          console.log('    → Add to State/Commitments.md');
          break;
        case 'question':
          console.log('    → Answer and archive, or escalate');
          break;
        case 'idea':
          console.log('    → Add to Context/Projects/ or note for later');
          break;
        case 'client':
          console.log('    → Add to relevant Context/Clients/*.md');
          break;
        default:
          console.log('    → File in appropriate Context/ location');
      }
    }
    console.log('');
  }

  console.log(`─────────────────────────────────────`);
  console.log(`\nTo process items:`);
  console.log(`1. Review each item above`);
  console.log(`2. Add to appropriate State/ or Context/ file`);
  console.log(`3. Run: bun inbox-process.ts --archive to move to processed`);

  if (args.includes('--archive')) {
    console.log('\n📦 Archiving all items...');
    for (const item of items) {
      await moveToProcessed(item);
      console.log(`    ✓ Archived: ${item.filename}`);
    }
    console.log('\n✅ All items archived to History/Inbox/processed/');
  }
}

main().catch(console.error);
