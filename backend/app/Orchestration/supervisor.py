from typing import Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from app.agents.state import SharedState
from app.agents.weather.weather_agent import WeatherAgent
from app.agents.crop.crop_agent import CropAgent
from app.core.config import settings

class Supervisor:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        self.weather_agent = WeatherAgent()
        self.crop_agent = CropAgent()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(SharedState)
        
        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("weather_agent", self.weather_agent.process)
        workflow.add_node("crop_agent", self.crop_agent.process)
        workflow.add_node("generate_response", self.generate_response)

        workflow.set_entry_point("classify_intent")

        workflow.add_conditional_edges(
            "classify_intent",
            self.route_to_agent,
            {
                "weather": "weather_agent",
                "crop": "crop_agent",
                "unknown": "generate_response"
            }
        )
        
        workflow.add_edge("weather_agent", "generate_response")
        workflow.add_edge("crop_agent", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def classify_intent(self, state: SharedState) -> SharedState:
            query = state['user_query'].lower()
            weather_keywords = ['weather', 'temperature', 'rain', 'wind', 'forecast', 'climate', 'humidity', 'precipitation', 'sunny', 'cloudy', 'storm']
            crop_keywords = ['crop', 'plant', 'grow', 'cultivate', 'farming', 'agriculture', 'sow', 'harvest', 'yield', 'season', 'soil', 'fertilizer', 'pesticide']

            if any(keyword in query for keyword in crop_keywords):
                intent = "crop"
            elif any(keyword in query for keyword in weather_keywords):
                intent = "weather"
            else:
                intent = "unknown"
            
            state["intent"] = intent
            print(f"🔍 Intent detected: {intent}")
            print(f"📝 Query: {query}")
            return state

    async def route_to_agent(self, state: SharedState) -> str:
        """Route to appropriate agent based on intent"""
        intent = state.get("intent", "unknown")
        print(f"🚦 Routing intent: {intent}")
        if intent == "weather":
            return "weather"
        elif intent == "crop":
            return "crop"
        return "unknown"
    
    async def generate_response(self, state: SharedState) -> SharedState:
        if state.get("error"):
            state["final_response"] = f"Error: {state['error']}"
        elif state.get("weather_analysis"):
            state["final_response"] = state["weather_analysis"]
        elif state.get("crop_analysis"):
            state["final_response"] = state["crop_analysis"]
        else:
            state["final_response"] = "I couldn't process your request."
        return state
    
    async def process(self, query: str) -> Dict[str, Any]:
        initial_state: SharedState = {
            "user_query": query,
            "intent": None,
            "location": None,
            "coordinates": None,
            "weather_data": None,
            "weather_analysis": None,
            "weather_recommendations": None,
            "final_response": None,
            "error": None,
            "messages": [],
            "current_agent": None,
            "current_season": None,
            "season_months": None,
            "crop_data": None,
            "crop_analysis": None,
            "completed_agents": []
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return {
            "success": final_state.get("error") is None,
            "response": final_state.get("final_response"),
            "error": final_state.get("error")
        }