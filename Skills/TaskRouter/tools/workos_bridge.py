#!/usr/bin/env python3
"""WorkOS MCP Bridge - CLI wrapper for WorkOS MCP server"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def call_workos(method: str, params: dict = None) -> dict:
    """Call WorkOS MCP method."""
    # Map common operations to MCP tool calls
    # These would be executed through Claude Code's MCP integration
    operations = {
        'get_tasks': 'workos_get_tasks',
        'create_task': 'workos_create_task',
        'complete_task': 'workos_complete_task',
        'get_habits': 'workos_get_habits',
        'brain_dump': 'workos_brain_dump',
        'get_energy': 'workos_get_energy',
        'daily_summary': 'workos_daily_summary',
    }

    if method not in operations:
        return {'error': f'Unknown method: {method}', 'available': list(operations.keys())}

    # In practice, this would be called via MCP
    # For now, return instruction for Claude Code
    return {
        'instruction': f'Call MCP tool: {operations[method]}',
        'params': params or {},
        'note': 'Execute via Claude Code MCP integration'
    }


def main():
    parser = argparse.ArgumentParser(description='WorkOS MCP Bridge')
    parser.add_argument('method', help='Method to call (get_tasks, create_task, etc.)')
    parser.add_argument('--params', type=json.loads, default={}, help='JSON params')
    parser.add_argument('--output', choices=['json', 'pretty'], default='pretty')

    args = parser.parse_args()
    result = call_workos(args.method, args.params)

    if args.output == 'json':
        print(json.dumps(result))
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
