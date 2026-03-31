from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

class WeatherCurrent(BaseModel):
    """Current weather data"""
    temperature: float
    humidity: float
    wind_speed: float
    precipitation: float
    weather_description: str
    timestamp: datetime

class DailyForecast(BaseModel):
    """Daily forecast - For 3-week tiles"""
    date: date
    temperature_max: float
    temperature_min: float
    precipitation: float
    wind_speed: float
    weather_description: str

class WeeklyForecast(BaseModel):
    """One week of forecast"""
    week_number: int
    days: List[DailyForecast]

class WeatherData(BaseModel):
    """Complete weather data model"""
    # Location info
    location_name: str
    latitude: float
    longitude: float
    timezone: str
    
    # Current weather
    current: WeatherCurrent
    
    # Forecast (3 weeks)
    forecast: List[WeeklyForecast]
    
    # Metadata
    last_updated: datetime
    data_source: str = "Open-Meteo"
    
    # Placeholder for future alerts
    alerts: Optional[List] = None
    
    # AI Analysis
    analysis: Optional[str] = None
    recommendations: Optional[List[str]] = None

# Request models
class WeatherRequest(BaseModel):
    location: str
    include_forecast: bool = True

class CoordinatesRequest(BaseModel):
    latitude: float
    longitude: float
    include_forecast: bool = True

# Response model for API
class WeatherResponse(BaseModel):
    success: bool
    data: Optional[WeatherData] = None
    error: Optional[str] = None