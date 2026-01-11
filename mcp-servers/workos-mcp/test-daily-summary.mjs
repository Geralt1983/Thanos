#!/usr/bin/env node
/**
 * Test script for workos_daily_summary tool via MCP JSON-RPC protocol.
 * Simulates Claude Code MCP integration to verify end-to-end functionality.
 *
 * Expected response structure:
 * - date: ISO date string (YYYY-MM-DD)
 * - source: "neon" (bypasses cache for date-sensitive queries)
 * - progress: { earnedPoints, targetPoints: 18, minimumPoints: 12, completedTasks, streak }
 * - today: { activeTasks: [...], activePoints, potentialTotal }
 * - upNext: array of queued tasks
 */

import { spawn } from 'child_process';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function runTest() {
  return new Promise((resolve, reject) => {
    const serverPath = join(__dirname, 'dist', 'index.js');
    const server = spawn('node', [serverPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
    });

    let stdout = '';
    let stderr = '';
    let initialized = false;
    let testCompleted = false;

    server.stdout.on('data', (data) => {
      stdout += data.toString();

      // Parse JSON-RPC responses
      const lines = stdout.split('\n').filter(l => l.trim());
      for (const line of lines) {
        try {
          const msg = JSON.parse(line);

          if (msg.id === 1) {
            // Initialize response received
            initialized = true;
            console.log('✓ Server initialized');

            // Send tools/call request for workos_daily_summary
            const callRequest = {
              jsonrpc: '2.0',
              id: 2,
              method: 'tools/call',
              params: {
                name: 'workos_daily_summary',
                arguments: {},
              },
            };
            server.stdin.write(JSON.stringify(callRequest) + '\n');
            console.log('→ Sent workos_daily_summary request');
          }

          if (msg.id === 2) {
            testCompleted = true;
            console.log('\n=== workos_daily_summary Response ===\n');

            if (msg.error) {
              console.log('✗ Error:', JSON.stringify(msg.error, null, 2));
              server.kill();
              resolve({ success: false, error: msg.error });
              return;
            }

            // Parse the result
            const result = msg.result;
            if (result && result.content && result.content[0]) {
              const content = result.content[0].text;
              try {
                const data = JSON.parse(content);
                console.log('Parsed Response:', JSON.stringify(data, null, 2));

                // Verification checks
                console.log('\n=== Verification ===\n');

                let allChecks = true;

                // Check 1: date field exists
                if (data.date) {
                  console.log('✓ date field present:', data.date);
                } else {
                  console.log('✗ date field MISSING');
                  allChecks = false;
                }

                // Check 2: source is "neon" (bypasses cache)
                if (data.source === 'neon') {
                  console.log('✓ source is "neon" (direct database query)');
                } else {
                  console.log('✗ source should be "neon", got:', data.source);
                  allChecks = false;
                }

                // Check 3: progress object
                if (data.progress) {
                  console.log('✓ progress object present');

                  if (typeof data.progress.earnedPoints === 'number') {
                    console.log('  ✓ earnedPoints:', data.progress.earnedPoints);
                  } else {
                    console.log('  ✗ earnedPoints missing or invalid');
                    allChecks = false;
                  }

                  if (data.progress.targetPoints === 18) {
                    console.log('  ✓ targetPoints: 18 (correct)');
                  } else {
                    console.log('  ✗ targetPoints should be 18, got:', data.progress.targetPoints);
                    allChecks = false;
                  }

                  if (data.progress.minimumPoints === 12) {
                    console.log('  ✓ minimumPoints: 12 (correct)');
                  } else {
                    console.log('  ✗ minimumPoints should be 12, got:', data.progress.minimumPoints);
                    allChecks = false;
                  }

                  if (typeof data.progress.completedTasks === 'number') {
                    console.log('  ✓ completedTasks:', data.progress.completedTasks);
                  } else {
                    console.log('  ✗ completedTasks missing or invalid');
                    allChecks = false;
                  }

                  if (typeof data.progress.streak === 'number') {
                    console.log('  ✓ streak:', data.progress.streak);
                  } else {
                    console.log('  ✗ streak missing or invalid');
                    allChecks = false;
                  }
                } else {
                  console.log('✗ progress object MISSING');
                  allChecks = false;
                }

                // Check 4: today object
                if (data.today) {
                  console.log('✓ today object present');

                  if (Array.isArray(data.today.activeTasks)) {
                    console.log('  ✓ activeTasks array:', data.today.activeTasks.length, 'tasks');
                    for (const task of data.today.activeTasks.slice(0, 3)) {
                      console.log('    - [' + task.id + ']', task.title, '(' + task.client + ')', task.points + 'pts');
                    }
                    if (data.today.activeTasks.length > 3) {
                      console.log('    ... and', data.today.activeTasks.length - 3, 'more');
                    }
                  } else {
                    console.log('  ✗ activeTasks should be array');
                    allChecks = false;
                  }

                  if (typeof data.today.activePoints === 'number') {
                    console.log('  ✓ activePoints:', data.today.activePoints);
                  } else {
                    console.log('  ✗ activePoints missing or invalid');
                    allChecks = false;
                  }

                  if (typeof data.today.potentialTotal === 'number') {
                    console.log('  ✓ potentialTotal:', data.today.potentialTotal);
                  } else {
                    console.log('  ✗ potentialTotal missing or invalid');
                    allChecks = false;
                  }
                } else {
                  console.log('✗ today object MISSING');
                  allChecks = false;
                }

                // Check 5: upNext array
                if (Array.isArray(data.upNext)) {
                  console.log('✓ upNext array present:', data.upNext.length, 'tasks');
                  for (const task of data.upNext.slice(0, 3)) {
                    console.log('  - [' + task.id + ']', task.title, '(' + task.client + ')');
                  }
                  if (data.upNext.length > 3) {
                    console.log('  ... and', data.upNext.length - 3, 'more');
                  }
                } else {
                  console.log('✗ upNext array MISSING');
                  allChecks = false;
                }

                console.log('\n=== Summary ===\n');
                if (allChecks) {
                  console.log('✓ ALL VERIFICATION CHECKS PASSED');
                  console.log('✓ workos_daily_summary tool working correctly');
                  console.log('✓ Direct Neon database connection verified');
                } else {
                  console.log('✗ Some verification checks FAILED');
                }

                server.kill();
                resolve({ success: allChecks, data });
              } catch (parseErr) {
                console.log('✗ Failed to parse response JSON:', parseErr.message);
                console.log('Raw content:', content);
                server.kill();
                resolve({ success: false, error: parseErr.message });
              }
            } else {
              console.log('✗ Unexpected response structure:', JSON.stringify(msg, null, 2));
              server.kill();
              resolve({ success: false, error: 'Unexpected response structure' });
            }
          }
        } catch (e) {
          // Not JSON, ignore
        }
      }
    });

    server.stderr.on('data', (data) => {
      stderr += data.toString();
      // Print cache messages for visibility
      const lines = data.toString().split('\n').filter(l => l.trim());
      for (const line of lines) {
        if (line.includes('[Cache]') || line.includes('WorkOS MCP')) {
          console.log('[Server]', line);
        }
      }
    });

    server.on('error', (err) => {
      console.error('Failed to start server:', err);
      reject(err);
    });

    server.on('close', (code) => {
      if (!testCompleted) {
        console.log('Server exited with code:', code);
        if (stderr) {
          console.log('Stderr:', stderr);
        }
        resolve({ success: false, error: 'Server exited before test completed' });
      }
    });

    // Send initialize request
    setTimeout(() => {
      const initRequest = {
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: { name: 'test-client', version: '1.0.0' },
        },
      };
      server.stdin.write(JSON.stringify(initRequest) + '\n');
    }, 500);

    // Timeout after 30 seconds
    setTimeout(() => {
      if (!testCompleted) {
        console.log('✗ Test timed out');
        server.kill();
        resolve({ success: false, error: 'Test timeout' });
      }
    }, 30000);
  });
}

console.log('===========================================');
console.log('Testing workos_daily_summary MCP Tool');
console.log('===========================================\n');

runTest()
  .then((result) => {
    console.log('\n===========================================');
    if (result.success) {
      console.log('TEST RESULT: PASSED ✓');
    } else {
      console.log('TEST RESULT: FAILED ✗');
      if (result.error) {
        console.log('Error:', result.error);
      }
    }
    console.log('===========================================\n');
    process.exit(result.success ? 0 : 1);
  })
  .catch((err) => {
    console.error('Test error:', err);
    process.exit(1);
  });
