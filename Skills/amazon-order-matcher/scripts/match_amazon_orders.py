#!/usr/bin/env python3
"""
Amazon Order Matcher - Match Amazon orders to Monarch transactions and auto-categorize.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add Thanos root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Category mapping: Amazon category keywords → Monarch category IDs
CATEGORY_MAP = {
    # Baby
    'baby': '225123032227674020',  # Baby formula
    'diaper': '225123032227674020',
    'infant': '225123032227674020',
    
    # Groceries
    'grocery': '162777981853398771',
    'food': '162777981853398771',
    'snack': '162777981853398771',
    'pantry': '162777981853398771',
    
    # Household
    'home': '162959461244237526',
    'kitchen': '162959461244237526',
    'household': '162959461244237526',
    'cleaning': '162959461244237526',
    
    # Health
    'health': '178464170624185526',  # Healthcare
    'vitamin': '178463219548976387',  # Supplements
    'supplement': '178463219548976387',
    
    # Electronics/Business
    'electronic': '178527072205960399',  # Business Expenses
    'computer': '178527072205960399',
    'office': '178527072205960399',
    'cable': '178527072205960399',
    'tech': '178527072205960399',
    
    # Clothing
    'clothing': '162777981853398780',
    'apparel': '162777981853398780',
    'shoes': '162777981853398780',
    
    # Toys/Kids
    'toy': '164848301004322293',  # Kids Spending
    'game': '164848301004322293',
    
    # Pet
    'pet': '178463275114067270',  # Dog Care
    'dog': '178463275114067270',
    
    # Books/Education
    'book': '162777981853398786',  # Education
    'kindle': '225122791379203427',  # Subscription
    
    # Furniture
    'furniture': '162777981853398781',  # Furniture & Housewares
    
    # Default catch-all
    'default': '162782301949818821',  # Jeremy Spending Money
}

def get_monarch_category(item_description):
    """Map Amazon item description to Monarch category ID."""
    desc_lower = item_description.lower()
    
    for keyword, category_id in CATEGORY_MAP.items():
        if keyword in desc_lower:
            return category_id
    
    return CATEGORY_MAP['default']

def scrape_amazon_orders(start_date, end_date):
    """
    Scrape Amazon order history using browser automation.
    Returns list of orders with: order_id, date, amount, items[], category
    """
    print(f"Scraping Amazon orders from {start_date} to {end_date}...")
    print("This will open Amazon in your browser...")
    print("Please ensure you're logged into Amazon first.\n")
    
    import subprocess
    
    # Use Node.js scraper with Playwright
    scraper_path = Path(__file__).parent / 'scrape_amazon.js'
    
    try:
        result = subprocess.run(
            ['node', str(scraper_path), start_date, end_date],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            print(f"Error scraping Amazon: {result.stderr}")
            return []
        
        # Parse JSON output
        orders = json.loads(result.stdout)
        return orders
        
    except subprocess.TimeoutExpired:
        print("⚠️  Scraping timed out after 2 minutes")
        return []
    except json.JSONDecodeError as e:
        print(f"Failed to parse Amazon order data: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def get_monarch_transactions(start_date, end_date):
    """Get uncategorized Monarch transactions for date range."""
    import subprocess
    
    cmd = [
        'node',
        '/Users/jeremy/Projects/Thanos/skills/monarch-money/dist/cli/index.js',
        'tx', 'search',
        '--start', start_date,
        '--end', end_date,
        '--limit', '500',
        '--json'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd='/Users/jeremy/Projects/Thanos/skills/monarch-money')
    
    if result.returncode != 0:
        print(f"Error fetching Monarch transactions: {result.stderr}")
        return []
    
    # Parse JSON output (need to extract from CLI output)
    # The CLI outputs logs + JSON, so we need to find the JSON part
    output = result.stdout
    try:
        # Find JSON array in output
        json_start = output.find('[')
        if json_start == -1:
            print("No JSON found in Monarch output")
            return []
        
        json_data = output[json_start:]
        transactions = json.loads(json_data)
        
        # Filter to Amazon and uncategorized
        amazon_txs = [
            tx for tx in transactions
            if 'amazon' in tx.get('merchant', {}).get('name', '').lower()
            and tx.get('category', {}).get('name') == 'Uncategorized'
        ]
        
        return amazon_txs
    except json.JSONDecodeError as e:
        print(f"Failed to parse Monarch JSON: {e}")
        return []

def match_orders_to_transactions(orders, transactions):
    """Match Amazon orders to Monarch transactions by amount and date."""
    matches = []
    
    for tx in transactions:
        tx_amount = abs(float(tx.get('amount', 0)))
        tx_date = datetime.strptime(tx.get('date', ''), '%Y-%m-%d')
        
        for order in orders:
            order_amount = float(order.get('amount', 0))
            order_date = datetime.strptime(order.get('date', ''), '%Y-%m-%d')
            
            # Match if amount matches and date within ±2 days
            amount_match = abs(tx_amount - order_amount) < 0.01
            date_diff = abs((tx_date - order_date).days)
            date_match = date_diff <= 2
            
            if amount_match and date_match:
                matches.append({
                    'transaction_id': tx.get('id'),
                    'order_id': order.get('order_id'),
                    'amount': tx_amount,
                    'date': tx.get('date'),
                    'items': order.get('items', []),
                    'suggested_category': get_monarch_category(' '.join(order.get('items', []))),
                })
                break
    
    return matches

def update_monarch_transactions(matches, dry_run=False):
    """Update Monarch transactions with matched categories."""
    import subprocess
    
    updated = 0
    for match in matches:
        tx_id = match['transaction_id']
        category_id = match['suggested_category']
        items_summary = ', '.join(match['items'][:3])  # First 3 items
        
        print(f"  {match['date']} ${match['amount']:.2f} → {items_summary}")
        
        if dry_run:
            print(f"  [DRY RUN] Would update transaction {tx_id} to category {category_id}")
            continue
        
        cmd = [
            'node',
            '/Users/jeremy/Projects/Thanos/skills/monarch-money/dist/cli/index.js',
            'tx', 'update', tx_id,
            '-c', category_id,
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd='/Users/jeremy/Projects/Thanos/skills/monarch-money'
        )
        
        if 'updated successfully' in result.stderr.lower():
            updated += 1
        else:
            print(f"  ⚠️  Update may have failed: {result.stderr[:100]}")
    
    return updated

def main():
    parser = argparse.ArgumentParser(description='Match Amazon orders to Monarch transactions')
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='Show matches without updating')
    
    args = parser.parse_args()
    
    print("Amazon Order Matcher\n")
    
    # Step 1: Scrape Amazon orders
    orders = scrape_amazon_orders(args.start, args.end)
    print(f"✓ Found {len(orders)} Amazon orders\n")
    
    # Step 2: Get Monarch transactions
    print("Fetching Monarch transactions...")
    transactions = get_monarch_transactions(args.start, args.end)
    print(f"✓ Found {len(transactions)} uncategorized Amazon transactions\n")
    
    # Step 3: Match orders to transactions
    print("Matching orders to transactions...")
    matches = match_orders_to_transactions(orders, transactions)
    print(f"✓ Matched {len(matches)} transactions\n")
    
    if not matches:
        print("No matches found.")
        return
    
    # Step 4: Update Monarch
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Updating Monarch transactions:\n")
    updated = update_monarch_transactions(matches, dry_run=args.dry_run)
    
    if not args.dry_run:
        print(f"\n✓ Updated {updated} transactions")
    
if __name__ == '__main__':
    main()
