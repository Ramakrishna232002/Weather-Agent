from abc import ABC, abstractmethod
from typing import Dict, Any
from langgraph.graph import StateGraph
from langchain_ollama import ChatOllama
from app.core.config import settings

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        self.graph = None
    
    @abstractmethod
    def _build_graph(self) -> StateGraph:
        pass
    
    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pass