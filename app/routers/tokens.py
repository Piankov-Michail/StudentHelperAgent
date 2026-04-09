from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.token_service import TokenService

router = APIRouter(prefix="/tokens", tags=["API Tokens"])

class TokenRequest(BaseModel):
    service_name: str
    token: str

@router.get("/")
async def list_tokens(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = TokenService(db)
    return await service.list_tokens(current_user.id)

@router.post("/")
async def save_token(
    request: TokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if request.service_name not in ["huggingface", "ollama", "openai", "groq", "nvidia"]:
        raise HTTPException(status_code=400, detail="Неподдерживаемый сервис")
    if not request.token or len(request.token) < 10:
        raise HTTPException(status_code=400, detail="Некорректный токен")
    
    service = TokenService(db)
    return await service.save_token(current_user.id, request.service_name, request.token)

@router.delete("/{service_name}")
async def delete_token(
    service_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = TokenService(db)
    return await service.delete_token(current_user.id, service_name)