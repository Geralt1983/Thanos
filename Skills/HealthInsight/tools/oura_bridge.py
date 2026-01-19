#!/usr/bin/env python3
"""Oura MCP Bridge - CLI wrapper for Oura MCP server"""
import argparse
import json
from datetime import date, timedelta
from pathlib import Path


def call_oura(method: str, params: dict = None) -> dict:
    """Call Oura MCP method."""
    operations = {
        'get_readiness': 'oura__get_daily_readiness',
        'get_sleep': 'oura__get_daily_sleep',
        'get_activity': 'oura__get_daily_activity',
        'get_stress': 'oura__get_daily_stress',
        'get_hrv': 'oura__get_daily_resilience',
    }

    if method not in operations:
        return {'error': f'Unknown method: {method}', 'available': list(operations.keys())}

    # Default date range: today
    if not params:
        today = date.today().isoformat()
        params = {'startDate': today, 'endDate': today}

    return {
        'instruction': f'Call MCP tool: {operations[method]}',
        'params': params,
        'note': 'Execute via Claude Code MCP integration'
    }


def get_readiness_score() -> int | None:
    """Try to get readiness score from cache."""
    thanos_root = Path(__file__).parent.parent.parent.parent
    cache_paths = [
        thanos_root / 'State' / 'oura_cache.db',
        thanos_root / 'mcp-servers' / 'oura-mcp' / 'cache' / 'oura_cache.db',
    ]

    for cache_path in cache_paths:
        if cache_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(cache_path))
                cursor = conn.execute(
                    "SELECT value FROM cache WHERE key LIKE '%readiness%' ORDER BY key DESC LIMIT 1"
                )
                row = cursor.fetchone()
                conn.close()
                if row:
                    data = json.loads(row[0])
                    if isinstance(data, list) and data:
                        return data[0].get('score')
                    elif isinstance(data, dict):
                        return data.get('score')
            except Exception:
                pass

    return None


def main():
    parser = argparse.ArgumentParser(description='Oura MCP Bridge')
    parser.add_argument('method', nargs='?', default='get_readiness',
                        help='Method to call (get_readiness, get_sleep, etc.)')
    parser.add_argument('--params', type=json.loads, default=None, help='JSON params')
    parser.add_argument('--output', choices=['json', 'pretty'], default='pretty')
    parser.add_argument('--cache', action='store_true', help='Try to read from cache')

    args = parser.parse_args()

    if args.cache and args.method == 'get_readiness':
        score = get_readiness_score()
        if score:
            result = {'readiness_score': score, 'source': 'cache'}
        else:
            result = call_oura(args.method, args.params)
    else:
        result = call_oura(args.method, args.params)

    if args.output == 'json':
        print(json.dumps(result))
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
