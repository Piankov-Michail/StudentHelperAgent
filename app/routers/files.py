from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.file_service import FileService
from app.dependencies import get_storage

router = APIRouter(prefix="/files", tags=["Files"])

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage = Depends(get_storage)
):
    service = FileService(db, storage)
    file_path = await service.upload_file(file, current_user.id)
    return {"file_path": file_path, "filename": file.filename}

@router.delete("/{file_path:path}")
async def delete_file(
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage = Depends(get_storage)
):
    service = FileService(db, storage)
    success = await service.delete_file(file_path, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Файл не найден")
    return {"message": "Файл удалён"}