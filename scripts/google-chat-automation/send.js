#!/usr/bin/env node
/**
 * Send Message Script
 * 
 * Send a message to a Google Chat conversation.
 * Runs headlessly.
 * 
 * Usage: node send.js <chat-name-or-index> <message>
 * Example: node send.js "Safe Harbor" "Hello everyone!"
 * Example: node send.js 0 "Message to first chat"
 */

import { createBrowser, isLoggedIn, openChat, sendMessage, getChats, formatChats } from './gchat.js';

async function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 2) {
    console.log('Usage: node send.js <chat-name-or-index> <message>');
    console.log('');
    console.log('Examples:');
    console.log('  node send.js "Safe Harbor" "Hello everyone!"');
    console.log('  node send.js 0 "Message to first chat"');
    console.log('');
    console.log('Run with just one arg to list available chats:');
    console.log('  node send.js --list');
    process.exit(1);
  }
  
  const chatIdentifier = args[0];
  const message = args.slice(1).join(' ');
  
  console.log('📤 Google Chat Send Message\n');
  
  const { browser, context, page } = await createBrowser(true);
  
  try {
    // Check if logged in
    const loggedIn = await isLoggedIn(page);
    if (!loggedIn) {
      console.log('❌ Not logged in. Run: node login.js');
      return;
    }
    
    // List chats if requested
    if (chatIdentifier === '--list') {
      const chats = await getChats(page);
      console.log('📋 Available chats:\n');
      console.log(formatChats(chats));
      return;
    }
    
    // Open the target chat
    const identifier = /^\d+$/.test(chatIdentifier) ? parseInt(chatIdentifier) : chatIdentifier;
    const opened = await openChat(page, identifier);
    
    if (!opened) {
      console.log('❌ Could not open chat:', chatIdentifier);
      console.log('\nAvailable chats:');
      const chats = await getChats(page);
      console.log(formatChats(chats));
      return;
    }
    
    // Send the message
    const sent = await sendMessage(page, message);
    
    if (sent) {
      console.log('✅ Message sent successfully!');
    } else {
      console.log('❌ Failed to send message');
    }
    
  } catch (e) {
    console.error('❌ Error:', e.message);
  } finally {
    await browser.close();
  }
}

main().catch(console.error);
