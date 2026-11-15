"""Unit tests for individual platform integration adapters."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.config import Settings
from app.platforms.telegram import TelegramPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.twitter import TwitterPlatform
from app.platforms.slack import SlackPlatform


def _mock_response(status_code: int = 200, json: dict = None, text: str = None) -> httpx.Response:
    """Helper to create httpx.Response with associated request instance for raise_for_status."""
    req = httpx.Request("POST", "https://api.mock.test")
    return httpx.Response(status_code, json=json, text=text, request=req)


def _clean_settings(**kwargs) -> Settings:
    """Creates a Settings instance with .env reading disabled for isolated unit tests."""
    defaults = {
        "_env_file": None,
        "simulation_mode": False,
        "telegram_bot_token": None,
        "telegram_chat_id": None,
        "telegram_channel_username": None,
        "discord_webhook_url": None,
        "mastodon_access_token": None,
        "twitter_bearer_token": None,
        "slack_webhook_url": None,
        "slack_bot_token": None,
        "slack_channel": None,
    }
    defaults.update(kwargs)
    return Settings(**defaults)


@pytest.mark.asyncio
async def test_telegram_unconfigured():
    settings = _clean_settings(simulation_mode=False)
    platform = TelegramPlatform(settings)
    assert not platform.is_configured()

    result = await platform.post("Test message https://example.com", "https://example.com")
    assert result.platform == "Telegram"
    assert result.status == "failed"
    assert "TELEGRAM_BOT_TOKEN" in result.error
    assert result.posted_url is None
    assert result.public_access is False


@pytest.mark.asyncio
async def test_telegram_simulation_mode():
    settings = _clean_settings(simulation_mode=True)
    platform = TelegramPlatform(settings)

    result = await platform.post("Test message https://example.com", "https://example.com")
    assert result.platform == "Telegram"
    assert result.status == "success"
    assert "t.me" in result.posted_url
    assert result.public_access is True
    assert result.error is None
    assert result.date is not None
    assert result.time is not None


@pytest.mark.asyncio
async def test_telegram_live_mock_public_channel():
    settings = _clean_settings(
        simulation_mode=False,
        telegram_bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        telegram_chat_id="-100987654321",
        telegram_channel_username="dxora_public",
    )
    platform = TelegramPlatform(settings)
    assert platform.is_configured()

    fake_resp = {
        "ok": True,
        "result": {
            "message_id": 999,
            "chat": {"id": -100987654321, "title": "Dxora Channel", "username": "dxora_public"},
            "date": 1731655800,
        },
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_response(200, json=fake_resp)

        result = await platform.post("Hello https://example.com", "https://example.com")
        assert result.status == "success"
        assert result.posted_url == "https://t.me/dxora_public/999"
        assert result.public_access is True


@pytest.mark.asyncio
async def test_telegram_private_chat():
    settings = _clean_settings(
        simulation_mode=False,
        telegram_bot_token="123456:token",
        telegram_chat_id="-100123456789",
        telegram_channel_username=None,
    )
    platform = TelegramPlatform(settings)

    fake_resp = {
        "ok": True,
        "result": {
            "message_id": 123,
            "chat": {"id": -100123456789, "title": "Private Group"},
            "date": 1731655800,
        },
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_response(200, json=fake_resp)

        result = await platform.post("Hello https://example.com", "https://example.com")
        assert result.status == "success"
        assert result.posted_url == "https://t.me/c/123456789/123"
        assert result.public_access is False


@pytest.mark.asyncio
async def test_discord_unconfigured():
    settings = _clean_settings(simulation_mode=False)
    platform = DiscordPlatform(settings)
    assert not platform.is_configured()

    result = await platform.post("Test https://example.com", "https://example.com")
    assert result.status == "failed"
    assert "DISCORD_WEBHOOK_URL" in result.error


@pytest.mark.asyncio
async def test_discord_live_mock():
    settings = _clean_settings(
        simulation_mode=False,
        discord_webhook_url="https://discord.com/api/webhooks/123/token",
        discord_guild_id="999888777",
    )
    platform = DiscordPlatform(settings)
    assert platform.is_configured()

    fake_resp = {
        "id": "555444333",
        "channel_id": "111222333",
        "guild_id": "999888777",
        "content": "Test https://example.com",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_response(200, json=fake_resp)

        result = await platform.post("Test https://example.com", "https://example.com")
        assert result.status == "success"
        assert result.posted_url == "https://discord.com/channels/999888777/111222333/555444333"
        assert result.public_access is False


@pytest.mark.asyncio
async def test_mastodon_live_mock():
    settings = _clean_settings(
        simulation_mode=False,
        mastodon_instance_url="mastodon.social",
        mastodon_access_token="fake_mastodon_token_123",
    )
    platform = MastodonPlatform(settings)
    assert platform.is_configured()

    fake_resp = {
        "id": "10987654321",
        "url": "https://mastodon.social/@dxora/10987654321",
        "visibility": "public",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_response(200, json=fake_resp)

        result = await platform.post("Test https://example.com", "https://example.com")
        assert result.status == "success"
        assert result.posted_url == "https://mastodon.social/@dxora/10987654321"
        assert result.public_access is True


@pytest.mark.asyncio
async def test_twitter_live_mock():
    settings = _clean_settings(
        simulation_mode=False,
        twitter_bearer_token="mock_bearer_token_xyz",
    )
    platform = TwitterPlatform(settings)
    assert platform.is_configured()

    tweet_resp = _mock_response(
        201, json={"data": {"id": "17928371928371", "text": "Post https://example.com"}}
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = tweet_resp

        result = await platform.post("Post https://example.com", "https://example.com")
        assert result.status == "success"
        assert result.posted_url == "https://x.com/i/status/17928371928371"
        assert result.public_access is True


@pytest.mark.asyncio
async def test_slack_webhook_mock():
    settings = _clean_settings(
        simulation_mode=False,
        slack_webhook_url="https://hooks.slack.com/services/T00/B00/XXXXX",
        slack_channel="C012345",
    )
    platform = SlackPlatform(settings)
    assert platform.is_configured()

    slack_resp = _mock_response(200, text="ok")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = slack_resp

        result = await platform.post("Slack post https://example.com", "https://example.com")
        assert result.status == "success"
        assert "slack.com/archives" in result.posted_url
        assert result.public_access is False


@pytest.mark.asyncio
async def test_slack_bot_token_mock():
    settings = _clean_settings(
        simulation_mode=False,
        slack_bot_token="xoxb-mock-bot-token",
        slack_channel="C998877",
    )
    platform = SlackPlatform(settings)
    assert platform.is_configured()

    post_resp = _mock_response(200, json={"ok": True, "ts": "1731655800.000100"})
    perm_resp = _mock_response(
        200,
        json={"ok": True, "permalink": "https://slack.com/archives/C998877/p1731655800000100"},
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock
    ) as mock_get:
        mock_post.return_value = post_resp
        mock_get.return_value = perm_resp

        result = await platform.post("Slack bot post https://example.com", "https://example.com")
        assert result.status == "success"
        assert result.posted_url == "https://slack.com/archives/C998877/p1731655800000100"
        assert result.public_access is False


@pytest.mark.asyncio
async def test_platform_http_error_handling():
    settings = _clean_settings(
        simulation_mode=False,
        twitter_bearer_token="mock_token",
    )
    platform = TwitterPlatform(settings)

    error_response = httpx.Response(
        status_code=401,
        text='{"errors":[{"message":"Could not authenticate you"}]}',
        request=httpx.Request("POST", "https://api.twitter.com/2/tweets"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = error_response

        result = await platform.post("Tweet https://example.com", "https://example.com")
        assert result.status == "failed"
        assert "HTTP 401" in result.error
        assert result.posted_url is None


@pytest.mark.asyncio
async def test_platform_timeout_handling():
    settings = _clean_settings(
        simulation_mode=False,
        twitter_bearer_token="mock_token",
    )
    platform = TwitterPlatform(settings)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timed out waiting for response")

        result = await platform.post("Tweet https://example.com", "https://example.com")
        assert result.status == "failed"
        assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_platform_network_error_handling():
    settings = _clean_settings(
        simulation_mode=False,
        twitter_bearer_token="mock_token",
    )
    platform = TwitterPlatform(settings)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.RequestError("Connection refused by host")

        result = await platform.post("Tweet https://example.com", "https://example.com")
        assert result.status == "failed"
        assert "Network error" in result.error
