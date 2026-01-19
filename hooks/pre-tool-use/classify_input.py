#!/usr/bin/env python3
"""
Pre-tool-use hook: Classify input before allowing task creation.
Exit 0 = allow, Exit 1 = block with message
"""
import sys
import json


def classify(text: str) -> tuple[str, float]:
    """Returns (category, confidence)"""
    text_lower = text.lower()

    scores = {
        'thinking': 0,
        'venting': 0,
        'observation': 0,
        'question': 0,
        'task': 0
    }

    # Question detection
    if '?' in text or text_lower.startswith(('what', 'how', 'why', 'when', 'where', 'who', 'can', 'should')):
        scores['question'] += 3

    # Venting signals
    venting_words = ['ugh', 'frustrated', 'annoying', 'hate', 'stupid', 'insane', 'crazy', 'ridiculous']
    scores['venting'] += sum(2 for w in venting_words if w in text_lower)

    # Thinking signals
    thinking_phrases = ["i've been thinking", "wondering if", "maybe", "what if", "considering"]
    scores['thinking'] += sum(2 for p in thinking_phrases if p in text_lower)

    # Observation signals
    observation_phrases = ["i noticed", "interesting that", "turns out", "apparently"]
    scores['observation'] += sum(2 for p in observation_phrases if p in text_lower)

    # Task signals
    task_phrases = ["need to", "have to", "must", "by friday", "deadline", "todo", "task"]
    scores['task'] += sum(2 for p in task_phrases if p in text_lower)

    # Action verbs boost task score
    action_verbs = ["fix", "create", "build", "write", "send", "call", "schedule", "deploy", "review"]
    scores['task'] += sum(1 for v in action_verbs if v in text_lower)

    # Weak commitment reduces task score
    weak_phrases = ["should probably", "might", "someday", "eventually", "maybe i'll"]
    scores['task'] -= sum(2 for p in weak_phrases if p in text_lower)

    total = sum(scores.values()) + 1
    category = max(scores, key=scores.get)
    confidence = scores[category] / total

    return category, confidence


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    try:
        hook_data = json.loads(sys.argv[1])
        tool_name = hook_data.get('tool', '')
        tool_args = hook_data.get('args', {})
    except json.JSONDecodeError:
        sys.exit(0)

    task_tools = ['task', 'workos', 'create_task', 'add_task', 'todo']
    if not any(t in tool_name.lower() for t in task_tools):
        sys.exit(0)

    input_text = (
        tool_args.get('description', '') or
        tool_args.get('text', '') or
        tool_args.get('content', '') or
        tool_args.get('title', '')
    )
    if not input_text:
        sys.exit(0)

    category, confidence = classify(input_text)

    if category != 'task' or confidence < 0.3:
        print(json.dumps({
            'blocked': True,
            'category': category,
            'confidence': f'{confidence:.0%}',
            'reason': f'Input classified as "{category}". Not creating task.',
            'suggestion': f'This seems more like {category}. Acknowledge instead?'
        }))
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
