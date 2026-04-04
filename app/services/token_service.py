from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from fastapi import HTTPException
from app.models import UserAPIKey
from app.security import encryptor

class TokenService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def save_token(self, user_id: int, service_name: str, token: str):
        result = await self.db.execute(
            select(UserAPIKey)
            .where(UserAPIKey.user_id == user_id, UserAPIKey.service_name == service_name)
        )
        existing = result.scalar_one_or_none()
        
        encrypted = encryptor.encrypt(token)
        
        if existing:
            existing.encrypted_key = encrypted
            existing.updated_at = func.now()
        else:
            new_key = UserAPIKey(
                user_id=user_id,
                service_name=service_name,
                encrypted_key=encrypted
            )
            self.db.add(new_key)
        
        await self.db.commit()
        return {"service": service_name, "status": "saved"}
    
    async def get_token(self, user_id: int, service_name: str) -> str:
        result = await self.db.execute(
            select(UserAPIKey)
            .where(UserAPIKey.user_id == user_id, UserAPIKey.service_name == service_name)
        )
        record = result.scalar_one_or_none()
        
        if not record:
            return None
        
        return encryptor.decrypt(record.encrypted_key)
    
    async def delete_token(self, user_id: int, service_name: str):
        await self.db.execute(
            delete(UserAPIKey)
            .where(UserAPIKey.user_id == user_id, UserAPIKey.service_name == service_name)
        )
        await self.db.commit()
        return {"status": "deleted"}
    
    async def list_tokens(self, user_id: int) -> list:
        result = await self.db.execute(
            select(UserAPIKey)
            .where(UserAPIKey.user_id == user_id)
        )
        keys = result.scalars().all()
        return [
            {
                "service": k.service_name,
                "created_at": k.created_at,
                "has_value": bool(k.encrypted_key)
            }
            for k in keys
        ]