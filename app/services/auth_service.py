from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.user_repo import UserRepository
from app.auth import get_password_hash, verify_password, create_access_token
from app.config import settings
from datetime import timedelta

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
    
    async def register(self, username: str, password: str):
        # Проверка существования
        existing = await self.user_repo.get_by_username(username)
        if existing:
            raise HTTPException(status_code=400, detail="Пользователь уже существует")
        
        # Создание
        hashed = get_password_hash(password)
        return await self.user_repo.create(username, hashed)
    
    async def login(self, username: str, password: str) -> dict:
        user = await self.user_repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return {"access_token": token, "token_type": "bearer"}
    
    async def delete_account(self, user_id: int) -> bool:
        return await self.user_repo.delete_with_cascade(user_id)