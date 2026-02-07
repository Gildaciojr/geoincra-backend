# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"

    # =========================================================
    # DATABASE
    # =========================================================
    DATABASE_URL: str

    # =========================================================
    # SECURITY (JWT)
    # =========================================================
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # =========================================================
    # Mapbox
    # =========================================================
    MAPBOX_TOKEN: str | None = None
    MAPBOX_STYLE_URL: str | None = None

    # =========================================================
    # CORS
    # =========================================================
    ALLOWED_ORIGINS: list[str] | str = []

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
