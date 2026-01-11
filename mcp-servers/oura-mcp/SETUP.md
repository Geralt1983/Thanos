# Complete Setup Guide - Oura Health Metrics MCP Server

This guide walks you through setting up the Oura MCP Server from scratch, step by step.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start (5 minutes)](#quick-start-5-minutes)
- [Detailed Setup](#detailed-setup)
- [Verification](#verification)
- [Integration Options](#integration-options)
- [Next Steps](#next-steps)

## Prerequisites

Before you begin, make sure you have:

- ✅ **Node.js 18 or higher** ([Download](https://nodejs.org/))
- ✅ **An Oura Ring** and active subscription
- ✅ **Oura account** at [cloud.ouraring.com](https://cloud.ouraring.com/)
- ✅ **Claude Desktop** (for AI integration) - [Download](https://claude.ai/download)
- ✅ **Terminal/Command Line** access
- ✅ **Text editor** for configuration files

### Verify Node.js Installation

```bash
node --version
# Should output v18.0.0 or higher
```

If you don't have Node.js installed:
- **macOS**: `brew install node` or download from [nodejs.org](https://nodejs.org/)
- **Windows**: Download installer from [nodejs.org](https://nodejs.org/)
- **Linux**: `sudo apt install nodejs npm` or use your package manager

## Quick Start (5 minutes)

For experienced users who want to get started quickly:

```bash
# 1. Navigate to the oura-mcp directory
cd /path/to/Thanos/mcp-servers/oura-mcp

# 2. Install dependencies
npm install

# 3. Copy environment template
cp .env.example .env

# 4. Edit .env and add your Personal Access Token
# OURA_ACCESS_TOKEN=your_token_here

# 5. Build the TypeScript project
npm run build

# 6. Test the server
npm start

# 7. Configure Claude Desktop (see Integration section)
```

Then skip to [Claude Desktop Integration](#claude-desktop-integration).

## Detailed Setup

### Step 1: Install Dependencies

Navigate to the `oura-mcp` directory and install npm packages:

```bash
cd /path/to/Thanos/mcp-servers/oura-mcp
npm install
```

**What this does:**
- Installs the Model Context Protocol SDK
- Installs axios for API requests
- Installs better-sqlite3 for caching
- Installs Zod for data validation
- Installs TypeScript and build tools

**Expected output:**
```
added 147 packages, and audited 148 packages in 12s
```

**Troubleshooting:**
- If you get permission errors, don't use `sudo`. Fix npm permissions instead.
- If `better-sqlite3` fails to compile, you may need build tools:
  - **macOS**: `xcode-select --install`
  - **Windows**: Install Visual Studio Build Tools
  - **Linux**: `sudo apt install build-essential`

### Step 2: Get Your Oura Personal Access Token

This is the easiest authentication method for personal use.

#### 2.1: Log into Oura Cloud

1. Open your browser and go to [cloud.ouraring.com](https://cloud.ouraring.com/)
2. Log in with your Oura account credentials
3. If you don't have an account, create one and sync your Oura Ring first

#### 2.2: Navigate to Personal Access Tokens

1. Click on your **profile icon** in the top-right corner
2. Select **"Personal Access Tokens"** from the dropdown menu
3. You'll see a list of any existing tokens (or an empty list)

#### 2.3: Create a New Token

1. Click **"Create A New Personal Access Token"**
2. Give it a descriptive name (e.g., "Thanos MCP Server" or "Claude Desktop")
3. Click **"Create"**

#### 2.4: Copy Your Token

**⚠️ CRITICAL: This is your only chance to copy the token!**

1. The token will be displayed **only once**
2. Click the **copy icon** or select and copy the entire token
3. It will look something like: `ABCDEFGHIJKLMNOP...` (long alphanumeric string)
4. Store it somewhere safe temporarily (you'll paste it in the next step)

### Step 3: Configure Environment Variables

#### 3.1: Create .env file

```bash
cp .env.example .env
```

#### 3.2: Edit .env file

Open `.env` in your favorite text editor:

```bash
# Using nano
nano .env

# Using vim
vim .env

# Using VS Code
code .env

# Using your system's default editor
open -e .env  # macOS
```

#### 3.3: Paste Your Token

Find this line:
```bash
OURA_ACCESS_TOKEN=your_personal_access_token_here
```

Replace `your_personal_access_token_here` with your actual token:
```bash
OURA_ACCESS_TOKEN=ABC123XYZ789...your_actual_token_here
```

**Important:**
- Don't add quotes around the token
- Don't add spaces before or after the `=`
- Make sure there's no trailing space at the end

#### 3.4: Optional Configuration

You can customize these settings if needed:

```bash
# Change cache location (default: ~/.oura-cache)
OURA_CACHE_DIR=/custom/path/to/cache

# Enable debug logging
DEBUG_SYNC=true
DEBUG_API_CALLS=true

# Adjust cache TTL (in hours)
CACHE_TTL_HOURS=2

# Adjust how many days of history to sync
SYNC_HISTORY_DAYS=14
```

For most users, the defaults are fine. **Save and close** the file.

### Step 4: Build the TypeScript Project

Compile the TypeScript code to JavaScript:

```bash
npm run build
```

**Expected output:**
```
Successfully compiled TypeScript files to dist/
```

**What this does:**
- Compiles `src/**/*.ts` files to `dist/**/*.js`
- Generates type definitions
- Validates your TypeScript code

**Troubleshooting:**
- If you get TypeScript errors, make sure you ran `npm install` first
- Check that `tsconfig.json` exists
- Try `rm -rf dist && npm run build` to rebuild from scratch

### Step 5: Test the Server

Run the server in development mode to verify everything works:

```bash
npm run dev
```

**Expected output:**
```
[Oura MCP] Server starting...
[Oura MCP] Registered 4 tools: oura_get_today_readiness, oura_get_sleep_summary, oura_get_weekly_trends, oura_health_check
[Oura MCP] Server running on stdio
```

**What this means:**
- ✅ Server started successfully
- ✅ All 4 MCP tools registered
- ✅ Listening for MCP protocol messages

Press `Ctrl+C` to stop the server. You're ready for integration!

## Verification

Let's verify everything is working correctly.

### Verify Installation

```bash
# Check build output exists
ls -la dist/

# Should show compiled JavaScript files:
# index.js, api/, cache/, tools/, shared/
```

### Verify Configuration

```bash
# Check your .env file (without exposing the token)
grep OURA_ACCESS_TOKEN .env | sed 's/=.*/=***HIDDEN***/g'

# Should output:
# OURA_ACCESS_TOKEN=***HIDDEN***
```

### Verify Cache Directory

After running the server once, check the cache:

```bash
ls -la ~/.oura-cache/

# Should show:
# oura-health.db      (SQLite database)
# rate-limit.json     (Rate limiting data)
```

### Run Health Check (Advanced)

To verify API connectivity, you can test the MCP tools:

1. Install the MCP Inspector: `npm install -g @modelcontextprotocol/inspector`
2. Run: `mcp-inspector node dist/index.js`
3. Test the `oura_health_check` tool

## Integration Options

Now that your server is running, choose how you want to use it:

### Option 1: Claude Desktop Integration

The most common use case - integrate with Claude Desktop for AI-powered health insights.

**See:** [Claude Desktop Integration](#claude-desktop-integration) below

### Option 2: Direct MCP Client

Use with any MCP-compatible client:

```json
{
  "command": "node",
  "args": ["/absolute/path/to/oura-mcp/dist/index.js"],
  "env": {
    "OURA_ACCESS_TOKEN": "your_token_here"
  }
}
```

### Option 3: Programmatic Use

Import and use the tools directly in your TypeScript/JavaScript code:

```typescript
import { handleGetTodayReadiness } from './src/tools/readiness.js';

const result = await handleGetTodayReadiness({});
console.log(result);
```

## Claude Desktop Integration

Integrate the Oura MCP server with Claude Desktop for AI-powered health analysis.

### Step 1: Locate Claude Desktop Config

The configuration file location depends on your operating system:

**macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```bash
~/.config/Claude/claude_desktop_config.json
```

### Step 2: Edit Configuration

Open the config file in a text editor:

```bash
# macOS
code ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or use nano
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Step 3: Add Oura MCP Server

Add this configuration (replace paths with your actual paths):

```json
{
  "mcpServers": {
    "oura-mcp": {
      "command": "node",
      "args": [
        "/Users/yourusername/Projects/Thanos/mcp-servers/oura-mcp/dist/index.js"
      ],
      "env": {
        "OURA_ACCESS_TOKEN": "your_oura_personal_access_token_here"
      }
    }
  }
}
```

**Important notes:**
1. **Use absolute paths** - relative paths won't work
2. **Replace `/Users/yourusername/Projects/Thanos/...`** with your actual path
3. **Replace `your_oura_personal_access_token_here`** with your actual token
4. **Check JSON syntax** - no trailing commas, proper quotes

**To get the absolute path:**
```bash
cd /path/to/oura-mcp
pwd
# Copy this path and add /dist/index.js
```

### Step 4: Restart Claude Desktop

1. **Quit Claude Desktop completely** (don't just close the window)
   - macOS: `Cmd+Q` or `Claude → Quit Claude`
   - Windows: Right-click taskbar icon → Quit
2. **Reopen Claude Desktop**

### Step 5: Verify Connection

1. Open a new conversation in Claude Desktop
2. Look for the **🔌 icon** in the bottom-right corner
3. Click it to see connected MCP servers
4. You should see **"oura-mcp"** listed with 4 available tools

### Step 6: Test the Integration

Try these prompts in Claude Desktop:

```
Check my Oura health status
```

```
What's my readiness score today?
```

```
How did I sleep last night?
```

```
Show me my health trends for the past week
```

If Claude can respond with your actual Oura data, **congratulations!** 🎉 You're all set up.

## Common Setup Issues

### "Cannot find module" error

**Problem:** Node can't find the compiled JavaScript files

**Solution:**
```bash
npm run build
ls dist/  # Verify dist/ directory exists with .js files
```

### "Authentication failed" error

**Problem:** Token is invalid or missing

**Solutions:**
1. Check `.env` file has `OURA_ACCESS_TOKEN=...`
2. Verify token at https://cloud.ouraring.com/ (Personal Access Tokens)
3. Generate a new token if needed
4. Make sure there are no extra spaces in the `.env` file

### Server not showing in Claude Desktop

**Problem:** MCP server not appearing in Claude's 🔌 menu

**Solutions:**
1. Check JSON syntax in `claude_desktop_config.json` (use a JSON validator)
2. Verify absolute path to `dist/index.js` is correct
3. Make sure you quit and reopened Claude Desktop (not just closed window)
4. Check Claude Desktop logs for errors
5. Try running `npm start` manually to ensure server works

### "Permission denied" errors

**Problem:** Can't write to cache directory

**Solution:**
```bash
# Check cache directory permissions
ls -la ~/.oura-cache/

# Fix permissions if needed
chmod 755 ~/.oura-cache/
chmod 644 ~/.oura-cache/*.db
```

### "Rate limit exceeded"

**Problem:** Hit Oura's API limit (5000 requests/day)

**Solution:**
- This is normal if testing heavily
- Server will automatically use cached data
- Wait 24 hours for limit to reset
- Check `~/.oura-cache/rate-limit.json` for reset time

## Next Steps

Now that you're set up:

1. **Read the [README.md](./README.md)** for tool documentation
2. **Check [EXAMPLES.md](./EXAMPLES.md)** for usage examples
3. **Explore the Health Persona** integration in Thanos
4. **Set up health-aware task prioritization**

## Advanced Configuration

### Using OAuth Instead of Personal Access Token

For production or multi-user applications:

See [OAUTH_SETUP.md](./OAUTH_SETUP.md) for detailed OAuth configuration.

### Custom Cache Location

If you want to store cache somewhere other than `~/.oura-cache`:

```bash
# In .env
OURA_CACHE_DIR=/custom/path/to/cache
```

### Debugging

Enable detailed logging:

```bash
# In .env
DEBUG_SYNC=true          # Log cache synchronization
DEBUG_API_CALLS=true     # Log all API requests/responses
DEBUG_RATE_LIMIT=true    # Log rate limiting decisions
```

View logs:
```bash
# Run in development mode to see logs
npm run dev

# Or in production with logging to file
npm start 2>&1 | tee oura-mcp.log
```

## Getting Help

If you're stuck:

1. **Check the troubleshooting guide** in [README.md](./README.md#troubleshooting)
2. **Run the health check tool** in Claude: "Run oura_health_check"
3. **Enable debug logging** and check the output
4. **Verify Oura Ring** is syncing data in the Oura mobile app
5. **Check Claude Desktop logs** for MCP errors

## Resources

- **Oura Cloud:** https://cloud.ouraring.com/
- **Oura API Docs:** https://cloud.ouraring.com/docs/
- **MCP Documentation:** https://modelcontextprotocol.io
- **Claude Desktop:** https://claude.ai/download

---

**Setup Complete!** You're ready to use AI-powered health insights with your Oura Ring data. 🎉
