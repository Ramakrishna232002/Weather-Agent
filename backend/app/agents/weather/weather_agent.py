from typing import Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from app.agents.base.base_agent import BaseAgent
from app.agents.state import SharedState
from app.services.weather_service import WeatherService
from app.services.geocoding_service import GeocodingService

class WeatherAgent(BaseAgent):
    def __init__(self):
        super().__init__("WeatherAgent")
        self.weather_service = WeatherService()
        self.geocoding_service = GeocodingService()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(SharedState)
        
        workflow.add_node("extract_location", self.extract_location)
        workflow.add_node("get_coordinates", self.get_coordinates)
        workflow.add_node("fetch_weather", self.fetch_weather)
        workflow.add_node("analyze_weather", self.analyze_weather)
        
        workflow.set_entry_point("extract_location")
        workflow.add_edge("extract_location", "get_coordinates")
        workflow.add_edge("get_coordinates", "fetch_weather")
        workflow.add_edge("fetch_weather", "analyze_weather")
        workflow.add_edge("analyze_weather", END)
        
        return workflow.compile()
    
    async def extract_location(self, state: SharedState) -> SharedState:
        prompt = f"Extract the city name from: {state['user_query']}. Return only city name."
        response = await self.llm.ainvoke([("user", prompt)])
        state["location"] = response.content.strip()
        return state
    
    async def get_coordinates(self, state: SharedState) -> SharedState:
        coords = await self.geocoding_service.get_coordinates(state["location"])
        if coords:
            state["coordinates"] = coords
        else:
            state["error"] = f"Location '{state['location']}' not found"
        return state
    
    async def fetch_weather(self, state: SharedState) -> SharedState:
        if state.get("error"):
            return state
        lat, lon = state["coordinates"]
        weather_data = await self.weather_service.get_weather_data(
            location_name=state["location"],
            latitude=lat,
            longitude=lon
        )
        state["weather_data"] = weather_data.dict() if weather_data else None
        return state
    
    async def analyze_weather(self, state: SharedState) -> SharedState:
        if state.get("error") or not state.get("weather_data"):
            return state
        
        weather = state["weather_data"]
        current_hour = datetime.now().hour

        if current_hour < 12:
            greeting = "Good morning"
        elif current_hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        prompt = f"""
        {greeting}!

        You are a professional weather expert. Analyze the weather data and provide helpful, accurate, and user-friendly insights.

        Location: {state['location']}
        Temperature: {weather.get('current', {}).get('temperature')}°C
        Conditions: {weather.get('current', {}).get('weather_description')}

        Instructions:
        1. Give a concise summary in 3-5 lines (professional and interactive tone)
        2. Provide accurate facts based on given data
        3. Then give practical recommendations in bullet points:
        - What to wear
        - What to carry
        - Outdoor activity suggestions
        - Food and drink suggestions
        4. Keep response clear, engaging, and helpful

        Format:
        Summary (3-5 lines)

        Recommendations:
        • ...
        • ...
        • ...
        """
        response = await self.llm.ainvoke([("user", prompt)])
        state["weather_analysis"] = response.content
        return state
    
    async def process(self, state: SharedState) -> SharedState:
        return await self.graph.ainvoke(state)