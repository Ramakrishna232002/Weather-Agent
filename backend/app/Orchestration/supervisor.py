from typing import Dict, Any, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from app.agents.state import SharedState
from app.agents.weather.weather_agent import WeatherAgent
from app.agents.crop.crop_agent import CropAgent
from app.agents.general.general_agent import GeneralAgent
from app.agents.soil.soil_agent import SoilAgent
from app.agents.market.market_agent import MarketAgent
from app.core.config import settings

class Supervisor:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        self.weather_agent = WeatherAgent()
        self.crop_agent = CropAgent()
        self.general_agent = GeneralAgent()
        self.soil_agent = SoilAgent()
        self.market_agent = MarketAgent()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(SharedState)
        
        # Nodes
        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("plan_agents", self.plan_agents)
        workflow.add_node("weather_agent", self.run_weather_agent)
        workflow.add_node("crop_agent", self.run_crop_agent)
        workflow.add_node("soil_agent", self.run_soil_agent)
        workflow.add_node("market_agent", self.run_market_agent)
        workflow.add_node("general_agent", self.run_general_agent)
        workflow.add_node("combine_responses", self.combine_responses)
        workflow.add_node("generate_response", self.generate_response)

        # Entry point
        workflow.set_entry_point("classify_intent")
        workflow.add_edge("classify_intent", "plan_agents")

        # Conditional routing
        workflow.add_conditional_edges(
            "plan_agents",
            self.get_next_agent,
            {
                "weather_agent": "weather_agent",
                "crop_agent": "crop_agent",
                "soil_agent": "soil_agent",
                "market_agent": "market_agent",
                "general_agent": "general_agent",
                "combine": "combine_responses"
            }
        )
        
        # After each agent, go back to plan_agents
        workflow.add_edge("weather_agent", "plan_agents")
        workflow.add_edge("crop_agent", "plan_agents")
        workflow.add_edge("soil_agent", "plan_agents")
        workflow.add_edge("market_agent", "plan_agents")
        workflow.add_edge("general_agent", "plan_agents")
        
        # Final flow
        workflow.add_edge("combine_responses", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def run_weather_agent(self, state: SharedState) -> SharedState:
        result = await self.weather_agent.process(state)
        if "completed_agents" not in result:
            result["completed_agents"] = []
        if "weather" not in result["completed_agents"]:
            result["completed_agents"].append("weather")
        return result
    
    async def run_crop_agent(self, state: SharedState) -> SharedState:
        result = await self.crop_agent.process(state)
        if "completed_agents" not in result:
            result["completed_agents"] = []
        if "crop" not in result["completed_agents"]:
            result["completed_agents"].append("crop")
        return result
    
    async def run_soil_agent(self, state: SharedState) -> SharedState:
        result = await self.soil_agent.process(state)
        if "completed_agents" not in result:
            result["completed_agents"] = []
        if "soil" not in result["completed_agents"]:
            result["completed_agents"].append("soil")
        return result
    
    async def run_market_agent(self, state: SharedState) -> SharedState:
        result = await self.market_agent.process(state)
        if "completed_agents" not in result:
            result["completed_agents"] = []
        if "market" not in result["completed_agents"]:
            result["completed_agents"].append("market")
        print(f"✅ MarketAgent marked as completed")
        return result
    
    async def run_general_agent(self, state: SharedState) -> SharedState:
        result = await self.general_agent.process(state)
        if "completed_agents" not in result:
            result["completed_agents"] = []
        if "general" not in result["completed_agents"]:
            result["completed_agents"].append("general")
        return result
    
    async def classify_intent(self, state: SharedState) -> SharedState:
        query = state['user_query'].lower()
        
        # Price detection patterns
        price_patterns = [
            r'price\s+of\s+(\w+)',           
            r'(\w+)\s+price',                 
            r'rate\s+of\s+(\w+)',             
            r'(\w+)\s+rate',                  
            r'cost\s+of\s+(\w+)',             
            r'(\w+)\s+cost',                  
            r'(\w+)\s+ka\s+price',            
            r'(\w+)\s+ke\s+rate',             
            r'price\s+in\s+(\w+)',            
            r'market\s+price',                
            r'mandi\s+rate',                  
            r'rate\s+in\s+(\w+)',             
            r'(\w+)\s+per\s+kg',              
            r'(\w+)\s+per\s+quintal',         
        ]
        
        import re
        is_price_query = any(re.search(pattern, query) for pattern in price_patterns)
        
        weather_keywords = ['weather', 'temperature', 'rain', 'wind', 'forecast', 'climate', 'humidity']
        crop_keywords = ['crop', 'plant', 'grow', 'cultivate', 'farming', 'agriculture', 'sow', 'harvest', 'yield', 'season']
        soil_keywords = ['soil', 'clay', 'loam', 'sandy', 'ph', 'nutrient', 'fertility', 'organic']
        
        if is_price_query:
            intent = "market"
        elif any(keyword in query for keyword in soil_keywords):
            intent = "soil"
        elif any(keyword in query for keyword in crop_keywords):
            intent = "crop"
        elif any(keyword in query for keyword in weather_keywords):
            intent = "weather"
        else:
            intent = "general"
        
        state["intent"] = intent
        print(f"🔍 Intent: {intent}")
        return state

    async def plan_agents(self, state: SharedState) -> SharedState:
        # Only plan once
        if state.get("needed_agents") is not None:
            print(f"📋 Already planned. Needed: {state.get('needed_agents')}")
            print(f"📋 Completed: {state.get('completed_agents')}")
            return state
        
        query = state['user_query'].lower()
        intent = state.get("intent", "general")
        
        needed = []
        
        # Add agents based on intent and keywords
        if intent == "market":
            needed.append("market")
        
        weather_kw = ['weather', 'temperature', 'rain', 'wind', 'forecast', 'climate', 'humidity']
        if any(k in query for k in weather_kw):
            needed.append("weather")
        
        crop_kw = ['crop', 'plant', 'grow', 'cultivate', 'farming', 'agriculture', 'sow', 'harvest', 'yield', 'season']
        if any(k in query for k in crop_kw):
            needed.append("crop")
        
        soil_kw = ['soil', 'clay', 'loam', 'sandy', 'ph', 'nutrient', 'fertility', 'organic']
        if any(k in query for k in soil_kw):
            needed.append("soil")
        
        if not needed:
            needed.append("general")
        
        # Execution order: weather, crop, soil, market, general
        execution_order = []
        if "weather" in needed:
            execution_order.append("weather")
        if "crop" in needed:
            execution_order.append("crop")
        if "soil" in needed:
            execution_order.append("soil")
        if "market" in needed:
            execution_order.append("market")
        if "general" in needed:
            execution_order.append("general")
        
        state["needed_agents"] = needed
        state["execution_order"] = execution_order
        state["completed_agents"] = []
        
        print(f"📋 Needed Agents: {needed}")
        print(f"📋 Execution Order: {execution_order}")
        
        return state

    def get_next_agent(self, state: SharedState) -> str:
        execution_order = state.get("execution_order", [])
        completed_agents = state.get("completed_agents", [])
        
        for agent in execution_order:
            if agent not in completed_agents:
                print(f"🚦 Running: {agent}_agent")
                return f"{agent}_agent"
        
        print("🚦 All agents done, combining...")
        return "combine"

    async def combine_responses(self, state: SharedState) -> SharedState:
        """Combine outputs from all agents into a single AI response"""
        user_query = state['user_query']
        location = state.get('location', 'your area')
        
        # Get all agent analyses
        weather_info = state.get('weather_analysis', '')
        crop_info = state.get('crop_analysis', '')
        soil_info = state.get('soil_analysis', '')
        market_info = state.get('market_analysis', '')
        general_info = state.get('general_analysis', '')
        
        # Prioritize market response if it exists
        if market_info and ("price" in user_query.lower() or "rate" in user_query.lower() or "cost" in user_query.lower()):
            state["combined_analysis"] = market_info
            return state
        
        # Otherwise combine all responses
        prompt = f"""You are an expert agricultural advisor. Answer the following question:

QUESTION: {user_query}

RELEVANT INFORMATION:
Weather Information: {weather_info if weather_info else 'Not available'}
Crop Information: {crop_info if crop_info else 'Not available'}
Soil Information: {soil_info if soil_info else 'Not available'}
Market Information: {market_info if market_info else 'Not available'}
General Information: {general_info if general_info else 'Not available'}

Provide a helpful, professional response for {location}."""
        
        response = await self.llm.ainvoke([("user", prompt)])
        state["combined_analysis"] = response.content
        return state

    async def generate_response(self, state: SharedState) -> SharedState:
        if state.get("error"):
            state["final_response"] = f"Error: {state['error']}"
        elif state.get("combined_analysis"):
            state["final_response"] = state["combined_analysis"]
        elif state.get("market_analysis"):
            state["final_response"] = state["market_analysis"]
        elif state.get("weather_analysis"):
            state["final_response"] = state["weather_analysis"]
        elif state.get("crop_analysis"):
            state["final_response"] = state["crop_analysis"]
        elif state.get("soil_analysis"):
            state["final_response"] = state["soil_analysis"]
        elif state.get("general_analysis"):
            state["final_response"] = state["general_analysis"]
        else:
            state["final_response"] = "I couldn't process your request. Please try again."
        
        return state
    
    async def process(self, query: str) -> Dict[str, Any]:
        initial_state: SharedState = {
            "user_query": query,
            "intent": None,
            "location": None,
            "coordinates": None,
            "weather_data": None,
            "weather_analysis": None,
            "soil_analysis": None,
            "weather_recommendations": None,
            "final_response": None,
            "error": None,
            "messages": [],
            "current_agent": None,
            "current_season": None,
            "season_months": None,
            "crop_data": None,
            "crop_analysis": None,
            "general_analysis": None,
            "needed_agents": None,
            "execution_order": None,
            "combined_analysis": None,
            "completed_agents": [],
            "commodity": None,
            "city": None,
            "state": None,
            "market_price_data": None,
            "market_analysis": None
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return {
            "success": final_state.get("error") is None,
            "response": final_state.get("final_response"),
            "intent": final_state.get("intent"),
            "data": {
                "weather": final_state.get("weather_data"),
                "weather_analysis": final_state.get("weather_analysis"),
                "market_data": final_state.get("market_price_data"),
                "market_analysis": final_state.get("market_analysis")
            },
            "error": final_state.get("error")
        }