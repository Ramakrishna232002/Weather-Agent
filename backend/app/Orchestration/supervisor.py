from typing import Dict, Any, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from app.agents.state import SharedState
from app.agents.weather.weather_agent import WeatherAgent
from app.agents.crop.crop_agent import CropAgent
from app.agents.general.general_agent import GeneralAgent
from app.agents.soil.soil_agent import SoilAgent
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
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(SharedState)
        
        # Nodes
        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("plan_agents", self.plan_agents)
        workflow.add_node("weather_agent", self.weather_agent.process)
        workflow.add_node("crop_agent", self.crop_agent.process)
        workflow.add_node("soil_agent", self.soil_agent.process)
        workflow.add_node("general_agent", self.general_agent.process)
        workflow.add_node("combine_responses", self.combine_responses)
        workflow.add_node("generate_response", self.generate_response)

        # Entry point
        workflow.set_entry_point("classify_intent")
        workflow.add_edge("classify_intent", "plan_agents")

        # Conditional routing from plan_agents using get_next_agent
        workflow.add_conditional_edges(
            "plan_agents",
            self.get_next_agent,
            {
                "weather_agent": "weather_agent",
                "crop_agent": "crop_agent",
                "soil_agent": "soil_agent",
                "general_agent": "general_agent",
                "combine": "combine_responses"
            }
        )
        
        # After each agent, go back to plan_agents to get next agent
        workflow.add_edge("weather_agent", "plan_agents")
        workflow.add_edge("crop_agent", "plan_agents")
        workflow.add_edge("soil_agent", "plan_agents")
        workflow.add_edge("general_agent", "plan_agents")
        
        # Final flow
        workflow.add_edge("combine_responses", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def classify_intent(self, state: SharedState) -> SharedState:
        query = state['user_query'].lower()
        
        weather_keywords = ['weather', 'temperature', 'rain', 'wind', 'forecast', 'climate', 'humidity', 'precipitation', 'sunny', 'cloudy', 'storm']
        crop_keywords = ['crop', 'plant', 'grow', 'cultivate', 'farming', 'agriculture', 'sow', 'harvest', 'yield', 'season']
        soil_keywords = ['soil', 'soil type', 'clay', 'loam', 'sandy', 'soil erosion', 'soil conservation', 'salinity', 'nutrients', 'fertility', 'organic matter', 'moisture', 'soil health', 'compaction', 'soil testing']
        
        if any(keyword in query for keyword in soil_keywords):
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
        """Determine which agents need to run and execution order"""
        
        # ONLY plan once 
        if state.get("needed_agents") is not None:
            print(f"📋 Already planned. Needed: {state.get('needed_agents')}")
            print(f"📋 Completed: {state.get('completed_agents')}")
            return state
        
        query = state['user_query'].lower()
        
        weather_kw = ['weather', 'temperature', 'rain', 'wind', 'forecast', 'climate', 'humidity']
        crop_kw = ['crop', 'plant', 'grow', 'cultivate', 'farming', 'agriculture', 'sow', 'harvest', 'yield', 'season', 'wheat', 'rice', 'maize', 'corn', 'sorghum']
        soil_kw = ['soil', 'clay', 'loam', 'sandy', 'ph', 'nutrient', 'fertility', 'organic', 'drainage', 'compost', 'manure']
        
        needed = []
        
        if any(k in query for k in weather_kw):
            needed.append("weather")
        if any(k in query for k in crop_kw):
            needed.append("crop")
        if any(k in query for k in soil_kw):
            needed.append("soil")
        
        if not needed:
            needed.append("general")
        
        # Execution order: weather → crop → soil → general
        execution_order = []
        if "weather" in needed:
            execution_order.append("weather")
        if "crop" in needed:
            execution_order.append("crop")
        if "soil" in needed:
            execution_order.append("soil")
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
        
        crop_info = state.get('crop_analysis', '')
        soil_info = state.get('soil_analysis', '')
        weather_info = state.get('weather_analysis', '')
        
        prompt = f"""You are an expert agricultural advisor and a experienced scientist and a best weather,crop,soil knowledge farmer and best advisor for Indian farmers. Answer the following question in a helpful, professional, and interactive manner.

QUESTION: {user_query}

RELEVANT INFORMATION:
Crop Information: {crop_info if crop_info else 'Not available'}
Soil Information: {soil_info if soil_info else 'Not available'}
Weather Information: {weather_info if weather_info else 'Not available'}

INSTRUCTIONS:
1. Answer the question directly and clearly and focus on the important part of solution as per requirement in the QUESTION
2. Use a warm, professional and practical tone (like a friendly expert and best Advisor)
3. Keep response to 3-4 paragraph professional and informative and mainly focus on solution for requested QUESTION
4. Each paragraph should have 3-4 lines and You can use suitable emoji if required
5. Include practical, professional ,actionable recommendations suggestions and key things to do
6. Do NOT list multiple crops unless specifically asked and always avoid the useless crop/plant information like weeds, useless grass etc.
7. Focus ONLY on answering the specific QUESTION from user and answer it more practicaly, expert and interactive way

Write a natural, conversational response for {location}."""
        
        response = await self.llm.ainvoke([("user", prompt)])
        state["combined_analysis"] = response.content
        return state

    async def generate_response(self, state: SharedState) -> SharedState:
        if state.get("error"):
            state["final_response"] = f"Error: {state['error']}"
        elif state.get("combined_analysis"):
            state["final_response"] = state["combined_analysis"]
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
            "completed_agents": []
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return {
            "success": final_state.get("error") is None,
            "response": final_state.get("final_response"),
            "data": {
                "weather": final_state.get("weather_data"),
                "weather_analysis": final_state.get("weather_analysis"),
                "weather_recommendations": final_state.get("weather_recommendations")
            },
            "error": final_state.get("error")
        }