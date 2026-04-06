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
    
    # Response
    final_response: Optional[str]
    
    # Error Handling
    error: Optional[str]
    
    # Messages for conversation history
    messages: Annotated[list, add_messages]
    
    # Workflow Control
    current_agent: Optional[str]
    completed_agents: List[str]
