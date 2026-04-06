import re
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.agents.base.base_agent import BaseAgent
from app.agents.state import SharedState
from app.services.geocoding_service import GeocodingService
from datetime import datetime

class CropAgent(BaseAgent):
    def __init__(self):
        super().__init__("CropAgent")
        self.geocoding_service = GeocodingService()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(SharedState)
        
        workflow.add_node("extract_location", self.extract_location)
        workflow.add_node("get_coordinates", self.get_coordinates)
        workflow.add_node("get_current_season", self.get_current_season)
        workflow.add_node("generate_recommendations", self.generate_recommendations)
        
        workflow.set_entry_point("extract_location")
        workflow.add_edge("extract_location", "get_coordinates")
        workflow.add_edge("get_coordinates", "get_current_season")
        workflow.add_edge("get_current_season", "generate_recommendations")
        workflow.add_edge("generate_recommendations", END)
        
        return workflow.compile()
    
    async def extract_location(self, state: SharedState) -> SharedState:
        query = state['user_query'].lower()
        
        # Extract location using regex patterns
        patterns = [
            r'in\s+([a-z\s]+?)(?:\?|$|\.)',
            r'at\s+([a-z\s]+?)(?:\?|$|\.)',
            r'for\s+([a-z\s]+?)(?:\?|$|\.)',
            r'cultivate now in\s+([a-z\s]+?)(?:\?|$|\.)',
            r'weather in\s+([a-z\s]+?)(?:\?|$|\.)',
            r'crop.*?in\s+([a-z\s]+?)(?:\?|$|\.)'
        ]
        
        location = None
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                location = match.group(1).strip()
                break
        
        if location:
            # Clean and capitalize location name
            location = location.title()
        else:
            # Fallback: try to get the last word before question mark or period
            words = query.replace('?', '').replace('.', '').split()
            if words:
                location = words[-1].title()
        
        state["location"] = location if location else "Pune"
        print(f"📍 Location extracted: {state['location']}")
        return state
    
    async def get_coordinates(self, state: SharedState) -> SharedState:
        location = state.get("location")
        if not location:
            state["error"] = "Location not found"
            return state
        
        coords = await self.geocoding_service.get_coordinates(location)
        if coords:
            state["coordinates"] = coords
        else:
            print(f"⚠️ Coordinates not found for {location}, proceeding without coordinates")
            state["coordinates"] = None
        return state
    
    async def get_current_season(self, state: SharedState) -> SharedState:
        current_month = datetime.now().month
        
        if 3 <= current_month <= 6:
            season = "Zaid (Summer)"
            months = "March to June"
        elif 7 <= current_month <= 10:
            season = "Kharif (Monsoon)"
            months = "July to October"
        else:
            season = "Rabi (Winter)"
            months = "November to February"
        
        state["current_season"] = season
        state["season_months"] = months
        print(f"📍 Season: {season}")
        return state
    
    async def generate_recommendations(self, state: SharedState) -> SharedState:
        print("📍 Crop Agent: generate_recommendations called")
        if state.get("error"):
            state["crop_analysis"] = f"Error: {state['error']}"
            return state
        
        location = state["location"]
        season = state.get("current_season", "")
        months = state.get("season_months", "")
        
        prompt = f"""You are an expert agricultural advisor for Indian farming conditions.

LOCATION: {location}
CURRENT SEASON: {season} ({months})

Based on the climate, soil, and seasonal patterns of {location}, recommend the top 5 most suitable crops for the current {season} season.

For EACH of the 5 crops, provide:

• Common Name and Scientific Name
• Growing Period (in days)
• Best Season with sowing and harvest months
• Suitable Soil Type
• Water Requirement (Low/Moderate/High with mm range)
• Expected Yield (quintals/hectare)

Also write a 5-8 line professional, human-like introductory paragraph that:
- Greets the user warmly
- Explains the agricultural suitability of {location} for the current {season} season
- Naturally mentions the 5 crops you are recommending
- Provides practical, actionable advice

FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS (use plain text, no markdown):

[Introductory paragraph here - 5 to 8 lines]

CROP 1: [Common Name] ([Scientific Name])
Growing Period: X-Y days
Best Season: [Season] (Sow: Month, Harvest: Month)
Soil Type: Description
Water Requirement: Level (X-Y mm)
Expected Yield: X-Y quintals/hectare

CROP 2: [Common Name] ([Scientific Name])
[Same format...]

Continue for CROP 3, CROP 4, CROP 5

Keep the response professional, informative, and farmer-friendly. Do not use any markdown like **bold** or *italics*. Use simple line breaks."""
        
        response = await self.llm.ainvoke([("user", prompt)])
        state["crop_analysis"] = response.content
        
        if "completed_agents" not in state:
            state["completed_agents"] = []
        state["completed_agents"].append(self.name)
        
        return state
    
    async def process(self, state: SharedState) -> SharedState:
        return await self.graph.ainvoke(state)