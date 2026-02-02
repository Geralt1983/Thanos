# Weather Monitor

## Setup

1. Get OpenWeatherMap API Key
   - Sign up at https://openweathermap.org/
   - Add to `.env` as `OPENWEATHERMAP_API_KEY=your_key_here`

2. Configure Location
   - Edit `WeatherMonitor` initialization in `weather_monitor.py`
   - Default: `Charlotte,NC`

## Usage

### CLI
```bash
python weather_monitor.py
```

### Integration
- Morning briefs
- Heartbeat checks
- Periodic system alerts

## Recommendations

Generates actionable recommendations:
- Car preparation
- Clothing suggestions
- Driving tips

## Customization

Modify `_load_recommendations()` to add:
- Location-specific advice
- More detailed weather parsing
- Custom action thresholds

## Features
- Temperature-based advice
- Precipitation detection
- Feels-like temperature consideration
- Configurable location