#!/usr/bin/env node
/**
 * One-time Login Script
 * 
 * Run this once to authenticate with Google Chat.
 * A browser window will open - log in manually.
 * Session will be saved for future headless use.
 * 
 * Usage: node login.js
 */

import { login, createBrowser, isLoggedIn, saveSession } from './gchat.js';

async function main() {
  console.log('🔐 Google Chat Login Setup\n');
  
  // First check if we already have a valid session
  console.log('Checking existing session...');
  const { browser, context, page } = await createBrowser(true); // Headless check
  
  const loggedIn = await isLoggedIn(page);
  await browser.close();
  
  if (loggedIn) {
    console.log('✅ Already logged in! Session is valid.');
    console.log('   You can run monitor.js, read.js, or send.js');
    return;
  }
  
  console.log('❌ No valid session found. Starting interactive login...\n');
  await login();
  
  console.log('\n🎉 Setup complete! You can now use:');
  console.log('   node monitor.js  - Monitor for new messages');
  console.log('   node read.js     - Read messages from a chat');
  console.log('   node send.js     - Send a message');
}

main().catch(console.error);
