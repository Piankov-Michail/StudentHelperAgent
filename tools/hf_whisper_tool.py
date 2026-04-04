import os
import time
import logging
from typing import Optional
from langchain_core.tools import tool
from huggingface_hub import InferenceClient
from app.database import async_session_maker
from sqlalchemy import select
from app.models import UserAPIKey
from app.security import encryptor

logger = logging.getLogger(__name__)

def create_transcribe_video_hf_tool(user_id: Optional[int] = None):
    """
    Фабрика для создания инструмента транскрибации с привязанным user_id.
    """
    @tool("transcribe_video")
    async def transcribe_video_hf(video_path: str) -> str:
        """Транскрибация видео/аудио через Hugging Face Inference API."""
        logger.info(f"🎤 Транскрибация: {video_path}, user_id={user_id}")
        if not os.path.exists(video_path):
            logger.error(f"❌ Файл не найден: {video_path}")
            return "Ошибка: Файл не найден."

        # Проверка размера (HF API лимит ~25MB)
        file_size = os.path.getsize(video_path)
        logger.info(f"📦 Размер файла: {file_size / 1024 / 1024:.2f} MB")
        if file_size > 25 * 1024 * 1024:
            return f"Ошибка: Файл слишком большой ({file_size / 1024 / 1024:.1f}MB). Максимум 25MB."

        # Получаем токен пользователя из БД
        hf_token = None
        if user_id:
            try:
                async with async_session_maker() as session:
                    result = await session.execute(
                        select(UserAPIKey).where(
                            UserAPIKey.user_id == user_id,
                            UserAPIKey.service_name == "huggingface"
                        )
                    )
                    key_record = result.scalar_one_or_none()
                    if key_record:
                        hf_token = encryptor.decrypt(key_record.encrypted_key)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения токена из БД: {e}")

        # Фоллбэк на ENV
        if not hf_token:
            hf_token = os.getenv("HUGGINGFACE_TOKEN", "")
            if hf_token:
                logger.info("⚠️ Токен получен из ENV")
        
        if not hf_token:
            return "Ошибка: Не указан токен Hugging Face. Добавьте его в настройках (⚙️ в UI)."

        max_retries = 3
        base_delay = 2
        
        # Используем модель turbo:fastest для максимальной скорости
        model_id = "openai/whisper-large-v3-turbo:fastest"
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Попытка {attempt + 1}/{max_retries}")
                
                # Инициализация официального клиента
                client = InferenceClient(
                    provider="auto",
                    api_key=hf_token,
                    timeout=300
                )
                
                # Вызов транскрибации
                # client.automatic_speech_recognition принимает путь к файлу
                output = client.automatic_speech_recognition(
                    audio=video_path,
                    model=model_id
                )
                
                # Парсинг ответа
                if isinstance(output, dict) and "text" in output:
                    text = output["text"]
                    return text if text.strip() else "⚠️ Аудио не содержит речи"
                elif isinstance(output, str):
                    return output if output.strip() else "⚠️ Аудио не содержит речи"
                else:
                    return f"Неожиданный формат ответа: {type(output)}"

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"❌ Ошибка (попытка {attempt+1}): {error_msg}")
                
                # Проверка на сетевые ошибки и тайм-ауты для повтора
                if "IncompleteRead" in error_msg or "Connection" in error_msg or "timeout" in error_msg.lower() or "503" in error_msg:
                    if attempt < max_retries - 1:
                        wait = base_delay * (attempt + 1)
                        logger.info(f"⏳ Ждем {wait} сек...")
                        time.sleep(wait)
                        continue
                
                return f"Ошибка транскрибации: {error_msg[:150]}"

        return "Ошибка: Не удалось выполнить транскрибацию после нескольких попыток"

    return transcribe_video_hf

# Для совместимости
transcribe_video_hf = create_transcribe_video_hf_tool(user_id=None)