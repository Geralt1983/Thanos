// =============================================================================
// PYTHON BRIDGE
// Executes Python Memory V2 tools via subprocess
// =============================================================================

import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to the Thanos project root
const THANOS_ROOT = path.resolve(__dirname, "../../../..");

/**
 * Execute a Python function from the Memory V2 module
 */
export async function executePythonTool(
  functionName: string,
  args: Record<string, any>
): Promise<any> {
  return new Promise((resolve, reject) => {
    // Build Python script to execute the function
    const pythonScript = `
import sys
import json
sys.path.insert(0, '${THANOS_ROOT}')

from Tools.memory_v2.mcp_tools import ${functionName}

# Parse arguments
args = json.loads('''${JSON.stringify(args)}''')

# Call the function with keyword arguments
result = ${functionName}(**args)

# Output as JSON
print(json.dumps(result, default=str))
`;

    const python = spawn("python3", ["-c", pythonScript], {
      cwd: THANOS_ROOT,
      env: {
        ...process.env,
        PYTHONPATH: THANOS_ROOT,
      },
    });

    let stdout = "";
    let stderr = "";

    python.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    python.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    python.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(`Python process exited with code ${code}: ${stderr}`));
        return;
      }

      try {
        const result = JSON.parse(stdout.trim());
        resolve(result);
      } catch (parseError) {
        // If not JSON, return as string
        resolve(stdout.trim());
      }
    });

    python.on("error", (error) => {
      reject(new Error(`Failed to start Python process: ${error.message}`));
    });
  });
}
