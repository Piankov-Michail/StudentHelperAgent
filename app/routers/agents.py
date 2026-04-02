from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user
from app.models import User
from agents.factory import AgentFactory
from agents.base import AgentConfig
from app.config import settings

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("/")
async def get_available_agents(current_user: User = Depends(get_current_user)):
    """Получить список доступных агентов"""
    agents = []
    for agent_type in AgentFactory.get_available_types():
        # Создаём временный экземпляр для получения описания
        config = AgentConfig(
            model_name=settings.OLLAMA_BASE_URL.split("/")[-1] or "llama3",
            base_url=settings.OLLAMA_BASE_URL
        )
        try:
            agent = AgentFactory.create(agent_type, config)
            agents.append({
                "type": agent_type,
                "name": agent.name,
                "description": agent.description
            })
        except Exception:
            pass
    return agents

@router.get("/{agent_type}/models")
async def get_agent_models(
    agent_type: str,
    current_user: User = Depends(get_current_user)
):
    """Получить доступные модели для агента"""
    config = AgentConfig(
        model_name="llama3",
        base_url=settings.OLLAMA_BASE_URL
    )
    agent = AgentFactory.create(agent_type, config)
    models = await agent.get_available_models()
    return {"models": models}