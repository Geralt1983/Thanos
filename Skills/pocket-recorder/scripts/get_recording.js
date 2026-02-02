#!/usr/bin/env node

const { PocketMCPClient } = require('./pocket_mcp_client');

const recordingId = process.argv[2];

if (!recordingId) {
  console.error('Usage: node get_recording.js <recording_id>');
  process.exit(1);
}

(async () => {
  try {
    const client = new PocketMCPClient();
    console.log('Fetching recording:', recordingId);
    
    const response = await client.getConversation(recordingId);
    const results = response.result?.[0]?.content?.[0]?.text;
    
    if (!results) {
      console.log('Recording not found');
      return;
    }

    const parsed = JSON.parse(results);
    
    if (parsed.recordings && parsed.recordings.length > 0) {
      const recording = parsed.recordings[0];
      
      console.log('\n=== RECORDING ===');
      console.log(`ID: ${recording.id}`);
      console.log(`Created: ${new Date(recording.created_at).toLocaleString()}`);
      console.log(`Duration: ${Math.round(recording.duration_ms / 1000)}s`);
      if (recording.tags && recording.tags.length > 0) {
        console.log(`Tags: ${recording.tags.join(', ')}`);
      }
      
      if (recording.audio_url) {
        console.log(`\nAudio URL (expires in 1h):`);
        console.log(recording.audio_url);
      }
      
      console.log(`\n=== TRANSCRIPT ===\n`);
      if (recording.sections && recording.sections.length > 0) {
        recording.sections.forEach(section => {
          const timestamp = new Date(section.start_ms).toISOString().substr(11, 8);
          console.log(`[${timestamp}] ${section.text}`);
        });
      } else {
        console.log('No transcript available');
      }
      
      if (recording.action_items && recording.action_items.length > 0) {
        console.log(`\n=== ACTION ITEMS (${recording.action_items.length}) ===\n`);
        recording.action_items.forEach((item, i) => {
          console.log(`${i + 1}. [${item.status}] ${item.title}`);
          if (item.description) {
            console.log(`   ${item.description}`);
          }
          if (item.due_date) {
            console.log(`   Due: ${new Date(item.due_date).toLocaleDateString()}`);
          }
          if (item.priority) {
            console.log(`   Priority: ${item.priority}`);
          }
          console.log('');
        });
      }
    } else {
      console.log('Recording not found');
    }
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
