#!/usr/bin/env node
/**
 * Scrape Amazon order history using Playwright
 * Outputs JSON array of orders
 */

const { chromium } = require('playwright');
const fs = require('fs');

async function scrapeAmazonOrders(startDate, endDate) {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const context = browser.contexts()[0];
  const page = await context.newPage();

  console.error('Navigating to Amazon order history...');
  await page.goto('https://www.amazon.com/gp/your-account/order-history', {
    waitUntil: 'networkidle',
    timeout: 30000
  });

  // Check if logged in
  const loginRequired = await page.locator('input[name="email"]').count() > 0;
  if (loginRequired) {
    console.error('⚠️  Not logged in to Amazon. Please login manually in the browser.');
    await browser.close();
    process.exit(1);
  }

  console.error('Logged in. Filtering orders by date...');

  // Filter by date range
  await page.selectOption('select[name="timeFilter"]', 'year-2026');
  await page.waitForTimeout(2000);

  const orders = [];
  let hasMore = true;
  let pageNum = 1;

  while (hasMore && pageNum <= 10) {  // Max 10 pages
    console.error(`Scraping page ${pageNum}...`);

    // Extract orders from current page
    const pageOrders = await page.evaluate(() => {
      const orderCards = document.querySelectorAll('.order-card, .order');
      const results = [];

      orderCards.forEach(card => {
        // Extract order date
        const dateEl = card.querySelector('.order-date-invoice-item, .a-span4 .a-size-base');
        const dateText = dateEl?.textContent || '';
        const dateMatch = dateText.match(/(\w+ \d+, \d{4})/);
        const orderDate = dateMatch ? new Date(dateMatch[1]).toISOString().split('T')[0] : '';

        // Extract order total
        const totalEl = card.querySelector('.order-total .value, .grand-total-price');
        const totalText = totalEl?.textContent || '';
        const totalMatch = totalText.match(/\$?([\d,]+\.\d{2})/);
        const total = totalMatch ? parseFloat(totalMatch[1].replace(',', '')) : 0;

        // Extract items
        const itemEls = card.querySelectorAll('.product-title, .a-link-normal[href*="/dp/"]');
        const items = Array.from(itemEls).map(el => el.textContent.trim()).filter(Boolean);

        // Extract order ID
        const orderIdEl = card.querySelector('.order-id, .order-info-value');
        const orderId = orderIdEl?.textContent.trim().replace(/Order #/, '') || '';

        if (orderDate && total > 0) {
          results.push({
            order_id: orderId,
            date: orderDate,
            amount: total,
            items: items.slice(0, 5)  // First 5 items
          });
        }
      });

      return results;
    });

    orders.push(...pageOrders);

    // Check for next page
    const nextButton = await page.locator('a:has-text("Next"), .a-pagination .a-last:not(.a-disabled)').count();
    if (nextButton > 0) {
      await page.click('a:has-text("Next"), .a-pagination .a-last a');
      await page.waitForTimeout(2000);
      pageNum++;
    } else {
      hasMore = false;
    }
  }

  await browser.close();

  // Filter by date range
  const start = new Date(startDate);
  const end = new Date(endDate);
  const filtered = orders.filter(order => {
    const orderDate = new Date(order.date);
    return orderDate >= start && orderDate <= end;
  });

  return filtered;
}

// Parse command line args
const args = process.argv.slice(2);
const startDate = args[0];
const endDate = args[1];

if (!startDate || !endDate) {
  console.error('Usage: node scrape_amazon.js <start-date> <end-date>');
  process.exit(1);
}

scrapeAmazonOrders(startDate, endDate)
  .then(orders => {
    console.log(JSON.stringify(orders, null, 2));
    console.error(`\n✓ Scraped ${orders.length} orders`);
  })
  .catch(err => {
    console.error('Error scraping Amazon:', err.message);
    process.exit(1);
  });
