#!/usr/bin/env python3
"""Simple CLI for WorkOS adapter."""

import asyncio
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Tools.adapters.workos import WorkOSAdapter


async def main():
    parser = argparse.ArgumentParser(description="WorkOS task management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add task
    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("--title", required=True, help="Task title")
    add_parser.add_argument("--client", required=True, help="Client name")
    add_parser.add_argument("--epic-id", help="Epic ticket ID")
    add_parser.add_argument("--points", type=int, default=2, help="Story points (1/2/4/7)")
    add_parser.add_argument("--status", default="queued", help="Status: queued/active/backlog/done")
    add_parser.add_argument("--description", help="Task description")

    # List tasks
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--client", help="Filter by client")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--limit", type=int, default=10, help="Max results")

    # Today's tasks
    subparsers.add_parser("today", help="Show today's tasks")

    args = parser.parse_args()

    adapter = WorkOSAdapter()
    
    try:
        if args.command == "add":
            # Map status
            status_map = {
                "In Progress": "active",
                "Not Started": "queued", 
                "Done": "done",
                "Backlog": "backlog",
            }
            status = status_map.get(args.status, args.status.lower())
            
            # Get client ID first
            clients_result = await adapter.call_tool("get_clients", {"active_only": False})
            client_id = None
            if clients_result.success:
                for c in clients_result.data:
                    if c.get("name", "").lower() == args.client.lower():
                        client_id = c.get("id")
                        break
            
            desc = args.description or ""
            if args.epic_id:
                desc = f"Epic #{args.epic_id}" + (f" - {desc}" if desc else "")
            
            result = await adapter.call_tool("create_task", {
                "title": args.title,
                "status": status,
                "client_id": client_id,
                "effort_estimate": args.points,
                "description": desc,
            })
            if result.success:
                print(f"✅ Added: {args.title} ({args.points}pts, {args.client})")
            else:
                print(f"❌ Error: {result.error}")

        elif args.command == "list":
            result = await adapter.call_tool("get_tasks", {
                "status": args.status,
                "limit": args.limit,
            })
            if result.success:
                tasks = result.data
                if not tasks:
                    print("No tasks found")
                else:
                    for t in tasks:
                        client = t.get('client_name') or 'No client'
                        if args.client and args.client.lower() not in client.lower():
                            continue
                        print(f"- [{t.get('status', '?')}] {t.get('title', 'Untitled')} ({t.get('effort_estimate', 0)}pts) - {client}")
            else:
                print(f"❌ Error: {result.error}")

        elif args.command == "today":
            result = await adapter.call_tool("daily_summary", {})
            if result.success:
                data = result.data
                print(f"📊 Today: {data.get('points_completed', 0)}/{data.get('points_target', 18)} pts")
                active = data.get('active_tasks', [])
                print(f"Active tasks: {len(active)}")
                for t in active[:5]:
                    print(f"  - {t.get('title', 'Untitled')} ({t.get('effort_estimate', 0)}pts)")
            else:
                print(f"❌ Error: {result.error}")

    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
