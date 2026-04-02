from typing import List, Dict, Any
from .base import BaseAgent, AgentConfig, AgentResult

class RAGAgent(BaseAgent):
    """RAG агент для работы с графом знаний (будущая реализация)"""
    
    @property
    def name(self) -> str:
        return "rag"
    
    @property
    def description(self) -> str:
        return "Поиск и синтез знаний из графа (GraphRAG)"
    
    async def process(self, message: str, context: Dict[str, Any]) -> AgentResult:
        # TODO: Реализовать GraphRAG
        return AgentResult(
            output="RAG агент в разработке. Используйте transcript агента.",
            model=self.config.model_name
        )
    
    async def get_available_models(self) -> List[str]:
        return [self.config.model_name]