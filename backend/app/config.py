from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://postgres:postgres@localhost:5432/fullstack_app"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    app_name: str = "FullStack API"
    debug: bool = True
    appointment_tolerance_minutes: int = 15
    appointment_worker_interval_seconds: int = 30
    booking_url: str = "http://localhost:4200/reservar-cita"
    whatsapp_api_url: str = "https://graph.facebook.com/v21.0"
    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_template_confirmed: str | None = None
    whatsapp_template_no_show: str | None = None

@lru_cache
def get_settings() -> Settings:
    return Settings()
