from typing import Dict, Type
from .base import BaseAgent, AgentConfig
from .transcript_agent import TranscriptAgent
from .assistant_agent import AssistantAgent
from .rag_agent import RAGAgent

class AgentFactory:
    _registry: Dict[str, Type[BaseAgent]] = {}
    
    @classmethod
    def register(cls, name: str, agent_class: Type[BaseAgent]):
        cls._registry[name] = agent_class
    
    @classmethod
    def create(cls, agent_type: str, config: AgentConfig) -> BaseAgent:
        if agent_type not in cls._registry:
            raise ValueError(f"Неизвестный тип агента: {agent_type}")
        return cls._registry[agent_type](config)
    
    @classmethod
    def get_available_types(cls) -> list:
        return list(cls._registry.keys())
    
    @classmethod
    def get_agent_info(cls, agent_type: str) -> dict:
        if agent_type not in cls._registry:
            return None
        # Временный экземпляр для получения информации
        config = AgentConfig(model_name="gpt-oss:20b-cloud", base_url="http://localhost:11434")
        agent = cls._registry[agent_type](config)
        return {
            "type": agent_type,
            "name": agent.name,
            "description": agent.description
        }

# Регистрация
AgentFactory.register("transcript", TranscriptAgent)
AgentFactory.register("assistant", AssistantAgent)
AgentFactory.register("rag", RAGAgent)