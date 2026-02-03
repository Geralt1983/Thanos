#!/usr/bin/env node
/**
 * Headless Monitor Script
 * 
 * Checks for new messages in Google Chat.
 * Runs headlessly - no visible browser window.
 * Designed to be called from cron/scheduled tasks.
 * 
 * Usage: node monitor.js [--notify]
 */

import { createBrowser, isLoggedIn, checkForNewMessages, formatChats, openChat, getMessages, formatMessages } from './gchat.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LOG_FILE = path.join(__dirname, '..', '..', 'logs', 'google-chat-monitor.log');

const NOTIFY = process.argv.includes('--notify');
const GATEWAY_URL = 'http://localhost:18789';
const GATEWAY_TOKEN = '71d632f95e9c08ade4dfe00bd841a860f2025e98286827ef';

function log(msg) {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] ${msg}`;
  console.log(line);
  fs.appendFileSync(LOG_FILE, line + '\n');
}

async function sendTelegramNotification(message) {
  if (!NOTIFY) return;
  
  try {
    const response = await fetch(`${GATEWAY_URL}/api/message/send`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GATEWAY_TOKEN}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        channel: 'telegram',
        to: '6135558908',
        message
      })
    });
    
    if (response.ok) {
      log('📱 Telegram notification sent');
    }
  } catch (e) {
    log(`❌ Failed to send notification: ${e.message}`);
  }
}

async function main() {
  log('🔍 Starting Google Chat monitor (headless)...');
  
  const { browser, context, page } = await createBrowser(true);
  
  try {
    // Check if logged in
    const loggedIn = await isLoggedIn(page);
    if (!loggedIn) {
      log('❌ Not logged in. Run: node login.js');
      await sendTelegramNotification('⚠️ Google Chat monitor: Session expired. Run `node login.js` to re-authenticate.');
      return;
    }
    
    log('✅ Session valid, checking for messages...');
    
    // Check for new messages
    const { chats, newMessages } = await checkForNewMessages(page);
    
    log(`📊 Found ${chats.length} chats, ${newMessages.length} with new activity`);
    
    if (newMessages.length > 0) {
      log('🔔 New messages detected!');
      
      // Build notification
      const chatNames = newMessages.map(c => c.name).join(', ');
      let notification = `🗨️ **Google Chat Activity**\n\nNew messages in: ${chatNames}`;
      
      // Try to read the actual messages from first unread chat
      if (newMessages[0]) {
        const opened = await openChat(page, newMessages[0].id);
        if (opened) {
          const messages = await getMessages(page, 5);
          if (messages.length > 0) {
            notification += `\n\n**Recent in ${newMessages[0].name}:**\n`;
            notification += messages.map(m => `• ${m.sender}: ${m.text.substring(0, 100)}`).join('\n');
          }
        }
      }
      
      await sendTelegramNotification(notification);
      
      // Output for CLI
      console.log('\n📬 New messages in:');
      newMessages.forEach(c => console.log(`   • ${c.name}`));
    } else {
      log('✅ No new messages');
    }
    
    // Always output current chat list
    console.log('\n📋 All chats:');
    console.log(formatChats(chats));
    
  } catch (e) {
    log(`❌ Error: ${e.message}`);
    await sendTelegramNotification(`⚠️ Google Chat monitor error: ${e.message}`);
  } finally {
    await browser.close();
  }
}

main().catch(e => {
  log(`❌ Fatal error: ${e.message}`);
  process.exit(1);
});
