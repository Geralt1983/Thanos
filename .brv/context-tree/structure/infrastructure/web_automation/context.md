# Web Automation Infrastructure

This topic covers browser automation, web scraping, and API-based data extraction.

## Key Documents
- `google_automation_constraints.md` - Why Google services are hard to automate and what works
- `browser_automation_infrastructure.md` (parent) - OpenClaw browser profiles and Playwright setup

## Tools Available
- **OpenClaw Browser** (`profile=openclaw`) - Local Chrome with persistent logins
- **Scrapfly** - Cloud scraping API with anti-bot bypass
- **Browser Use** - Cloud browsers (limited for Google)
- **Playwright** - Direct browser automation scripts

## Quick Reference
| Target | Tool | Success Rate |
|--------|------|--------------|
| Google services | Local browser | 100% |
| Amazon, LinkedIn | Scrapfly | 98% |
| General web | Any | High |
