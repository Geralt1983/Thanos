# Finance Skill

## Overview
Financial tracking, invoicing, and business management. Future integration planned with Monarch Money.

## Status
**PARTIAL** - Basic business tracking active, Monarch Money MCP integration planned

## USE WHEN
- User mentions: money, invoice, billing, hours, rate, payment, client payment, financial planning
- User mentions: "budget", "balance", "spending", "finances", "cash flow"
- User asks about finances, spending, or budgets
- Financial planning or review requested
- Expense categorization needed
- Invoice or payment tracking
- System needs to: alert on low balance, include in daily briefing

## Business Overview
- Target annual revenue: $500k+
- Target weekly hours: 15-20 billable
- Implied hourly rate target: $480-640/hr effective

## Client Billing

### Active Clients
| Client | Rate | Terms | Status |
|--------|------|-------|--------|
| Memphis | [Rate] | [Net 30?] | Active |
| Raleigh | [Rate] | [Terms] | Active |
| Orlando | [Rate] | [Terms] | Active |
| Nova | [Rate] | [Terms] | Active |
| Baptist Rehab | [Rate] | [Terms] | Active |

## Workflow Routing
- Invoice creation -> Workflows/InvoiceTracking.md
- Hour tracking -> Workflows/BillableHours.md
- Quarterly review -> Workflows/QuarterlyReview.md

## Weekly Tracking
- Log billable hours daily
- Target: 15-20 hours/week
- Review: Every Friday

## Monthly Tasks
- [ ] Send invoices (1st of month)
- [ ] Follow up on outstanding (15th)
- [ ] Review cash flow

## Quarterly Tasks
- [ ] Revenue review
- [ ] Rate evaluation
- [ ] Client profitability analysis
- [ ] Tax preparation

## Invoice Process
1. Export hours from tracking
2. Create invoice per client
3. Send with clear terms
4. Track in Workflows/InvoiceTracking.md
5. Follow up on outstanding

## Financial Health Indicators
- Runway: [months of expenses covered]
- Outstanding invoices: [total]
- This month revenue: [amount]
- YTD revenue: [amount]

## Red Flags
- Hours below 10/week for 2+ weeks
- Invoice outstanding > 45 days
- Single client > 50% of revenue
- Rate pressure from clients

## Gating Rules
```
IF balance < alert_threshold:
    -> Surface in daily briefing
    -> Block non-essential task creation

IF upcoming_bills > available:
    -> Alert immediately
    -> Suggest payment prioritization
```

---

## Planned: Monarch Money Integration

### Data Sources (Future)
| Tool | Data Provided |
|------|---------------|
| `get_accounts` | Account balances, types |
| `get_transactions` | Recent transactions |
| `get_budgets` | Budget categories and status |
| `get_goals` | Financial goals progress |
| `get_cashflow` | Income vs expenses |

### Planned Features

#### Transaction Insights
- Daily/weekly spending summaries
- Category breakdown
- Anomaly detection (unusual spending)
- Recurring charge tracking

#### Budget Management
- Budget vs actual by category
- Alerts when approaching limits
- Savings rate tracking
- Goal progress updates

#### Work-Finance Integration
- Client payment tracking
- Invoice status correlation
- Revenue forecasting
- Tax preparation helpers

### Future Workflows
- `workflows/Projection.md` - Cash flow projection
- `workflows/BudgetCheck.md` - Budget vs actual
- `workflows/DailyFinance.md` - Yesterday's spending, balances, alerts
- `workflows/SpendingAnalysis.md` - Category breakdown, trends
- `workflows/InvoiceTracker.md` - Pending invoices, payment history

### Future Tools
- `tools/monarch_bridge.py` - Monarch API wrapper

## Integration Points

### With Orchestrator
- Include finance summary in morning brief (opt-in)
- Alert on important financial events

### With TaskRouter
- Detect finance-related queries
- Route to appropriate financial workflow

### With WorkOS
- Correlate client tasks with payments
- Track billable work against invoices

## Configuration (Planned)

```yaml
finance:
  enabled: false  # Enable when Monarch MCP ready

  morning_brief:
    include_balance: true
    include_spending: true
    include_alerts: true

  alerts:
    budget_threshold: 0.8  # Alert at 80% of budget
    unusual_transaction: 500  # Flag transactions over $500
    bill_reminder_days: 3  # Remind 3 days before due

  privacy:
    show_amounts: true  # Can hide actual amounts
    show_accounts: true
```

## Current Behavior

When user asks about personal finances (not client billing):
```
Personal finance tracking via Monarch Money isn't set up yet.
This feature is planned for future integration.

In the meantime, you can:
- Create a task to review finances manually
- Set a reminder for financial review
- Tell me what financial tracking features would be most valuable to you

For client billing and invoicing, I can help with that now.
```

## Implementation Notes

### Prerequisites
1. Monarch Money MCP server created
2. User's Monarch Money credentials configured
3. Privacy settings reviewed with user
4. Initial sync completed

### Security Considerations
- No financial data cached locally
- Read-only access (no transactions)
- Amounts can be hidden in responses
- No sharing of financial data with other services

## Roadmap

| Phase | Features |
|-------|----------|
| **Current** | Client billing tracking, invoice management |
| **v1** | Basic balance and transaction queries |
| **v2** | Budget tracking and alerts |
| **v3** | Spending analysis and insights |
| **v4** | Work-finance correlation (invoices) |
