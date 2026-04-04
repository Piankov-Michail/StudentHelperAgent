from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, update
from app.models import Message, Chat
from datetime import datetime

class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_chat(self, chat_id: int, include_deleted: bool = False) -> List[Message]:
        """Получить сообщения чата. По умолчанию исключает удалённые."""
        query = select(Message).where(Message.chat_id == chat_id)
        
        if not include_deleted:
            query = query.where(Message.is_deleted == False)
        
        query = query.order_by(Message.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_id(self, message_id: int) -> Optional[Message]:
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()
    
    async def create(
        self,
        chat_id: int,
        content: str,
        role: str,
        file_path: Optional[str] = None
    ) -> Message:
        message = Message(
            chat_id=chat_id,
            content=content,
            role=role,
            file_path=file_path
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message
    
    async def delete(self, message_id: int) -> bool:
        message = await self.get_by_id(message_id)
        if message:
            await self.db.delete(message)
            await self.db.commit()
            return True
        return False
    
    async def delete_by_chat(self, chat_id: int) -> int:
        result = await self.db.execute(
            delete(Message).where(Message.chat_id == chat_id)
        )
        await self.db.commit()
        return result.rowcount
    
    async def get_chat_history(self, chat_id: int, limit: int = 10) -> List[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_all_with_files(self) -> List[Message]:
        """Получить все сообщения с файлами (для очистки)"""
        result = await self.db.execute(
            select(Message).where(Message.file_path.isnot(None))
        )
        return list(result.scalars().all())
    
    async def delete_after(self, message_id: int) -> int:
        """Мягкое удаление всех сообщений после указанного (включая его)"""
        target_msg = await self.get_by_id(message_id)
        if not target_msg:
            return 0
        
        target_time = target_msg.created_at
        
        # Обновляем is_deleted вместо физического удаления
        result = await self.db.execute(
            update(Message)
            .where(
                Message.chat_id == target_msg.chat_id,
                Message.created_at >= target_time
            )
            .values(is_deleted=True)
        )
        await self.db.commit()
        return result.rowcount