#!/usr/bin/env python3
"""
Impulse Circuit Breaker

Monitors for impulse spending patterns and sends alerts.
Triggered during heartbeats or on-demand.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

THANOS_ROOT = Path(__file__).parent.parent
STATE_FILE = THANOS_ROOT / "memory" / "impulse-monitor-state.json"

# Thresholds
AMAZON_CLUSTER_THRESHOLD = 3  # Orders in 24h to trigger alert
CLUSTER_WINDOW_HOURS = 24


def load_state() -> dict:
    """Load monitor state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_alert": None, "alerted_dates": []}


def save_state(state: dict):
    """Save monitor state."""
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_recent_transactions(hours: int = 48) -> list:
    """Fetch recent transactions."""
    cmd = [
        "node", str(THANOS_ROOT / "skills/monarch-money/dist/cli/index.js"),
        "tx", "search", "--limit", "50", "--json"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=THANOS_ROOT)
        output = result.stdout.strip()
        
        start_idx = output.find('[')
        if start_idx == -1:
            return []
        
        bracket_count = 0
        end_idx = start_idx
        for i, char in enumerate(output[start_idx:], start_idx):
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    break
        
        return json.loads(output[start_idx:end_idx])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return []


def check_impulse_patterns(transactions: list) -> list:
    """Check for impulse spending patterns."""
    alerts = []
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Group Amazon orders by date
    amazon_by_date = defaultdict(list)
    
    for tx in transactions:
        merchant = tx.get("merchant", {}).get("name", "").lower()
        date = tx.get("date", "")
        amount = abs(tx.get("amount", 0))
        
        if "amazon" in merchant and date in [today, yesterday]:
            amazon_by_date[date].append({
                "amount": amount,
                "merchant": tx.get("merchant", {}).get("name", ""),
                "category": tx.get("category", {}).get("name", "")
            })
    
    # Check for clusters
    state = load_state()
    alerted = state.get("alerted_dates", [])
    
    for date, orders in amazon_by_date.items():
        if len(orders) >= AMAZON_CLUSTER_THRESHOLD and date not in alerted:
            total = sum(o["amount"] for o in orders)
            alerts.append({
                "type": "amazon_cluster",
                "date": date,
                "count": len(orders),
                "total": total,
                "message": f"🚨 Impulse Alert: {len(orders)} Amazon orders on {date}, total ${total:.2f}"
            })
            alerted.append(date)
    
    # Save state
    state["alerted_dates"] = alerted[-30:]  # Keep last 30 days
    state["last_check"] = datetime.now().isoformat()
    save_state(state)
    
    return alerts


def main():
    """Run impulse check."""
    transactions = get_recent_transactions()
    
    if not transactions:
        print("No transactions to check")
        return
    
    alerts = check_impulse_patterns(transactions)
    
    if alerts:
        for alert in alerts:
            print(alert["message"])
    else:
        print("No impulse patterns detected")


if __name__ == "__main__":
    main()
