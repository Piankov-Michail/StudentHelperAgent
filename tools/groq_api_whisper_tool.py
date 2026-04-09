import os
import asyncio
import logging
import subprocess
from typing import Optional
from langchain_core.tools import tool
from groq import AsyncGroq
from app.database import async_session_maker
from sqlalchemy import select
from app.models import UserAPIKey
from app.security import encryptor

logger = logging.getLogger(__name__)

async def prepare_audio_for_api(input_path: str) -> str:
    """Асинхронно конвертирует аудио в Opus/OGG для минимального размера и быстрой обработки."""
    ext = os.path.splitext(input_path)[1].lower()
    output_path = input_path.rsplit('.', 1)[0] + "_tiny.ogg"
    
    # Если это уже легкий аудиофайл, можно пропустить (опционально)
    if ext == '.ogg' and os.path.getsize(input_path) < 25 * 1024 * 1024:
        return input_path

    command = [
        'ffmpeg', '-i', input_path,
        '-vn',                      # Отключаем видео
        '-acodec', 'libopus',       # Самый быстрый и эффективный кодек для речи
        '-b:a', '16k',              # Экстремально низкий битрейт (файл будет ~12-14МБ за 2 часа)
        '-vbr', 'on',               # Переменный битрейт для сохранения четкости речи
        '-compression_level', '0',  # Минимальная нагрузка на CPU (макс. скорость)
        '-ar', '16000',             # Родная частота для Whisper
        '-ac', '1',                 # Моно (в 2 раза меньше данных)
        '-y', output_path
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.communicate()
        
        if process.returncode != 0:
            logger.warning(f"Ошибка FFmpeg при конвертации, используем исходный файл")
            return input_path
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка FFmpeg: {e}")
        return input_path  # Возвращаем исходник, если сжатие не вышло
        
    return output_path

# Внутренняя реализация для прямого вызова
async def _transcribe_groq_impl(video_path: str, user_id: Optional[int] = None) -> str:
    """Внутренняя реализация транскрибации через Groq API"""
    logger.info(f"🎤 Groq транскрибация: {video_path}, user_id={user_id}")
    
    if not os.path.exists(video_path):
        return "Ошибка: Файл не найден."

    # Получение токена
    groq_token = None
    if user_id:
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(UserAPIKey).where(
                        UserAPIKey.user_id == user_id,
                        UserAPIKey.service_name == "groq"
                    )
                )
                key_record = result.scalar_one_or_none()
                if key_record:
                    groq_token = encryptor.decrypt(key_record.encrypted_key)
        except Exception as e:
            logger.warning(f"Ошибка получения токена: {e}")

    if not groq_token:
        groq_token = os.getenv("GROQ_API_KEY", "")
        if not groq_token:
            return "Ошибка: Не указан токен Groq API."

    compressed_audio_path = None
    try:
        # 1. Извлекаем и сжимаем аудио в Opus/OGG
        logger.info("Сжатие аудио через FFmpeg (Opus/OGG)...")
        compressed_audio_path = await prepare_audio_for_api(video_path)
        
        # 2. Проверяем размер после сжатия
        file_size = os.path.getsize(compressed_audio_path)
        if file_size > 25 * 1024 * 1024:
            return f"Ошибка: Даже после сжатия файл слишком большой ({file_size / 1024 / 1024:.1f}MB). Максимум 25MB."

        # 3. Отправляем на Groq API
        client = AsyncGroq(api_key=groq_token, timeout=180.0)  # 60 секунд timeout
        logger.info("Отправка аудио на Groq API...")
        
        with open(compressed_audio_path, "rb") as file:
            transcription = await client.audio.transcriptions.create(
                file=(os.path.basename(compressed_audio_path), file.read()),
                model="whisper-large-v3-turbo",
                temperature=0,
                response_format="verbose_json",
            )
        
        text = transcription.text if hasattr(transcription, "text") else str(transcription)
        return text if text.strip() else "⚠️ Аудио не содержит речи"

    except Exception as e:
        logger.error(f"❌ Ошибка транскрибации Groq: {e}")
        error_msg = str(e)
        
        # Более информативные сообщения об ошибках
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            return "Ошибка: Groq API не ответил вовремя (timeout). Попробуйте файл меньшего размера или используйте HuggingFace."
        elif "403" in error_msg or "Forbidden" in error_msg:
            return "Ошибка: Groq API отклонил запрос (403 Forbidden). Проверьте корректность API ключа или попробуйте позже."
        elif "401" in error_msg or "Unauthorized" in error_msg:
            return "Ошибка: Неверный Groq API ключ. Проверьте токен в настройках."
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return "Ошибка: Превышен лимит запросов Groq API. Попробуйте позже."
        else:
            return f"Ошибка при обработке через Groq API: {error_msg[:150]}"
        
    finally:
        # Удаляем временный файл
        if compressed_audio_path and compressed_audio_path != video_path and os.path.exists(compressed_audio_path):
            try:
                os.remove(compressed_audio_path)
                logger.info("🗑 Временный аудиофайл удален.")
            except Exception as cleanup_error:
                logger.warning(f"Не удалось удалить временный файл {compressed_audio_path}: {cleanup_error}")


def create_transcribe_video_groq_tool(user_id: Optional[int] = None):
    @tool("transcribe_video_groq")
    async def transcribe_video_groq(video_path: str) -> str:
        """Транскрибация видео/аудио через Groq API Whisper (с предварительным сжатием в Opus/OGG)."""
        return await _transcribe_groq_impl(video_path, user_id)

    return transcribe_video_groq

# Функция для прямого вызова без LangChain
async def transcribe_video_groq_direct(video_path: str, user_id: Optional[int] = None) -> str:
    """Прямой вызов транскрибации через Groq без LangChain wrapper"""
    return await _transcribe_groq_impl(video_path, user_id)

transcribe_video_groq = create_transcribe_video_groq_tool(user_id=None)
