from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    slack_bot_token: str = ""
    slack_app_token: str = ""
    slack_signing_secret: str = ""
    anthropic_api_key: str = ""
    database_url: str = "sqlite:///./crm.db"
    secret_key: str = "change-me-in-production"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = True
    web_base_url: str = "http://localhost:8000"
    slack_owner_user_id: str = ""   # Your Slack user ID (e.g. U01234ABCDE) for DM notifications
    digest_time: str = "09:00"      # UTC time for daily digest (HH:MM)


@lru_cache
def get_settings() -> Settings:
    return Settings()
