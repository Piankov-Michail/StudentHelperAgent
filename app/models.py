from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class AgentType(str, enum.Enum):
    ASSISTANT = "assistant"
    TRANSCRIPT = "transcript"
    RAG = "rag"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    api_keys = relationship("UserAPIKey", back_populates="user", cascade="all, delete-orphan")

class UserAPIKey(Base):
    __tablename__ = "user_api_keys"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_name = Column(String(50), nullable=False)  # "ollama", "huggingface", "openai"
    encrypted_key = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user = relationship("User", back_populates="api_keys")

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), default="Новый чат")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_type = Column(Enum(AgentType), default=AgentType.TRANSCRIPT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at", lazy="selectin")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    file_path = Column(String(500), nullable=True)
    processing_steps = Column(Text, nullable=True)  # JSON с шагами обработки
    is_deleted = Column(Boolean, default=False, nullable=False)  # Мягкое удаление
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    chat = relationship("Chat", back_populates="messages")