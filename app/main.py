from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.database import init_db
from app.dependencies import get_storage, get_agent
from app.routers import auth, chats, agents, files, tokens, ws
import asyncio

app = FastAPI(title="Video AI Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Создаём директорию uploads перед монтированием
Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

Path("static").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Роуты
app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(agents.router)
app.include_router(files.router)
app.include_router(tokens.router)
app.include_router(ws.router)

@app.on_event("startup")
async def startup():
    await init_db()
    # Запуск очистителя в фоне
    # asyncio.create_task(start_cleanup_scheduler())

@app.get("/")
async def root():
    return FileResponse("static/index.html")