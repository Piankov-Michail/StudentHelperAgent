from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from app.models import Chat, Message
from datetime import datetime

class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, chat_id: int, user_id: int) -> Optional[Chat]:
        result = await self.db.execute(
            select(Chat)
            .where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id_with_messages(self, chat_id: int, user_id: int) -> Optional[Chat]:
        result = await self.db.execute(
            select(Chat)
            .options(selectinload(Chat.messages))
            .where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, user_id: int) -> List[Chat]:
        result = await self.db.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.updated_at.desc())
        )
        return list(result.scalars().all())
    
    async def create(self, title: str, user_id: int) -> Chat:
        chat = Chat(title=title, user_id=user_id)
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        return chat
    
    async def update_title(self, chat_id: int, title: str) -> Optional[Chat]:
        chat = await self.get_by_id(chat_id, 0)  # user_id проверять в сервисе
        if chat:
            chat.title = title
            chat.updated_at = func.now()
            await self.db.commit()
            await self.db.refresh(chat)
        return chat
    
    async def delete(self, chat_id: int, user_id: int) -> bool:
        chat = await self.get_by_id(chat_id, user_id)
        if chat:
            await self.db.delete(chat)
            await self.db.commit()
            return True
        return False
    
    async def get_message_count(self, chat_id: int) -> int:
        result = await self.db.execute(
            select(func.count(Message.id)).where(Message.chat_id == chat_id)
        )
        return result.scalar() or 0