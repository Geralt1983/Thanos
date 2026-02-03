#!/usr/bin/env node
/**
 * Read Messages Script
 * 
 * Read recent messages from a Google Chat conversation.
 * Runs headlessly.
 * 
 * Usage: node read.js [chat-name-or-index] [--count N]
 * Example: node read.js "Safe Harbor" --count 10
 * Example: node read.js 0
 * Example: node read.js (lists all chats)
 */

import { createBrowser, isLoggedIn, openChat, getMessages, getChats, formatChats, formatMessages } from './gchat.js';

async function main() {
  const args = process.argv.slice(2);
  
  let chatIdentifier = null;
  let count = 20;
  
  // Parse arguments
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--count' && args[i + 1]) {
      count = parseInt(args[i + 1]);
      i++;
    } else if (!chatIdentifier) {
      chatIdentifier = /^\d+$/.test(args[i]) ? parseInt(args[i]) : args[i];
    }
  }
  
  console.log('📖 Google Chat Read Messages\n');
  
  const { browser, context, page } = await createBrowser(true);
  
  try {
    // Check if logged in
    const loggedIn = await isLoggedIn(page);
    if (!loggedIn) {
      console.log('❌ Not logged in. Run: node login.js');
      return;
    }
    
    // List chats if no identifier provided
    if (chatIdentifier === null) {
      const chats = await getChats(page);
      console.log('📋 Available chats:\n');
      console.log(formatChats(chats));
      console.log('\nUsage: node read.js <chat-name-or-index> [--count N]');
      return;
    }
    
    // Open the target chat
    const opened = await openChat(page, chatIdentifier);
    
    if (!opened) {
      console.log('❌ Could not open chat:', chatIdentifier);
      console.log('\nAvailable chats:');
      const chats = await getChats(page);
      console.log(formatChats(chats));
      return;
    }
    
    // Read messages
    const messages = await getMessages(page, count);
    
    if (messages.length === 0) {
      console.log('📭 No messages found (or unable to parse)');
    } else {
      console.log(`📬 Last ${messages.length} messages:\n`);
      console.log(formatMessages(messages));
    }
    
  } catch (e) {
    console.error('❌ Error:', e.message);
  } finally {
    await browser.close();
  }
}

main().catch(console.error);
