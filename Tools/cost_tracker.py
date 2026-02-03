#!/usr/bin/env python3
"""
Cost and Token Tracker for Claude Code Sessions

Tracks token usage and costs across sessions by parsing transcript files.
Integrates with TimeState for comprehensive session metrics.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Claude Code model pricing (as of 2026)
MODEL_PRICING = {
    "anthropic/claude-sonnet-4-5": {
        "input": 3.00 / 1_000_000,   # $3 per million input tokens
        "output": 15.00 / 1_000_000  # $15 per million output tokens
    },
    "anthropic/claude-opus-4-5": {
        "input": 15.00 / 1_000_000,
        "output": 75.00 / 1_000_000
    },
    "anthropic/claude-3-5-haiku-20241022": {
        "input": 1.00 / 1_000_000,
        "output": 5.00 / 1_000_000
    }
}

class CostTracker:
    """Track costs and tokens across Claude Code sessions."""

    def __init__(self, thanos_root: Optional[Path] = None):
        """Initialize cost tracker."""
        self.thanos_root = thanos_root or Path.home() / "Projects" / "Thanos"
        self.state_file = self.thanos_root / "State" / "CostState.json"
        self.transcript_dir = Path.home() / ".claude" / "projects"

    def get_latest_transcript(self) -> Optional[Path]:
        """Find the most recently modified transcript file."""
        try:
            transcripts = list(self.transcript_dir.glob("*/*.jsonl"))
            if not transcripts:
                return None
            return max(transcripts, key=lambda p: p.stat().st_mtime)
        except Exception:
            return None

    def parse_transcript(self, transcript_path: Path) -> Dict:
        """
        Parse transcript to extract token and cost information.

        Returns:
            Dict with tokens, costs, and model usage
        """
        result = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "models_used": {},
            "message_count": 0,
            "last_updated": datetime.now().isoformat()
        }

        try:
            with open(transcript_path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())

                        # Extract model info
                        model = entry.get("model", "unknown")

                        # Extract token usage
                        usage = entry.get("usage", {})
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)

                        result["total_input_tokens"] += input_tokens
                        result["total_output_tokens"] += output_tokens
                        result["message_count"] += 1

                        # Track per-model usage
                        if model not in result["models_used"]:
                            result["models_used"][model] = {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cost": 0.0,
                                "calls": 0
                            }

                        model_stats = result["models_used"][model]
                        model_stats["input_tokens"] += input_tokens
                        model_stats["output_tokens"] += output_tokens
                        model_stats["calls"] += 1

                        # Calculate cost if pricing available
                        if model in MODEL_PRICING:
                            pricing = MODEL_PRICING[model]
                            cost = (input_tokens * pricing["input"] +
                                   output_tokens * pricing["output"])
                            model_stats["cost"] += cost
                            result["total_cost"] += cost

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"Error parsing transcript: {e}", file=sys.stderr)

        return result

    def load_state(self) -> Dict:
        """Load saved cost state."""
        if not self.state_file.exists():
            return {
                "sessions": [],
                "lifetime_total": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0
                }
            }

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {"sessions": [], "lifetime_total": {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}}

    def save_state(self, state: Dict):
        """Save cost state."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def get_current_session_cost(self) -> Dict:
        """Get cost/token stats for current session."""
        transcript = self.get_latest_transcript()
        if not transcript:
            return {
                "status": "no_transcript",
                "cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0
            }

        stats = self.parse_transcript(transcript)
        return {
            "status": "ok",
            "cost": round(stats["total_cost"], 4),
            "input_tokens": stats["total_input_tokens"],
            "output_tokens": stats["total_output_tokens"],
            "total_tokens": stats["total_input_tokens"] + stats["total_output_tokens"],
            "models": stats["models_used"],
            "messages": stats["message_count"]
        }

    def get_summary(self, include_current: bool = True) -> Dict:
        """Get comprehensive cost summary."""
        state = self.load_state()
        result = {
            "lifetime": state.get("lifetime_total", {}),
            "session_count": len(state.get("sessions", [])),
        }

        if include_current:
            result["current_session"] = self.get_current_session_cost()

        return result

    def record_session_end(self):
        """Record session completion with final costs."""
        transcript = self.get_latest_transcript()
        if not transcript:
            return

        stats = self.parse_transcript(transcript)
        state = self.load_state()

        # Add session record
        session_record = {
            "timestamp": datetime.now().isoformat(),
            "cost": stats["total_cost"],
            "input_tokens": stats["total_input_tokens"],
            "output_tokens": stats["total_output_tokens"],
            "models": stats["models_used"]
        }

        state["sessions"].append(session_record)

        # Update lifetime totals
        lifetime = state["lifetime_total"]
        lifetime["input_tokens"] += stats["total_input_tokens"]
        lifetime["output_tokens"] += stats["total_output_tokens"]
        lifetime["cost"] += stats["total_cost"]

        self.save_state(state)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Track Claude Code costs and tokens")
    parser.add_argument("--current", action="store_true", help="Show current session stats")
    parser.add_argument("--summary", action="store_true", help="Show lifetime summary")
    parser.add_argument("--record-end", action="store_true", help="Record session end")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    tracker = CostTracker()

    if args.record_end:
        tracker.record_session_end()
        if args.json:
            print(json.dumps({"status": "recorded"}))
        else:
            print("Session cost recorded")
        sys.exit(0)

    if args.current:
        data = tracker.get_current_session_cost()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            if data["status"] == "ok":
                print(f"Current Session:")
                print(f"  Cost: ${data['cost']:.4f}")
                print(f"  Tokens: {data['total_tokens']:,} ({data['input_tokens']:,} in / {data['output_tokens']:,} out)")
                print(f"  Messages: {data['messages']}")
            else:
                print("No transcript available")
        sys.exit(0)

    if args.summary:
        data = tracker.get_summary()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            lifetime = data["lifetime"]
            print(f"Lifetime Stats ({data['session_count']} sessions):")
            print(f"  Total Cost: ${lifetime.get('cost', 0):.2f}")
            print(f"  Total Tokens: {lifetime.get('input_tokens', 0) + lifetime.get('output_tokens', 0):,}")

            if "current_session" in data and data["current_session"]["status"] == "ok":
                current = data["current_session"]
                print(f"\nCurrent Session:")
                print(f"  Cost: ${current['cost']:.4f}")
                print(f"  Tokens: {current['total_tokens']:,}")
        sys.exit(0)

    # Default: show current
    data = tracker.get_current_session_cost()
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
