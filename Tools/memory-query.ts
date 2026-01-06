#!/usr/bin/env bun
/**
 * Memory Query Tool
 * Query the Life OS vector memory system from command line
 *
 * Usage:
 *   bun memory-query.ts "what did I decide about X"
 *   bun memory-query.ts --collection commitments "ashley"
 *   bun memory-query.ts --days 7 "energy patterns"
 */

import { queryMemory, searchConversations, searchCommitments, searchByDateRange, getMemoryStats } from '../Memory/retrieval';

interface Args {
  query: string;
  collection?: string;
  days?: number;
  limit?: number;
  stats?: boolean;
}

function parseArgs(): Args {
  const args = process.argv.slice(2);
  const result: Args = { query: '' };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--collection' || arg === '-c') {
      result.collection = args[++i];
    } else if (arg === '--days' || arg === '-d') {
      result.days = parseInt(args[++i], 10);
    } else if (arg === '--limit' || arg === '-l') {
      result.limit = parseInt(args[++i], 10);
    } else if (arg === '--stats' || arg === '-s') {
      result.stats = true;
    } else if (!arg.startsWith('-')) {
      result.query = arg;
    }
  }

  return result;
}

async function main() {
  const args = parseArgs();

  // Show stats if requested
  if (args.stats) {
    console.log('📊 Memory Stats:\n');
    const stats = await getMemoryStats();
    for (const [collection, count] of Object.entries(stats)) {
      console.log(`  ${collection}: ${count} items`);
    }
    return;
  }

  if (!args.query) {
    console.log(`
Memory Query Tool - Search your Life OS memory

Usage:
  bun memory-query.ts "your query here"
  bun memory-query.ts --collection commitments "query"
  bun memory-query.ts --days 7 "query"
  bun memory-query.ts --stats

Options:
  --collection, -c  Search specific collection (conversations, commitments, decisions, daily_logs, learnings, client_interactions)
  --days, -d        Limit to last N days
  --limit, -l       Max results (default: 10)
  --stats, -s       Show memory statistics
`);
    process.exit(1);
  }

  console.log(`🔍 Searching: "${args.query}"\n`);

  let results;

  if (args.days) {
    const end = new Date().toISOString();
    const start = new Date(Date.now() - args.days * 24 * 60 * 60 * 1000).toISOString();
    results = await searchByDateRange(args.query, start, end);
  } else if (args.collection) {
    results = await queryMemory(args.query, {
      collection: args.collection,
      limit: args.limit || 10,
    });
  } else {
    results = await searchConversations(args.query, args.limit || 10);
  }

  if (results.length === 0) {
    console.log('No results found.');
    return;
  }

  console.log(`Found ${results.length} results:\n`);

  results.forEach((result, i) => {
    console.log(`─────────────────────────────────────`);
    console.log(`[${i + 1}] Distance: ${result.distance.toFixed(4)}`);
    if (result.metadata.date) {
      console.log(`    Date: ${result.metadata.date}`);
    }
    if (result.metadata.topic) {
      console.log(`    Topic: ${result.metadata.topic}`);
    }
    console.log(`\n${result.content.slice(0, 500)}${result.content.length > 500 ? '...' : ''}\n`);
  });
}

main().catch(console.error);
