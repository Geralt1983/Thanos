# Browser Automation Guide

## Overview

Thanos has multiple ways to access the web:

1. **OpenClaw Managed Browser** (primary) — isolated Chrome profile I control directly
2. **Browser Use Cloud** — cloud browsers for autonomous tasks
3. **Chrome Extension Relay** — control your existing Chrome tabs

---

## 1. OpenClaw Managed Browser (Recommended)

### Start
```bash
browser action=start profile=openclaw
```

### Open a URL
```bash
browser action=open profile=openclaw targetUrl="https://example.com"
```

### Take Snapshot (see page structure)
```bash
browser action=snapshot profile=openclaw targetId=<targetId>
```

### Take Screenshot
```bash
browser action=screenshot profile=openclaw targetId=<targetId>
```

### Click Element
```bash
browser action=act profile=openclaw targetId=<targetId> request='{"kind": "click", "ref": "e123"}'
```

### Type Text
```bash
browser action=act profile=openclaw targetId=<targetId> request='{"kind": "type", "ref": "e123", "text": "hello"}'
```

### Run JavaScript
```bash
browser action=act profile=openclaw targetId=<targetId> request='{"kind": "evaluate", "fn": "document.title"}'
```

### Stop Browser
```bash
browser action=stop profile=openclaw
```

### Key Details
- **Profile:** `openclaw`
- **CDP Port:** 18800
- **User Data:** `~/.openclaw/browser/openclaw/user-data`
- **Color:** Orange (#FF4500) — easy to identify
- **Persists logins** across sessions

### Currently Logged In
- **Kimi.com** — Jeremy Kimble (Moderato plan)

---

## 2. Browser Use Cloud (Autonomous Tasks)

For tasks that run while user is away, or need cloud infrastructure.

### Config
- **API Key:** `BROWSER_USE_API_KEY` in `.env`
- **Profile ID:** `BROWSER_USE_PROFILE_ID` in `.env`
- **Profile Name:** `Thanos-Main`

### Run Autonomous Task
```bash
curl -X POST "https://api.browser-use.com/api/v2/tasks" \
  -H "X-Browser-Use-API-Key: $BROWSER_USE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Your task description",
    "llm": "browser-use-llm",
    "profileId": "<profile-id>",
    "startUrl": "https://example.com"
  }'
```

### Check Task Status
```bash
curl "https://api.browser-use.com/api/v2/tasks/<task-id>" \
  -H "X-Browser-Use-API-Key: $BROWSER_USE_API_KEY"
```

### Start Live Session (for manual login)
```bash
curl -X POST "https://api.browser-use.com/api/v2/browsers" \
  -H "X-Browser-Use-API-Key: $BROWSER_USE_API_KEY" \
  -d '{"profileId": "<profile-id>", "timeout": 30}'
```

### Pricing
- $0.03-0.06/hour
- Billed per minute, refunded for unused time

---

## 3. Chrome Extension Relay

For controlling user's existing Chrome tabs (requires manual tab attachment).

### Setup
1. Install extension: `openclaw browser extension install`
2. Load unpacked in `chrome://extensions`
3. Click extension icon on tab to attach (badge shows ON)

### Use
```bash
browser action=tabs profile=chrome
browser action=snapshot profile=chrome
```

---

## When to Use Each

| Method | Best For |
|--------|----------|
| **OpenClaw Browser** | Most tasks, persisted logins, autonomous work |
| **Browser Use** | Long-running tasks, parallel sessions, cloud infrastructure |
| **Chrome Extension** | Quick tasks on existing tabs, debugging |

---

## Troubleshooting

### Element refs not found
- Take a fresh snapshot before clicking
- Use JavaScript evaluate as fallback:
  ```
  {"kind": "evaluate", "fn": "document.querySelector('button').click()"}
  ```

### Sidebar collapsed
- Resize window wider: `{"kind": "resize", "width": 1400, "height": 900}`

### Login required
- OpenClaw browser persists sessions in user-data dir
- For new sites: log in once manually, session persists
