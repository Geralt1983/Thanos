#!/usr/bin/env python3
"""
OpenClaw ↔ Thanos CLI bridge.

Used by the OpenClaw plugin to route messages through Thanos and capture learnings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path for imports when run directly
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Tools.openclaw_harness import OpenClawHarness


def _read_stdin_json() -> Dict[str, Any] | None:
    if sys.stdin is None or sys.stdin.isatty():
        return None
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    return json.loads(raw)


def cmd_route(args: argparse.Namespace) -> int:
    payload = _read_stdin_json() or {}
    message = payload.get("message") or args.message
    if not message:
        print("message required", file=sys.stderr)
        return 2

    session_id = payload.get("session_id") or args.session_id
    context = payload.get("context") or {}
    source = payload.get("source") or args.source or "openclaw"
    allow_llm_capture = payload.get("allow_llm_capture") or args.allow_llm_capture

    harness = OpenClawHarness()
    result = harness.route_message(
        message=message,
        session_id=session_id,
        context=context,
        source=source,
        allow_llm_capture=bool(allow_llm_capture),
    )
    print(json.dumps(result, ensure_ascii=True))
    return 0


def cmd_refresh(_: argparse.Namespace) -> int:
    harness = OpenClawHarness()
    harness.refresh_state()
    print(json.dumps({"ok": True}, ensure_ascii=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="openclaw_cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_route = sub.add_parser("route")
    p_route.add_argument("--message", type=str)
    p_route.add_argument("--session-id", type=str, default=None)
    p_route.add_argument("--source", type=str, default="openclaw")
    p_route.add_argument("--allow-llm-capture", action="store_true")
    p_route.set_defaults(func=cmd_route)

    p_refresh = sub.add_parser("refresh")
    p_refresh.set_defaults(func=cmd_refresh)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
