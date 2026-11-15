"""Application configuration module using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for the multi-platform posting system."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application Settings
    app_name: str = "Automated Multi-Platform Posting System"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 4000
    debug: bool = False
    request_timeout_seconds: float = 10.0

    # Simulation / Mock Mode
    simulation_mode: bool = False

    # 1. Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_channel_username: Optional[str] = None

    # 2. Discord
    discord_webhook_url: Optional[str] = None
    discord_guild_id: Optional[str] = None
    discord_channel_id: Optional[str] = None
    discord_public_access: bool = False

    # 3. Mastodon
    mastodon_instance_url: str = "mastodon.social"
    mastodon_access_token: Optional[str] = None

    # 4. Twitter / X
    twitter_bearer_token: Optional[str] = None
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached instance of application settings."""
    return Settings()
