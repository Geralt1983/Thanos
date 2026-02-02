#!/usr/bin/env python3
"""
Morning Brief Generator
Consolidates data from multiple sources into a unified daily brief.
"""

import os
import sys
import json
import subprocess
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests

# Add parent Tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

CONFIG_PATH = Path(__file__).parent / "config" / "sources.yaml"
CACHE_DIR = Path(__file__).parent / "cache"


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


THANOS_ROOT = Path(__file__).parent.parent.parent
MONARCH_CLI = THANOS_ROOT / "skills" / "monarch-money" / "dist" / "cli" / "index.js"


def load_env():
    """Load environment variables from .env file."""
    env_file = THANOS_ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = value


def run_command(cmd: List[str], timeout: int = 30, cwd: Optional[Path] = None) -> tuple[bool, str]:
    """Run a shell command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


class MorningBrief:
    def __init__(self):
        load_env()  # Load .env file
        self.config = load_config()
        self.data = {}
        self.errors = []
        CACHE_DIR.mkdir(exist_ok=True)
    
    def fetch_energy(self) -> Dict[str, Any]:
        """Fetch energy/readiness data from Oura."""
        cfg = self.config["sources"]["energy"]
        if not cfg["enabled"]:
            return {"status": "disabled"}
        
        # Try both possible env var names
        token = os.environ.get("OURA_PERSONAL_ACCESS_TOKEN") or os.environ.get("OURA_ACCESS_TOKEN")
        if not token:
            self.errors.append("OURA_ACCESS_TOKEN not set")
            return {"status": "error", "message": "No API token"}
        
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            # Fetch readiness
            resp = requests.get(
                cfg["endpoints"]["readiness"],
                headers=headers,
                params={"start_date": yesterday, "end_date": today},
                timeout=10
            )
            resp.raise_for_status()
            readiness_data = resp.json()
            
            # Fetch sleep
            resp = requests.get(
                cfg["endpoints"]["sleep"],
                headers=headers,
                params={"start_date": yesterday, "end_date": today},
                timeout=10
            )
            resp.raise_for_status()
            sleep_data = resp.json()
            
            # Extract latest scores
            readiness_score = None
            sleep_score = None
            
            if readiness_data.get("data"):
                latest = readiness_data["data"][-1]
                readiness_score = latest.get("score")
            
            if sleep_data.get("data"):
                latest = sleep_data["data"][-1]
                sleep_score = latest.get("score")
            
            return {
                "status": "ok",
                "readiness_score": readiness_score,
                "sleep_score": sleep_score,
                "energy_level": self._classify_energy(readiness_score)
            }
        except requests.RequestException as e:
            self.errors.append(f"Oura API error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _classify_energy(self, score: Optional[int]) -> str:
        """Classify energy level from readiness score."""
        if score is None:
            return "unknown"
        if score >= 85:
            return "HIGH"
        if score >= 70:
            return "MODERATE"
        if score >= 55:
            return "LOW"
        return "VERY LOW"
    
    def fetch_calendar(self) -> Dict[str, Any]:
        """Fetch calendar events using gog CLI."""
        cfg = self.config["sources"]["calendar"]
        if not cfg["enabled"]:
            return {"status": "disabled"}
        
        events = []
        
        # Use gog calendar events --json
        success, output = run_command([
            "gog", "calendar", "events",
            "--json",
            "--account", cfg.get("account", "jkimble1983@gmail.com")
        ], timeout=45)
        
        if success and output:
            try:
                data = json.loads(output)
                raw_events = data.get("events", [])
                
                # Filter to today and tomorrow, parse and format
                now = datetime.now()
                today = now.date()
                tomorrow = today + timedelta(days=1)
                
                for evt in raw_events:
                    start = evt.get("start", {})
                    start_dt = start.get("dateTime") or start.get("date")
                    
                    if start_dt:
                        try:
                            if "T" in start_dt:
                                evt_date = datetime.fromisoformat(start_dt.replace("Z", "+00:00")).date()
                                evt_time = datetime.fromisoformat(start_dt.replace("Z", "+00:00")).strftime("%I:%M %p")
                            else:
                                evt_date = datetime.strptime(start_dt, "%Y-%m-%d").date()
                                evt_time = "All day"
                            
                            if evt_date in (today, tomorrow):
                                events.append({
                                    "summary": evt.get("summary", "No title"),
                                    "start": evt_time,
                                    "date": str(evt_date),
                                    "is_tomorrow": evt_date == tomorrow
                                })
                        except (ValueError, TypeError):
                            continue
            except json.JSONDecodeError:
                events = self._parse_calendar_text(output)
        
        if not success and not events:
            self.errors.append(f"Calendar fetch failed: {output}")
            return {"status": "error", "message": output}
        
        return {
            "status": "ok",
            "events": events[:10],
            "count": len(events)
        }
    
    def _parse_calendar_text(self, text: str) -> List[Dict]:
        """Parse calendar text output into structured events."""
        events = []
        for line in text.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                events.append({"summary": line, "raw": True})
        return events
    
    def fetch_budget(self) -> Dict[str, Any]:
        """Fetch budget status from Monarch Money."""
        cfg = self.config["sources"]["budget"]
        if not cfg["enabled"]:
            return {"status": "disabled"}
        
        monarch_dir = THANOS_ROOT / "skills" / "monarch-money"
        
        # Use local monarch CLI
        success, output = run_command(
            ["node", str(MONARCH_CLI), "acc", "list"],
            cwd=monarch_dir,
            timeout=45
        )
        
        if not success:
            self.errors.append(f"Monarch fetch failed: {output}")
            return {"status": "error", "message": output}
        
        # Parse the table output
        accounts = []
        lines = output.split("\n")
        in_table = False
        
        for line in lines:
            if "│" in line and "ID" not in line and "───" not in line:
                parts = [p.strip() for p in line.split("│") if p.strip()]
                if len(parts) >= 4:
                    try:
                        accounts.append({
                            "id": parts[0],
                            "name": parts[1],
                            "type": parts[2],
                            "balance": parts[3]
                        })
                    except IndexError:
                        continue
        
        # Calculate totals
        total_cash = 0
        total_debt = 0
        
        for acc in accounts:
            bal_str = acc["balance"].replace("$", "").replace(",", "")
            try:
                bal = float(bal_str)
                if bal < 0:
                    total_debt += bal
                else:
                    total_cash += bal
            except ValueError:
                continue
        
        return {
            "status": "ok",
            "accounts": accounts,
            "total_cash": total_cash,
            "total_debt": total_debt,
            "net_worth": total_cash + total_debt
        }
    
    def fetch_tasks(self) -> Dict[str, Any]:
        """Fetch tasks from Todoist."""
        cfg = self.config["sources"]["tasks"]
        if not cfg["enabled"]:
            return {"status": "disabled"}
        
        # Use todoist CLI
        success, output = run_command(["todoist", "today", "--format", "json"])
        
        if not success:
            # Try without format flag
            success, output = run_command(["todoist", "today"])
        
        if not success:
            self.errors.append(f"Todoist fetch failed: {output}")
            return {"status": "error", "message": output}
        
        try:
            tasks = json.loads(output)
            return {
                "status": "ok",
                "tasks": tasks[:cfg["max_display"]]
            }
        except json.JSONDecodeError:
            # Parse text output
            tasks = [{"content": line.strip()} for line in output.split("\n") if line.strip()]
            return {
                "status": "ok",
                "tasks": tasks[:cfg["max_display"]]
            }
    
    def fetch_weather(self) -> Dict[str, Any]:
        """Fetch weather from wttr.in using curl."""
        cfg = self.config["sources"]["weather"]
        if not cfg["enabled"]:
            return {"status": "disabled"}
        
        location = cfg["location"].replace(" ", "+")
        
        # Use curl for more reliable connection
        success, output = run_command([
            "curl", "-s", f"https://wttr.in/{location}?format=j1"
        ], timeout=15)
        
        if not success:
            self.errors.append(f"Weather fetch failed: {output}")
            return {"status": "error", "message": output}
        
        try:
            data = json.loads(output)
            
            current = data.get("current_condition", [{}])[0]
            forecast = data.get("weather", [{}])[0]
            
            return {
                "status": "ok",
                "current": {
                    "temp_f": current.get("temp_F"),
                    "feels_like_f": current.get("FeelsLikeF"),
                    "condition": current.get("weatherDesc", [{}])[0].get("value"),
                    "humidity": current.get("humidity"),
                },
                "forecast": {
                    "high_f": forecast.get("maxtempF"),
                    "low_f": forecast.get("mintempF"),
                    "rain_chance": forecast.get("hourly", [{}])[0].get("chanceofrain"),
                }
            }
        except json.JSONDecodeError as e:
            self.errors.append(f"Weather parse failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def generate(self) -> str:
        """Generate the complete morning brief."""
        # Fetch all data
        self.data["energy"] = self.fetch_energy()
        self.data["calendar"] = self.fetch_calendar()
        self.data["budget"] = self.fetch_budget()
        self.data["tasks"] = self.fetch_tasks()
        self.data["weather"] = self.fetch_weather()
        
        # Build output
        now = datetime.now()
        output = []
        
        # Header
        output.append(f"🌅 **MORNING BRIEF** — {now.strftime('%A, %B %d, %Y')}")
        output.append("")
        
        # Energy Section
        output.append("🔋 **ENERGY**")
        energy = self.data["energy"]
        if energy["status"] == "ok":
            level = energy.get("energy_level", "unknown")
            readiness = energy.get("readiness_score")
            sleep = energy.get("sleep_score")
            emoji = {"HIGH": "🟢", "MODERATE": "🟡", "LOW": "🟠", "VERY LOW": "🔴"}.get(level, "⚪")
            output.append(f"{emoji} Energy: **{level}**")
            if readiness:
                output.append(f"  • Readiness: {readiness}")
            if sleep:
                output.append(f"  • Sleep: {sleep}")
        else:
            output.append(f"⚠️ {energy.get('message', 'Unable to fetch energy data')}")
        output.append("")
        
        # Calendar Section
        output.append("📅 **CALENDAR**")
        calendar = self.data["calendar"]
        if calendar["status"] == "ok":
            events = calendar.get("events", [])
            if events:
                today_events = [e for e in events if not e.get("is_tomorrow")]
                tomorrow_events = [e for e in events if e.get("is_tomorrow")]
                
                if today_events:
                    output.append("  **Today:**")
                    for event in today_events[:5]:
                        summary = event.get("summary", "No title")
                        start = event.get("start", "")
                        output.append(f"    • {start}: {summary}")
                
                if tomorrow_events:
                    output.append("  **Tomorrow:**")
                    for event in tomorrow_events[:3]:
                        summary = event.get("summary", "No title")
                        start = event.get("start", "")
                        output.append(f"    • {start}: {summary}")
                
                if not today_events and not tomorrow_events:
                    output.append("  No events in next 48h")
            else:
                output.append("  No events scheduled")
        else:
            output.append(f"⚠️ {calendar.get('message', 'Unable to fetch calendar')}")
        output.append("")
        
        # Budget Section
        output.append("💰 **FINANCES**")
        budget = self.data["budget"]
        if budget["status"] == "ok":
            total_cash = budget.get("total_cash", 0)
            total_debt = budget.get("total_debt", 0)
            net_worth = budget.get("net_worth", 0)
            
            output.append(f"  💵 Cash: ${total_cash:,.2f}")
            output.append(f"  📉 Debt: ${total_debt:,.2f}")
            output.append(f"  📊 Net: ${net_worth:,.2f}")
            
            # Show cash accounts
            accounts = budget.get("accounts", [])
            cash_accounts = [a for a in accounts if a.get("type") == "Cash"]
            if cash_accounts:
                output.append("  **Cash Accounts:**")
                for acc in cash_accounts[:4]:
                    output.append(f"    • {acc['name']}: {acc['balance']}")
        else:
            output.append(f"⚠️ {budget.get('message', 'Unable to fetch budget')}")
        output.append("")
        
        # Tasks Section
        output.append("✅ **TASKS**")
        tasks = self.data["tasks"]
        if tasks["status"] == "ok":
            task_list = tasks.get("tasks", [])
            if task_list:
                for t in task_list[:5]:
                    content = t.get("content", str(t))
                    output.append(f"  • {content}")
            else:
                output.append("  No tasks due today")
        else:
            output.append(f"⚠️ {tasks.get('message', 'Unable to fetch tasks')}")
        output.append("")
        
        # Weather Section
        output.append("🌤️ **WEATHER**")
        weather = self.data["weather"]
        if weather["status"] == "ok":
            current = weather.get("current", {})
            forecast = weather.get("forecast", {})
            temp = current.get("temp_f", "?")
            feels = current.get("feels_like_f", "?")
            condition = current.get("condition", "Unknown")
            high = forecast.get("high_f", "?")
            low = forecast.get("low_f", "?")
            rain = forecast.get("rain_chance", "?")
            
            output.append(f"  Currently: {temp}°F (feels like {feels}°F) — {condition}")
            output.append(f"  Today: High {high}°F / Low {low}°F")
            if rain and int(rain) > 20:
                output.append(f"  🌧️ Rain chance: {rain}%")
        else:
            output.append(f"⚠️ {weather.get('message', 'Unable to fetch weather')}")
        
        # Errors summary
        if self.errors:
            output.append("")
            output.append("⚠️ **Issues:**")
            for err in self.errors:
                output.append(f"  • {err}")
        
        return "\n".join(output)


def main():
    """Main entry point."""
    brief = MorningBrief()
    print(brief.generate())
    
    # Also save to cache for debugging
    cache_file = CACHE_DIR / f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(cache_file, "w") as f:
        json.dump({
            "data": brief.data,
            "errors": brief.errors,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)


if __name__ == "__main__":
    main()
