import os
import asyncio
import logging
import mimetypes
from typing import Optional
from langchain_core.tools import tool
from huggingface_hub import AsyncInferenceClient
from app.database import async_session_maker
from sqlalchemy import select
from app.models import UserAPIKey
from app.security import encryptor

logger = logging.getLogger(__name__)

# Принудительно регистрируем mp3, чтобы HF API точно распознал его как audio/mpeg
mimetypes.add_type('audio/mpeg', '.mp3')

async def prepare_audio_async(input_path: str) -> str:
    """Асинхронно извлекает аудио и сжимает его в mp3 через ffmpeg."""
    base, _ = os.path.splitext(input_path)
    output_path = f"{base}_compressed.mp3"
    
    # Конвертируем в 16kHz, mono, 32kbps mp3 (идеально для Whisper)
    command =[
        'ffmpeg', '-i', input_path,
        '-vn',                    # Игнорировать видео
        '-acodec', 'libmp3lame',  # Кодировать в MP3
        '-ar', '16000',           # Частота дискретизации 16kHz
        '-ac', '1',               # Один канал (моно)
        '-b:a', '32k',            # Битрейт 32k
        '-y', output_path         # Перезаписать файл, если есть
    ]
    
    # Запускаем ffmpeg асинхронно, чтобы не блокировать event loop
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    
    await process.communicate()
    
    if process.returncode != 0 or not os.path.exists(output_path):
        raise RuntimeError("Ошибка при конвертации/извлечении аудио через FFmpeg")
        
    return output_path

# Внутренняя реализация для прямого вызова
async def _transcribe_impl(video_path: str, user_id: Optional[int] = None) -> str:
    """Внутренняя реализация транскрибации"""
    logger.info(f"🎤 Транскрибация: {video_path}, user_id={user_id}")
    
    if not os.path.exists(video_path):
        return "Ошибка: Файл не найден."

    # Получение токена
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
            logger.warning(f"Ошибка получения токена: {e}")

    if not hf_token:
        hf_token = os.getenv("HUGGINGFACE_TOKEN", "")
        if not hf_token:
            return "Ошибка: Не указан токен Hugging Face."

    compressed_audio_path = None
    try:
        # 1. Извлекаем и сжимаем аудио
        logger.info("Сжатие аудио через FFmpeg...")
        compressed_audio_path = await prepare_audio_async(video_path)
        
        # 2. Проверяем размер после сжатия
        file_size = os.path.getsize(compressed_audio_path)
        if file_size > 25 * 1024 * 1024:
            return f"Ошибка: Даже после сжатия файл слишком большой ({file_size / 1024 / 1024:.1f}MB). Максимум 25MB."

        # 3. Отправляем на Hugging Face
        client = AsyncInferenceClient(token=hf_token)
        logger.info("Отправка сжатого аудио на Hugging Face...")
        
        transcription = await client.automatic_speech_recognition(
            compressed_audio_path, 
            model="openai/whisper-large-v3-turbo"
        )
        
        text = transcription.text if hasattr(transcription, "text") else transcription
        return text if text.strip() else "⚠️ Аудио не содержит речи"

    except Exception as e:
        logger.error(f"❌ Ошибка транскрибации: {e}")
        return f"Ошибка при обработке: {str(e)[:150]}"
        
    finally:
        # Удаляем временный файл
        if compressed_audio_path and os.path.exists(compressed_audio_path):
            try:
                os.remove(compressed_audio_path)
                logger.info("🗑 Временный аудиофайл удален.")
            except Exception as cleanup_error:
                logger.warning(f"Не удалось удалить временный файл {compressed_audio_path}: {cleanup_error}")


def create_transcribe_video_hf_tool(user_id: Optional[int] = None):
    @tool("transcribe_video")
    async def transcribe_video_hf(video_path: str) -> str:
        """Транскрибация видео/аудио через Hugging Face Inference API (с предварительным сжатием)."""
        return await _transcribe_impl(video_path, user_id)

    return transcribe_video_hf

# Функция для прямого вызова без LangChain
async def transcribe_video_direct(video_path: str, user_id: Optional[int] = None) -> str:
    """Прямой вызов транскрибации без LangChain wrapper"""
    return await _transcribe_impl(video_path, user_id)

transcribe_video_hf = create_transcribe_video_hf_tool(user_id=None)