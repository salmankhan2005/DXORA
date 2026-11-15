"""Pytest configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing clean unconfigured settings isolated from any local .env file."""
    return Settings(
        _env_file=None,
        simulation_mode=False,
        telegram_bot_token=None,
        telegram_chat_id=None,
        telegram_channel_username=None,
        discord_webhook_url=None,
        mastodon_access_token=None,
        twitter_bearer_token=None,
        slack_webhook_url=None,
        slack_bot_token=None,
        slack_channel=None,
    )


@pytest.fixture
def simulation_settings() -> Settings:
    """Fixture providing settings configured for simulation mode."""
    return Settings(
        _env_file=None,
        simulation_mode=True,
    )


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)
