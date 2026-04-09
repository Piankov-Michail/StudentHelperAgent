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
    
    # Neo4j settings
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "your_neo4j_password_here"
    
    # NVIDIA API for embeddings
    NVIDIA_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()