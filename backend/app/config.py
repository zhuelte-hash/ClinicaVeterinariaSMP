from functools import lru_cache
from decimal import Decimal
from pathlib import Path

from pydantic import Field
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
    purchase_whatsapp_number: str = ""
    purchase_delivery_cost: Decimal = Field(default=Decimal("10.00"), ge=0, max_digits=12, decimal_places=2)
    purchase_yape_holder: str = ""
    purchase_yape_phone: str = ""
    purchase_yape_qr_url: str = ""
    purchase_plin_holder: str = ""
    purchase_plin_phone: str = ""
    purchase_plin_qr_url: str = ""
    frontend_url: str = "http://localhost:4200"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    smtp_ssl: bool = False
    mail_from: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = ""
    login_lock_minutes: int = Field(default=15, ge=1, le=1440)

@lru_cache
def get_settings() -> Settings:
    return Settings()
