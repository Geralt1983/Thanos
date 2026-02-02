#!/usr/bin/env node

const { PocketMCPClient } = require('./pocket_mcp_client');

const args = process.argv.slice(2);
const days = args.includes('--days') ? parseInt(args[args.indexOf('--days') + 1]) : 7;

const afterDate = new Date();
afterDate.setDate(afterDate.getDate() - days);

const options = {
  recordingDateAfter: afterDate.toISOString()
};

if (args.includes('--tags')) {
  options.tags = args[args.indexOf('--tags') + 1].split(',');
}

(async () => {
  try {
    const client = new PocketMCPClient();
    console.log(`Fetching recordings from last ${days} day(s)...`);
    
    const response = await client.recentRecordings(options);
    const results = response.result?.[0]?.content?.[0]?.text;
    
    if (!results) {
      console.log('No recordings found');
      return;
    }

    const parsed = JSON.parse(results);
    
    if (parsed.recordings && parsed.recordings.length > 0) {
      console.log(`\nFound ${parsed.recordings.length} recording(s):\n`);
      
      parsed.recordings.forEach((recording, i) => {
        console.log(`${i + 1}. ${recording.id}`);
        console.log(`   Created: ${new Date(recording.created_at).toLocaleString()}`);
        console.log(`   Duration: ${Math.round(recording.duration_ms / 1000)}s`);
        
        if (recording.tags && recording.tags.length > 0) {
          console.log(`   Tags: ${recording.tags.join(', ')}`);
        }
        
        // Show first few words of transcript
        if (recording.sections && recording.sections.length > 0) {
          const preview = recording.sections[0].text.substring(0, 100);
          console.log(`   Preview: "${preview}..."`);
        }
        
        if (recording.action_items && recording.action_items.length > 0) {
          console.log(`   Action items: ${recording.action_items.length}`);
        }
        
        console.log('');
      });
    } else {
      console.log('No recordings found');
    }
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
