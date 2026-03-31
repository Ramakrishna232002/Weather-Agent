from typing import Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from app.agents.state import SharedState
from app.agents.weather.weather_agent import WeatherAgent
from app.core.config import settings

class Supervisor:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        self.weather_agent = WeatherAgent()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(SharedState)
        
        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("weather_agent", self.weather_agent.process)
        workflow.add_node("generate_response", self.generate_response)
        
        workflow.set_entry_point("classify_intent")
        workflow.add_edge("classify_intent", "weather_agent")
        workflow.add_edge("weather_agent", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def classify_intent(self, state: SharedState) -> SharedState:
        prompt = f"Classify this query as 'weather' or 'other': {state['user_query']}"
        response = await self.llm.ainvoke([("user", prompt)])
        state["intent"] = response.content.strip().lower()
        return state
    
    async def generate_response(self, state: SharedState) -> SharedState:
        if state.get("error"):
            state["final_response"] = f"Error: {state['error']}"
        elif state.get("weather_analysis"):
            state["final_response"] = state["weather_analysis"]
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
            "completed_agents": []
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return {
            "success": final_state.get("error") is None,
            "response": final_state.get("final_response"),
            "error": final_state.get("error")
        }