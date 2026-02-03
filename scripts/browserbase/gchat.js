#!/usr/bin/env node
/**
 * Google Chat via Browserbase.
 * Commands: unreads, send <space> <message>
 */

const { chromium } = require('playwright');

const BROWSERBASE_API_KEY = process.env.BROWSERBASE_API_KEY;
const BROWSERBASE_PROJECT_ID = process.env.BROWSERBASE_PROJECT_ID;
const GOOGLE_CHAT_URL = 'https://chat.google.com';

async function createSession(contextId = null) {
  const body = {
    projectId: BROWSERBASE_PROJECT_ID,
    browserSettings: {
      fingerprint: { devices: ['desktop'] },
      viewport: { width: 1280, height: 800 },
    },
  };
  
  // Use persistent context if provided
  if (contextId) {
    body.browserSettings.context = { id: contextId, persist: true };
  }

  const response = await fetch('https://api.browserbase.com/v1/sessions', {
    method: 'POST',
    headers: {
      'x-bb-api-key': BROWSERBASE_API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Session create failed: ${await response.text()}`);
  }
  return response.json();
}

async function createContext() {
  const response = await fetch('https://api.browserbase.com/v1/contexts', {
    method: 'POST',
    headers: {
      'x-bb-api-key': BROWSERBASE_API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ projectId: BROWSERBASE_PROJECT_ID }),
  });

  if (!response.ok) {
    throw new Error(`Context create failed: ${await response.text()}`);
  }
  return response.json();
}

async function connect(sessionId) {
  const wsUrl = `wss://connect.browserbase.com?apiKey=${BROWSERBASE_API_KEY}&sessionId=${sessionId}`;
  return chromium.connectOverCDP(wsUrl);
}

async function checkUnreads(page) {
  await page.goto(GOOGLE_CHAT_URL, { waitUntil: 'networkidle', timeout: 30000 });
  
  // Check if logged in
  const url = page.url();
  if (url.includes('accounts.google.com')) {
    return { error: 'Not logged in - need to authenticate first' };
  }

  // Wait for chat to load
  await page.waitForTimeout(3000);
  
  // Look for unread indicators (red badges)
  const unreads = await page.evaluate(() => {
    const results = [];
    // Look for unread badges in sidebar
    const badges = document.querySelectorAll('[data-unread-count], .unread-count, [aria-label*="unread"]');
    badges.forEach(b => {
      const text = b.textContent || b.getAttribute('aria-label') || '';
      if (text) results.push(text);
    });
    
    // Also check for bold/unread room names
    const rooms = document.querySelectorAll('[role="listitem"]');
    rooms.forEach(r => {
      const style = window.getComputedStyle(r);
      if (style.fontWeight >= 600 || r.querySelector('.unread')) {
        const name = r.textContent?.trim().substring(0, 50);
        if (name) results.push(`Unread: ${name}`);
      }
    });
    
    return results;
  });

  return { unreads, count: unreads.length };
}

async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (!command) {
    console.log('Usage: gchat.js [unreads|login|send <space> <message>]');
    process.exit(1);
  }

  // Load context ID if saved
  const fs = require('fs');
  const contextFile = `${__dirname}/gchat-context.json`;
  let contextId = null;
  
  try {
    const data = JSON.parse(fs.readFileSync(contextFile, 'utf8'));
    contextId = data.contextId;
  } catch (e) {}

  try {
    if (command === 'login') {
      // Create new persistent context
      const context = await createContext();
      console.log('Created context:', context.id);
      fs.writeFileSync(contextFile, JSON.stringify({ contextId: context.id }));
      
      const session = await createSession(context.id);
      console.log('Session:', session.id);
      console.log('\nOpen this URL to login:');
      console.log(`https://www.browserbase.com/sessions/${session.id}/debug`);
      console.log('\nLogin to Google, then the session will persist.');
      return;
    }

    const session = await createSession(contextId);
    const browser = await connect(session.id);
    const ctx = browser.contexts()[0];
    const page = ctx.pages()[0] || await ctx.newPage();

    if (command === 'unreads') {
      const result = await checkUnreads(page);
      console.log(JSON.stringify(result, null, 2));
    }

    await browser.close();
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
}

main();
