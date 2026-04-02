from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

class StorageStrategy(ABC):
    """Стратегия хранения файлов (DIP)"""
    
    @abstractmethod
    async def save(self, file: UploadFile, user_id: int) -> str:
        """Сохранить файл, вернуть путь"""
        pass
    
    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """Удалить файл"""
        pass
    
    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Проверить существование"""
        pass
    
    @abstractmethod
    async def get_url(self, file_path: str) -> str:
        """Получить URL для доступа"""
        pass