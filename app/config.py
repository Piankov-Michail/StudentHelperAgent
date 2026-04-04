from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://videos_agent:password@localhost:5432/videos_agent"
    JWT_SECRET: str = "change_this_secret_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30
    OLLAMA_BASE_URL: str = "https://ollama.com"
    OLLAMA_API_KEY: str = ""
    DEFAULT_MODEL: str = "gpt-oss:20b-cloud"
    ENCRYPTION_KEY: str = ""
    HUGGINGFACE_TOKEN: str = ""
    OLLAMA_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()