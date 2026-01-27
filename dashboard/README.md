# Thanos Dashboard

A web-based visualization dashboard for the Thanos Operating System. Provides at-a-glance status of tasks, energy patterns, health metrics, and productivity correlations.

## Features

- **Tasks Widget**: View today's tasks, daily points progress, and streak status
- **Energy Chart**: 7-day energy trend with color-coded levels (high/medium/low)
- **Health Metrics**: Oura Ring readiness score, sleep balance, and top contributors
- **Correlation Chart**: Visualize the relationship between energy levels and task completion
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Auto-Refresh**: Widgets automatically update every 60 seconds
- **Dark Cosmic Theme**: Thanos-inspired deep space aesthetic

## Architecture

```
dashboard/
├── backend (Python + FastAPI)
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── mcp_client.py        # MCP server communication
│   └── api/                 # API endpoints
│       ├── tasks.py         # Tasks and metrics
│       ├── energy.py        # Energy logs
│       ├── health.py        # Oura readiness data
│       └── correlations.py  # Productivity correlations
│
└── frontend (React + TypeScript + Vite)
    ├── src/
    │   ├── App.tsx                      # Main application
    │   ├── components/                  # React components
    │   │   ├── Layout.tsx               # Dashboard layout
    │   │   ├── TasksWidget.tsx          # Tasks widget
    │   │   ├── EnergyChart.tsx          # Energy chart
    │   │   ├── HealthMetrics.tsx        # Health metrics
    │   │   └── CorrelationChart.tsx     # Correlation chart
    │   ├── api/
    │   │   └── client.ts                # API client
    │   ├── types/
    │   │   └── index.ts                 # TypeScript types
    │   └── styles/
    │       └── index.css                # Global styles
    └── package.json
```

## Prerequisites

### Required

- **Python 3.9+**: Backend server
- **Node.js 18+**: Frontend dev server and build
- **npm**: JavaScript package manager (comes with Node.js)

### MCP Servers (Optional for Full Functionality)

The dashboard connects to two MCP servers to fetch data:
- **WorkOS MCP**: Tasks, energy logs, and productivity data
- **Oura MCP**: Health and readiness metrics from Oura Ring

Without these configured, the dashboard will show error states but still function.

## Quick Start

### Option 1: Quick Start (Single Command)

```bash
# From the dashboard directory
cd dashboard
./start.sh
```

Or from the parent directory:

```bash
./dashboard/start.sh
```

This starts the backend server in the background. The server will be accessible at `http://localhost:8001`.

### Option 2: Start Everything (Recommended for Development)

```bash
cd dashboard
./start-all.sh
```

This will:
1. Open a terminal for the backend server (port 8001)
2. Open a terminal for the frontend server (port 3000)
3. Display URLs to access the dashboard

Then open `http://localhost:3000` in your browser.

### Option 3: Start Manually

#### Terminal 1: Backend

```bash
cd dashboard
./start-backend.sh
```

Backend will start on `http://localhost:8001`

#### Terminal 2: Frontend

```bash
cd dashboard
./start-frontend.sh
```

Frontend will start on `http://localhost:3000`

### Option 4: Manual Setup

#### Backend Setup

```bash
cd dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

#### Frontend Setup

```bash
cd dashboard/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

## Usage

### Accessing the Dashboard

Once both servers are running:
- **Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8001/docs
- **API Health Check**: http://localhost:8001/health

### API Endpoints

All API endpoints are under `/api`:

- `GET /api/tasks` - Get today's tasks
- `GET /api/tasks/metrics` - Get daily metrics (points, targets, streaks)
- `GET /api/energy?days=7` - Get energy logs (1-90 days)
- `GET /api/health/readiness?days=7` - Get Oura readiness data
- `GET /api/correlations?days=7` - Get energy vs productivity correlation

### Configuration

#### Backend Configuration

The backend can be configured via environment variables:

```bash
# Optional: MCP server configuration
export WORKOS_DATABASE_URL="postgresql://..."
export OURA_PERSONAL_ACCESS_TOKEN="..."

# Optional: Backend port (default: 8001)
export PORT=8001
```

#### Frontend Configuration

Create `dashboard/frontend/.env` for custom configuration:

```bash
# Backend API URL (default: http://localhost:8001)
VITE_API_BASE_URL=http://localhost:8001
```

## Development

### Backend Development

```bash
cd dashboard

# Install dev dependencies
pip install -r requirements.txt

# Run with auto-reload
python3 -m uvicorn main:app --reload

# Check syntax
python3 -m py_compile main.py config.py mcp_client.py
```

### Frontend Development

```bash
cd dashboard/frontend

# Install dependencies
npm install

# Run dev server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Building for Production

### Backend

The backend requires no build step. Deploy with:

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001
```

### Frontend

```bash
cd dashboard/frontend

# Build production bundle
npm run build

# Output will be in: frontend/dist/
```

Serve the `dist/` directory with any static file server (nginx, Apache, Caddy, etc.).

## Testing

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Install test dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=dashboard --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py           # Test fixtures and configuration
├── test_main.py          # Tests for main.py (health check, root)
├── test_tasks.py         # Tests for /api/tasks endpoints
├── test_energy.py        # Tests for /api/energy endpoint
├── test_health.py        # Tests for /api/health endpoints
├── test_correlations.py  # Tests for /api/correlations endpoint
├── test_mcp_client.py    # Tests for MCP client
└── integration/
    ├── __init__.py
    ├── test_correlations_integration.py
    └── test_mcp_communication.py
```

### Running Integration Tests

Integration tests require MCP servers to be running:

```bash
# Terminal 1: Start WorkOS MCP
cd ../../mcp-servers/workos-mcp
npm run build && npm start

# Terminal 2: Start Oura MCP
cd ../../mcp-servers/oura-mcp
npm run build && npm start

# Terminal 3: Run integration tests
cd dashboard
python -m pytest tests/integration/ -v
```

### Frontend Testing

```bash
cd dashboard/frontend

# Build verification
npm run build

# Type checking
npx tsc --noEmit

# Lint
npm run lint
```

### End-to-End Testing

See [VERIFICATION.md](./VERIFICATION.md) for comprehensive end-to-end verification steps.

## Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Problem**: Port 8001 already in use
```bash
# Solution: Change port
uvicorn main:app --port 8002
```

**Problem**: MCP connection errors
```bash
# Solution: Check MCP servers are built
ls ../mcp-servers/workos-mcp/dist/
ls ../mcp-servers/oura-mcp/dist/

# If missing, build them:
cd ../mcp-servers/workos-mcp && npm run build
cd ../mcp-servers/oura-mcp && npm run build
```

### Frontend Issues

**Problem**: `Cannot GET /`
```bash
# Solution: Start dev server
npm run dev
```

**Problem**: CORS errors in browser
```bash
# Solution: Ensure backend allows localhost:3000
# Check dashboard/main.py CORS configuration
```

**Problem**: API calls fail
```bash
# Solution: Verify backend is running
curl http://localhost:8001/health

# Check VITE_API_BASE_URL in .env
```

### Browser Issues

**Problem**: Blank page, no errors
```bash
# Solution: Check browser console (F12)
# Check that JavaScript is enabled
# Try hard refresh: Ctrl+Shift+R (Cmd+Shift+R on Mac)
```

**Problem**: Widgets show errors
```bash
# This is expected if MCP servers are not configured
# The dashboard will display error states gracefully
```

## Performance

- **Backend**: FastAPI with async/await for high performance
- **Frontend**: React with Vite for fast hot module replacement
- **Auto-Refresh**: 60-second polling interval (configurable)
- **Build Size**: ~150KB gzipped for production frontend
- **API Response**: <100ms average (with MCP servers running)

## Security

- **CORS**: Configured for `localhost:3000` in development
- **Rate Limiting**: Not implemented (recommended for production)
- **Authentication**: Not implemented (recommended for production)
- **HTTPS**: Not configured (use reverse proxy in production)

## Deployment Recommendations

### Production Checklist

- [ ] Configure CORS for production domain
- [ ] Add authentication (OAuth, JWT, etc.)
- [ ] Enable HTTPS with SSL certificates
- [ ] Add rate limiting to API endpoints
- [ ] Configure logging and monitoring
- [ ] Set up error tracking (Sentry, etc.)
- [ ] Use production-grade web server (Gunicorn, etc.)
- [ ] Serve frontend from CDN or nginx
- [ ] Set up environment variables securely
- [ ] Configure MCP servers with production credentials

### Example Nginx Configuration

```nginx
server {
    listen 80;
    server_name dashboard.example.com;

    # Frontend
    location / {
        root /var/www/dashboard/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Contributing

When adding new features:

1. **Backend**: Add endpoint in `dashboard/api/`, update types in API clients
2. **Frontend**: Create component in `src/components/`, add to `App.tsx`
3. **Styles**: Use existing CSS variables for theming
4. **Types**: Update TypeScript types in `src/types/index.ts`

## License

Part of the Thanos Operating System project.

## Support

For issues, questions, or feature requests, see the main Thanos repository.

---

**The hardest choices require the strongest wills. Get after it.**

*- Thanos Operating System*
