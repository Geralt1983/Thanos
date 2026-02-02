#!/Users/jeremy/Projects/Thanos/.venv/bin/python

import os
import json
import logging
from datetime import datetime, timedelta

# Monarch Money CLI import
import monarch_money_cli as monarch

# Browser interaction
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/Users/jeremy/Projects/Thanos/logs/amazon_order_matcher.log'
)

# Category Mapping
CATEGORY_MAP = {
    'Baby': 225123032227674020,
    'Household': 162959461244237526,
    'Business': 178462006985127548,
    'Personal': 162782301949818821,
    'Transportation': 162777981853398770,
    'Gifts': 162777981853398756
}

class AmazonOrderMatcher:
    def __init__(self, orders_file='/Users/jeremy/Projects/Thanos/Skills/amazon-order-matcher/data/amazon_orders_2026.json'):
        self.orders_file = orders_file
        self.orders = self.load_orders()
    
    def load_orders(self):
        """Load existing Amazon orders from JSON file."""
        if os.path.exists(self.orders_file):
            with open(self.orders_file, 'r') as f:
                return json.load(f)
        return []
    
    def scrape_new_orders(self):
        """Use browser automation to scrape new Amazon orders."""
        driver = webdriver.Chrome()  # Assuming Chrome WebDriver
        driver.get('https://www.amazon.com/your-orders/orders?timeFilter=year-2026')
        
        try:
            # Wait for orders to load
            orders = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.order-card'))
            )
            
            new_orders = []
            for order in orders:
                # Extract order details
                date = order.find_element(By.CSS_SELECTOR, '.order-date').text
                total = order.find_element(By.CSS_SELECTOR, '.order-total').text
                items = order.find_elements(By.CSS_SELECTOR, '.item-title')
                
                new_orders.append({
                    'date': date,
                    'total': total,
                    'items': [item.text for item in items]
                })
            
            # Save new orders
            self.orders.extend(new_orders)
            self.save_orders()
            
            return new_orders
        finally:
            driver.quit()
    
    def save_orders(self):
        """Save orders to JSON file."""
        with open(self.orders_file, 'w') as f:
            json.dump(self.orders, f, indent=2)
    
    def match_monarch_transactions(self, days_tolerance=3):
        """
        Match Amazon orders to Monarch transactions.
        
        Args:
            days_tolerance: Number of days to allow for bank posting differences
        """
        # Get uncategorized Monarch transactions
        uncategorized_txns = monarch.get_uncategorized_transactions()
        
        matches = []
        for txn in uncategorized_txns:
            for order in self.orders:
                # Check if transaction amount matches order total within tolerance
                if abs(float(txn['amount']) - float(order['total'])) < 0.01:
                    # Check date within tolerance
                    txn_date = datetime.strptime(txn['date'], '%Y-%m-%d')
                    order_date = datetime.strptime(order['date'], '%B %d, %Y')
                    
                    if abs((txn_date - order_date).days) <= days_tolerance:
                        # Determine category based on items
                        category = self.categorize_order(order)
                        
                        matches.append({
                            'transaction_id': txn['id'],
                            'order_date': order['date'],
                            'amount': txn['amount'],
                            'category_id': category
                        })
        
        return matches
    
    def categorize_order(self, order):
        """
        Determine Monarch category based on order items.
        
        Heuristics:
        - Check for specific keywords
        - Fallback to default 'Personal' category
        """
        item_keywords = {
            'Baby': ['baby', 'diaper', 'formula', 'infant'],
            'Household': ['home', 'kitchen', 'cleaning', 'appliance'],
            'Business': ['tool', 'equipment', 'work', 'office'],
            'Transportation': ['car', 'auto', 'vehicle'],
            'Gifts': ['gift', 'present']
        }
        
        for category, keywords in item_keywords.items():
            if any(keyword in ' '.join(order['items']).lower() for keyword in keywords):
                return CATEGORY_MAP[category]
        
        return CATEGORY_MAP['Personal']
    
    def batch_update_monarch(self, matches):
        """
        Update Monarch transactions with matched categories.
        
        Args:
            matches: List of matched transactions with category IDs
        """
        for match in matches:
            monarch.update_transaction_category(
                transaction_id=match['transaction_id'], 
                category_id=match['category_id']
            )
        
        logging.info(f"Updated {len(matches)} Monarch transactions")

def main():
    matcher = AmazonOrderMatcher()
    
    try:
        # Scrape new orders
        new_orders = matcher.scrape_new_orders()
        logging.info(f"Scraped {len(new_orders)} new Amazon orders")
        
        # Match to Monarch transactions
        matches = matcher.match_monarch_transactions()
        logging.info(f"Found {len(matches)} transaction matches")
        
        # Update Monarch categories
        matcher.batch_update_monarch(matches)
        
    except Exception as e:
        logging.error(f"Error in Amazon Order Matcher: {e}")

if __name__ == '__main__':
    main()