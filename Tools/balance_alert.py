#!/usr/bin/env python3
"""
Balance Alert System

Monitors checking account balance and sends WhatsApp alert when below threshold.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

THANOS_ROOT = Path(__file__).parent.parent
STATE_FILE = THANOS_ROOT / "memory" / "balance-alert-state.json"

# Configuration
BALANCE_THRESHOLD = 3000  # Alert when checking drops below this
ALERT_COOLDOWN_HOURS = 12  # Don't re-alert within this window
CHECKING_ACCOUNT_PATTERNS = ["checking"]


def load_state() -> dict:
    """Load alert state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_alert": None, "last_balance": None}


def save_state(state: dict):
    """Save alert state."""
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_checking_balance() -> float:
    """Fetch checking account balance from Monarch."""
    cmd = [
        "node", str(THANOS_ROOT / "skills/monarch-money/dist/cli/index.js"),
        "acc", "list", "--json"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=THANOS_ROOT)
        output = result.stdout.strip()
        
        start_idx = output.find('[')
        if start_idx == -1:
            return None
        
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
        
        accounts = json.loads(output[start_idx:end_idx])
        
        # Find checking account
        for acc in accounts:
            name = acc.get("displayName", "").lower()
            if any(p in name for p in CHECKING_ACCOUNT_PATTERNS):
                return acc.get("currentBalance", 0)
        
        return None
    except Exception as e:
        print(f"Error fetching balance: {e}", file=sys.stderr)
        return None


def should_alert(balance: float, state: dict) -> bool:
    """Determine if we should send an alert."""
    if balance is None or balance >= BALANCE_THRESHOLD:
        return False
    
    # Check cooldown
    last_alert = state.get("last_alert")
    if last_alert:
        last_time = datetime.fromisoformat(last_alert)
        hours_since = (datetime.now() - last_time).total_seconds() / 3600
        if hours_since < ALERT_COOLDOWN_HOURS:
            return False
    
    return True


def check_balance() -> dict:
    """Check balance and return alert info if needed."""
    state = load_state()
    balance = get_checking_balance()
    
    result = {
        "balance": balance,
        "threshold": BALANCE_THRESHOLD,
        "alert_needed": False,
        "message": None
    }
    
    if balance is None:
        result["error"] = "Could not fetch balance"
        return result
    
    state["last_balance"] = balance
    state["last_check"] = datetime.now().isoformat()
    
    if should_alert(balance, state):
        result["alert_needed"] = True
        result["message"] = f"⚠️ Low Balance Alert: Checking at ${balance:,.2f} (below ${BALANCE_THRESHOLD:,} threshold)"
        state["last_alert"] = datetime.now().isoformat()
    
    save_state(state)
    return result


def main():
    """Run balance check."""
    result = check_balance()
    
    if result.get("error"):
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    balance = result["balance"]
    print(f"Checking balance: ${balance:,.2f}")
    print(f"Threshold: ${BALANCE_THRESHOLD:,}")
    
    if result["alert_needed"]:
        print(f"\n🚨 ALERT: {result['message']}")
        # Output for WhatsApp (caller should send)
        print(f"\nWHATSAPP_ALERT:{result['message']}")
    else:
        status = "OK" if balance >= BALANCE_THRESHOLD else f"Below threshold (cooldown active)"
        print(f"Status: {status}")


if __name__ == "__main__":
    main()
