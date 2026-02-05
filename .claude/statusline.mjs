/**
 * Agentic Flow Statusline for Claude Code
 * Shows model, tokens, cost, swarm status, agents, and memory usage
 */

import { execSync } from 'child_process';

// Cache for expensive operations
let lastSwarmCheck = 0;
let cachedSwarmStatus = null;
let cachedAgentCounts = null;
const CACHE_TTL = 5000; // 5 seconds

/**
 * Get agent/swarm counts from running processes
 */
function getAgentCounts() {
  const now = Date.now();
  if (cachedAgentCounts && (now - lastSwarmCheck) < CACHE_TTL) {
    return cachedAgentCounts;
  }

  try {
    // Count Claude subagent processes (resumed agents = subagents)
    const psResult = execSync('ps aux | grep -c "claude.*--resume" 2>/dev/null || echo "0"', {
      encoding: 'utf-8',
      timeout: 2000
    }).trim();

    // Subtract 1 for the grep process itself
    const subagents = Math.max(0, parseInt(psResult, 10) - 1);

    // Count main Claude sessions (interactive terminals)
    const sessionsResult = execSync('ps aux | grep -E "claude.*--dangerously-skip" | grep -v grep | wc -l 2>/dev/null || echo "0"', {
      encoding: 'utf-8',
      timeout: 2000
    }).trim();

    const sessions = parseInt(sessionsResult, 10) || 0;

    cachedAgentCounts = { subagents, sessions };
    return cachedAgentCounts;
  } catch {
    cachedAgentCounts = { subagents: 0, sessions: 0 };
    return cachedAgentCounts;
  }
}

/**
 * Get swarm status (cached)
 */
function getSwarmStatus() {
  const now = Date.now();
  if (cachedSwarmStatus && (now - lastSwarmCheck) < CACHE_TTL) {
    return cachedSwarmStatus;
  }

  try {
    const result = execSync('npx agentic-flow@alpha mcp status 2>/dev/null || echo "idle"', {
      encoding: 'utf-8',
      timeout: 2000
    }).trim();

    cachedSwarmStatus = result.includes('running') ? '🐝' : '⚡';
    lastSwarmCheck = now;
    return cachedSwarmStatus;
  } catch {
    cachedSwarmStatus = '⚡';
    lastSwarmCheck = now;
    return cachedSwarmStatus;
  }
}

/**
 * Format token count
 */
function formatTokens(tokens) {
  if (tokens >= 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`;
  }
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}K`;
  }
  return String(tokens);
}

/**
 * Format cost
 */
function formatCost(cost) {
  if (cost >= 1) {
    return `$${cost.toFixed(2)}`;
  }
  return `$${cost.toFixed(4)}`;
}

/**
 * Main statusline export
 */
export default function statusline(context) {
  const parts = [];

  // Agentic Flow indicator
  parts.push('🤖');

  // Model name (shortened)
  if (context.model) {
    const model = context.model
      .replace('claude-', '')
      .replace('-20250514', '')
      .replace('sonnet-4', 'S4')
      .replace('opus-4', 'O4')
      .replace('haiku-3.5', 'H3.5');
    parts.push(model);
  }

  // Token usage
  if (context.inputTokens !== undefined || context.outputTokens !== undefined) {
    const input = formatTokens(context.inputTokens || 0);
    const output = formatTokens(context.outputTokens || 0);
    parts.push(`↑${input} ↓${output}`);
  }

  // Cost
  if (context.totalCost !== undefined && context.totalCost > 0) {
    parts.push(formatCost(context.totalCost));
  }

  // Swarm/MCP status indicator
  parts.push(getSwarmStatus());

  // Agent counts
  const agents = getAgentCounts();
  if (agents.subagents > 0 || agents.sessions > 1) {
    const agentInfo = [];
    if (agents.sessions > 0) agentInfo.push(`${agents.sessions}🖥️`);
    if (agents.subagents > 0) agentInfo.push(`${agents.subagents}🤖`);
    parts.push(agentInfo.join(' '));
  }

  // Session time
  if (context.sessionStartTime) {
    const elapsed = Math.floor((Date.now() - context.sessionStartTime) / 1000);
    const mins = Math.floor(elapsed / 60);
    const secs = elapsed % 60;
    if (mins > 0) {
      parts.push(`${mins}m${secs}s`);
    } else {
      parts.push(`${secs}s`);
    }
  }

  return parts.join(' │ ');
}
