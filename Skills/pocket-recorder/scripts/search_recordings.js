#!/usr/bin/env node

const { PocketMCPClient } = require('./pocket_mcp_client');

const args = process.argv.slice(2);
const query = args.find(a => !a.startsWith('--')) || '';

const options = {};
if (args.includes('--after')) {
  options.recordingDateAfter = args[args.indexOf('--after') + 1];
}
if (args.includes('--before')) {
  options.recordingDateBefore = args[args.indexOf('--before') + 1];
}
if (args.includes('--tags')) {
  options.tags = args[args.indexOf('--tags') + 1].split(',');
}

(async () => {
  try {
    const client = new PocketMCPClient();
    console.log('Searching for:', query);
    
    const response = await client.searchConversations(query, options);
    const results = response.result?.[0]?.content?.[0]?.text;
    
    if (!results) {
      console.log('No results found');
      return;
    }

    const parsed = JSON.parse(results);
    
    if (parsed.results && parsed.results.length > 0) {
      console.log(`\nFound ${parsed.results.length} result(s):\n`);
      
      parsed.results.forEach((result, i) => {
        console.log(`${i + 1}. Recording: ${result.recording_id}`);
        console.log(`   Date: ${new Date(result.recording_created_at).toLocaleString()}`);
        console.log(`   Match: "${result.text.substring(0, 200)}..."`);
        console.log(`   Score: ${result.score?.toFixed(3)}`);
        if (result.tags && result.tags.length > 0) {
          console.log(`   Tags: ${result.tags.join(', ')}`);
        }
        console.log('');
      });
    } else {
      console.log('No matching recordings found');
    }
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
