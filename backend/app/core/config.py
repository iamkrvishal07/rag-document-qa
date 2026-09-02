from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GOOGLE_API_KEY: str

    REDIS_URL: str = "redis://localhost:6379/0"
    FRONTEND_ORIGIN: str = (
        "http://localhost:5173"
    )

    MAX_UPLOAD_SIZE_MB: int = 5

    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    SIMILARITY_THRESHOLD: float = 0.6
    RETRIEVAL_TOP_K: int = 5
    SESSION_EXPIRY_SECONDS: int = 3600
    UPLOAD_DIR: str = "./uploads"

    EMBEDDING_MODEL: str = "gemini-embedding-2"
    CHROMA_DIR: str = "./chroma_db"
    LLM_MODEL: str = "gemini-3.6-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
