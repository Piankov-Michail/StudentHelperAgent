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
from app.security import encryptor  # Импорт утилиты расшифровки

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
    default_hf_token = getattr(settings, 'HUGGINGFACE_TOKEN', '')
    default_ollama_key = getattr(settings, 'OLLAMA_API_KEY', '')
    
    hf_token = default_hf_token
    ollama_key = default_ollama_key
    
    # Попытка получить токены пользователя
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserAPIKey).where(UserAPIKey.user_id == user_id)
        )
        keys = result.scalars().all()
        
        for key_record in keys:
            try:
                decrypted = encryptor.decrypt(key_record.encrypted_key)
                if key_record.service_name == "huggingface":
                    hf_token = decrypted
                elif key_record.service_name == "ollama":
                    ollama_key = decrypted
            except Exception:
                # Если расшифровка не удалась, оставляем дефолт
                pass
    
    return AgentConfig(
        model_name=settings.DEFAULT_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        api_key=ollama_key,
        hf_token=hf_token,  # Специфично для Whisper
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