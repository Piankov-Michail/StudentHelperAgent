from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user_by_token
from app.models import User
from typing import Dict, Set
import json
import asyncio

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Менеджер подключений
class ConnectionManager:
    def __init__(self):
        # user_id -> {chat_id -> WebSocket}
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int, chat_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][chat_id] = websocket
    
    def disconnect(self, user_id: int, chat_id: int):
        if user_id in self.active_connections:
            if chat_id in self.active_connections[user_id]:
                del self.active_connections[user_id][chat_id]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: int, chat_id: int):
        if user_id in self.active_connections:
            if chat_id in self.active_connections[user_id]:
                websocket = self.active_connections[user_id][chat_id]
                try:
                    await websocket.send_json(message)
                except:
                    self.disconnect(user_id, chat_id)
    
    def get_connection(self, user_id: int, chat_id: int) -> WebSocket | None:
        if user_id in self.active_connections:
            return self.active_connections[user_id].get(chat_id)
        return None

manager = ConnectionManager()

async def get_current_user_by_token(token: str, db: AsyncSession = Depends(get_db)) -> User:
    from jose import JWTError, jwt
    from app.config import settings
    from sqlalchemy import select
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.websocket("/progress/{chat_id}")
async def websocket_progress(
    websocket: WebSocket,
    chat_id: int,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint для прогресса обработки"""
    try:
        user = await get_current_user_by_token(token, db)
        
        # Проверка прав на чат
        from app.repositories.chat_repo import ChatRepository
        repo = ChatRepository(db)
        chat = await repo.get_by_id(chat_id, user.id)
        if not chat:
            await websocket.close(code=4003, reason="Chat not found")
            return
        
        # Подключаем
        await manager.connect(websocket, user.id, chat_id)
        
        # Отправляем подтверждение подключения
        await websocket.send_json({
            "type": "connected",
            "chat_id": chat_id,
            "message": "Подключено к прогрессу"
        })
        
        # Держим соединение живым
        try:
            while True:
                # Получаем данные от клиента (heartbeat)
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            manager.disconnect(user.id, chat_id)
        except Exception as e:
            manager.disconnect(user.id, chat_id)
            
    except HTTPException as e:
        await websocket.close(code=e.status_code, reason=e.detail)
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))

# Функция для отправки прогресса из chat_service
async def send_progress(user_id: int, chat_id: int, step: int, total_steps: int, message: str, status: str = "processing"):
    """Отправить обновление прогресса через WebSocket"""
    await manager.send_personal_message({
        "type": "progress",
        "step": step,
        "total_steps": total_steps,
        "message": message,
        "status": status,  # "processing", "completed", "error"
        "timestamp": asyncio.get_event_loop().time()
    }, user_id, chat_id)