import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException
from .base import StorageStrategy

class LocalStorage(StorageStrategy):
    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.max_size = 300 * 1024 * 1024  # 100MB
        self.allowed_extensions = {
            '.mp4', '.avi', '.mov', '.mkv', '.webm',
            '.mp3', '.wav', '.m4a', '.flac', '.ogg'
        }
    
    async def save(self, file: UploadFile, user_id: int) -> str:
        # Проверка размера
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > self.max_size:
            raise HTTPException(400, f"Файл слишком большой (макс. {self.max_size // 1024 // 1024}MB)")
        
        # Проверка расширения
        ext = Path(file.filename).suffix.lower()
        if ext not in self.allowed_extensions:
            raise HTTPException(400, "Неподдерживаемый формат файла")
        
        # Сохранение
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(exist_ok=True)
        
        file_id = uuid.uuid4().hex
        file_path = user_dir / f"{file_id}{ext}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return str(file_path)
    
    async def delete(self, file_path: str) -> bool:
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                # Очистка пустых директорий
                try:
                    path.parent.rmdir()
                except OSError:
                    pass
            return True
        except Exception:
            return False
    
    async def exists(self, file_path: str) -> bool:
        return Path(file_path).exists()
    
    async def get_url(self, file_path: str) -> str:
        return f"/static/{file_path}"