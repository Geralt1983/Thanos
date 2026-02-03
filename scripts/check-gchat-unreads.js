#!/usr/bin/env node
/**
 * Google Chat Unread Checker
 * Uses OpenClaw browser to check for unread messages
 * Returns JSON with unread status for cron job processing
 */

import { execSync } from 'child_process';

async function checkUnreads() {
  try {
    // Start browser if needed
    execSync('openclaw browser start --profile openclaw', { stdio: 'pipe' });
    
    // Open Google Chat
    const tabResult = JSON.parse(execSync(
      'openclaw browser open --profile openclaw --url "https://mail.google.com/chat/u/0/#chat/home" --json',
      { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }
    ).trim());
    
    const targetId = tabResult.targetId;
    
    // Wait for page to load
    await new Promise(r => setTimeout(r, 5000));
    
    // Take snapshot and look for unread indicators
    const snapshotResult = execSync(
      `openclaw browser snapshot --profile openclaw --target-id "${targetId}" --max-chars 15000 --json`,
      { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }
    ).trim();
    
    // Parse for unread patterns
    const unreads = [];
    
    // Look for "X unread" patterns
    const unreadMatches = snapshotResult.match(/(\d+)\s*unread/gi) || [];
    const notificationMatches = snapshotResult.match(/(\d+)\s*Notification/gi) || [];
    
    // Look for specific spaces/chats with unreads
    const spaceUnreads = snapshotResult.match(/Unread\s+([^"]+?)\s+Space/gi) || [];
    const dmUnreads = snapshotResult.match(/Unread.*?(Direct message|DM)/gi) || [];
    
    // Check for "Home shortcut, X unread"
    const homeUnread = snapshotResult.match(/Home shortcut,?\s*(\d+)\s*unread/i);
    
    const totalUnread = unreadMatches.reduce((sum, m) => {
      const num = parseInt(m.match(/\d+/)?.[0] || '0');
      return sum + num;
    }, 0);
    
    const result = {
      hasUnreads: totalUnread > 0 || spaceUnreads.length > 0,
      totalUnread,
      homeUnread: homeUnread ? parseInt(homeUnread[1]) : 0,
      spaces: spaceUnreads.map(s => s.replace(/Unread\s+/i, '').replace(/\s+Space/i, '')),
      raw: {
        unreadMatches,
        notificationMatches,
        spaceUnreads
      },
      checkedAt: new Date().toISOString()
    };
    
    console.log(JSON.stringify(result, null, 2));
    
  } catch (error) {
    console.error(JSON.stringify({
      error: true,
      message: error.message,
      checkedAt: new Date().toISOString()
    }));
    process.exit(1);
  }
}

checkUnreads();
