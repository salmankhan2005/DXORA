"""Pytest configuration and shared fixtures."""

import os
import pytest
from fastapi.testclient import TestClient

# Ensure test environment doesn't load accidental local overrides
os.environ["SIMULATION_MODE"] = "false"

from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing clean unconfigured settings."""
    return Settings(
        simulation_mode=False,
        telegram_bot_token=None,
        telegram_chat_id=None,
        discord_webhook_url=None,
        mastodon_access_token=None,
        reddit_client_id=None,
        twitter_bearer_token=None,
        slack_webhook_url=None,
    )


@pytest.fixture
def simulation_settings() -> Settings:
    """Fixture providing settings configured for simulation mode."""
    return Settings(
        simulation_mode=True,
    )


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)
