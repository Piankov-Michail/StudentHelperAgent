from langchain_core.tools import tool
import requests
import os
import time
from app.database import async_session_maker
from sqlalchemy import select
from app.models import UserAPIKey
from app.security import encryptor

@tool
async def transcribe_video_hf(video_path: str, user_id: int = None) -> str:
    '''Транскрибация видео/аудио через Hugging Face Inference API'''
    if not os.path.exists(video_path):
        return "Ошибка: Файл не найден."
    
    # Получаем токен пользователя
    hf_token = None
    if user_id:
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserAPIKey)
                .where(UserAPIKey.user_id == user_id, UserAPIKey.service_name == "huggingface")
            )
            key_record = result.scalar_one_or_none()
            if key_record:
                hf_token = encryptor.decrypt(key_record.encrypted_key)
    
    if not hf_token:
        hf_token = os.getenv("HUGGINGFACE_TOKEN", "")
    
    if not hf_token:
        return "Ошибка: Не указан токен Hugging Face. Добавьте его в настройках."
    
    # ✅ Retry-логика с экспоненциальной задержкой
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            with open(video_path, "rb") as f:
                data = f.read()
            
            # ✅ Проверка размера файла (макс 25MB для HF API)
            if len(data) > 25 * 1024 * 1024:
                return f"Ошибка: Файл слишком большой ({len(data) / 1024 / 1024:.1f}MB). Максимум 25MB для HF API."
            
            response = requests.post(
                "https://api-inference.huggingface.co/models/openai/whisper-large-v3",
                headers={
                    "Authorization": f"Bearer {hf_token}",
                    "Content-Type": "application/octet-stream"
                },
                data=data,
                timeout=300,
                stream=True  # ✅ Для больших файлов
            )
            
            # ✅ Обработка 503 (модель загружается)
            if response.status_code == 503:
                wait_time = response.json().get('estimated_time', 30)
                if attempt < max_retries - 1:
                    time.sleep(min(wait_time, 60))
                    continue
                return f"Ошибка: Модель не доступна. Попробуйте через {wait_time:.0f} сек."
            
            if response.status_code != 200:
                return f"Ошибка HF API: {response.status_code} - {response.text[:200]}"
            
            # ✅ Читаем ответ частями
            result = response.json()
            if isinstance(result, dict) and "text" in result:
                return result["text"]
            elif isinstance(result, list) and len(result) > 0:
                return " ".join([item.get("text", "") for item in result])
            else:
                return f"Неожиданный формат ответа: {result}"
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(base_delay * (attempt + 1))
                continue
            return "Ошибка: Превышено время ожидания транскрибации"
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                time.sleep(base_delay * (attempt + 1))
                continue
            return f"Ошибка соединения: {str(e)[:100]}. Попробуйте файл меньшего размера."
        except Exception as e:
            return f"Ошибка при обработке видео: {str(e)[:200]}"
    
    return "Ошибка: Не удалось выполнить транскрибацию после нескольких попыток"