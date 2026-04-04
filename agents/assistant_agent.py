from typing import List, Dict, Any
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
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
        
        # Получаем историю чата из контекста
        chat_history = context.get("chat_history", [])
        
        # Формируем сообщения с учётом истории
        messages = [SystemMessage(content=system_prompt)]
        
        # Добавляем историю чата (только неудалённые сообщения)
        for msg in chat_history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        # Добавляем текущее сообщение
        messages.append(HumanMessage(content=message))
        
        response = await self.llm.ainvoke(messages)
        
        return AgentResult(
            output=response.content,
            model=self.config.model_name,
            metadata={"agent_type": "assistant", "tools_used": []}
        )
    
    async def process_stream(self, message: str, context: Dict[str, Any]):
        """Streaming версия process - возвращает async generator с токенами и полным ответом"""
        system_prompt = """Ты — полезный ассистент. Отвечай подробно и структурированно.
        Если пользователь спрашивает о видео/аудио файлах — объясни, что для работы с ними 
        нужно выбрать агента 'Транскрайбер'."""
        
        # Получаем историю чата из контекста
        chat_history = context.get("chat_history", [])
        
        # Формируем сообщения с учётом истории
        messages = [SystemMessage(content=system_prompt)]
        
        # Добавляем историю чата (только неудалённые сообщения)
        for msg in chat_history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        # Добавляем текущее сообщение
        messages.append(HumanMessage(content=message))
        
        full_response = ""
        async for chunk in self.llm.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                full_response += chunk.content
                yield {"type": "token", "content": chunk.content}
        
        # В конце отправляем полный ответ
        yield {"type": "complete", "content": full_response}
    
    async def get_available_models(self) -> List[str]:
        return [self.config.model_name]