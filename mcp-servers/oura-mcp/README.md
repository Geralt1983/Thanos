# Oura Health Metrics MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that integrates with the Oura Ring API to provide AI assistants with access to sleep scores, readiness scores, activity data, and HRV metrics.

[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org/)
[![MCP SDK](https://img.shields.io/badge/MCP%20SDK-1.0-green.svg)](https://github.com/modelcontextprotocol/sdk)

## ✨ Features

- **OAuth Authentication** - Secure authentication with Oura Ring API
- **Comprehensive Health Metrics** - Access sleep, readiness, activity, and HRV data
- **Smart Caching** - SQLite cache reduces API calls and improves performance
- **Rate Limiting** - Respects Oura API limits (5000 requests/day)
- **Graceful Degradation** - Returns cached data when API is unavailable
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
OURA_CLIENT_ID=your_client_id_here
OURA_CLIENT_SECRET=your_client_secret_here
OURA_ACCESS_TOKEN=your_access_token_here
```

See the [OAuth Setup Guide](#oauth-setup-guide) below for detailed instructions on obtaining these credentials.

### Running the Server

```bash
# Production
npm start

# Development (with hot reload)
npm run dev
```

The server will start and listen for MCP protocol requests over stdio.

## 🔑 OAuth Setup Guide

### Step 1: Create an Oura Application

1. Go to [Oura Cloud OAuth Applications](https://cloud.ouraring.com/oauth/applications)
2. Log in with your Oura account
3. Click "Create a new OAuth application"
4. Fill in the application details:
   - **Name**: Thanos Oura MCP Server (or any name you prefer)
   - **Redirect URI**: `http://localhost:3000/callback` (for local testing)
   - **Scopes**: Select all scopes (daily, heartrate, workout, session, tag, personal, sleep)

5. Click "Create application"

### Step 2: Get Your Credentials

After creating the application, you'll see:
- **Client ID**: Copy this to `OURA_CLIENT_ID` in your `.env` file
- **Client Secret**: Copy this to `OURA_CLIENT_SECRET` in your `.env` file

### Step 3: Generate an Access Token

For development and testing, you can generate a personal access token:

1. In your Oura application settings, look for "Personal Access Token"
2. Click "Create Personal Access Token"
3. Select the required scopes (daily, heartrate, workout, session, tag, personal, sleep)
4. Copy the generated token to `OURA_ACCESS_TOKEN` in your `.env` file

**Note**: Personal access tokens don't expire but have the same rate limits as OAuth tokens. For production use, implement the full OAuth flow with refresh tokens.

### Step 4: (Optional) OAuth Flow for Refresh Tokens

For automatic token renewal, implement the OAuth authorization flow:

1. Direct users to: `https://cloud.ouraring.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=YOUR_REDIRECT_URI`
2. User authorizes the application
3. Exchange the authorization code for an access token and refresh token
4. Store both tokens in your `.env` file

The server will automatically handle token refresh when needed.

## 🛠️ Available Tools

### `get_today_readiness`

Fetch today's readiness score and contributing factors.

**Returns**:
- Readiness score (0-100)
- Contributing factors (sleep, HRV, temperature, activity balance, etc.)
- Timestamp of last update

**Example usage**:
```typescript
{
  "readiness_score": 85,
  "contributors": {
    "sleep_score": 88,
    "hrv_balance": 92,
    "temperature": 85,
    "activity_balance": 78,
    "resting_heart_rate": 90
  },
  "timestamp": "2026-01-11T08:00:00Z"
}
```

### `get_sleep_summary`

Fetch sleep summary for a specific date (defaults to last night).

**Parameters**:
- `date` (optional): Date in YYYY-MM-DD format. Defaults to last night.

**Returns**:
- Sleep score (0-100)
- Total sleep time
- Sleep stages (REM, deep, light sleep durations)
- Sleep efficiency
- Latency and timing

**Example usage**:
```typescript
{
  "date": "2026-01-10",
  "sleep_score": 82,
  "total_sleep_seconds": 26100,  // 7h 15m
  "rem_sleep_seconds": 6300,
  "deep_sleep_seconds": 5400,
  "light_sleep_seconds": 14400,
  "efficiency": 91,
  "latency_seconds": 480
}
```

### `get_weekly_trends`

Fetch weekly health trends and patterns.

**Returns**:
- 7-day trends for readiness, sleep, and activity scores
- Statistical summary (average, min, max)
- Trend direction (improving, declining, stable)
- Pattern insights

**Example usage**:
```typescript
{
  "period": "2026-01-04 to 2026-01-10",
  "readiness": {
    "average": 82,
    "min": 68,
    "max": 92,
    "trend": "improving",
    "daily_scores": [68, 75, 78, 82, 85, 88, 92]
  },
  "sleep": {
    "average": 79,
    "min": 65,
    "max": 88,
    "trend": "stable",
    "daily_scores": [78, 79, 82, 75, 77, 80, 88]
  },
  "insights": [
    "Readiness improving over the week",
    "Sleep quality consistent"
  ]
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
| `OURA_CLIENT_ID` | OAuth client ID | Required |
| `OURA_CLIENT_SECRET` | OAuth client secret | Required |
| `OURA_ACCESS_TOKEN` | OAuth access token | Required |
| `OURA_REFRESH_TOKEN` | OAuth refresh token | Optional |
| `CACHE_DB_PATH` | SQLite cache path | `.cache/oura-health.db` |
| `CACHE_TTL` | Cache TTL in seconds | `3600` (1 hour) |
| `RATE_LIMIT_MAX_REQUESTS` | Max requests per day | `5000` |
| `RATE_LIMIT_WINDOW` | Rate limit window (ms) | `86400000` (24h) |
| `LOG_LEVEL` | Logging level | `info` |
| `DEBUG_API_CALLS` | Enable debug logging | `false` |

## 🔗 Integration with Claude Desktop

Add this server to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "oura-health": {
      "command": "node",
      "args": ["/path/to/oura-mcp/dist/index.js"],
      "env": {
        "OURA_CLIENT_ID": "your_client_id",
        "OURA_CLIENT_SECRET": "your_client_secret",
        "OURA_ACCESS_TOKEN": "your_access_token"
      }
    }
  }
}
```

## 🏥 Health Persona Integration

This MCP server is designed to work with the Thanos Health persona. Example prompts:

- "What's my readiness score today?"
- "How did I sleep last night?"
- "Show me my sleep trends for the past week"
- "Should I do a hard workout today based on my recovery?"

The Health persona can use this data to provide personalized recommendations based on your physical state.

## 🐛 Troubleshooting

### "Invalid credentials" error

- Verify your `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET`, and `OURA_ACCESS_TOKEN` are correct
- Check that your personal access token hasn't been revoked
- Ensure your OAuth application has the required scopes

### "Rate limit exceeded" error

- You've hit the 5000 requests/day limit
- Wait for the rate limit window to reset (24 hours)
- Consider increasing cache TTL to reduce API calls

### "No data available" error

- Make sure you're wearing your Oura Ring regularly
- Data may not be available for today until it's synced
- Check the Oura app to verify data is present

### Cache not updating

- Check that `.cache/oura-health.db` is writable
- Verify `CACHE_TTL` is set appropriately
- Try manually deleting the cache file to force a refresh

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
