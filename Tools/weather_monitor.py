"""
Weather Monitoring System for Morning Briefs

Provides context-aware weather recommendations
focused on practical daily actions.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path('/Users/jeremy/Projects/Thanos/.env')
load_dotenv(dotenv_path=env_path)

class WeatherMonitor:
    def __init__(self, api_key: Optional[str] = None, location: str = "King,US"):
        """
        Initialize weather monitoring.
        
        Args:
            api_key: OpenWeatherMap API key (optional, falls back to .env)
            location: City and state/country code
        """
        self.location = location
        self.api_key = api_key or os.getenv('OPENWEATHERMAP_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key required. Set in .env or pass directly.")
        
        self.base_url = "https://api.openweathermap.org/data/2.5/forecast"
        self._load_recommendations()
    
    def _load_recommendations(self):
        """Load context-specific weather recommendations."""
        self.recommendations = {
            "temperature": {
                "freezing": {
                    "temp_range": (0, 32),  # Fahrenheit
                    "actions": [
                        "Start car 10-15 minutes before driving",
                        "Check tire pressure (drops in cold)",
                        "Keep ice scraper in car",
                        "Warm up engine gently"
                    ]
                },
                "cold": {
                    "temp_range": (33, 45),
                    "actions": [
                        "Start car 5-10 minutes before driving",
                        "Check windshield washer fluid (don't let freeze)",
                        "Consider remote start if available"
                    ]
                }
            },
            "precipitation": {
                "rain": {
                    "conditions": ["Rain", "Drizzle", "Thunderstorm"],
                    "actions": [
                        "Pack umbrella",
                        "Check windshield wipers",
                        "Allow extra travel time",
                        "Keep waterproof jacket handy"
                    ]
                },
                "snow": {
                    "conditions": ["Snow", "Sleet", "Freezing Rain"],
                    "actions": [
                        "Pack snow brush/scraper",
                        "Check tire tread",
                        "Drive slowly",
                        "Keep emergency kit in trunk"
                    ]
                }
            }
        }
    
    def get_forecast(self) -> Dict:
        """
        Fetch weather forecast.
        
        Returns:
            Dict with forecast details
        """
        params = {
            'q': self.location,
            'appid': self.api_key,
            'units': 'imperial'  # Fahrenheit
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Weather API error: {e}")
            print(f"URL: {response.url}")
            print(f"Status code: {response.status_code}")
            print(f"Response text: {response.text}")
            return {}
    
    def parse_forecast(self, forecast_data: Dict) -> Dict:
        """
        Extract key forecast information.
        
        Args:
            forecast_data: Raw forecast JSON
        
        Returns:
            Parsed forecast summary
        """
        if not forecast_data or 'list' not in forecast_data:
            return {}
        
        # Next morning's forecast (around 6-9am)
        morning_forecast = forecast_data['list'][1]
        
        return {
            'temperature': morning_forecast['main']['temp'],
            'feels_like': morning_forecast['main']['feels_like'],
            'description': morning_forecast['weather'][0]['description'].title(),
            'precipitation_chance': forecast_data.get('pop', 0) * 100  # Probability of precipitation
        }
    
    def get_recommendations(self, forecast: Dict) -> List[str]:
        """
        Generate actionable recommendations.
        
        Args:
            forecast: Parsed forecast dictionary
        
        Returns:
            List of practical recommendations
        """
        if not forecast:
            return ["Unable to fetch weather recommendations"]
        
        temp = forecast.get('temperature', 0)
        desc = forecast.get('description', '').lower()
        
        recommendations = []
        
        # Temperature-based recommendations
        if temp <= 32:
            recommendations.extend(self.recommendations['temperature']['freezing']['actions'])
        elif temp <= 45:
            recommendations.extend(self.recommendations['temperature']['cold']['actions'])
        
        # Precipitation recommendations
        if any(precip in desc for precip in ['rain', 'drizzle', 'thunderstorm']):
            recommendations.extend(self.recommendations['precipitation']['rain']['actions'])
        
        if any(precip in desc for precip in ['snow', 'sleet', 'freezing rain']):
            recommendations.extend(self.recommendations['precipitation']['snow']['actions'])
        
        return recommendations
    
    def generate_morning_brief(self) -> str:
        """
        Generate a concise morning weather brief.
        
        Returns:
            Formatted weather brief
        """
        forecast_data = self.get_forecast()
        forecast = self.parse_forecast(forecast_data)
        recommendations = self.get_recommendations(forecast)
        
        brief = "🌦️ MORNING WEATHER BRIEF 🌦️\n"
        brief += f"Temp: {forecast.get('temperature', 'N/A')}°F "
        brief += f"(Feels like {forecast.get('feels_like', 'N/A')}°F)\n"
        brief += f"Conditions: {forecast.get('description', 'Unknown')}\n\n"
        
        brief += "🚗 ACTION ITEMS:\n"
        for rec in recommendations:
            brief += f"• {rec}\n"
        
        return brief


def main():
    """CLI interface for weather monitor."""
    monitor = WeatherMonitor()
    print(monitor.generate_morning_brief())


if __name__ == '__main__':
    main()