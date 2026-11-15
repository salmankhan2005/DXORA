"""Telegram Bot API integration for publishing messages to channels or groups."""

from datetime import datetime
from typing import Optional, Tuple
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class TelegramPlatform(BasePlatform):
    """Integrates with the official Telegram Bot API (sendMessage).

    Docs: https://core.telegram.org/bots/api#sendmessage
    """

    @property
    def name(self) -> str:
        return "Telegram"

    @property
    def default_public_access(self) -> bool:
        # Defaults to True when posting to a public channel
        return True if self.settings.telegram_channel_username else False

    def is_configured(self) -> bool:
        return bool(self.settings.telegram_bot_token and self.settings.telegram_chat_id)

    def configuration_error_message(self) -> str:
        return (
            "Authentication failed: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID "
            "must be configured in environment"
        )

    def _simulate_post(self, message: str, cta_url: str) -> PlatformResult:
        now = datetime.now()
        fake_id = int(now.timestamp()) % 100000 + 40000
        channel = (
            self.settings.telegram_channel_username.lstrip("@")
            if self.settings.telegram_channel_username
            else "dxora_channel"
        )
        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=f"https://t.me/{channel}/{fake_id}",
            public_access=True,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            error=None,
        )

    async def _publish(
        self, client: httpx.AsyncClient, message: str, cta_url: str
    ) -> Tuple[str, Optional[bool]]:
        token = self.settings.telegram_bot_token
        chat_id = self.settings.telegram_chat_id
        api_url = f"https://api.telegram.org/bot{token}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": False,
        }

        response = await client.post(api_url, json=payload)
        response.raise_for_status()

        data = response.json()
        if not data.get("ok"):
            raise ValueError(f"Telegram API error: {data.get('description', 'Unknown error')}")

        result = data.get("result", {})
        message_id = result.get("message_id")
        chat_info = result.get("chat", {})

        # Determine public URL and accessibility
        channel_username = (
            self.settings.telegram_channel_username
            or chat_info.get("username")
        )

        if channel_username:
            username_clean = channel_username.lstrip("@")
            posted_url = f"https://t.me/{username_clean}/{message_id}"
            public_access = True
        else:
            # Private chat or supergroup internal link
            raw_chat_id = str(chat_id).replace("-100", "").lstrip("-")
            posted_url = f"https://t.me/c/{raw_chat_id}/{message_id}"
            public_access = False

        return posted_url, public_access
