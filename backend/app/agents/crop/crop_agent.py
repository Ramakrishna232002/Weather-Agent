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
            location = location.title()
        else:
            words = query.replace('?', '').replace('.', '').split()
            if words:
                location = words[-1].title()
        
        state["location"] = location if location else "Pune"
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
        return state
    
    async def generate_recommendations(self, state: SharedState) -> SharedState:
        if state.get("error"):
            state["crop_analysis"] = f"Error: {state['error']}"
            return state
        
        location = state["location"]
        user_query = state['user_query']
        
        prompt = f"""Answer this question as professional crop expert and focus on main things first: {user_query}

Focus ONLY on the specific crop mentioned. Provide:
- What the crop needs (best soil, water, climate)
- Growing period
- Best season
- Expected yield

Keep response short and factual. 5-7 sentences only."""
        
        response = await self.llm.ainvoke([("user", prompt)])
        state["crop_analysis"] = response.content
        
        if "completed_agents" not in state:
            state["completed_agents"] = []
        if "crop" not in state["completed_agents"]:
            state["completed_agents"].append("crop")
        
        return state
    
    async def process(self, state: SharedState) -> SharedState:
        return await self.graph.ainvoke(state)