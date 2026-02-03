#!/usr/bin/env python3
"""
Complexity Scorer - Determine which model tier a message needs.

Usage:
    python complexity_scorer.py "your message here"
    echo "message" | python complexity_scorer.py
"""

import sys
import re

# Trigger words by tier
OPUS_TRIGGERS = [
    'analyze', 'architecture', 'design', 'strategic', 'deep dive',
    'think hard', 'really think', 'complex', 'thorough', 'comprehensive',
    'system design', 'trade-offs', 'trade-off', 'evaluate options',
    'multi-step', 'planning', 'strategy', 'optimize', 'scalability',
    'refactor entire', 'rewrite', 'overhaul'
]

SONNET_TRIGGERS = [
    'code', 'debug', 'refactor', 'implement', 'explain',
    'how does', 'build', 'create', 'fix', 'error',
    'function', 'class', 'api', 'integration', 'script'
]

HAIKU_TRIGGERS = [
    'yes', 'no', 'quick', 'simple', 'just',
    'status', 'check', 'confirm', 'ok', 'thanks',
    'what time', 'weather', 'remind'
]

MODEL_MAP = {
    'haiku': 'anthropic/claude-3-5-haiku-20241022',
    'sonnet': 'anthropic/claude-sonnet-4-0',
    'opus': 'anthropic/claude-opus-4-5'
}


def score_complexity(message: str) -> dict:
    """Score message complexity and determine model tier."""
    lower = message.lower()
    triggers_found = []
    score = 0.3  # Default baseline
    
    # Check Haiku triggers (fast exit for simple messages)
    haiku_matches = [t for t in HAIKU_TRIGGERS if t in lower]
    if haiku_matches and len(message) < 50:
        return {
            'score': 0.1,
            'model': 'haiku',
            'model_id': MODEL_MAP['haiku'],
            'triggers': haiku_matches,
            'reason': 'Simple query with haiku triggers'
        }
    
    # Check Opus triggers
    opus_matches = [t for t in OPUS_TRIGGERS if t in lower]
    for _ in opus_matches:
        score += 0.2
    triggers_found.extend(opus_matches)
    
    # Check Sonnet triggers
    sonnet_matches = [t for t in SONNET_TRIGGERS if t in lower]
    for _ in sonnet_matches:
        score += 0.1
    triggers_found.extend(sonnet_matches)
    
    # Length heuristics
    if len(message) > 500:
        score += 0.15
    if len(message) > 1000:
        score += 0.15
    
    # Multiple questions
    question_count = len(re.findall(r'\?', message))
    if question_count > 2:
        score += 0.1
    
    # Code blocks
    if '```' in message:
        score += 0.1
    
    # Cap score
    score = min(score, 1.0)
    
    # Determine model
    if score >= 0.7 or opus_matches:
        model = 'opus'
        reason = f"High complexity ({score:.2f}) or opus triggers"
    elif score >= 0.3 or sonnet_matches:
        model = 'sonnet'
        reason = f"Medium complexity ({score:.2f}) or sonnet triggers"
    else:
        model = 'haiku'
        reason = f"Low complexity ({score:.2f})"
    
    return {
        'score': round(score, 2),
        'model': model,
        'model_id': MODEL_MAP[model],
        'triggers': triggers_found,
        'reason': reason
    }


def main():
    # Get message from args or stdin
    if len(sys.argv) > 1:
        message = ' '.join(sys.argv[1:])
    else:
        message = sys.stdin.read().strip()
    
    if not message:
        print("Usage: python complexity_scorer.py 'your message'")
        sys.exit(1)
    
    result = score_complexity(message)
    
    print(f"Score: {result['score']}")
    print(f"Model: {result['model'].upper()} ({result['model_id']})")
    if result['triggers']:
        print(f"Triggers: {', '.join(result['triggers'])}")
    print(f"Reason: {result['reason']}")
    
    # Output model ID for piping
    if '--model-only' in sys.argv:
        print(result['model_id'])


if __name__ == '__main__':
    main()
