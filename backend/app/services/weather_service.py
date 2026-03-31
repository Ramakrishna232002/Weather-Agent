import httpx
from datetime import datetime, date
from typing import List, Optional
from app.models.weather import (
    WeatherCurrent, 
    DailyForecast, 
    WeeklyForecast, 
    WeatherData
)
from app.core.config import settings

class WeatherService:
    def __init__(self):
        self.base_url = settings.WEATHER_API_URL
    
    def _get_weather_description(self, weather_code: int) -> str:
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Rain showers",
            81: "Moderate showers",
            82: "Violent showers",
            95: "Thunderstorm"
        }
        return weather_codes.get(weather_code, "Unknown")
    
    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherCurrent:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,rain",
            "timezone": "Asia/Kolkata"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            current_data = data["current"]
            
            return WeatherCurrent(
                temperature=current_data["temperature_2m"],
                humidity=current_data["relative_humidity_2m"],
                wind_speed=current_data["wind_speed_10m"],
                precipitation=current_data["rain"],
                weather_description="",
                timestamp=datetime.now()
            )
    
    async def get_all_forecast(self, latitude: float, longitude: float) -> List[DailyForecast]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,rain_sum,wind_speed_10m_max,weather_code",
            "timezone": "Asia/Kolkata",
            "forecast_days": 16
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            daily_data = data["daily"]
            days = []
            
            for i in range(len(daily_data["time"])):
                # Get values and handle nulls
                temp_max = daily_data["temperature_2m_max"][i]
                temp_min = daily_data["temperature_2m_min"][i]
                rain = daily_data["rain_sum"][i]
                wind = daily_data["wind_speed_10m_max"][i]
                weather_code = daily_data["weather_code"][i]
                
                # Convert None to 0
                if temp_max is None:
                    temp_max = 0.0
                if temp_min is None:
                    temp_min = 0.0
                if rain is None:
                    rain = 0.0
                if wind is None:
                    wind = 0.0
                if weather_code is None:
                    weather_code = 0
                
                day = DailyForecast(
                    date=datetime.strptime(daily_data["time"][i], "%Y-%m-%d").date(),
                    temperature_max=float(temp_max),
                    temperature_min=float(temp_min),
                    precipitation=float(rain),
                    wind_speed=float(wind),
                    weather_description=self._get_weather_description(weather_code)
                )
                days.append(day)
            
            return days
    
    async def get_weather_data(
        self, 
        location_name: str,
        latitude: float, 
        longitude: float
    ) -> WeatherData:
        current = await self.get_current_weather(latitude, longitude)
        
        all_days = await self.get_all_forecast(latitude, longitude)
        
        if not all_days:
            return WeatherData(
                location_name=location_name,
                latitude=latitude,
                longitude=longitude,
                timezone="Asia/Kolkata",
                current=current,
                forecast=[],
                last_updated=datetime.now()
            )
        
        current.weather_description = all_days[0].weather_description
        
        week1 = all_days[:7]
        week2 = all_days[7:14]
        week3 = all_days[14:16]
        
        forecast = []
        if week1:
            forecast.append(WeeklyForecast(week_number=1, days=week1))
        if week2:
            forecast.append(WeeklyForecast(week_number=2, days=week2))
        if week3:
            forecast.append(WeeklyForecast(week_number=3, days=week3))
        
        return WeatherData(
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            timezone="Asia/Kolkata",
            current=current,
            forecast=forecast,
            last_updated=datetime.now()
        )