from typing import List, Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.storage.base import StorageStrategy
from app.repositories.message_repo import MessageRepository

class FileService:
    def __init__(self, db: AsyncSession, storage: StorageStrategy):
        self.db = db
        self.storage = storage
        self.message_repo = MessageRepository(db)
    
    async def upload_file(
        self,
        file: UploadFile,
        user_id: int,
        chat_id: Optional[int] = None
    ) -> str:
        """Загрузить файл и вернуть путь"""
        return await self.storage.save(file, user_id)
    
    async def delete_file(self, file_path: str, user_id: int) -> bool:
        """Удалить файл"""
        # Проверка прав (файл принадлежит пользователю)
        if not file_path.startswith(f"uploads/{user_id}/"):
            raise HTTPException(status_code=403, detail="Нет прав на удаление")
        
        return await self.storage.delete(file_path)
    
    async def get_user_files(self, user_id: int) -> List[dict]:
        """Получить список файлов пользователя"""
        messages = await self.message_repo.get_by_chat(0)  # Нужно доработать
        files = []
        for msg in messages:
            if msg.file_path and str(user_id) in msg.file_path:
                files.append({
                    "path": msg.file_path,
                    "message_id": msg.id,
                    "created_at": msg.created_at
                })
        return files