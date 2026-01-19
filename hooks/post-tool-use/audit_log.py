#!/usr/bin/env python3
"""Post-tool-use hook: Log all tool executions for audit trail"""
import sys
import json
import os
from datetime import datetime
from pathlib import Path


def main():
    thanos_root = os.environ.get('THANOS_ROOT', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    decisions_dir = Path(thanos_root) / 'history' / 'decisions'
    decisions_dir.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) < 2:
        return

    try:
        hook_data = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        return

    entry = {
        'timestamp': datetime.now().isoformat(),
        'tool': hook_data.get('tool', 'unknown'),
        'args': hook_data.get('args', {}),
        'result': hook_data.get('result', {}),
        'success': hook_data.get('success', True),
    }

    date_str = datetime.now().strftime('%Y-%m-%d')
    log_file = decisions_dir / f'{date_str}.jsonl'

    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')


if __name__ == '__main__':
    main()
