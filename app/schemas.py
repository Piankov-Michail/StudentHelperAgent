from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Auth
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Chat
class ChatCreate(BaseModel):
    title: Optional[str] = "Новый чат"

class ChatResponse(BaseModel):
    id: int
    title: str
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Message
class MessageCreate(BaseModel):
    content: str
    role: str
    file_path: Optional[str] = None

class MessageResponse(BaseModel):
    id: int
    content: str
    role: str
    file_path: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatWithMessages(BaseModel):
    chat: ChatResponse
    messages: List[MessageResponse]