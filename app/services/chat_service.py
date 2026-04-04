from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException
from app.repositories.chat_repo import ChatRepository
from app.repositories.message_repo import MessageRepository
from app.storage.base import StorageStrategy
from agents.base import BaseAgent, AgentResult

from app.routers.ws import send_progress, send_token

class ChatService:
    def __init__(
        self,
        db: AsyncSession,
        storage: StorageStrategy,
        agent: BaseAgent,
        user_id: int = None,
        chat_id: int = None
    ):
        self.db = db
        self.storage = storage
        self.agent = agent
        self.chat_repo = ChatRepository(db)
        self.message_repo = MessageRepository(db)
        self.user_id = user_id
        self.chat_id = chat_id
    
    async def get_chats(self, user_id: int) -> List:
        return await self.chat_repo.get_all(user_id)
    
    async def get_chat(self, chat_id: int, user_id: int) -> dict:
        chat = await self.chat_repo.get_by_id_with_messages(chat_id, user_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Чат не найден")
        return {
            "chat": chat,
            "messages": chat.messages
        }
    
    async def create_chat(self, title: str, user_id: int):
        return await self.chat_repo.create(title, user_id)
    
    async def process_message(
        self,
        chat_id: int,
        user_id: int,
        content: str,
        file: Optional[UploadFile] = None
    ) -> dict:
        # Проверка существования чата
        chat = await self.chat_repo.get_by_id(chat_id, user_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Чат не найден")
        
        file_path = None
        
        # ✅ Отправляем прогресс: загрузка файла
        if file:
            await send_progress(user_id, chat_id, 1, 4, "📁 Загрузка файла...", "processing")
            file_path = await self.storage.save(file, user_id)
        
        # Сохранение сообщения пользователя
        user_message = await self.message_repo.create(
            chat_id=chat_id,
            content=content,
            role="user",
            file_path=file_path
        )
        
        # Подготовка запроса к агенту
        query = content
        if file_path:
            query += f" (Файл: {file_path})"
        
        # Контекст для агента (включая историю чата без удалённых сообщений)
        chat_history = await self.message_repo.get_by_chat(chat_id, include_deleted=False)
        
        context = {
            "chat_id": chat_id,
            "user_id": user_id,
            "file_path": file_path,
            "message_count": await self.chat_repo.get_message_count(chat_id),
            "chat_history": chat_history,
            "send_progress": lambda step, msg: send_progress(user_id, chat_id, step, 4, msg, "processing")
        }
        
        # ✅ Отправляем прогресс: транскрибация
        await send_progress(user_id, chat_id, 2, 4, "🔊 Транскрибация аудио...", "processing")
        
        # Запрос к агенту
        result: AgentResult = await self.agent.process(query, context)
        
        # ✅ Отправляем прогресс: анализ
        await send_progress(user_id, chat_id, 3, 4, "📝 Анализ транскрипции...", "processing")
        
        # Сохранение ответа
        assistant_message = await self.message_repo.create(
            chat_id=chat_id,
            content=result.output,
            role="assistant"
        )
        
        # ✅ Отправляем прогресс: завершено
        await send_progress(user_id, chat_id, 4, 4, "✨ Готово!", "completed")
        
        # Обновление заголовка если это первое сообщение
        msg_count = await self.chat_repo.get_message_count(chat_id)
        if msg_count <= 2:
            await self.chat_repo.update_title(chat_id, content[:50])
        
        return {
            "output": result.output,
            "user_message_id": user_message.id,
            "assistant_message_id": assistant_message.id
        }

    async def process_message_stream(
        self,
        chat_id: int,
        user_id: int,
        content: str,
        file: Optional[UploadFile] = None
    ) -> dict:
        """Streaming версия process_message"""
        # Проверка существования чата
        chat = await self.chat_repo.get_by_id(chat_id, user_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Чат не найден")
        
        file_path = None
        
        # Загрузка файла
        if file:
            await send_progress(user_id, chat_id, 1, 3, "📁 Загрузка файла...", "processing")
            file_path = await self.storage.save(file, user_id)
        
        # Сохранение сообщения пользователя
        user_message = await self.message_repo.create(
            chat_id=chat_id,
            content=content,
            role="user",
            file_path=file_path
        )
        
        # Подготовка запроса к агенту
        query = content
        if file_path:
            query += f" (Файл: {file_path})"
        
        # Контекст для агента (включая историю чата без удалённых сообщений)
        chat_history = await self.message_repo.get_by_chat(chat_id, include_deleted=False)
        
        context = {
            "chat_id": chat_id,
            "user_id": user_id,
            "file_path": file_path,
            "message_count": await self.chat_repo.get_message_count(chat_id),
            "chat_history": chat_history
        }
        
        # Проверяем, поддерживает ли агент streaming
        full_response = ""
        if hasattr(self.agent, 'process_stream'):
            async for chunk in self.agent.process_stream(query, context):
                if chunk["type"] == "token":
                    await send_token(user_id, chat_id, chunk["content"])
                elif chunk["type"] == "complete":
                    full_response = chunk["content"]
        else:
            # Fallback на обычный метод
            result: AgentResult = await self.agent.process(query, context)
            full_response = result.output
        
        # Сохранение ответа
        assistant_message = await self.message_repo.create(
            chat_id=chat_id,
            content=full_response,
            role="assistant"
        )
        
        # Обновление заголовка если это первое сообщение
        msg_count = await self.chat_repo.get_message_count(chat_id)
        if msg_count <= 2:
            await self.chat_repo.update_title(chat_id, content[:50])
        
        return {
            "output": full_response,
            "user_message_id": user_message.id,
            "assistant_message_id": assistant_message.id
        }

    async def delete_chat(self, chat_id: int, user_id: int):
        # Получаем сообщения для удаления файлов
        messages = await self.message_repo.get_by_chat(chat_id)
        
        # Удаляем файлы
        for msg in messages:
            if msg.file_path:
                await self.storage.delete(msg.file_path)
        
        # Удаляем чат (сообщения удалятся каскадом)
        deleted = await self.chat_repo.delete(chat_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Чат не найден")