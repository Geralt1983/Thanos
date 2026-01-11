"""
Oura Ring API adapter for Thanos.

Provides direct access to Oura Ring health data via the v2 REST API,
bypassing the MCP server for better control and async support.
"""

from datetime import datetime, timedelta
import os
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx

from .base import BaseAdapter, ToolResult


class OuraAdapter(BaseAdapter):
    """Direct adapter for Oura Ring API."""

    BASE_URL = "https://api.ouraring.com/v2"

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize the Oura adapter.

        Args:
            access_token: Oura personal access token. Falls back to
                         OURA_PERSONAL_ACCESS_TOKEN env var.
        """
        self.access_token = access_token or os.environ.get('OURA_PERSONAL_ACCESS_TOKEN')
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "oura"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            if not self.access_token:
                raise ValueError(
                    "No Oura access token configured. Set OURA_PERSONAL_ACCESS_TOKEN."
                )
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30.0
            )
        return self._client

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return list of available Oura tools."""
        return [
            {
                "name": "get_daily_readiness",
                "description": "Get daily readiness scores (recovery, contributors)",
                "parameters": {
                    "start_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Start date (YYYY-MM-DD). Defaults to today."
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date",
                        "description": "End date (YYYY-MM-DD). Defaults to today."
                    }
                }
            },
            {
                "name": "get_daily_sleep",
                "description": "Get daily sleep scores and summary",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_sleep",
                "description": "Get detailed sleep sessions with phases and HRV",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_daily_activity",
                "description": "Get daily activity data (steps, calories, movement)",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_daily_stress",
                "description": "Get daily stress data and recovery time",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_workout",
                "description": "Get workout sessions",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_heart_rate",
                "description": "Get heart rate data (5-minute intervals)",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_personal_info",
                "description": "Get user profile information",
                "parameters": {}
            },
            {
                "name": "get_daily_summary",
                "description": "Get combined readiness, sleep, and activity for a date range",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_today_health",
                "description": "Get today's complete health snapshot",
                "parameters": {}
            }
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute an Oura tool."""
        try:
            client = await self._get_client()

            # Default date handling
            today = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
            start_date = arguments.get('start_date', today)
            end_date = arguments.get('end_date', today)

            # Simple endpoint mappings
            endpoint_map = {
                "get_daily_readiness": "/usercollection/daily_readiness",
                "get_daily_sleep": "/usercollection/daily_sleep",
                "get_sleep": "/usercollection/sleep",
                "get_daily_activity": "/usercollection/daily_activity",
                "get_daily_stress": "/usercollection/daily_stress",
                "get_workout": "/usercollection/workout",
                "get_heart_rate": "/usercollection/heartrate",
            }

            # Handle special tools
            if tool_name == "get_personal_info":
                return await self._get_personal_info(client)
            elif tool_name == "get_daily_summary":
                return await self._get_daily_summary(client, start_date, end_date)
            elif tool_name == "get_today_health":
                return await self._get_today_health(client)
            elif tool_name in endpoint_map:
                return await self._fetch_endpoint(
                    client, endpoint_map[tool_name], start_date, end_date
                )
            else:
                return ToolResult.fail(f"Unknown tool: {tool_name}")

        except httpx.HTTPStatusError as e:
            return ToolResult.fail(
                f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            )
        except httpx.RequestError as e:
            return ToolResult.fail(f"Request error: {e}")
        except Exception as e:
            return ToolResult.fail(f"Error: {e}")

    async def _fetch_endpoint(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        start_date: str,
        end_date: str
    ) -> ToolResult:
        """Fetch data from an Oura API endpoint."""
        response = await client.get(
            endpoint,
            params={"start_date": start_date, "end_date": end_date}
        )
        response.raise_for_status()
        data = response.json()
        return ToolResult.ok(data.get('data', data))

    async def _get_personal_info(self, client: httpx.AsyncClient) -> ToolResult:
        """Get user profile information."""
        response = await client.get("/usercollection/personal_info")
        response.raise_for_status()
        return ToolResult.ok(response.json())

    async def _get_daily_summary(
        self,
        client: httpx.AsyncClient,
        start_date: str,
        end_date: str
    ) -> ToolResult:
        """Get combined health summary for a date range."""
        # Fetch all data types in parallel
        endpoints = {
            "readiness": "/usercollection/daily_readiness",
            "sleep": "/usercollection/daily_sleep",
            "activity": "/usercollection/daily_activity",
            "stress": "/usercollection/daily_stress",
        }

        results = {}
        for name, endpoint in endpoints.items():
            try:
                response = await client.get(
                    endpoint,
                    params={"start_date": start_date, "end_date": end_date}
                )
                if response.status_code == 200:
                    data = response.json()
                    results[name] = data.get('data', [])
                else:
                    results[name] = None
            except Exception:
                results[name] = None

        return ToolResult.ok(results)

    async def _get_today_health(self, client: httpx.AsyncClient) -> ToolResult:
        """Get today's complete health snapshot with analysis."""
        today = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
        yesterday = (
            datetime.now(ZoneInfo('America/New_York')) - timedelta(days=1)
        ).strftime('%Y-%m-%d')

        # Get today's data (may include last night's sleep)
        summary_result = await self._get_daily_summary(client, yesterday, today)

        if not summary_result.success:
            return summary_result

        data = summary_result.data

        # Extract the most recent entries for each metric
        snapshot = {
            "date": today,
            "readiness": self._get_latest(data.get('readiness', []), today),
            "sleep": self._get_latest(data.get('sleep', []), today),
            "activity": self._get_latest(data.get('activity', []), today),
            "stress": self._get_latest(data.get('stress', []), today),
        }

        # Calculate summary metrics
        snapshot["summary"] = self._calculate_summary(snapshot)

        return ToolResult.ok(snapshot)

    def _get_latest(self, items: List[Dict], target_date: str) -> Optional[Dict]:
        """Get the most recent item, preferring the target date."""
        if not items:
            return None

        # Try to find exact date match
        for item in reversed(items):
            if item.get('day') == target_date:
                return item

        # Fall back to most recent
        return items[-1] if items else None

    def _calculate_summary(self, snapshot: Dict) -> Dict[str, Any]:
        """Calculate summary metrics from snapshot data."""
        summary = {
            "overall_status": "unknown",
            "recommendations": []
        }

        readiness = snapshot.get('readiness')
        sleep = snapshot.get('sleep')
        activity = snapshot.get('activity')

        scores = []

        if readiness and 'score' in readiness:
            score = readiness['score']
            scores.append(score)
            summary['readiness_score'] = score
            if score < 70:
                summary['recommendations'].append("Consider a recovery day - readiness is low")

        if sleep and 'score' in sleep:
            score = sleep['score']
            scores.append(score)
            summary['sleep_score'] = score
            if score < 70:
                summary['recommendations'].append("Prioritize sleep tonight")

        if activity and 'score' in activity:
            score = activity['score']
            summary['activity_score'] = score

        # Calculate overall status
        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score >= 85:
                summary['overall_status'] = 'excellent'
            elif avg_score >= 70:
                summary['overall_status'] = 'good'
            elif avg_score >= 55:
                summary['overall_status'] = 'fair'
            else:
                summary['overall_status'] = 'poor'

        return summary

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> ToolResult:
        """Check Oura API connectivity."""
        try:
            client = await self._get_client()
            response = await client.get("/usercollection/personal_info")
            if response.status_code == 200:
                return ToolResult.ok({
                    'status': 'ok',
                    'adapter': self.name,
                    'api': 'connected'
                })
            else:
                return ToolResult.fail(
                    f"API returned status {response.status_code}"
                )
        except Exception as e:
            return ToolResult.fail(f"Health check failed: {e}")
