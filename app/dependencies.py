from functools import lru_cache
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.storage.local import LocalStorage
from app.storage.base import StorageStrategy
from agents.factory import AgentFactory
from agents.base import AgentConfig
from app.database import async_session_maker
from app.models import UserAPIKey
from app.security import encryptor

import os

@lru_cache()
def get_storage() -> StorageStrategy:
    """Получить стратегию хранилища (синглтон)"""
    return LocalStorage()

async def get_agent_config_for_user(
    user_id: int,
    agent_type: str = "transcript"
) -> AgentConfig:
    """
    Получает конфигурацию агента с токенами конкретного пользователя из БД.
    """
    # Токены по умолчанию из .env (если у пользователя нет своих)
    default_ollama_key = getattr(settings, 'OLLAMA_API_KEY', '')
    default_nvidia_key = getattr(settings, 'NVIDIA_API_KEY', '')
    
    ollama_key = default_ollama_key
    nvidia_key = default_nvidia_key
    
    # Попытка получить токены пользователя
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserAPIKey).where(UserAPIKey.user_id == user_id)
        )
        keys = result.scalars().all()
        
        for key_record in keys:
            try:
                decrypted = encryptor.decrypt(key_record.encrypted_key)
                if key_record.service_name == "ollama":
                    ollama_key = decrypted
                elif key_record.service_name == "nvidia":
                    nvidia_key = decrypted
            except Exception:
                pass
    
    # Устанавливаем переменные окружения для использования в tools
    if ollama_key:
        os.environ["OLLAMA_API_KEY"] = ollama_key
    if nvidia_key:
        os.environ["NVIDIA_API_KEY"] = nvidia_key

    return AgentConfig(
        model_name=settings.DEFAULT_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        api_key=ollama_key,
        temperature=0.7
    )

async def get_agent(
    user_id: int,
    agent_type: str = "transcript"
):
    """
    Factory-функция для создания агента с конфигурацией пользователя.
    """
    config = await get_agent_config_for_user(user_id, agent_type)
    return AgentFactory.create(agent_type, config)