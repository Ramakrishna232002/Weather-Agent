from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.agents.base.base_agent import BaseAgent
from app.agents.state import SharedState

class GeneralAgent(BaseAgent):
    def __init__(self):
        super().__init__("GeneralAgent")
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(SharedState)
        
        workflow.add_node("generate_response", self.generate_response)
        
        workflow.set_entry_point("generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def generate_response(self, state: SharedState) -> SharedState:
        """
        Generate response for general knowledge queries using LLM
        """
        query = state['user_query']
        
        prompt = f"""You are a helpful, knowledgeable assistant. Answer the following question in a clear, concise, and informative manner.

Question: {query}

Provide a well-structured response that is:
- Accurate and factual
- Easy to understand
- Professional yet friendly
- Include relevant details when appropriate

Keep the response to 3-5 paragraphs maximum. Use plain text, no markdown formatting."""
        
        response = await self.llm.ainvoke([("user", prompt)])
        state["general_analysis"] = response.content
        
        if "completed_agents" not in state:
            state["completed_agents"] = []
        if "general" not in state["completed_agents"]:
            state["completed_agents"].append("general")
        
        return state
    
    async def process(self, state: SharedState) -> SharedState:
        return await self.graph.ainvoke(state)