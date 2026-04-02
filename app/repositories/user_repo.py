from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models import User, Chat, Message

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    async def create(self, username: str, hashed_password: str) -> User:
        user = User(username=username, hashed_password=hashed_password)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def delete(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if user:
            # Каскадное удаление должно сработать через relationship
            await self.db.delete(user)
            await self.db.commit()
            return True
        return False
    
    async def delete_with_cascade(self, user_id: int) -> bool:
        """Удалить пользователя со всеми данными"""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        # Удаляем сообщения через чаты
        chats_result = await self.db.execute(
            select(Chat.id).where(Chat.user_id == user_id)
        )
        chat_ids = [c[0] for c in chats_result.all()]
        
        if chat_ids:
            await self.db.execute(
                delete(Message).where(Message.chat_id.in_(chat_ids))
            )
        
        await self.db.execute(delete(Chat).where(Chat.user_id == user_id))
        await self.db.delete(user)
        await self.db.commit()
        return True