#!/usr/bin/env python3
"""
Financial Forecasting & Early Warning System

Analyzes transaction patterns and generates predictive warnings.
Based on behavioral finance research and ADHD-specific patterns.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Budget configuration - Zero-based from January 2026 actuals
MONTHLY_BUDGET = 29750  # Total monthly budget

# Variable expense budgets (excludes fixed housing/debt)
CATEGORY_BUDGETS = {
    "Groceries": 2700,
    "Restaurants & Bars": 2500,  # Part of $3000 Food Out
    "Coffee Shops": 400,  # Part of $3000 Food Out
    "Baby formula": 1000,
    "Household": 950,
    "Gas": 800,  # Part of $950 Transportation
    "Auto Maintenance": 150,  # Part of $950 Transportation
    "Business expense": 3000,  # Part of $3300 Business/Work
    "Business Expenses": 300,  # Secondary business category
    "Software": 100,  # Part of Business/Work
    "Phone": 700,
    "Subscription": 400,  # Part of $500 Subscriptions
    "Streaming": 100,  # Part of $500 Subscriptions
    "Medical": 200,  # Part of $400 Health
    "Prescriptions": 150,  # Part of $400 Health
    "Supplements": 50,  # Part of $400 Health
    "Education": 400,  # Part of $850 Kids/Education
    "School expense": 250,  # Part of Kids/Education
    "Child Activities": 100,  # Part of Kids/Education
    "Family Activities": 100,  # Part of Kids/Education
    "Dog Care": 500,  # Part of $650 Pets
    "Dog Grooming": 150,  # Part of $650 Pets
    "Jeremy Spending Money": 250,  # Part of $650 Personal
    "Clothing": 400,  # Part of $650 Personal
    "Gifts": 1000,  # Part of $6050 Variable
    "Home Improvement": 1000,  # Part of Variable
    "Travel & Vacation": 1000,  # Part of Variable
}

# Warning thresholds
DAILY_BURN_WARNING = 100  # $ per day
RUNWAY_WARNING_DAYS = 20
RUNWAY_CRITICAL_DAYS = 15
IMPULSE_CLUSTER_COUNT = 3
IMPULSE_CLUSTER_HOURS = 24
CATEGORY_WARNING_PCT = 80
CATEGORY_CRITICAL_PCT = 100


def get_transactions(days: int = 30) -> List[dict]:
    """Fetch recent transactions from Monarch."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cmd = [
        "node", "skills/monarch-money/dist/cli/index.js",
        "tx", "search",
        "--start", start_date,
        "--end", end_date,
        "--limit", "500",
        "--json"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        # Parse JSON from output (skip non-JSON lines)
        lines = result.stdout.strip().split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('['):
                json_str = '\n'.join(lines[i:])
                return json.loads(json_str)
    except Exception as e:
        print(f"Error fetching transactions: {e}", file=sys.stderr)
        return []
    
    return []


def get_account_balances() -> Dict[str, float]:
    """Fetch account balances from Monarch."""
    cmd = ["node", "skills/monarch-money/dist/cli/index.js", "acc", "list", "--json"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        lines = result.stdout.strip().split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('['):
                json_str = '\n'.join(lines[i:])
                accounts = json.loads(json_str)
                
                balances = {"liquid": 0, "credit": 0, "total": 0}
                for acc in accounts:
                    bal = acc.get("currentBalance", 0) or 0
                    acc_type = str(acc.get("type", "") or "").lower()
                    acc_name = str(acc.get("displayName", "") or "").lower()
                    
                    # Identify account types
                    if acc_type == "credit" or "card" in acc_name or "platinum" in acc_name or "gold" in acc_name:
                        balances["credit"] += bal  # Usually negative
                    elif any(x in acc_name for x in ["checking", "savings", "money market", "share"]):
                        balances["liquid"] += bal
                    elif bal > 0:  # Positive balance, likely liquid
                        balances["liquid"] += bal
                    
                    balances["total"] += bal
                
                return balances
    except Exception as e:
        print(f"Error fetching balances: {e}", file=sys.stderr)
    
    return {"liquid": 0, "credit": 0, "total": 0}


def analyze_spending_velocity(transactions: List[dict]) -> Dict:
    """Analyze spending rate and velocity."""
    now = datetime.now()
    
    # Group spending by day (exclude transfers, income, credit card payments)
    transfer_categories = ["Transfer", "Credit Card Payment", "Paychecks", "Interest"]
    daily_spending = defaultdict(float)
    
    for tx in transactions:
        if tx.get("amount", 0) < 0:  # Expenses are negative
            cat_name = tx.get("category", {}).get("name", "")
            if cat_name not in transfer_categories:
                date = tx.get("date", "")
                daily_spending[date] += abs(tx["amount"])
    
    if not daily_spending:
        return {"daily_burn": 0, "weekly_trend": 0, "mtd_total": 0, "last_month_total": 0}
    
    # Calculate MTD
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    mtd_spending = sum(amt for date, amt in daily_spending.items() if date >= month_start)
    days_elapsed = now.day
    
    # If early in month (day 1-3), use last month's data for burn rate
    last_month_end = now.replace(day=1) - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1).strftime("%Y-%m-%d")
    last_month_end_str = last_month_end.strftime("%Y-%m-%d")
    
    last_month_spending = sum(amt for date, amt in daily_spending.items() 
                              if last_month_start <= date <= last_month_end_str)
    last_month_days = last_month_end.day
    
    # Use last month's average if we're early in current month
    if days_elapsed <= 3 and last_month_spending > 0:
        daily_burn = last_month_spending / last_month_days
    else:
        daily_burn = mtd_spending / days_elapsed if days_elapsed > 0 else 0
    
    # Week-over-week trend
    this_week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    last_week_start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    
    this_week = sum(amt for date, amt in daily_spending.items() 
                    if date >= this_week_start)
    last_week = sum(amt for date, amt in daily_spending.items() 
                    if last_week_start <= date < this_week_start)
    
    weekly_trend = ((this_week - last_week) / last_week * 100) if last_week > 0 else 0
    
    return {
        "daily_burn": round(daily_burn, 2),
        "mtd_total": round(mtd_spending, 2),
        "last_month_total": round(last_month_spending, 2),
        "days_elapsed": days_elapsed,
        "weekly_trend": round(weekly_trend, 1),
        "this_week": round(this_week, 2),
        "last_week": round(last_week, 2),
    }


def analyze_category_spending(transactions: List[dict]) -> Dict[str, Dict]:
    """Analyze spending by category vs budget."""
    now = datetime.now()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    
    category_totals = defaultdict(float)
    
    for tx in transactions:
        if tx.get("amount", 0) < 0 and tx.get("date", "") >= month_start:
            cat = tx.get("category", {}).get("name", "Uncategorized")
            category_totals[cat] += abs(tx["amount"])
    
    results = {}
    for cat, budget in CATEGORY_BUDGETS.items():
        spent = category_totals.get(cat, 0)
        pct = (spent / budget * 100) if budget > 0 else 0
        
        status = "ok"
        if pct >= CATEGORY_CRITICAL_PCT:
            status = "critical"
        elif pct >= CATEGORY_WARNING_PCT:
            status = "warning"
        
        results[cat] = {
            "spent": round(spent, 2),
            "budget": budget,
            "percent": round(pct, 1),
            "status": status,
            "remaining": round(budget - spent, 2),
        }
    
    return results


def detect_impulse_patterns(transactions: List[dict]) -> List[Dict]:
    """Detect impulse spending clusters."""
    warnings = []
    
    # Group by date
    by_date = defaultdict(list)
    for tx in transactions:
        if tx.get("amount", 0) < 0:
            by_date[tx.get("date", "")].append(tx)
    
    # Check for clusters
    for date, txs in by_date.items():
        if len(txs) >= IMPULSE_CLUSTER_COUNT:
            amazon_count = sum(1 for t in txs if "amazon" in t.get("merchant", {}).get("name", "").lower())
            total = sum(abs(t["amount"]) for t in txs)
            
            if amazon_count >= 3:
                warnings.append({
                    "type": "impulse_cluster",
                    "date": date,
                    "count": len(txs),
                    "amazon_count": amazon_count,
                    "total": round(total, 2),
                    "message": f"Impulse pattern: {amazon_count} Amazon orders on {date}, total ${total:.2f}"
                })
            elif len(txs) >= 5:
                warnings.append({
                    "type": "high_transaction_day",
                    "date": date,
                    "count": len(txs),
                    "total": round(total, 2),
                    "message": f"High activity: {len(txs)} transactions on {date}, total ${total:.2f}"
                })
    
    return warnings


def calculate_runway(balances: Dict, velocity: Dict) -> Dict:
    """Calculate cash runway based on burn rate."""
    liquid = balances.get("liquid", 0)
    daily_burn = velocity.get("daily_burn", 0)
    
    if daily_burn <= 0:
        return {"days": 999, "status": "ok", "message": "No spending detected"}
    
    runway_days = liquid / daily_burn
    
    status = "ok"
    if runway_days < RUNWAY_CRITICAL_DAYS:
        status = "critical"
    elif runway_days < RUNWAY_WARNING_DAYS:
        status = "warning"
    
    return {
        "days": round(runway_days, 1),
        "status": status,
        "liquid_cash": round(liquid, 2),
        "daily_burn": daily_burn,
        "message": f"Cash runway: {runway_days:.0f} days at ${daily_burn:.0f}/day"
    }


def project_end_of_month(velocity: Dict, balances: Dict) -> Dict:
    """Project end-of-month spending and balance."""
    now = datetime.now()
    days_in_month = (now.replace(month=now.month % 12 + 1, day=1) - timedelta(days=1)).day
    days_remaining = days_in_month - now.day
    
    mtd = velocity.get("mtd_total", 0)
    daily_burn = velocity.get("daily_burn", 0)
    
    projected_total = mtd + (daily_burn * days_remaining)
    projected_balance = balances.get("liquid", 0) - (daily_burn * days_remaining)
    
    over_budget = projected_total > MONTHLY_BUDGET
    budget_variance = projected_total - MONTHLY_BUDGET
    
    return {
        "projected_spending": round(projected_total, 2),
        "projected_balance": round(projected_balance, 2),
        "days_remaining": days_remaining,
        "over_budget": over_budget,
        "variance": round(budget_variance, 2),
        "message": f"Projected EOM: ${projected_total:.0f} spending, ${projected_balance:.0f} cash"
    }


def generate_warnings(velocity: Dict, categories: Dict, runway: Dict, 
                      projection: Dict, impulse: List) -> List[str]:
    """Generate prioritized warning messages."""
    warnings = []
    
    # Critical warnings (🔴)
    if runway["status"] == "critical":
        warnings.append(f"🔴 CRITICAL: {runway['message']}")
    
    if projection["projected_balance"] < 500:
        warnings.append(f"🔴 CRITICAL: Low EOM balance projected (${projection['projected_balance']:.0f})")
    
    # Category overages (⚠️)
    for cat, data in categories.items():
        if data["status"] == "critical":
            warnings.append(f"⚠️ OVER BUDGET: {cat} ${data['spent']:.0f}/${data['budget']} ({data['percent']:.0f}%)")
        elif data["status"] == "warning":
            warnings.append(f"⚠️ Approaching limit: {cat} ${data['spent']:.0f}/${data['budget']} ({data['percent']:.0f}%)")
    
    # Velocity warnings
    if velocity["daily_burn"] > DAILY_BURN_WARNING:
        warnings.append(f"⚠️ High burn rate: ${velocity['daily_burn']:.0f}/day")
    
    if velocity["weekly_trend"] > 30:
        warnings.append(f"⚠️ Spending up {velocity['weekly_trend']:.0f}% vs last week")
    
    # Projection warnings
    if projection["over_budget"] and projection["variance"] > 200:
        warnings.append(f"⚠️ Projected ${projection['variance']:.0f} over budget by EOM")
    
    # Impulse warnings
    for imp in impulse:
        warnings.append(f"ℹ️ {imp['message']}")
    
    return warnings


def format_brief_section(velocity: Dict, categories: Dict, runway: Dict,
                         projection: Dict, balances: Dict, warnings: List[str]) -> str:
    """Format the financial section for morning brief."""
    
    # Budget progress bar
    pct = min(100, velocity["mtd_total"] / MONTHLY_BUDGET * 100)
    bar_filled = int(pct / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)
    
    output = []
    output.append("💰 FINANCIAL PULSE")
    output.append("━━━━━━━━━━━━━━━━━━")
    output.append(f"Cash: ${balances['liquid']:,.0f} | Cards: ${balances['credit']:,.0f}")
    output.append(f"Runway: {runway['days']:.0f} days @ ${velocity['daily_burn']:.0f}/day")
    output.append("")
    output.append(f"MTD: ${velocity['mtd_total']:,.0f} / ${MONTHLY_BUDGET:,}")
    output.append(f"[{bar}] {pct:.0f}%")
    output.append(f"Pace: ${projection['projected_spending']:,.0f} projected")
    
    # Top categories
    output.append("")
    output.append("Categories:")
    for cat in ["Groceries", "Baby formula", "Gas", "Restaurants & Bars"]:
        if cat in categories:
            c = categories[cat]
            emoji = "🔴" if c["status"] == "critical" else "⚠️" if c["status"] == "warning" else "✅"
            output.append(f"  {emoji} {cat}: ${c['spent']:.0f}/${c['budget']}")
    
    # Warnings
    if warnings:
        output.append("")
        output.append("Alerts:")
        for w in warnings[:5]:  # Limit to 5 warnings
            output.append(f"  {w}")
    
    output.append("━━━━━━━━━━━━━━━━━━")
    
    return "\n".join(output)


def main():
    """Run financial forecasting analysis."""
    print("Analyzing financial patterns...\n", file=sys.stderr)
    
    # Fetch data
    transactions = get_transactions(60)  # 60 days for trends
    balances = get_account_balances()
    
    if not transactions:
        print("❌ No transaction data available")
        return
    
    # Run analyses
    velocity = analyze_spending_velocity(transactions)
    categories = analyze_category_spending(transactions)
    impulse = detect_impulse_patterns(transactions)
    runway = calculate_runway(balances, velocity)
    projection = project_end_of_month(velocity, balances)
    
    # Generate warnings
    warnings = generate_warnings(velocity, categories, runway, projection, impulse)
    
    # Output
    brief = format_brief_section(velocity, categories, runway, projection, balances, warnings)
    print(brief)
    
    # Detailed JSON output to stderr for logging
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "velocity": velocity,
        "runway": runway,
        "projection": projection,
        "categories": categories,
        "warnings": warnings,
        "impulse_patterns": impulse,
    }
    print(f"\n--- Detailed Analysis ---", file=sys.stderr)
    print(json.dumps(analysis, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
