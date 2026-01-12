# Architecture Documentation - Oura Health Metrics MCP Server

Technical architecture documentation for developers working with or extending the Oura MCP server.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Authentication System](#authentication-system)
- [Caching Strategy](#caching-strategy)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Type System](#type-system)
- [Extending the Server](#extending-the-server)

## System Overview

The Oura MCP Server is a TypeScript-based MCP (Model Context Protocol) server that provides AI assistants with access to Oura Ring health metrics through a set of well-defined tools.

### Key Design Principles

1. **Cache-First Architecture**: Minimize API calls through intelligent caching
2. **Graceful Degradation**: Always return useful data, even when API fails
3. **Type Safety**: Full TypeScript with runtime validation via Zod
4. **Resilience**: Comprehensive error handling and retry logic
5. **Observability**: Built-in health checks and debugging tools

### Technology Stack

- **Runtime**: Node.js 18+
- **Language**: TypeScript 5.7
- **MCP SDK**: @modelcontextprotocol/sdk ^1.0
- **HTTP Client**: Axios ^1.7
- **Database**: SQLite (better-sqlite3 ^11.0)
- **Validation**: Zod ^3.24
- **Transport**: stdio (MCP protocol)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         MCP Client                           │
│                    (Claude Desktop, etc.)                    │
└─────────────────────────┬───────────────────────────────────┘
                          │ stdio (MCP Protocol)
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    MCP Server (index.ts)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Request Router & Tool Registry              │   │
│  │  • ListToolsRequestSchema                           │   │
│  │  • CallToolRequestSchema                            │   │
│  └──────────────┬───────────────────────┬───────────────┘   │
│                 │                       │                    │
│    ┌────────────▼─────────┐  ┌─────────▼────────────┐       │
│    │   MCP Tools Layer    │  │  Health Check Tool   │       │
│    │  • readiness.ts      │  │  • Diagnostics       │       │
│    │  • sleep.ts          │  │  • System status     │       │
│    │  • trends.ts         │  └──────────────────────┘       │
│    └────────────┬─────────┘                                 │
└─────────────────┼─────────────────────────────────────────┘
                  │
    ┌─────────────▼──────────────┐
    │   Shared Error Handling    │
    │  • OuraMCPError            │
    │  • handleToolError()       │
    │  • Graceful degradation    │
    └─────────────┬──────────────┘
                  │
    ┌─────────────▼──────────────┐
    │    Cache Layer (SQLite)    │
    │  • db.ts - Connection      │
    │  • schema.ts - Tables      │
    │  • operations.ts - CRUD    │
    │  • sync.ts - Background    │
    └─────────────┬──────────────┘
                  │
    ┌─────────────▼──────────────┐
    │      API Client Layer      │
    │  • client.ts - HTTP        │
    │  • oauth.ts - Auth         │
    │  • rate-limiter.ts         │
    │  • schemas.ts - Validation │
    │  • types.ts - TypeScript   │
    └─────────────┬──────────────┘
                  │
    ┌─────────────▼──────────────┐
    │       Oura API v2          │
    │  https://api.ouraring.com  │
    └────────────────────────────┘
```

## Core Components

### 1. MCP Server (`src/index.ts`)

**Purpose**: Main entry point and request router

**Responsibilities**:
- Initialize MCP server with stdio transport
- Register MCP tools
- Route incoming requests to appropriate handlers
- Global error handling
- Graceful shutdown

**Key Code**:
```typescript
const server = new Server(
  {
    name: "oura-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      getTodayReadinessTool,
      getSleepSummaryTool,
      getWeeklyTrendsTool,
      healthCheckTool,
    ],
  };
});
```

### 2. MCP Tools (`src/tools/`)

**Purpose**: Implement the four MCP tools

#### readiness.ts
- Tool: `oura_get_today_readiness`
- Fetches readiness score and contributors
- Provides interpretation for LLM consumption
- Cache-first with API fallback

#### sleep.ts
- Tool: `oura_get_sleep_summary`
- Fetches sleep metrics and stages
- Calculates percentages and formatted durations
- Includes all contributors and metrics

#### trends.ts
- Tool: `oura_get_weekly_trends`
- Analyzes multi-day health trends
- Statistical analysis (avg, min, max, trend direction)
- Pattern recognition (overtraining, recovery synergy)
- Cross-metric correlation

#### health-check.ts
- Tool: `oura_health_check`
- System diagnostics
- API connectivity test
- Cache health verification
- Rate limit status
- Actionable recommendations

### 3. API Client (`src/api/client.ts`)

**Purpose**: HTTP client for Oura API v2

**Features**:
- Axios-based with interceptors
- Automatic authentication via OAuth client
- Request/response logging (when `DEBUG_API_CALLS=true`)
- Retry logic with exponential backoff
- Pagination handling
- Error handling with context

**Key Methods**:
```typescript
class OuraAPIClient {
  async getDailySleep(options: APIRequestOptions): Promise<DailySleep[]>
  async getDailyReadiness(options: APIRequestOptions): Promise<DailyReadiness[]>
  async getDailyActivity(options: APIRequestOptions): Promise<DailyActivity[]>
  async getHeartRate(options: APIRequestOptions): Promise<HeartRateData[]>
}
```

### 4. OAuth Client (`src/api/oauth.ts`)

**Purpose**: Handle authentication with Oura API

**Supports Two Auth Methods**:
1. **Personal Access Token**: Simple, no expiration
2. **OAuth 2.0**: Full flow with token refresh

**Features**:
- Token caching to `.cache/oura-tokens.json`
- Automatic token refresh (5-minute buffer before expiration)
- Token revocation
- Fallback to `OURA_ACCESS_TOKEN` env var

**Key Methods**:
```typescript
class OuraOAuthClient {
  async getValidAccessToken(): Promise<string>
  async refreshAccessToken(): Promise<StoredTokenData>
  async exchangeCodeForToken(code: string, redirectUri: string): Promise<OuraTokenResponse>
  getAuthorizationUrl(redirectUri: string): string
}
```

### 5. Rate Limiter (`src/api/rate-limiter.ts`)

**Purpose**: Respect Oura API limits (5000 requests/24 hours)

**Strategy**: Sliding window with persistent state

**Features**:
- Tracks requests in 24-hour sliding window
- Exponential backoff calculation
- Request queue when limit reached
- Persistent state to `.cache/rate-limit.json`
- Statistics and monitoring

**Key Methods**:
```typescript
class RateLimiter {
  async checkRateLimit(): Promise<boolean>
  recordRequest(): void
  handleRateLimitResponse(retryAfter?: number): void
  getRateLimitStats(): RateLimitStats
}
```

### 6. Cache Layer (`src/cache/`)

**Purpose**: SQLite-based caching to reduce API calls

#### Database (`db.ts`)
- SQLite connection management
- WAL mode for better concurrency
- Singleton pattern
- Graceful shutdown
- Database statistics

#### Schema (`schema.ts`)
- Table definitions for:
  - `sleep_data`
  - `readiness_data`
  - `activity_data`
  - `heart_rate_data`
  - `api_tokens`
  - `cache_meta`
- Indexes for date-based queries
- Migration system
- TTL and expiry logic

#### Operations (`operations.ts`)
- CRUD operations for all data types
- Cache-first pattern
- Expiry detection
- Bulk operations
- Statistics and monitoring

#### Sync (`sync.ts`)
- Background synchronization
- Staleness detection
- Parallel data fetching
- Sync status tracking
- Configurable history depth (default: 7 days)

## Data Flow

### 1. Tool Invocation Flow

```
Claude Desktop
  │
  ├─ User: "What's my readiness today?"
  │
  ▼
MCP Protocol (stdio)
  │
  ├─ CallToolRequest: { name: "oura_get_today_readiness", arguments: {} }
  │
  ▼
index.ts (Request Router)
  │
  ├─ Routes to: handleGetTodayReadiness()
  │
  ▼
readiness.ts (Tool Handler)
  │
  ├─ 1. Check cache: getCachedReadiness(today)
  │    ├─ Cache HIT → Return cached data
  │    └─ Cache MISS → Continue to API
  │
  ├─ 2. Fetch from API: client.getDailyReadiness()
  │    │
  │    ▼
  │  client.ts (API Client)
  │    ├─ Check rate limit
  │    ├─ Get valid access token (auto-refresh if needed)
  │    ├─ Make HTTP request
  │    ├─ Retry on transient failures
  │    └─ Validate response with Zod schema
  │
  ├─ 3. Cache API response: setCachedReadiness()
  │
  ├─ 4. Format for LLM consumption
  │    ├─ Add interpretations
  │    ├─ Add meanings to contributors
  │    └─ Add source indicator
  │
  └─ 5. Return to Claude
       │
       ▼
Claude Desktop
  │
  └─ Displays formatted response to user
```

### 2. Cache Sync Flow

```
Server Startup
  │
  ▼
CacheSync.initializeSync()
  │
  ├─ Check last sync time
  ├─ If stale (>1 hour) → Trigger sync
  │
  ▼
CacheSync.syncNow()
  │
  ├─ Determine date range (last 7 days)
  │
  ├─ Parallel fetch:
  │    ├─ Sleep data
  │    ├─ Readiness data
  │    └─ Activity data
  │
  ├─ For each data type:
  │    ├─ Fetch from API (with rate limiting)
  │    ├─ Validate with Zod schema
  │    └─ Write to cache
  │
  ├─ Update last sync timestamp
  │
  └─ Return sync results
```

### 3. Authentication Flow

```
API Request
  │
  ▼
client.ts
  │
  ├─ Interceptor: Request authentication
  │
  ▼
oauth.ts: getValidAccessToken()
  │
  ├─ Check if token exists
  │    ├─ Env var: OURA_ACCESS_TOKEN
  │    └─ Cached: .cache/oura-tokens.json
  │
  ├─ Check if token expired
  │    ├─ If expires within 5 min → Refresh
  │    └─ If valid → Use it
  │
  ├─ Refresh if needed:
  │    ├─ POST /oauth/token (with refresh_token)
  │    ├─ Get new access + refresh tokens
  │    └─ Cache new tokens
  │
  └─ Return valid access token
       │
       ▼
client.ts
  │
  └─ Add to header: Authorization: Bearer {token}
```

## Authentication System

### Two Modes

#### 1. Personal Access Token (Recommended for Personal Use)

**Configuration**:
```bash
OURA_ACCESS_TOKEN=your_token_here
```

**Flow**:
1. User creates PAT at cloud.ouraring.com
2. Token stored in `.env` file
3. OAuth client returns env var when requested
4. No expiration, no refresh needed

**Pros**:
- ✅ Simple setup
- ✅ No expiration
- ✅ No OAuth flow needed

**Cons**:
- ❌ Manual token management
- ❌ Can't be revoked remotely (must regenerate)
- ❌ Not suitable for multi-user apps

#### 2. OAuth 2.0 (For Production Apps)

**Configuration**:
```bash
OURA_CLIENT_ID=your_client_id
OURA_CLIENT_SECRET=your_client_secret
```

**Flow**:
1. User authorizes application
2. App exchanges authorization code for tokens
3. Tokens cached to `.cache/oura-tokens.json`
4. Automatic refresh before expiration

**Pros**:
- ✅ Secure for multi-user apps
- ✅ Automatic token refresh
- ✅ Scoped permissions
- ✅ Can be revoked

**Cons**:
- ❌ Complex setup
- ❌ Requires web server for redirect
- ❌ Token refresh logic needed

## Caching Strategy

### Cache-First Pattern

```typescript
async function getData(date: string) {
  // 1. Try cache
  const cached = getCachedData(date);
  if (cached && !isExpired(cached)) {
    return { data: cached, source: 'cache' };
  }

  // 2. Fetch from API
  try {
    const fresh = await api.getData(date);
    setCachedData(date, fresh);
    return { data: fresh, source: 'api' };
  } catch (error) {
    // 3. Fallback to stale cache on API failure
    if (cached) {
      return { data: cached, source: 'cache_stale' };
    }
    throw error;
  }
}
```

### Cache Expiration

- **TTL**: 1 hour (configurable via `CACHE_TTL_HOURS`)
- **Staleness Detection**: Checked on every read
- **Automatic Cleanup**: `cleanupExpiredCache()` removes old entries
- **Graceful Degradation**: Stale cache used when API unavailable

### Cache Schema

**Tables**:
1. `sleep_data` - Daily sleep summaries
2. `readiness_data` - Daily readiness scores
3. `activity_data` - Daily activity summaries
4. `heart_rate_data` - Heart rate time series
5. `api_tokens` - OAuth token storage
6. `cache_meta` - Metadata (last sync, schema version)

**Indexes**:
- `idx_*_day` - Fast lookups by date
- `idx_*_expires` - Fast expiry cleanup

**Storage**:
- Location: `~/.oura-cache/oura-health.db`
- Format: SQLite 3
- Mode: WAL (Write-Ahead Logging) for better concurrency

## Rate Limiting

### Sliding Window Algorithm

```typescript
class RateLimiter {
  private requests: number[] = []; // Timestamps of requests
  private readonly maxRequests = 5000; // Per 24 hours
  private readonly windowMs = 24 * 60 * 60 * 1000; // 24 hours

  checkRateLimit(): boolean {
    const now = Date.now();
    const windowStart = now - this.windowMs;

    // Remove requests outside window
    this.requests = this.requests.filter(t => t > windowStart);

    // Check if under limit
    return this.requests.length < this.maxRequests;
  }
}
```

### Features

1. **Persistent State**: Survives server restarts
2. **Exponential Backoff**: Smart retry delays
3. **Request Queue**: Serializes when limit reached
4. **Statistics**: Track usage and remaining quota
5. **Configurable**: Adjust limits via environment variables

### Rate Limit Response Handling

```typescript
if (response.status === 429) {
  const retryAfter = response.headers['retry-after'];
  const delay = rateLimiter.handleRateLimitResponse(retryAfter);
  await sleep(delay);
  return retry();
}
```

## Error Handling

### Error Hierarchy

```
OuraMCPError (Base)
  ├── OuraAuthError (401, 403, missing tokens)
  ├── OuraAPIError (network, server errors)
  ├── CacheError (SQLite failures)
  ├── RateLimitError (429, quota exceeded)
  └── ValidationError (schema validation failures)
```

### Error Handling Strategy

```typescript
try {
  return await fetchFromAPI();
} catch (error) {
  if (isAuthError(error)) {
    // Try to refresh token, return stale cache
  } else if (isRateLimitError(error)) {
    // Use cache, wait for reset
  } else if (isCacheError(error)) {
    // API-only mode, warn user
  } else {
    // Log, return graceful error message
  }
}
```

### Graceful Degradation

1. **Primary**: Fresh data from API
2. **Fallback 1**: Cached data (fresh)
3. **Fallback 2**: Cached data (stale but usable)
4. **Fallback 3**: Helpful error message with recommendations

### Error Messages for LLMs

All errors return user-friendly messages suitable for LLM interpretation:

```typescript
{
  error: "Unable to fetch readiness data",
  reason: "API rate limit exceeded",
  suggestion: "Using cached data from 2 hours ago. Rate limit resets in 4 hours.",
  data: { /* stale cached data */ },
  source: "cache_stale"
}
```

## Type System

### TypeScript Interfaces (`src/api/types.ts`)

Comprehensive type definitions for all Oura API responses:

```typescript
export interface DailyReadiness {
  id: string;
  day: DateString;
  score: Score | null;
  temperature_deviation: number | null;
  temperature_trend_deviation: number | null;
  contributors: ReadinessContributors;
  // ... more fields
}
```

### Zod Schemas (`src/api/schemas.ts`)

Runtime validation matching TypeScript interfaces:

```typescript
export const DailyReadinessSchema = z.object({
  id: z.string(),
  day: DateStringSchema,
  score: ScoreSchema.nullable(),
  temperature_deviation: z.number().nullable(),
  // ... matching all TypeScript fields
});
```

### Validation Flow

```
API Response
  │
  ▼
schemas.ts: validateResponse()
  │
  ├─ Parse with Zod schema
  ├─ Validate all fields
  ├─ Transform dates
  └─ Return typed data
       │
       ▼
Type-safe TypeScript code
```

### Type Guards

```typescript
export function isAuthError(error: unknown): error is OuraAuthError {
  return error instanceof OuraAuthError;
}

export function isRecoverableError(error: unknown): boolean {
  return isAPIError(error) || isCacheError(error);
}
```

## Extending the Server

### Adding a New Tool

1. **Define tool interface** (`src/tools/new-tool.ts`):

```typescript
import type { Tool } from '@modelcontextprotocol/sdk/types.js';

export const myNewTool: Tool = {
  name: "oura_my_new_tool",
  description: "Description for LLM to understand when to use this tool",
  inputSchema: {
    type: "object",
    properties: {
      param1: {
        type: "string",
        description: "Parameter description"
      }
    }
  }
};
```

2. **Implement handler**:

```typescript
export async function handleMyNewTool(args: any): Promise<any> {
  try {
    // 1. Check cache
    const cached = await getCachedData();
    if (cached) return cached;

    // 2. Fetch from API
    const fresh = await client.getData();

    // 3. Cache result
    await setCachedData(fresh);

    // 4. Format for LLM
    return formatForLLM(fresh);

  } catch (error) {
    return handleToolError(error);
  }
}
```

3. **Register in `src/index.ts`**:

```typescript
import { myNewTool, handleMyNewTool } from './tools/new-tool.js';

// Add to tools list
const tools = [
  getTodayReadinessTool,
  getSleepSummaryTool,
  getWeeklyTrendsTool,
  healthCheckTool,
  myNewTool, // ← Add here
];

// Add to router
case "oura_my_new_tool":
  return await handleMyNewTool(params.arguments);
```

4. **Add tests** (`test-new-tool.mjs`)

5. **Update documentation** (README.md)

### Adding a New API Endpoint

1. **Add TypeScript types** (`src/api/types.ts`):

```typescript
export interface NewData {
  id: string;
  date: DateString;
  metric: number;
  // ...
}
```

2. **Add Zod schema** (`src/api/schemas.ts`):

```typescript
export const NewDataSchema = z.object({
  id: z.string(),
  date: DateStringSchema,
  metric: z.number(),
  // ...
});
```

3. **Add API client method** (`src/api/client.ts`):

```typescript
async getNewData(options: APIRequestOptions): Promise<NewData[]> {
  const response = await this.requestWithRetry<NewData>({
    method: 'GET',
    url: '/usercollection/new_data',
    params: {
      start_date: options.start_date,
      end_date: options.end_date,
    },
  });
  return response.data.data;
}
```

4. **Add cache operations** (`src/cache/schema.ts` and `operations.ts`)

5. **Test the endpoint**

## Testing

### Test Structure

```
test-*.mjs                 # ESM test files
├── Unit Tests
│   ├── test-api-client.mjs
│   ├── test-oauth.mjs
│   ├── test-schemas.mjs
│   └── test-rate-limiter.mjs
├── Integration Tests
│   └── test-integration-mcp-tools.mjs
└── Component Tests
    ├── test-readiness-tool.mjs
    ├── test-sleep-tool.mjs
    └── test-trends-tool.mjs
```

### Running Tests

```bash
# Run all tests
find . -name "test-*.mjs" -exec node {} \;

# Run specific test
./test-readiness-tool.mjs
```

### Test Coverage

See [TEST_SUMMARY.md](./TEST_SUMMARY.md) for detailed coverage report.

## Performance Considerations

### Caching Impact

- **Without cache**: ~200-500ms per API request
- **With cache**: ~5-10ms per cache hit
- **Cache hit rate**: ~85% in typical usage

### Rate Limiting

- **Limit**: 5000 requests / 24 hours
- **Typical usage**: ~50-100 requests / day (with caching)
- **Headroom**: ~95% capacity available

### Database Performance

- **WAL mode**: Concurrent reads while writing
- **Indexes**: O(log n) lookups by date
- **Cleanup**: Periodic expiry cleanup (async)

## Security Considerations

1. **Credentials**: Never commit `.env` file
2. **Token Storage**: File permissions 600 on cache directory
3. **API Keys**: Treat as passwords
4. **SQLite**: Use parameterized queries (we do)
5. **MCP Protocol**: stdio transport (local only)

## Future Enhancements

Potential areas for extension:

1. **More Tools**:
   - Workout analysis
   - Tag management
   - Personal info queries

2. **Advanced Caching**:
   - Predictive pre-fetching
   - Smart cache warming
   - Redis for distributed caching

3. **Analytics**:
   - Long-term trend analysis
   - Anomaly detection
   - Predictive modeling

4. **Integrations**:
   - Calendar sync
   - Task management integration
   - Notification system

## Resources

- [MCP Specification](https://modelcontextprotocol.io)
- [Oura API Docs](https://cloud.ouraring.com/docs/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Better SQLite3 Docs](https://github.com/WiseLibs/better-sqlite3/blob/master/docs/api.md)

---

**Last Updated**: 2026-01-11
**Architecture Version**: 1.0.0
