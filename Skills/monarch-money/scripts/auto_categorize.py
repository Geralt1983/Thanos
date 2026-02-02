#!/usr/bin/env python3
"""
Monarch Money Auto-Categorization Rules

Automatically categorizes transactions based on merchant name patterns.
Run manually or via cron for weekly reconciliation.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from monarchmoney import MonarchMoney
except ImportError:
    print("Error: monarchmoney package not installed")
    print("Run: pip install monarchmoney")
    sys.exit(1)


# ============================================================================
# AUTO-CATEGORIZATION RULES
# Format: "merchant_pattern": "category_name"
# Patterns are case-insensitive and match if contained in merchant name
# ============================================================================

CATEGORIZATION_RULES = {
    # Gas & Auto
    "sheetz": "Gas",
    "shell": "Gas",
    "exxon": "Gas",
    "bp ": "Gas",
    "chevron": "Gas",
    "speedway": "Gas",
    "wawa": "Gas",
    "love's": "Gas",
    "pilot": "Gas",
    "car wash": "Car Wash Membership",
    
    # Coffee
    "starbucks": "Coffee Shops",
    "dunkin": "Coffee Shops",
    "cup of joe": "Coffee Shops",
    
    # Restaurants
    "mcdonald": "Restaurants & Bars",
    "chick-fil-a": "Restaurants & Bars",
    "wendy": "Restaurants & Bars",
    "taco bell": "Restaurants & Bars",
    "chipotle": "Restaurants & Bars",
    "olive garden": "Restaurants & Bars",
    "applebee": "Restaurants & Bars",
    "little caesars": "Restaurants & Bars",
    "domino": "Restaurants & Bars",
    "pizza hut": "Restaurants & Bars",
    
    # Groceries
    "walmart": "Groceries",
    "kroger": "Groceries",
    "food lion": "Groceries",
    "aldi": "Groceries",
    "publix": "Groceries",
    "harris teeter": "Groceries",
    "whole foods": "Groceries",
    "trader joe": "Groceries",
    
    # Shopping
    "amazon": "Shopping",  # May need manual review for business
    "target": "Shopping",
    "costco": "Shopping",
    "sam's club": "Shopping",
    "best buy": "Electronics",
    "home depot": "Home Improvement",
    "lowe's": "Home Improvement",
    
    # Children
    "carter's": "Clothing",
    "children's place": "Clothing",
    "toys r us": "Child Activities",
    
    # Subscriptions (likely business)
    "google one": "Business expense",
    "microsoft": "Business expense",
    "adobe": "Business expense",
    "openai": "Business expense",
    "anthropic": "Business expense",
    "github": "Business expense",
    "slack": "Business expense",
    "zoom": "Business expense",
    "dropbox": "Business expense",
    
    # Entertainment
    "netflix": "Entertainment",
    "hulu": "Entertainment",
    "disney+": "Entertainment",
    "spotify": "Entertainment",
    "apple music": "Entertainment",
    "santikos": "Entertainment",
    "amc": "Entertainment",
    "regal": "Entertainment",
}


class MonarchAutoCategorizer:
    """Handles auto-categorization and reconciliation for Monarch Money."""
    
    def __init__(self):
        self.mm = MonarchMoney()
        self.categories_cache: Dict[str, str] = {}  # name -> id mapping
        
    async def login(self):
        """Login using environment variables."""
        email = os.environ.get("MONARCH_EMAIL")
        password = os.environ.get("MONARCH_PASSWORD")
        mfa_secret = os.environ.get("MONARCH_MFA_SECRET")
        
        if not all([email, password]):
            raise ValueError("MONARCH_EMAIL and MONARCH_PASSWORD must be set")
        
        await self.mm.login(
            email=email,
            password=password,
            mfa_secret_key=mfa_secret
        )
        print(f"✓ Logged in as {email}")
    
    async def load_categories(self):
        """Load and cache category name -> ID mapping."""
        categories = await self.mm.get_transaction_categories()
        
        for cat in categories:
            name = cat.get("name", "").lower()
            cat_id = cat.get("id")
            if name and cat_id:
                self.categories_cache[name] = cat_id
        
        print(f"✓ Loaded {len(self.categories_cache)} categories")
    
    def find_category_id(self, category_name: str) -> Optional[str]:
        """Find category ID by name (case-insensitive)."""
        return self.categories_cache.get(category_name.lower())
    
    def match_rule(self, merchant: str) -> Optional[str]:
        """Match merchant against rules, return category name if found."""
        merchant_lower = merchant.lower()
        
        for pattern, category in CATEGORIZATION_RULES.items():
            if pattern in merchant_lower:
                return category
        
        return None
    
    async def get_transactions(self, days: int = 30, limit: int = 100) -> List[Dict]:
        """Fetch recent transactions."""
        # MonarchMoney library uses get_transactions
        transactions = await self.mm.get_transactions(limit=limit)
        return transactions
    
    async def update_category(self, transaction_id: str, category_id: str) -> bool:
        """Update a transaction's category."""
        try:
            await self.mm.update_transaction(
                transaction_id=transaction_id,
                category_id=category_id
            )
            return True
        except Exception as e:
            print(f"  ✗ Failed to update: {e}")
            return False
    
    async def auto_categorize(self, days: int = 30, dry_run: bool = True) -> Dict:
        """
        Auto-categorize transactions based on rules.
        
        Args:
            days: Look back this many days
            dry_run: If True, just report what would change
            
        Returns:
            Summary of changes made/proposed
        """
        print(f"\n{'DRY RUN: ' if dry_run else ''}Auto-categorizing transactions from last {days} days...")
        
        transactions = await self.get_transactions(days=days)
        
        results = {
            "total_reviewed": 0,
            "would_change": [],
            "changed": [],
            "no_rule": [],
            "already_correct": 0,
            "errors": []
        }
        
        for tx in transactions:
            results["total_reviewed"] += 1
            
            merchant = tx.get("merchant", {}).get("name", "") or tx.get("plaidName", "")
            current_category = tx.get("category", {}).get("name", "")
            tx_id = tx.get("id")
            amount = tx.get("amount", 0)
            date = tx.get("date", "")
            
            if not merchant:
                continue
            
            # Check if rule matches
            suggested_category = self.match_rule(merchant)
            
            if not suggested_category:
                results["no_rule"].append({
                    "merchant": merchant,
                    "current_category": current_category,
                    "amount": amount,
                    "date": date
                })
                continue
            
            # Check if already correct
            if current_category.lower() == suggested_category.lower():
                results["already_correct"] += 1
                continue
            
            # Find category ID
            category_id = self.find_category_id(suggested_category)
            if not category_id:
                results["errors"].append(f"Category not found: {suggested_category}")
                continue
            
            change = {
                "id": tx_id,
                "merchant": merchant,
                "amount": amount,
                "date": date,
                "from": current_category,
                "to": suggested_category
            }
            
            if dry_run:
                results["would_change"].append(change)
                print(f"  → {merchant}: {current_category} → {suggested_category}")
            else:
                success = await self.update_category(tx_id, category_id)
                if success:
                    results["changed"].append(change)
                    print(f"  ✓ {merchant}: {current_category} → {suggested_category}")
                else:
                    results["errors"].append(f"Failed to update {merchant}")
        
        return results
    
    async def find_uncategorized(self, days: int = 30) -> List[Dict]:
        """Find transactions that might need manual review."""
        transactions = await self.get_transactions(days=days)
        
        uncategorized = []
        
        for tx in transactions:
            merchant = tx.get("merchant", {}).get("name", "") or tx.get("plaidName", "")
            current_category = tx.get("category", {}).get("name", "")
            
            # Check if no rule exists AND category is generic
            suggested = self.match_rule(merchant) if merchant else None
            
            if not suggested and current_category in ["Uncategorized", "Other", "", None]:
                uncategorized.append({
                    "id": tx.get("id"),
                    "merchant": merchant,
                    "category": current_category,
                    "amount": tx.get("amount", 0),
                    "date": tx.get("date", ""),
                    "account": tx.get("account", {}).get("displayName", "")
                })
        
        return uncategorized
    
    async def review_transactions(self, days: int = 30) -> str:
        """Generate a review report of transactions needing attention."""
        print(f"\n📋 Reviewing transactions from last {days} days...\n")
        
        # Get transactions needing auto-categorization
        auto_results = await self.auto_categorize(days=days, dry_run=True)
        
        # Get uncategorized transactions
        uncategorized = await self.find_uncategorized(days=days)
        
        report = []
        report.append("=" * 60)
        report.append("MONARCH MONEY - TRANSACTION REVIEW")
        report.append(f"Period: Last {days} days")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 60)
        
        # Auto-categorization candidates
        report.append(f"\n📊 AUTO-CATEGORIZATION CANDIDATES: {len(auto_results['would_change'])}")
        if auto_results['would_change']:
            for tx in auto_results['would_change'][:10]:
                report.append(f"  • {tx['merchant']}: {tx['from']} → {tx['to']} (${abs(tx['amount']):.2f})")
            if len(auto_results['would_change']) > 10:
                report.append(f"  ... and {len(auto_results['would_change']) - 10} more")
        
        # Uncategorized needing manual review
        report.append(f"\n⚠️  NEEDS MANUAL REVIEW: {len(uncategorized)}")
        if uncategorized:
            for tx in uncategorized[:10]:
                report.append(f"  • {tx['merchant'] or 'Unknown'}: ${abs(tx['amount']):.2f} ({tx['date']})")
            if len(uncategorized) > 10:
                report.append(f"  ... and {len(uncategorized) - 10} more")
        
        # No rules (might want to add rules for these)
        no_rule_merchants = set(tx['merchant'] for tx in auto_results['no_rule'] if tx['merchant'])
        report.append(f"\n📝 MERCHANTS WITHOUT RULES: {len(no_rule_merchants)}")
        if no_rule_merchants:
            for merchant in list(no_rule_merchants)[:10]:
                report.append(f"  • {merchant}")
            if len(no_rule_merchants) > 10:
                report.append(f"  ... and {len(no_rule_merchants) - 10} more")
        
        # Summary
        report.append(f"\n📈 SUMMARY:")
        report.append(f"  • Total reviewed: {auto_results['total_reviewed']}")
        report.append(f"  • Already correct: {auto_results['already_correct']}")
        report.append(f"  • Can auto-fix: {len(auto_results['would_change'])}")
        report.append(f"  • Needs manual: {len(uncategorized)}")
        
        report.append("\n" + "=" * 60)
        report.append("Run with --apply to auto-categorize transactions")
        report.append("=" * 60)
        
        return "\n".join(report)


async def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monarch Money Auto-Categorization")
    parser.add_argument("--days", type=int, default=30, help="Days to look back")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry run)")
    parser.add_argument("--review", action="store_true", help="Generate review report")
    parser.add_argument("--uncategorized", action="store_true", help="List uncategorized only")
    
    args = parser.parse_args()
    
    categorizer = MonarchAutoCategorizer()
    
    try:
        await categorizer.login()
        await categorizer.load_categories()
        
        if args.review:
            report = await categorizer.review_transactions(days=args.days)
            print(report)
        
        elif args.uncategorized:
            uncategorized = await categorizer.find_uncategorized(days=args.days)
            print(f"\nFound {len(uncategorized)} uncategorized transactions:\n")
            for tx in uncategorized:
                print(f"  {tx['date']} | {tx['merchant'] or 'Unknown':30} | ${abs(tx['amount']):>10.2f}")
        
        else:
            results = await categorizer.auto_categorize(
                days=args.days,
                dry_run=not args.apply
            )
            
            print(f"\n{'Applied' if args.apply else 'Would apply'} {len(results.get('changed', results.get('would_change', [])))} changes")
            if results.get("errors"):
                print(f"Errors: {len(results['errors'])}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
