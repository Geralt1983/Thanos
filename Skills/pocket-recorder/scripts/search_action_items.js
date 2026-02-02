#!/usr/bin/env node

const { PocketMCPClient } = require('./pocket_mcp_client');

const args = process.argv.slice(2);

const options = {};
if (args.includes('--status')) {
  options.status = args[args.indexOf('--status') + 1];
}
if (args.includes('--priority')) {
  options.priority = args[args.indexOf('--priority') + 1];
}
if (args.includes('--category')) {
  options.category = args[args.indexOf('--category') + 1];
}
if (args.includes('--due-before')) {
  options.dueBefore = args[args.indexOf('--due-before') + 1];
}
if (args.includes('--due-after')) {
  options.dueAfter = args[args.indexOf('--due-after') + 1];
}
if (args.includes('--query')) {
  options.query = args[args.indexOf('--query') + 1];
}

(async () => {
  try {
    const client = new PocketMCPClient();
    console.log('Searching action items...');
    
    const response = await client.searchActionItems(options);
    const results = response.result?.[0]?.content?.[0]?.text;
    
    if (!results) {
      console.log('No action items found');
      return;
    }

    const parsed = JSON.parse(results);
    
    if (parsed.action_items && parsed.action_items.length > 0) {
      console.log(`\nFound ${parsed.action_items.length} action item(s):\n`);
      
      parsed.action_items.forEach((item, i) => {
        console.log(`${i + 1}. [${item.status}] ${item.title}`);
        if (item.description) {
          console.log(`   ${item.description}`);
        }
        if (item.priority) {
          console.log(`   Priority: ${item.priority}`);
        }
        if (item.category) {
          console.log(`   Category: ${item.category}`);
        }
        if (item.due_date) {
          console.log(`   Due: ${new Date(item.due_date).toLocaleDateString()}`);
        }
        console.log(`   Recording: ${item.recording_id} (${new Date(item.recording_created_at).toLocaleDateString()})`);
        console.log('');
      });
    } else {
      console.log('No action items found');
    }
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
