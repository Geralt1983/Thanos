#!/usr/bin/env python3
"""
Quick Amazon categorization - uses simple heuristics without scraping.
Categorizes Amazon transactions based on amount patterns and date.
"""

import subprocess
import json
import sys

# Category mapping based on common patterns
def categorize_amazon_amount(amount):
    """Guess category based on amount."""
    amt = abs(float(amount))
    
    # Common patterns
    if amt < 15:
        return ('162782301949818821', 'Shopping (small item)')  # Jeremy Spending
    elif amt < 30:
        return ('162959461244237526', 'Household (likely)')  # Household
    elif amt < 60:
        return ('225123032227674020', 'Baby/Household')  # Baby formula
    elif amt < 100:
        return ('162959461244237526', 'Household')
    else:
        return ('178527072205960399', 'Business/Large purchase')  # Business Expenses

def get_uncategorized_amazon_transactions(start_date, end_date):
    """Get uncategorized Amazon transactions from Monarch."""
    import re
    
    cmd = [
        'node',
        '/Users/jeremy/Projects/Thanos/skills/monarch-money/dist/cli/index.js',
        'tx', 'search',
        '--start', start_date,
        '--end', end_date,
        '--limit', '500'
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd='/Users/jeremy/Projects/Thanos/skills/monarch-money'
    )
    
    # Parse output to find Amazon + Uncategorized
    # Format: │ ID │ Date │ Merchant │ Amount │ Category │ Account │
    lines = result.stdout.split('\n')
    amazon_uncategorized = []
    
    for line in lines:
        if 'Amazon' in line and 'Uncategorized' in line:
            # Use regex to extract columns
            match = re.search(r'│\s*(\d+)\s*│\s*([^│]+)│\s*Amazon\s*│\s*(-?\$[\d.]+)\s*│\s*Uncategorized', line)
            if match:
                tx_id = match.group(1).strip()
                date_str = match.group(2).strip()
                amount_str = match.group(3).strip()
                
                amazon_uncategorized.append({
                    'id': tx_id,
                    'date': date_str,
                    'amount': amount_str
                })
    
    return amazon_uncategorized

def auto_categorize(transactions, dry_run=False):
    """Auto-categorize transactions based on amount heuristics."""
    updated = 0
    
    for tx in transactions:
        category_id, category_name = categorize_amazon_amount(tx['amount'].replace('$', '').replace('-', ''))
        
        print(f"{tx['date']} {tx['amount']:>10s} → {category_name}")
        
        if dry_run:
            continue
        
        cmd = [
            'node',
            '/Users/jeremy/Projects/Thanos/skills/monarch-money/dist/cli/index.js',
            'tx', 'update', tx['id'],
            '-c', category_id
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd='/Users/jeremy/Projects/Thanos/skills/monarch-money'
        )
        
        if 'updated successfully' in result.stderr.lower():
            updated += 1
    
    return updated

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--dry-run', action='store_true')
    
    args = parser.parse_args()
    
    print("Quick Amazon Categorization (amount-based heuristics)\n")
    
    print(f"Fetching uncategorized Amazon transactions...")
    txs = get_uncategorized_amazon_transactions(args.start, args.end)
    print(f"Found {len(txs)} uncategorized Amazon transactions\n")
    
    if not txs:
        print("No uncategorized Amazon transactions found.")
        sys.exit(0)
    
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Auto-categorizing:\n")
    updated = auto_categorize(txs, dry_run=args.dry_run)
    
    if not args.dry_run:
        print(f"\n✓ Updated {updated} transactions")
