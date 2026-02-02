# Monarch Money - Remaining Categorization Guide

## Status
✅ **Done:** 724 transactions marked as reviewed (you completed this)  
⚠️ **Remaining:** 241 transactions need category remapping  
📝 **Manual review:** 35 transactions (one-offs, need individual attention)

## API Issue
Monarch's API rejects bulk transaction updates with generic errors. Not a rate limit issue - their API isn't designed for this use case. **Recommended: Use the app's built-in bulk features** (5 minutes vs 12+ hours of API failures).

---

## Quick Recategorization (5 minutes in app)

### Method 1: Bulk Change by Category

1. **Open Monarch app** → Transactions
2. **Filter by category** (use search)
3. **Select All** (checkbox at top)
4. **Change Category** (bulk action button)
5. **Repeat for each mapping below**

### Category Mappings (241 transactions total)

| Current Category | New Category | Count | Notes |
|-----------------|--------------|-------|-------|
| **Coffee Shops** | Restaurants & Bars | 44 | Starbucks, Dunkin', etc. |
| **Streaming** | Entertainment | 13 | Disney+, Netflix, etc. |
| **Gas & Electric** | Utilities | 4 | Duke Energy |
| **Medical** | Health & Wellness | 6 | Novant Health, etc. |
| **Prescriptions** | Health & Wellness | 5 | |
| **Gifts** | Jeremy Spending Money | 10 | Cash App, Etsy |
| **Family Activities** | Jeremy Spending Money | 5 | Cash withdrawals |
| **Child Activities** | Jeremy Spending Money | 4 | Girl Scouts, etc. |
| **School expense** | Jeremy Spending Money | 3 | Yearbooks, etc. |
| **Education** | Jeremy Spending Money | 8 | EF Education |
| **Dog Care** | Household | 2 | |
| **Dog Grooming** | Household | 2 | |
| **Personal Loan** | Jeremy Spending Money | 55 | Affirm, Klarna purchases |
| **Auto Maintenance** | Transportation | 2 | |
| **Car Insurance** | Transportation | 2 | Geico |
| **Auto Payment** | Transportation | 2 | Honda Financial |
| **Supplements** | Health & Wellness | 4 | Vitamin Shoppe, etc. |
| **Internet & Cable** | Utilities | 2 | Spectrum |
| **Water** | Utilities | 1 | |
| **Cafeteria** | Restaurants & Bars | 2 | LINQ Connect |
| **Student Loans** | Jeremy Spending Money | 8 | MOHELA, Dept of Ed |
| **Taxes** | Jeremy Spending Money | 1 | US Treasury |
| **HOA** | Utilities | 2 | HOA dues |
| **Helping out others** | Jeremy Spending Money | 2 | Venmo, etc. |
| **DVC** | Travel & Vacation | 1 | Timeshare payment |

**Plus Uncategorized (pattern-matched):**
- Amazon → Jeremy Spending Money (40+)
- PlayStation/Gaming → Entertainment (8)
- Best Buy → Jeremy Spending Money (5)
- Klarna/Affirm → Jeremy Spending Money (already in Personal Loan)
- Postal Service → Household (2)
- City/County fees → Utilities (3)

---

## Method 2: Create Transaction Rules (Prevents Future Issues)

**Settings → Rules → New Rule**

Example rules to create:

```
IF Category = "Coffee Shops"
THEN Set Category = "Restaurants & Bars"
☑ Apply to existing transactions

IF Category = "Streaming"  
THEN Set Category = "Entertainment"
☑ Apply to existing transactions

IF Category = "Medical" OR "Prescriptions"
THEN Set Category = "Health & Wellness"
☑ Apply to existing transactions

IF Category = "Personal Loan"
THEN Set Category = "Jeremy Spending Money"
☑ Apply to existing transactions
```

Creating rules with "Apply to existing" will automatically recategorize matching transactions.

---

## Manual Review (35 transactions)

These need individual attention - saved in `/tmp/manual_review.json`:

- Hair products (Sephora) - decide category
- Accountability software - Business or Jeremy Spending?
- Apple purchases (no description) - check receipts
- WFU Athletic tickets - Entertainment?
- Bossasaservice.com - unknown charge
- Railway.com (recurring) - Business
- Every Ever Trial - subscription?

**Recommendation:** Review these in the app with full transaction details visible.

---

## Files Created

- `/tmp/category_updates.json` - 241 transactions with new categories mapped
- `/tmp/manual_review.json` - 35 transactions needing individual attention
- `/tmp/categorize_and_review.js` - Script (API failed, not recommended)

---

## Why API Failed

Monarch's GraphQL API returns generic "Something went wrong" errors for bulk transaction updates. Likely causes:
1. Transactions already in review state can't be bulk updated
2. API designed for single updates, not batch operations
3. Session/auth state issues with rapid sequential requests

**Bottom line:** Use the app. It's faster and actually works.

---

## Estimated Time

- **App bulk change:** 5-10 minutes (select category → select all → change)
- **Transaction rules:** 10 minutes (creates + applies automatically)
- **Manual review:** 10 minutes (35 transactions one-by-one)

**Total: ~30 minutes** to complete all 276 remaining transactions.
