import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import select
from app.database import async_session_maker
from app.models import Message

class FileCleaner:
    def __init__(self, uploads_dir: str = "uploads", max_age_days: int = 7):
        self.uploads_dir = Path(uploads_dir)
        self.max_age = timedelta(days=max_age_days)
    
    async def cleanup_orphaned_files(self):
        async with async_session_maker() as session:
            result = await session.execute(
                select(Message.file_path).where(Message.file_path.isnot(None))
            )
            valid_paths = set(row[0] for row in result if row[0])
        
        if not self.uploads_dir.exists():
            return
        
        for file_path in self.uploads_dir.rglob("*"):
            if file_path.is_file():
                if str(file_path) not in valid_paths:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if datetime.now() - mtime > self.max_age:
                        file_path.unlink()
                        print(f"Удалён осиротевший файл: {file_path}")
    
    async def cleanup_old_files(self):
        cutoff = datetime.now() - self.max_age
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(Message).where(
                    Message.file_path.isnot(None),
                    Message.created_at < cutoff
                )
            )
            messages = result.scalars().all()
            
            for msg in messages:
                if msg.file_path and Path(msg.file_path).exists():
                    Path(msg.file_path).unlink()
                    msg.file_path = None
            
            await session.commit()

async def start_cleanup_scheduler():
    cleaner = FileCleaner()
    while True:
        await asyncio.sleep(3600)
        await cleaner.cleanup_orphaned_files()