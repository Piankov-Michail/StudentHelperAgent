from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class AgentConfig(BaseModel):
    """Конфигурация агента"""
    model_name: str
    base_url: str
    api_key: Optional[str] = None       # Для Ollama/OpenAI
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    custom_params: Dict[str, Any] = {}

class AgentResult(BaseModel):
    output: str
    tokens_used: int = 0
    model: str
    metadata: Dict[str, Any] = {}

class BaseAgent(ABC):
    """Базовый класс агента (OCP - открыт для расширения)"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.tools = []
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Имя агента"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Описание для UI"""
        pass
    
    @abstractmethod
    async def process(self, message: str, context: Dict[str, Any]) -> AgentResult:
        """Обработать сообщение"""
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Список доступных моделей"""
        pass
    
    def register_tool(self, tool):
        """Регистрация инструмента"""
        self.tools.append(tool)