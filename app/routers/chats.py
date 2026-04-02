from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.chat_service import ChatService
from app.dependencies import get_storage, get_agent

router = APIRouter(prefix="/chats", tags=["Chats"])

@router.get("/")
async def get_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить список чатов - не нужен agent/storage"""
    from app.repositories.chat_repo import ChatRepository
    repo = ChatRepository(db)
    chats = await repo.get_all(current_user.id)
    return chats

@router.post("/")
async def create_chat(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать чат - не нужен agent/storage"""
    from app.repositories.chat_repo import ChatRepository
    repo = ChatRepository(db)
    chat = await repo.create("Новый чат", current_user.id)
    return chat

@router.get("/{chat_id}")
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить чат с сообщениями - не нужен agent/storage"""
    from app.repositories.chat_repo import ChatRepository
    repo = ChatRepository(db)
    chat = await repo.get_by_id_with_messages(chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return {
        "chat": chat,
        "messages": chat.messages
    }

@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage = Depends(get_storage)
):
    """Удалить чат - нужен storage для удаления файлов"""
    from app.repositories.chat_repo import ChatRepository
    from app.repositories.message_repo import MessageRepository
    
    chat_repo = ChatRepository(db)
    message_repo = MessageRepository(db)
    
    messages = await message_repo.get_by_chat(chat_id)
    for msg in messages:
        if msg.file_path:
            await storage.delete(msg.file_path)
    
    deleted = await chat_repo.delete(chat_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return {"message": "Чат удалён"}

@router.post("/{chat_id}/message")
async def send_message(
    chat_id: int,
    text: str = Form(...),
    file: Optional[UploadFile] = File(None),
    agent_type: str = Form("transcript"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage = Depends(get_storage)
):
    from app.dependencies import get_agent
    from app.services.chat_service import ChatService
    
    agent = await get_agent(current_user.id, agent_type)
    service = ChatService(db, storage, agent, user_id=current_user.id, chat_id=chat_id)
    answer = await service.process_message(chat_id, current_user.id, text, file)
    return {"answer": answer, "status": "success", "agent_type": agent_type}