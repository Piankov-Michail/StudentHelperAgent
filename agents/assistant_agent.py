from typing import List, Dict, Any
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from .base import BaseAgent, AgentConfig, AgentResult

class AssistantAgent(BaseAgent):
    """Простой чат-агент без инструментов"""
    
    @property
    def name(self) -> str:
        return "assistant"
    
    @property
    def description(self) -> str:
        return "Обычный чат-помощник для ответов на вопросы"
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.llm = ChatOllama(
            base_url=config.base_url,
            model=config.model_name,
            temperature=config.temperature
        )
    
    async def process(self, message: str, context: Dict[str, Any]) -> AgentResult:
        system_prompt = """Ты — полезный ассистент. Отвечай подробно и структурированно.
        Если пользователь спрашивает о видео/аудио файлах — объясни, что для работы с ними 
        нужно выбрать агента 'Транскрайбер'."""
        
        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ])
        
        return AgentResult(
            output=response.content,
            model=self.config.model_name,
            metadata={"agent_type": "assistant", "tools_used": []}
        )
    
    async def get_available_models(self) -> List[str]:
        return [self.config.model_name]