/**
 * Complexity Router Hook
 * 
 * STUB: Waiting for OpenClaw to implement `message:received` event.
 * Once available, this will auto-escalate models based on message complexity.
 */

// Complexity keywords and their weights
const OPUS_TRIGGERS = [
  'analyze', 'architecture', 'design', 'strategic', 'deep dive',
  'think hard', 'really think', 'complex', 'thorough', 'comprehensive',
  'system design', 'trade-offs', 'evaluate options', 'trade-off',
  'multi-step', 'planning', 'strategy', 'optimize', 'scalability'
];

const SONNET_TRIGGERS = [
  'code', 'debug', 'refactor', 'implement', 'explain',
  'how does', 'build', 'create', 'fix', 'error',
  'function', 'class', 'api', 'integration'
];

const HAIKU_TRIGGERS = [
  'yes', 'no', 'quick', 'simple', 'just',
  'status', 'check', 'confirm', 'ok', 'thanks'
];

export interface ComplexityResult {
  score: number;
  model: 'haiku' | 'sonnet' | 'opus';
  triggers: string[];
}

export function scoreComplexity(message: string): ComplexityResult {
  const lower = message.toLowerCase();
  const triggers: string[] = [];
  let score = 0.3; // Default to low-medium
  
  // Check for Haiku triggers (fast exit)
  for (const trigger of HAIKU_TRIGGERS) {
    if (lower.includes(trigger)) {
      triggers.push(trigger);
    }
  }
  if (triggers.length > 0 && message.length < 50) {
    return { score: 0.1, model: 'haiku', triggers };
  }
  
  // Check for Opus triggers
  const opusTriggers: string[] = [];
  for (const trigger of OPUS_TRIGGERS) {
    if (lower.includes(trigger)) {
      opusTriggers.push(trigger);
      score += 0.2;
    }
  }
  
  // Check for Sonnet triggers
  const sonnetTriggers: string[] = [];
  for (const trigger of SONNET_TRIGGERS) {
    if (lower.includes(trigger)) {
      sonnetTriggers.push(trigger);
      score += 0.1;
    }
  }
  
  // Length heuristic
  if (message.length > 500) score += 0.15;
  if (message.length > 1000) score += 0.15;
  
  // Question complexity (multiple questions)
  const questionCount = (message.match(/\?/g) || []).length;
  if (questionCount > 2) score += 0.1;
  
  // Cap score
  score = Math.min(score, 1.0);
  
  // Determine model
  let model: 'haiku' | 'sonnet' | 'opus';
  if (score >= 0.7 || opusTriggers.length > 0) {
    model = 'opus';
  } else if (score >= 0.3 || sonnetTriggers.length > 0) {
    model = 'sonnet';
  } else {
    model = 'haiku';
  }
  
  return {
    score,
    model,
    triggers: [...opusTriggers, ...sonnetTriggers]
  };
}

// Model mapping
const MODEL_MAP = {
  haiku: 'anthropic/claude-3-5-haiku-20241022',
  sonnet: 'anthropic/claude-sonnet-4-0',
  opus: 'anthropic/claude-opus-4-5'
};

// Hook handler - STUB until message:received is available
const handler = async (event: any) => {
  // This hook listens for message:received which doesn't exist yet
  if (event.type !== 'message' || event.action !== 'received') {
    return;
  }
  
  const message = event.context?.message?.text || '';
  if (!message) return;
  
  const result = scoreComplexity(message);
  
  console.log(`[complexity-router] Score: ${result.score.toFixed(2)}, Model: ${result.model}`);
  if (result.triggers.length > 0) {
    console.log(`[complexity-router] Triggers: ${result.triggers.join(', ')}`);
  }
  
  // TODO: When message:received is available, call session_status here
  // await event.api.session_status({ model: MODEL_MAP[result.model] });
};

export default handler;
