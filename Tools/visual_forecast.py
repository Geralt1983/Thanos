#!/usr/bin/env python3
"""
Visual Cash Flow Forecast

Generates stunning visual forecasts as images for messaging.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

THANOS_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = THANOS_ROOT / "output"

# Color palette - modern, professional
COLORS = {
    "green": "#10B981",      # Emerald
    "green_light": "#D1FAE5",
    "red": "#EF4444",        # Rose
    "red_light": "#FEE2E2",
    "yellow": "#F59E0B",     # Amber
    "yellow_light": "#FEF3C7",
    "blue": "#3B82F6",       # Blue
    "blue_light": "#DBEAFE",
    "gray": "#6B7280",
    "dark": "#1F2937",
    "white": "#FFFFFF",
    "bg": "#F9FAFB",
}


def get_forecast_data() -> dict:
    """Run financial forecasting and get analysis."""
    cmd = [sys.executable, str(THANOS_ROOT / "Tools" / "financial_forecasting.py")]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=THANOS_ROOT)
        stderr = result.stderr
        json_start = stderr.find('{')
        if json_start >= 0:
            return json.loads(stderr[json_start:])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    return {}


def create_gauge(ax, value, max_value, label, threshold_low, threshold_high):
    """Create a semi-circular gauge."""
    # Clear axis
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-0.2, 1.2)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Background arc
    theta = np.linspace(np.pi, 0, 100)
    x = np.cos(theta)
    y = np.sin(theta)
    ax.fill_between(x, 0, y, color=COLORS["gray"], alpha=0.2)
    
    # Colored sections
    pct = min(1, max(0, value / max_value))
    
    if pct < threshold_low / max_value:
        color = COLORS["red"]
    elif pct < threshold_high / max_value:
        color = COLORS["yellow"]
    else:
        color = COLORS["green"]
    
    theta_filled = np.linspace(np.pi, np.pi - (np.pi * pct), 100)
    x_filled = np.cos(theta_filled)
    y_filled = np.sin(theta_filled)
    ax.fill_between(x_filled, 0, y_filled, color=color, alpha=0.8)
    
    # Center text
    ax.text(0, 0.3, f"${value:,.0f}", fontsize=20, fontweight='bold', 
            ha='center', va='center', color=COLORS["dark"])
    ax.text(0, -0.05, label, fontsize=11, ha='center', va='center', color=COLORS["gray"])


def create_scenario_bars(ax, scenarios):
    """Create horizontal scenario comparison bars."""
    names = ['Best Case', 'Expected', 'Worst Case']
    values = [
        scenarios.get('best_case', {}).get('eom_balance', 0),
        scenarios.get('expected', {}).get('eom_balance', 0),
        scenarios.get('worst_case', {}).get('eom_balance', 0)
    ]
    
    colors = [COLORS["green"], COLORS["yellow"], COLORS["red"]]
    
    y_pos = np.arange(len(names))
    
    # Determine x-axis range
    min_val = min(0, min(values)) - 500
    max_val = max(0, max(values)) + 500
    
    bars = ax.barh(y_pos, values, color=colors, height=0.6, edgecolor='white', linewidth=2)
    
    # Zero line
    ax.axvline(x=0, color=COLORS["dark"], linewidth=1, linestyle='-', alpha=0.3)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=11, fontweight='medium')
    ax.set_xlim(min_val, max_val)
    ax.set_xlabel('End of Month Balance ($)', fontsize=10, color=COLORS["gray"])
    
    # Value labels
    for bar, val in zip(bars, values):
        x_pos = val + (200 if val >= 0 else -200)
        ha = 'left' if val >= 0 else 'right'
        color = COLORS["green"] if val >= 0 else COLORS["red"]
        ax.text(x_pos, bar.get_y() + bar.get_height()/2, f'${val:,.0f}', 
                va='center', ha=ha, fontsize=11, fontweight='bold', color=color)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(left=False)


def create_category_progress(ax, categories):
    """Create category budget progress bars."""
    # Select top categories to show
    show_cats = ['Groceries', 'Baby formula', 'Gas', 'Restaurants & Bars', 'Coffee Shops', 'Household']
    
    cat_data = []
    for cat in show_cats:
        if cat in categories:
            c = categories[cat]
            cat_data.append({
                'name': cat,
                'spent': c['spent'],
                'budget': c['budget'],
                'pct': c['percent']
            })
    
    if not cat_data:
        return
    
    y_pos = np.arange(len(cat_data))
    
    for i, cat in enumerate(cat_data):
        # Background bar (budget)
        ax.barh(i, cat['budget'], color=COLORS["gray"], alpha=0.2, height=0.5)
        
        # Progress bar
        pct = cat['pct']
        color = COLORS["red"] if pct > 100 else COLORS["yellow"] if pct > 80 else COLORS["green"]
        ax.barh(i, cat['spent'], color=color, height=0.5)
        
        # Label
        ax.text(-50, i, cat['name'], va='center', ha='right', fontsize=9, color=COLORS["dark"])
        ax.text(cat['budget'] + 50, i, f"{pct:.0f}%", va='center', ha='left', fontsize=9, 
                fontweight='bold', color=color)
    
    ax.set_xlim(-max(c['budget'] for c in cat_data) * 0.5, max(c['budget'] for c in cat_data) * 1.3)
    ax.set_ylim(-0.5, len(cat_data) - 0.5)
    ax.axis('off')


def create_runway_indicator(ax, runway_days, daily_burn):
    """Create visual runway indicator."""
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    # Background track
    ax.barh(0.5, 60, height=0.3, color=COLORS["gray"], alpha=0.2)
    
    # Danger zone (0-15 days)
    ax.barh(0.5, 15, height=0.3, color=COLORS["red"], alpha=0.3)
    
    # Warning zone (15-30 days)
    ax.barh(0.5, 15, left=15, height=0.3, color=COLORS["yellow"], alpha=0.3)
    
    # Safe zone (30+ days)
    ax.barh(0.5, 30, left=30, height=0.3, color=COLORS["green"], alpha=0.3)
    
    # Current position marker
    pos = min(60, runway_days)
    color = COLORS["red"] if pos < 15 else COLORS["yellow"] if pos < 30 else COLORS["green"]
    ax.plot(pos, 0.5, 'v', markersize=15, color=color)
    ax.text(pos, 0.15, f"{runway_days:.0f} days", ha='center', fontsize=10, fontweight='bold', color=color)
    
    # Labels
    ax.text(7.5, 0.85, "Critical", ha='center', fontsize=8, color=COLORS["red"])
    ax.text(22.5, 0.85, "Warning", ha='center', fontsize=8, color=COLORS["yellow"])
    ax.text(45, 0.85, "Safe", ha='center', fontsize=8, color=COLORS["green"])
    
    ax.text(30, -0.1, f"Runway @ ${daily_burn:.0f}/day", ha='center', fontsize=9, color=COLORS["gray"])


def generate_visual_forecast(output_path: str = None) -> str:
    """Generate the visual forecast image."""
    data = get_forecast_data()
    
    if not data:
        print("Could not get forecast data")
        return None
    
    # Extract data
    velocity = data.get("velocity", {})
    runway = data.get("runway", {})
    scenarios = data.get("scenarios", {})
    categories = data.get("categories", {})
    income = data.get("income", {})
    warnings = data.get("warnings", [])
    
    # Create figure with subplots
    fig = plt.figure(figsize=(12, 8), facecolor=COLORS["bg"])
    
    # Title (no emoji - font compatibility)
    now = datetime.now()
    fig.suptitle(f"CASH FLOW FORECAST — {now.strftime('%B %d, %Y')}", 
                 fontsize=18, fontweight='bold', color=COLORS["dark"], y=0.97)
    
    # Grid layout
    gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3, 
                          left=0.08, right=0.92, top=0.88, bottom=0.08)
    
    # Cash gauge (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    liquid = runway.get("liquid_cash", 0)
    create_gauge(ax1, liquid, 10000, "Available Cash", 2000, 5000)
    
    # Burn rate gauge (top middle)
    ax2 = fig.add_subplot(gs[0, 1])
    daily_burn = velocity.get("daily_burn", 0)
    ax2.set_xlim(-1.5, 1.5)
    ax2.set_ylim(-0.2, 1.2)
    ax2.axis('off')
    burn_color = COLORS["red"] if daily_burn > 150 else COLORS["yellow"] if daily_burn > 100 else COLORS["green"]
    ax2.text(0, 0.5, f"${daily_burn:.0f}", fontsize=28, fontweight='bold', 
             ha='center', va='center', color=burn_color)
    ax2.text(0, 0.1, "Daily Burn Rate", fontsize=11, ha='center', va='center', color=COLORS["gray"])
    
    # Income status (top right)
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.axis('off')
    mtd_income = income.get("mtd_income", 0)
    expected = income.get("expected_to_date", 0)
    inc_color = COLORS["green"] if mtd_income >= expected else COLORS["red"]
    ax3.text(0.5, 0.6, f"${mtd_income:,.0f}", fontsize=24, fontweight='bold',
             ha='center', va='center', transform=ax3.transAxes, color=inc_color)
    ax3.text(0.5, 0.3, f"of ${expected:,.0f} expected", fontsize=10,
             ha='center', va='center', transform=ax3.transAxes, color=COLORS["gray"])
    ax3.text(0.5, 0.1, "MTD Income", fontsize=11, ha='center', va='center', 
             transform=ax3.transAxes, color=COLORS["gray"])
    
    # Runway indicator (middle, full width)
    ax4 = fig.add_subplot(gs[1, :])
    runway_days = runway.get("days", 0)
    create_runway_indicator(ax4, runway_days, daily_burn)
    
    # Scenario bars (bottom left, 2 cols)
    ax5 = fig.add_subplot(gs[2, :2])
    create_scenario_bars(ax5, scenarios)
    ax5.set_title("End of Month Scenarios", fontsize=12, fontweight='bold', 
                  color=COLORS["dark"], pad=10)
    
    # Warnings (bottom right)
    ax6 = fig.add_subplot(gs[2, 2])
    ax6.axis('off')
    if warnings:
        warning_text = "\n".join(w[:40] + "..." if len(w) > 40 else w for w in warnings[:4])
        ax6.text(0.05, 0.95, "⚠️ Alerts", fontsize=11, fontweight='bold',
                 transform=ax6.transAxes, va='top', color=COLORS["dark"])
        ax6.text(0.05, 0.75, warning_text, fontsize=8, transform=ax6.transAxes, 
                 va='top', color=COLORS["gray"], linespacing=1.5)
    
    # Save
    OUTPUT_DIR.mkdir(exist_ok=True)
    if output_path is None:
        output_path = str(OUTPUT_DIR / f"forecast_{now.strftime('%Y%m%d_%H%M%S')}.png")
    
    plt.savefig(output_path, dpi=150, facecolor=COLORS["bg"], edgecolor='none', bbox_inches='tight')
    plt.close()
    
    print(f"Saved to: {output_path}")
    return output_path


def main():
    """Generate and output forecast image path."""
    import sys
    
    output_path = sys.argv[1] if len(sys.argv) > 1 else None
    result = generate_visual_forecast(output_path)
    
    if result:
        print(f"\n✅ Visual forecast generated: {result}")
    else:
        print("❌ Failed to generate forecast")
        sys.exit(1)


if __name__ == "__main__":
    main()
