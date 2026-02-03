#!/usr/bin/env node
/**
 * Browserbase connection helper for Thanos.
 * Creates sessions and connects Playwright to cloud browser.
 */

const { chromium } = require('playwright');

const BROWSERBASE_API_KEY = process.env.BROWSERBASE_API_KEY;
const BROWSERBASE_API_URL = 'https://api.browserbase.com';

async function createSession(options = {}) {
  const response = await fetch(`${BROWSERBASE_API_URL}/v1/sessions`, {
    method: 'POST',
    headers: {
      'x-bb-api-key': BROWSERBASE_API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      projectId: options.projectId || process.env.BROWSERBASE_PROJECT_ID,
      browserSettings: {
        fingerprint: { devices: ['desktop'] },
        ...options.browserSettings,
      },
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to create session: ${response.status} ${error}`);
  }

  return response.json();
}

async function connectToSession(sessionId) {
  const wsUrl = `wss://connect.browserbase.com?apiKey=${BROWSERBASE_API_KEY}&sessionId=${sessionId}`;
  const browser = await chromium.connectOverCDP(wsUrl);
  return browser;
}

async function createAndConnect(options = {}) {
  const session = await createSession(options);
  console.error(`Session created: ${session.id}`);
  const browser = await connectToSession(session.id);
  return { browser, session };
}

// CLI mode
if (require.main === module) {
  const args = process.argv.slice(2);
  const command = args[0];

  (async () => {
    try {
      if (command === 'test') {
        console.log('Testing Browserbase connection...');
        const { browser, session } = await createAndConnect();
        const context = browser.contexts()[0];
        const page = context.pages()[0] || await context.newPage();
        
        await page.goto('https://httpbin.org/ip');
        const content = await page.textContent('body');
        console.log('IP from cloud browser:', content);
        
        await browser.close();
        console.log('✅ Browserbase working! Session:', session.id);
      } else if (command === 'session') {
        const session = await createSession();
        console.log(JSON.stringify(session, null, 2));
      } else {
        console.log('Usage: connect.js [test|session]');
      }
    } catch (err) {
      console.error('❌ Error:', err.message);
      process.exit(1);
    }
  })();
}

module.exports = { createSession, connectToSession, createAndConnect };
