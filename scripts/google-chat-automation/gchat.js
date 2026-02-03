/**
 * Google Chat Automation Core Module
 * 
 * Provides headless browser automation for Google Chat using Playwright.
 * Works with personal Gmail accounts, persists login sessions.
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SESSION_FILE = path.join(__dirname, 'session.json');
const STATE_FILE = path.join(__dirname, 'state.json');

// Stealth settings to avoid bot detection
const STEALTH_ARGS = [
  '--disable-blink-features=AutomationControlled',
  '--disable-features=IsolateOrigins,site-per-process',
  '--disable-site-isolation-trials',
];

const USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

/**
 * Create a browser context with stealth settings
 */
export async function createBrowser(headless = true) {
  const browser = await chromium.launch({
    headless,
    args: STEALTH_ARGS,
  });
  
  const contextOptions = {
    userAgent: USER_AGENT,
    viewport: { width: 1920, height: 1080 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
  };
  
  // Load existing session if available
  if (fs.existsSync(SESSION_FILE)) {
    contextOptions.storageState = SESSION_FILE;
    console.log('📂 Loading existing session...');
  }
  
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();
  
  // Additional stealth
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
  });
  
  return { browser, context, page };
}

/**
 * Save the current session for future use
 */
export async function saveSession(context) {
  await context.storageState({ path: SESSION_FILE });
  console.log('💾 Session saved to', SESSION_FILE);
}

/**
 * Check if user is logged into Google Chat
 */
export async function isLoggedIn(page) {
  try {
    await page.goto('https://chat.google.com', { waitUntil: 'networkidle', timeout: 30000 });
    
    // Check for login page indicators
    const loginButton = await page.$('input[type="email"]');
    if (loginButton) {
      return false;
    }
    
    // Check for chat UI indicators
    const chatUI = await page.$('[data-group-id], [data-conversation-id], [role="main"]');
    return !!chatUI;
  } catch (e) {
    console.error('Error checking login status:', e.message);
    return false;
  }
}

/**
 * Interactive login flow (run with headless=false)
 */
export async function login() {
  console.log('🔐 Starting interactive login...');
  console.log('   A browser window will open. Please log in to Google Chat.');
  
  const { browser, context, page } = await createBrowser(false); // Visible browser
  
  await page.goto('https://chat.google.com');
  
  console.log('\n⏳ Waiting for you to complete login...');
  console.log('   (This script will continue once you reach the Chat interface)\n');
  
  // Wait for chat UI to appear (user has logged in)
  try {
    await page.waitForSelector('[data-group-id], [data-conversation-id], [role="main"]', { 
      timeout: 300000 // 5 minutes to login
    });
    
    console.log('✅ Login successful!');
    await saveSession(context);
    
  } catch (e) {
    console.error('❌ Login timed out or failed');
  }
  
  await browser.close();
}

/**
 * Get list of visible chats/conversations
 */
export async function getChats(page) {
  await page.goto('https://chat.google.com', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000); // Let UI settle
  
  const chats = await page.evaluate(() => {
    const results = [];
    
    // Try to find conversation list items
    const items = document.querySelectorAll('[data-conversation-id], [data-group-id], [role="listitem"]');
    
    items.forEach((item, index) => {
      const nameEl = item.querySelector('[data-name], [data-tooltip], span');
      const unreadEl = item.querySelector('[data-unread-count], .unread-count, [aria-label*="unread"]');
      
      results.push({
        index,
        id: item.getAttribute('data-conversation-id') || item.getAttribute('data-group-id') || `item-${index}`,
        name: nameEl?.textContent?.trim() || `Chat ${index}`,
        unread: unreadEl ? parseInt(unreadEl.textContent) || true : false,
        element: item.className
      });
    });
    
    return results;
  });
  
  return chats;
}

/**
 * Get recent messages from current chat view
 */
export async function getMessages(page, limit = 20) {
  await page.waitForTimeout(1000);
  
  const messages = await page.evaluate((limit) => {
    const results = [];
    
    // Find message elements (Google Chat uses various selectors)
    const msgElements = document.querySelectorAll('[data-message-id], [data-local-id], .message-content');
    
    const items = Array.from(msgElements).slice(-limit);
    
    items.forEach((el, index) => {
      const textEl = el.querySelector('[data-message-text], .message-text, span[dir="ltr"]') || el;
      const senderEl = el.closest('[data-sender-id]') || el.querySelector('[data-sender-name]');
      const timeEl = el.querySelector('[data-absolute-timestamp], time');
      
      results.push({
        index,
        id: el.getAttribute('data-message-id') || el.getAttribute('data-local-id') || `msg-${index}`,
        text: textEl?.textContent?.trim() || '',
        sender: senderEl?.getAttribute('data-sender-name') || senderEl?.textContent?.trim() || 'Unknown',
        time: timeEl?.getAttribute('datetime') || timeEl?.textContent || ''
      });
    });
    
    return results;
  }, limit);
  
  return messages.filter(m => m.text);
}

/**
 * Open a specific chat by name or index
 */
export async function openChat(page, identifier) {
  const chats = await getChats(page);
  
  let targetChat;
  if (typeof identifier === 'number') {
    targetChat = chats[identifier];
  } else {
    targetChat = chats.find(c => 
      c.name.toLowerCase().includes(identifier.toLowerCase()) ||
      c.id === identifier
    );
  }
  
  if (!targetChat) {
    console.error('Chat not found:', identifier);
    return false;
  }
  
  console.log(`📂 Opening chat: ${targetChat.name}`);
  
  // Click on the chat
  await page.evaluate((id) => {
    const el = document.querySelector(`[data-conversation-id="${id}"], [data-group-id="${id}"]`) ||
               document.querySelectorAll('[role="listitem"]')[parseInt(id.replace('item-', ''))];
    if (el) el.click();
  }, targetChat.id);
  
  await page.waitForTimeout(1500);
  return true;
}

/**
 * Send a message to the current chat
 */
export async function sendMessage(page, text) {
  // Find the message input
  const inputSelectors = [
    '[aria-label="Message"], [aria-label*="message"]',
    '[contenteditable="true"]',
    'textarea[placeholder*="message"]',
    '[role="textbox"]'
  ];
  
  let input;
  for (const selector of inputSelectors) {
    input = await page.$(selector);
    if (input) break;
  }
  
  if (!input) {
    console.error('Could not find message input');
    return false;
  }
  
  // Type the message
  await input.click();
  await page.keyboard.type(text, { delay: 30 }); // Human-like typing
  
  // Press Enter to send
  await page.keyboard.press('Enter');
  
  console.log(`📤 Sent: "${text.substring(0, 50)}${text.length > 50 ? '...' : ''}"`);
  await page.waitForTimeout(1000);
  
  return true;
}

/**
 * Monitor for new messages (returns changed state)
 */
export async function checkForNewMessages(page) {
  const chats = await getChats(page);
  
  // Load previous state
  let prevState = {};
  if (fs.existsSync(STATE_FILE)) {
    prevState = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
  }
  
  const newMessages = [];
  
  for (const chat of chats) {
    if (chat.unread && !prevState[chat.id]?.unread) {
      newMessages.push(chat);
    }
  }
  
  // Save current state
  const currentState = {};
  chats.forEach(c => {
    currentState[c.id] = { unread: c.unread, name: c.name };
  });
  fs.writeFileSync(STATE_FILE, JSON.stringify(currentState, null, 2));
  
  return { chats, newMessages };
}

/**
 * Take a screenshot of current view
 */
export async function screenshot(page, filename) {
  const screenshotPath = path.join(__dirname, '..', '..', 'data', 'screenshots', 'google-chat', filename);
  await page.screenshot({ path: screenshotPath, fullPage: false });
  console.log(`📸 Screenshot saved: ${screenshotPath}`);
  return screenshotPath;
}

// CLI helpers
export function formatChats(chats) {
  return chats.map((c, i) => 
    `${i}. ${c.unread ? '🔴 ' : '  '}${c.name}`
  ).join('\n');
}

export function formatMessages(messages) {
  return messages.map(m => 
    `[${m.time || '?'}] ${m.sender}: ${m.text}`
  ).join('\n');
}
