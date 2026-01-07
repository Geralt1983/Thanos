/**
 * Thanos Memory Retrieval System
 * Vector-based semantic search across all Thanos history
 */

import { ChromaClient, Collection } from 'chromadb';
import OpenAI from 'openai';

const chroma = new ChromaClient();
const openai = new OpenAI();

interface QueryResult {
  content: string;
  metadata: Record<string, any>;
  distance: number;
}

interface QueryOptions {
  collection?: string;
  filter?: Record<string, any>;
  limit?: number;
  dateRange?: { start: string; end: string };
}

/**
 * Query the memory system with natural language
 */
export async function queryMemory(
  query: string,
  options: QueryOptions = {}
): Promise<QueryResult[]> {
  const { collection = 'conversations', filter, limit = 10, dateRange } = options;

  // Generate embedding for query
  const embedding = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: query,
  });

  // Build where clause
  let whereClause = filter || {};
  if (dateRange) {
    whereClause = {
      ...whereClause,
      $and: [
        { date: { $gte: dateRange.start } },
        { date: { $lte: dateRange.end } },
      ],
    };
  }

  // Query collection
  const coll = await chroma.getCollection({ name: collection });
  const results = await coll.query({
    queryEmbeddings: [embedding.data[0].embedding],
    nResults: limit,
    where: Object.keys(whereClause).length > 0 ? whereClause : undefined,
  });

  return results.documents[0].map((doc, i) => ({
    content: doc as string,
    metadata: results.metadatas[0][i] as Record<string, any>,
    distance: results.distances?.[0][i] ?? 0,
  }));
}

/**
 * Add content to memory
 */
export async function addToMemory(
  content: string,
  collection: string,
  metadata: Record<string, any>
): Promise<void> {
  const embedding = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: content,
  });

  const coll = await chroma.getOrCreateCollection({ name: collection });
  await coll.add({
    ids: [`${collection}-${Date.now()}`],
    embeddings: [embedding.data[0].embedding],
    documents: [content],
    metadatas: [{ ...metadata, indexed_at: new Date().toISOString() }],
  });
}

// ============================================
// Convenience Functions
// ============================================

/**
 * Search all conversations
 */
export async function searchConversations(query: string, limit = 10) {
  return queryMemory(query, { collection: 'conversations', limit });
}

/**
 * Search commitments
 */
export async function searchCommitments(query: string, limit = 10) {
  return queryMemory(query, { collection: 'commitments', limit });
}

/**
 * Search by client name
 */
export async function searchByClient(client: string, query: string) {
  return queryMemory(query, {
    collection: 'client_interactions',
    filter: { client },
  });
}

/**
 * Search within a date range
 */
export async function searchByDateRange(query: string, start: string, end: string) {
  return queryMemory(query, { dateRange: { start, end } });
}

/**
 * Find patterns in a domain over time
 */
export async function findPatterns(domain: string, timeframeDays = 30) {
  const end = new Date().toISOString();
  const start = new Date(Date.now() - timeframeDays * 24 * 60 * 60 * 1000).toISOString();

  return queryMemory(`patterns trends recurring themes in ${domain}`, {
    collection: 'daily_logs',
    filter: { domain },
    dateRange: { start, end },
    limit: 50,
  });
}

/**
 * Search decisions with alternatives
 */
export async function searchDecisions(query: string, domain?: string) {
  return queryMemory(query, {
    collection: 'decisions',
    filter: domain ? { domain } : undefined,
    limit: 20,
  });
}

/**
 * Get recent learnings
 */
export async function getRecentLearnings(domain: string, days = 7) {
  const end = new Date().toISOString();
  const start = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();

  return queryMemory('learnings insights', {
    collection: 'learnings',
    filter: { domain },
    dateRange: { start, end },
    limit: 20,
  });
}

// ============================================
// Initialization
// ============================================

/**
 * Initialize all collections
 */
export async function initializeMemory(): Promise<void> {
  const collections = [
    'conversations',
    'commitments',
    'decisions',
    'daily_logs',
    'learnings',
    'client_interactions'
  ];

  for (const name of collections) {
    await chroma.getOrCreateCollection({ name });
  }

  console.log('✅ Memory system initialized');
}

/**
 * Get memory stats
 */
export async function getMemoryStats(): Promise<Record<string, number>> {
  const collections = [
    'conversations',
    'commitments',
    'decisions',
    'daily_logs',
    'learnings',
    'client_interactions'
  ];

  const stats: Record<string, number> = {};

  for (const name of collections) {
    try {
      const coll = await chroma.getCollection({ name });
      const count = await coll.count();
      stats[name] = count;
    } catch {
      stats[name] = 0;
    }
  }

  return stats;
}
