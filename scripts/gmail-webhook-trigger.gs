/**
 * Gmail to OpenClaw Webhook Trigger
 * 
 * Setup:
 * 1. Go to script.google.com
 * 2. Create new project
 * 3. Paste this code
 * 4. Run checkThanosEmails() once manually to authorize
 * 5. Set up trigger: Edit > Triggers > Add Trigger
 *    - Function: checkThanosEmails
 *    - Event source: Time-driven
 *    - Type: Minutes timer
 *    - Interval: Every minute
 */

const WEBHOOK_URL = 'https://ashleys-macbook-air.taildf96dd.ts.net/hooks/agent';
const WEBHOOK_TOKEN = '486d95c72a5b4ed4aeff0673d436d3c3';
const TARGET_ADDRESS = 'jkimble1983+thanos@gmail.com';

// Track processed message IDs to avoid duplicates
const PROCESSED_KEY = 'processedMessageIds';

function checkThanosEmails() {
  // Search for unread emails to +thanos address
  const threads = GmailApp.search('to:' + TARGET_ADDRESS + ' is:unread', 0, 10);
  
  if (threads.length === 0) {
    console.log('No new Thanos emails');
    return;
  }
  
  // Get processed IDs
  const props = PropertiesService.getScriptProperties();
  let processed = JSON.parse(props.getProperty(PROCESSED_KEY) || '[]');
  
  for (const thread of threads) {
    const messages = thread.getMessages();
    const latestMessage = messages[messages.length - 1];
    const messageId = latestMessage.getId();
    
    // Skip if already processed
    if (processed.includes(messageId)) {
      continue;
    }
    
    const from = latestMessage.getFrom();
    const subject = latestMessage.getSubject();
    const body = latestMessage.getPlainBody().substring(0, 2000); // Limit size
    const threadId = thread.getId();
    
    console.log('Processing email from: ' + from + ', subject: ' + subject);
    
    // Call OpenClaw webhook
    try {
      const payload = {
        message: `[EMAIL REQUEST from ${from}]\nSubject: ${subject}\n\n${body}\n\n---\nIMPORTANT: Reply via email using:\ngog gmail send --account jkimble1983@gmail.com --thread-id "${threadId}" --reply-all --body "YOUR_RESPONSE"\n\nProcess this request and send your response via the gog command above.`,
        name: 'Email',
        sessionKey: 'hook:email:' + threadId,
        wakeMode: 'now',
        deliver: false, // Don't deliver to Telegram, we'll reply via email
        model: 'anthropic/claude-sonnet-4-0',
        timeoutSeconds: 120
      };
      
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'Authorization': 'Bearer ' + WEBHOOK_TOKEN
        },
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      };
      
      const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
      console.log('Webhook response: ' + response.getResponseCode());
      
      // Mark as processed
      processed.push(messageId);
      
      // Mark email as read
      latestMessage.markRead();
      
    } catch (error) {
      console.error('Webhook error: ' + error);
    }
  }
  
  // Keep only last 100 processed IDs
  processed = processed.slice(-100);
  props.setProperty(PROCESSED_KEY, JSON.stringify(processed));
}

// Optional: Function to send reply (called from OpenClaw via another webhook)
function sendEmailReply(threadId, replyBody) {
  const thread = GmailApp.getThreadById(threadId);
  if (thread) {
    thread.reply(replyBody);
    console.log('Reply sent to thread: ' + threadId);
  }
}
