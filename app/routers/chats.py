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
    
    # Serialize messages with IDs
    messages_data = []
    for msg in chat.messages:
        messages_data.append({
            "id": msg.id,
            "content": msg.content,
            "role": msg.role,
            "file_path": msg.file_path,
            "created_at": msg.created_at
        })
    
    return {
        "chat": {
            "id": chat.id,
            "title": chat.title,
            "user_id": chat.user_id,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at
        },
        "messages": messages_data
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
    result = await service.process_message(chat_id, current_user.id, text, file)
    return {
        "answer": result["output"],
        "user_message_id": result["user_message_id"],
        "assistant_message_id": result["assistant_message_id"],
        "status": "success",
        "agent_type": agent_type
    }

@router.delete("/{chat_id}/messages/{message_id}")
async def delete_messages_after(
    chat_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage = Depends(get_storage)
):
    """Удалить сообщение и все последующие"""
    from app.repositories.chat_repo import ChatRepository
    from app.repositories.message_repo import MessageRepository
    
    # Проверка прав на чат
    chat_repo = ChatRepository(db)
    chat = await chat_repo.get_by_id(chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    message_repo = MessageRepository(db)
    
    # Удаляем файлы перед удалением сообщений
    messages_to_delete = await message_repo.get_by_chat(chat_id)
    target_msg = await message_repo.get_by_id(message_id)
    if target_msg and target_msg.chat_id == chat_id:
        target_time = target_msg.created_at
        for msg in messages_to_delete:
            if msg.created_at >= target_time and msg.file_path:
                await storage.delete(msg.file_path)
        
        deleted_count = await message_repo.delete_after(message_id)
        return {"message": f"Удалено {deleted_count} сообщений", "deleted_count": deleted_count}
    
    raise HTTPException(status_code=404, detail="Сообщение не найдено")

@router.post("/{chat_id}/retry/{message_id}")
async def retry_message(
    chat_id: int,
    message_id: int,
    agent_type: str = Form("transcript"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage = Depends(get_storage)
):
    """Повторить запрос - удалить все сообщения после указанного и повторить обработку"""
    from app.dependencies import get_agent
    from app.services.chat_service import ChatService
    from app.repositories.message_repo import MessageRepository
    
    # Проверка прав на чат
    from app.repositories.chat_repo import ChatRepository
    chat_repo = ChatRepository(db)
    chat = await chat_repo.get_by_id(chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    message_repo = MessageRepository(db)
    target_msg = await message_repo.get_by_id(message_id)
    if not target_msg or target_msg.chat_id != chat_id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    
    # Удаляем все сообщения после указанного
    deleted_count = await message_repo.delete_after(message_id)
    
    # Получаем текст сообщения для повторного запроса
    content = target_msg.content
    
    # Создаём сервис и обрабатываем
    agent = await get_agent(current_user.id, agent_type)
    service = ChatService(db, storage, agent, user_id=current_user.id, chat_id=chat_id)
    result = await service.process_message(chat_id, current_user.id, content, None)
    
    return {
        "answer": result["output"],
        "user_message_id": result["user_message_id"],
        "assistant_message_id": result["assistant_message_id"],
        "status": "success",
        "agent_type": agent_type,
        "deleted_messages": deleted_count
    }