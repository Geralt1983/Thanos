# Thanos Integration Specs: Ashley's Suburban Fuel Monitor

## Project Overview
Build a fuel monitoring daemon that tracks Ashley's 2024 Chevy Suburban fuel level via Smartcar API and sends low-fuel alerts through Thanos notification system.

---

## System Requirements

### Dependencies
```bash
pip install smartcar --break-system-packages
pip install requests --break-system-packages
```

### External Services
- Smartcar API (free tier: 500 calls/month)
- GM OnStar (included free for 3 years with 2024 Suburban)
- Active internet connection

### Credentials Needed
- Smartcar Client ID (from dashboard.smartcar.com)
- Smartcar Client Secret
- Smartcar access/refresh tokens (obtained via OAuth with Ashley's myChevrolet login)

---

## File Structure
```
~/Projects/Thanos/
├── Tools/
│   └── fuel_monitor/
│       ├── fuel_monitor.py      # Main daemon process
│       ├── smartcar_client.py   # Smartcar API wrapper
│       └── smartcar_oauth.py    # One-time OAuth setup script
├── config/
│   └── fuel_monitor.json        # Configuration file
└── docs/
    └── fuel-monitor-specs.md    # This file
```

---

## Configuration Schema

File: `config/fuel_monitor.json`
```json
{
  "smartcar": {
    "client_id": "SMARTCAR_CLIENT_ID",
    "client_secret": "SMARTCAR_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8000/callback",
    "mode": "live"
  },
  "monitoring": {
    "check_interval_seconds": 21600,
    "fuel_threshold_percent": 25,
    "alert_cooldown_hours": 6
  },
  "vehicle": {
    "name": "Ashley's Suburban",
    "owner": "Ashley"
  },
  "thanos_integration": {
    "notify_via": "telegram",
    "log_file": "logs/fuel_monitor.log"
  }
}
```

---

## API Specifications

### Smartcar Endpoints

#### 1. Get Fuel Level
```
GET https://api.smartcar.com/v2.0/vehicles/{vehicle_id}/fuel
Authorization: Bearer {access_token}

Response:
{
  "percentRemaining": 0.3,
  "range": 40.5,
  "amountRemaining": 53.2
}
```

#### 2. Get Location (optional)
```
GET https://api.smartcar.com/v2.0/vehicles/{vehicle_id}/location
Authorization: Bearer {access_token}

Response:
{
  "latitude": 36.1699,
  "longitude": -80.2584
}
```

#### 3. Refresh Access Token
```
POST https://auth.smartcar.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token={refresh_token}
&client_id={client_id}
&client_secret={client_secret}

Response:
{
  "access_token": "new_token",
  "refresh_token": "new_refresh_token",
  "expires_in": 7200
}
```

---

## Core Functionality Requirements

### 1. OAuth Setup Script (smartcar_oauth.py)

**Purpose:** One-time script to obtain initial OAuth tokens

**Requirements:**
- Start local HTTP server on port 8000
- Generate Smartcar auth URL with scopes: `read_fuel`, `read_location`, `read_vehicle_info`
- Open browser to auth URL
- Capture OAuth callback with authorization code
- Exchange code for access/refresh tokens
- Save tokens securely
- Print vehicle ID and basic info to confirm connection

**Output:**
```json
{
  "vehicle_id": "abc123...",
  "access_token": "token...",
  "refresh_token": "refresh...",
  "expires_at": 1738450800,
  "vehicle_info": {
    "make": "CHEVROLET",
    "model": "Suburban",
    "year": 2024
  }
}
```

---

### 2. Smartcar Client Library (smartcar_client.py)

```python
class SmartcarClient:
    def __init__(self, config_path: str):
        """Load config and tokens"""
    
    def get_fuel_level(self) -> dict:
        """Returns fuel percentage, range, and amount remaining"""
    
    def get_location(self) -> dict:
        """Returns lat/long coordinates"""
    
    def refresh_tokens(self) -> None:
        """Refresh OAuth tokens before expiry"""
    
    def is_token_expired(self) -> bool:
        """Check if access token needs refresh"""
```

---

### 3. Fuel Monitor Daemon (fuel_monitor.py)

**Behavior:**
- Check fuel level every 6 hours (configurable)
- Alert via Telegram if fuel < 25%
- Respect cooldown (don't spam alerts)
- Auto-refresh tokens before expiry
- Log all checks to file

**Cron Integration:**
```bash
# Add to OpenClaw cron
fuel-level-check: every 6 hours
  - Call fuel_monitor.py
  - If low, send Telegram notification
  - Log result
```

---

## Setup Steps

1. Create Smartcar account at dashboard.smartcar.com
2. Create application, get client ID/secret
3. Run OAuth script with Ashley's myChevrolet credentials
4. Configure thresholds in config file
5. Set up cron job for periodic checks
6. Test with manual trigger

---

## SmartcarClient Methods

```python
def get_fuel_data(self) -> dict:
    """
    Get current fuel level
    Returns: {
        'percent': float,
        'range_miles': float,
        'timestamp': str (ISO 8601)
    }
    Handles token refresh automatically
    """

def get_location(self) -> dict:
    """
    Get current GPS location
    Returns: {
        'latitude': float,
        'longitude': float,
        'timestamp': str
    }
    """

def refresh_token_if_needed(self) -> bool:
    """
    Check if access token expired and refresh if needed
    Returns: True if refreshed, False if still valid
    """

def _save_tokens(self, tokens: dict):
    """Save tokens to secure storage"""
```

### Error Handling
- Network errors → Retry up to 3 times with exponential backoff
- Token expired → Auto-refresh and retry request
- API rate limit → Log error, wait until next interval
- Vehicle offline → Return last known data with staleness indicator

---

## Fuel Monitor Daemon (fuel_monitor.py)

### Main Loop Logic
```python
while True:
    # 1. Load config
    # 2. Get fuel data via SmartcarClient
    # 3. Check if below threshold
    # 4. If low AND cooldown expired:
    #    - Create alert notification
    #    - Send via Telegram
    #    - Update last_alert_time
    # 5. Log data point (for historical tracking)
    # 6. Sleep for check_interval_seconds
```

### Alert Notification Schema
```json
{
  "id": "fuel_alert_20260201_143022",
  "timestamp": "2026-02-01T14:30:22Z",
  "type": "fuel_low",
  "priority": "medium",
  "vehicle": "Ashley's Suburban",
  "data": {
    "fuel_percent": 23.5,
    "range_miles": 38.2,
    "location": {
      "latitude": 36.1699,
      "longitude": -80.2584
    }
  },
  "message": "Ashley's Suburban at 23.5% fuel (38 miles range)",
  "action_suggested": "Consider filling up soon"
}
```

### Logging Requirements
- Log every fuel check (timestamp, fuel %, range)
- Log alerts sent
- Log errors/retries
- Log token refreshes
- Rotate logs daily, keep 30 days

---

## Integration with Thanos

### Notification Delivery
Instead of file-based queue, use OpenClaw's native messaging:

```python
# Direct Telegram notification via OpenClaw
def send_fuel_alert(message: str):
    """Send alert through Thanos notification system"""
    # Option 1: Write to cron event
    # Option 2: HTTP to gateway API
    # Option 3: Use message tool directly
```

### Health Monitoring
Create heartbeat file: `~/Projects/Thanos/logs/fuel_monitor_heartbeat.json`

```json
{
  "daemon": "fuel_monitor",
  "last_check": "2026-02-01T14:30:22Z",
  "status": "healthy",
  "last_fuel_reading": {
    "percent": 45.2,
    "timestamp": "2026-02-01T14:30:22Z"
  },
  "api_calls_this_month": 87,
  "errors_last_24h": 0
}
```

Update this file after every check so heartbeat can monitor daemon health.

---

## Deployment Options

### Option 1: OpenClaw Cron (Recommended)
```yaml
# Add to OpenClaw cron jobs
fuel-level-check:
  schedule: every 6 hours
  payload:
    kind: agentTurn
    message: "Check Ashley's Suburban fuel level via Smartcar API"
  sessionTarget: isolated
```

### Option 2: Systemd Service
```ini
[Unit]
Description=Thanos Fuel Monitor - Ashley's Suburban
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=jeremy
WorkingDirectory=/Users/jeremy/Projects/Thanos
ExecStart=/Users/jeremy/Projects/Thanos/.venv/bin/python Tools/fuel_monitor/fuel_monitor.py
Restart=always
RestartSec=300
StandardOutput=append:/Users/jeremy/Projects/Thanos/logs/fuel_monitor.log
StandardError=append:/Users/jeremy/Projects/Thanos/logs/fuel_monitor_error.log

[Install]
WantedBy=multi-user.target
```

### Option 3: launchd (macOS)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.thanos.fuel-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/jeremy/Projects/Thanos/.venv/bin/python</string>
        <string>/Users/jeremy/Projects/Thanos/Tools/fuel_monitor/fuel_monitor.py</string>
    </array>
    <key>StartInterval</key>
    <integer>21600</integer>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

---

## Testing Requirements

### Unit Tests
1. Token refresh logic (mock expired token)
2. Fuel data parsing
3. Alert threshold detection
4. Notification delivery
5. Error handling (network failures, API errors)
6. Cooldown logic (don't spam alerts)

### Integration Test
```python
# Manual test with high threshold to trigger alert
python -c "
from Tools.fuel_monitor.fuel_monitor import check_fuel
check_fuel(threshold=100)  # Force alert
"
```

---

## Security Considerations

### Token Storage
- Store tokens in `~/.thanos/tokens/`
- File permissions: `chmod 600` (owner read/write only)
- Never log tokens
- Never commit tokens to git

### API Key Management
Store Smartcar credentials via environment variables:
```bash
export SMARTCAR_CLIENT_ID="..."
export SMARTCAR_CLIENT_SECRET="..."
```
Or add to `.env` (already gitignored).

---

## Operational Specs

### Performance
- Check interval: 6 hours (4 checks/day = 120 checks/month, well under 500 limit)
- API call timeout: 10 seconds
- Retry on failure: 3 attempts with 5s, 15s, 30s backoff

### Resource Usage
- Memory: ~50MB (Python + smartcar library)
- CPU: Negligible (sleeps 99.9% of time)
- Network: ~2KB per check (4 API calls/day)
- Disk: ~1MB logs/month

### Alert Logic
```python
if fuel_percent < threshold AND (
    last_alert_time is None OR
    hours_since_last_alert > cooldown_hours
):
    send_alert()
```
This prevents alert spam if she doesn't fill up immediately.

---

## Deployment Checklist

### Phase 1: Setup (one-time, requires Ashley)
- [ ] Create Smartcar developer account
- [ ] Get client ID and secret
- [ ] Run OAuth script with Ashley present
- [ ] Verify tokens saved and vehicle connected
- [ ] Test fuel data retrieval

### Phase 2: Installation
- [ ] Install dependencies
- [ ] Create file structure
- [ ] Deploy scripts and config
- [ ] Set file permissions
- [ ] Create launchd/cron job
- [ ] Enable and start service

### Phase 3: Validation
- [ ] Check logs for successful fuel checks
- [ ] Verify heartbeat file updating
- [ ] Manually trigger alert (set threshold high)
- [ ] Confirm alert delivered via Telegram
- [ ] Monitor for 24 hours

### Phase 4: Integration
- [ ] Connect to OpenClaw cron for scheduling
- [ ] Test end-to-end alert delivery
- [ ] Set up monitoring for daemon health
- [ ] Document for future maintenance

---

## Monitoring & Maintenance

### Daily
- Thanos checks heartbeat file (should update every 6h)
- Alert if heartbeat stale >12 hours

### Weekly
- Review error logs
- Check API call usage (stay under 500/month)

### Monthly
- Verify tokens still valid
- Review alert frequency (tune threshold if needed)

### Every 60 days
- Refresh tokens expire - re-run OAuth if needed
- Or implement proactive refresh before expiry

---

## Error Recovery Procedures

| Error | Detection | Recovery |
|-------|-----------|----------|
| Token expired | 401 from API | Auto-refresh using refresh_token |
| Refresh token expired | 400 on refresh | Notify Jeremy to re-run OAuth with Ashley |
| Network failure | Timeout/connection error | Retry 3x, log, continue |
| Vehicle offline | Stale data indicator | Use cached data, alert if >24h stale |
| API rate limit | 429 response | Log warning, skip check, wait for next interval |
| Daemon crash | launchd detects | Auto-restart via launchd |

---

## Future Enhancements (optional)

1. **Predictive alerts:** Based on historical usage, predict when tank will be empty
2. **Location-aware alerts:** "Fuel low + near home = good time to fill up"
3. **Gas price integration:** "Fuel low + cheap gas nearby"
4. **Multi-vehicle support:** Add Jeremy's vehicle
5. **Historical tracking:** Graph fuel usage over time
6. **Webhook integration:** Real-time updates instead of polling

---

## Implementation Priority

### Must-have (MVP)
1. OAuth setup script
2. Smartcar client library with token refresh
3. Basic daemon with alert logic
4. Telegram notification integration
5. launchd/cron scheduling

### Nice-to-have
- Location data
- Historical logging
- Health monitoring
- Comprehensive error handling

### Can wait
- Unit tests
- Predictive alerts
- Multi-vehicle

---

## Success Criteria

- [ ] Daemon runs continuously without intervention
- [ ] Fuel level checked every 6 hours
- [ ] Alert sent when fuel <25%
- [ ] Alert delivered to Jeremy via Telegram
- [ ] No more than 200 API calls/month (stay well under limit)
- [ ] Token auto-refresh works
- [ ] Survives system reboot
- [ ] Ashley never has to do anything after initial OAuth

---

## Notes

- Smartcar free tier: 500 API calls/month
- 4 checks/day = 120 calls/month (well under limit)
- GM OnStar included free with 2024 vehicles for 3 years
- Consider adding tire pressure monitoring later
