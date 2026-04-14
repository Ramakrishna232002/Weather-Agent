from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
import re
from app.Orchestration.supervisor import Supervisor
from app.services.weather_service import WeatherService
from app.services.geocoding_service import GeocodingService

router = APIRouter()
supervisor = Supervisor()
weather_service = WeatherService()
geocoding_service = GeocodingService()

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    success: bool
    response: str
    data: Optional[Any] = None
    error: Optional[str] = None
    intent: Optional[str] = None

@router.post("", response_model=QueryResponse)
@router.post("/", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Universal endpoint for all queries.
    Calls Supervisor for AI analysis AND Weather Service for weather data.
    """
    try:
        # Step 1: Get AI analysis from Supervisor
        result = await supervisor.process(request.query)
        
        if not result["success"]:
            return QueryResponse(
                success=False,
                response="",
                data=None,
                error=result.get("error", "Failed to process query"),
                intent=None
            )
        
        # Step 2: Try to get weather data if it's a weather-related query
        weather_data = None
        
        # Extract location from query
        location_match = re.search(r'(?:weather|temperature|rain|wind|forecast|climate).*?(?:in|at|for)\s+([a-zA-Z\s]+?)(?:\?|$|\.)', request.query.lower())
        
        if location_match:
            location = location_match.group(1).strip()
            location = re.sub(r'\s+(today|tomorrow|this week|next week|tonight)$', '', location)
            location = location.strip()
            
            # Get coordinates for the location
            coordinates = await geocoding_service.get_coordinates(location)
            
            if coordinates:
                lat, lon = coordinates
                # Get weather data
                weather_data = await weather_service.get_weather_data(
                    location_name=location.title(),
                    latitude=lat,
                    longitude=lon
                )
                # Add AI analysis to weather data
                if weather_data:
                    weather_data.analysis = result["response"]
                    weather_data.recommendations = result.get("recommendations", [])
        
        # Step 3: Return combined response
        return QueryResponse(
            success=True,
            response=result["response"],
            data=weather_data.dict() if weather_data else None,
            error=None,
            intent=result.get("intent")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))