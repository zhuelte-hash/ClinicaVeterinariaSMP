from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/fullstack_app"
    secret_key: str = "supersecretkey_change_in_production_abc123xyz"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    app_name: str = "FullStack API"
    debug: bool = True

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
