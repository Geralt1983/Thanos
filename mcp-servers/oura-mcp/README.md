# Oura Health Metrics MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that integrates with the Oura Ring API to provide AI assistants with access to sleep scores, readiness scores, activity data, and HRV metrics.

[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org/)
[![MCP SDK](https://img.shields.io/badge/MCP%20SDK-1.0-green.svg)](https://github.com/modelcontextprotocol/sdk)

## ✨ Features

- **Personal Access Token Auth** - Simple, secure authentication with Oura Ring API
- **4 MCP Tools** - Readiness, sleep, trends, and health check diagnostics
- **Comprehensive Health Metrics** - Access sleep, readiness, activity, and HRV data
- **Smart Caching** - SQLite cache reduces API calls and improves performance
- **Rate Limiting** - Respects Oura API limits (5000 requests/day)
- **Graceful Degradation** - Returns cached data when API is unavailable
- **Health Diagnostics** - Built-in health check tool for troubleshooting
- **Type-Safe** - Full TypeScript support with Zod validation

## 🚀 Quick Start

### Prerequisites

- Node.js 18 or higher
- An Oura Ring account
- Oura API credentials (see Setup Guide below)

### Installation

```bash
# Install dependencies
npm install

# Build the TypeScript project
npm run build
```

### Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Configure your Oura API credentials in `.env`:

```bash
# Required: Oura Personal Access Token
OURA_API_KEY=your_oura_personal_access_token_here

# Optional: Custom cache directory (defaults to ~/.oura-cache)
# OURA_CACHE_DIR=/path/to/cache

# Optional: Enable sync debugging
# DEBUG_SYNC=true
```

See the [Personal Access Token Setup](#personal-access-token-setup) below for detailed instructions on obtaining your token.

### Running the Server

```bash
# Production
npm start

# Development (with hot reload)
npm run dev
```

The server will start and listen for MCP protocol requests over stdio.

## 🔑 Personal Access Token Setup

### Step 1: Navigate to Oura Cloud

1. Go to [Oura Cloud](https://cloud.ouraring.com/)
2. Log in with your Oura account

### Step 2: Create Personal Access Token

1. Click on your profile icon (top right)
2. Select **Personal Access Tokens** from the dropdown menu
3. Click **Create A New Personal Access Token**
4. Give it a descriptive name (e.g., "Thanos MCP Server")
5. The token will be generated and displayed **only once** - copy it immediately!

### Step 3: Configure Environment

Paste your token into the `.env` file:

```bash
OURA_API_KEY=your_copied_token_here
```

**Important Security Notes**:
- Personal Access Tokens provide read-only access to your health data
- Tokens don't expire unless you revoke them
- Never commit your `.env` file to version control
- Keep your token secure - treat it like a password
- You can revoke tokens anytime at https://cloud.ouraring.com/

### Why Personal Access Tokens?

This server uses Personal Access Tokens instead of OAuth for simplicity:
- ✅ No complex OAuth flow needed
- ✅ Read-only access (can't modify your data)
- ✅ Easy to set up and test
- ✅ Same rate limits as OAuth (5000 requests/day)
- ✅ No token refresh needed (doesn't expire)

For production applications with multiple users, OAuth with refresh tokens would be more appropriate.

## 🛠️ Available Tools

### `oura_get_today_readiness`

Fetch today's readiness score and contributing factors.

**Parameters**:
- `date` (optional): Date in YYYY-MM-DD format. Defaults to today.

**Returns**:
- Readiness score (0-100) with interpretation
- 8 contributors with scores and explanations
- Raw metrics (temperature, HRV, resting heart rate)
- Data source indicator (cache, api, cache_stale)

**Example response**:
```json
{
  "date": "2026-01-11",
  "score": 85,
  "interpretation": "Good - Ready for moderate activity",
  "contributors": {
    "sleep_score": { "score": 88, "meaning": "Good sleep quality" },
    "hrv_balance": { "score": 92, "meaning": "Excellent recovery" },
    "body_temperature": { "score": 85, "meaning": "Normal temperature deviation" },
    "resting_heart_rate": { "score": 90, "meaning": "Good cardiovascular recovery" },
    "activity_balance": { "score": 78, "meaning": "Moderate activity recovery" },
    "sleep_balance": { "score": 82, "meaning": "Good sleep consistency" },
    "previous_day": { "score": 80, "meaning": "Good activity level" },
    "recovery_index": { "score": 87, "meaning": "Good overall recovery" }
  },
  "metrics": {
    "temperature_celsius": 36.5,
    "hrv_ms": 55,
    "resting_hr_bpm": 52
  },
  "source": "cache"
}
```

### `oura_get_sleep_summary`

Fetch sleep summary for a specific date (defaults to last night).

**Parameters**:
- `date` (optional): Date in YYYY-MM-DD format. Defaults to last night.

**Returns**:
- Sleep score (0-100) with interpretation
- Duration breakdown (total, REM, deep, light, awake)
- Sleep efficiency percentage
- 7 contributors with explanations
- Additional metrics (heart rate, HRV, breath rate, temperature)
- Data source indicator

**Example response**:
```json
{
  "date": "2026-01-10",
  "score": 82,
  "interpretation": "Good - Quality restorative sleep",
  "duration": {
    "total_seconds": 26100,
    "total_hours": 7.25,
    "rem_seconds": 6300,
    "rem_hours": 1.75,
    "deep_seconds": 5400,
    "deep_hours": 1.5,
    "light_seconds": 14400,
    "light_hours": 4.0,
    "awake_seconds": 900,
    "awake_hours": 0.25
  },
  "efficiency": {
    "percentage": 91,
    "interpretation": "Excellent - Minimal time awake"
  },
  "contributors": {
    "total_sleep": { "score": 85, "meaning": "Good duration" },
    "efficiency": { "score": 91, "meaning": "Excellent efficiency" },
    "restfulness": { "score": 88, "meaning": "Good restfulness" },
    "rem_sleep": { "score": 82, "meaning": "Good REM duration" },
    "deep_sleep": { "score": 80, "meaning": "Good deep sleep" },
    "latency": { "score": 90, "meaning": "Fast sleep onset" },
    "timing": { "score": 85, "meaning": "Good sleep schedule" }
  },
  "source": "cache"
}
```

### `oura_get_weekly_trends`

Fetch weekly health trends and patterns with statistical analysis.

**Parameters**:
- `days` (optional): Number of days to analyze (1-30). Defaults to 7.

**Returns**:
- Statistical summary for readiness, sleep, and activity
- Trend direction with percentage change
- Daily score arrays
- Cross-metric pattern insights
- Data source indicators for each metric

**Example response**:
```json
{
  "period": {
    "start_date": "2026-01-04",
    "end_date": "2026-01-10",
    "days": 7
  },
  "readiness": {
    "average": 82,
    "min": 68,
    "max": 92,
    "trend": "improving",
    "trend_percentage": 15.3,
    "daily_scores": [68, 75, 78, 82, 85, 88, 92],
    "source": "cache"
  },
  "sleep": {
    "average": 79,
    "min": 65,
    "max": 88,
    "trend": "stable",
    "trend_percentage": 2.1,
    "daily_scores": [78, 79, 82, 75, 77, 80, 88],
    "source": "cache"
  },
  "activity": {
    "average": 75,
    "min": 60,
    "max": 85,
    "trend": "declining",
    "trend_percentage": -8.2,
    "daily_scores": [85, 80, 78, 75, 70, 65, 60],
    "source": "cache"
  },
  "patterns": [
    "Readiness improving significantly over the week (+15.3%)",
    "Sleep quality stable with consistent scores",
    "Activity declining while readiness improves - good recovery balance"
  ]
}
```

### `oura_health_check`

Check the health status of the Oura MCP server for troubleshooting.

**Parameters**:
- `include_cache_samples` (optional): If true, includes sample data from cache. Defaults to false.

**Returns**:
- Overall health status (healthy, degraded)
- API connectivity status with response time
- Cache status with entry counts
- Rate limit information
- Diagnostic recommendations

**Example response**:
```json
{
  "overall_status": "healthy",
  "timestamp": "2026-01-11T19:45:00.000Z",
  "components": {
    "api": {
      "status": "connected",
      "message": "Successfully connected to Oura API",
      "response_time_ms": 245,
      "status_code": 200
    },
    "cache": {
      "status": "healthy",
      "message": "Cache is healthy with 127 total entries",
      "statistics": {
        "readiness_entries": 45,
        "sleep_entries": 42,
        "activity_entries": 40,
        "total_entries": 127
      },
      "last_sync": {
        "date": "2026-01-11",
        "hasDataToday": true
      }
    }
  },
  "diagnostics": {
    "can_fetch_fresh_data": true,
    "can_use_cached_data": true,
    "has_today_data": true,
    "recommendations": [
      "✅ System is healthy and ready. Today's data is available."
    ]
  }
}
```

## 📁 Project Structure

```
oura-mcp/
├── src/
│   ├── index.ts              # Main server entry point
│   ├── api/                  # Oura API client
│   │   ├── client.ts         # API client implementation
│   │   ├── oauth.ts          # OAuth flow handling
│   │   ├── rate-limiter.ts   # Rate limiting logic
│   │   ├── types.ts          # TypeScript interfaces
│   │   └── schemas.ts        # Zod validation schemas
│   ├── cache/                # SQLite caching layer
│   │   ├── db.ts             # Database initialization
│   │   ├── operations.ts     # Cache CRUD operations
│   │   ├── schema.ts         # Cache schema definition
│   │   └── sync.ts           # Background sync logic
│   ├── tools/                # MCP tool implementations
│   │   ├── readiness.ts      # get_today_readiness
│   │   ├── sleep.ts          # get_sleep_summary
│   │   ├── trends.ts         # get_weekly_trends
│   │   └── health-check.ts   # API health check
│   └── shared/               # Shared utilities
│       ├── errors.ts         # Custom error types
│       └── utils.ts          # Common utilities
├── dist/                     # Compiled JavaScript
├── .cache/                   # SQLite cache database
├── .env.example              # Environment template
└── README.md                 # This file
```

## 💾 Caching Strategy

The server uses a cache-first strategy to minimize API calls:

1. **Cache-First Reads**: Always check cache before hitting the API
2. **Stale Detection**: Cache expires after 1 hour (configurable)
3. **Background Sync**: Automatic cache refresh when stale
4. **Write-Through**: API updates also update cache
5. **Graceful Degradation**: Return stale cache data if API fails

This approach ensures:
- Fast response times
- Reduced API usage
- Resilience to API outages
- Better user experience

## ⚡ Rate Limiting

The Oura API has a limit of 5000 requests per day. This server implements:

- **Request Tracking**: Counts API calls within 24-hour window
- **Exponential Backoff**: Handles 429 (Too Many Requests) responses
- **Request Queue**: Serializes concurrent requests
- **Smart Caching**: Reduces need for API calls

## 🧪 Testing

```bash
# Run all tests
npm test

# Run specific test suites
npm run test:api
npm run test:cache
npm run test:tools
```

## 🔧 Configuration

All configuration is managed through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OURA_API_KEY` | Personal Access Token | Required |
| `OURA_CACHE_DIR` | Cache directory path | `~/.oura-cache` |
| `DEBUG_SYNC` | Enable sync debugging | `false` |

## 🔗 Integration with Claude Desktop

Add this server to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "oura-mcp": {
      "command": "node",
      "args": ["/absolute/path/to/oura-mcp/dist/index.js"],
      "env": {
        "OURA_API_KEY": "your_personal_access_token_here"
      }
    }
  }
}
```

**Important Notes**:
- Use **absolute paths** for the `args` array
- Replace `/absolute/path/to/oura-mcp` with your actual installation path
- Replace `your_personal_access_token_here` with your Oura Personal Access Token
- Restart Claude Desktop after modifying the configuration

**Verification**:
1. Restart Claude Desktop
2. Open a new conversation
3. Look for the 🔌 icon in the bottom-right to confirm the server is connected
4. Try asking: "Check my Oura health status" or "What's my readiness score today?"

## 🏥 Health Persona Integration

This MCP server is designed to work with the Thanos Health persona. Example prompts:

- "What's my readiness score today?"
- "How did I sleep last night?"
- "Show me my sleep trends for the past week"
- "Should I do a hard workout today based on my recovery?"

The Health persona can use this data to provide personalized recommendations based on your physical state.

## 🐛 Troubleshooting

### Using the Health Check Tool

The best way to diagnose issues is to use the built-in health check tool:

```
Ask Claude: "Run oura_health_check"
```

This will provide comprehensive diagnostics including:
- API connectivity status and response time
- Cache database health and entry counts
- Rate limit status and remaining quota
- Actionable recommendations for fixing issues

### Common Issues

#### "Invalid credentials" or "Authentication failed" error

**Symptoms**: Error 401 or 403 when trying to fetch data

**Solutions**:
1. Run health check to verify API connectivity
2. Check your `OURA_API_KEY` in `.env` file is correct
3. Verify token hasn't been revoked at https://cloud.ouraring.com/
4. Generate a new Personal Access Token if needed
5. Restart the MCP server after updating credentials

#### "Rate limit exceeded" error

**Symptoms**: Error 429, health check shows rate_limited status

**Solutions**:
1. Check health check output for rate limit reset time
2. Wait for the 24-hour window to reset
3. Cache will automatically serve stale data during rate limits
4. Consider reducing query frequency if hitting limits regularly
5. The server respects Oura's 5000 requests/day limit

#### "No data available" error

**Symptoms**: Tools return null or empty data

**Solutions**:
1. Run health check to see if today's data exists in cache
2. Verify you're wearing your Oura Ring regularly
3. Check the Oura app to confirm data has synced
4. Data typically syncs in the morning after waking
5. Try using a date parameter for yesterday's data: `{ "date": "2026-01-10" }`

#### Cache not updating

**Symptoms**: Stale data, health check shows old last_sync date

**Solutions**:
1. Run health check to see cache statistics
2. Check that cache directory (`~/.oura-cache`) is writable
3. Verify no permission issues on the SQLite database
4. Try clearing cache: `rm -rf ~/.oura-cache` (will refetch from API)
5. Check if DEBUG_SYNC=true in .env shows sync activity

#### Server not appearing in Claude Desktop

**Symptoms**: MCP server not listed, 🔌 icon not shown

**Solutions**:
1. Verify configuration file location: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Check JSON syntax is valid (no trailing commas, proper quotes)
3. Ensure absolute path to `dist/index.js` is correct
4. Run `npm run build` to ensure compiled JavaScript exists
5. Restart Claude Desktop completely (Quit and reopen)
6. Check Claude Desktop logs for error messages

#### TypeScript compilation errors

**Symptoms**: `npm run build` fails

**Solutions**:
1. Run `npm install` to ensure dependencies are installed
2. Check Node.js version (requires 18+)
3. Verify tsconfig.json exists and is valid
4. Review error messages for missing types or imports
5. Try `rm -rf node_modules package-lock.json && npm install`

## 📚 API Documentation

For detailed Oura API documentation, see:
- [Oura API Docs](https://cloud.ouraring.com/docs/)
- [API Reference](https://cloud.ouraring.com/v2/docs)

## 📝 License

This is a private project integrated with the Thanos ecosystem.

## 🔗 Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io) - Protocol specification
- [MCP SDK](https://github.com/modelcontextprotocol/sdk) - TypeScript SDK
- [Oura Ring](https://ouraring.com/) - Health tracking device

---

**Last Updated**: 2026-01-11
**Part of**: Thanos Multi-Agent OS
**Task**: #041 - Oura Health Metrics MCP Adapter
