from typing import TypedDict, Optional, List, Any, Dict
from langgraph.graph.message import add_messages
from typing_extensions import Annotated

class SharedState(TypedDict):
    """Shared state for all agents"""
    
    # User Input
    user_query: str
    intent: Optional[str]
    
    # Location
    location: Optional[str]
    coordinates: Optional[tuple]

    # Season
    current_season: Optional[str]
    season_months: Optional[str]

    # Crop Data
    crop_data: Optional[List[Dict[str, Any]]]
    crop_analysis: Optional[str]
    
    # Weather Data
    weather_data: Optional[Dict[str, Any]]
    weather_analysis: Optional[str]
    weather_recommendations: Optional[List[str]]

    #General
    general_analysis: Optional[str]

    # Soil Data
    soil_analysis: Optional[str]
    
    # Multi-Agent Response
    needed_agents: Optional[List[str]]
    execution_order: Optional[List[str]]
    current_agent_index: Optional[int]
    combined_analysis: Optional[str]

  
    # Market Data
    commodity: Optional[str]
    city: Optional[str]
    state: Optional[str]
    market_price_data: Optional[List[Dict[str, Any]]]
    market_analysis: Optional[str]
    
    # Response
    final_response: Optional[str]
    
    # Error Handling
    error: Optional[str]
    
    # Messages for conversation history
    messages: Annotated[list, add_messages]
    
    # Workflow Control
    current_agent: Optional[str]
    completed_agents: List[str]
