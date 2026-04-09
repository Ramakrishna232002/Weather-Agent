from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.agents.base.base_agent import BaseAgent
from app.agents.state import SharedState
from app.services.geocoding_service import GeocodingService

class SoilAgent(BaseAgent):
    def __init__(self):
        super().__init__("SoilAgent")
        self.geocoding_service = GeocodingService()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(SharedState)
        
        workflow.add_node("extract_location", self.extract_location)
        workflow.add_node("get_coordinates", self.get_coordinates)
        workflow.add_node("analyze_soil", self.analyze_soil)
        
        workflow.set_entry_point("extract_location")
        workflow.add_edge("extract_location", "get_coordinates")
        workflow.add_edge("get_coordinates", "analyze_soil")
        workflow.add_edge("analyze_soil", END)
        
        return workflow.compile()
    
    async def extract_location(self, state: SharedState) -> SharedState:
        prompt = f"Extract the city/location name from this query. Return only the city name: {state['user_query']}"
        response = await self.llm.ainvoke([("user", prompt)])
        state["location"] = response.content.strip()
        return state
    
    async def get_coordinates(self, state: SharedState) -> SharedState:
        coords = await self.geocoding_service.get_coordinates(state["location"])
        if coords:
            state["coordinates"] = coords
        else:
            state["coordinates"] = None
        return state
    
    async def analyze_soil(self, state: SharedState) -> SharedState:
        
        if state.get("error"):
            state["soil_analysis"] = f"Error: {state['error']}"
            return state
        
        location = state["location"]
        user_query = state['user_query']
        crop_info = state.get('crop_analysis', '')
        
        prompt = f"""Answer this question as professional soil expert and scientist and a well known experienced farmer and focus on main things first: {user_query}

Crop needs: {crop_info if crop_info else 'General crop'}

Focus ONLY on the query. Provide:
- Correct soil type 
- Correct soil properties
- Correct soil information based on query

Give specific soil recommendations for {location}. Be direct and practical. 4-6 sentences only."""
        
        response = await self.llm.ainvoke([("user", prompt)])
        state["soil_analysis"] = response.content    
        if "completed_agents" not in state:
            state["completed_agents"] = []
        if "soil" not in state["completed_agents"]:
            state["completed_agents"].append("soil")
        
        return state
    
    async def process(self, state: SharedState) -> SharedState:
        return await self.graph.ainvoke(state)