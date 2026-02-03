#!/usr/bin/env python3
"""
Visual Cash Flow Forecast v2

Enhanced visual forecasts with waterfall charts and sparklines.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import numpy as np

THANOS_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = THANOS_ROOT / "output"

# Modern color palette
COLORS = {
    "primary": "#6366F1",     # Indigo
    "success": "#10B981",     # Emerald
    "warning": "#F59E0B",     # Amber
    "danger": "#EF4444",      # Rose
    "info": "#3B82F6",        # Blue
    "dark": "#111827",        # Gray 900
    "gray": "#6B7280",        # Gray 500
    "light": "#F3F4F6",       # Gray 100
    "white": "#FFFFFF",
    "bg": "#FAFAFA",
    "card": "#FFFFFF",
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


def draw_card(ax, x, y, w, h, title="", shadow=True):
    """Draw a card background."""
    if shadow:
        shadow_rect = FancyBboxPatch((x+2, y-2), w, h, boxstyle="round,pad=0.02,rounding_size=0.02",
                                      facecolor="#00000011", edgecolor='none', transform=ax.transAxes)
        ax.add_patch(shadow_rect)
    
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.02",
                          facecolor=COLORS["card"], edgecolor=COLORS["light"], linewidth=1,
                          transform=ax.transAxes)
    ax.add_patch(rect)
    
    if title:
        ax.text(x + 0.015, y + h - 0.025, title, transform=ax.transAxes,
                fontsize=9, fontweight='bold', color=COLORS["gray"], va='top')


def draw_metric_card(ax, x, y, value, label, color=None, prefix="$", suffix=""):
    """Draw a metric display card."""
    if color is None:
        color = COLORS["dark"]
    
    # Value
    if isinstance(value, (int, float)):
        if prefix == "$":
            display = f"${value:,.0f}{suffix}"
        else:
            display = f"{prefix}{value:,.0f}{suffix}"
    else:
        display = str(value)
    
    ax.text(x, y + 0.03, display, transform=ax.transAxes,
            fontsize=22, fontweight='bold', color=color, va='center', ha='center')
    
    # Label
    ax.text(x, y - 0.025, label, transform=ax.transAxes,
            fontsize=9, color=COLORS["gray"], va='center', ha='center')


def draw_waterfall(ax, data):
    """Draw waterfall chart for cash flow."""
    categories = ['Starting\nCash', 'Income', 'Fixed\nExpenses', 'Variable\nExpenses', 'Projected\nEOM']
    
    # Calculate values
    liquid = data.get("runway", {}).get("liquid_cash", 2500)
    income_expected = data.get("income", {}).get("expected_monthly", 28000)
    
    # Estimate expenses from burn rate
    daily_burn = data.get("velocity", {}).get("daily_burn", 80)
    days_remaining = data.get("projection", {}).get("days_remaining", 26)
    total_expenses = daily_burn * days_remaining
    
    fixed_expenses = total_expenses * 0.4  # Estimate 40% fixed
    variable_expenses = total_expenses * 0.6  # 60% variable
    
    eom = liquid + income_expected - fixed_expenses - variable_expenses
    
    values = [liquid, income_expected, -fixed_expenses, -variable_expenses, eom]
    
    # Calculate cumulative for waterfall
    cumulative = [0]
    running = 0
    for i, v in enumerate(values[:-1]):
        if i == 0:
            running = v
        else:
            running += v
        cumulative.append(running)
    
    # Colors
    colors = []
    for i, v in enumerate(values):
        if i == 0 or i == len(values) - 1:
            colors.append(COLORS["primary"])
        elif v >= 0:
            colors.append(COLORS["success"])
        else:
            colors.append(COLORS["danger"])
    
    x_pos = np.arange(len(categories))
    
    # Draw bars
    for i, (cat, val, cum, col) in enumerate(zip(categories, values, cumulative + [0], colors)):
        if i == 0:
            ax.bar(i, val, color=col, width=0.6, edgecolor='white', linewidth=2)
        elif i == len(values) - 1:
            ax.bar(i, val, color=col, width=0.6, edgecolor='white', linewidth=2)
        else:
            bottom = cumulative[i] if val < 0 else cumulative[i]
            ax.bar(i, abs(val), bottom=bottom - abs(val) if val < 0 else bottom, 
                   color=col, width=0.6, edgecolor='white', linewidth=2)
        
        # Value label
        label_y = val if i == 0 else (cumulative[i] + val/2 if i < len(values)-1 else val)
        if i == len(values) - 1:
            label_y = val
        elif i > 0:
            label_y = cumulative[i] + val/2 if val > 0 else cumulative[i] - abs(val)/2
        
        va = 'bottom' if val > 0 else 'top'
        y_offset = 500 if val > 0 else -500
        
        ax.text(i, val + y_offset if i in [0, len(values)-1] else label_y, 
                f'${abs(val):,.0f}', ha='center', va=va, fontsize=8, fontweight='bold',
                color=col)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_ylabel('Cash ($)', fontsize=9, color=COLORS["gray"])
    ax.axhline(y=0, color=COLORS["dark"], linewidth=0.5, alpha=0.3)
    
    # Clean up
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLORS["light"])
    ax.spines['bottom'].set_color(COLORS["light"])
    ax.tick_params(colors=COLORS["gray"])


def draw_scenario_gauge(ax, scenarios):
    """Draw a horizontal gauge showing scenario range."""
    best = scenarios.get('best_case', {}).get('eom_balance', 1000)
    expected = scenarios.get('expected', {}).get('eom_balance', 500)
    worst = scenarios.get('worst_case', {}).get('eom_balance', -500)
    
    # Determine range
    min_val = min(worst - 500, -1000)
    max_val = max(best + 500, 2000)
    
    ax.set_xlim(min_val, max_val)
    ax.set_ylim(0, 1)
    
    # Background
    ax.axhspan(0.3, 0.7, color=COLORS["light"], alpha=0.5)
    
    # Range bar (worst to best)
    ax.plot([worst, best], [0.5, 0.5], color=COLORS["gray"], linewidth=8, solid_capstyle='round', alpha=0.3)
    
    # Markers
    markers = [
        (worst, COLORS["danger"], "Worst", "top"),
        (expected, COLORS["warning"], "Expected", "bottom"),
        (best, COLORS["success"], "Best", "top"),
    ]
    
    for val, color, label, va in markers:
        ax.plot(val, 0.5, 'o', markersize=14, color=color, markeredgecolor='white', markeredgewidth=2)
        y_text = 0.8 if va == "top" else 0.2
        ax.text(val, y_text, f'${val:,.0f}', ha='center', va='center', fontsize=9, fontweight='bold', color=color)
        ax.text(val, y_text + (0.12 if va == "top" else -0.12), label, ha='center', va='center', fontsize=7, color=COLORS["gray"])
    
    # Zero line
    if min_val < 0 < max_val:
        ax.axvline(x=0, color=COLORS["dark"], linewidth=1, linestyle='--', alpha=0.3)
        ax.text(0, 0.05, '$0', ha='center', fontsize=7, color=COLORS["gray"])
    
    ax.axis('off')


def draw_runway_progress(ax, runway_days, max_days=60):
    """Draw runway as a progress bar."""
    pct = min(1, runway_days / max_days)
    
    # Determine color
    if runway_days < 15:
        color = COLORS["danger"]
        status = "CRITICAL"
    elif runway_days < 30:
        color = COLORS["warning"]
        status = "WARNING"
    else:
        color = COLORS["success"]
        status = "HEALTHY"
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    
    # Background bar
    bg = FancyBboxPatch((0.05, 0.35), 0.9, 0.3, boxstyle="round,pad=0.01,rounding_size=0.1",
                        facecolor=COLORS["light"], edgecolor='none', transform=ax.transAxes)
    ax.add_patch(bg)
    
    # Progress bar
    if pct > 0:
        progress = FancyBboxPatch((0.05, 0.35), 0.9 * pct, 0.3, boxstyle="round,pad=0.01,rounding_size=0.1",
                                  facecolor=color, edgecolor='none', transform=ax.transAxes)
        ax.add_patch(progress)
    
    # Text
    ax.text(0.5, 0.5, f"{runway_days:.0f} DAYS", transform=ax.transAxes,
            ha='center', va='center', fontsize=14, fontweight='bold', color='white' if pct > 0.3 else COLORS["dark"])
    
    ax.text(0.5, 0.1, f"Cash Runway ({status})", transform=ax.transAxes,
            ha='center', va='center', fontsize=9, color=COLORS["gray"])
    
    ax.axis('off')


def draw_sparkline(ax, data_points, color=COLORS["primary"]):
    """Draw a simple sparkline."""
    if not data_points:
        return
    
    x = range(len(data_points))
    ax.fill_between(x, data_points, alpha=0.2, color=color)
    ax.plot(x, data_points, color=color, linewidth=2)
    ax.scatter([len(data_points)-1], [data_points[-1]], color=color, s=30, zorder=5)
    ax.axis('off')


def generate_visual_forecast_v2(output_path: str = None) -> str:
    """Generate enhanced visual forecast."""
    data = get_forecast_data()
    
    if not data:
        print("Could not get forecast data")
        return None
    
    velocity = data.get("velocity", {})
    runway = data.get("runway", {})
    scenarios = data.get("scenarios", {})
    income = data.get("income", {})
    warnings = data.get("warnings", [])
    
    # Create figure
    fig = plt.figure(figsize=(14, 9), facecolor=COLORS["bg"])
    
    # Main axis for cards
    ax_main = fig.add_axes([0, 0, 1, 1])
    ax_main.set_xlim(0, 1)
    ax_main.set_ylim(0, 1)
    ax_main.axis('off')
    
    # Header
    now = datetime.now()
    ax_main.text(0.5, 0.96, "FINANCIAL FORECAST", transform=ax_main.transAxes,
                 fontsize=24, fontweight='bold', color=COLORS["dark"], ha='center')
    ax_main.text(0.5, 0.92, now.strftime('%B %d, %Y'), transform=ax_main.transAxes,
                 fontsize=12, color=COLORS["gray"], ha='center')
    
    # Top metrics row
    draw_card(ax_main, 0.02, 0.72, 0.22, 0.17, "AVAILABLE CASH")
    liquid = runway.get("liquid_cash", 0)
    cash_color = COLORS["success"] if liquid > 3000 else COLORS["warning"] if liquid > 1500 else COLORS["danger"]
    draw_metric_card(ax_main, 0.13, 0.77, liquid, "Current Balance", cash_color)
    
    draw_card(ax_main, 0.26, 0.72, 0.22, 0.17, "DAILY BURN")
    burn = velocity.get("daily_burn", 0)
    burn_color = COLORS["success"] if burn < 100 else COLORS["warning"] if burn < 150 else COLORS["danger"]
    draw_metric_card(ax_main, 0.37, 0.77, burn, "Avg Per Day", burn_color)
    
    draw_card(ax_main, 0.50, 0.72, 0.22, 0.17, "MTD INCOME")
    mtd_income = income.get("mtd_income", 0)
    expected_income = income.get("expected_to_date", 0)
    inc_color = COLORS["success"] if mtd_income >= expected_income else COLORS["danger"]
    draw_metric_card(ax_main, 0.61, 0.77, mtd_income, f"of ${expected_income:,.0f} expected", inc_color)
    
    draw_card(ax_main, 0.74, 0.72, 0.24, 0.17, "PROJECTED EOM")
    eom = scenarios.get("expected", {}).get("eom_balance", 0)
    eom_color = COLORS["success"] if eom > 500 else COLORS["warning"] if eom > 0 else COLORS["danger"]
    draw_metric_card(ax_main, 0.86, 0.77, eom, "Expected Balance", eom_color)
    
    # Runway bar
    draw_card(ax_main, 0.02, 0.56, 0.96, 0.13, "CASH RUNWAY")
    ax_runway = fig.add_axes([0.04, 0.57, 0.92, 0.10])
    draw_runway_progress(ax_runway, runway.get("days", 0))
    
    # Waterfall chart
    draw_card(ax_main, 0.02, 0.20, 0.54, 0.33, "CASH FLOW WATERFALL")
    ax_waterfall = fig.add_axes([0.06, 0.22, 0.46, 0.26])
    draw_waterfall(ax_waterfall, data)
    
    # Scenario gauge
    draw_card(ax_main, 0.58, 0.20, 0.40, 0.33, "END OF MONTH SCENARIOS")
    ax_scenarios = fig.add_axes([0.60, 0.28, 0.36, 0.18])
    draw_scenario_gauge(ax_scenarios, scenarios)
    
    # Alerts panel
    draw_card(ax_main, 0.02, 0.02, 0.96, 0.15, "ALERTS & INSIGHTS")
    
    if warnings:
        # Filter and format warnings
        clean_warnings = []
        for w in warnings[:6]:
            # Remove emoji codes that won't render
            w = w.replace("🔴", "[!]").replace("⚠️", "[!]").replace("ℹ️", "[i]")
            if len(w) > 60:
                w = w[:57] + "..."
            clean_warnings.append(w)
        
        # Display in two columns
        col1 = clean_warnings[:3]
        col2 = clean_warnings[3:6]
        
        for i, w in enumerate(col1):
            ax_main.text(0.04, 0.135 - i*0.035, f"• {w}", transform=ax_main.transAxes,
                        fontsize=8, color=COLORS["dark"])
        
        for i, w in enumerate(col2):
            ax_main.text(0.50, 0.135 - i*0.035, f"• {w}", transform=ax_main.transAxes,
                        fontsize=8, color=COLORS["dark"])
    else:
        ax_main.text(0.5, 0.09, "No alerts - finances looking healthy!", 
                    transform=ax_main.transAxes, fontsize=10, color=COLORS["success"], ha='center')
    
    # Footer
    ax_main.text(0.98, 0.005, "Generated by Thanos Financial System", transform=ax_main.transAxes,
                 fontsize=7, color=COLORS["gray"], ha='right', style='italic')
    
    # Save
    OUTPUT_DIR.mkdir(exist_ok=True)
    if output_path is None:
        output_path = str(OUTPUT_DIR / f"forecast_v2_{now.strftime('%Y%m%d_%H%M%S')}.png")
    
    plt.savefig(output_path, dpi=150, facecolor=COLORS["bg"], edgecolor='none', bbox_inches='tight')
    plt.close()
    
    return output_path


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else None
    result = generate_visual_forecast_v2(output_path)
    
    if result:
        print(f"Generated: {result}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
