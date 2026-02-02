#!/usr/bin/env node

const https = require('https');
const { Readable } = require('stream');
const fs = require('fs');
const path = require('path');

// Load .env file manually
function loadEnv() {
  try {
    const envPath = path.join(__dirname, '../../../.env');
    if (fs.existsSync(envPath)) {
      const envContent = fs.readFileSync(envPath, 'utf8');
      envContent.split('\n').forEach(line => {
        line = line.trim();
        if (line && !line.startsWith('#')) {
          const [key, ...valueParts] = line.split('=');
          if (key && valueParts.length > 0) {
            process.env[key.trim()] = valueParts.join('=').trim();
          }
        }
      });
    }
  } catch (err) {
    // Silently fail if .env doesn't exist
  }
}

loadEnv();

class PocketMCPClient {
  constructor(apiKey) {
    this.apiKey = apiKey || process.env.POCKET_API_KEY;
    this.endpoint = 'https://public.heypocketai.com/mcp';
    this.sessionId = null;
  }

  async initialize() {
    // Send initialize request (this will capture the session ID from headers)
    const response = await this.call('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: {
        name: 'openclaw',
        version: '1.0.0'
      }
    });
    
    // Send initialized notification (no response expected)
    await this.notify('notifications/initialized');
    
    return response;
  }

  async notify(method, params = {}) {
    return new Promise((resolve, reject) => {
      const payload = JSON.stringify({
        jsonrpc: '2.0',
        method,
        params
      });

      const headers = {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'Content-Length': Buffer.byteLength(payload)
      };
      
      // Add session ID if we have one
      if (this.sessionId) {
        headers['mcp-session-id'] = this.sessionId;
      }

      const options = {
        method: 'POST',
        headers
      };

      const req = https.request(this.endpoint, options, (res) => {
        let data = '';
        res.on('data', chunk => { data += chunk.toString(); });
        res.on('end', () => { resolve(); }); // Notifications don't return data
      });

      req.on('error', reject);
      req.write(payload);
      req.end();
    });
  }

  async call(method, params = {}) {
    return new Promise((resolve, reject) => {
      const payload = JSON.stringify({
        jsonrpc: '2.0',
        id: Date.now(),
        method,
        params
      });

      const headers = {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'Content-Length': Buffer.byteLength(payload)
      };
      
      // Add session ID if we have one
      if (this.sessionId) {
        headers['mcp-session-id'] = this.sessionId;
      }

      const options = {
        method: 'POST',
        headers
      };

      const req = https.request(this.endpoint, options, (res) => {
        // Capture session ID from response headers
        if (res.headers['mcp-session-id']) {
          this.sessionId = res.headers['mcp-session-id'];
        }
        
        let data = '';
        
        res.on('data', chunk => {
          data += chunk.toString();
        });

        res.on('end', () => {
          // Parse SSE format
          if (process.env.DEBUG) {
            console.error('Raw response:', data);
          }
          
          const lines = data.split('\n').filter(l => l.trim().startsWith('data: '));
          if (lines.length === 0) {
            console.error('Response had no data lines. Full response:', data);
            reject(new Error('No data in response'));
            return;
          }
          
          const lastData = lines[lines.length - 1].replace(/^data:\s*/, '').trim();
          if (!lastData) {
            reject(new Error('Empty data in response'));
            return;
          }
          
          try {
            const parsed = JSON.parse(lastData);
            if (parsed.error) {
              reject(new Error(parsed.error.message));
            } else {
              resolve(parsed);
            }
          } catch (err) {
            console.error('Failed to parse:', lastData);
            reject(err);
          }
        });
      });

      req.on('error', reject);
      req.write(payload);
      req.end();
    });
  }

  async searchConversations(query, options = {}) {
    if (!this.sessionId) await this.initialize();
    
    const params = {
      name: 'search_pocket_conversations',
      arguments: {
        query,
        ...options
      }
    };

    return this.call('tools/call', params);
  }

  async getConversation(recordingIds) {
    if (!this.sessionId) await this.initialize();
    
    const params = {
      name: 'get_pocket_conversation',
      arguments: {
        recording_ids: Array.isArray(recordingIds) ? recordingIds : [recordingIds]
      }
    };

    return this.call('tools/call', params);
  }

  async searchActionItems(options = {}) {
    if (!this.sessionId) await this.initialize();
    
    const params = {
      name: 'search_pocket_actionitems',
      arguments: options
    };

    return this.call('tools/call', params);
  }

  async recentRecordings(options = {}) {
    if (!this.sessionId) await this.initialize();
    
    const params = {
      name: 'search_pocket_conversations_timerange',
      arguments: options
    };

    return this.call('tools/call', params);
  }
}

module.exports = { PocketMCPClient };

// CLI usage
if (require.main === module) {
  const client = new PocketMCPClient();
  
  (async () => {
    try {
      await client.initialize();
      console.log('✓ Connected to Pocket MCP');
      console.log('Session initialized');
    } catch (err) {
      console.error('✗ Connection failed:', err.message);
      process.exit(1);
    }
  })();
}
