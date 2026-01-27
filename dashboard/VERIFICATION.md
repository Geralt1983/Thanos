# Thanos Dashboard - End-to-End Verification Guide

## Overview

This document provides comprehensive steps for end-to-end verification of the Thanos visualization dashboard. The dashboard consists of:
- **Backend**: FastAPI server (Python) on port 8001
- **Frontend**: React + Vite application (TypeScript) on port 3000
- **Dependencies**: WorkOS MCP server and Oura MCP server

## Pre-Verification Checklist

### 1. Code Syntax Verification ✓

All backend Python files are syntactically correct:
- `dashboard/main.py` ✓
- `dashboard/config.py` ✓
- `dashboard/mcp_client.py` ✓
- `dashboard/api/__init__.py` ✓
- `dashboard/api/tasks.py` ✓
- `dashboard/api/energy.py` ✓
- `dashboard/api/health.py` ✓
- `dashboard/api/correlations.py` ✓

### 2. Frontend Components ✓

All frontend TypeScript components are in place:
- `dashboard/frontend/src/App.tsx` ✓
- `dashboard/frontend/src/main.tsx` ✓
- `dashboard/frontend/src/components/TasksWidget.tsx` ✓
- `dashboard/frontend/src/components/EnergyChart.tsx` ✓
- `dashboard/frontend/src/components/HealthMetrics.tsx` ✓
- `dashboard/frontend/src/components/CorrelationChart.tsx` ✓
- `dashboard/frontend/src/components/Layout.tsx` ✓
- `dashboard/frontend/src/api/client.ts` ✓
- `dashboard/frontend/src/types/index.ts` ✓
- `dashboard/frontend/src/styles/index.css` ✓

## End-to-End Verification Steps

### Step 1: Build MCP Servers

Both MCP servers need to be built before the backend can communicate with them.

```bash
# Build WorkOS MCP server
cd mcp-servers/workos-mcp
npm install
npm run build
cd ../..

# Build Oura MCP server
cd mcp-servers/oura-mcp
npm install
npm run build
cd ../..
```

**Expected Result**: Both servers should have `dist/` directories with compiled JavaScript.

**Verification**:
```bash
ls -la mcp-servers/workos-mcp/dist/index.js
ls -la mcp-servers/oura-mcp/dist/index.js
```

### Step 2: Install Backend Dependencies

```bash
cd dashboard
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

**Expected Result**: All Python dependencies installed without errors.

**Verification**:
```bash
python3 -c "import fastapi, uvicorn; print('✓ Backend dependencies OK')"
```

### Step 3: Start Backend Server

```bash
cd dashboard
source venv/bin/activate  # If not already activated
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Expected Result**:
- Server starts on `http://localhost:8001`
- No import or syntax errors
- Console shows "Application startup complete"

**Verification** (in a new terminal):
```bash
# Health check
curl http://localhost:8001/health
# Expected: {"status":"healthy","service":"thanos-dashboard-api"}

# API docs
curl http://localhost:8001/docs
# Expected: OpenAPI documentation HTML

# Root endpoint
curl http://localhost:8001/
# Expected: {"name":"Thanos Dashboard API","version":"0.1.0","status":"operational","docs":"/docs"}
```

### Step 4: Test Backend API Endpoints

With the backend running, test each endpoint:

```bash
# Tasks endpoint
curl http://localhost:8001/api/tasks
# Expected: {"tasks":[],"metrics":{...}} or actual task data

# Tasks metrics
curl http://localhost:8001/api/tasks/metrics
# Expected: {"daily_points":0,"daily_target":100,...}

# Energy endpoint (7-day trend)
curl http://localhost:8001/api/energy?days=7
# Expected: {"energy_logs":[...],"summary":{...}}

# Health readiness endpoint
curl http://localhost:8001/api/health/readiness?days=7
# Expected: {"readiness_data":[...],"summary":{...}}

# Correlations endpoint
curl http://localhost:8001/api/correlations?days=7
# Expected: {"daily_data":[...],"correlation":{...}}
```

**Note**: If MCP servers are not running or not configured, endpoints will return:
```json
{
  "error": "MCP connection failed",
  "details": "..."
}
```

This is expected if MCP servers are not yet configured with proper credentials.

### Step 5: Install Frontend Dependencies

```bash
cd dashboard/frontend
npm install
```

**Expected Result**: All npm packages installed (177+ packages).

**Verification**:
```bash
ls node_modules/react node_modules/vite
# Both should exist
```

### Step 6: Start Frontend Dev Server

```bash
# From dashboard/frontend directory
npm run dev
```

**Expected Result**:
- Dev server starts on `http://localhost:3000`
- Vite displays "Local: http://localhost:3000/"
- No build errors

### Step 7: Browser Verification

Open `http://localhost:3000` in a web browser.

#### Visual Checks:

1. **Layout**:
   - [ ] Header displays "THANOS DASHBOARD" with subtitle
   - [ ] Dark cosmic theme (deep space colors)
   - [ ] Responsive grid layout (4 columns on desktop)

2. **TasksWidget**:
   - [ ] Widget renders with "Today's Focus" title
   - [ ] Shows daily points progress bar
   - [ ] Displays active and completed task counts
   - [ ] Shows streak indicator
   - [ ] Lists next 3 tasks (or shows "No active tasks")
   - [ ] Loading state displays spinner
   - [ ] If error: shows error message with retry button

3. **EnergyChart**:
   - [ ] Widget renders with "Energy Trend" title
   - [ ] Shows 7-day line chart
   - [ ] Data points are color-coded (green/yellow/red)
   - [ ] Grid lines visible
   - [ ] Legend displays (High/Medium/Low)
   - [ ] Current energy level shown at top
   - [ ] X-axis shows dates, Y-axis shows energy levels

4. **HealthMetrics**:
   - [ ] Widget renders with "Health Metrics" title
   - [ ] Displays current readiness score with color coding
   - [ ] Shows 7-day trend sparkline
   - [ ] Displays average score
   - [ ] Shows sleep balance
   - [ ] Lists top 3 contributors (Previous Night, HRV Balance, Recovery Index)

5. **CorrelationChart**:
   - [ ] Widget renders with "Productivity Correlation" title
   - [ ] Shows scatter plot (energy vs. tasks)
   - [ ] Displays correlation statistics
   - [ ] Data points visible with tooltips/labels
   - [ ] Legend shows Energy Level and Tasks Completed

#### Browser Console Checks:

1. **Open Developer Tools** (F12 or Right-click → Inspect)
2. **Console Tab**:
   - [ ] No JavaScript errors
   - [ ] No CORS errors
   - [ ] No 404 errors
   - [ ] API calls return successfully (check Network tab)

3. **Network Tab**:
   - [ ] GET `http://localhost:8001/api/tasks` - Status 200
   - [ ] GET `http://localhost:8001/api/tasks/metrics` - Status 200
   - [ ] GET `http://localhost:8001/api/energy?days=7` - Status 200
   - [ ] GET `http://localhost:8001/api/health/readiness?days=7` - Status 200
   - [ ] GET `http://localhost:8001/api/correlations?days=7` - Status 200

**Note**: If MCP servers are not configured with credentials, API endpoints will return errors. This is expected. The widgets should display error states gracefully with retry buttons.

### Step 8: Responsive Design Testing

Test the dashboard at different viewport widths:

1. **Desktop (1920px)**:
   - [ ] 4-column grid layout
   - [ ] All widgets display side-by-side

2. **Laptop (1366px)**:
   - [ ] 3-4 column grid layout
   - [ ] Widgets reflow naturally

3. **Tablet (768px)**:
   - [ ] 2-column grid layout
   - [ ] Header layout stacks vertically
   - [ ] Card padding reduces
   - [ ] Font sizes adjust

4. **Mobile (375px)**:
   - [ ] 1-column grid layout
   - [ ] All widgets stack vertically
   - [ ] Touch-friendly sizing
   - [ ] No horizontal scrolling

**How to Test**:
- Use browser DevTools (F12) → Toggle Device Toolbar
- Set viewport to 768px width
- Check layout reflows correctly
- No overlapping elements
- All text readable

### Step 9: Auto-Refresh Testing

Widgets auto-refresh every 60 seconds. To verify:

1. Open browser console
2. Watch Network tab
3. Wait 60 seconds
4. [ ] API calls repeat automatically
5. [ ] UI updates with new data
6. [ ] No memory leaks (check Performance tab)

### Step 10: Error Handling Testing

Test error scenarios:

1. **Backend Down**:
   - Stop the backend server
   - Refresh frontend
   - [ ] All widgets show error states
   - [ ] Error messages are user-friendly
   - [ ] Retry buttons appear

2. **API Timeout**:
   - Simulate slow network (DevTools → Network → Throttling)
   - [ ] Loading states display
   - [ ] Timeout errors handled gracefully

3. **Invalid Data**:
   - [ ] Empty data arrays don't crash UI
   - [ ] Missing fields have defaults
   - [ ] Chart components handle edge cases

## Verification Completion Checklist

- [ ] Backend builds and starts successfully
- [ ] Frontend builds and starts successfully
- [ ] All API endpoints return expected responses
- [ ] All widgets render correctly
- [ ] No console errors in browser
- [ ] CORS configured correctly
- [ ] Responsive design works at 768px
- [ ] Auto-refresh works
- [ ] Error handling works
- [ ] Performance is acceptable (no lag)

## Known Limitations

1. **MCP Server Configuration**: The dashboard requires properly configured MCP servers with valid database URLs and API tokens. Without these, the dashboard will show error states.

2. **Environment**: This verification was performed without Node.js available, so MCP servers could not be built and the full end-to-end flow could not be tested in a browser. Manual verification by the user is required.

3. **Data Requirements**: The dashboard displays real data from WorkOS and Oura. If no data exists in the databases, widgets will show empty states.

## Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`
**Solution**: Install dependencies: `pip install -r requirements.txt`

**Problem**: `Connection refused` when accessing MCP servers
**Solution**: Ensure MCP servers are built and environment variables are set (WORKOS_DATABASE_URL, OURA_PERSONAL_ACCESS_TOKEN)

### Frontend Issues

**Problem**: `Cannot GET /`
**Solution**: Ensure frontend dev server is running: `npm run dev`

**Problem**: CORS errors in browser console
**Solution**: Check that backend CORS middleware allows `http://localhost:3000`

**Problem**: Blank page with no errors
**Solution**: Check that `VITE_API_BASE_URL` is set correctly (defaults to `http://localhost:8001`)

### MCP Server Issues

**Problem**: MCP servers not built
**Solution**: Run `npm run build` in each MCP server directory

**Problem**: MCP tools not found
**Solution**: Check that MCP server `dist/index.js` files exist

## Next Steps

After successful verification:
1. Create production build: `npm run build` in frontend directory
2. Deploy backend and frontend to hosting service
3. Configure environment variables for production
4. Set up monitoring and logging
5. Add authentication if needed

## Verification Status

**Date**: 2026-01-26
**Status**: ✓ Code verification complete, manual browser testing required
**Verified By**: auto-claude
**Environment**: Limited (no Node.js available)
**Next Action**: User should run Steps 1-10 with Node.js available
