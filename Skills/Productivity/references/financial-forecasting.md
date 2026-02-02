# Financial Forecasting & Early Warning System

Research-based patterns and predictive indicators for proactive financial health monitoring.

## Core Forecasting Principles

### 1. Velocity-Based Spending Detection
Track not just amounts, but **rate of spending**.

| Metric | Formula | Warning Threshold |
|--------|---------|-------------------|
| Daily burn rate | MTD spending / days elapsed | >$100/day |
| Weekly velocity | This week vs last week | >30% increase |
| Category acceleration | Category growth rate | >50% week-over-week |

### 2. Runway Calculation
**Cash runway** = Liquid cash ÷ Average daily burn

| Runway | Status | Action |
|--------|--------|--------|
| >30 days | ✅ Healthy | Maintain |
| 15-30 days | ⚠️ Caution | Reduce discretionary |
| <15 days | 🔴 Critical | Emergency mode |

### 3. Projected End-of-Month (EOM) Balance
```
EOM Balance = Current Balance - (Daily Burn × Days Remaining) - Known Bills
```

**Alert if:** Projected EOM < $500 buffer

---

## Behavioral Finance Warning Patterns

### Pattern 1: Subscription Creep
**Signal:** New recurring charges appearing
**Detection:** 
- Any new merchant with "subscription" category
- Same merchant charging monthly
- Small amounts ($5-$30) easy to ignore

**Alert:** "New recurring charge detected: {merchant} ${amount}/mo. Annual cost: ${amount×12}"

### Pattern 2: Lifestyle Inflation
**Signal:** Baseline spending increasing without income increase
**Detection:**
- 3-month rolling average increasing
- Same categories, higher amounts
- "Upgrade" purchases (premium versions)

**Alert:** "Spending baseline up {%} vs 3-month avg. Income unchanged."

### Pattern 3: Impulse Clustering (ADHD-Specific)
**Signal:** Multiple purchases in short timeframe
**Detection:**
- 3+ Amazon orders in 24 hours
- 5+ transactions in single day
- Late-night purchases (10pm-2am)

**Alert:** "Impulse pattern detected: {count} purchases in {hours}h. Total: ${amount}"

### Pattern 4: Avoidance Spending
**Signal:** Spending increases during stress periods
**Detection:**
- Correlation with low Oura readiness
- Increase during known stressful periods
- "Comfort" categories spike (food delivery, entertainment)

**Alert:** "Stress spending pattern: {category} up {%} on low-energy days"

### Pattern 5: The Nickel-and-Dime Drain
**Signal:** Death by 1000 small purchases
**Detection:**
- High transaction count, low average amount
- Coffee + snacks + convenience stores
- "Invisible" spending accumulates

**Alert:** "Small purchase accumulation: {count} transactions under $20 = ${total} this week"

---

## ADHD-Specific Financial Patterns

### Hyperfocus Spending
**Pattern:** Deep dive into a hobby/interest → spending spree
**Detection:** 
- Single category spikes 300%+
- Multiple purchases same merchant/type
- Research → purchase → research → purchase cycle

**Alert:** "Hyperfocus spending: ${amount} on {category} in {days} days"

### Out-of-Sight-Out-of-Mind
**Pattern:** Forgetting about subscriptions, memberships, recurring charges
**Detection:**
- Subscriptions not used (no associated activity)
- Annual renewals approaching
- Forgotten trials converting to paid

**Alert:** "Subscription audit: {count} recurring charges totaling ${monthly}/mo. Review needed?"

### Decision Fatigue Spending
**Pattern:** Poor choices late in day or when depleted
**Detection:**
- Transaction time correlation with poor decisions
- Higher spending per transaction in evening
- Fast food/delivery spikes after 6pm

**Alert:** "Evening spending elevated: ${amount} after 6pm vs ${amount} daytime"

### The "Someday" Trap
**Pattern:** Buying items for future self that never gets used
**Detection:**
- Exercise equipment + no gym visits
- Books accumulating
- Courses/subscriptions unused

**Intervention:** Don't alert, but note in weekly review

---

## Predictive Warning Triggers

### Immediate Alerts (Real-time)

| Trigger | Threshold | Alert |
|---------|-----------|-------|
| Large single purchase | >$200 unplanned | 🔴 Verify intentional |
| Daily spend exceeded | >$150 in 24h | ⚠️ High burn day |
| Impulse cluster | 3+ purchases/hour | ⚠️ Slow down |
| Unusual merchant | First-time + >$50 | ℹ️ New merchant |
| Credit utilization | >30% of limit | ⚠️ Debt creep |

### Daily Brief Alerts

| Check | Trigger | Alert |
|-------|---------|-------|
| Yesterday vs average | >150% of typical | "Spent ${X} yesterday (typical: ${Y})" |
| Week-to-date pace | On track to exceed budget | "Pace: ${projected} / ${budget} this month" |
| Cash runway | <20 days | "Cash runway: {X} days at current pace" |
| Upcoming bills | Within 7 days | "Bills due: ${total} in next 7 days" |

### Weekly Review Alerts

| Analysis | Detection | Alert |
|----------|-----------|-------|
| Category drift | Any category >120% of budget | "Over budget: {categories}" |
| Spending trend | 3 weeks increasing | "Upward spending trend detected" |
| Subscription audit | Quarterly | "Review {count} subscriptions: ${monthly}/mo" |
| Savings rate | <10% of income | "Savings rate below target" |

### Monthly Forecast Alerts

| Projection | Trigger | Alert |
|------------|---------|-------|
| EOM balance | <$1000 projected | "Tight month ahead: ${projected} EOM" |
| Upcoming large expenses | Known bills/annual charges | "Large expense coming: {description}" |
| Seasonal patterns | Holiday/back-to-school/etc | "Historically high spending month" |
| Income gaps | Irregular pay periods | "Gap between paychecks: {days} days" |

---

## Implementation: Morning Brief Integration

### Daily Financial Section

```
💰 FINANCIAL PULSE
━━━━━━━━━━━━━━━━━━
Cash: $X,XXX | Cards: -$X,XXX
Runway: XX days @ $XX/day burn

MTD: $X,XXX / $2,750 (XX%)
Pace: ${projected} by EOM

{warnings if any}
━━━━━━━━━━━━━━━━━━
```

### Warning Priority

1. 🔴 **CRITICAL**: Runway <15 days, projected negative balance
2. ⚠️ **WARNING**: Category >100% budget, high burn rate
3. ℹ️ **INFO**: Approaching limits, new patterns detected

---

## Data Sources for Forecasting

1. **Monarch Money** (via CLI)
   - Transaction history
   - Account balances
   - Category totals

2. **Oura Ring** (via API)
   - Readiness score correlation
   - Sleep → spending patterns

3. **Calendar** (via gog)
   - Upcoming events with costs
   - Travel/vacation planning

4. **Historical patterns**
   - Same month last year
   - Seasonal spending curves

---

## Formulas Reference

### Daily Burn Rate
```python
daily_burn = mtd_spending / days_elapsed_in_month
```

### Projected EOM Spending
```python
projected_eom = (mtd_spending / days_elapsed) * days_in_month
```

### Cash Runway
```python
runway_days = liquid_cash / avg_daily_burn
```

### Category Velocity
```python
velocity = (this_week_spending - last_week_spending) / last_week_spending * 100
```

### Budget Pace
```python
expected_pace = (budget / days_in_month) * days_elapsed
actual_vs_expected = (mtd_spending / expected_pace) * 100
# >100% = over pace, <100% = under pace
```
