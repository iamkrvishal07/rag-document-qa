from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GOOGLE_API_KEY: str

    REDIS_URL: str = "redis://localhost:6379/0"

    MAX_UPLOAD_SIZE_MB: int = 5

    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    SIMILARITY_THRESHOLD: float = 0.7
    TOP_K: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()